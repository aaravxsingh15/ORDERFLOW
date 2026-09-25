"""Train the delay classifier (RandomForest primary; LogisticRegression / GradientBoosting for comparison).

    python -m ml.train_delay_model
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ml import feature_config as fc  # noqa: E402
from ml.dataset import load_training_frame, split_indices  # noqa: E402
from ml.evaluate import MODEL_DIR, classification_metrics, importance_table  # noqa: E402
import delay_predictor as dp  # noqa: E402
from feature_engineering import model_frame  # noqa: E402

MODEL_PATH = MODEL_DIR / "delay_classifier.joblib"


def train(verbose: bool = True) -> dict:
    feats, quality = load_training_frame()
    tr, te = split_indices(feats)
    X = model_frame(feats, "classifier")
    y = feats["delayed"].astype(int)
    X_tr, X_te, y_tr, y_te = X.loc[tr], X.loc[te], y.loc[tr], y.loc[te]

    comparison, primary, primary_metrics = [], None, None
    for kind in ("random_forest", "logistic_regression", "gradient_boosting"):
        pipe = dp.build_pipeline(kind).fit(X_tr, y_tr)
        m = classification_metrics(y_te, pipe.predict_proba(X_te)[:, 1])
        comparison.append({"model": dp.NAMES[kind], "primary": kind == "random_forest",
                           **{k: m[k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc")}})
        if kind == "random_forest":
            primary, primary_metrics = pipe, m
        if verbose:
            print(f"  {dp.NAMES[kind]:28s} acc={m['accuracy']:.3f} f1={m['f1']:.3f} auc={m['roc_auc']:.3f}")

    importance = importance_table(primary, X_te, y_te, "roc_auc")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": primary, "sklearn_version": sklearn.__version__, "kind": "classifier"}, MODEL_PATH, compress=3)
    report = {
        "dataset": {"rows_total": int(len(feats)), "train_rows": int(len(tr)), "test_rows": int(len(te)),
                    "delay_rate": float(y.mean()), "random_state": fc.RANDOM_STATE, "test_size": fc.TEST_SIZE,
                    "sklearn_version": sklearn.__version__, "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "cleaning": quality},
        "classifier": {"model": dp.NAMES["random_forest"], "features": fc.CLASSIFIER_NUMERIC + fc.CATEGORICAL_FEATURES,
                       "metrics": {k: primary_metrics[k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc")},
                       "confusion_matrix": primary_metrics["confusion_matrix"], "comparison": comparison,
                       "feature_importance": importance},
    }
    (MODEL_DIR / "delay_metrics.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    print("Training delay classifier...")
    r = train()
    print(json.dumps(r["classifier"]["metrics"], indent=2))
