# Canonical JSON Contracts (§5.3.1)

Human-readable reference for the data shapes exchanged between AI producers
(Aryan, Ahmed) and the application consumer (Zubair). The machine-readable source
of truth is [`libs/contracts/`](../../libs/contracts/) (Pydantic v2 models).

## Exported JSON Schemas

Run `uv run python -c "import ice_contracts; ice_contracts.export_schemas('docs/contracts/_exported')"`
to regenerate. CI does this in the `contract-check` job and fails on drift.

## Schemas (summary)

### Transcript segment (Aryan -> all)
```json
{ "id": 1, "start": 0.0, "end": 2.5, "text": "hello world",
  "speaker": "SPEAKER_00", "words": [{"w":"hello","t":0.0}], "confidence": 0.95 }
```

### Visual extraction item (Ahmed -> Aryan)
```json
{ "frame_idx": 0, "ts": 1.2, "type": "code", "text": "x = 1",
  "bbox": [0.1,0.2,0.3,0.4], "code_lang": "python", "confidence": 0.88 }
```

### Concept (Aryan -> Zubair)
```json
{ "id": "python.dict", "label": "Python dict", "description": "...",
  "embedding": [0.1, ...], "difficulty": 2, "taxonomy_id": "Q1063" }
```

### Segment / topic (Aryan -> Zubair)
```json
{ "id": "s1", "start": 0.0, "end": 45.0, "title": "Creating dicts",
  "summary": "...", "concepts": ["python.dict"], "source_frames": [0,1],
  "structuredness": 0.8 }
```

### Exercise (union by `type`) (Aryan -> Zubair)
```json
{ "id": "e1", "type": "coding", "ts": 45.0, "concept_id": "python.dict",
  "difficulty": 3, "prompt": "...", "confidence": 0.9, "validation_passed": true,
  "coding": { "starter": "", "tests_visible": [], "tests_hidden": ["assert True"],
              "reference_solution": "x = {}", "language": "python", "constraints": [] } }
```

### Eval result (Aryan -> Zubair/frontend)
```json
{ "exercise_id": "e1", "verdict": "partial", "score": 0.5,
  "explanation": "...", "hints": ["check X"], "anti_cheat_flag": false }
```

See `libs/contracts/src/ice_contracts/*.py` for the authoritative field definitions.
