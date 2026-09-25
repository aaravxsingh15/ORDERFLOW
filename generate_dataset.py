"""Build every dataset ORDERFLOW ships with (deterministic seeds):

  data/training_orders.csv         6,000 orders used to train both models
  data/demo_orders.csv               600 held-out orders preloaded in demo mode (never seen in training)
  data/sample_orders.csv             200 clean orders for trying the CSV upload
  data/sample_orders_with_issues.csv 203 messy rows that exercise validation and cleaning

    python generate_dataset.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from synthetic_data import delay_rate, generate_orders, inject_issues  # noqa: E402

SETS = {
    "training_orders.csv": (6000, 7, False),
    "demo_orders.csv": (600, 2026, False),
    "sample_orders.csv": (200, 314, False),
    "sample_orders_with_issues.csv": (200, 99, True),
}


def main() -> None:
    out = ROOT / "data"
    out.mkdir(exist_ok=True)
    for name, (n, seed, messy) in SETS.items():
        df = generate_orders(n, seed)
        rate = delay_rate(df)
        if messy:
            df = inject_issues(df, seed=11)
        df.to_csv(out / name, index=False)
        print(f"{name:34s} {len(df):5d} rows  delay rate {rate:.1%}")


if __name__ == "__main__":
    main()
