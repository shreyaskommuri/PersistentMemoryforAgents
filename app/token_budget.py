from __future__ import annotations

import math
from functools import lru_cache

from .models import MemoryEntry, MemoryType

# Soft token limits per tier — used by the context assembler and GC docs.
TIER_TOKEN_LIMITS: dict[MemoryType, int] = {
    MemoryType.working: 2_000,
    MemoryType.episodic: 8_000,
    MemoryType.semantic: 32_000,
    MemoryType.archived: 128_000,
}


@lru_cache(maxsize=1)
def _encoder():
    """Load the tiktoken cl100k_base encoder once and reuse it.

    cl100k_base is the closest public approximation to Claude's BPE tokenizer.
    Falls back to a word-count heuristic if tiktoken is not installed.
    """
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        return None


def count_tokens(text: str) -> int:
    """Count tokens in a string using tiktoken, or a word-count heuristic as fallback."""
    enc = _encoder()
    if enc is not None:
        return max(1, len(enc.encode(text)))
    # Fallback: ~1.3 tokens per whitespace-delimited word (BPE approximation)
    return max(1, math.ceil(len(text.split()) * 1.3))


def count_entry_tokens(entry: MemoryEntry) -> int:
    parts = [entry.content] + entry.tags + entry.linked_entities
    return count_tokens(" ".join(parts))


class TokenBudgetManager:
    def __init__(self, total_budget: int = 4096) -> None:
        self.total_budget = total_budget

    def allocate(self, memories: list[MemoryEntry]) -> list[MemoryEntry]:
        """Pack memories greedily in score order until the token budget is exhausted."""
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
