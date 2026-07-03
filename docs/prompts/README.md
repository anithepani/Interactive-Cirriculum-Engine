# Prompt Engineering Guide

How prompts are versioned, evaluated, and routed in this codebase.

## Prompt library layout

See [`prompt-library/README.md`](../../prompt-library/README.md) and Appendix C.
Every prompt is a directory with a `manifest.yaml` + `template.md` + optional
`few_shot.json`. The manifest records the model, tier, inputs, output schema,
and an eval baseline.

## Routing (Hybrid, ADR 0001)

`libs/ai/llm/LLMClient.complete(tier=...)` routes by tier:
- `high_value` -> GPT-4o (fallback Llama 3.1 70B)
- `bulk` -> Llama 3.1 70B
- `code` -> Qwen2.5-Coder-32B

## Model cards

Per AI component (§9 item 4): record model name/version, input/output,
training/few-shot data, limitations, latency, cost, fallback. File one per
component in this directory as the components land.

## Drift control (risk E26)

CI (`eval-regression.yml`) re-runs every prompt against the golden set when
`prompt-library/**` changes. A regression below `eval_baseline` in the manifest
fails the build. Bump the manifest version on any template/schema change.
