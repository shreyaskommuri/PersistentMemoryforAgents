from __future__ import annotations

import threading
from typing import Optional

from .models import MemoryEntry, MemoryType


class MemoryStore:
    """Thread-safe in-memory store. Swap this class to add persistence."""

    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}
        self._lock = threading.RLock()

    def add(self, entry: MemoryEntry) -> MemoryEntry:
        with self._lock:
            self._store[entry.id] = entry
            return entry

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        with self._lock:
            return self._store.get(memory_id)

    def update(self, entry: MemoryEntry) -> MemoryEntry:
        with self._lock:
            self._store[entry.id] = entry
            return entry

    def delete(self, memory_id: str) -> bool:
        with self._lock:
            if memory_id in self._store:
                del self._store[memory_id]
                return True
            return False

    def all(self, memory_types: Optional[list[MemoryType]] = None) -> list[MemoryEntry]:
        with self._lock:
            entries = list(self._store.values())
        if memory_types:
            entries = [e for e in entries if e.memory_type in memory_types]
        return entries

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
