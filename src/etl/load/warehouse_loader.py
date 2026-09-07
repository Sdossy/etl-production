"""
Loads staging tables into the dw layer: dim_customer (SCD Type 2)
and fact_orders (plain insert/replace keyed on order_id).
"""
from etl.utils.database import db_cursor
from etl.utils.logger import get_logger

logger = get_logger(__name__)

# Columns compared to decide whether a customer's dimension row has changed
_SCD_TRACKED_COLUMNS = ["first_name", "last_name", "email", "phone", "city", "state", "postal_code", "country"]


def load_dim_customer(pipeline_run_id: str) -> tuple[int, int]:
    """
    SCD Type 2 upsert from stg_customers into dim_customer:
      - brand new customer_id -> insert new current row
      - existing customer_id, tracked columns changed -> close old row, insert new current row
      - existing customer_id, nothing changed -> no-op
    Returns (inserted_count, updated_count).
    """
    inserted, updated = 0, 0
    with db_cursor() as cur:
        cur.execute("SELECT * FROM stg_customers WHERE pipeline_run_id = ?", (pipeline_run_id,))
        staged = cur.fetchall()

        for row in staged:
            cur.execute(
                "SELECT * FROM dim_customer WHERE customer_id = ? AND is_current = 1",
                (row["customer_id"],),
            )
            current = cur.fetchone()

            if current is None:
                cur.execute(
                    """
                    INSERT INTO dim_customer (
                        customer_id, first_name, last_name, email, phone,
                        city, state, postal_code, country
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["customer_id"], row["first_name"], row["last_name"],
                        row["email"], row["phone"], row["city"], row["state"],
                        row["postal_code"], row["country"],
                    ),
                )
                inserted += 1
                continue

            changed = any(row[col] != current[col] for col in _SCD_TRACKED_COLUMNS)
            if not changed:
                continue

            cur.execute(
                """
                UPDATE dim_customer
                SET is_current = 0, end_date = date('now'), updated_at = datetime('now')
                WHERE customer_sk = ?
                """,
                (current["customer_sk"],),
            )
            cur.execute(
                """
                INSERT INTO dim_customer (
                    customer_id, first_name, last_name, email, phone,
                    city, state, postal_code, country
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["customer_id"], row["first_name"], row["last_name"],
                    row["email"], row["phone"], row["city"], row["state"],
                    row["postal_code"], row["country"],
                ),
            )
            updated += 1

    logger.info(f"dim_customer: {inserted} inserted, {updated} updated (SCD2)")
    return inserted, updated


def load_fact_orders(pipeline_run_id: str) -> tuple[int, int]:
    """
    Insert/replace fact_orders rows from stg_orders, resolving customer_sk
    via the current dim_customer row. Orders whose customer_id has no
    matching current dim row are skipped (orphans -- surfaced separately
    by the referential-integrity data-quality check).
    Returns (loaded_count, orphaned_count).
    """
    loaded, orphaned = 0, 0
    with db_cursor() as cur:
        cur.execute("SELECT * FROM stg_orders WHERE pipeline_run_id = ?", (pipeline_run_id,))
        staged = cur.fetchall()

        for row in staged:
            cur.execute(
                "SELECT customer_sk FROM dim_customer WHERE customer_id = ? AND is_current = 1",
                (row["customer_id"],),
            )
            dim_row = cur.fetchone()

            if dim_row is None:
                logger.warning(f"Order {row['order_id']} references unknown customer_id {row['customer_id']}")
                orphaned += 1
                continue

            cur.execute(
                """
                INSERT INTO fact_orders (
                    order_id, customer_sk, order_date, status, subtotal,
                    tax, total_amount, currency, pipeline_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    customer_sk=excluded.customer_sk,
                    order_date=excluded.order_date,
                    status=excluded.status,
                    subtotal=excluded.subtotal,
                    tax=excluded.tax,
                    total_amount=excluded.total_amount,
                    currency=excluded.currency,
                    loaded_at=datetime('now'),
                    pipeline_run_id=excluded.pipeline_run_id
                """,
                (
                    row["order_id"], dim_row["customer_sk"], row["order_date"],
                    row["status"], row["subtotal"], row["tax"], row["total_amount"],
                    row["currency"], pipeline_run_id,
                ),
            )
            loaded += 1

    logger.info(f"fact_orders: {loaded} loaded, {orphaned} orphaned (skipped)")
    return loaded, orphaned
