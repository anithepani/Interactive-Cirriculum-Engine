"""M10 Adaptive Progression Controller.

Input: learner performance stream, concept graph, current difficulty.
Output: next checkpoint difficulty, remediation inserts, skip decisions.

Tech (MVP): heuristic moving average over the recent performance window
(interpretable, no training data required). A full IRT 3PL / DKT model is a
Phase 6 stretch; this heuristic is the documented fallback.

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

# --- Tunables (kept module-level so tests/callers can reference them) ------- #
_MIN_DIFFICULTY = 1
_MAX_DIFFICULTY = 5
# Score below this counts as a "fail" on a single checkpoint.
_FAIL_SCORE = 0.5
# Score at/above this counts as a strong "pass" that warrants stepping up.
_STRONG_PASS_SCORE = 0.85
# Number of most-recent observations the moving average considers.
_WINDOW = 3
# Consecutive fails that trigger a remedial insert (E27 soft-fail).
_REMEDIAL_FAIL_STREAK = 2
# Moving-average mastery at/above which we allow skipping the next checkpoint.
_SKIP_MASTERY = 0.9
# Never move difficulty by more than one level per step (E27: no hard-block /
# no whiplash jumps).
_MAX_STEP = 1


def _clamp_difficulty(value: int) -> int:
    return max(_MIN_DIFFICULTY, min(_MAX_DIFFICULTY, value))


def _recent(history: list[LearnerPerformance], n: int) -> list[LearnerPerformance]:
    return history[-n:] if n > 0 else list(history)


def _moving_average(history: list[LearnerPerformance]) -> float:
    window = _recent(history, _WINDOW)
    if not window:
        return 0.0
    return sum(p.score for p in window) / len(window)


def _trailing_fail_streak(history: list[LearnerPerformance]) -> int:
    streak = 0
    for perf in reversed(history):
        if perf.score < _FAIL_SCORE:
            streak += 1
        else:
            break
    return streak


def next_state(
    history: list[LearnerPerformance],
    current_difficulty: int,
    session_id: str = "session",
) -> AdaptiveState:
    """Compute next difficulty + remediation/skip decisions.

    Heuristic (moving-average fallback for IRT/DKT):
      * With no history, hold the current difficulty (calibration, E10).
      * If the most recent checkpoint was a fail (score < ``_FAIL_SCORE``),
        lower difficulty by 1 (never more, E27 soft-fail).
      * If the most recent checkpoint was a strong pass
        (score >= ``_STRONG_PASS_SCORE``) *and* the moving average is healthy,
        raise difficulty by 1.
      * Otherwise hold.
      * ``insert_remedial`` fires after ``_REMEDIAL_FAIL_STREAK`` consecutive
        fails (reveal explanation + simpler analog).
      * ``skip_next`` fires when the moving-average mastery is very high.

    Args:
        history: Ordered LearnerPerformance observations (oldest first). The
            last element is the most recent checkpoint.
        current_difficulty: The difficulty of the checkpoint just completed.
        session_id: Learning-session id echoed back on the state.

    Returns:
        An ``AdaptiveState`` with the recommended next difficulty and flags.
    """
    current = _clamp_difficulty(int(current_difficulty))

    if not history:
        return AdaptiveState(
            session_id=session_id,
            next_difficulty=current,
            insert_remedial=False,
            skip_next=False,
            performance_history=[],
        )

    avg = _moving_average(history)
    fail_streak = _trailing_fail_streak(history)
    last_score = history[-1].score

    # Decide the difficulty delta (bounded to +/- one level).
    if last_score < _FAIL_SCORE:
        delta = -_MAX_STEP
    elif last_score >= _STRONG_PASS_SCORE and avg >= _STRONG_PASS_SCORE:
        delta = _MAX_STEP
    else:
        delta = 0

    next_difficulty = _clamp_difficulty(current + delta)

    insert_remedial = fail_streak >= _REMEDIAL_FAIL_STREAK
    # Only skip when consistently strong and not currently struggling.
    skip_next = avg >= _SKIP_MASTERY and fail_streak == 0

    return AdaptiveState(
        session_id=session_id,
        next_difficulty=next_difficulty,
        insert_remedial=insert_remedial,
        skip_next=skip_next,
        performance_history=_recent(history, _WINDOW),
    )
