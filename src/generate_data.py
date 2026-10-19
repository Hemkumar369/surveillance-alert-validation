"""Build a synthetic order/trade dataset with 23 injected data defects and
labeled surveillance cases (wash trades, spoofing/layering). Fully seeded."""
import random
from pathlib import Path
import pandas as pd

SEED = 42
N_BASE = 300
DEFECTS = {"missing_trade": 8, "quantity_mismatch": 8, "duplicate_trade_id": 7}  # = 23
N_WASH_TRUE, N_WASH_TRUE_SLOW, N_WASH_FP = 12, 3, 13   # 3 of the 12 true cases are "slow" (gap > 60s)
N_SPOOF_TRUE, N_SPOOF_FP = 17, 5


def build(seed: int = SEED):
    rng = random.Random(seed)
    orders, trades, labels, defects = [], [], [], []
    ids = {"o": 0, "t": 0}
    t0 = pd.Timestamp("2026-03-02 09:30:00")

    def order(acct, firm, owner, sym, side, qty, px, ts, status="FILLED"):
        ids["o"] += 1
        o = dict(order_id=f"O{ids['o']:06d}", account_id=acct, firm_id=firm, owner_id=owner,
                 symbol=sym, side=side, qty=qty, price=px, ts=ts, status=status)
        orders.append(o)
        return o

    def fill(o, qty=None):
        ids["t"] += 1
        t = dict(trade_id=f"T{ids['t']:06d}", order_id=o["order_id"], symbol=o["symbol"],
                 side=o["side"], qty=qty if qty is not None else o["qty"], price=o["price"],
                 ts=o["ts"] + pd.Timedelta(seconds=1))
        trades.append(t)
        return t

    # ---- clean baseline flow (orders spaced > 300s apart so no accidental pairs) ----
    base = []
    for i in range(N_BASE):
        firm = f"F{rng.randint(1, 10):02d}"
        o = order(f"A{rng.randint(1, 40):03d}", firm, f"OWN-{firm}", f"BASE{rng.randint(1, 20):02d}",
                  rng.choice(["BUY", "SELL"]), rng.randint(2, 50) * 100, round(rng.uniform(10, 200), 2),
                  t0 + pd.Timedelta(seconds=i * 400 + rng.randint(0, 30)))
        base.append(o)

    # ---- inject 23 data defects into baseline orders ----
    picks = rng.sample(range(N_BASE), sum(DEFECTS.values()))
    cut = 0
    for dtype, n in DEFECTS.items():
        for idx in picks[cut:cut + n]:
            o = base[idx]
            if dtype == "missing_trade":
                defects.append((dtype, o["order_id"]))
            elif dtype == "quantity_mismatch":
                fill(o, qty=o["qty"] - 100)
                defects.append((dtype, o["order_id"]))
            else:  # duplicate_trade_id: same trade row loaded twice
                t = fill(o)
                trades.append(dict(t))
                defects.append((dtype, t["trade_id"]))
        cut += n
    injected = set(picks)
    for idx, o in enumerate(base):
        if idx not in injected:
            fill(o)

    # ---- wash-trade cases ----
    day = t0 + pd.Timedelta(days=10)
    for k in range(N_WASH_TRUE):
        sym, firm, owner = f"WASH{k:02d}", f"FW{k:02d}", f"OWN-W{k:02d}"
        gap = rng.randint(10, 50) if k < N_WASH_TRUE - N_WASH_TRUE_SLOW else rng.randint(120, 240)
        qty, px, ts = rng.randint(5, 40) * 100, round(rng.uniform(20, 90), 2), day + pd.Timedelta(hours=k)
        fill(order(f"AW{k:02d}A", firm, owner, sym, "BUY", qty, px, ts))
        fill(order(f"AW{k:02d}B", firm, owner, sym, "SELL", qty, px, ts + pd.Timedelta(seconds=gap)))
        labels.append(("wash_trade", sym, True))
    for k in range(N_WASH_FP):  # same firm, different beneficial owners (legit desk-to-desk flow)
        sym, firm = f"WASHFP{k:02d}", f"FF{k:02d}"
        gap = rng.randint(30, 200)
        qty, px, ts = rng.randint(5, 40) * 100, round(rng.uniform(20, 90), 2), day + pd.Timedelta(hours=20 + k)
        fill(order(f"AF{k:02d}A", firm, f"OWN-D{k:02d}A", sym, "BUY", qty, px, ts))
        fill(order(f"AF{k:02d}B", firm, f"OWN-D{k:02d}B", sym, "SELL", qty, px, ts + pd.Timedelta(seconds=gap)))
        labels.append(("wash_trade", sym, False))

    # ---- spoofing / layering cases (rapid repeated cancels) ----
    sday = t0 + pd.Timedelta(days=20)
    for k in range(N_SPOOF_TRUE + N_SPOOF_FP):
        is_true = k < N_SPOOF_TRUE
        sym, firm = f"SPOOF{k:02d}", f"FS{k:02d}"
        n, step = (4, 5) if is_true else (3, 8)
        for j in range(n):
            order(f"AS{k:02d}", firm, f"OWN-{firm}", sym, "BUY", 5000, 50.0,
                  sday + pd.Timedelta(hours=k, seconds=j * step), status="CANCELLED")
        labels.append(("spoofing", sym, is_true))

    return (pd.DataFrame(orders), pd.DataFrame(trades),
            pd.DataFrame(labels, columns=["pattern", "symbol", "is_true"]),
            pd.DataFrame(defects, columns=["defect_type", "key"]))


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data"
    out.mkdir(exist_ok=True)
    for name, df in zip(["orders", "trades", "labels", "injected_defects"], build()):
        df.to_csv(out / f"{name}.csv", index=False)
