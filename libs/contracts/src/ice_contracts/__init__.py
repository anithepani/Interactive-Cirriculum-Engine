"""ice-contracts: canonical data contracts for the Interactive Curriculum Engine.

Single source of truth for the JSON shapes exchanged between AI producers
(Aryan, Ahmed) and the application consumer (Zubair). Master plan section 5.3.

Any change here requires dual sign-off from @aryan and @zubair.
"""

from ice_contracts.transcript import Transcript, TranscriptSegment, WordToken
from ice_contracts.visual import VisualItem, VisualRegionType
from ice_contracts.concept import Concept
from ice_contracts.segment import Segment
from ice_contracts.exercise import (
    ConceptualPayload,
    CodingPayload,
    DebugPayload,
    Exercise,
    ExerciseType,
    McqPayload,
)
from ice_contracts.eval_result import EvalResult, EvalVerdict
from ice_contracts.checkpoint import Checkpoint
from ice_contracts.curriculum import Curriculum, CurriculumStatus
from ice_contracts.adaptive import AdaptiveState, LearnerPerformance
from ice_contracts.skill import SkillModel
from ice_contracts.api import (
    AdaptiveStateResponse,
    CurriculumGenerateRequest,
    CurriculumGenerateResponse,
    EvaluateRequest,
    EvaluateResponse,
    NlpSegmentRequest,
    RegenerateRequest,
    VisionExtractRequest,
    VisionExtractResponse,
)

__all__ = [
    # transcript
    "Transcript",
    "TranscriptSegment",
    "WordToken",
    # visual
    "VisualItem",
    "VisualRegionType",
    # concept + segment
    "Concept",
    "Segment",
    # exercise
    "Exercise",
    "ExerciseType",
    "McqPayload",
    "CodingPayload",
    "DebugPayload",
    "ConceptualPayload",
    # eval
    "EvalResult",
    "EvalVerdict",
    # checkpoint + curriculum
    "Checkpoint",
    "Curriculum",
    "CurriculumStatus",
    # adaptive + skill
    "AdaptiveState",
    "LearnerPerformance",
    "SkillModel",
    # api shapes
    "CurriculumGenerateRequest",
    "CurriculumGenerateResponse",
    "EvaluateRequest",
    "EvaluateResponse",
    "RegenerateRequest",
    "RegenerateResponse",
    "AdaptiveStateResponse",
    "VisionExtractRequest",
    "VisionExtractResponse",
    "NlpSegmentRequest",
]

__version__ = "0.1.0"


def export_schemas(output_dir: str) -> None:
    """Export every model's JSON Schema to `output_dir` for the docs/ API."""
    import json
    from pathlib import Path

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    schema = {
        "Transcript": Transcript.model_json_schema(),
        "TranscriptSegment": TranscriptSegment.model_json_schema(),
        "VisualItem": VisualItem.model_json_schema(),
        "Concept": Concept.model_json_schema(),
        "Segment": Segment.model_json_schema(),
        "Exercise": Exercise.model_json_schema(),
        "EvalResult": EvalResult.model_json_schema(),
        "Checkpoint": Checkpoint.model_json_schema(),
        "Curriculum": Curriculum.model_json_schema(),
        "AdaptiveState": AdaptiveState.model_json_schema(),
        "SkillModel": SkillModel.model_json_schema(),
    }
    for name, s in schema.items():
        (out / f"{name}.json").write_text(json.dumps(s, indent=2, default=str))
