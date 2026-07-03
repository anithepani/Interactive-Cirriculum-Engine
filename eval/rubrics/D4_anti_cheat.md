# Anti-Cheat False-Positive Rate (D.4)

Owner: **Aryan**

Measures how often the anti-cheat detector (CodeBLEU/AST diff vs instructor's
extracted code, risk E12) wrongly flags legitimate learner code.

## Target

- False-positive rate <=5% (legitimate code flagged as cheating)
- False-negative rate <=10% (obvious copies missed)

## Procedure

1. Collect legitimate solutions (from human testers / golden solver runs).
2. Collect cheating solutions (instructor's code lightly renamed).
3. Run the anti-cheat check; compute FP/FN rates.
4. Write `eval/reports/anti-cheat-<date>.json`.
