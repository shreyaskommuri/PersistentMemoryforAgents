from __future__ import annotations

import math

from .models import MemoryEntry, MemoryType

# Informational reference limits per tier (not enforced by storage, used by GC and docs).
TIER_TOKEN_LIMITS: dict[MemoryType, int] = {
    MemoryType.working: 2_000,
    MemoryType.episodic: 8_000,
    MemoryType.semantic: 32_000,
    MemoryType.archived: 128_000,
}


def estimate_tokens(text: str) -> int:
    """Approximate token count: ~1.3 tokens per whitespace-delimited word."""
    words = len(text.split())
    return max(1, math.ceil(words * 1.3))


def count_entry_tokens(entry: MemoryEntry) -> int:
    parts = [entry.content] + entry.tags + entry.linked_entities
    return estimate_tokens(" ".join(parts))


class TokenBudgetManager:
    def __init__(self, total_budget: int = 4096) -> None:
        self.total_budget = total_budget

    def allocate(self, memories: list[MemoryEntry]) -> list[MemoryEntry]:
        """Pack memories greedily in order until the token budget is exhausted."""
        result: list[MemoryEntry] = []
        used = 0
        for mem in memories:
            tokens = mem.token_count or count_entry_tokens(mem)
            if used + tokens > self.total_budget:
                continue
            result.append(mem)
            used += tokens
        return result

    def usage_fraction(self, memories: list[MemoryEntry]) -> float:
        used = sum(m.token_count or count_entry_tokens(m) for m in memories)
        return min(1.0, used / self.total_budget)
