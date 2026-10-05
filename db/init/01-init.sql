-- Runs once, when the postgres volume is first created.
-- Tables are created automatically by the FastAPI backend on startup.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
