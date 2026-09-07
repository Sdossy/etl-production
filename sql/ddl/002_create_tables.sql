-- 002_create_tables.sql  (SQLite)
-- Raw landing tables, staging tables, and dw dimension/fact tables
-- for the Customers / Orders example data model.
-- Run after 001_create_schemas.sql

-- =========================================================
-- RAW LAYER  (loose typing on purpose -- landing zone only)
-- =========================================================

CREATE TABLE IF NOT EXISTS raw_customers (
    raw_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system   TEXT NOT NULL DEFAULT 'sample',
    payload         TEXT NOT NULL,          -- original record, stored as JSON text
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now')),
    pipeline_run_id TEXT
);

CREATE TABLE IF NOT EXISTS raw_orders (
    raw_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system   TEXT NOT NULL DEFAULT 'sample',
    payload         TEXT NOT NULL,
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now')),
    pipeline_run_id TEXT
);

-- =========================================================
-- STAGING LAYER  (typed, cleaned, still one row per source record)
-- =========================================================

CREATE TABLE IF NOT EXISTS stg_customers (
    customer_id     TEXT PRIMARY KEY,       -- natural/source key
    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,
    phone           TEXT,
    address_line1   TEXT,
    city            TEXT,
    state           TEXT,
    postal_code     TEXT,
    country         TEXT,
    created_at      TEXT,
    updated_at      TEXT,
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now')),
    pipeline_run_id TEXT
);

CREATE TABLE IF NOT EXISTS stg_orders (
    order_id        TEXT PRIMARY KEY,       -- natural/source key
    customer_id     TEXT NOT NULL,
    order_date      TEXT,
    status          TEXT,
    subtotal        NUMERIC,
    tax             NUMERIC,
    total_amount    NUMERIC,
    currency        TEXT DEFAULT 'USD',
    created_at      TEXT,
    updated_at      TEXT,
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now')),
    pipeline_run_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_stg_orders_customer_id ON stg_orders (customer_id);

-- =========================================================
-- DW LAYER -- DIMENSIONS
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_sk     INTEGER PRIMARY KEY AUTOINCREMENT,  -- surrogate key
    customer_id     TEXT NOT NULL,                       -- natural key from source
    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,
    phone           TEXT,
    city            TEXT,
    state           TEXT,
    postal_code     TEXT,
    country         TEXT,
    -- SCD Type 2 tracking columns
    effective_date  TEXT NOT NULL DEFAULT (date('now')),
    end_date        TEXT,
    is_current      INTEGER NOT NULL DEFAULT 1,          -- 1 = true, 0 = false
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Partial unique index: only one "current" row per natural key
CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_customer_current
    ON dim_customer (customer_id)
    WHERE is_current = 1;

-- =========================================================
-- DW LAYER -- FACTS
-- =========================================================

CREATE TABLE IF NOT EXISTS fact_orders (
    order_sk        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        TEXT NOT NULL UNIQUE,
    customer_sk     INTEGER NOT NULL REFERENCES dim_customer (customer_sk),
    order_date      TEXT NOT NULL,
    status          TEXT,
    subtotal        NUMERIC,
    tax             NUMERIC,
    total_amount    NUMERIC,
    currency        TEXT DEFAULT 'USD',
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now')),
    pipeline_run_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_fact_orders_customer_sk ON fact_orders (customer_sk);
CREATE INDEX IF NOT EXISTS idx_fact_orders_order_date ON fact_orders (order_date);
