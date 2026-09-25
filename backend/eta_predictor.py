"""ETA regressor: pipeline definition + inference wrapper (estimate, expected range, confidence)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

import config  # noqa: F401
from ml import feature_config as fc
from feature_engineering import model_frame

NAMES = {"random_forest": "RandomForestRegressor", "gradient_boosting": "GradientBoostingRegressor"}


def build_pipeline(kind: str = "random_forest") -> Pipeline:
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), fc.CATEGORICAL_FEATURES),
        ("num", "passthrough", fc.REGRESSOR_NUMERIC),
    ])
    if kind == "random_forest":
        est = RandomForestRegressor(n_estimators=200, min_samples_leaf=3, max_features=0.5,
                                    random_state=fc.RANDOM_STATE, n_jobs=1)
    elif kind == "gradient_boosting":
        est = GradientBoostingRegressor(n_estimators=250, max_depth=3, learning_rate=0.08, random_state=fc.RANDOM_STATE)
    else:
        raise ValueError(f"unknown regressor kind: {kind}")
    return Pipeline([("prep", pre), ("model", est)])


class EtaPredictor:
    """`meta` carries what training measured: residual quantiles (range) and tree-spread tertiles (confidence)."""

    def __init__(self, pipeline: Pipeline, meta: dict):
        self.pipeline = pipeline
        self.meta = meta

    def predict_minutes(self, features: pd.DataFrame) -> np.ndarray:
        return self.pipeline.predict(model_frame(features, "regressor"))

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        X = self.pipeline.named_steps["prep"].transform(model_frame(features, "regressor"))
        forest = self.pipeline.named_steps["model"]
        per_tree = np.stack([t.predict(X) for t in forest.estimators_])
        eta = per_tree.mean(axis=0)
        spread = per_tree.std(axis=0)
        lo_q, hi_q = self.meta["residual_q10"], self.meta["residual_q90"]
        conf = np.where(spread <= self.meta["spread_q33"], "High", np.where(spread <= self.meta["spread_q66"], "Medium", "Low"))
        return pd.DataFrame({
            "eta_minutes": eta,
            "eta_low": np.maximum(eta + lo_q, fc.ACCEPT_MIN + 5),
            "eta_high": eta + hi_q,
            "eta_confidence": conf,
        }, index=features.index)
