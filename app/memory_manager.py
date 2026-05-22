from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .garbage_collector import GarbageCollector, _Decision
from .graph_memory import GraphMemory
from .models import (
    AddMemoryRequest,
    ContextRequest,
    ContextResponse,
    DetailedStats,
    GCAction,
    GCPreview,
    GCPreviewEntry,
    GCStats,
    GraphNeighbors,
    LifecycleEvent,
    MemoryEntry,
    MemoryInspect,
    MemoryLineage,
    MemorySearchResult,
    MemoryType,
    SearchQuery,
    TierStats,
)
from .retrieval import Retriever, build_score_breakdown, composite_score
from .storage import MemoryStore
from .token_budget import TokenBudgetManager, count_entry_tokens


class MemoryManager:
    """Central orchestrator. Routes all agent requests to the appropriate subsystem."""

    def __init__(self) -> None:
        self._store = MemoryStore()
        self._retriever = Retriever()
        self._gc = GarbageCollector(self._store)
        self._graph = GraphMemory(self._store)
        self._lifecycle: dict[str, list[LifecycleEvent]] = {}

    # ------------------------------------------------------------------ #
    # Lifecycle tracking (internal)                                        #
    # ------------------------------------------------------------------ #

    def _record(
        self,
        memory_id: str,
        event_type: str,
        from_tier: Optional[MemoryType] = None,
        to_tier: Optional[MemoryType] = None,
        trigger: str = "",
        score: Optional[float] = None,
    ) -> None:
        event = LifecycleEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            from_tier=from_tier,
            to_tier=to_tier,
            trigger=trigger,
            score=score,
        )
        self._lifecycle.setdefault(memory_id, []).append(event)

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def add(self, req: AddMemoryRequest) -> MemoryEntry:
        entry = MemoryEntry(
            content=req.content,
            memory_type=req.memory_type,
            importance=req.importance,
            tags=req.tags,
            linked_entities=req.linked_entities,
            namespace=req.namespace,
            metadata=req.metadata,
        )
        entry.token_count = count_entry_tokens(entry)
        self._store.add(entry)
        self._record(entry.id, "created", to_tier=entry.memory_type, trigger="user")
        return entry

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        entry = self._store.get(memory_id)
        if entry:
            entry.access_count += 1
            entry.accessed_at = datetime.now(timezone.utc)
            self._store.update(entry)
            self._record(
                memory_id, "accessed",
                from_tier=entry.memory_type, to_tier=entry.memory_type,
                trigger="user",
            )
        return entry

    def delete(self, memory_id: str) -> bool:
        entry = self._store.get(memory_id)
        if entry:
            self._record(memory_id, "deleted", from_tier=entry.memory_type, trigger="user")
        return self._store.delete(memory_id)

    def list_all(
        self,
        memory_types: Optional[list[MemoryType]] = None,
        namespace: Optional[str] = None,
    ) -> list[MemoryEntry]:
        return self._store.all(memory_types, namespace=namespace)

    # ------------------------------------------------------------------ #
    # Search                                                               #
    # ------------------------------------------------------------------ #

    def search(self, query: SearchQuery) -> list[MemorySearchResult]:
        corpus = self._store.all(namespace=query.namespace)
        results = self._retriever.search(
            query=query.query,
            corpus=corpus,
            tags=query.tags,
            memory_types=query.memory_types,
            limit=query.limit,
            min_score=query.min_score,
        )
        for result in results:
            result.memory.access_count += 1
            result.memory.accessed_at = datetime.now(timezone.utc)
            self._store.update(result.memory)
        return results

    # ------------------------------------------------------------------ #
    # Context window assembly                                              #
    # ------------------------------------------------------------------ #

    def get_context(self, req: ContextRequest) -> ContextResponse:
        budget = TokenBudgetManager(total_budget=req.token_budget)
        corpus = self._store.all(req.memory_types, namespace=req.namespace)

        if req.query:
            results = self._retriever.search(
                query=req.query,
                corpus=corpus,
                memory_types=req.memory_types,
                limit=len(corpus) or 1,
            )
            ordered = [r.memory for r in results]
        else:
            ordered = sorted(corpus, key=composite_score, reverse=True)

        selected = budget.allocate(ordered)
        total_tokens = sum(m.token_count or count_entry_tokens(m) for m in selected)
        return ContextResponse(
            memories=selected,
            total_tokens=total_tokens,
            budget_used=budget.usage_fraction(selected),
        )

    # ------------------------------------------------------------------ #
    # Graph                                                                #
    # ------------------------------------------------------------------ #

    def graph_neighbors(self, entity: str) -> GraphNeighbors:
        return self._graph.neighbors(entity)

    def linked_memories(self, memory_id: str) -> list[MemoryEntry]:
        entry = self._store.get(memory_id)
        if not entry:
            return []
        return self._graph.linked_memories(entry)

    # ------------------------------------------------------------------ #
    # Garbage collection                                                   #
    # ------------------------------------------------------------------ #

    def run_gc(self) -> GCStats:
        stats, decisions = self._gc.run()
        for d in decisions:
            if d.action != GCAction.keep:
                self._record(
                    d.memory_id,
                    d.action.value,
                    from_tier=d.from_tier,
                    to_tier=d.new_tier,
                    trigger=f"gc — {d.reason}",
                    score=d.breakdown.composite,
                )
        return stats

    # ------------------------------------------------------------------ #
    # Observability                                                        #
    # ------------------------------------------------------------------ #

    def inspect(self, memory_id: str) -> Optional[MemoryInspect]:
        entry = self._store.get(memory_id)
        if not entry:
            return None
        decision = self._gc.analyze(memory_id)
        breakdown = build_score_breakdown(entry)
        return MemoryInspect(
            memory=entry,
            score_breakdown=breakdown,
            gc_action=decision.action,
            gc_reason=decision.reason,
            predicted_tier=decision.new_tier,
        )

    def gc_preview(self) -> GCPreview:
        decisions = self._gc.preview()
        to_promote: list[GCPreviewEntry] = []
        to_demote: list[GCPreviewEntry] = []
        to_archive: list[GCPreviewEntry] = []
        to_delete: list[GCPreviewEntry] = []
        to_keep: list[GCPreviewEntry] = []
        token_delta = 0

        for d in decisions:
            entry = GCPreviewEntry(
                memory_id=d.memory_id,
                content_preview=d.content_preview,
                current_tier=d.from_tier,
                predicted_tier=d.new_tier,
                action=d.action,
                reason=d.reason,
                score=d.breakdown.composite,
                score_breakdown=d.breakdown,
            )
            if d.action == GCAction.promote:
                to_promote.append(entry)
            elif d.action == GCAction.demote:
                to_demote.append(entry)
            elif d.action == GCAction.archive:
                to_archive.append(entry)
                if d.from_tier != MemoryType.archived:
                    token_delta += d.token_count
            elif d.action == GCAction.delete:
                to_delete.append(entry)
                token_delta += d.token_count
            else:
                to_keep.append(entry)

        total = len(decisions)
        affected = len(to_promote) + len(to_demote) + len(to_archive) + len(to_delete)
        summary = (
            f"GC would affect {affected} of {total} memories: "
            f"{len(to_promote)} promoted, {len(to_demote)} demoted, "
            f"{len(to_archive)} archived, {len(to_delete)} deleted. "
            f"Would free {token_delta} tokens from active tiers."
        )
        return GCPreview(
            to_promote=to_promote,
            to_demote=to_demote,
            to_archive=to_archive,
            to_delete=to_delete,
            to_keep=to_keep,
            total_affected=affected,
            token_delta=token_delta,
            summary=summary,
        )

    def lineage(self, memory_id: str) -> Optional[MemoryLineage]:
        events = self._lifecycle.get(memory_id)
        if not events:
            return None

        entry = self._store.get(memory_id)
        if entry:
            current_tier = entry.memory_type
        else:
            # Memory was deleted — reconstruct tier from last event before deletion
            deleted = [e for e in events if e.event_type == "deleted"]
            current_tier = deleted[-1].from_tier if deleted else MemoryType.archived

        created = next((e for e in events if e.event_type == "created"), None)
        if created:
            ct = created.timestamp
            if ct.tzinfo is None:
                ct = ct.replace(tzinfo=timezone.utc)
            age_hours = round((datetime.now(timezone.utc) - ct).total_seconds() / 3600.0, 2)
        else:
            age_hours = 0.0

        return MemoryLineage(
            memory_id=memory_id,
            current_tier=current_tier,
            age_hours=age_hours,
            total_promotions=sum(1 for e in events if e.event_type == "promote"),
            total_demotions=sum(1 for e in events if e.event_type in ("demote", "archive")),
            total_accesses=sum(1 for e in events if e.event_type == "accessed"),
            events=events,
        )

    def detailed_stats(self) -> DetailedStats:
        all_entries = self._store.all()
        empty_tier = TierStats(count=0, total_tokens=0, avg_score=0.0)

        if not all_entries:
            return DetailedStats(
                total=0,
                total_tokens=0,
                by_tier={t.value: empty_tier for t in MemoryType},
                gc_pressure=0,
                avg_composite_score=0.0,
            )

        tier_buckets: dict[str, list[float]] = {t.value: [] for t in MemoryType}
        tier_tokens: dict[str, int] = {t.value: 0 for t in MemoryType}
        all_scores: list[float] = []

        for entry in all_entries:
            score = composite_score(entry)
            tier_buckets[entry.memory_type.value].append(score)
            tier_tokens[entry.memory_type.value] += entry.token_count
            all_scores.append(score)

        by_tier = {
            tier: TierStats(
                count=len(scores),
                total_tokens=tier_tokens[tier],
                avg_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
            )
            for tier, scores in tier_buckets.items()
        }

        decisions = self._gc.preview()
        gc_pressure = sum(1 for d in decisions if d.action != GCAction.keep)

        return DetailedStats(
            total=len(all_entries),
            total_tokens=sum(e.token_count for e in all_entries),
            by_tier=by_tier,
            gc_pressure=gc_pressure,
            avg_composite_score=round(sum(all_scores) / len(all_scores), 4),
        )

    def seed_from_project(self, project_root: str, namespace: str = "default") -> int:
        """
        Read project docs and save key sections as semantic memories.
        Returns the number of memories created.
        Idempotent — skips sections already stored within the same namespace.
        """
        from pathlib import Path

        root = Path(project_root)
        docs = [
            (root / "CLAUDE.md",              0.95, ["guidelines", "meta"]),
            (root / "CODEX.md",               0.90, ["guidelines", "meta"]),
            (root / "docs" / "ARCHITECTURE.md", 0.95, ["architecture"]),
            (root / "docs" / "ROADMAP.md",    0.85, ["roadmap"]),
            (root / "README.md",              0.80, ["overview"]),
        ]

        existing_prefixes = {e.content[:80] for e in self._store.all(namespace=namespace)}
        count = 0

        for doc_path, importance, tags in docs:
            if not doc_path.exists():
                continue
            for section in self._split_markdown(doc_path.read_text()):
                if len(section) < 60:
                    continue
                if section[:80] in existing_prefixes:
                    continue
                self.add(AddMemoryRequest(
                    content=section[:600],
                    memory_type=MemoryType.semantic,
                    importance=importance,
                    tags=tags + [doc_path.stem.lower()],
                    namespace=namespace,
                    metadata={"source": str(doc_path), "seeded": True},
                ))
                existing_prefixes.add(section[:80])
                count += 1

        return count

    @staticmethod
    def _split_markdown(text: str) -> list[str]:
        """Split markdown into sections at ## headings."""
        sections: list[str] = []
        current: list[str] = []
        for line in text.splitlines():
            if line.startswith("## ") and current:
                sections.append("\n".join(current).strip())
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append("\n".join(current).strip())
        return sections

    def recount_tokens(self) -> int:
        """Recompute token_count for every memory using the current tokenizer.

        Run this once after upgrading to tiktoken to fix counts stored under
        the old word-heuristic. Returns the number of memories updated.
        """
        updated = 0
        for entry in self._store.all():
            new_count = count_entry_tokens(entry)
            if new_count != entry.token_count:
                entry.token_count = new_count
                self._store.update(entry)
                updated += 1
        return updated

    def stats(self) -> dict:
        all_entries = self._store.all()
        by_type = {t.value: 0 for t in MemoryType}
        for entry in all_entries:
            by_type[entry.memory_type.value] += 1
        return {
            "total": len(all_entries),
            "by_type": by_type,
            "total_tokens": sum(e.token_count for e in all_entries),
        }
