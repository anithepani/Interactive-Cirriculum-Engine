"""baseline: create all 15 tenant-scoped tables + pgvector + RLS policies.

Tables (master plan section 5.3.3): tenants, users, curricula, segments, concepts,
concept_edges, exercises, tests, sessions, session_events, eval_results,
skill_model, artifacts, prompt_versions.

All tenant-scoped tables carry tenant_id and are protected by Postgres Row-Level
Security keyed on the session GUC `app.tenant_id` (set by the API/worker per request).
This is the enforcement for multi-tenant isolation (locked decision #5, risk E25).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-03
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- Extensions ----
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pgvector\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\"")

    # ---- 1. tenants ----
    op.create_table(
        "tenants",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("token_budget", sa.BigInteger, nullable=False, server_default="250000"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ---- 2. users ----
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(120)),
        sa.Column("role", sa.String(20), nullable=False, server_default="learner"),  # learner | instructor | admin
        sa.Column("oauth_provider", sa.String(20)),   # google | github
        sa.Column("oauth_subject", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    # ---- 3. curricula ----
    op.create_table(
        "curricula",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("video_ref", sa.String(1024), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),  # queued|processing|ready|failed
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("duration_sec", sa.Float, nullable=False),
        sa.Column("content_hash", sa.String(64), index=True),  # dedupe (E22)
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text),
    )

    # ---- 4. segments ----
    op.create_table(
        "segments",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("curriculum_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("start", sa.Float, nullable=False),
        sa.Column("end", sa.Float, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("source_frames", sa.dialects.postgresql.JSONB, server_default="[]"),
        sa.Column("structuredness", sa.Float, nullable=False),
    )

    # ---- 5. concepts ----
    op.create_table(
        "concepts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("curriculum_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("difficulty", sa.SmallInteger, nullable=False),
        sa.Column("taxonomy_id", sa.String(128)),
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float), nullable=True),  # pgvector; cast in app
    )
    op.execute("ALTER TABLE concepts ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector(1024)")
    op.create_index("ix_concepts_embedding", "concepts", ["embedding"], postgresql_using="ivfflat", postgresql_with={"lists": 100})

    # ---- 6. concept_edges ----
    op.create_table(
        "concept_edges",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("src_concept_id", sa.String(64), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("dst_concept_id", sa.String(64), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("relation", sa.String(40), nullable=False),  # prerequisite | related | part_of
        sa.UniqueConstraint("src_concept_id", "dst_concept_id", "relation", name="uq_concept_edge"),
    )

    # ---- 7. exercises ----
    op.create_table(
        "exercises",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("curriculum_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("segment_id", sa.String(64), sa.ForeignKey("segments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("concept_id", sa.String(64), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),  # mcq|coding|debug|conceptual
        sa.Column("ts", sa.Float, nullable=False),
        sa.Column("difficulty", sa.SmallInteger, nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB, nullable=False),  # type-specific (mcq|coding|debug|conceptual)
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("validation_passed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ---- 8. tests ----
    op.create_table(
        "tests",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("exercise_id", sa.String(64), sa.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("is_visible", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("mutation_score", sa.Float),  # E15 - tests must catch bugs
    )

    # ---- 9. sessions ----
    op.create_table(
        "sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("curriculum_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("resume_ts", sa.Float, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )

    # ---- 10. session_events ----
    op.create_table(
        "session_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("session_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("ts", sa.Float, nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),  # play|pause|checkpoint_open|submit|...
        sa.Column("payload", sa.dialects.postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ---- 11. eval_results ----
    op.create_table(
        "eval_results",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("exercise_id", sa.String(64), sa.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("session_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("verdict", sa.String(10), nullable=False),  # pass|fail|partial
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("explanation", sa.Text),
        sa.Column("hints", sa.dialects.postgresql.JSONB, server_default="[]"),
        sa.Column("anti_cheat_flag", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ---- 12. skill_model ----
    op.create_table(
        "skill_model",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("curriculum_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("mastery", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),  # {concept_id: [0,1]}
        sa.Column("weak_concepts", sa.dialects.postgresql.JSONB, server_default="[]"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "curriculum_id", name="uq_skill_user_curriculum"),
    )

    # ---- 13. artifacts ----
    op.create_table(
        "artifacts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("curriculum_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("kind", sa.String(40), nullable=False),  # video|audio|frames|transcript|visual_items|curriculum_json
        sa.Column("s3_key", sa.String(1024), nullable=False),  # tenants/<id>/...
        sa.Column("meta", sa.dialects.postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ---- 14. prompt_versions ----
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(120), nullable=False, index=True),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("template", sa.Text, nullable=False),
        sa.Column("schema", sa.dialects.postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", "version", name="uq_prompt_name_version"),
    )

    # ---- 15. audit_log (multi-tenant security, E25) ----
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("actor_user_id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("target_table", sa.String(60)),
        sa.Column("target_id", sa.String(128)),
        sa.Column("payload", sa.dialects.postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ---- Row-Level Security (risk E25) ----
    # Enable RLS on every tenant-scoped table. The app sets app.tenant_id per
    # session/request; policies expose only rows matching that tenant.
    _TENANT_TABLES = [
        "users", "curricula", "segments", "concepts", "concept_edges",
        "exercises", "tests", "sessions", "session_events", "eval_results",
        "skill_model", "artifacts", "audit_log",
    ]
    for t in _TENANT_TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {t} "
            f"USING (tenant_id = current_setting('app.tenant_id')::uuid)"
        )


def downgrade() -> None:
    for t in [
        "audit_log", "prompt_versions", "artifacts", "skill_model", "eval_results",
        "session_events", "sessions", "tests", "exercises", "concept_edges",
        "concepts", "segments", "curricula", "users", "tenants",
    ]:
        op.drop_table(t)
