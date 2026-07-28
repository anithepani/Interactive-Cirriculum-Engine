"""Review Payload Contracts.

Defines the discriminated union schemas for the mixed-format review system.
"""
from typing import Literal, Union
from pydantic import BaseModel, Field

class ReviewOutputPrediction(BaseModel):
    type: Literal["output_prediction"] = "output_prediction"
    code: str
    expected_output: str
    explanation: str

class ReviewFillGap(BaseModel):
    type: Literal["fill_gap"] = "fill_gap"
    code: str  # Code with {{blank}} or similar placeholders
    answer: str  # Exact expected string
    explanation: str

class ReviewSpotBug(BaseModel):
    type: Literal["spot_bug"] = "spot_bug"
    code: str
    bug_line: int  # 1-indexed
    fixed_code: str
    expected_output: str | None = None
    explanation: str

class ReviewConceptRecall(BaseModel):
    type: Literal["concept_recall"] = "concept_recall"
    question: str
    options: list[str]
    answer_index: int
    explanation: str

class TraceStateRow(BaseModel):
    iteration: Union[int, str]
    variables: dict[str, str]

class ReviewTraceState(BaseModel):
    type: Literal["trace_state"] = "trace_state"
    code: str
    initial_variables: dict[str, str]
    table: list[TraceStateRow]
    explanation: str

class ReviewLegacy(BaseModel):
    type: Literal["legacy"] = "legacy"
    legacy: Literal[True] = True
    question: str
    answer: str

ReviewPayload = Union[
    ReviewOutputPrediction,
    ReviewFillGap,
    ReviewSpotBug,
    ReviewConceptRecall,
    ReviewTraceState,
    ReviewLegacy,
]
