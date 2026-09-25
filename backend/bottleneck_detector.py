"""Bottleneck detection: which stage most likely contributed the most excess minutes to an order.

Transparent rules measure how far each stage runs past what is normal (see ml/feature_config.py).
A what-if check on the ETA regressor (set that one factor back to normal, re-predict, read the drop in
ETA) is blended in at 30% so the ranking also reflects what the trained model has learned.

The output is a *likely contributing factor*, never a proven cause.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config  # noqa: F401
from ml import feature_config as fc
from eta_predictor import EtaPredictor
from feature_engineering import engineer_features

NO_BOTTLENECK = "No Major Bottleneck"
FACTORS = ["Restaurant Preparation", "Rider Assignment", "Pickup Waiting", "Transit / Traffic",
           "Weather", "High Order Complexity", "Restaurant Overload"]
CATEGORIES = FACTORS + [NO_BOTTLENECK]

RULE_WEIGHT, MODEL_WEIGHT = 0.7, 0.3
MIN_PRIMARY_MINUTES = 3.0     # below this the order has no stand-out bottleneck
MIN_SECONDARY_MINUTES = 2.0
OVERLOAD_SHARE = {"Low": 0.0, "Moderate": 0.0, "High": 0.3, "Very High": 0.6}  # share of prep excess blamed on load

# stage of the delivery pipeline each factor belongs to (for the timeline highlight)
FACTOR_STAGE = {"Restaurant Preparation": "preparing", "Restaurant Overload": "preparing", "High Order Complexity": "preparing",
                "Rider Assignment": "assignment", "Pickup Waiting": "pickup", "Transit / Traffic": "transit", "Weather": "transit"}


def rule_minutes(c: pd.DataFrame) -> pd.DataFrame:
    """Excess minutes per factor from transparent rules (c = cleaned orders)."""
    items = c["num_items"].astype(float)
    prep_excess = (c["prep_time"] - fc.normal_prep_minutes(items)).clip(lower=0)
    share = c["restaurant_load"].map(OVERLOAD_SHARE).astype(float)
    free_flow = c["distance_km"] / fc.FREE_FLOW_SPEED_KMPH * 60
    t_mult = c["traffic_level"].map(fc.TRAFFIC_MULT).astype(float)
    w_mult = c["weather"].map(fc.WEATHER_MULT).astype(float)
    return pd.DataFrame({
        "Restaurant Preparation": prep_excess * (1 - share),
        "Restaurant Overload": prep_excess * share,
        "Rider Assignment": (c["rider_assignment_delay"] - fc.NORMAL_ASSIGN_MIN).clip(lower=0),
        "Pickup Waiting": (c["pickup_wait"] - fc.NORMAL_WAIT_MIN).clip(lower=0),
        "Transit / Traffic": free_flow * (t_mult - 1),
        "Weather": free_flow * t_mult * (w_mult - 1),
        "High Order Complexity": (items - 6).clip(lower=0) * 1.5 + c["batch_delivery"] * 3.0,
    }, index=c.index)


def _what_if_minutes(c: pd.DataFrame, eta: EtaPredictor, base_eta: np.ndarray) -> pd.DataFrame:
    """Drop in predicted ETA when one factor is reset to normal (model-based, per order)."""
    items = c["num_items"].astype(float)

    def drop(modified: pd.DataFrame) -> np.ndarray:
        return np.clip(base_eta - eta.predict_minutes(engineer_features(modified)), 0, None)

    prep = drop(c.assign(prep_time=np.minimum(c["prep_time"], fc.normal_prep_minutes(items))))
    share = c["restaurant_load"].map(OVERLOAD_SHARE).astype(float).to_numpy()
    return pd.DataFrame({
        "Restaurant Preparation": prep * (1 - share),
        "Restaurant Overload": prep * share,
        "Rider Assignment": drop(c.assign(rider_assignment_delay=np.minimum(c["rider_assignment_delay"], fc.NORMAL_ASSIGN_MIN))),
        "Pickup Waiting": drop(c.assign(pickup_wait=np.minimum(c["pickup_wait"], fc.NORMAL_WAIT_MIN))),
        "Transit / Traffic": drop(c.assign(traffic_level="Low")),
        "Weather": drop(c.assign(weather="Clear")),
        "High Order Complexity": drop(c.assign(num_items=np.minimum(c["num_items"], 4), batch_delivery=0)),
    }, index=c.index)


def detect(cleaned: pd.DataFrame, eta: EtaPredictor, base_eta: np.ndarray, detailed: bool = False) -> pd.DataFrame:
    """Per-order bottleneck. `detailed=True` also returns every factor's score/share (used for single orders)."""
    rules = rule_minutes(cleaned)
    scores = RULE_WEIGHT * rules + MODEL_WEIGHT * _what_if_minutes(cleaned, eta, base_eta)
    arr = scores[FACTORS].to_numpy()
    total = arr.sum(axis=1)
    order = np.argsort(-arr, axis=1)
    rows = np.arange(len(arr))
    p1, p2 = order[:, 0], order[:, 1]
    s1, s2 = arr[rows, p1], arr[rows, p2]
    pct = lambda s: np.where(total > 0, s / np.where(total > 0, total, 1) * 100, 0.0)
    has_primary = s1 >= MIN_PRIMARY_MINUTES
    has_secondary = has_primary & (s2 >= MIN_SECONDARY_MINUTES)
    fac = np.asarray(FACTORS, dtype=object)
    out = pd.DataFrame({
        "primary_bottleneck": np.where(has_primary, fac[p1], NO_BOTTLENECK),
        "primary_pct": np.where(has_primary, pct(s1), 0.0),
        "primary_minutes": np.where(has_primary, s1, 0.0),
        "secondary_bottleneck": np.where(has_secondary, fac[p2], None),
        "secondary_pct": np.where(has_secondary, pct(s2), 0.0),
        "secondary_minutes": np.where(has_secondary, s2, 0.0),
        "excess_minutes_total": total,
    }, index=cleaned.index)
    if detailed:
        out["contributions"] = [
            [{"name": FACTORS[j], "minutes": float(arr[i, j]), "pct": float(arr[i, j] / total[i] * 100) if total[i] > 0 else 0.0}
             for j in order[i] if arr[i, j] >= 0.5]
            for i in range(len(arr))
        ]
    return out
