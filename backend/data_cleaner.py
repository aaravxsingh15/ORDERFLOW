"""Validation + cleaning: raw CSV / form data -> typed, model-ready orders and a data-quality summary."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config  # noqa: F401  (puts repo root on sys.path)
from ml import feature_config as fc

NUMERIC_RE = re.compile(r"^\s*(?:₹|rs\.?|inr)?\s*(-?\d+(?:\.\d+)?)\s*(?:mins?|minutes?|kms?)?\s*$", re.I)
TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([ap]m)?\s*$", re.I)
NULL_TOKENS = {"", "nan", "none", "null", "na", "n/a", "-", "--"}
CLIP_LIMITS = {k: v * 1.5 for k, v in fc.SOFT_LIMITS.items() if k != "actual_delivery_time"}

COLUMN_ALIASES = {
    "id": "order_id", "orderid": "order_id", "time": "order_time", "day": "day_of_week", "dayofweek": "day_of_week",
    "items": "num_items", "n_items": "num_items", "number_of_items": "num_items", "value": "order_value",
    "prep": "prep_time", "preparation_time": "prep_time", "restaurant_preparation_time": "prep_time",
    "load": "restaurant_load", "assignment_delay": "rider_assignment_delay", "assign_delay": "rider_assignment_delay",
    "pickup_waiting_time": "pickup_wait", "wait": "pickup_wait", "distance": "distance_km", "traffic": "traffic_level",
    "weather_condition": "weather", "area": "area_type", "experience": "rider_experience", "peak": "peak_hour",
    "weekend_indicator": "weekend", "is_weekend": "weekend", "delivery_time": "actual_delivery_time",
    "actual_time": "actual_delivery_time", "eta": "promised_eta", "promised_time": "promised_eta",
    "batch": "batch_delivery", "multi_order": "batch_delivery", "batch_flag": "batch_delivery",
}
LEVEL_SYNONYMS = {
    "traffic_level": {"low": "Low", "light": "Low", "moderate": "Moderate", "medium": "Moderate", "med": "Moderate",
                      "heavy": "Heavy", "high": "Heavy", "severe": "Severe", "jam": "Severe", "gridlock": None},
    "restaurant_load": {"low": "Low", "moderate": "Moderate", "medium": "Moderate", "med": "Moderate",
                        "high": "High", "very high": "Very High", "very_high": "Very High", "veryhigh": "Very High",
                        "extreme": "Very High"},
    "weather": {"clear": "Clear", "sunny": "Clear", "rain": "Rain", "rainy": "Rain", "fog": "Fog", "foggy": "Fog",
                "hot": "Hot", "cold": "Cold"},
    "area_type": {"urban": "Urban", "dense urban": "Dense Urban", "dense_urban": "Dense Urban", "dense": "Dense Urban",
                  "suburban": "Suburban", "suburb": "Suburban"},
    "rider_experience": {"new": "New", "novice": "New", "low": "New", "moderate": "Moderate", "medium": "Moderate",
                         "experienced": "Experienced", "expert": "Experienced", "high": "Experienced", "veteran": "Experienced"},
}
IMPUTE_DEFAULTS = {"traffic_level": "Moderate", "restaurant_load": "Moderate", "weather": "Clear",
                   "area_type": "Urban", "rider_experience": "Moderate"}
BOOL_TRUE = {"yes", "y", "true", "t", "1", "1.0", "peak"}
BOOL_FALSE = {"no", "n", "false", "f", "0", "0.0", "off-peak", "offpeak", "off peak"}
DAY_LOOKUP = {d[:3].lower(): d for d in fc.DAYS}


class ValidationError(Exception):
    """Raised when an upload cannot be processed at all; carries readable details for the API."""

    def __init__(self, message: str, issues: list[dict] | None = None, summary: dict | None = None):
        super().__init__(message)
        self.message = message
        self.issues = issues or []
        self.summary = summary


@dataclass
class CleaningResult:
    df: pd.DataFrame
    summary: dict
    issues: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Decode an upload into an all-string frame; raises ValidationError for empty/unreadable files."""
    if not data or not data.strip():
        raise ValidationError("The uploaded file is empty.")
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None or not text.strip():
        raise ValidationError("The file could not be decoded as text. Please upload a UTF-8 CSV.")
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, skipinitialspace=True)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValidationError(f"The file is not a valid CSV: {exc}") from exc
    if df.empty:
        raise ValidationError("The CSV has a header but no data rows.")
    return df


def _norm_col(name: str) -> str:
    n = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")
    return COLUMN_ALIASES.get(n, n)


def _clean_str(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    return s.mask(s.str.lower().isin(NULL_TOKENS))


def _parse_number(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Returns (values, present_but_malformed_mask)."""
    raw = _clean_str(s).str.replace(",", "", regex=False)
    vals = pd.to_numeric(raw.str.extract(NUMERIC_RE)[0], errors="coerce")
    return vals.astype(float), raw.notna() & vals.isna()


def _parse_time(value: str | None) -> tuple[float, str, pd.Timestamp | None] | None:
    """-> (decimal_hour, 'HH:MM', date_or_None) or None when malformed."""
    if value is None or pd.isna(value):
        return None
    m = TIME_RE.match(str(value))
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(4)
        if ap:
            if not 1 <= h <= 12:
                return None
            h = h % 12 + (12 if ap.lower() == "pm" else 0)
        if not (0 <= h <= 23 and 0 <= mi <= 59):
            return None
        return h + mi / 60, f"{h:02d}:{mi:02d}", None
    try:
        ts = pd.to_datetime(str(value), errors="coerce")
    except (ValueError, OverflowError):
        return None
    if pd.isna(ts):
        return None
    return ts.hour + ts.minute / 60, f"{ts.hour:02d}:{ts.minute:02d}", ts.normalize()


def _parse_bool(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    low = _clean_str(s).str.lower()
    out = pd.Series(np.nan, index=s.index, dtype=float)
    out[low.isin(BOOL_TRUE)] = 1.0
    out[low.isin(BOOL_FALSE)] = 0.0
    return out, low.notna() & out.isna()


def is_peak(hour: pd.Series) -> pd.Series:
    mask = pd.Series(False, index=hour.index)
    for lo, hi in fc.PEAK_WINDOWS:
        mask |= (hour >= lo) & (hour < hi)
    return mask.astype(int)


def clean_orders(raw: pd.DataFrame) -> CleaningResult:
    if raw is None or len(raw) == 0:
        raise ValidationError("The uploaded file contains no data rows.")
    if len(raw) > config.MAX_UPLOAD_ROWS:
        raise ValidationError(f"Too many rows ({len(raw):,}). The limit is {config.MAX_UPLOAD_ROWS:,} rows per upload.")

    df = raw.copy()
    df.columns = [_norm_col(c) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()].reset_index(drop=True)
    n = len(df)
    source_row = np.arange(n) + 2  # 1-based CSV row incl. header

    missing = [c for c in fc.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValidationError(
            "Missing required column(s): " + ", ".join(missing) + ". Expected columns: " + ", ".join(fc.CSV_COLUMNS[:17]) + ".")

    reasons: list[list[tuple[str, str]]] = [[] for _ in range(n)]
    fixed = 0
    warnings: list[str] = []

    def flag(mask: pd.Series | np.ndarray, code: str, msg) -> None:
        mask = np.asarray(mask, dtype=bool)
        for i in np.flatnonzero(mask):
            reasons[i].append((code, msg(i) if callable(msg) else msg))

    out = pd.DataFrame(index=df.index)
    out["order_id"] = _clean_str(df["order_id"])
    flag(out["order_id"].isna(), "missing_field", "order_id is empty")

    # ---- timestamps --------------------------------------------------------------------------
    times = _clean_str(df["order_time"])
    parsed = [_parse_time(v) for v in times]
    out["order_hour"] = [p[0] if p else np.nan for p in parsed]
    out["order_time"] = [p[1] if p else None for p in parsed]
    dates = pd.to_datetime(pd.Series([p[2] if p else pd.NaT for p in parsed], index=df.index), errors="coerce")
    flag(times.isna(), "missing_field", "order_time is empty")
    flag(times.notna() & out["order_hour"].isna(), "malformed_time",
         lambda i: f"malformed order_time '{times.iloc[i]}' (use HH:MM or a full date-time)")

    # ---- day of week / weekend ----------------------------------------------------------------
    has_day_col = "day_of_week" in df.columns
    if not has_day_col and dates.isna().all():
        raise ValidationError("Missing required column(s): day_of_week (or supply a full date in order_time).")
    day_raw = _clean_str(df["day_of_week"]) if has_day_col else pd.Series(pd.NA, index=df.index, dtype="string")
    day = day_raw.str.lower().str[:3].map(DAY_LOOKUP)
    flag(day_raw.notna() & day.isna(), "invalid_category",
         lambda i: f"invalid day_of_week '{day_raw.iloc[i]}'")
    derived = dates.dt.day_name()
    blank = day_raw.isna()
    day = day.mask(blank, derived)
    still_blank = blank & day.isna()
    if still_blank.any():
        known = day.dropna()
        if known.empty:
            raise ValidationError("No usable day_of_week values were found.")
        day = day.fillna(known.mode().iloc[0])
        fixed += int(still_blank.sum())
    out["day_of_week"] = day
    out["weekend"] = day.isin(fc.WEEKEND_DAYS).astype(int)
    if "weekend" in df.columns:
        given, _ = _parse_bool(df["weekend"])
        mismatch = int((given.notna() & (given != out["weekend"])).sum())
        if mismatch:
            warnings.append(f"{mismatch} row(s) had a weekend flag that contradicted day_of_week; day_of_week was used.")

    # ---- numerics -----------------------------------------------------------------------------
    numeric_specs = {  # column -> (imputable when blank)
        "num_items": False, "order_value": True, "prep_time": False,
        "rider_assignment_delay": True, "pickup_wait": True, "distance_km": False,
    }
    for col, imputable in numeric_specs.items():
        vals, malformed = _parse_number(df[col])
        blank = vals.isna() & ~malformed
        flag(malformed, "not_numeric", lambda i, c=col: f"{c} is not a number ('{df[c].iloc[i]}')")
        if imputable:
            if blank.any() and vals.notna().any():
                vals = vals.fillna(float(vals.median()))
                fixed += int(blank.sum())
            elif blank.any():
                flag(blank, "missing_field", f"{col} is empty")
        else:
            flag(blank, "missing_field", f"{col} is empty")
        out[col] = vals

    for col in ("prep_time", "rider_assignment_delay", "pickup_wait"):
        flag(out[col] < 0, "negative_value", lambda i, c=col: f"negative {c} ({out[c].iloc[i]:g})")
    flag(out["distance_km"] <= 0, "invalid_distance", lambda i: f"distance_km must be greater than zero ({out['distance_km'].iloc[i]:g})")
    flag(out["order_value"] <= 0, "invalid_value", lambda i: f"order_value must be positive ({out['order_value'].iloc[i]:g})")
    flag(out["num_items"] < 1, "invalid_value", lambda i: f"num_items must be at least 1 ({out['num_items'].iloc[i]:g})")
    flag(out["num_items"].notna() & (out["num_items"] % 1 != 0), "invalid_value", "num_items must be a whole number")
    for col, lim in fc.IMPOSSIBLE_LIMITS.items():
        if col in out.columns:
            flag(out[col] > lim, "implausible", lambda i, c=col, l=lim: f"{c} of {out[c].iloc[i]:g} is implausible (limit {l})")

    # ---- categoricals -------------------------------------------------------------------------
    for col, synonyms in LEVEL_SYNONYMS.items():
        raw_col = _clean_str(df[col])
        canon = raw_col.str.lower().map(synonyms)
        bad = raw_col.notna() & canon.isna()
        flag(bad, "invalid_category",
             lambda i, c=col: f"invalid {c} '{raw_col.iloc[i]}' (expected one of: {', '.join(fc.CATEGORIES[c])})")
        blank = raw_col.isna()
        if blank.any():
            good = canon.dropna()
            fill = good.mode().iloc[0] if len(good) else IMPUTE_DEFAULTS[col]
            canon = canon.mask(blank, fill)
            fixed += int(blank.sum())
        out[col] = canon

    # ---- flags --------------------------------------------------------------------------------
    if "peak_hour" in df.columns:
        peak, bad = _parse_bool(df["peak_hour"])
        flag(bad, "invalid_category", lambda i: f"invalid peak_hour '{df['peak_hour'].iloc[i]}' (use Yes/No)")
        derived_peak = is_peak(out["order_hour"].fillna(0))
        blank = peak.isna() & ~bad
        peak = peak.fillna(derived_peak)
        fixed += int(blank.sum())
        out["peak_hour"] = peak.astype(int)
    else:
        out["peak_hour"] = is_peak(out["order_hour"].fillna(0))
    if "batch_delivery" in df.columns:
        batch, bad = _parse_bool(df["batch_delivery"])
        flag(bad, "invalid_category", lambda i: f"invalid batch_delivery '{df['batch_delivery'].iloc[i]}' (use Yes/No)")
        out["batch_delivery"] = batch.fillna(0).astype(int)
    else:
        out["batch_delivery"] = 0

    # ---- promised ETA / actual delivery time (optional) -----------------------------------------
    for col in ("promised_eta", "actual_delivery_time"):
        if col in df.columns:
            vals, malformed = _parse_number(df[col])
            flag(malformed, "not_numeric", lambda i, c=col: f"{c} is not a number ('{df[c].iloc[i]}')")
            flag(vals <= 0, "negative_value", lambda i, c=col: f"{c} must be positive ({vals.iloc[i]:g})")
            out[col] = vals
        else:
            out[col] = np.nan
    for col in ("customer_zone", "restaurant_zone"):
        out[col] = _clean_str(df[col]).fillna("") if col in df.columns else ""

    # ---- duplicates (only among rows still valid) -----------------------------------------------
    invalid_so_far = np.array([bool(r) for r in reasons])
    key = out["order_id"].str.lower()
    dup = key.duplicated(keep="first") & key.notna() & ~invalid_so_far
    first_row = {k: source_row[i] for i, k in reversed(list(enumerate(key))) if isinstance(k, str)}
    flag(dup, "duplicate_id", lambda i: f"duplicate order_id '{out['order_id'].iloc[i]}' (first seen on row {first_row[key.iloc[i]]})")

    # ---- assemble issues + drop invalid rows ----------------------------------------------------
    issues = [{"row": int(source_row[i]), "order_id": None if pd.isna(out["order_id"].iloc[i]) else str(out["order_id"].iloc[i]),
               "code": code, "reason": msg} for i, rs in enumerate(reasons) for code, msg in rs]
    invalid = np.array([bool(r) for r in reasons])
    valid = out[~invalid].copy()
    valid.insert(0, "source_row", source_row[~invalid])
    counts: dict[str, int] = {}
    for it in issues:
        counts[it["code"]] = counts.get(it["code"], 0) + 1
    summary = {
        "rows_uploaded": int(n), "rows_valid": int(len(valid)), "rows_removed": int(invalid.sum()),
        "missing_values_fixed": int(fixed), "outliers_flagged": 0,
        "duplicates_removed": int(dup.sum()), "issue_counts": counts,
        "promised_eta_estimated": 0, "has_actuals": False,
    }
    if valid.empty:
        first = issues[0]
        raise ValidationError(f"None of the {n} uploaded row(s) passed validation. First problem (row {first['row']}): {first['reason']}.",
                              issues[:100], summary)

    # ---- outliers: flag (IQR fence / soft limits), clip to sane caps ------------------------------
    flags = pd.Series("", index=valid.index)
    for col in ("prep_time", "rider_assignment_delay", "pickup_wait", "distance_km", "order_value", "num_items"):
        soft = valid[col] > fc.SOFT_LIMITS[col]
        if len(valid) >= 50:
            q1, q3 = valid[col].quantile([0.25, 0.75])
            if q3 > q1:
                soft |= valid[col] > q3 + 3 * (q3 - q1)
        flags = flags.mask(soft, flags + col + ";")
        valid[col] = valid[col].clip(upper=CLIP_LIMITS[col])
    valid["outlier_flag"] = flags != ""
    valid["outlier_fields"] = flags.str.rstrip(";")
    summary["outliers_flagged"] = int(valid["outlier_flag"].sum())

    # ---- typing + promise + label -----------------------------------------------------------------
    valid["num_items"] = valid["num_items"].astype(int)
    provided = valid["promised_eta"].notna()
    est = fc.baseline_quote(valid["distance_km"], valid["num_items"])
    valid["promised_eta_estimated"] = ~provided
    valid["promised_eta"] = valid["promised_eta"].where(provided, est)
    summary["promised_eta_estimated"] = int((~provided).sum())
    if summary["promised_eta_estimated"]:
        warnings.append(f"promised_eta was not supplied for {summary['promised_eta_estimated']} order(s); "
                        "the platform baseline quote (distance + items) was used instead.")
    has_actual = valid["actual_delivery_time"].notna()
    summary["has_actuals"] = bool(has_actual.any())
    labelled = has_actual & provided
    valid["delayed"] = np.where(labelled, (valid["actual_delivery_time"] > valid["promised_eta"] + fc.DELAY_GRACE_MINUTES).astype(float), np.nan)
    if summary["rows_removed"]:
        warnings.append(f"{summary['rows_removed']} row(s) were removed by validation; see the issue list.")
    return CleaningResult(valid.reset_index(drop=True), summary, issues, warnings)
