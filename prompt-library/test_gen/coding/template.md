You are an expert at designing Python test cases for a coding exercise.

## Exercise prompt
{{ prompt }}

## Reference solution (known correct)
```python
{{ reference_solution }}
```

## Starter code (defines the expected function signature)
```python
{{ starter }}
```

## Constraints
{{ constraints }}

## Difficulty target (1-5): {{ difficulty }}

## Your task
Generate a comprehensive set of test cases as Python `assert` statements that call
the function(s) defined in the reference solution and check the expected output.

Rules:
1. `tests_visible`: 2-3 basic tests shown to the learner (clear, simple inputs).
2. `tests_hidden`: 3-5 thorough tests NOT shown to the learner. Cover edge cases
   (empty input, single element, zero, negatives), boundaries, and typical values.
3. Every test MUST be a single-line Python `assert` statement.
4. Tests MUST pass against the reference solution above.
5. Tests MUST be discriminating enough to catch common bugs (off-by-one, wrong
   operator, missing edge cases, incorrect return type).

Return strict JSON conforming to the output schema:
{"tests_visible": ["assert ...", ...], "tests_hidden": ["assert ...", ...]}
