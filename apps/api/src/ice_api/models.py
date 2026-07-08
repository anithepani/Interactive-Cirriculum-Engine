from __future__ import annotations
from sqlalchemy import (
    Column, Integer, String, Float, JSON, Text, DateTime, ForeignKey,
    Boolean, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ice_shared.db import Base
import enum
class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_used = Column(Boolean, default=False)
# ---- Enums ----
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
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    plan = Column(String, default="free")
    created_at = Column(DateTime, server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, default="User")
    password_hash = Column(String(255), nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.learner)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_id"),
        Index("ix_users_tenant", "tenant_id"),
    )

class Curriculum(Base):
    __tablename__ = "curricula"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    source_type = Column(String, nullable=True)       # "youtube" or "upload"
    source_ref = Column(String, nullable=True)        # YouTube URL or file path
    content_hash = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    status = Column(Enum(CurriculumStatus), default=CurriculumStatus.queued)
    language = Column(String, default="en")
    framework_version = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    ready_at = Column(DateTime, nullable=True)

class Segment(Base):
    __tablename__ = "segments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    curriculum_id = Column(Integer, ForeignKey("curricula.id"), nullable=False)
    
    start_time = Column(Float, nullable=True)    # renamed from 'start' to match usage
    end_time = Column(Float, nullable=True)      # renamed from 'end'
    title = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    structuredness = Column(Float, nullable=True)
    topic_label = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    __table_args__ = (Index("ix_segments_curriculum", "curriculum_id"),)

class Concept(Base):
    __tablename__ = "concepts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    curriculum_id = Column(Integer, ForeignKey("curricula.id"), nullable=False)
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(Float, default=1.5)
    # Remove: embedding, canonical_id (if they don't exist in DB)
    __table_args__ = (Index("ix_concepts_curriculum", "curriculum_id"),)

class ConceptEdge(Base):
    __tablename__ = "concept_edges"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    relation = Column(String, nullable=False)   # "prereq" or "related"
    __table_args__ = (UniqueConstraint("source_id", "target_id", "relation"),)

class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id = Column(Integer, primary_key=True, autoincrement=True)
    curriculum_id = Column(Integer, ForeignKey("curricula.id"), nullable=False)
    segment_id = Column(Integer, ForeignKey("segments.id"), nullable=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=True)
    ts = Column(Float, nullable=False)
    exercise_type = Column(Enum(ExerciseType), nullable=False)
    difficulty = Column(Float, default=1.5)
    # ordering column removed
    __table_args__ = (Index("ix_checkpoints_curriculum", "curriculum_id"),)

class Exercise(Base):
    __tablename__ = "exercises"
    id = Column(Integer, primary_key=True, autoincrement=True)
    checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=False)
    type = Column(Enum(ExerciseType), nullable=False)
    payload = Column(JSON, nullable=True)       # stores question, options, answer, etc.
    confidence = Column(Float, nullable=True)
    validation_passed = Column(Boolean, default=False)
    prompt_version_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Test(Base):
    __tablename__ = "tests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    kind = Column(String, nullable=False)       # "visible" or "hidden"
    input = Column(Text, nullable=True)
    expected = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    curriculum_id = Column(Integer, ForeignKey("curricula.id"), nullable=False)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    resume_ts = Column(Float, default=0.0)

class SessionEvent(Base):
    __tablename__ = "session_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    ts = Column(Float, nullable=False)
    type = Column(String, nullable=False)       # "play", "pause", "checkpoint", "submit", "feedback"
    payload = Column(JSON, nullable=True)

class EvalResult(Base):
    __tablename__ = "eval_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_event_id = Column(Integer, ForeignKey("session_events.id"), nullable=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    verdict = Column(Enum(Verdict), nullable=False)
    score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)
    anti_cheat_flag = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class SkillModel(Base):
    __tablename__ = "skill_model"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    mastery = Column(Float, default=0.0)
    attempts = Column(Integer, default=0)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("user_id", "concept_id"),)

class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    model = Column(String, nullable=False)
    temperature = Column(Float, nullable=False)
    eval_score = Column(Float, nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    curriculum_id = Column(Integer, ForeignKey("curricula.id"), nullable=False)
    kind = Column(String, nullable=False)       # "video", "audio", "frame", "transcript", "ocr"
    storage_uri = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)