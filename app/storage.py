from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Optional

from .models import MemoryEntry, MemoryType


class _DictStore:
    """Purely in-memory store. Used when PMA_STORAGE=memory (tests, dev)."""

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
        pass  # memory-only mode — nothing to persist

    def load_from_file(self, path: str) -> None:
        pass  # memory-only mode — nothing to load


class _SQLiteStore:
    """SQLite-backed store via SQLAlchemy. Default backend."""

    _CREATE = """
        CREATE TABLE IF NOT EXISTS memories (
            id              TEXT PRIMARY KEY,
            content         TEXT NOT NULL,
            memory_type     TEXT NOT NULL,
            importance      REAL NOT NULL,
            tags            TEXT NOT NULL,
            linked_entities TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            accessed_at     TEXT NOT NULL,
            access_count    INTEGER NOT NULL DEFAULT 0,
            token_count     INTEGER NOT NULL DEFAULT 0,
            namespace       TEXT NOT NULL DEFAULT 'default',
            metadata        TEXT NOT NULL
        )
    """

    def __init__(self, db_url: str) -> None:
        from sqlalchemy import create_engine
        self._engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        from sqlalchemy import text
        with self._engine.connect() as conn:
            conn.execute(text(self._CREATE))
            conn.commit()

    @staticmethod
    def _row_to_entry(row) -> MemoryEntry:
        return MemoryEntry(
            id=row[0],
            content=row[1],
            memory_type=row[2],
            importance=row[3],
            tags=json.loads(row[4]),
            linked_entities=json.loads(row[5]),
            created_at=row[6],
            accessed_at=row[7],
            access_count=row[8],
            token_count=row[9],
            namespace=row[10],
            metadata=json.loads(row[11]),
        )

    @staticmethod
    def _entry_params(entry: MemoryEntry) -> dict:
        return {
            "id": entry.id,
            "content": entry.content,
            "memory_type": entry.memory_type.value,
            "importance": entry.importance,
            "tags": json.dumps(entry.tags),
            "linked_entities": json.dumps(entry.linked_entities),
            "created_at": entry.created_at.isoformat(),
            "accessed_at": entry.accessed_at.isoformat(),
            "access_count": entry.access_count,
            "token_count": entry.token_count,
            "namespace": entry.namespace,
            "metadata": json.dumps(entry.metadata),
        }

    def add(self, entry: MemoryEntry) -> MemoryEntry:
        from sqlalchemy import text
        sql = text("""
            INSERT INTO memories
                (id, content, memory_type, importance, tags, linked_entities,
                 created_at, accessed_at, access_count, token_count, namespace, metadata)
            VALUES
                (:id, :content, :memory_type, :importance, :tags, :linked_entities,
                 :created_at, :accessed_at, :access_count, :token_count, :namespace, :metadata)
        """)
        with self._lock:
            with self._engine.connect() as conn:
                conn.execute(sql, self._entry_params(entry))
                conn.commit()
        return entry

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        from sqlalchemy import text
        with self._lock:
            with self._engine.connect() as conn:
                row = conn.execute(
                    text("SELECT * FROM memories WHERE id = :id"), {"id": memory_id}
                ).fetchone()
        return self._row_to_entry(row) if row else None

    def update(self, entry: MemoryEntry) -> MemoryEntry:
        from sqlalchemy import text
        sql = text("""
            UPDATE memories SET
                content=:content, memory_type=:memory_type, importance=:importance,
                tags=:tags, linked_entities=:linked_entities, created_at=:created_at,
                accessed_at=:accessed_at, access_count=:access_count,
                token_count=:token_count, namespace=:namespace, metadata=:metadata
            WHERE id=:id
        """)
        with self._lock:
            with self._engine.connect() as conn:
                conn.execute(sql, self._entry_params(entry))
                conn.commit()
        return entry

    def delete(self, memory_id: str) -> bool:
        from sqlalchemy import text
        with self._lock:
            with self._engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM memories WHERE id = :id"), {"id": memory_id}
                )
                conn.commit()
                return result.rowcount > 0

    def all(
        self,
        memory_types: Optional[list[MemoryType]] = None,
        namespace: Optional[str] = None,
    ) -> list[MemoryEntry]:
        from sqlalchemy import text
        conditions: list[str] = []
        params: dict = {}
        if memory_types:
            placeholders = ", ".join(f":t{i}" for i in range(len(memory_types)))
            conditions.append(f"memory_type IN ({placeholders})")
            for i, t in enumerate(memory_types):
                params[f"t{i}"] = t.value
        if namespace is not None:
            conditions.append("namespace = :namespace")
            params["namespace"] = namespace
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._lock:
            with self._engine.connect() as conn:
                rows = conn.execute(text(f"SELECT * FROM memories {where}"), params).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def count(self) -> int:
        from sqlalchemy import text
        with self._lock:
            with self._engine.connect() as conn:
                return conn.execute(text("SELECT COUNT(*) FROM memories")).scalar() or 0

    def clear(self) -> None:
        from sqlalchemy import text
        with self._lock:
            with self._engine.connect() as conn:
                conn.execute(text("DELETE FROM memories"))
                conn.commit()

    def save_to_file(self, path: str) -> None:
        pass  # SQLite writes are immediate — nothing to flush

    def load_from_file(self, path: str) -> None:
        """One-time migration from the legacy JSON store if the DB is empty."""
        if self.count() > 0:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for entry_data in data.values():
                self.add(MemoryEntry.model_validate(entry_data))
        except FileNotFoundError:
            pass
        except Exception:
            pass


def MemoryStore() -> "_DictStore | _SQLiteStore":
    """Factory: returns the backend selected by PMA_STORAGE env var.

    PMA_STORAGE=sqlite  (default) — durable SQLite file at PMA_DB_PATH
    PMA_STORAGE=memory             — in-process dict, no persistence (tests/dev)
    """
    backend = os.environ.get("PMA_STORAGE", "sqlite")
    if backend == "memory":
        return _DictStore()
    db_path = os.environ.get("PMA_DB_PATH", str(Path.home() / ".pma_store.db"))
    return _SQLiteStore(f"sqlite:///{db_path}")
