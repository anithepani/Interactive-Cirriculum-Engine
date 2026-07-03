# M8 - Test Generation & Validation

LLM generates N candidate tests + reference solution; mutation testing ensures tests
catch bugs; CodeT self-consistency (generate multiple solutions, keep tests passing on
majority); execute in sandbox before publish.

An exercise only becomes publishable once `validation_passed=True`.

**Lead:** Aryan · **Support:** Zubair (sandbox)

Papers [MUST]: "CodeT: Code Generation with Generated Tests" (Chen 2022).
