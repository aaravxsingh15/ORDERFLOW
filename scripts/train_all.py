"""Train both models and write ml/models/metrics.json:  python scripts/train_all.py"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "backend"):
    sys.path.insert(0, str(p))

from ml.evaluate import combine_metrics  # noqa: E402
from ml.train_delay_model import train as train_delay  # noqa: E402
from ml.train_eta_model import train as train_eta  # noqa: E402

if __name__ == "__main__":
    t = time.time()
    print("Delay classifier")
    train_delay()
    print("ETA regressor")
    train_eta()
    m = combine_metrics()
    print(f"done in {time.time() - t:.0f}s")
    print("classifier:", {k: round(v, 3) for k, v in m["classifier"]["metrics"].items()})
    print("regressor :", {k: round(v, 3) for k, v in m["regressor"]["metrics"].items()})
    for r in m["classifier"]["feature_importance"][:8]:
        print(f"  {r['label']:40s} {r['importance']:.1f}")
