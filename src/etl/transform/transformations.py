"""
Pure cleaning/typing functions plus the raw -> staging transform step.
Keeping the cleaning functions pure (no DB access) makes them easy to
unit test in isolation -- see tests/unit/test_transformations.py.
"""
import json
from typing import Any

from etl.utils.database import db_cursor
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def clean_string(value: Any) -> str | None:
    """Trim whitespace, collapse empty strings to None."""
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def clean_email(value: Any) -> str | None:
    """Lowercase + trim; empty -> None."""
    cleaned = clean_string(value)
    return cleaned.lower() if cleaned else None


def clean_numeric(value: Any) -> float | None:
    """Coerce to float; blank/invalid -> None rather than raising."""
    cleaned = clean_string(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def transform_customer_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw customer payload dict to typed staging columns."""
    return {
        "customer_id": clean_string(raw.get("customer_id")),
        "first_name": clean_string(raw.get("first_name")),
        "last_name": clean_string(raw.get("last_name")),
        "email": clean_email(raw.get("email")),
        "phone": clean_string(raw.get("phone")),
        "address_line1": clean_string(raw.get("address_line1")),
        "city": clean_string(raw.get("city")),
        "state": clean_string(raw.get("state")),
        "postal_code": clean_string(raw.get("postal_code")),
        "country": clean_string(raw.get("country")),
        "created_at": clean_string(raw.get("created_at")),
        "updated_at": clean_string(raw.get("updated_at")),
    }


def transform_order_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw order payload dict to typed staging columns."""
    return {
        "order_id": clean_string(raw.get("order_id")),
        "customer_id": clean_string(raw.get("customer_id")),
        "order_date": clean_string(raw.get("order_date")),
        "status": clean_string(raw.get("status")),
        "subtotal": clean_numeric(raw.get("subtotal")),
        "tax": clean_numeric(raw.get("tax")),
        "total_amount": clean_numeric(raw.get("total_amount")),
        "currency": clean_string(raw.get("currency")) or "USD",
        "created_at": clean_string(raw.get("created_at")),
        "updated_at": clean_string(raw.get("updated_at")),
    }


def stage_customers(pipeline_run_id: str) -> tuple[int, int]:
    """
    Read this run's raw_customers rows, clean them, and upsert into
    stg_customers. Rows missing a customer_id are rejected (can't key on nothing).
    Returns (loaded_count, rejected_count).
    """
    loaded, rejected = 0, 0
    with db_cursor() as cur:
        cur.execute(
            "SELECT payload FROM raw_customers WHERE pipeline_run_id = ?",
            (pipeline_run_id,),
        )
        raw_rows = cur.fetchall()

        for row in raw_rows:
            raw = json.loads(row["payload"])
            record = transform_customer_record(raw)

            if not record["customer_id"]:
                logger.warning(f"Rejecting customer record with no customer_id: {raw}")
                rejected += 1
                continue

            cur.execute(
                """
                INSERT INTO stg_customers (
                    customer_id, first_name, last_name, email, phone,
                    address_line1, city, state, postal_code, country,
                    created_at, updated_at, pipeline_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    email=excluded.email,
                    phone=excluded.phone,
                    address_line1=excluded.address_line1,
                    city=excluded.city,
                    state=excluded.state,
                    postal_code=excluded.postal_code,
                    country=excluded.country,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    loaded_at=datetime('now'),
                    pipeline_run_id=excluded.pipeline_run_id
                """,
                (
                    record["customer_id"], record["first_name"], record["last_name"],
                    record["email"], record["phone"], record["address_line1"],
                    record["city"], record["state"], record["postal_code"],
                    record["country"], record["created_at"], record["updated_at"],
                    pipeline_run_id,
                ),
            )
            loaded += 1

    logger.info(f"Staged customers: {loaded} loaded, {rejected} rejected")
    return loaded, rejected


def stage_orders(pipeline_run_id: str) -> tuple[int, int]:
    """
    Read this run's raw_orders rows, clean them, and upsert into stg_orders.
    Rows missing order_id, customer_id, or total_amount are rejected.
    Returns (loaded_count, rejected_count).
    """
    loaded, rejected = 0, 0
    with db_cursor() as cur:
        cur.execute(
            "SELECT payload FROM raw_orders WHERE pipeline_run_id = ?",
            (pipeline_run_id,),
        )
        raw_rows = cur.fetchall()

        for row in raw_rows:
            raw = json.loads(row["payload"])
            record = transform_order_record(raw)

            if not record["order_id"] or not record["customer_id"] or record["total_amount"] is None:
                logger.warning(f"Rejecting order record (missing required field): {raw}")
                rejected += 1
                continue

            cur.execute(
                """
                INSERT INTO stg_orders (
                    order_id, customer_id, order_date, status, subtotal,
                    tax, total_amount, currency, created_at, updated_at,
                    pipeline_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    customer_id=excluded.customer_id,
                    order_date=excluded.order_date,
                    status=excluded.status,
                    subtotal=excluded.subtotal,
                    tax=excluded.tax,
                    total_amount=excluded.total_amount,
                    currency=excluded.currency,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    loaded_at=datetime('now'),
                    pipeline_run_id=excluded.pipeline_run_id
                """,
                (
                    record["order_id"], record["customer_id"], record["order_date"],
                    record["status"], record["subtotal"], record["tax"],
                    record["total_amount"], record["currency"],
                    record["created_at"], record["updated_at"], pipeline_run_id,
                ),
            )
            loaded += 1

    logger.info(f"Staged orders: {loaded} loaded, {rejected} rejected")
    return loaded, rejected
