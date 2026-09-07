"""
Order extraction. In production this would query a source database
(see the commented sqlalchemy-style stub in _fetch_from_source_db);
for now it reads data/sample/orders.csv so the pipeline is fully
runnable without an external database. Swap _fetch_from_source_db's
body for a real query when a source system is available.
"""
import csv
import json
from pathlib import Path
from typing import Any

from etl.config.settings import get_settings
from etl.utils.database import db_cursor
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def _fetch_from_source_db(source_path: Path) -> list[dict[str, Any]]:
    """Stand-in for a real source-database query. Reads a local CSV."""
    # Real version might look like:
    #   with source_engine.connect() as conn:
    #       result = conn.execute(text("SELECT * FROM orders WHERE updated_at > :since"), {"since": since})
    #       return [dict(row) for row in result]
    with open(source_path, newline="") as f:
        return list(csv.DictReader(f))


def extract_orders(pipeline_run_id: str) -> int:
    """
    Pull order records and land them (as raw JSON) into raw_orders.
    Returns the number of records extracted.
    """
    settings = get_settings()
    source_path = Path(settings.paths.sample_data_dir) / "orders.csv"

    if not source_path.exists():
        raise FileNotFoundError(f"No order source file found at {source_path}")

    records = _fetch_from_source_db(source_path)
    logger.info(f"Extracted {len(records)} order records from {source_path}")

    with db_cursor() as cur:
        for record in records:
            cur.execute(
                """
                INSERT INTO raw_orders (source_system, payload, pipeline_run_id)
                VALUES (?, ?, ?)
                """,
                ("sample_db", json.dumps(record), pipeline_run_id),
            )

    return len(records)
