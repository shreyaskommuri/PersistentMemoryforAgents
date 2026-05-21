from __future__ import annotations

from typing import Optional

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from .dashboard import HTML
from .memory_manager import MemoryManager
from .models import (
    AddMemoryRequest,
    ContextRequest,
    ContextResponse,
    DetailedStats,
    GCPreview,
    GCStats,
    GraphNeighbors,
    MemoryEntry,
    MemoryInspect,
    MemoryLineage,
    MemorySearchResult,
    MemoryType,
    SearchQuery,
    SnapshotImportResult,
)

app = FastAPI(
    title="PersistentMemoryforAgents",
    description="Adaptive memory runtime for long-running AI agents.",
    version="0.1.0",
)

_STORE_PATH = Path.home() / ".pma_store.json"
_ACTIVITY_PATH = Path.home() / ".pma_activity.json"

manager = MemoryManager()
manager._store.load_from_file(str(_STORE_PATH))


def _save() -> None:
    manager._store.save_to_file(str(_STORE_PATH))


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    return HTML


@app.post("/reload")
def reload_store() -> dict:
    manager._store.load_from_file(str(_STORE_PATH))
    return {"loaded": manager._store.count()}


@app.get("/activity")
def activity(limit: int = Query(default=20, ge=1, le=50)) -> list[dict]:
    try:
        log = json.loads(_ACTIVITY_PATH.read_text())
        return log[:limit]
    except Exception:
        return []


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict:
    return manager.stats()


# ── Observability dashboard ────────────────────────────────────────────────


@app.get("/memory/stats", response_model=DetailedStats)
def detailed_stats() -> DetailedStats:
    return manager.detailed_stats()


@app.get("/memory/inspect/{memory_id}", response_model=MemoryInspect)
def inspect_memory(memory_id: str) -> MemoryInspect:
    result = manager.inspect(memory_id)
    if not result:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result


@app.get("/memory/gc/preview", response_model=GCPreview)
def gc_preview() -> GCPreview:
    return manager.gc_preview()


@app.get("/memory/lineage/{memory_id}", response_model=MemoryLineage)
def memory_lineage(memory_id: str) -> MemoryLineage:
    result = manager.lineage(memory_id)
    if not result:
        raise HTTPException(status_code=404, detail="No lifecycle events found for this memory")
    return result


# ── Memories ──────────────────────────────────────────────────────────────── #


@app.post("/memories", response_model=MemoryEntry, status_code=201)
def add_memory(
    req: AddMemoryRequest,
    namespace: str = Query(default="default", description="Memory namespace / project scope"),
) -> MemoryEntry:
    req.namespace = namespace
    entry = manager.add(req)
    _save()
    return entry


@app.get("/memories/search", response_model=list[MemorySearchResult])
def search_memories(
    q: str = Query(..., description="Search query text"),
    memory_type: Optional[MemoryType] = Query(default=None),
    tags: Optional[str] = Query(default=None, description="Comma-separated tag filter"),
    limit: int = Query(default=10, ge=1, le=100),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    namespace: Optional[str] = Query(default="default", description="Memory namespace / project scope"),
) -> list[MemorySearchResult]:
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    query = SearchQuery(
        query=q,
        memory_types=[memory_type] if memory_type else None,
        tags=tag_list,
        limit=limit,
        min_score=min_score,
        namespace=namespace,
    )
    return manager.search(query)


@app.get("/memories/context", response_model=ContextResponse)
def get_context(
    q: Optional[str] = Query(default=None, description="Optional query to rank memories"),
    token_budget: int = Query(default=4096, ge=1, le=32768),
    memory_type: Optional[MemoryType] = Query(default=None),
    namespace: Optional[str] = Query(default="default", description="Memory namespace / project scope"),
) -> ContextResponse:
    req = ContextRequest(
        query=q,
        token_budget=token_budget,
        memory_types=[memory_type] if memory_type else None,
        namespace=namespace,
    )
    return manager.get_context(req)


@app.get("/memories", response_model=list[MemoryEntry])
def list_memories(
    memory_type: Optional[MemoryType] = Query(default=None),
    namespace: Optional[str] = Query(default=None, description="Filter by namespace (omit for all)"),
) -> list[MemoryEntry]:
    return manager.list_all([memory_type] if memory_type else None, namespace=namespace)


# ── Snapshots ────────────────────────────────────────────────────────────── #
# Must be registered before /memories/{memory_id} or FastAPI matches them as IDs.


@app.get("/memories/export")
def export_memories(
    namespace: Optional[str] = Query(default=None, description="Export one namespace (omit for all)"),
) -> list[dict]:
    entries = manager.list_all(namespace=namespace)
    return [e.model_dump(mode="json") for e in entries]


@app.post("/memories/import", response_model=SnapshotImportResult, status_code=200)
def import_memories(
    snapshot: list[dict],
    namespace: Optional[str] = Query(default=None, description="Override namespace for all imported entries"),
    skip_existing: bool = Query(default=True, description="Skip entries whose ID already exists"),
) -> SnapshotImportResult:
    imported = skipped = 0
    for raw in snapshot:
        try:
            entry = MemoryEntry.model_validate(raw)
        except Exception:
            skipped += 1
            continue
        if namespace is not None:
            entry.namespace = namespace
        if skip_existing and manager._store.get(entry.id):
            skipped += 1
            continue
        manager._store.add(entry)
        imported += 1
    if imported:
        _save()
    return SnapshotImportResult(
        imported=imported,
        skipped=skipped,
        total_in_snapshot=len(snapshot),
    )


@app.get("/memories/{memory_id}", response_model=MemoryEntry)
def get_memory(memory_id: str) -> MemoryEntry:
    entry = manager.get(memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    return entry


@app.get("/memories/{memory_id}/linked", response_model=list[MemoryEntry])
def linked_memories(memory_id: str) -> list[MemoryEntry]:
    if not manager._store.get(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return manager.linked_memories(memory_id)


@app.delete("/memories/{memory_id}", status_code=204)
def delete_memory(memory_id: str) -> None:
    if not manager.delete(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    _save()


# ── Graph ─────────────────────────────────────────────────────────────────── #


@app.get("/graph/{entity}", response_model=GraphNeighbors)
def graph_neighbors(entity: str) -> GraphNeighbors:
    return manager.graph_neighbors(entity)


# ── Garbage collection ────────────────────────────────────────────────────── #


@app.post("/gc", response_model=GCStats)
def run_gc() -> GCStats:
    stats = manager.run_gc()
    _save()
    return stats
