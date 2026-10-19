-- name: clean_trades_view
-- Exact duplicate rows (same trade_id loaded twice) are collapsed before reconciling.
CREATE VIEW clean_trades AS SELECT DISTINCT * FROM trades;

-- name: duplicate_trade_ids
SELECT trade_id, COUNT(*) AS n_rows
FROM trades
GROUP BY trade_id
HAVING COUNT(*) > 1;

-- name: missing_trades
-- FILLED orders with no matching trade.
SELECT o.order_id
FROM orders o
LEFT JOIN clean_trades t ON t.order_id = o.order_id
WHERE o.status = 'FILLED' AND t.trade_id IS NULL;

-- name: quantity_mismatches
-- FILLED orders whose executed quantity differs from the order quantity.
SELECT o.order_id, o.qty AS order_qty, SUM(t.qty) AS trade_qty
FROM orders o
JOIN clean_trades t ON t.order_id = o.order_id
WHERE o.status = 'FILLED'
GROUP BY o.order_id, o.qty
HAVING SUM(t.qty) <> o.qty;
