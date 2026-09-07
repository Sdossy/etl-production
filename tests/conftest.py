"""
Shared pytest fixtures. `isolated_db` points etl.config.settings at a
throwaway SQLite file for the duration of a test, runs the DDL against
it, and cleans up afterward -- so tests never touch data/processed/etl_production.db.
"""
import sqlite3
from pathlib import Path

import pytest

from etl.config.settings import Settings, DatabaseSettings, PathSettings, LoggingSettings, PipelineSettings
import etl.config.settings as settings_module

REPO_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = REPO_ROOT / "sql" / "ddl"


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_etl.db"
    log_path = tmp_path / "test.log"

    test_settings = Settings(
        environment="test",
        database=DatabaseSettings(path=str(db_path), timeout_seconds=10),
        paths=PathSettings(
            raw_data_dir=str(REPO_ROOT / "data" / "sample"),
            sample_data_dir=str(REPO_ROOT / "data" / "sample"),
            log_dir=str(tmp_path),
        ),
        logging=LoggingSettings(level="WARNING", log_to_file=False, log_file=str(log_path)),
        pipeline=PipelineSettings(batch_size=50, retry_attempts=1, retry_backoff_seconds=0),
    )

    # Patch the module-level cache rather than the get_settings function itself:
    # other modules did `from etl.config.settings import get_settings`, binding
    # their own reference to the function object. That function reads the
    # module's global _settings_cache on every call, so patching the cache
    # (not the function) is what actually propagates everywhere.
    monkeypatch.setattr(settings_module, "_settings_cache", test_settings)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    for ddl_file in sorted(DDL_DIR.glob("*.sql")):
        conn.executescript(ddl_file.read_text())
    conn.commit()
    conn.close()

    yield db_path
