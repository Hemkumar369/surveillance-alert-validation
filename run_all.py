"""End-to-end: generate data -> reconcile -> score defects -> tune v1/v2 -> regression diff."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from generate_data import build          # noqa: E402
from reconcile import reconcile, score   # noqa: E402
from rules import run_version            # noqa: E402
from evaluate import pattern_metrics, regression_diff  # noqa: E402

pd.set_option("display.width", 140)
out = ROOT / "out"; out.mkdir(exist_ok=True)
orders, trades, labels, injected = build()
for n, df in [("orders", orders), ("trades", trades), ("labels", labels), ("injected_defects", injected)]:
    df.to_csv(ROOT / "data" / f"{n}.csv", index=False)

print("== 1. Order-to-trade reconciliation ==")
rec = score(reconcile(orders, trades), injected)
print(rec.to_string(index=False)); rec.to_csv(out / "defect_detection.csv", index=False)

a1, a2 = run_version(orders, trades, "v1"), run_version(orders, trades, "v2")
print("\n== 2. Alert precision / recall per pattern ==")
for v, a in (("v1", a1), ("v2", a2)):
    m = pattern_metrics(a, labels).assign(version=v)
    print(f"\n{v}: {len(a)} total alerts"); print(m.round(3).to_string(index=False))
    m.to_csv(out / f"metrics_{v}.csv", index=False)

print("\n== 3. v1 -> v2 regression diff ==")
diff = regression_diff(a1, a2, labels); diff.to_csv(out / "regression_diff.csv", index=False)
print(diff.groupby(["pattern", "change", "verdict"]).size().rename("cases").to_string())
print(f"\nTotal alerts: {len(a1)} -> {len(a2)}")
