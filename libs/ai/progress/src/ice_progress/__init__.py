"""M11 Learner Profile & Progress Tracker.

Input: session events, eval results. Output: skill model, mastery per concept,
history, spaced-repetition schedule (stretch).

Tech: Postgres tables (RLS); FSRS-4.5 for SRS (stretch); Redis for hot session state.

Papers [OPT]: FSRS whitepaper; SM-2; "Open Learner Models" survey.

Dashboard (UC-11): concepts mastered, accuracy streak, weak concepts, time spent,
session history, "tutorial hell score".

Phase 4 MVP: fold a single :class:`EvalResult` into the learner's per-concept
mastery map via an exponential weighted moving average (EWMA), and recompute the
``weak_concepts`` list against a fixed mastery threshold. Pure function, no I/O —
persistence lives at the ``/evaluate`` boundary (see ``curricula.py``).

Lead: Zubair. Support: Aryan (skill model input).
"""
from __future__ import annotations

from ice_contracts import EvalResult, SkillModel

# EWMA weight for the newest observation. 0.4 keeps history influential while
# still moving quickly enough to reflect recent performance.
_EWMA_ALPHA = 0.4

# Concepts with mastery below this are surfaced as "weak" on the dashboard.
_WEAK_THRESHOLD = 0.6


def update_skill(
    skill: SkillModel,
    result: EvalResult,
    concept_id: str | None = None,
) -> SkillModel:
    """Fold an eval result into the learner's skill model.

    Args:
        skill: The learner's current :class:`SkillModel` (per-concept mastery map
            + weak-concept list).
        result: The :class:`EvalResult` from a single attempt.
        concept_id: The concept the exercise tested. ``EvalResult`` does not carry
            the concept id, so callers pass it explicitly. When omitted we fall
            back to the exercise id so the update is still recorded (degraded but
            non-crashing).

    Returns:
        A new :class:`SkillModel` with the concept's mastery updated (EWMA) and
        ``weak_concepts`` recomputed. The input is not mutated.
    """
    cid = concept_id or result.exercise_id
    score = float(result.score)

    # Copy so we never mutate the caller's object (important when the ORM row is
    # translated in and out at the /evaluate boundary).
    mastery = dict(skill.mastery)

    prior = mastery.get(cid)
    if prior is None:
        # First observation for this concept: seed directly with the score.
        new_mastery = score
    else:
        new_mastery = (1.0 - _EWMA_ALPHA) * float(prior) + _EWMA_ALPHA * score

    # Clamp defensively (confloat on the contract also enforces [0,1]).
    mastery[cid] = max(0.0, min(1.0, new_mastery))

    weak_concepts = sorted(c for c, m in mastery.items() if m < _WEAK_THRESHOLD)

    return SkillModel(
        learner_id=skill.learner_id,
        curriculum_id=skill.curriculum_id,
        mastery=mastery,
        weak_concepts=weak_concepts,
    )
