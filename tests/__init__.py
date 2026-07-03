Cross-cutting tests.

- `integration/` — flows across services (api <-> worker <-> sandbox <-> db). Requires
  the live compose stack (`make dev`). Marks: `@pytest.mark.integration`.
- `e2e/` — full pipeline: submit video -> generate -> play -> checkpoint -> eval -> adapt. Mark: `@pytest.mark.e2e`.
- `contract/` — consumer-driven contract tests validating live endpoints against `libs/contracts/`. Run in the `contract-check` CI job.

Per-package unit tests live alongside the code (`libs/*/tests/`, `apps/*/tests/`).
