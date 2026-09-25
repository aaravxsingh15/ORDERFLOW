"""Per-order 'why was this flagged?' explanation for the delay classifier.

Occlusion method: reset one group of inputs to a typical value, re-predict, and read how much the delay
probability moves. Influence shows what the model responds to, not what physically caused the delay.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config  # noqa: F401
from ml import feature_config as fc
from delay_predictor import DelayPredictor
from feature_engineering import engineer_features

TYPICAL_DISTANCE_KM = 3.5
TYPICAL_ITEMS = 3
TYPICAL_HOUR = 15.5


def _groups(c: pd.DataFrame) -> dict[str, pd.DataFrame]:
    items = c["num_items"].astype(float)
    return {
        "Restaurant Preparation Time": c.assign(prep_time=fc.normal_prep_minutes(items)),
        "Restaurant Load": c.assign(restaurant_load="Moderate"),
        "Rider Assignment Delay": c.assign(rider_assignment_delay=fc.NORMAL_ASSIGN_MIN),
        "Pickup Wait": c.assign(pickup_wait=fc.NORMAL_WAIT_MIN),
        "Delivery Distance": c.assign(distance_km=TYPICAL_DISTANCE_KM),
        "Traffic Level": c.assign(traffic_level="Moderate"),
        "Weather": c.assign(weather="Clear"),
        "Order Size": c.assign(num_items=TYPICAL_ITEMS, batch_delivery=0),
        "Peak Hour": c.assign(peak_hour=0, order_hour=TYPICAL_HOUR),
        "Area Type": c.assign(area_type="Urban"),
        "Rider Experience": c.assign(rider_experience="Moderate"),
        "Promised ETA": c.assign(promised_eta=fc.baseline_quote(c["distance_km"], c["num_items"])),
    }


def _display(label: str, r: pd.Series) -> str:
    return {
        "Restaurant Preparation Time": f"{r['prep_time']:g} min", "Restaurant Load": str(r["restaurant_load"]),
        "Rider Assignment Delay": f"{r['rider_assignment_delay']:g} min", "Pickup Wait": f"{r['pickup_wait']:g} min",
        "Delivery Distance": f"{r['distance_km']:g} km", "Traffic Level": str(r["traffic_level"]),
        "Weather": str(r["weather"]), "Order Size": f"{int(r['num_items'])} items" + (" (batch)" if r["batch_delivery"] else ""),
        "Peak Hour": "Yes" if r["peak_hour"] else "No", "Area Type": str(r["area_type"]),
        "Rider Experience": str(r["rider_experience"]), "Promised ETA": f"{r['promised_eta']:g} min",
    }[label]


def explain_order(cleaned_row: pd.DataFrame, delay: DelayPredictor, base_probability: float, top: int = 6) -> list[dict]:
    """cleaned_row: a one-row cleaned frame."""
    groups = _groups(cleaned_row)
    stacked = pd.concat(groups.values(), ignore_index=True)
    p_ref = delay.predict_proba(engineer_features(stacked))
    delta = base_probability - p_ref                      # >0: this input pushes delay risk up vs a typical order
    total = float(np.abs(delta).sum())
    row = cleaned_row.iloc[0]
    out = [{
        "label": label, "value": _display(label, row), "delta_probability": float(d),
        "influence_pct": float(abs(d) / total * 100) if total > 1e-9 else 0.0,
        "direction": "increases" if d > 0.005 else "reduces" if d < -0.005 else "neutral",
    } for label, d in zip(groups, delta)]
    out.sort(key=lambda r: -r["influence_pct"])
    return out[:top]
