"""Train the ETA regressor (RandomForest primary; GradientBoosting + naive baselines for comparison).

    python -m ml.train_eta_model
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import sklearn

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ml import feature_config as fc  # noqa: E402
from ml.dataset import load_training_frame, split_indices  # noqa: E402
from ml.evaluate import MODEL_DIR, importance_table, regression_metrics  # noqa: E402
import eta_predictor as ep  # noqa: E402
from feature_engineering import model_frame  # noqa: E402

MODEL_PATH = MODEL_DIR / "eta_regressor.joblib"


def train(verbose: bool = True) -> dict:
    feats, _ = load_training_frame()
    tr, te = split_indices(feats)
    X = model_frame(feats, "regressor")
    y = feats["actual_delivery_time"].astype(float)
    X_tr, X_te, y_tr, y_te = X.loc[tr], X.loc[te], y.loc[tr], y.loc[te]

    comparison, primary, primary_metrics = [], None, None
    for kind in ("random_forest", "gradient_boosting"):
        pipe = ep.build_pipeline(kind).fit(X_tr, y_tr)
        m = regression_metrics(y_te, pipe.predict(X_te))
        comparison.append({"model": ep.NAMES[kind], "primary": kind == "random_forest", **m})
        if kind == "random_forest":
            primary, primary_metrics = pipe, m
        if verbose:
            print(f"  {ep.NAMES[kind]:28s} MAE={m['mae']:.2f} RMSE={m['rmse']:.2f} R2={m['r2']:.3f}")
    # naive references, so the model's value is visible
    comparison.append({"model": "Baseline: platform quote (promised ETA)", "primary": False,
                       **regression_metrics(y_te, feats.loc[te, "promised_eta"])})
    comparison.append({"model": "Baseline: training mean", "primary": False,
                       **regression_metrics(y_te, np.full(len(te), y_tr.mean()))})

    # residual quantiles (expected range) and tree-spread tertiles (confidence) come from held-out data only
    X_t = primary.named_steps["prep"].transform(X_te)
    per_tree = np.stack([t.predict(X_t) for t in primary.named_steps["model"].estimators_])
    pred, spread = per_tree.mean(axis=0), per_tree.std(axis=0)
    resid = y_te.to_numpy() - pred
    meta = {"residual_q10": float(np.quantile(resid, 0.10)), "residual_q90": float(np.quantile(resid, 0.90)),
            "spread_q33": float(np.quantile(spread, 1 / 3)), "spread_q66": float(np.quantile(spread, 2 / 3))}
    cover = float(np.mean((resid >= meta["residual_q10"]) & (resid <= meta["residual_q90"])))

    rng = np.random.default_rng(fc.RANDOM_STATE)
    pick = rng.choice(len(te), size=min(400, len(te)), replace=False)
    importance = importance_table(primary, X_te, y_te, "neg_mean_absolute_error")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": primary, "meta": meta, "sklearn_version": sklearn.__version__, "kind": "regressor"}, MODEL_PATH, compress=3)
    report = {"regressor": {
        "model": ep.NAMES["random_forest"], "features": fc.REGRESSOR_NUMERIC + fc.CATEGORICAL_FEATURES,
        "metrics": primary_metrics, "comparison": comparison, "feature_importance": importance,
        "range_coverage": cover, "meta": meta,
        "actual_vs_predicted": [{"actual": float(y_te.to_numpy()[i]), "predicted": float(pred[i])} for i in pick],
    }}
    (MODEL_DIR / "eta_metrics.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    print("Training ETA regressor...")
    r = train()
    print(json.dumps(r["regressor"]["metrics"], indent=2))
