"""
One-off script to initialize the SQLite database from the DDL files
in sql/ddl/. Run from the project root:

    python scripts/init_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/processed/etl_production.db")
DDL_DIR = Path("sql/ddl")
DDL_FILES = [
    "001_create_schemas.sql",
    "002_create_tables.sql",
    "003_create_audit_tables.sql",
]

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    for filename in DDL_FILES:
        path = DDL_DIR / filename
        print(f"Running {path} ...")
        sql = path.read_text()
        conn.executescript(sql)

    conn.commit()

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"\nDatabase created at: {DB_PATH.resolve()}")
    print(f"Tables ({len(tables)}):")
    for t in tables:
        print(f"  - {t}")

if __name__ == "__main__":
    main()
