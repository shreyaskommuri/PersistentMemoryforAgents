from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .models import GCAction, GCStats, MemoryEntry, MemoryType, ScoreBreakdown
from .retrieval import build_score_breakdown
from .storage import MemoryStore

# Hours a memory may sit at near-zero composite score before forced demotion.
# This is a backstop for memories that score so low recency can't save them —
# not a primary GC driver. High-importance memories will score above thresholds
# and be kept regardless of age.
TIER_MAX_AGE_HOURS: dict[MemoryType, int] = {
    MemoryType.working: 4,
    MemoryType.episodic: 72,
    MemoryType.semantic: 30 * 24,
}

# Score thresholds driving tier changes.
# Note: max achievable GC score (no query) = 0.3 + 0.2 + 0.1 = 0.6.
PROMOTION_THRESHOLD = 0.45
DEMOTION_THRESHOLD = 0.25
ARCHIVE_THRESHOLD = 0.10
DELETE_THRESHOLD = 0.05

_TIER_ORDER = [
    MemoryType.working,
    MemoryType.episodic,
    MemoryType.semantic,
    MemoryType.archived,
]


def _promote(t: MemoryType) -> MemoryType:
    return _TIER_ORDER[max(0, _TIER_ORDER.index(t) - 1)]


def _demote(t: MemoryType) -> MemoryType:
    return _TIER_ORDER[min(len(_TIER_ORDER) - 1, _TIER_ORDER.index(t) + 1)]


@dataclass
class _Decision:
    """Internal GC decision record. Carries everything needed for lifecycle logging."""
    memory_id: str
    content_preview: str
    from_tier: MemoryType
    token_count: int
    new_tier: Optional[MemoryType]  # None means deletion
    action: GCAction
    reason: str
    breakdown: ScoreBreakdown


class GarbageCollector:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def _analyze_entry(self, entry: MemoryEntry) -> _Decision:
        """Pure analysis — no side effects. Returns the decision that GC would make."""
        breakdown = build_score_breakdown(entry)
        score = breakdown.composite
        age_hours = breakdown.age_hours

        # Age-based demotion only fires when the composite score is already low.
        # This prevents age from overriding genuinely high-value memories whose
        # recency component has decayed but importance/frequency keep them useful.
        max_age = TIER_MAX_AGE_HOURS.get(entry.memory_type)
        if max_age and age_hours > max_age and score <= DEMOTION_THRESHOLD:
            new_tier = _demote(entry.memory_type)
            action = GCAction.archive if new_tier == MemoryType.archived else GCAction.demote
            reason = (
                f"Idle {age_hours:.1f}h exceeds {entry.memory_type} max age of {max_age}h "
                f"and score {score:.3f} ≤ demotion threshold"
            )
            return self._decision(entry, new_tier, action, reason, breakdown)

        if score >= PROMOTION_THRESHOLD and entry.memory_type != MemoryType.working:
            new_tier = _promote(entry.memory_type)
            reason = (
                f"Score {score:.3f} ≥ promotion threshold {PROMOTION_THRESHOLD} "
                f"(importance={entry.importance:.2f}, recency={breakdown.recency:.2f})"
            )
            return self._decision(entry, new_tier, GCAction.promote, reason, breakdown)

        if score <= DELETE_THRESHOLD and entry.memory_type == MemoryType.archived:
            reason = f"Score {score:.3f} ≤ delete threshold {DELETE_THRESHOLD}, already archived"
            return self._decision(entry, None, GCAction.delete, reason, breakdown)

        if score <= ARCHIVE_THRESHOLD and entry.memory_type != MemoryType.archived:
            reason = f"Score {score:.3f} ≤ archive threshold {ARCHIVE_THRESHOLD}"
            return self._decision(
                entry, MemoryType.archived, GCAction.archive, reason, breakdown
            )

        if (
            score <= DEMOTION_THRESHOLD
            and entry.memory_type not in (MemoryType.working, MemoryType.archived)
        ):
            new_tier = _demote(entry.memory_type)
            reason = f"Score {score:.3f} ≤ demotion threshold {DEMOTION_THRESHOLD}"
            return self._decision(entry, new_tier, GCAction.demote, reason, breakdown)

        reason = f"Score {score:.3f} within normal range for {entry.memory_type} tier"
        return self._decision(entry, entry.memory_type, GCAction.keep, reason, breakdown)

    @staticmethod
    def _decision(
        entry: MemoryEntry,
        new_tier: Optional[MemoryType],
        action: GCAction,
        reason: str,
        breakdown: ScoreBreakdown,
    ) -> _Decision:
        return _Decision(
            memory_id=entry.id,
            content_preview=entry.content[:80],
            from_tier=entry.memory_type,
            token_count=entry.token_count,
            new_tier=new_tier,
            action=action,
            reason=reason,
            breakdown=breakdown,
        )

    def analyze(self, memory_id: str) -> Optional[_Decision]:
        """Analyze a single memory with no side effects."""
        entry = self._store.get(memory_id)
        return self._analyze_entry(entry) if entry else None

    def preview(self) -> list[_Decision]:
        """Dry-run over all memories — no side effects."""
        return [self._analyze_entry(e) for e in self._store.all()]

    def run(self) -> tuple[GCStats, list[_Decision]]:
        """Apply GC decisions and return stats + the decisions that were made."""
        stats = GCStats(promoted=0, demoted=0, archived=0, deleted=0)
        decisions = [self._analyze_entry(e) for e in self._store.all()]

        for d in decisions:
            if d.action == GCAction.keep:
                continue
            entry = self._store.get(d.memory_id)
            if not entry:
                continue
            if d.action in (GCAction.promote, GCAction.demote, GCAction.archive):
                entry.memory_type = d.new_tier
                self._store.update(entry)
                if d.action == GCAction.promote:
                    stats.promoted += 1
                elif d.action == GCAction.demote:
                    stats.demoted += 1
                else:
                    stats.archived += 1
            elif d.action == GCAction.delete:
                self._store.delete(d.memory_id)
                stats.deleted += 1

        return stats, decisions
