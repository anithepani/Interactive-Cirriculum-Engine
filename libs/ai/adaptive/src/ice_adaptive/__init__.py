"""M10 Adaptive Progression Controller.

Input: learner performance stream, concept graph, current difficulty.
Output: next checkpoint difficulty, remediation inserts, skip decisions.

Tech (MVP): IRT 3PL (simpler, interpretable) or heuristic moving average.
(Phase 6 stretch): Deep Knowledge Tracing (DKT) / DKVMN.

Papers [MUST]: DKT (Piech 2015).
Papers [OPT]: DKVMN (Zhang 2017); Bayesian Knowledge Tracing; IRT 3PL.

Edge case E10 (beginner vs advanced mismatch): initial calibration question;
per-concept difficulty tags; adaptive band.
Edge case E27 (learner churns after repeated failures): soft-fail - after N
fails, reveal explanation + offer "watch again" + simpler analog; never
hard-block progression >1 level.

Lead: Aryan. Support: Zubair (session state).
"""
from __future__ import annotations

from ice_contracts import AdaptiveState, LearnerPerformance


def next_state(history: list[LearnerPerformance], current_difficulty: int) -> AdaptiveState:
    """Compute next difficulty + remediation/skip decisions."""
    raise NotImplementedError("Phase 4 deliverable")
