"""Batch aggregation: scored orders -> summary numbers and chart-ready series (all from real predictions)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config  # noqa: F401
from ml import feature_config as fc
from ml.evaluate import classification_metrics, regression_metrics
from feature_engineering import DISTANCE_LABELS

STATUS_ORDER = ["ON TIME", "AT RISK", "DELAY LIKELY"]


def _r(x, nd: int = 4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def _group(df: pd.DataFrame, col: str, order: list, has_actual: bool, eta: bool = False) -> list[dict]:
    rows = []
    for key in order:
        g = df[df[col] == key]
        if g.empty:
            continue
        row = {"label": str(key), "orders": int(len(g)), "avg_delay_probability": _r(g["delay_probability"].mean())}
        if eta:
            row.update(avg_eta=_r(g["eta_minutes"].mean(), 1), actual_avg=_r(g["actual_delivery_time"].mean(), 1) if has_actual else None)
        else:
            row["actual_delay_rate"] = _r(g["actual_delayed"].mean()) if has_actual else None
        rows.append(row)
    return rows


def worst_window(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    hourly = df.groupby("hour")["delay_probability"].agg(["mean", "count"])
    eligible = hourly[hourly["count"] >= max(10, int(0.02 * len(df)))]
    hourly = eligible if not eligible.empty else hourly
    h = int(hourly["mean"].idxmax())
    return f"{h:02d}:00-{(h + 1) % 24:02d}:00"


def summarize(df: pd.DataFrame) -> dict:
    has_actual = bool(df["actual_delivery_time"].notna().any())
    labelled = df[df["actual_delayed"].notna()]
    counts = df["status"].value_counts()
    top = df["primary_bottleneck"].value_counts()
    real_bottlenecks = top.drop(labels=["No Major Bottleneck"], errors="ignore")
    summary = {
        "orders_analysed": int(len(df)),
        "on_time": int(counts.get("ON TIME", 0)), "at_risk": int(counts.get("AT RISK", 0)),
        "delay_likely": int(counts.get("DELAY LIKELY", 0)),
        "avg_eta_minutes": _r(df["eta_minutes"].mean(), 1), "avg_delay_probability": _r(df["delay_probability"].mean()),
        "most_common_bottleneck": str(real_bottlenecks.index[0]) if len(real_bottlenecks) else "No Major Bottleneck",
        "worst_delay_window": worst_window(df),
        "has_actuals": has_actual, "evaluation": None,
    }
    if has_actual and len(labelled) >= 2 and labelled["actual_delayed"].nunique() == 2:
        cls = classification_metrics(labelled["actual_delayed"].to_numpy(), labelled["delay_probability"].to_numpy())
        act = df[df["actual_delivery_time"].notna()]
        summary["evaluation"] = {
            "orders_compared": int(len(labelled)), "actual_delay_rate": _r(labelled["actual_delayed"].mean()),
            "classification": {k: _r(cls[k]) for k in ("accuracy", "precision", "recall", "f1", "roc_auc")},
            "eta": {k: _r(v, 3) for k, v in regression_metrics(act["actual_delivery_time"], act["eta_minutes"]).items()},
        }
    return summary


def build_charts(df: pd.DataFrame) -> dict:
    has_actual = bool(df["actual_delivery_time"].notna().any())
    bins = np.clip((df["delay_probability"] * 10).astype(int), 0, 9)
    hist = [{"bin": f"{i * 10}-{i * 10 + 10}%", "count": int((bins == i).sum())} for i in range(10)]

    avp = []
    if has_actual:
        sample = df[df["actual_delivery_time"].notna()]
        sample = sample.sample(min(500, len(sample)), random_state=fc.RANDOM_STATE)
        avp = [{"actual": _r(a, 1), "predicted": _r(p, 1)} for a, p in zip(sample["actual_delivery_time"], sample["eta_minutes"])]

    hourly = []
    for h, g in df.groupby("hour"):
        hourly.append({"hour": int(h), "label": f"{int(h):02d}:00", "orders": int(len(g)),
                       "avg_delay_probability": _r(g["delay_probability"].mean()),
                       "actual_delay_rate": _r(g["actual_delayed"].mean()) if has_actual and g["actual_delayed"].notna().any() else None})

    peak = df.assign(_peak=np.where(df["peak_hour"] == 1, "Peak", "Off-peak"))
    return {
        "probability_histogram": hist,
        "actual_vs_predicted": avp,
        "status_counts": [{"status": s, "count": int((df["status"] == s).sum())} for s in STATUS_ORDER],
        "by_traffic": _group(df, "traffic_level", fc.TRAFFIC_LEVELS, has_actual),
        "by_restaurant_load": _group(df, "restaurant_load", fc.RESTAURANT_LOADS, has_actual),
        "eta_by_distance": _group(df, "distance_category", DISTANCE_LABELS, has_actual, eta=True),
        "bottlenecks": [{"name": k, "count": int(v)} for k, v in df["primary_bottleneck"].value_counts().items()],
        "peak_vs_offpeak": _group(peak, "_peak", ["Peak", "Off-peak"], has_actual),
        "hourly": hourly,
    }
