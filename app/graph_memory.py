from __future__ import annotations

from collections import defaultdict

from .models import GraphNeighbors, MemoryEntry
from .storage import MemoryStore


class GraphMemory:
    """
    Implicit tag- and entity-indexed memory graph.

    Edges are derived at query time — no separate adjacency store.
    Two memories are neighbors if they share at least one tag or linked entity.
    """

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def neighbors(self, entity: str) -> GraphNeighbors:
        """Return all memories touching this entity/tag and their related nodes."""
        tag_index, entity_index = self._build_indexes()
        key = entity.lower()
        memory_ids = set(entity_index.get(key, [])) | set(tag_index.get(key, []))

        memories: list[MemoryEntry] = []
        related: set[str] = set()
        for mid in memory_ids:
            entry = self._store.get(mid)
            if entry:
                memories.append(entry)
                related.update(e.lower() for e in entry.linked_entities)
                related.update(t.lower() for t in entry.tags)
        related.discard(key)

        return GraphNeighbors(
            entity=entity, memories=memories, related_entities=sorted(related)
        )

    def linked_memories(self, entry: MemoryEntry) -> list[MemoryEntry]:
        """Return memories that share at least one tag or entity with the given entry."""
        keys = {t.lower() for t in entry.tags} | {e.lower() for e in entry.linked_entities}
        if not keys:
            return []

        tag_index, entity_index = self._build_indexes()
        related_ids: set[str] = set()
        for k in keys:
            related_ids.update(tag_index.get(k, []))
            related_ids.update(entity_index.get(k, []))
        related_ids.discard(entry.id)

        return [e for mid in related_ids if (e := self._store.get(mid)) is not None]

    def _build_indexes(self) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        tag_index: dict[str, list[str]] = defaultdict(list)
        entity_index: dict[str, list[str]] = defaultdict(list)
        for entry in self._store.all():
            for tag in entry.tags:
                tag_index[tag.lower()].append(entry.id)
            for entity in entry.linked_entities:
                entity_index[entity.lower()].append(entry.id)
        return tag_index, entity_index
