"""Runtime paths and settings. Model/feature assumptions live in ml/feature_config.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml import feature_config as fc  # noqa: E402  (needs ROOT on sys.path)

MODEL_DIR = ROOT / "ml" / "models"
DATA_DIR = ROOT / "data"
TRAIN_CSV = DATA_DIR / "training_orders.csv"
DEMO_CSV = DATA_DIR / "demo_orders.csv"
SAMPLE_CSV = DATA_DIR / "sample_orders.csv"
SAMPLE_ISSUES_CSV = DATA_DIR / "sample_orders_with_issues.csv"

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_UPLOAD_ROWS = 50_000
TABLE_ROW_CAP = 20_000  # rows returned to the browser for the order table

DISCLAIMER = (
    "ORDERFLOW is an independent portfolio project inspired by food-delivery operations. "
    "It is not affiliated with, endorsed by, or sponsored by Zomato."
)
CREDIT = "Designed & Developed by Aarav Singh"
