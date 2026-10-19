"""Order-to-trade reconciliation (SQL on SQLite) and defect detection scoring."""
import re
import sqlite3
from pathlib import Path
import pandas as pd

SQL_FILE = Path(__file__).resolve().parents[1] / "sql" / "reconcile.sql"


def _queries():
    parts = re.split(r"^-- name: (\w+)\s*$", SQL_FILE.read_text(), flags=re.M)
    return dict(zip(parts[1::2], (p.strip() for p in parts[2::2])))


def reconcile(orders: pd.DataFrame, trades: pd.DataFrame):
    con = sqlite3.connect(":memory:")
    orders.assign(ts=orders.ts.astype(str)).to_sql("orders", con, index=False)
    trades.assign(ts=trades.ts.astype(str)).to_sql("trades", con, index=False)
    q = _queries()
    con.execute(q["clean_trades_view"])
    found = {
        "duplicate_trade_id": pd.read_sql(q["duplicate_trade_ids"], con).trade_id,
        "missing_trade": pd.read_sql(q["missing_trades"], con).order_id,
        "quantity_mismatch": pd.read_sql(q["quantity_mismatches"], con).order_id,
    }
    con.close()
    return {k: set(v) for k, v in found.items()}


def score(found: dict, injected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dtype, grp in injected.groupby("defect_type"):
        truth, got = set(grp.key), found[dtype]
        rows.append(dict(defect_type=dtype, injected=len(truth), detected=len(truth & got),
                         false_positives=len(got - truth)))
    out = pd.DataFrame(rows)
    out.loc[len(out)] = ["TOTAL", out.injected.sum(), out.detected.sum(), out.false_positives.sum()]
    return out
