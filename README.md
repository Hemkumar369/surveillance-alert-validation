# Surveillance Alert Validation and Tuning (Python, SQL, pandas)

Validates a trade-surveillance pipeline end to end: reconcile orders to trades, score alert
logic against labeled cases, tune thresholds, and regression-test the change (v1 -> v2).

## Results (seeded, reproducible)
| Stage | Result |
|---|---|
| Order-to-trade reconciliation | Detected **23 / 23** injected defects (8 missing trades, 8 quantity mismatches, 7 duplicate trade IDs), 0 false positives |
| v1 -> v2 tuning | Total alerts cut **47 -> 31** |
| Wash-trade precision | **48% -> 100%** (recall 100% -> 75%) |
| Documented trade-off | **3 missed wash-trade cases** in v2: genuine washes with a 2-4 minute gap, outside the tightened 60s window |
| Spoofing/layering | Unchanged v1 vs v2 (precision 77%, recall 100%), used as a regression guard |

## What changed in v2 (`src/rules.py`)
| Parameter | v1 | v2 |
|---|---|---|
| Match entity | firm | beneficial owner (removes legit desk-to-desk flow) |
| Window | 300s | 60s |
| Qty tolerance | 10% | 5% |

## Layout
- `sql/reconcile.sql` - dedupe view, duplicate IDs, missing trades, quantity mismatches (SQLite)
- `src/generate_data.py` - seeded synthetic orders/trades, defect injection, labeled cases
- `src/reconcile.py` - runs the SQL, scores detection against the injected-defect log
- `src/rules.py` - wash-trade and spoofing rules plus v1/v2 configs
- `src/evaluate.py` - precision/recall per pattern, regression diff with verdicts
- `run_all.py` - runs everything, writes CSVs to `out/`

## Run
```
pip install -r requirements.txt
python run_all.py
```
Note: data is synthetic and the labels are constructed, so these are validation-harness results, not production performance.
