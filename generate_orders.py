"""Generate synthetic food-delivery orders.

    python generate_orders.py --n 5000 --seed 7 --out data/my_orders.csv
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from synthetic_data import delay_rate, generate_orders  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=6000, help="number of orders (3,000-8,000 recommended for training)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "orders.csv")
    a = ap.parse_args()
    df = generate_orders(a.n, a.seed)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"wrote {len(df):,} orders to {a.out}  (delay rate {delay_rate(df):.1%})")


if __name__ == "__main__":
    main()
