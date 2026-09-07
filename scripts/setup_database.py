"""
Sets up the local database for the current environment (ETL_ENV,
defaults to 'dev'): runs every .sql file in sql/ddl/ in order.

Usage:
    python scripts/setup_database.py
    ETL_ENV=test python scripts/setup_database.py
"""
import sqlite3
from pathlib import Path

from etl.config.settings import get_settings

DDL_DIR = Path("sql/ddl")


def main():
    settings = get_settings()
    db_path = Path(settings.database.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    ddl_files = sorted(DDL_DIR.glob("*.sql"))
    if not ddl_files:
        raise FileNotFoundError(f"No .sql files found in {DDL_DIR}")

    for path in ddl_files:
        print(f"Running {path} ...")
        conn.executescript(path.read_text())

    conn.commit()

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"\nEnvironment: {settings.environment}")
    print(f"Database ready at: {db_path.resolve()}")
    print(f"Tables ({len(tables)}): {', '.join(tables)}")


if __name__ == "__main__":
    main()
