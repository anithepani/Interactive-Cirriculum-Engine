"""Reconcile session progress and index the aggregate skill model.

Revision ID: 0003_runtime_schema_reconciliation
Revises: 0002_auth_columns_and_rls
Create Date: 2026-08-05
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0003_runtime_schema_reconciliation"
down_revision: Union[str, None] = "0002_auth_columns_and_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS tenant_id uuid")
    op.execute(
        "UPDATE sessions s SET tenant_id = c.tenant_id FROM curricula c "
        "WHERE s.curriculum_id = c.id AND s.tenant_id IS NULL"
    )
    op.execute("ALTER TABLE sessions ALTER COLUMN tenant_id SET NOT NULL")
    op.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS max_watched_ts double precision DEFAULT 0")
    op.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS watched_seconds double precision DEFAULT 0")
    op.execute(
        "UPDATE sessions SET max_watched_ts = GREATEST(COALESCE(max_watched_ts, 0), "
        "COALESCE(resume_ts, 0)), watched_seconds = COALESCE(watched_seconds, 0)"
    )
    op.execute(
        "WITH ranked AS ("
        " SELECT id, first_value(id) OVER (PARTITION BY user_id, curriculum_id "
        " ORDER BY COALESCE(max_watched_ts, 0) DESC, COALESCE(watched_seconds, 0) DESC, started_at) keep_id,"
        " max(COALESCE(resume_ts, 0)) OVER (PARTITION BY user_id, curriculum_id) max_resume,"
        " max(COALESCE(max_watched_ts, 0)) OVER (PARTITION BY user_id, curriculum_id) max_watched,"
        " sum(COALESCE(watched_seconds, 0)) OVER (PARTITION BY user_id, curriculum_id) total_watched"
        " FROM sessions), updated AS ("
        " UPDATE sessions s SET resume_ts = r.max_resume, max_watched_ts = r.max_watched,"
        " watched_seconds = r.total_watched FROM ranked r WHERE s.id = r.keep_id RETURNING s.id)"
        " DELETE FROM sessions s USING ranked r WHERE s.id = r.id AND r.id <> r.keep_id"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_user_curriculum "
        "ON sessions (user_id, curriculum_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sessions_tenant ON sessions (tenant_id)")

    # Production still has the original aggregate skill model. The application
    # needs curriculum_id for deletion; per-concept migration is intentionally
    # kept separate because expanding historic JSON mastery requires product rules.
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_model_curriculum ON skill_model (curriculum_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_skill_model_curriculum")
    op.execute("DROP INDEX IF EXISTS uq_sessions_user_curriculum")
    op.execute("DROP INDEX IF EXISTS ix_sessions_tenant")
