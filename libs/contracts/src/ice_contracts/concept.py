"""Concept contract (section 5.3.1).

Producer: Aryan (M5 Knowledge Graph / Concept Mapper).
Consumer: Zubair (persistence, frontend), M7 exercise generation.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, confloat


class Concept(BaseModel):
    """A learned concept, mapped to a curated CS/programming taxonomy."""

    id: str = Field(..., description="Stable concept id (canonical taxonomy)")
    label: str = Field(..., min_length=1, description="Human-readable label")
    description: str = Field(..., description="Short explanation of the concept")
    embedding: list[float] = Field(
        default_factory=list, description="BGE-M3 embedding vector (pgvector)"
    )
    difficulty: int = Field(..., ge=1, le=5, description="Intrinsic difficulty 1-5")
    taxonomy_id: Optional[str] = Field(
        None, description="Link to Wikidata/CS taxonomy canonical id"
    )
