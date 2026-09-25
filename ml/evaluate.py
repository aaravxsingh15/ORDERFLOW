"""Evaluation helpers + metrics.json assembly. `python -m ml.evaluate` prints the saved report."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error, precision_score,
                             r2_score, recall_score, roc_auc_score)

from ml import feature_config as fc

MODEL_DIR = Path(__file__).resolve().parent / "models"


def classification_metrics(y_true, proba, threshold: float = fc.CLASSIFIER_THRESHOLD) -> dict:
    y = np.asarray(y_true).astype(int)
    pred = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y, pred)), "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)), "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, proba)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def regression_metrics(y_true, pred) -> dict:
    y, p = np.asarray(y_true, dtype=float), np.asarray(pred, dtype=float)
    return {"mae": float(mean_absolute_error(y, p)), "rmse": float(np.sqrt(np.mean((y - p) ** 2))), "r2": float(r2_score(y, p))}


def importance_table(pipeline, X_test, y_test, scoring: str, top: int = 12) -> list[dict]:
    """Permutation importance on held-out data, per raw feature, as % of total positive importance."""
    res = permutation_importance(pipeline, X_test, y_test, scoring=scoring, n_repeats=5,
                                 random_state=fc.RANDOM_STATE, n_jobs=1)
    imp = np.clip(res.importances_mean, 0, None)
    total = imp.sum() or 1.0
    rows = [{"feature": c, "label": fc.FEATURE_LABELS.get(c, c), "importance": float(v / total * 100)}
            for c, v in zip(X_test.columns, imp)]
    return sorted(rows, key=lambda r: -r["importance"])[:top]


def combine_metrics() -> dict:
    delay = json.loads((MODEL_DIR / "delay_metrics.json").read_text())
    eta = json.loads((MODEL_DIR / "eta_metrics.json").read_text())
    combined = {
        "dataset": delay["dataset"],
        "config": {"delay_grace_minutes": fc.DELAY_GRACE_MINUTES, "on_time_below": fc.STATUS_ON_TIME_BELOW,
                   "delay_likely_from": fc.STATUS_DELAY_LIKELY_FROM, "classifier_threshold": fc.CLASSIFIER_THRESHOLD,
                   "delay_rule": f"Delayed if actual_delivery_time > promised_eta + {fc.DELAY_GRACE_MINUTES:g} minutes"},
        "classifier": delay["classifier"], "regressor": eta["regressor"],
    }
    (MODEL_DIR / "metrics.json").write_text(json.dumps(combined, indent=2))
    return combined


if __name__ == "__main__":
    m = json.loads((MODEL_DIR / "metrics.json").read_text())
    print(json.dumps({"dataset": m["dataset"], "classifier": m["classifier"]["metrics"], "regressor": m["regressor"]["metrics"]}, indent=2))
