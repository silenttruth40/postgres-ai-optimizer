-- Intentionally inefficient demo queries. Metrics come from EXPLAIN ANALYZE.

-- Q001: filtered join + aggregation (missing composite index)
SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_count, SUM(o.amount) AS total_amount
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.customer_id, c.name
ORDER BY total_amount DESC;

-- Q002: sequential scan with sensitive literal (privacy demo)
SELECT customer_id, name, email
FROM customers
WHERE email = 'user42@example.com';

-- Q003: aggregation + sort on unindexed timestamp
SELECT customer_id, COUNT(*) AS txn_count, SUM(amount) AS total
FROM transactions
WHERE created_at >= CURRENT_DATE - INTERVAL '14 days'
GROUP BY customer_id
ORDER BY total DESC
LIMIT 50;

-- Q004: SELECT * + large sort
SELECT *
FROM orders
WHERE status = 'open'
ORDER BY created_at DESC, amount DESC;

-- Q005: correlated subquery (rewrite candidate)
SELECT c.customer_id, c.name
FROM customers c
WHERE EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = c.customer_id
      AND o.amount > 500
);

-- Q006: join without supporting indexes
SELECT o.order_id, p.name, oi.quantity, oi.unit_price
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '7 days'
  AND p.category = 'electronics';
