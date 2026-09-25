"""Loads (or trains) both models and runs the full pipeline: validate -> clean -> features -> predict -> explain."""
from __future__ import annotations

import json
import threading
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn

import config
from ml import feature_config as fc
import analytics
import bottleneck_detector as bd
from data_cleaner import CleaningResult, ValidationError, clean_orders, read_csv_bytes
from delay_predictor import DelayPredictor
from eta_predictor import EtaPredictor
from explainer import explain_order
from feature_engineering import engineer_features
from utils import build_timeline, delay_rule_text, records, summary_text

DELAY_PATH = config.MODEL_DIR / "delay_classifier.joblib"
ETA_PATH = config.MODEL_DIR / "eta_regressor.joblib"
METRICS_PATH = config.MODEL_DIR / "metrics.json"

ORDER_FIELDS = [
    "order_id", "order_time", "hour", "day_of_week", "num_items", "order_value", "prep_time", "restaurant_load",
    "rider_assignment_delay", "pickup_wait", "distance_km", "traffic_level", "weather", "area_type", "rider_experience",
    "peak_hour", "batch_delivery", "promised_eta", "promised_eta_estimated", "distance_category", "status",
    "delay_probability", "delay_confidence", "eta_minutes", "primary_bottleneck", "primary_pct", "secondary_bottleneck",
    "secondary_pct", "actual_delivery_time", "actual_delayed", "outlier_flag",
]


class ModelService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._demo: dict | None = None
        self.delay: DelayPredictor | None = None
        self.eta: EtaPredictor | None = None
        self.metrics: dict = {}

    # ---- lifecycle ---------------------------------------------------------------------------------
    def _artifacts_current(self) -> bool:
        if not (DELAY_PATH.exists() and ETA_PATH.exists() and METRICS_PATH.exists()):
            return False
        try:
            trained_with = json.loads(METRICS_PATH.read_text())["dataset"]["sklearn_version"]
            trained_delay = json.loads(METRICS_PATH.read_text())["config"]["delay_grace_minutes"]
        except (KeyError, ValueError):
            return False
        return trained_with == sklearn.__version__ and trained_delay == fc.DELAY_GRACE_MINUTES

    def load(self) -> None:
        if not self._artifacts_current():
            print("[orderflow] models missing or stale, training (about 30 s)...", flush=True)
            from ml.evaluate import combine_metrics
            from ml.train_delay_model import train as train_delay
            from ml.train_eta_model import train as train_eta
            train_delay(verbose=False)
            train_eta(verbose=False)
            combine_metrics()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d, e = joblib.load(DELAY_PATH), joblib.load(ETA_PATH)
        self.delay = DelayPredictor(d["pipeline"])
        self.eta = EtaPredictor(e["pipeline"], e["meta"])
        self.metrics = json.loads(METRICS_PATH.read_text())

    @property
    def ready(self) -> bool:
        return self.delay is not None and self.eta is not None

    # ---- scoring -------------------------------------------------------------------------------------
    def _score(self, cleaned: pd.DataFrame, detailed: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
        feats = engineer_features(cleaned)
        d = self.delay.predict(feats)
        e = self.eta.predict(feats)
        b = bd.detect(cleaned, self.eta, e["eta_minutes"].to_numpy(), detailed=detailed)
        scored = pd.concat([feats, d, e, b], axis=1)
        scored["hour"] = np.floor(scored["order_hour"]).astype(int)
        scored["expected_delay_minutes"] = (scored["eta_minutes"] - scored["promised_eta"]).clip(lower=0)
        scored["actual_delayed"] = scored["delayed"]
        return scored, feats

    # ---- single order --------------------------------------------------------------------------------
    def analyze_order(self, order: dict) -> dict:
        try:
            cleaned_res = clean_orders(pd.DataFrame([{k: ("" if v is None else v) for k, v in order.items()}]).astype(str))
        except ValidationError as exc:
            if exc.issues:
                raise ValidationError(f"Invalid order: {exc.issues[0]['reason']}.", exc.issues) from exc
            raise
        cleaned = cleaned_res.df
        scored, _ = self._score(cleaned, detailed=True)
        r = scored.iloc[0]
        stages, total = build_timeline(cleaned, float(r["eta_minutes"]), r["primary_bottleneck"], r["secondary_bottleneck"])
        primary = {"name": r["primary_bottleneck"], "contribution_pct": float(r["primary_pct"]), "minutes": float(r["primary_minutes"])}
        secondary = ({"name": r["secondary_bottleneck"], "contribution_pct": float(r["secondary_pct"]), "minutes": float(r["secondary_minutes"])}
                     if r["secondary_bottleneck"] else None)
        out = {
            "order_id": str(r["order_id"]), "status": r["status"], "delay_probability": float(r["delay_probability"]),
            "predicted_delayed": bool(r["predicted_delayed"]), "delay_confidence": r["delay_confidence"],
            "eta": {"minutes": float(r["eta_minutes"]), "low": float(r["eta_low"]), "high": float(r["eta_high"]),
                    "confidence": r["eta_confidence"]},
            "promised_eta": float(r["promised_eta"]), "promised_eta_estimated": bool(r["promised_eta_estimated"]),
            "expected_delay_minutes": float(r["expected_delay_minutes"]),
            "bottleneck": {"primary": primary, "secondary": secondary, "contributions": r["contributions"],
                           "method": "Rules (excess minutes vs normal stage durations, 70%) blended with an ETA-model what-if check (30%)."},
            "pipeline": {"stages": stages, "total_minutes": total},
            "explanation": explain_order(cleaned, self.delay, float(r["delay_probability"])),
            "inputs": records(cleaned[["order_id", "order_time", "day_of_week", "num_items", "order_value", "prep_time",
                                       "restaurant_load", "rider_assignment_delay", "pickup_wait", "distance_km",
                                       "traffic_level", "weather", "area_type", "rider_experience", "peak_hour",
                                       "weekend", "batch_delivery"]])[0],
            "warnings": cleaned_res.warnings + ([f"Outlier flagged and clipped: {cleaned.iloc[0]['outlier_fields'].replace(';', ', ')}."]
                                                if cleaned.iloc[0]["outlier_flag"] else []),
            "delay_rule": delay_rule_text(),
        }
        out["summary"] = summary_text(out)
        return out

    # ---- batch ---------------------------------------------------------------------------------------
    def analyze_batch(self, raw: pd.DataFrame, source: str = "upload", filename: str | None = None) -> dict:
        res: CleaningResult = clean_orders(raw)
        scored, _ = self._score(res.df)
        scored["order_id"] = scored["order_id"].astype(str)
        cols = [c for c in ORDER_FIELDS if c in scored.columns]
        table = scored[cols].copy()
        for c in ("delay_probability", "primary_pct", "secondary_pct"):
            table[c] = table[c].round(4 if c == "delay_probability" else 1)
        table["eta_minutes"] = table["eta_minutes"].round(1)
        return {
            "source": source, "filename": filename,
            "quality": {**res.summary, "warnings": res.warnings, "issues": res.issues[:100], "issues_truncated": len(res.issues) > 100},
            "summary": analytics.summarize(scored), "charts": analytics.build_charts(scored),
            "orders": records(table.head(config.TABLE_ROW_CAP)), "orders_truncated": len(table) > config.TABLE_ROW_CAP,
            "delay_rule": delay_rule_text(),
        }

    def analyze_csv(self, data: bytes, filename: str | None) -> dict:
        return self.analyze_batch(read_csv_bytes(data), "upload", filename)

    def demo_batch(self) -> dict:
        with self._lock:
            if self._demo is None:
                if not config.DEMO_CSV.exists():
                    import synthetic_data
                    config.DATA_DIR.mkdir(exist_ok=True)
                    synthetic_data.generate_orders(600, seed=2026).to_csv(config.DEMO_CSV, index=False)
                raw = pd.read_csv(config.DEMO_CSV, dtype=str, keep_default_na=False)
                self._demo = self.analyze_batch(raw, "demo", "demo_orders.csv")
            return self._demo


service = ModelService()

__all__ = ["service", "ModelService", "ValidationError"]
