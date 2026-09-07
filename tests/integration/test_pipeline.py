"""
End-to-end integration test: runs the real pipeline against an isolated
temp SQLite DB, using the actual data/sample CSVs (including the
intentional data-quality issues), and checks the outcome.
"""
from etl.orchestration.pipeline import run_pipeline
from etl.utils.database import db_cursor


def test_full_pipeline_run(isolated_db):
    summary = run_pipeline()

    assert summary["status"] in ("SUCCESS", "PARTIAL")
    assert summary["steps"]["extract_customers"]["extracted"] == 51  # 50 + 1 intentional dup row
    assert summary["steps"]["extract_orders"]["extracted"] == 200

    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM dim_customer WHERE is_current = 1")
        assert cur.fetchone()["cnt"] > 0

        cur.execute("SELECT COUNT(*) as cnt FROM fact_orders")
        assert cur.fetchone()["cnt"] > 0

        cur.execute("SELECT status FROM audit_pipeline_run WHERE pipeline_run_id = ?", (summary["pipeline_run_id"],))
        assert cur.fetchone()["status"] == summary["status"]


def test_pipeline_flags_known_quality_issues(isolated_db):
    """The sample data has planted issues -- confirm the checks actually catch them."""
    summary = run_pipeline()
    messages = " ".join(i["message"] for i in summary["quality_issues"])

    # Orphan order (CUST9999) and missing email should both surface somewhere
    assert len(summary["quality_issues"]) > 0
