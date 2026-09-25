"""Small shared helpers: JSON-safe records, timeline construction and the plain-language summary."""
from __future__ import annotations

import json

import pandas as pd

import config  # noqa: F401
from ml import feature_config as fc
from bottleneck_detector import FACTOR_STAGE, NO_BOTTLENECK, rule_minutes


def records(df: pd.DataFrame) -> list[dict]:
    """NaN -> null, numpy scalars -> python."""
    return json.loads(df.to_json(orient="records"))


def delay_rule_text() -> str:
    return f"Delayed if actual delivery time > promised ETA + {fc.DELAY_GRACE_MINUTES:g} min"


def build_timeline(cleaned_row: pd.DataFrame, eta_minutes: float, primary: str, secondary: str | None) -> tuple[list[dict], float]:
    """Seven-stage pipeline. Pre-pickup stages are the order's own numbers; transit is what the ETA model leaves over."""
    r = cleaned_row.iloc[0]
    excess = rule_minutes(cleaned_row).iloc[0]
    pre = fc.ACCEPT_MIN + r["prep_time"] + r["rider_assignment_delay"] + r["pickup_wait"]
    transit = max(3.0, eta_minutes - pre)
    stage_of = {p: FACTOR_STAGE.get(p) for p in (primary, secondary) if p and p != NO_BOTTLENECK}
    flags = {}
    for name, stage in stage_of.items():
        flags.setdefault(stage, "primary" if name == primary else "secondary")
    stage_excess = {
        "preparing": float(excess["Restaurant Preparation"] + excess["Restaurant Overload"] + excess["High Order Complexity"]),
        "assignment": float(excess["Rider Assignment"]), "pickup": float(excess["Pickup Waiting"]),
        "transit": float(excess["Transit / Traffic"] + excess["Weather"]),
    }
    spec = [
        ("placed", "Order Placed", 0.0), ("accepted", "Restaurant Accepted", fc.ACCEPT_MIN),
        ("preparing", "Preparing", float(r["prep_time"])), ("assignment", "Rider Assigned", float(r["rider_assignment_delay"])),
        ("pickup", "Pickup", float(r["pickup_wait"])), ("transit", "In Transit", float(transit)), ("delivered", "Delivered", 0.0),
    ]
    stages, clock = [], 0.0
    for key, label, minutes in spec:
        clock += minutes
        stages.append({"key": key, "label": label, "minutes": round(minutes, 1), "cumulative": round(clock, 1),
                       "flag": flags.get(key), "excess_minutes": round(stage_excess.get(key, 0.0), 1)})
    return stages, round(clock, 1)


def summary_text(o: dict) -> str:
    eta = o["eta"]
    parts = [
        f"Order {o['order_id']} is flagged {o['status']}: the model puts the chance of a delay at "
        f"{o['delay_probability'] * 100:.0f}% ({o['delay_confidence'].lower()} confidence) and estimates delivery in "
        f"{eta['minutes']:.0f} min (likely {eta['low']:.0f}-{eta['high']:.0f}) against a promised {o['promised_eta']:.0f} min"
        f"{' (baseline quote, none supplied)' if o['promised_eta_estimated'] else ''}."
    ]
    b = o["bottleneck"]
    if b["primary"]["name"] == NO_BOTTLENECK:
        parts.append("No single stage stands out as a bottleneck for this order.")
    else:
        line = (f"Likely contributing factor: {b['primary']['name']} ({b['primary']['contribution_pct']:.0f}% of the excess minutes "
                f"identified across stages)")
        if b["secondary"]:
            line += f", followed by {b['secondary']['name']} ({b['secondary']['contribution_pct']:.0f}%)"
        parts.append(line + ".")
    parts.append("Factors are likely contributors, not proven causes.")
    return " ".join(parts)
