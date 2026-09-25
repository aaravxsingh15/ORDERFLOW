import pandas as pd
import pytest

from data_cleaner import ValidationError, clean_orders, read_csv_bytes
from ml import feature_config as fc

from conftest import as_text


def _row(**over) -> dict:
    base = dict(order_id="A1", order_time="19:30", day_of_week="Friday", num_items="3", order_value="450", prep_time="15",
                restaurant_load="Moderate", rider_assignment_delay="3", pickup_wait="3", distance_km="4", traffic_level="Heavy",
                weather="Clear", area_type="Urban", rider_experience="Moderate", actual_delivery_time="40", promised_eta="34")
    base.update({k: str(v) for k, v in over.items()})
    return base


def _clean(*rows: dict):
    return clean_orders(pd.DataFrame(rows))


def test_clean_synthetic_data_passes_untouched(raw_orders):
    res = clean_orders(as_text(raw_orders))
    assert res.summary["rows_removed"] == 0 and res.summary["rows_valid"] == len(raw_orders)
    assert res.summary["missing_values_fixed"] == 0
    assert res.df["order_id"].is_unique


def test_empty_inputs_have_readable_errors():
    with pytest.raises(ValidationError, match="empty"):
        read_csv_bytes(b"")
    with pytest.raises(ValidationError, match="no data rows"):
        read_csv_bytes(b"order_id,order_time\n")
    with pytest.raises(ValidationError, match="no data rows"):
        clean_orders(pd.DataFrame(columns=["order_id"]))


def test_missing_required_columns_are_named():
    with pytest.raises(ValidationError) as e:
        clean_orders(pd.DataFrame([{"order_id": "A", "order_time": "10:00"}]))
    assert "distance_km" in e.value.message and "prep_time" in e.value.message


@pytest.mark.parametrize("over,code", [
    ({"prep_time": -5}, "negative_value"), ({"rider_assignment_delay": -1}, "negative_value"),
    ({"pickup_wait": -2}, "negative_value"), ({"distance_km": 0}, "invalid_distance"), ({"distance_km": -2}, "invalid_distance"),
    ({"order_value": -100}, "invalid_value"), ({"order_value": 0}, "invalid_value"), ({"num_items": 0}, "invalid_value"),
    ({"num_items": 2.5}, "invalid_value"), ({"traffic_level": "Gridlock"}, "invalid_category"), ({"weather": "Tornado"}, "invalid_category"),
    ({"order_time": "25:99"}, "malformed_time"), ({"order_time": "later tonight"}, "malformed_time"),
    ({"prep_time": 999}, "implausible"), ({"distance_km": "far"}, "not_numeric"), ({"day_of_week": "Funday"}, "invalid_category"),
])
def test_bad_rows_are_removed_with_a_reason(over, code):
    res = _clean(_row(), _row(order_id="B2", **over))
    assert res.summary["rows_removed"] == 1 and list(res.df["order_id"]) == ["A1"]
    assert any(i["code"] == code and i["order_id"] == "B2" for i in res.issues)
    assert all(i["reason"] for i in res.issues)


def test_all_invalid_raises_with_issue_list():
    with pytest.raises(ValidationError) as e:
        _clean(_row(distance_km=0), _row(order_id="B", prep_time=-1))
    assert len(e.value.issues) == 2 and e.value.summary["rows_removed"] == 2


def test_duplicate_order_ids_keep_first():
    res = _clean(_row(prep_time=10), _row(prep_time=99), _row(order_id="a1"))
    assert len(res.df) == 1 and res.df.loc[0, "prep_time"] == 10
    assert res.summary["duplicates_removed"] == 2


def test_missing_values_are_imputed_and_counted():
    res = _clean(_row(), _row(order_id="B", pickup_wait="", weather="", rider_assignment_delay="N/A"), _row(order_id="C", pickup_wait=7))
    assert res.summary["missing_values_fixed"] == 3 and res.summary["rows_removed"] == 0
    b = res.df.set_index("order_id").loc["B"]
    assert b["pickup_wait"] == 5 and b["weather"] == "Clear"        # median of 3 and 7 / only category present
    assert b["rider_assignment_delay"] == 3


def test_required_numeric_missing_is_not_guessed():
    res = _clean(_row(), _row(order_id="B", prep_time=""))
    assert res.summary["rows_removed"] == 1


def test_normalisation_of_types_and_categories():
    res = _clean(_row(order_id=" x9 ", traffic_level="heavy", restaurant_load="very high", day_of_week="fri", order_value="Rs. 1,240",
                      prep_time="24 min", distance_km="7.2 km", order_time="8:15 PM", peak_hour="yes"))
    r = res.df.iloc[0]
    assert r["order_id"] == "x9" and r["traffic_level"] == "Heavy" and r["restaurant_load"] == "Very High"
    assert r["day_of_week"] == "Friday" and r["order_value"] == 1240 and r["prep_time"] == 24 and r["distance_km"] == 7.2
    assert r["order_time"] == "20:15" and r["peak_hour"] == 1 and r["weekend"] == 0


def test_full_datetime_supplies_day_and_hour():
    res = clean_orders(pd.DataFrame([{k: v for k, v in _row(order_time="2026-03-07 21:05:00").items() if k != "day_of_week"}]))
    r = res.df.iloc[0]
    assert r["day_of_week"] == "Saturday" and r["weekend"] == 1 and r["order_time"] == "21:05" and r["peak_hour"] == 1


def test_peak_hour_derived_when_absent():
    res = _clean(_row(order_time="13:00"), _row(order_id="B", order_time="16:00"))
    assert list(res.df["peak_hour"]) == [1, 0]


def test_outliers_flagged_and_clipped_not_removed():
    res = _clean(_row(), _row(order_id="B", prep_time=75), _row(order_id="C", distance_km=24))
    assert res.summary["outliers_flagged"] == 2 and len(res.df) == 3
    assert res.df.set_index("order_id").loc["B", "outlier_fields"] == "prep_time"


def test_delay_label_uses_configured_grace():
    res = _clean(_row(actual_delivery_time=39, promised_eta=34), _row(order_id="B", actual_delivery_time=40, promised_eta=34))
    assert list(res.df["delayed"]) == [0.0, 1.0]         # 39 = 34 + 5 is on time; 40 is late
    assert fc.DELAY_GRACE_MINUTES == 5


def test_missing_promise_uses_baseline_quote_and_no_label():
    res = clean_orders(pd.DataFrame([{k: v for k, v in _row().items() if k not in ("promised_eta",)}]))
    r = res.df.iloc[0]
    assert r["promised_eta_estimated"] and r["promised_eta"] == fc.baseline_quote(4.0, 3) and pd.isna(r["delayed"])
    assert res.summary["promised_eta_estimated"] == 1 and res.warnings
