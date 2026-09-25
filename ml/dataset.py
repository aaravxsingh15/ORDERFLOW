"""Shared data loading + the single train/test split used by both models (no leakage between them)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ml import feature_config as fc  # noqa: E402
import config  # noqa: E402
from data_cleaner import clean_orders  # noqa: E402
from feature_engineering import engineer_features  # noqa: E402


def load_training_frame(path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """Reads the training CSV (generating it if missing), then runs the *same* clean + engineer steps as production."""
    path = Path(path or config.TRAIN_CSV)
    if not path.exists():
        import synthetic_data
        path.parent.mkdir(parents=True, exist_ok=True)
        synthetic_data.generate_orders(6000, seed=7).to_csv(path, index=False)
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    cleaned = clean_orders(raw)
    feats = engineer_features(cleaned.df)
    feats = feats[feats["delayed"].notna() & feats["actual_delivery_time"].notna()].reset_index(drop=True)
    return feats, cleaned.summary


def split_indices(feats: pd.DataFrame):
    idx = feats.index.to_numpy()
    return train_test_split(idx, test_size=fc.TEST_SIZE, random_state=fc.RANDOM_STATE, stratify=feats["delayed"].astype(int))
