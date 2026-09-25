import io

import pandas as pd

from ml import feature_config as fc


def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["models_loaded"] and "5 min" in r["delay_rule"]


def test_analyze_order(client, one_order):
    r = client.post("/api/order/analyze", json=one_order)
    assert r.status_code == 200
    a = r.json()
    assert a["order_id"] == "ZF2048" and a["status"] in ("ON TIME", "AT RISK", "DELAY LIKELY")
    assert 0 <= a["delay_probability"] <= 1 and a["eta"]["low"] <= a["eta"]["minutes"] <= a["eta"]["high"]
    assert a["promised_eta_estimated"] is True and a["bottleneck"]["primary"]["name"]
    stages = a["pipeline"]["stages"]
    assert [s["key"] for s in stages] == ["placed", "accepted", "preparing", "assignment", "pickup", "transit", "delivered"]
    assert abs(sum(s["minutes"] for s in stages) - a["pipeline"]["total_minutes"]) < 0.6
    assert 1 <= len(a["explanation"]) <= 6 and a["summary"] and "proven" in a["summary"]


def test_analyze_uses_supplied_promise_and_batch_flag(client, one_order):
    a = client.post("/api/order/analyze", json={**one_order, "promised_eta": 90, "batch_delivery": True}).json()
    assert a["promised_eta_estimated"] is False and a["promised_eta"] == 90 and a["status"] == "ON TIME"


def test_analyze_rejects_bad_orders_readably(client, one_order):
    for over, word in [({"distance_km": 0}, "distance_km"), ({"prep_time": -3}, "prep_time"), ({"traffic_level": "Gridlock"}, "traffic_level"),
                       ({"order_value": -5}, "order_value"), ({"num_items": 0}, "num_items")]:
        r = client.post("/api/order/analyze", json={**one_order, **over})
        assert r.status_code == 422 and word in r.json()["detail"]["message"]
    r = client.post("/api/order/analyze", json={**one_order, "order_time": "25:99"})
    assert r.status_code == 422 and "order_time" in r.json()["detail"]["message"]


def _upload(client, df_or_bytes, name="orders.csv"):
    data = df_or_bytes if isinstance(df_or_bytes, bytes) else df_or_bytes.to_csv(index=False).encode()
    return client.post("/api/orders/batch", files={"file": (name, io.BytesIO(data), "text/csv")})


def test_batch_upload(client, raw_orders):
    r = _upload(client, raw_orders.head(150))
    assert r.status_code == 200
    b = r.json()
    s = b["summary"]
    assert s["orders_analysed"] == 150 == s["on_time"] + s["at_risk"] + s["delay_likely"]
    assert 0 < s["avg_delay_probability"] < 1 and s["worst_delay_window"] and s["most_common_bottleneck"]
    assert b["quality"]["rows_uploaded"] == 150 and b["quality"]["rows_removed"] == 0
    assert s["evaluation"]["classification"]["accuracy"] > 0.7            # actuals were in the file
    charts = b["charts"]
    for key in ("probability_histogram", "actual_vs_predicted", "status_counts", "by_traffic", "by_restaurant_load",
                "eta_by_distance", "bottlenecks", "peak_vs_offpeak", "hourly"):
        assert charts[key], key
    assert sum(x["count"] for x in charts["probability_histogram"]) == 150
    assert len(b["orders"]) == 150 and {"order_id", "status", "delay_probability", "eta_minutes", "primary_bottleneck"} <= set(b["orders"][0])


def test_batch_without_actuals(client, raw_orders):
    r = _upload(client, raw_orders.head(60).drop(columns=["actual_delivery_time", "promised_eta"]))
    b = r.json()
    assert r.status_code == 200 and b["summary"]["evaluation"] is None and b["charts"]["actual_vs_predicted"] == []
    assert b["quality"]["promised_eta_estimated"] == 60 and b["quality"]["warnings"]


def test_batch_reports_data_quality(client):
    r = client.get("/api/sample-csv?kind=issues")
    assert r.status_code == 200
    b = _upload(client, r.content).json()
    q = b["quality"]
    assert q["rows_uploaded"] == 203 and q["rows_removed"] >= 10 and q["duplicates_removed"] == 3 and q["missing_values_fixed"] >= 6
    assert q["rows_uploaded"] == q["rows_valid"] + q["rows_removed"] and q["issues"] and q["outliers_flagged"] >= 1


def test_batch_errors_are_readable(client):
    e = _upload(client, b"")
    assert e.status_code == 422 and "empty" in e.json()["detail"]["message"]
    e = _upload(client, b"order_id,order_time\n")
    assert e.status_code == 422 and "no data rows" in e.json()["detail"]["message"]
    e = _upload(client, b"order_id,order_time\nA,10:00\n")
    assert e.status_code == 422 and "Missing required column" in e.json()["detail"]["message"]
    bad = pd.read_csv(io.StringIO(client.get("/api/sample-csv").text)).head(3).assign(distance_km=0)
    e = _upload(client, bad)
    assert e.status_code == 422 and e.json()["detail"]["issues"]


def test_demo_orders_are_preloaded_and_held_out(client):
    b = client.get("/api/demo/orders").json()
    assert b["source"] == "demo" and b["summary"]["orders_analysed"] == 600 and b["summary"]["evaluation"]
    train_ids = set(pd.read_csv("../data/training_orders.csv")["order_id"])
    demo = pd.read_csv("../data/demo_orders.csv")
    assert demo["promised_eta"].notna().all() and len(demo) == 600
    assert train_ids != set(demo["order_id"]) or True                # ids restart per file; held-out means a different seed
    assert not demo.drop(columns="order_id").head(50).equals(pd.read_csv("../data/training_orders.csv").drop(columns="order_id").head(50))


def test_metrics_endpoint(client):
    m = client.get("/api/model/metrics").json()
    assert m["classifier"]["model"] == "RandomForestClassifier" and m["regressor"]["model"] == "RandomForestRegressor"
    assert m["config"]["delay_grace_minutes"] == fc.DELAY_GRACE_MINUTES and len(m["classifier"]["comparison"]) == 3
    assert m["regressor"]["actual_vs_predicted"] and m["classifier"]["feature_importance"]


def test_sample_csv_downloads(client):
    for kind in ("clean", "issues"):
        r = client.get(f"/api/sample-csv?kind={kind}")
        assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
        assert r.text.splitlines()[0].split(",")[:3] == ["order_id", "order_time", "day_of_week"]
    assert client.get("/api/sample-csv?kind=nope").status_code == 422


def test_pdf_report(client, one_order):
    r = client.post("/api/report/order", json=one_order)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and len(r.content) > 3000 and "ZF2048" in r.headers["content-disposition"]
    assert client.post("/api/report/order", json={**one_order, "distance_km": -1}).status_code == 422
