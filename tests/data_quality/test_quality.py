"""Tests for the data-quality check functions against a small isolated DB."""
from etl.utils.database import db_cursor
from etl.quality.data_quality import null_check, duplicate_check, referential_integrity_check


def _seed_minimal_data(pipeline_run_id="test-run"):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO stg_customers (customer_id, email, pipeline_run_id) VALUES (?, ?, ?)",
            ("CUST0001", "a@example.com", pipeline_run_id),
        )
        cur.execute(
            "INSERT INTO stg_customers (customer_id, email, pipeline_run_id) VALUES (?, ?, ?)",
            ("CUST0002", "a@example.com", pipeline_run_id),  # duplicate email
        )
        cur.execute(
            "INSERT INTO stg_orders (order_id, customer_id, total_amount, pipeline_run_id) VALUES (?, ?, ?, ?)",
            ("ORD0001", "CUST9999", 10.0, pipeline_run_id),  # orphan: no matching customer
        )


def test_null_check_passes_when_no_nulls(isolated_db):
    _seed_minimal_data()
    issues = null_check("stg_customers", ["customer_id"])
    assert issues == []


def test_null_check_flags_nulls(isolated_db):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO stg_orders (order_id, customer_id, total_amount) VALUES (?, ?, NULL)",
            ("ORD0002", "CUST0001"),
        )
    issues = null_check("stg_orders", ["total_amount"])
    assert len(issues) == 1
    assert "total_amount" in issues[0].message


def test_duplicate_check_flags_duplicate_emails(isolated_db):
    _seed_minimal_data()
    issues = duplicate_check("stg_customers", ["email"], where="email IS NOT NULL")
    assert len(issues) == 1


def test_referential_integrity_check_flags_orphan_order(isolated_db):
    _seed_minimal_data()
    issues = referential_integrity_check()
    assert len(issues) == 1
    assert "1 stg_orders row" in issues[0].message
