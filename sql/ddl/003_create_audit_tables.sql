-- 003_create_audit_tables.sql  (SQLite)
-- Audit/logging tables: one row per pipeline run, plus per-step
-- row-count and error detail. Run after 001 and 002.
--
-- Note: SQLite has no gen_random_uuid(). Generate the pipeline_run_id
-- in Python (e.g. str(uuid.uuid4())) and pass it in on INSERT.

CREATE TABLE IF NOT EXISTS audit_pipeline_run (
    pipeline_run_id TEXT PRIMARY KEY,
    pipeline_name   TEXT NOT NULL,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'RUNNING'
                        CHECK (status IN ('RUNNING','SUCCESS','FAILED','PARTIAL')),
    triggered_by    TEXT DEFAULT 'manual',
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS audit_step_run (
    step_run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id TEXT NOT NULL REFERENCES audit_pipeline_run (pipeline_run_id),
    step_name       TEXT NOT NULL,          -- e.g. 'extract_customers', 'load_dim_customer'
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'RUNNING'
                        CHECK (status IN ('RUNNING','SUCCESS','FAILED','SKIPPED')),
    records_extracted INTEGER DEFAULT 0,
    records_loaded     INTEGER DEFAULT 0,
    records_rejected   INTEGER DEFAULT 0,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_step_run_pipeline_run_id ON audit_step_run (pipeline_run_id);
