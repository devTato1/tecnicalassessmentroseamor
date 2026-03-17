-- Staging: ORDERS
-- Cleaning applied:
--   - Blank unit_price   -> _null_price=1
--   - Negative quantity  -> _negative_qty=1
--   - Duplicate order_id -> _is_duplicate=1 
--   - order_date         -> cast to DATE
--   - channel            -> lower case
DROP TABLE IF EXISTS stg_orders CASCADE;

CREATE TABLE stg_orders (
    order_id      TEXT,
    customer_id   TEXT,
    sku           TEXT,
    quantity      INTEGER,
    unit_price    DOUBLE PRECISION,
    order_date    DATE,
    channel       TEXT,
    _is_duplicate SMALLINT DEFAULT 0,
    _negative_qty SMALLINT DEFAULT 0,
    _null_price   SMALLINT DEFAULT 0
);


-- Staging: CUSTOMERS
-- Cleaning applied:
--   - Empty country -> 'Unknown'
--   - Empty segment -> 'Unknown'
--   - created_at    -> DATE
DROP TABLE IF EXISTS stg_customers CASCADE;

CREATE TABLE stg_customers (
    customer_id TEXT,
    name        TEXT,
    country     TEXT,
    segment     TEXT,
    created_at  DATE
);


-- Staging: PRODUCTS
-- Cleaning applied:
--   - Empty category -> 'Unknown'
--   - active         -> SMALLINT (1=True, 0=False)
DROP TABLE IF EXISTS stg_products CASCADE;

CREATE TABLE stg_products (
    sku      TEXT,
    category TEXT,
    cost     DOUBLE PRECISION,
    active   SMALLINT
);


-- QA checks (run after loading)
SELECT 'duplicates' AS issue, COUNT(*) AS rows FROM stg_orders WHERE _is_duplicate = 1
UNION ALL
SELECT 'negative_qty', COUNT(*) FROM stg_orders WHERE _negative_qty = 1
UNION ALL
SELECT 'null_price', COUNT(*) FROM stg_orders WHERE _null_price = 1;

SELECT country, segment, COUNT(*) AS rows
FROM stg_customers
WHERE country = 'Unknown' OR segment = 'Unknown'
GROUP BY country, segment;

SELECT category, COUNT(*) AS rows
FROM stg_products
WHERE category = 'Unknown'
GROUP BY category;
