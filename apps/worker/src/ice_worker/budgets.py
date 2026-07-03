"""Per-curriculum token budget enforcement (cost control, risk E16).

Tracks token spend against LLM_TOKEN_BUDGET_PER_CURRICULUM; flips to the cheap
fallback model tier when the budget is exceeded; pauses the pipeline if a
tenant quota is hit (§6.4 degradation).
"""
from __future__ import annotations


class TokenBudget:
    def __init__(self, curriculum_id: str, limit: int) -> None:
        self.curriculum_id = curriculum_id
        self.limit = limit
        self.spent = 0

    def consume(self, tokens: int) -> bool:
        """Returns True if within budget; False if exceeded (triggers fallback)."""
        if self.spent + tokens > self.limit:
            return False
        self.spent += tokens
        return True
