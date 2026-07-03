# Prompt Library

Versioned prompt library for every LLM call (master plan section 9 + Appendix C).
Each prompt is a directory containing:

- `manifest.yaml` — metadata: model, version, inputs, output schema, eval baseline, tags
- `template.md` (or `.j2`) — the prompt template with `{{ variables }}`
- `few_shot.json` — optional few-shot examples (concept-conditioned)
- `eval.json` — last eval result against the golden set (drift detection, E26)

## Why version prompts?

- **Drift alerts (E26):** benchmark regression on the golden set per release
- **Cost control:** swap to cheaper models for bulk tasks deliberately, not silently
- **Reproducibility:** a curriculum generated at version X is explainable later
- **Fallback (§6.4):** the manifest records the fallback model used when GPT-4o is down

## Layout (Appendix C.0.1)

```
prompt-library/
  _manifest.schema.json     # JSON Schema validating every manifest.yaml
  segmentation/
  exercise_gen/
    mcq/
    coding/
    debug/
    conceptual/
  test_gen/
  evaluation/
```

Owner: **Aryan**. CI (`eval-regression.yml`) re-runs every prompt against the
golden set when `prompt-library/**` changes and fails on regression.
