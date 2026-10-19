"""Surveillance rules and versioned threshold configs (v1 baseline, v2 tuned)."""
import pandas as pd

CONFIGS = {
    "v1": {  # baseline: firm-level matching, wide window, loose qty tolerance
        "wash": dict(key="firm_id", window_s=300, qty_tol=0.10, price_tol=0.005),
        "spoof": dict(min_cancels=3, window_s=30),
    },
    "v2": {  # tuned: beneficial-owner matching, tighter window and qty tolerance
        "wash": dict(key="owner_id", window_s=60, qty_tol=0.05, price_tol=0.005),
        "spoof": dict(min_cancels=3, window_s=30),
    },
}


def detect_wash(orders, trades, cfg) -> set:
    t = trades.merge(orders[["order_id", "firm_id", "owner_id"]], on="order_id")
    buys, sells = t[t.side == "BUY"], t[t.side == "SELL"]
    m = buys.merge(sells, on=["symbol", cfg["key"]], suffixes=("_b", "_s"))
    dt = (m.ts_b - m.ts_s).abs().dt.total_seconds()
    qty_diff = (m.qty_b - m.qty_s).abs() / m[["qty_b", "qty_s"]].max(axis=1)
    px_diff = (m.price_b - m.price_s).abs() / m[["price_b", "price_s"]].max(axis=1)
    hit = m[(dt <= cfg["window_s"]) & (qty_diff <= cfg["qty_tol"]) & (px_diff <= cfg["price_tol"])]
    return set(hit.symbol)


def detect_spoof(orders, cfg) -> set:
    c = orders[orders.status == "CANCELLED"].sort_values("ts")
    alerts = set()
    for (_, sym, _), g in c.groupby(["account_id", "symbol", "side"]):
        ts = g.ts.reset_index(drop=True)
        for i in range(len(ts)):
            n = ((ts >= ts[i]) & (ts <= ts[i] + pd.Timedelta(seconds=cfg["window_s"]))).sum()
            if n >= cfg["min_cancels"]:
                alerts.add(sym)
                break
    return alerts


def run_version(orders, trades, version) -> pd.DataFrame:
    cfg = CONFIGS[version]
    rows = [("wash_trade", s) for s in detect_wash(orders, trades, cfg["wash"])]
    rows += [("spoofing", s) for s in detect_spoof(orders, cfg["spoof"])]
    return pd.DataFrame(rows, columns=["pattern", "symbol"]).assign(version=version)
