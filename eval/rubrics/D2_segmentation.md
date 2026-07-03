# Segmentation Rubric (D.2)

Owner: **Aryan**

Measures whether concept segmentation + checkpoint placement land on real topic boundaries.

## Metrics

| Metric | Definition | Target |
| --- | --- | --- |
| Boundary precision | fraction of generated boundaries within +/-5s of a human-labeled topic boundary | >=0.80 |
| Boundary recall | fraction of human-labeled boundaries captured | >=0.70 |
| Over-segmentation rate | segments that split a single topic | <=0.20 |
| Checkpoint placement | checkpoints land on a real transition + after a learnable concept | >=0.80 |
| Structuredness accuracy | the structuredness score correctly flags unstructured videos (E4) | >=0.75 |

## Procedure

1. Run the pipeline (`scripts/eval-golden.py`) on the 5 golden videos.
2. Compare generated segments/checkpoints against `golden_set/*/expected.json` + human labels.
3. Write `eval/reports/segmentation-<date>.json`.
4. CI compares against `eval/reports/baseline.json`; fails on regression.
