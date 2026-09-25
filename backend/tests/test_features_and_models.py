import numpy as np
import pandas as pd
import pytest

import bottleneck_detector as bd
import synthetic_data
from data_cleaner import clean_orders
from feature_engineering import distance_category, engineer_features, model_frame
from ml import feature_config as fc

from conftest import as_text


@pytest.fixture(scope="module")
def feats(raw_orders):
    return engineer_features(clean_orders(as_text(raw_orders)).df)


# ---- synthetic data ------------------------------------------------------------------------------------
def test_generator_is_deterministic_and_plausible():
    a, b = synthetic_data.generate_orders(500, 1), synthetic_data.generate_orders(500, 1)
    pd.testing.assert_frame_equal(a, b)
    assert 0.2 < synthetic_data.delay_rate(synthetic_data.generate_orders(4000, 2)) < 0.45


def test_generator_relationships_point_the_right_way():
    df = synthetic_data.generate_orders(6000, 3)
    m = lambda col, k: df[df[col] == k]["actual_delivery_time"].mean()
    assert m("traffic_level", "Severe") > m("traffic_level", "Low") + 4
    assert m("weather", "Rain") > m("weather", "Clear")
    assert df.groupby("restaurant_load")["prep_time"].mean().reindex(fc.RESTAURANT_LOADS).is_monotonic_increasing
    assert df[["distance_km", "actual_delivery_time"]].corr().iloc[0, 1] > 0.3
    # ...but never deterministic
    assert df[["distance_km", "actual_delivery_time"]].corr().iloc[0, 1] < 0.95


def test_messy_generator_output_is_cleaned():
    messy = synthetic_data.inject_issues(synthetic_data.generate_orders(200, 4))
    res = clean_orders(messy.astype(str))
    assert res.summary["rows_removed"] >= 10 and res.summary["duplicates_removed"] == 3 and res.summary["missing_values_fixed"] >= 6


# ---- features ---------------------------------------------------------------------------------------
def test_engineered_features_are_complete_and_finite(feats):
    for cols in (fc.CLASSIFIER_NUMERIC, fc.REGRESSOR_NUMERIC):
        block = feats[cols]
        assert list(block.columns) == cols and np.isfinite(block.to_numpy(dtype=float)).all()
    assert feats["peak_hour_score"].between(0, 1).all() and feats["operational_pressure"].between(0, 1).all()


def test_feature_formulas(feats):
    r = feats.iloc[0]
    assert r["pre_pickup_time"] == r["prep_time"] + r["rider_assignment_delay"] + r["pickup_wait"]
    assert r["distance_per_item"] == pytest.approx(r["distance_km"] / r["num_items"])
    assert r["assignment_delay_ratio"] + r["pickup_delay_ratio"] <= 1.0001
    assert r["transit_budget"] == pytest.approx(r["promised_eta"] - fc.ACCEPT_MIN - r["pre_pickup_time"])


def test_regressor_features_never_see_the_promise_or_target(feats):
    reg = set(model_frame(feats, "regressor").columns)
    assert not reg & {"promised_eta", "transit_budget", "actual_delivery_time", "delayed"}
    assert "actual_delivery_time" not in set(model_frame(feats, "classifier").columns)


def test_distance_categories():
    assert list(distance_category(pd.Series([0.5, 2.0, 6.9, 12.0]))) == ["0-2 km", "2-5 km", "5-8 km", "8+ km"]


# ---- trained models ---------------------------------------------------------------------------------------
def test_reported_metrics_are_credible(service):
    m = service.metrics
    c, r = m["classifier"]["metrics"], m["regressor"]["metrics"]
    assert 0.75 < c["accuracy"] < 0.985 and 0.85 < c["roc_auc"] < 0.995      # good, but not "too good to be true"
    assert 0.3 < r["r2"] < 0.97 and 1.0 < r["mae"] < r["rmse"]
    assert m["dataset"]["train_rows"] + m["dataset"]["test_rows"] == m["dataset"]["rows_total"]
    assert set(m["classifier"]["confusion_matrix"]) == {"tn", "fp", "fn", "tp"}
    assert any(b["model"].startswith("Baseline") for b in m["regressor"]["comparison"])


def test_predictions_are_well_formed(service, feats):
    d, e = service.delay.predict(feats), service.eta.predict(feats)
    assert d["delay_probability"].between(0, 1).all() and set(d["status"]) <= {"ON TIME", "AT RISK", "DELAY LIKELY"}
    assert (e["eta_low"] <= e["eta_minutes"]).all() and (e["eta_minutes"] <= e["eta_high"]).all()
    assert set(e["eta_confidence"]) <= {"High", "Medium", "Low"}


def _order(**over) -> pd.DataFrame:
    base = dict(order_id="T", order_time="14:00", day_of_week="Tuesday", num_items=3, order_value=500, prep_time=13,
                restaurant_load="Moderate", rider_assignment_delay=3, pickup_wait=3, distance_km=3, traffic_level="Low",
                weather="Clear", area_type="Urban", rider_experience="Moderate", peak_hour="No", promised_eta=34)
    base.update(over)
    return pd.DataFrame([base]).astype(str)


def test_model_responds_sensibly_to_conditions(service):
    easy = service.analyze_order({**_order().iloc[0].to_dict()})
    hard = service.analyze_order({**_order(traffic_level="Severe", weather="Rain", prep_time=40, rider_assignment_delay=20,
                                            distance_km=9, restaurant_load="Very High").iloc[0].to_dict()})
    assert hard["delay_probability"] > easy["delay_probability"] + 0.3
    assert hard["eta"]["minutes"] > easy["eta"]["minutes"] + 15
    assert easy["status"] == "ON TIME" and hard["status"] == "DELAY LIKELY"


# ---- bottleneck detector ---------------------------------------------------------------------------------
def _detect(service, **over):
    cleaned = clean_orders(_order(**over)).df
    eta = service.eta.predict_minutes(engineer_features(cleaned))
    return bd.detect(cleaned, service.eta, eta, detailed=True).iloc[0]


def test_normal_order_has_no_major_bottleneck(service):
    assert _detect(service)["primary_bottleneck"] == bd.NO_BOTTLENECK


@pytest.mark.parametrize("over,expected", [
    ({"prep_time": 45}, "Restaurant Preparation"), ({"rider_assignment_delay": 25}, "Rider Assignment"),
    ({"pickup_wait": 20}, "Pickup Waiting"), ({"traffic_level": "Severe", "distance_km": 8}, "Transit / Traffic"),
    ({"weather": "Rain", "distance_km": 10}, "Weather"), ({"prep_time": 45, "restaurant_load": "Very High"}, "Restaurant Overload"),
])
def test_dominant_stage_is_named(service, over, expected):
    r = _detect(service, **over)
    assert r["primary_bottleneck"] == expected or expected in [c["name"] for c in r["contributions"][:2]]
    assert r["primary_pct"] > 0


def test_contributions_are_shares(service):
    r = _detect(service, prep_time=40, rider_assignment_delay=15, traffic_level="Heavy")
    assert sum(c["pct"] for c in r["contributions"]) <= 100.5
    assert r["primary_pct"] >= r["secondary_pct"] > 0
    assert r["secondary_bottleneck"] != r["primary_bottleneck"]
