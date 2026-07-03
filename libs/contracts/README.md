# ice-contracts

The **single source of truth** for every canonical JSON shape exchanged between AI producers (Aryan, Ahmed) and the application consumer (Zubair). Defined in the master plan, section 5.3.1 "Shared data formats".

> **Hard rule:** any change to this package requires sign-off from **both** Aryan and Zubair. See `CONTRIBUTING.md`.

## Models

This package exports Pydantic v2 models for:

| Model | Producer -> Consumer | Master plan ref |
| --- | --- | --- |
| `TranscriptSegment` | Aryan -> all | §5.3.1 |
| `WordToken` | Aryan -> all | §5.3.1 (transcript.words) |
| `Transcript` | Aryan -> all | §5.3.1 |
| `VisualItem` | Ahmed -> Aryan | §5.3.1 |
| `Concept` | Aryan -> Zubair | §5.3.1 |
| `Segment` (topic) | Aryan -> Zubair | §5.3.1 |
| `Exercise` (union: mcq\|coding\|debug\|conceptual) | Aryan -> Zubair | §5.3.1 |
| `McqPayload`, `CodingPayload`, `DebugPayload`, `ConceptualPayload` | Aryan -> Zubair | §5.3.1 |
| `EvalResult` | Aryan -> Zubair/frontend | §5.3.1 |
| `Checkpoint` | Aryan -> Zubair/frontend | §4.2.6 |
| `Curriculum` | Aryan -> Zubair/frontend | §4.1 (curriculum JSON) |
| `AdaptiveState` | Aryan -> Zubair | §4.2.10 |
| `SkillModel` | Zubair/Aryan | §4.2.11 |

It also exposes the **request/response shapes for the 7 AI service endpoints** (§5.3.2):
`POST /ai/curriculum/generate`, `GET /ai/curriculum/{id}`, `POST /ai/evaluate`, `POST /ai/regenerate`, `GET /ai/adaptive/{session_id}`, `POST /vision/extract`, `POST /nlp/segment`.

## Usage

```python
from ice_contracts import Exercise, EvalResult, CurriculumGenerateRequest

# Producer side (Aryan's AI module emits a validated object)
exercise = Exercise.model_validate(raw_llm_json)

# Consumer side (Zubair's API validates an inbound request)
req = CurriculumGenerateRequest.model_validate(await request.json())
```

## Exporting JSON Schema

```python
import ice_contracts
ice_contracts.export_schemas("docs/contracts/_exported")
```

This is run in CI (`contract-check` job) to keep `docs/contracts/` in sync.
