"""
Data-quality checks: null checks, duplicate checks, referential
integrity, and row-count sanity checks. Each check returns a
QualityIssue list (empty = passed) rather than raising, so the
pipeline can run every check and report all findings at once.
"""
from dataclasses import dataclass

from etl.utils.database import db_cursor
from etl.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QualityIssue:
    check_name: str
    severity: str  # 'WARNING' or 'ERROR'
    message: str


def null_check(table: str, required_columns: list[str]) -> list[QualityIssue]:
    """Flags rows where any required column is NULL."""
    issues = []
    with db_cursor() as cur:
        for col in required_columns:
            cur.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE {col} IS NULL")
            count = cur.fetchone()["cnt"]
            if count > 0:
                issues.append(QualityIssue(
                    check_name="null_check",
                    severity="ERROR",
                    message=f"{table}.{col} has {count} NULL value(s)",
                ))
    return issues


def duplicate_check(table: str, key_columns: list[str], where: str = "") -> list[QualityIssue]:
    """Flags duplicate non-null values on the given key column(s). Optional raw `where` clause, e.g. "email IS NOT NULL"."""
    cols = ", ".join(key_columns)
    where_clause = f"WHERE {where}" if where else ""
    with db_cursor() as cur:
        cur.execute(f"""
            SELECT {cols}, COUNT(*) as cnt
            FROM {table}
            {where_clause}
            GROUP BY {cols}
            HAVING COUNT(*) > 1
        """)
        dupes = cur.fetchall()

    if not dupes:
        return []
    return [QualityIssue(
        check_name="duplicate_check",
        severity="WARNING",
        message=f"{table} has {len(dupes)} duplicate value(s) on ({cols})",
    )]


def referential_integrity_check() -> list[QualityIssue]:
    """Flags fact_orders rows and stg_orders rows with no matching customer."""
    issues = []
    with db_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt FROM stg_orders so
            LEFT JOIN dim_customer dc
                ON so.customer_id = dc.customer_id AND dc.is_current = 1
            WHERE dc.customer_sk IS NULL
        """)
        orphaned = cur.fetchone()["cnt"]
        if orphaned > 0:
            issues.append(QualityIssue(
                check_name="referential_integrity_check",
                severity="WARNING",
                message=f"{orphaned} stg_orders row(s) reference a customer_id not present in dim_customer",
            ))
    return issues


def row_count_check(raw_table: str, staged_table: str, pipeline_run_id: str, tolerance: float = 0.0) -> list[QualityIssue]:
    """
    Compares raw vs staged row counts for this pipeline run. Some gap is
    expected (rejected records) -- tolerance is the allowed fraction lost
    (0.0 = staged count must equal raw count exactly).
    """
    with db_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) as cnt FROM {raw_table} WHERE pipeline_run_id = ?", (pipeline_run_id,))
        raw_count = cur.fetchone()["cnt"]
        cur.execute(f"SELECT COUNT(*) as cnt FROM {staged_table} WHERE pipeline_run_id = ?", (pipeline_run_id,))
        staged_count = cur.fetchone()["cnt"]

    if raw_count == 0:
        return []

    loss_fraction = 1 - (staged_count / raw_count)
    if loss_fraction > tolerance:
        return [QualityIssue(
            check_name="row_count_check",
            severity="WARNING",
            message=(
                f"{raw_table} -> {staged_table}: {raw_count} raw vs {staged_count} staged "
                f"({loss_fraction:.1%} loss, tolerance {tolerance:.1%})"
            ),
        )]
    return []


def run_all_checks(pipeline_run_id: str) -> list[QualityIssue]:
    """Runs the full suite and returns every issue found (empty = all clean)."""
    issues: list[QualityIssue] = []

    issues += null_check("stg_customers", ["customer_id"])
    issues += null_check("stg_orders", ["order_id", "customer_id", "total_amount"])
    issues += duplicate_check("stg_customers", ["email"], where="email IS NOT NULL")
    issues += referential_integrity_check()
    issues += row_count_check("raw_customers", "stg_customers", pipeline_run_id, tolerance=0.05)
    issues += row_count_check("raw_orders", "stg_orders", pipeline_run_id, tolerance=0.05)

    for issue in issues:
        log_fn = logger.error if issue.severity == "ERROR" else logger.warning
        log_fn(f"[{issue.check_name}] {issue.message}")

    return issues
