"""Feature engineering: cleaned orders -> model features. Every derived column has an operational meaning."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config  # noqa: F401
from ml import feature_config as fc

DISTANCE_BANDS = [(0, 2, "0-2 km"), (2, 5, "2-5 km"), (5, 8, "5-8 km"), (8, 1e9, "8+ km")]
DISTANCE_LABELS = [b[2] for b in DISTANCE_BANDS]


def distance_category(distance_km: pd.Series) -> pd.Series:
    labels = np.select([(distance_km >= lo) & (distance_km < hi) for lo, hi, _ in DISTANCE_BANDS], DISTANCE_LABELS, default="8+ km")
    return pd.Series(labels, index=distance_km.index)


def _peak_bump(hour: pd.Series) -> pd.Series:
    """Smooth 0-1 proximity to the lunch (13:15) and dinner (20:30) rushes."""
    lunch = np.exp(-((hour - 13.25) ** 2) / (2 * 1.1 ** 2))
    dinner = np.exp(-((hour - 20.5) ** 2) / (2 * 1.4 ** 2))
    return np.maximum(lunch, dinner)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds engineered columns to a cleaned frame (returns a new frame)."""
    f = df.copy()
    items = f["num_items"].clip(lower=1).astype(float)
    dist = f["distance_km"].astype(float)

    f["traffic_score"] = f["traffic_level"].map(fc.TRAFFIC_SCORE).astype(float)
    f["load_score"] = f["restaurant_load"].map(fc.LOAD_SCORE).astype(float)
    f["rider_experience_score"] = f["rider_experience"].map(fc.EXPERIENCE_SCORE).astype(float)

    # time spent before the rider leaves the restaurant
    f["pre_pickup_time"] = f["prep_time"] + f["rider_assignment_delay"] + f["pickup_wait"]
    # minutes lost beyond what is normal for this basket / for assignment and pickup
    f["operational_delay"] = (
        (f["prep_time"] - fc.normal_prep_minutes(items)).clip(lower=0)
        + (f["rider_assignment_delay"] - fc.NORMAL_ASSIGN_MIN).clip(lower=0)
        + (f["pickup_wait"] - fc.NORMAL_WAIT_MIN).clip(lower=0)
    )
    f["distance_per_item"] = dist / items
    f["prep_per_item"] = f["prep_time"] / items
    denom = f["pre_pickup_time"].clip(lower=1.0)
    f["assignment_delay_ratio"] = f["rider_assignment_delay"] / denom
    f["pickup_delay_ratio"] = f["pickup_wait"] / denom

    f["peak_hour_score"] = (0.5 * f["peak_hour"] + 0.5 * _peak_bump(f["order_hour"])).round(4)
    f["distance_category"] = distance_category(dist)
    f["order_complexity"] = items + 3 * f["batch_delivery"] + (items >= 7) * 2
    # distance stretched by traffic and weather: the free-flow-equivalent km the rider effectively covers
    t_mult = f["traffic_level"].map(fc.TRAFFIC_MULT).astype(float)
    w_mult = f["weather"].map(fc.WEATHER_MULT).astype(float)
    f["travel_burden"] = dist * t_mult * w_mult
    f["operational_pressure"] = (
        0.30 * f["load_score"] / 3 + 0.25 * f["traffic_score"] / 3 + 0.20 * f["peak_hour_score"]
        + 0.15 * (f["pre_pickup_time"] / 45).clip(upper=1) + 0.10 * (f["order_complexity"] / 12).clip(upper=1)
    ).round(4)

    # time left in the promise once the rider has left the restaurant (classifier only)
    f["transit_budget"] = f["promised_eta"] - fc.ACCEPT_MIN - f["pre_pickup_time"]
    # ...and how that budget compares with a prior-based travel estimate (free-flow time x traffic x weather + handover);
    # one combined number keeps unusual orders inside well-covered territory for the tree model
    est_travel_min = f["travel_burden"] / fc.FREE_FLOW_SPEED_KMPH * 60 + 3
    f["quote_slack"] = f["transit_budget"] + fc.DELAY_GRACE_MINUTES - est_travel_min
    return f


def model_frame(features: pd.DataFrame, kind: str) -> pd.DataFrame:
    cols = (fc.CLASSIFIER_NUMERIC if kind == "classifier" else fc.REGRESSOR_NUMERIC) + fc.CATEGORICAL_FEATURES
    return features[cols]
