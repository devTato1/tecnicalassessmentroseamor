-- =============================================================================
-- 02_consumption.sql  --  RoseAmor  |  Staging to Consumption Layer
-- =============================================================================
-- Purpose : Build the star-schema dimensional model used by the BI dashboard.
-- Engine  : PostgreSQL 14+
-- Run     : psql -U dev -d test -f sql/02_consumption.sql
-- Prereq  : 01_staging.sql (or etl/load_data.py) must have run first
-- =============================================================================


-- Dimensions: CUSTOMERS
DROP TABLE IF EXISTS dim_customers CASCADE;
CREATE TABLE dim_customers AS
SELECT customer_id, name, country, segment, created_at FROM stg_customers;
ALTER TABLE dim_customers ADD PRIMARY KEY (customer_id);


-- Dimensions: PRODUCTS
DROP TABLE IF EXISTS dim_products CASCADE;
CREATE TABLE dim_products AS
SELECT sku, category, cost, active FROM stg_products;
ALTER TABLE dim_products ADD PRIMARY KEY (sku);


-- Fact Table: ORDERS
-- Excluded rows:
--   _is_duplicate = 0  keep only the first occurrence
--   _negative_qty = 0  exclude returns / cancellations
--   _null_price   = 0  exclude rows where revenue cannot be calculated
--
-- Metrics: revenue, gross_profit, margin_pct (pre-computed at load time)
DROP TABLE IF EXISTS fact_orders CASCADE;

CREATE TABLE fact_orders AS
SELECT
    o.order_id,
    o.customer_id,
    o.sku,
    o.quantity,
    o.unit_price,
    o.order_date,
    TO_CHAR(o.order_date, 'YYYY')    AS year,
    TO_CHAR(o.order_date, 'MM')      AS month,
    TO_CHAR(o.order_date, 'YYYY-MM') AS year_month,
    o.channel,
    ROUND((o.quantity * o.unit_price)::numeric,                         2) AS revenue,
    ROUND((o.quantity * (o.unit_price - COALESCE(p.cost, 0)))::numeric, 2) AS gross_profit,
    ROUND((CASE
               WHEN o.unit_price > 0
               THEN (o.unit_price - COALESCE(p.cost, 0)) / o.unit_price * 100
               ELSE NULL
           END)::numeric, 2) AS margin_pct
FROM stg_orders  o
LEFT JOIN dim_products p ON o.sku = p.sku
WHERE o._is_duplicate = 0
  AND o._negative_qty = 0
  AND o._null_price   = 0;

ALTER TABLE fact_orders ADD PRIMARY KEY (order_id);
CREATE INDEX idx_fact_orders_customer ON fact_orders (customer_id);
CREATE INDEX idx_fact_orders_sku      ON fact_orders (sku);
CREATE INDEX idx_fact_orders_date     ON fact_orders (order_date);
CREATE INDEX idx_fact_orders_channel  ON fact_orders (channel);


-- Analytical view (denormalized - used by Power BI / Looker Studio)
DROP VIEW IF EXISTS v_orders_full;

CREATE VIEW v_orders_full AS
SELECT
    f.order_id,
    f.order_date,
    f.year,
    f.month,
    f.year_month,
    f.channel,
    f.quantity,
    f.unit_price,
    f.revenue,
    f.gross_profit,
    f.margin_pct,
    c.customer_id,
    c.name        AS customer_name,
    c.country,
    c.segment,
    p.sku,
    p.category,
    p.cost        AS product_cost,
    p.active      AS product_active
FROM fact_orders   f
JOIN dim_customers c ON f.customer_id = c.customer_id
JOIN dim_products  p ON f.sku         = p.sku;
