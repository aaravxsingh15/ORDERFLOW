"""Delay classifier: pipeline definition + inference wrapper (probability, class, status, confidence)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import config  # noqa: F401
from ml import feature_config as fc
from feature_engineering import model_frame

NAMES = {"random_forest": "RandomForestClassifier", "logistic_regression": "LogisticRegression",
         "gradient_boosting": "GradientBoostingClassifier"}


def build_pipeline(kind: str = "random_forest") -> Pipeline:
    numeric = StandardScaler() if kind == "logistic_regression" else "passthrough"
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), fc.CATEGORICAL_FEATURES),
        ("num", numeric, fc.CLASSIFIER_NUMERIC),
    ])
    if kind == "random_forest":
        est = RandomForestClassifier(n_estimators=250, min_samples_leaf=4, max_features=0.5,
                                     random_state=fc.RANDOM_STATE, n_jobs=1)
    elif kind == "logistic_regression":
        est = LogisticRegression(max_iter=3000, C=1.0, random_state=fc.RANDOM_STATE)
    elif kind == "gradient_boosting":
        est = GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.08, random_state=fc.RANDOM_STATE)
    else:
        raise ValueError(f"unknown classifier kind: {kind}")
    return Pipeline([("prep", pre), ("model", est)])


def status_for(p: float) -> str:
    if p < fc.STATUS_ON_TIME_BELOW:
        return "ON TIME"
    return "DELAY LIKELY" if p >= fc.STATUS_DELAY_LIKELY_FROM else "AT RISK"


def confidence_for(p: float) -> str:
    """How far the probability is from the coin-flip zone (not a calibrated confidence interval)."""
    m = max(p, 1 - p)
    return "High" if m >= 0.80 else "Medium" if m >= 0.65 else "Low"


class DelayPredictor:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        return self.pipeline.predict_proba(model_frame(features, "classifier"))[:, 1]

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        p = self.predict_proba(features)
        return pd.DataFrame({
            "delay_probability": p,
            "predicted_delayed": p >= fc.CLASSIFIER_THRESHOLD,
            "status": [status_for(x) for x in p],
            "delay_confidence": [confidence_for(x) for x in p],
        }, index=features.index)
