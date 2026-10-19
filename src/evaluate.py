"""Precision/recall per pattern against labeled cases, and a v1->v2 regression diff."""
import pandas as pd


def pattern_metrics(alerts: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pattern, lab in labels.groupby("pattern"):
        a = set(alerts[alerts.pattern == pattern].symbol)
        pos = set(lab[lab.is_true].symbol)
        tp = len(a & pos)
        rows.append(dict(pattern=pattern, alerts=len(a), true_pos=tp, false_pos=len(a) - tp,
                         missed=len(pos - a), precision=tp / len(a) if a else float("nan"),
                         recall=tp / len(pos) if pos else float("nan")))
    return pd.DataFrame(rows)


def regression_diff(a1: pd.DataFrame, a2: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    d = (a1[["pattern", "symbol"]].assign(in_v1=True)
         .merge(a2[["pattern", "symbol"]].assign(in_v2=True), on=["pattern", "symbol"], how="outer")
         .fillna(False))
    d[["in_v1", "in_v2"]] = d[["in_v1", "in_v2"]].astype(bool)
    d = d.merge(labels, on=["pattern", "symbol"], how="left").fillna({"is_true": False})
    d["is_true"] = d.is_true.astype(bool)
    d["change"] = "unchanged"
    d.loc[d.in_v1 & ~d.in_v2, "change"] = "removed_in_v2"
    d.loc[~d.in_v1 & d.in_v2, "change"] = "added_in_v2"
    d["verdict"] = ""
    d.loc[(d.change == "removed_in_v2") & ~d.is_true, "verdict"] = "good: false positive removed"
    d.loc[(d.change == "removed_in_v2") & d.is_true, "verdict"] = "MISSED true case (trade-off)"
    d.loc[(d.change == "added_in_v2") & ~d.is_true, "verdict"] = "regression: new false positive"
    return d.sort_values(["change", "pattern", "symbol"]).reset_index(drop=True)
