-- 001_create_schemas.sql
-- SQLite has no CREATE SCHEMA. Instead, the four logical layers are
-- represented as table name prefixes within a single .db file:
--   raw_...    -> landing zone, minimally-typed copies of source data
--   stg_...    -> cleaned/typed staging tables
--   dim_/fact_ -> data warehouse layer (dimensions + facts)
--   audit_...  -> pipeline run metadata, row counts, error logs
--
-- This file just turns on foreign key enforcement, which SQLite
-- has OFF by default. Run this once per connection/session
-- (the Python db helper should also set this on every connect()).

PRAGMA foreign_keys = ON;
