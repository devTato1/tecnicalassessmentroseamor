# RoseAmor - Technical Test Documentation

This repository is migrated to PostgreSQL.

Default database configuration used by ETL and app:
- Database: `test`
- User: `dev`
- Password: `test`
- Host: `localhost`
- Port: `5432`

These values can be overridden with environment variables:
- `PG_HOST`, `PG_PORT`, `PG_DBNAME`, `PG_USER`, `PG_PASSWORD`

---

## 1. Project Structure

```text
rosemoretecnicaltest/
  data/
    customers.csv
    orders.csv
    products.csv
  etl/
    load_data.py
  sql/
    01_staging.sql
    02_consumption.sql
    kpis.sql
  app/
    app.py
    requirements.txt
    templates/
      index.html
      list.html
  README.md
```

---

## 2. Architecture and Data Flow

`raw CSV -> staging tables -> dimensional model -> BI dashboard`

1. Raw files are read from `data/`.
2. `etl/load_data.py` creates and loads:
   - `stg_orders`
   - `stg_customers`
   - `stg_products`
3. Consumption model is generated:
   - `dim_customers`
   - `dim_products`
   - `fact_orders`
   - `v_orders_full`
4. Power BI/Looker consumes `v_orders_full` (or the star model).

---

## 3. Data Cleaning Rules

### orders.csv
- Duplicate `order_id`: keep first occurrence, flag `_is_duplicate=1` for later rows.
- Negative `quantity`: flag `_negative_qty=1` and exclude from `fact_orders`.
- Empty `unit_price`: flag `_null_price=1` and exclude from `fact_orders`.
- `order_date`: normalized to `DATE`.
- `channel`: normalized to lowercase.

### customers.csv
- Empty `country` -> `'Unknown'`
- Empty `segment` -> `'Unknown'`
- `created_at` normalized to `DATE`.

### products.csv
- Empty `category` -> `'Unknown'`
- `active`: mapped to `1/0`.

---

## 4. Data Model

### Dimensions
- `dim_customers(customer_id PK, name, country, segment, created_at)`
- `dim_products(sku PK, category, cost, active)`

### Fact
- `fact_orders(order_id PK, customer_id, sku, quantity, unit_price, order_date, year, month, year_month, channel, revenue, gross_profit, margin_pct)`

### Metrics
- `revenue = quantity * unit_price`
- `gross_profit = quantity * (unit_price - cost)`
- `margin_pct = (unit_price - cost) / unit_price * 100`

---

## 5. How to Run

### 5.1 Prerequisites
- Python 3.11+
- PostgreSQL installed and running
- Database/user available:
  - DB: `test`
  - User: `dev`
  - Password: `test`

If database does not exist:

```sql
CREATE DATABASE test;
```

If user does not exist:

```sql
CREATE USER dev WITH PASSWORD 'test';
GRANT ALL PRIVILEGES ON DATABASE test TO dev;
```

### 5.2 Install dependencies

```bash
cd app
pip install -r requirements.txt
cd ..
```

### 5.3 Run ETL

```bash
python etl/load_data.py
```

Expected: tables in PostgreSQL are created/updated.

### 5.4 Run KPI SQL

```bash
psql -h localhost -p 5432 -U dev -d test -f sql/kpis.sql
```

### 5.5 Run web app

```bash
cd app
python app.py
```

Open: `http://127.0.0.1:5000`

Orders are saved in PostgreSQL table: `public.new_orders`.

---

## 6. BI Dashboard Requirements Mapping

Current status:
- Data model is ready in PostgreSQL (`fact_orders`, `dim_*`, `v_orders_full`).
- The `.pbix` file still needs to be created in Power BI Desktop.

Build it in Power BI Desktop (all with Power BI):

1. Open Power BI Desktop.
2. Get Data -> PostgreSQL database.
3. Server: `localhost:5432`
4. Database: `test`
5. User/password: `dev` / `test`
6. In Navigator, load `v_orders_full` (recommended) or `fact_orders + dim_*`.
7. Save the report as `RoseAmor_Dashboard.pbix` in the repo root.

Recommended DAX measures (create in Power BI):

```DAX
Total Sales = SUM(v_orders_full[revenue])

Total Margin = SUM(v_orders_full[gross_profit])

Order Count = DISTINCTCOUNT(v_orders_full[order_id])

Average Ticket = DIVIDE([Total Sales], [Order Count], 0)

Margin % = DIVIDE([Total Margin], [Total Sales], 0)
```

Required visuals:
- KPI card: `Total Sales`
- KPI card: `Total Margin`
- KPI card: `Order Count`
- KPI card: `Average Ticket`
- Line chart: Axis `year_month`, Values `Total Sales`
- Column chart: Axis `channel`, Values `Total Sales`
- Bar chart: Axis `category`, Values `Total Margin` (or `Margin %`)
- Bar chart (Top N 10): Axis `customer_name`, Values `Total Sales`
- Bar chart (Top N 10): Axis `sku`, Values `SUM(quantity)` or `Total Sales`

Required slicers:
- `order_date` (between)
- `channel`
- `category`
- `country`

Publish/delivery:
- Deliver `RoseAmor_Dashboard.pbix` in the repository.
- If using Power BI Service, add report link in this README.

---

## 7. Web App (Order Registration)

Form fields:
- `order_id`, `customer_id`, `sku`, `quantity`, `unit_price`, `order_date`, `channel`

Validations:
- Required fields
- Non-negative and valid numeric values
- Date format `YYYY-MM-DD`
- Channel in `{ecommerce, retail, wholesale, export}`
- Unique `order_id` (database constraint)

---

## 8. Refresh Process (New CSV)

1. Replace files in `data/`.
2. Re-run ETL:

```bash
python etl/load_data.py
```

3. Refresh Power BI dataset.

The ETL is idempotent for full reload because it drops/recreates staging and consumption tables each run.
