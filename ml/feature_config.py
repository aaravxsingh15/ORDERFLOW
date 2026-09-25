"""Single source of truth for ORDERFLOW's schema, delay rule, encodings and feature lists.

Everything the cleaner, the feature builder, both models, the bottleneck detector and the synthetic
generator need to agree on lives here, so assumptions are visible in one place.
"""
from __future__ import annotations

import os

# --------------------------------------------------------------------------------------------
# DELAY DEFINITION  (configurable, deliberately not hidden)
#   An order is DELAYED when   actual_delivery_time > promised_eta + DELAY_GRACE_MINUTES
# Override with the ORDERFLOW_DELAY_GRACE_MIN environment variable; retrain after changing it.
# --------------------------------------------------------------------------------------------
DELAY_GRACE_MINUTES: float = float(os.environ.get("ORDERFLOW_DELAY_GRACE_MIN", "5"))

# Status bands applied to the classifier's delay probability.
STATUS_ON_TIME_BELOW: float = 0.30      # p <  0.30            -> ON TIME
STATUS_DELAY_LIKELY_FROM: float = 0.60  # 0.30 <= p < 0.60     -> AT RISK ; p >= 0.60 -> DELAY LIKELY
CLASSIFIER_THRESHOLD: float = 0.50      # "Predicted class" = Delayed when p >= 0.50

# --------------------------------------------------------------------------------------------
# Categorical vocabularies (ordered from mildest to most severe where an order exists)
# --------------------------------------------------------------------------------------------
TRAFFIC_LEVELS = ["Low", "Moderate", "Heavy", "Severe"]
WEATHER = ["Clear", "Rain", "Fog", "Hot", "Cold"]
AREA_TYPES = ["Urban", "Dense Urban", "Suburban"]
RESTAURANT_LOADS = ["Low", "Moderate", "High", "Very High"]
RIDER_EXPERIENCE = ["New", "Moderate", "Experienced"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKEND_DAYS = {"Saturday", "Sunday"}

CATEGORIES: dict[str, list[str]] = {
    "traffic_level": TRAFFIC_LEVELS,
    "weather": WEATHER,
    "area_type": AREA_TYPES,
    "restaurant_load": RESTAURANT_LOADS,
    "rider_experience": RIDER_EXPERIENCE,
    "day_of_week": DAYS,
}

# Ordinal scores
TRAFFIC_SCORE = {v: i for i, v in enumerate(TRAFFIC_LEVELS)}            # 0..3
LOAD_SCORE = {v: i for i, v in enumerate(RESTAURANT_LOADS)}              # 0..3
EXPERIENCE_SCORE = {"New": 0, "Moderate": 1, "Experienced": 2}

# Domain priors used for the travel-burden feature and the bottleneck rules (documented in README)
FREE_FLOW_SPEED_KMPH = 30.0
TRAFFIC_MULT = {"Low": 1.0, "Moderate": 1.25, "Heavy": 1.6, "Severe": 2.1}
WEATHER_MULT = {"Clear": 1.0, "Rain": 1.25, "Fog": 1.15, "Hot": 1.05, "Cold": 1.03}

# Peak windows (decimal hours) used to derive `peak_hour` when the column is absent
PEAK_WINDOWS = [(12.0, 14.5), (19.0, 22.5)]

# What a "normal" restaurant / rider stage looks like (bottleneck rules measure excess over these)
NORMAL_PREP_BASE_MIN = 7.0
NORMAL_PREP_PER_ITEM_MIN = 1.8
NORMAL_ASSIGN_MIN = 3.0
NORMAL_WAIT_MIN = 3.0
ACCEPT_MIN = 1.0  # restaurant acceptance lag, included in total delivery time

# Platform quote used by the generator and as fallback when promised_eta is not supplied
QUOTE_BASE_MIN = 18.0
QUOTE_PER_KM = 3.6
QUOTE_PER_ITEM = 1.4
QUOTE_FLOOR_MIN = 20.0


def baseline_quote(distance_km, num_items):
    """Deterministic platform quote (minutes) from distance and basket size."""
    q = QUOTE_BASE_MIN + QUOTE_PER_KM * distance_km + QUOTE_PER_ITEM * num_items
    try:
        return q.clip(lower=QUOTE_FLOOR_MIN).round()
    except AttributeError:
        return max(QUOTE_FLOOR_MIN, round(q))


def normal_prep_minutes(num_items):
    return NORMAL_PREP_BASE_MIN + NORMAL_PREP_PER_ITEM_MIN * num_items


# --------------------------------------------------------------------------------------------
# CSV schema
# --------------------------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "order_id", "order_time", "num_items", "order_value", "prep_time", "restaurant_load",
    "rider_assignment_delay", "pickup_wait", "distance_km", "traffic_level", "weather",
    "area_type", "rider_experience",
]
# day_of_week is required unless order_time carries a full date; peak_hour / weekend are derived if absent.
OPTIONAL_COLUMNS = [
    "day_of_week", "peak_hour", "weekend", "promised_eta", "actual_delivery_time",
    "customer_zone", "restaurant_zone", "batch_delivery",
]
CSV_COLUMNS = [
    "order_id", "order_time", "day_of_week", "num_items", "order_value", "prep_time", "restaurant_load",
    "rider_assignment_delay", "pickup_wait", "distance_km", "traffic_level", "weather", "area_type",
    "rider_experience", "peak_hour", "actual_delivery_time", "promised_eta",
    "customer_zone", "restaurant_zone", "batch_delivery",
]

# Plausibility limits. Beyond IMPOSSIBLE the row is rejected; beyond SOFT it is kept, flagged and clipped.
SOFT_LIMITS = {"prep_time": 60, "rider_assignment_delay": 30, "pickup_wait": 30, "distance_km": 20,
               "num_items": 20, "order_value": 5000, "actual_delivery_time": 150}
IMPOSSIBLE_LIMITS = {"prep_time": 240, "rider_assignment_delay": 180, "pickup_wait": 180, "distance_km": 100,
                     "num_items": 60, "order_value": 100000, "actual_delivery_time": 480, "promised_eta": 300}

# --------------------------------------------------------------------------------------------
# Model features
# --------------------------------------------------------------------------------------------
CATEGORICAL_FEATURES = ["weather", "area_type"]
REGRESSOR_NUMERIC = [
    "num_items", "order_value", "prep_time", "rider_assignment_delay", "pickup_wait", "distance_km",
    "pre_pickup_time", "operational_delay", "distance_per_item", "prep_per_item",
    "assignment_delay_ratio", "pickup_delay_ratio", "peak_hour_score", "weekend", "traffic_score",
    "load_score", "rider_experience_score", "batch_delivery", "order_complexity", "travel_burden",
    "operational_pressure",
]
# The classifier additionally sees the quoted ETA, because "late" is defined relative to that promise.
CLASSIFIER_EXTRA = ["promised_eta", "transit_budget", "quote_slack"]
CLASSIFIER_NUMERIC = REGRESSOR_NUMERIC + CLASSIFIER_EXTRA

FEATURE_LABELS = {
    "num_items": "Number of Items", "order_value": "Order Value", "prep_time": "Restaurant Preparation Time",
    "rider_assignment_delay": "Rider Assignment Delay", "pickup_wait": "Pickup Wait", "distance_km": "Delivery Distance",
    "pre_pickup_time": "Total Pre-Pickup Time", "operational_delay": "Total Operational Delay",
    "distance_per_item": "Distance per Item", "prep_per_item": "Preparation Time per Item",
    "assignment_delay_ratio": "Assignment Delay Ratio", "pickup_delay_ratio": "Pickup Delay Ratio",
    "peak_hour_score": "Peak Hour Score", "weekend": "Weekend", "traffic_score": "Traffic Severity",
    "load_score": "Restaurant Load", "rider_experience_score": "Rider Experience", "batch_delivery": "Batch Delivery",
    "order_complexity": "Order Complexity", "travel_burden": "Estimated Travel Burden",
    "operational_pressure": "Combined Operational Pressure", "promised_eta": "Promised ETA",
    "transit_budget": "Transit Budget (ETA - pre-pickup)", "quote_slack": "Quote Slack vs Travel Estimate",
    "weather": "Weather", "area_type": "Area Type",
}

RANDOM_STATE = 42
TEST_SIZE = 0.2
