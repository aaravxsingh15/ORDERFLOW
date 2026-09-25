"""Synthetic food-delivery order generator.

Relationships are logical but noisy (nothing is deterministic):
  * heavy traffic, rain and long distance stretch transit time
  * high restaurant load inflates preparation time; peak hours load restaurants and thin out riders
  * long rider-assignment delays and pickup waits add straight to the total
  * a small share of orders hit an *unobserved* incident (address issue, rider breakdown, order re-made),
    and a few restaurants/riders have outright outages: these are the natural anomalies.
The platform's promised ETA starts from distance and basket size, partly reflects live conditions, and is noisy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config  # noqa: F401
from ml import feature_config as fc

INCIDENT_RATE = 0.10
PREP_OUTAGE_RATE = 0.006
RIDER_SHORTAGE_RATE = 0.005


def _choice(rng, options, probs):
    return rng.choice(options, p=np.asarray(probs, dtype=float) / np.sum(probs))


def _choice_rows(rng, options, prob_matrix):
    """Row-wise categorical sample from an (n, k) probability matrix."""
    p = prob_matrix / prob_matrix.sum(axis=1, keepdims=True)
    u = rng.random(len(p))[:, None]
    return np.asarray(options)[(u > p.cumsum(axis=1)).sum(axis=1).clip(0, len(options) - 1)]


def generate_orders(n: int = 6000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # -- when ----------------------------------------------------------------------------------
    comp = rng.choice(3, size=n, p=[0.30, 0.42, 0.28])
    hour = np.where(comp == 0, rng.normal(13.2, 1.0, n), np.where(comp == 1, rng.normal(20.4, 1.3, n), rng.uniform(9, 23.5, n)))
    hour = np.clip(hour, 9.0, 23.75)
    minutes = (hour * 60).astype(int)
    hh, mm = minutes // 60, minutes % 60
    order_time = [f"{h:02d}:{m:02d}" for h, m in zip(hh, mm)]
    hour_f = hh + mm / 60
    peak = np.zeros(n, dtype=bool)
    for lo, hi in fc.PEAK_WINDOWS:
        peak |= (hour_f >= lo) & (hour_f < hi)
    day_w = np.array([1, 1, 1, 1.05, 1.3, 1.45, 1.35])
    day = rng.choice(fc.DAYS, size=n, p=day_w / day_w.sum())
    weekend = np.isin(day, list(fc.WEEKEND_DAYS))

    # -- where / who ------------------------------------------------------------------------------
    area = rng.choice(fc.AREA_TYPES, size=n, p=[0.45, 0.30, 0.25])
    dist = rng.gamma(3.0, 1.15, n)
    dist = dist * np.where(area == "Suburban", 1.3, np.where(area == "Dense Urban", 0.8, 1.0))
    dist = np.round(np.clip(dist, 0.4, 18.0), 1)
    exp = rng.choice(fc.RIDER_EXPERIENCE, size=n, p=[0.20, 0.45, 0.35])
    batch = rng.random(n) < np.where(peak, 0.16, 0.09)
    items = np.clip(1 + rng.poisson(2.0, n) + (rng.random(n) < 0.03) * rng.integers(3, 8, n), 1, 16)
    value = np.round(items * rng.lognormal(np.log(165), 0.35, n) + rng.normal(30, 8, n), 0).clip(60)

    # -- conditions ---------------------------------------------------------------------------------
    load_p = np.where(peak[:, None], [[0.10, 0.32, 0.38, 0.20]], [[0.35, 0.40, 0.20, 0.05]]) + weekend[:, None] * np.array([[-0.05, 0, 0.03, 0.02]])
    load = _choice_rows(rng, fc.RESTAURANT_LOADS, np.clip(load_p, 0.01, None))
    traffic_p = np.where(peak[:, None], [[0.12, 0.36, 0.37, 0.15]], [[0.38, 0.40, 0.18, 0.04]])
    traffic_p = traffic_p + (area == "Dense Urban")[:, None] * np.array([[-0.08, -0.02, 0.06, 0.04]]) \
        + (area == "Suburban")[:, None] * np.array([[0.14, 0.04, -0.12, -0.06]])
    traffic = _choice_rows(rng, fc.TRAFFIC_LEVELS, np.clip(traffic_p, 0.01, None))
    weather = rng.choice(fc.WEATHER, size=n, p=[0.62, 0.16, 0.06, 0.11, 0.05])

    # -- stage durations ------------------------------------------------------------------------------
    load_score = np.vectorize(fc.LOAD_SCORE.get)(load)
    load_mult = np.vectorize({"Low": 0.85, "Moderate": 1.0, "High": 1.3, "Very High": 1.7}.get)(load)
    prep = (fc.normal_prep_minutes(items) * load_mult * rng.lognormal(0, 0.27, n) + batch * 1.5)
    out_prep = rng.random(n) < PREP_OUTAGE_RATE
    prep = np.where(out_prep, prep + rng.uniform(30, 55, n), prep)
    prep = np.round(np.clip(prep, 4, 110)).astype(int)

    assign_scale = 1.4 * np.where(peak, 1.5, 1.0) * np.where(weather == "Rain", 1.3, 1.0) \
        * np.where(area == "Suburban", 1.4, np.where(area == "Dense Urban", 1.1, 1.0)) * np.where(exp == "New", 1.0, 1.0)
    assign = rng.gamma(2.0, assign_scale)
    shortage = rng.random(n) < RIDER_SHORTAGE_RATE
    assign = np.where(shortage, assign + rng.uniform(20, 40, n), assign)
    assign = np.round(np.clip(assign, 1, 60)).astype(int)

    wait = 1.0 + rng.gamma(1.5, 1.6, n) * (1 + 0.5 * load_score / 3) + (exp == "New") * rng.uniform(0, 2, n)
    wait = np.round(np.clip(wait, 0, 40)).astype(int)

    area_mult = np.vectorize({"Urban": 1.0, "Dense Urban": 1.15, "Suburban": 0.92}.get)(area)
    exp_mult = np.vectorize({"New": 1.12, "Moderate": 1.0, "Experienced": 0.93}.get)(exp)
    t_mult = np.vectorize(fc.TRAFFIC_MULT.get)(traffic)
    w_mult = np.vectorize(fc.WEATHER_MULT.get)(weather)
    free_flow = dist / fc.FREE_FLOW_SPEED_KMPH * 60
    transit = free_flow * t_mult * w_mult * area_mult * exp_mult * rng.lognormal(0, 0.12, n) \
        + 3 + (area == "Dense Urban") * 2 + batch * 3.5
    incident = rng.random(n) < INCIDENT_RATE
    transit = transit + incident * rng.uniform(5, 22, n)

    actual = np.round(fc.ACCEPT_MIN + prep + assign + wait + transit).astype(int)
    # The quote starts from distance + basket size, then partly reflects live conditions (the platform sees some of the
    # traffic/weather picture and pads peak/busy kitchens); ~10% of quotes are generous (scheduled / wide delivery slots).
    seen_stretch = 0.45 * free_flow * (t_mult * w_mult - 1)
    pad = peak * rng.uniform(1, 4, n) + (load_score >= 2) * rng.uniform(0, 4, n)
    generous = (rng.random(n) < 0.10) * rng.integers(8, 26, n)
    quote = fc.baseline_quote(pd.Series(dist), pd.Series(items)).to_numpy() + seen_stretch + pad + generous + rng.integers(-4, 5, n)
    promised = np.round(np.maximum(fc.QUOTE_FLOOR_MIN, quote)).astype(int)

    df = pd.DataFrame({
        "order_id": [f"ORD-{1000 + i}" for i in range(n)],
        "order_time": order_time, "day_of_week": day, "num_items": items, "order_value": value.astype(int),
        "prep_time": prep, "restaurant_load": load, "rider_assignment_delay": assign, "pickup_wait": wait,
        "distance_km": dist, "traffic_level": traffic, "weather": weather, "area_type": area,
        "rider_experience": exp, "peak_hour": np.where(peak, "Yes", "No"),
        "actual_delivery_time": actual, "promised_eta": promised,
        "customer_zone": [f"Z{z}" for z in rng.integers(1, 9, n)], "restaurant_zone": [f"Z{z}" for z in rng.integers(1, 9, n)],
        "batch_delivery": np.where(batch, "Yes", "No"),
    })
    return df[fc.CSV_COLUMNS]


def delay_rate(df: pd.DataFrame) -> float:
    return float((df["actual_delivery_time"] > df["promised_eta"] + fc.DELAY_GRACE_MINUTES).mean())


def inject_issues(df: pd.DataFrame, seed: int = 11) -> pd.DataFrame:
    """Make a deliberately messy copy (for demonstrating validation and cleaning)."""
    rng = np.random.default_rng(seed)
    d = df.copy().astype(object)
    idx = rng.permutation(len(d))
    pos = iter(idx)
    d.loc[next(pos), "prep_time"] = -12                       # negative time
    d.loc[next(pos), "distance_km"] = 0                       # zero distance
    d.loc[next(pos), "distance_km"] = -3.5
    d.loc[next(pos), "order_value"] = -450                    # impossible value
    d.loc[next(pos), "order_time"] = "25:99"                  # malformed time
    d.loc[next(pos), "order_time"] = "yesterday evening"
    d.loc[next(pos), "traffic_level"] = "Gridlock"            # invalid category
    d.loc[next(pos), "weather"] = "Tornado"
    d.loc[next(pos), "prep_time"] = 900                       # implausible
    d.loc[next(pos), "num_items"] = "many"                    # non-numeric
    for _ in range(3):                                        # values that are only *missing*
        d.loc[next(pos), "pickup_wait"] = ""
    for _ in range(3):
        d.loc[next(pos), "rider_assignment_delay"] = ""
    d.loc[next(pos), "weather"] = ""
    d.loc[next(pos), "rider_experience"] = ""
    d.loc[next(pos), "prep_time"] = 75                        # extreme but plausible -> flagged, kept
    d.loc[next(pos), "distance_km"] = 24.5
    d.loc[next(pos), "traffic_level"] = "heavy"               # casing normalised
    d.loc[next(pos), "restaurant_load"] = "very high"
    dup_src = d.iloc[[next(pos), next(pos), next(pos)]]
    return pd.concat([d, dup_src], ignore_index=True)         # duplicate order ids


if __name__ == "__main__":
    sample = generate_orders(6000)
    print(f"delay rate {delay_rate(sample):.1%}")
