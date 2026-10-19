-- ============================================================================
-- Part 1, Task 3 — Reports a–i (20 marks)
--
-- Nine business queries run against the RAW, uncleaned loaded data.
-- Run after schema.sql + seed_data.sql:
--     sqlite3 mamaearth.db < sql/reports.sql
--
-- The exact output of each query (captured from the sqlite3 CLI in `.mode box`)
-- is pasted as a comment block directly above the query, per the brief.
--
-- Revenue convention (used in a, e, f): revenue per row is
--     quantity * price * (1 - discount_pct/100)
-- NULL discount is treated as 0% via COALESCE, and we divide by 100.0 (float)
-- so SQLite does NOT do integer division (discount_pct/100 on an INT is 0).
-- ============================================================================


-- a) Order totals — total orders, total revenue, average order value ----------
--    (NULL discount = 0%). Joins orders to products.
-- Expected: total_orders = 180, total_revenue = 99860.20, avg_order_value = 554.78
--
-- Output:
-- ┌──────────────┬───────────────┬─────────────────┐
-- │ total_orders │ total_revenue │ avg_order_value │
-- ├──────────────┼───────────────┼─────────────────┤
-- │ 180          │ 99860.2       │ 554.78          │
-- └──────────────┴───────────────┴─────────────────┘
SELECT COUNT(*) AS total_orders,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_revenue,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)) / COUNT(*), 2) AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id;


-- b) COUNT(*) vs COUNT(column) — how many orders have no rating ----------------
-- Expected: (180, 165, 15) — 15 orders have no rating yet.
-- COUNT(*) counts rows; COUNT(rating) skips NULLs, so the gap is the missing count.
--
-- Output:
-- ┌────────────┬──────────────┬─────────────────┐
-- │ count_star │ count_rating │ missing_ratings │
-- ├────────────┼──────────────┼─────────────────┤
-- │ 180        │ 165          │ 15              │
-- └────────────┴──────────────┴─────────────────┘
SELECT COUNT(*)            AS count_star,
       COUNT(rating)       AS count_rating,
       COUNT(*) - COUNT(rating) AS missing_ratings
FROM orders;


-- c) Customers with zero orders — two independent ways, results must match -----
-- Expected: both queries return exactly one row — C045, Vihaan.
--
-- c.1  LEFT JOIN + GROUP BY + HAVING COUNT(order_id) = 0
-- Output:
-- ┌─────────────┬────────┐
-- │ customer_id │  name  │
-- ├─────────────┼────────┤
-- │ C045        │ Vihaan │
-- └─────────────┴────────┘
SELECT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(o.order_id) = 0;

-- c.2  NOT IN (SELECT DISTINCT customer_id FROM orders) — confirms c.1 blindly-free
-- Output:
-- ┌─────────────┬────────┐
-- │ customer_id │  name  │
-- ├─────────────┼────────┤
-- │ C045        │ Vihaan │
-- └─────────────┴────────┘
SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);


-- d) Return rate by city, keeping only cities above 20% ------------------------
-- Expected exactly 3 rows: Jaipur (19, 8, 42.1), Lucknow (49, 15, 30.6),
--   Bangalore (33, 8, 24.2). Mumbai (17.9%) and Delhi (17.4%) correctly excluded.
--
-- Output:
-- ┌───────────┬──────────────┬─────────────────┬─────────────────┐
-- │   city    │ total_orders │ returned_orders │ return_rate_pct │
-- ├───────────┼──────────────┼─────────────────┼─────────────────┤
-- │ Jaipur    │ 19           │ 8               │ 42.1            │
-- │ Lucknow   │ 49           │ 15              │ 30.6            │
-- │ Bangalore │ 33           │ 8               │ 24.2            │
-- └───────────┴──────────────┴─────────────────┴─────────────────┘
SELECT c.city,
       COUNT(*)        AS total_orders,
       SUM(o.returned) AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 1) AS return_rate_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.city
HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;


-- e) Top customers by spend — ORDER BY + LIMIT / OFFSET ------------------------
-- Tie-break: ORDER BY total_spend DESC, customer_id ASC. The second key makes
-- the ordering deterministic when two customers have an equal total_spend, so
-- that LIMIT 3 OFFSET 2 returns exactly the same rows 3–5 as the LIMIT 5 slice.
-- Expected top 5: C043 12920.00, C026 8371.60, C008 4564.60, C011 4111.00, C042 3785.00
--
-- e.1  LIMIT 5
-- Output:
-- ┌─────────────┬─────────┬─────────────┐
-- │ customer_id │  name   │ total_spend │
-- ├─────────────┼─────────┼─────────────┤
-- │ C043        │ Reyansh │ 12920.0     │
-- │ C026        │ Isha    │ 8371.6      │
-- │ C008        │ Meera   │ 4564.6      │
-- │ C011        │ Arjun   │ 4111.0      │
-- │ C042        │ Sanya   │ 3785.0      │
-- └─────────────┴─────────┴─────────────┘
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products p  ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 5;

-- e.2  LIMIT 3 OFFSET 2 — ranks 3–5 without re-deriving the top 5
-- Output:
-- ┌─────────────┬───────┬─────────────┐
-- │ customer_id │ name  │ total_spend │
-- ├─────────────┼───────┼─────────────┤
-- │ C008        │ Meera │ 4564.6      │
-- │ C011        │ Arjun │ 4111.0      │
-- │ C042        │ Sanya │ 3785.0      │
-- └─────────────┴───────┴─────────────┘
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products p  ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 3 OFFSET 2;


-- f) Order count and revenue by product category — three-table JOIN -----------
-- customers is joined too (not strictly needed here) to confirm the three-way
-- join compiles cleanly, since Part 3's numbers trace back through it.
-- Expected: Haircare (54, 44956.10), Skincare (60, 27346.00),
--   Babycare (30, 16805.00), PersonalCare (36, 10753.10).
--
-- Output:
-- ┌──────────────┬─────────────┬──────────────────┐
-- │   category   │ order_count │ category_revenue │
-- ├──────────────┼─────────────┼──────────────────┤
-- │ Haircare     │ 54          │ 44956.1          │
-- │ Skincare     │ 60          │ 27346.0          │
-- │ Babycare     │ 30          │ 16805.0          │
-- │ PersonalCare │ 36          │ 10753.1          │
-- └──────────────┴─────────────┴──────────────────┘
SELECT p.category,
       COUNT(*) AS order_count,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS category_revenue
FROM orders o
JOIN products p  ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY p.category
ORDER BY category_revenue DESC;


-- g) LIKE pattern match — customers whose name starts with 'A' -----------------
-- Expected: exactly 10 rows.
--
-- Output:
-- ┌─────────────┬────────┐
-- │ customer_id │  name  │
-- ├─────────────┼────────┤
-- │ C001        │ Aarav  │
-- │ C003        │ Aditi  │
-- │ C004        │ Ananya │
-- │ C011        │ Arjun  │
-- │ C021        │ Aryan  │
-- │ C030        │ Anika  │
-- │ C031        │ Aditya │
-- │ C036        │ Aisha  │
-- │ C041        │ Ayaan  │
-- │ C044        │ Aria   │
-- └─────────────┴────────┘
SELECT customer_id, name
FROM customers
WHERE name LIKE 'A%';


-- h) DISTINCT — distinct acquisition sources across all customers --------------
-- Expected: exactly 4 values — Ad, Organic, Referral, Social.
--
-- Output:
-- ┌────────────────────┐
-- │ acquisition_source │
-- ├────────────────────┤
-- │ Ad                 │
-- │ Organic            │
-- │ Referral           │
-- │ Social             │
-- └────────────────────┘
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;


-- i) ALTER TABLE + UPDATE with CASE — add loyalty_tier -------------------------
-- Gold for tier-1 cities, Silver otherwise. Single UPDATE, no WHERE clause, so
-- every row gets a value.
-- Expected: Gold, 28 and Silver, 17.
--
-- Output of the GROUP BY check:
-- ┌──────────────┬────┐
-- │ loyalty_tier │ n  │
-- ├──────────────┼────┤
-- │ Gold         │ 28 │
-- │ Silver       │ 17 │
-- └──────────────┴────┘
ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);

UPDATE customers
SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold' ELSE 'Silver' END;

SELECT loyalty_tier, COUNT(*) AS n
FROM customers
GROUP BY loyalty_tier;
