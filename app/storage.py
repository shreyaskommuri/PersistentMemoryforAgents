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

    def all(
        self,
        memory_types: Optional[list[MemoryType]] = None,
        namespace: Optional[str] = None,
    ) -> list[MemoryEntry]:
        with self._lock:
            entries = list(self._store.values())
        if memory_types:
            entries = [e for e in entries if e.memory_type in memory_types]
        if namespace is not None:
            entries = [e for e in entries if e.namespace == namespace]
        return entries

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def save_to_file(self, path: str) -> None:
        """Persist the store to a JSON file (best-effort, never raises).

        Uses an atomic write (temp file + rename) so readers never see a
        partially written file.
        """
        import json
        import os
        import tempfile
        try:
            with self._lock:
                data = {k: v.model_dump(mode="json") for k, v in self._store.items()}
            dir_path = os.path.dirname(os.path.abspath(path))
            with tempfile.NamedTemporaryFile("w", dir=dir_path, delete=False, suffix=".tmp") as f:
                json.dump(data, f, indent=2)
                tmp = f.name
            os.replace(tmp, path)  # atomic on POSIX — readers see old or new, never partial
        except Exception:
            pass

    def load_from_file(self, path: str) -> None:
        """Load memories from a JSON file produced by save_to_file (best-effort)."""
        import json
        try:
            with open(path) as f:
                data = json.load(f)
            with self._lock:
                self._store = {k: MemoryEntry.model_validate(v) for k, v in data.items()}
        except FileNotFoundError:
            pass  # first run — no store yet
        except Exception:
            pass  # corrupt file — start fresh
