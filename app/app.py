"""
app.py – RoseAmor Order Registration Web App
=============================================
A minimal Flask application that allows users to register new orders
with basic validation and stores them in a PostgreSQL database.

Connection config (env vars with defaults):
  PG_HOST     = localhost
  PG_PORT     = 5432
  PG_DBNAME   = test
  PG_USER     = dev
  PG_PASSWORD = test

Usage:
    cd app
    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

import os
from datetime import datetime
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "roseamor-dev-secret-change-in-prod")

VALID_CHANNELS = {"ecommerce", "retail", "wholesale", "export"}


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ.get("PG_HOST",     "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        dbname=os.environ.get("PG_DBNAME", "test"),
        user=os.environ.get("PG_USER",     "dev"),
        password=os.environ.get("PG_PASSWORD", "test"),
    )


def get_db():
    conn = _pg_conn()
    return conn


def init_db():
    """Create the new_orders table if it does not yet exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS new_orders (
            id           SERIAL       PRIMARY KEY,
            order_id     TEXT         NOT NULL UNIQUE,
            customer_id  TEXT         NOT NULL,
            sku          TEXT         NOT NULL,
            quantity     INTEGER      NOT NULL CHECK (quantity > 0),
            unit_price   DOUBLE PRECISION NOT NULL CHECK (unit_price > 0),
            order_date   DATE         NOT NULL,
            channel      TEXT         NOT NULL,
            created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_order(data: dict) -> dict:
    """
    Validate form data.
    Returns a dict of {field: error_message}.
    Empty dict means no errors.
    """
    errors = {}

    # Required text fields
    for field, label in [
        ("order_id",    "Order ID"),
        ("customer_id", "Customer ID"),
        ("sku",         "SKU"),
        ("order_date",  "Fecha del pedido"),
        ("channel",     "Canal"),
    ]:
        if not data.get(field, "").strip():
            errors[field] = f"{label} es obligatorio."

    # Quantity: required, integer, > 0
    qty_str = data.get("quantity", "").strip()
    if not qty_str:
        errors["quantity"] = "La cantidad es obligatoria."
    else:
        try:
            qty = int(qty_str)
            if qty <= 0:
                errors["quantity"] = "La cantidad debe ser mayor a 0."
        except ValueError:
            errors["quantity"] = "La cantidad debe ser un número entero."

    # Unit price: required, numeric, > 0
    price_str = data.get("unit_price", "").strip()
    if not price_str:
        errors["unit_price"] = "El precio unitario es obligatorio."
    else:
        try:
            price = float(price_str)
            if price <= 0:
                errors["unit_price"] = "El precio debe ser mayor a 0."
        except ValueError:
            errors["unit_price"] = "El precio debe ser un número válido (ej. 19.99)."

    # Date format: YYYY-MM-DD
    date_str = data.get("order_date", "").strip()
    if date_str and "order_date" not in errors:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            errors["order_date"] = "Formato de fecha inválido. Use YYYY-MM-DD."

    # Channel: must be in allowed list
    channel = data.get("channel", "").strip().lower()
    if channel and channel not in VALID_CHANNELS:
        errors["channel"] = f"Canal inválido. Opciones: {', '.join(sorted(VALID_CHANNELS))}."

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", errors={}, form_data={})


@app.route("/orders", methods=["POST"])
def create_order():
    form_data = {
        "order_id":   request.form.get("order_id",   "").strip(),
        "customer_id":request.form.get("customer_id","").strip(),
        "sku":        request.form.get("sku",         "").strip(),
        "quantity":   request.form.get("quantity",    "").strip(),
        "unit_price": request.form.get("unit_price",  "").strip(),
        "order_date": request.form.get("order_date",  "").strip(),
        "channel":    request.form.get("channel",     "").strip().lower(),
    }

    errors = validate_order(form_data)
    if errors:
        return render_template("index.html", errors=errors, form_data=form_data), 422

    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            """
            INSERT INTO new_orders
                (order_id, customer_id, sku, quantity, unit_price, order_date, channel)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                form_data["order_id"],
                form_data["customer_id"],
                form_data["sku"],
                int(form_data["quantity"]),
                float(form_data["unit_price"]),
                form_data["order_date"],
                form_data["channel"],
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        errors["order_id"] = f"El Order ID '{form_data['order_id']}' ya existe en la base de datos."
        return render_template("index.html", errors=errors, form_data=form_data), 409

    return render_template("index.html", errors={}, form_data={}, success=True)


@app.route("/orders/list", methods=["GET"])
def list_orders():
    """Read-only view of all registered orders."""
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM new_orders ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("list.html", orders=rows)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print(
        "Database: "
        f"{os.environ.get('PG_DBNAME', 'test')}"
        " | host: "
        f"{os.environ.get('PG_HOST', 'localhost')}:{os.environ.get('PG_PORT', '5432')}"
    )
    app.run(debug=True, host="127.0.0.1", port=5000)
