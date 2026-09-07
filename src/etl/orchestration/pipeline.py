"""
Top-level pipeline orchestration. Wraps every step in an audit.step_run
record (start/finish/status/counts) under one audit.pipeline_run, so
every execution is traceable after the fact via the audit tables.
"""
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from etl.extract.api_extract import extract_customers
from etl.extract.database_extract import extract_orders
from etl.transform.transformations import stage_customers, stage_orders
from etl.load.warehouse_loader import load_dim_customer, load_fact_orders
from etl.quality.data_quality import run_all_checks
from etl.utils.database import db_cursor
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def _start_pipeline_run(pipeline_name: str) -> str:
    run_id = str(uuid.uuid4())
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO audit_pipeline_run (pipeline_run_id, pipeline_name, status) VALUES (?, ?, 'RUNNING')",
            (run_id, pipeline_name),
        )
    return run_id


def _finish_pipeline_run(run_id: str, status: str, notes: str = "") -> None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE audit_pipeline_run SET finished_at = datetime('now'), status = ?, notes = ? WHERE pipeline_run_id = ?",
            (status, notes, run_id),
        )


@contextmanager
def _track_step(pipeline_run_id: str, step_name: str):
    """
    Context manager: creates an audit_step_run row, yields a dict the
    caller fills in with record counts, marks SUCCESS/FAILED on exit.
    """
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO audit_step_run (pipeline_run_id, step_name, status) VALUES (?, ?, 'RUNNING')",
            (pipeline_run_id, step_name),
        )
        step_run_id = cur.lastrowid

    counts = {"extracted": 0, "loaded": 0, "rejected": 0}
    try:
        yield counts
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE audit_step_run
                SET finished_at = datetime('now'), status = 'SUCCESS',
                    records_extracted = ?, records_loaded = ?, records_rejected = ?
                WHERE step_run_id = ?
                """,
                (counts["extracted"], counts["loaded"], counts["rejected"], step_run_id),
            )
        logger.info(f"Step '{step_name}' succeeded: {counts}")
    except Exception as exc:
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE audit_step_run
                SET finished_at = datetime('now'), status = 'FAILED', error_message = ?
                WHERE step_run_id = ?
                """,
                (str(exc), step_run_id),
            )
        logger.exception(f"Step '{step_name}' failed")
        raise


def run_pipeline(pipeline_name: str = "customers_orders_etl") -> dict:
    """
    Runs the full extract -> stage -> load -> quality pipeline once.
    Returns a summary dict; also fully recorded in the audit_* tables.
    """
    run_id = _start_pipeline_run(pipeline_name)
    logger.info(f"Starting pipeline run {run_id} ({pipeline_name})")
    summary = {"pipeline_run_id": run_id, "steps": {}}

    try:
        with _track_step(run_id, "extract_customers") as counts:
            counts["extracted"] = extract_customers(run_id)
            counts["loaded"] = counts["extracted"]
        summary["steps"]["extract_customers"] = counts

        with _track_step(run_id, "extract_orders") as counts:
            counts["extracted"] = extract_orders(run_id)
            counts["loaded"] = counts["extracted"]
        summary["steps"]["extract_orders"] = counts

        with _track_step(run_id, "stage_customers") as counts:
            loaded, rejected = stage_customers(run_id)
            counts["loaded"], counts["rejected"] = loaded, rejected
        summary["steps"]["stage_customers"] = counts

        with _track_step(run_id, "stage_orders") as counts:
            loaded, rejected = stage_orders(run_id)
            counts["loaded"], counts["rejected"] = loaded, rejected
        summary["steps"]["stage_orders"] = counts

        with _track_step(run_id, "load_dim_customer") as counts:
            inserted, updated = load_dim_customer(run_id)
            counts["loaded"] = inserted + updated
        summary["steps"]["load_dim_customer"] = counts

        with _track_step(run_id, "load_fact_orders") as counts:
            loaded, orphaned = load_fact_orders(run_id)
            counts["loaded"], counts["rejected"] = loaded, orphaned
        summary["steps"]["load_fact_orders"] = counts

        issues = run_all_checks(run_id)
        summary["quality_issues"] = [
            {"check": i.check_name, "severity": i.severity, "message": i.message} for i in issues
        ]

        has_errors = any(i.severity == "ERROR" for i in issues)
        status = "PARTIAL" if has_errors else "SUCCESS"
        _finish_pipeline_run(run_id, status, notes=f"{len(issues)} quality issue(s) found")
        summary["status"] = status

    except Exception as exc:
        _finish_pipeline_run(run_id, "FAILED", notes=str(exc))
        summary["status"] = "FAILED"
        summary["error"] = str(exc)
        raise

    logger.info(f"Pipeline run {run_id} finished with status {summary['status']}")
    return summary
