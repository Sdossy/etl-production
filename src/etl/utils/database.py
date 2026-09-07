"""
SQLite connection helper. All pipeline code should get connections
through get_connection() rather than calling sqlite3.connect() directly,
so foreign keys, row factory, and the db path all stay consistent.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from etl.config.settings import get_settings


def get_connection() -> sqlite3.Connection:
    settings = get_settings()
    db_path = Path(settings.database.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=settings.database.timeout_seconds)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    """
    Yields a cursor, commits on clean exit, rolls back on exception,
    always closes the connection.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
