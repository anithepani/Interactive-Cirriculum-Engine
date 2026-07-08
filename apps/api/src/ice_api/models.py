"""SQLAlchemy ORM models mirroring db/migrations/0001_baseline.py.

Every tenant-scoped table carries a ``tenant_id`` and is protected by Postgres
Row-Level Security (the app sets ``app.tenant_id`` per request). Primary keys
are UUID (server-generated) for tenants/users/etc. and String(64) for
segments/concepts/exercises (stable slug ids from the AI pipeline).

Note: there is NO ``checkpoints`` table - checkpoint placement data (ts,
segment_id, concept_id, difficulty) is folded into the ``exercises`` table
per the canonical migration.
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ice_shared.db import Base

# pgvector is only needed for the Concept.embedding column.
try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - pgvector is in deps; guard for safety
    Vector = None  # type: ignore[assignment, misc]


# ---- Enums (stored as sa.String to match the migration; not SQL enums) ----


class UserRole(str, enum.Enum):
    learner = "learner"
    instructor = "instructor"
    admin = "admin"


class CurriculumStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class ExerciseType(str, enum.Enum):
    mcq = "mcq"
    coding = "coding"
    debug = "debug"
    conceptual = "conceptual"


class Verdict(str, enum.Enum):
    pass_ = "pass"
    fail = "fail"
    partial = "partial"


# ---- Tables ----


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    name = Column(String(120), nullable=False)
    slug = Column(String(60), nullable=False, unique=True)
    token_budget = Column(BigInteger, nullable=False, server_default="250000")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email = Column(String(255), nullable=False)
    name = Column(String(120))
    role = Column(String(20), nullable=False, server_default="learner")
    oauth_provider = Column(String(20))
    oauth_subject = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)


class Curriculum(Base):
    __tablename__ = "curricula"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_ref = Column(String(1024), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, server_default="queued")
    language = Column(String(8), nullable=False, server_default="en")
    duration_sec = Column(Float, nullable=False)
    content_hash = Column(String(64), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text)


class Segment(Base):
    __tablename__ = "segments"

    id = Column(String(64), primary_key=True)
    curriculum_id = Column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    start = Column(Float, nullable=False)
    end = Column(Float, nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text)
    source_frames = Column(JSONB, server_default="[]")
    structuredness = Column(Float, nullable=False)


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String(64), primary_key=True)
    curriculum_id = Column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    label = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty = Column(SmallInteger, nullable=False)
    taxonomy_id = Column(String(128))
    # pgvector column - only declared if the extension import succeeded.
    embedding = Column(Vector(1024), nullable=True) if Vector is not None else None


class ConceptEdge(Base):
    __tablename__ = "concept_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    src_concept_id = Column(
        String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dst_concept_id = Column(
        String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    relation = Column(String(40), nullable=False)

    __table_args__ = (
        UniqueConstraint("src_concept_id", "dst_concept_id", "relation", name="uq_concept_edge"),
    )


class Exercise(Base):
    """Exercises carry checkpoint placement data (ts, segment_id, concept_id).

    The canonical migration has no separate ``checkpoints`` table; the
    checkpoint fields are columns here.
    """

    __tablename__ = "exercises"

    id = Column(String(64), primary_key=True)
    curriculum_id = Column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    segment_id = Column(
        String(64), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(20), nullable=False)  # mcq|coding|debug|conceptual
    ts = Column(Float, nullable=False)
    difficulty = Column(SmallInteger, nullable=False)
    prompt = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    confidence = Column(Float, nullable=False)
    validation_passed = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Test(Base):
    __tablename__ = "tests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    exercise_id = Column(
        String(64), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_visible = Column(Boolean, nullable=False, server_default="false")
    code = Column(Text, nullable=False)
    mutation_score = Column(Float)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    curriculum_id = Column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    resume_ts = Column(Float, nullable=False, server_default="0")
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class SessionEvent(Base):
    __tablename__ = "session_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ts = Column(Float, nullable=False)
    kind = Column(String(40), nullable=False)  # play|pause|checkpoint_open|submit|...
    payload = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    exercise_id = Column(
        String(64), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    verdict = Column(String(10), nullable=False)  # pass|fail|partial
    score = Column(Float, nullable=False)
    explanation = Column(Text)
    hints = Column(JSONB, server_default="[]")
    anti_cheat_flag = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SkillModel(Base):
    __tablename__ = "skill_model"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    curriculum_id = Column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    mastery = Column(JSONB, nullable=False, server_default="{}")  # {concept_id: [0,1]}
    weak_concepts = Column(JSONB, server_default="[]")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "curriculum_id", name="uq_skill_user_curriculum"),
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    curriculum_id = Column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    kind = Column(String(40), nullable=False)  # video|audio|frames|transcript|...
    s3_key = Column(String(1024), nullable=False)
    meta = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    name = Column(String(120), nullable=False, index=True)
    version = Column(String(40), nullable=False)
    model = Column(String(80), nullable=False)
    template = Column(Text, nullable=False)
    schema = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("name", "version", name="uq_prompt_name_version"),)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_user_id = Column(UUID(as_uuid=True))
    action = Column(String(60), nullable=False)
    target_table = Column(String(60))
    target_id = Column(String(128))
    payload = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
