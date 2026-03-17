-- =============================================================================
-- kpis.sql  --  RoseAmor  |  Dashboard KPI Queries
-- =============================================================================
-- Target  : PostgreSQL 14+  (database: test)
-- Run     : psql -U dev -d test -f sql/kpis.sql
-- Prereq  : Run etl/load_data.py first to create the tables
-- =============================================================================


-- =============================================================================
-- SECTION 1 - KPI CARDS
-- =============================================================================

-- 1.1  Total Revenue
SELECT ROUND(SUM(revenue)::numeric, 2) AS total_revenue
FROM fact_orders;

-- 1.2  Total Gross Profit
SELECT ROUND(SUM(gross_profit)::numeric, 2) AS total_gross_profit
FROM fact_orders;

-- 1.3  Total Orders
SELECT COUNT(DISTINCT order_id) AS total_orders
FROM fact_orders;

-- 1.4  Average Ticket (revenue / orders)
SELECT ROUND((SUM(revenue) / NULLIF(COUNT(DISTINCT order_id), 0))::numeric, 2) AS avg_ticket
FROM fact_orders;

-- 1.5  Overall Margin %
SELECT ROUND((SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue), 0))::numeric, 2) AS overall_margin_pct
FROM fact_orders;


-- =============================================================================
-- SECTION 2 - SALES BY MONTH
-- =============================================================================

SELECT
    year_month,
    ROUND(SUM(revenue)::numeric,      2) AS revenue,
    ROUND(SUM(gross_profit)::numeric, 2) AS gross_profit,
    COUNT(DISTINCT order_id)             AS orders,
    ROUND((SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue), 0))::numeric, 2) AS margin_pct
FROM fact_orders
GROUP BY year_month
ORDER BY year_month;


-- =============================================================================
-- SECTION 3 - SALES BY CHANNEL
-- =============================================================================

WITH channel_agg AS (
    SELECT
        channel,
        ROUND(SUM(revenue)::numeric,      2) AS revenue,
        ROUND(SUM(gross_profit)::numeric, 2) AS gross_profit,
        COUNT(DISTINCT order_id)             AS orders
    FROM fact_orders
    GROUP BY channel
),
grand AS (SELECT SUM(revenue) AS total FROM channel_agg)
SELECT
    ca.channel,
    ca.revenue,
    ca.gross_profit,
    ca.orders,
    ROUND((ca.revenue * 100.0 / g.total)::numeric, 2) AS revenue_share_pct
FROM channel_agg ca, grand g
ORDER BY ca.revenue DESC;


-- =============================================================================
-- SECTION 4 - MARGIN BY CATEGORY
-- =============================================================================

SELECT
    p.category,
    ROUND(SUM(f.revenue)::numeric,      2) AS revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2) AS gross_profit,
    COUNT(DISTINCT f.order_id)             AS orders,
    ROUND((SUM(f.gross_profit) * 100.0 / NULLIF(SUM(f.revenue), 0))::numeric, 2) AS margin_pct
FROM fact_orders  f
JOIN dim_products p ON f.sku = p.sku
GROUP BY p.category
ORDER BY margin_pct DESC;


-- =============================================================================
-- SECTION 5 - TOP 10 CUSTOMERS BY REVENUE
-- =============================================================================

SELECT
    c.customer_id,
    c.name            AS customer_name,
    c.country,
    c.segment,
    ROUND(SUM(f.revenue)::numeric,      2) AS total_revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2) AS total_gross_profit,
    COUNT(DISTINCT f.order_id)             AS orders
FROM fact_orders   f
JOIN dim_customers c ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.name, c.country, c.segment
ORDER BY total_revenue DESC
LIMIT 10;


-- =============================================================================
-- SECTION 6 - TOP 10 PRODUCTS BY REVENUE
-- =============================================================================

SELECT
    p.sku,
    p.category,
    SUM(f.quantity)                        AS units_sold,
    ROUND(SUM(f.revenue)::numeric,      2) AS total_revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2) AS total_gross_profit,
    ROUND((SUM(f.gross_profit) * 100.0 / NULLIF(SUM(f.revenue), 0))::numeric, 2) AS margin_pct
FROM fact_orders  f
JOIN dim_products p ON f.sku = p.sku
GROUP BY p.sku, p.category
ORDER BY total_revenue DESC
LIMIT 10;


-- =============================================================================
-- SECTION 7 - SALES BY COUNTRY
-- =============================================================================

SELECT
    c.country,
    ROUND(SUM(f.revenue)::numeric,      2) AS revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2) AS gross_profit,
    COUNT(DISTINCT f.order_id)             AS orders
FROM fact_orders   f
JOIN dim_customers c ON f.customer_id = c.customer_id
GROUP BY c.country
ORDER BY revenue DESC;


-- =============================================================================
-- SECTION 8 - SALES BY SEGMENT
-- =============================================================================

SELECT
    c.segment,
    ROUND(SUM(f.revenue)::numeric,      2) AS revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2) AS gross_profit,
    COUNT(DISTINCT f.order_id)             AS orders,
    ROUND(AVG(f.revenue)::numeric,      2) AS avg_order_value
FROM fact_orders   f
JOIN dim_customers c ON f.customer_id = c.customer_id
GROUP BY c.segment
ORDER BY revenue DESC;


-- =============================================================================
-- SECTION 9 - MONTHLY GROWTH (Month-over-Month)
-- =============================================================================

WITH monthly AS (
    SELECT year_month, SUM(revenue) AS revenue
    FROM fact_orders
    GROUP BY year_month
)
SELECT
    m.year_month,
    ROUND(m.revenue::numeric, 2) AS revenue,
    ROUND(
        (m.revenue - LAG(m.revenue) OVER (ORDER BY m.year_month))
        * 100.0
        / NULLIF(LAG(m.revenue) OVER (ORDER BY m.year_month), 0),
        2
    ) AS mom_growth_pct
FROM monthly m
ORDER BY m.year_month;
