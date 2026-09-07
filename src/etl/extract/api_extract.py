"""
Customer extraction. In production this would call a real customer API
(see the `requests`-based stub in _fetch_from_api below); for now it
reads data/sample/customers.csv or data/raw/customers.csv so the pipeline
is fully runnable without external dependencies. Swap _fetch_from_api's
body for a real HTTP call when a source system is available -- everything
downstream (raw loading, staging, dims) stays the same either way.
"""
import csv
import json
from pathlib import Path
from typing import Any

from etl.config.settings import get_settings
from etl.utils.database import db_cursor
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def _fetch_from_api(source_path: Path) -> list[dict[str, Any]]:
    """Stand-in for a real API call. Reads a local CSV as the 'response'."""
    with open(source_path, newline="") as f:
        return list(csv.DictReader(f))


def extract_customers(pipeline_run_id: str) -> int:
    """
    Pull customer records and land them (as raw JSON) into raw_customers.
    Returns the number of records extracted.
    """
    settings = get_settings()
    source_path = Path(settings.paths.sample_data_dir) / "customers.csv"

    if not source_path.exists():
        raise FileNotFoundError(f"No customer source file found at {source_path}")

    records = _fetch_from_api(source_path)
    logger.info(f"Extracted {len(records)} customer records from {source_path}")

    with db_cursor() as cur:
        for record in records:
            cur.execute(
                """
                INSERT INTO raw_customers (source_system, payload, pipeline_run_id)
                VALUES (?, ?, ?)
                """,
                ("sample_api", json.dumps(record), pipeline_run_id),
            )

    return len(records)
