-- ICE: PostgreSQL extensions required by the app schema.
-- Mounted into /docker-entrypoint-initdb.d/ by docker-compose.dev.yml so the
-- pgvector / uuid-ossp / pg_trgm extensions are present on first DB init.
-- NOTE: docker-entrypoint-initdb.d scripts only run on an EMPTY data volume.
-- For an already-initialized DB, run `make migrate` (alembic 0001_baseline)
-- or `python init_db.py`, which both issue `CREATE EXTENSION IF NOT EXISTS`.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
