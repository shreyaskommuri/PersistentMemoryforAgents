from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query

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
)

app = FastAPI(
    title="PersistentMemoryforAgents",
    description="Adaptive memory runtime for long-running AI agents.",
    version="0.1.0",
)

manager = MemoryManager()


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
def add_memory(req: AddMemoryRequest) -> MemoryEntry:
    return manager.add(req)


@app.get("/memories/search", response_model=list[MemorySearchResult])
def search_memories(
    q: str = Query(..., description="Search query text"),
    memory_type: Optional[MemoryType] = Query(default=None),
    tags: Optional[str] = Query(default=None, description="Comma-separated tag filter"),
    limit: int = Query(default=10, ge=1, le=100),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
) -> list[MemorySearchResult]:
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    query = SearchQuery(
        query=q,
        memory_types=[memory_type] if memory_type else None,
        tags=tag_list,
        limit=limit,
        min_score=min_score,
    )
    return manager.search(query)


@app.get("/memories/context", response_model=ContextResponse)
def get_context(
    q: Optional[str] = Query(default=None, description="Optional query to rank memories"),
    token_budget: int = Query(default=4096, ge=1, le=32768),
    memory_type: Optional[MemoryType] = Query(default=None),
) -> ContextResponse:
    req = ContextRequest(
        query=q,
        token_budget=token_budget,
        memory_types=[memory_type] if memory_type else None,
    )
    return manager.get_context(req)


@app.get("/memories", response_model=list[MemoryEntry])
def list_memories(
    memory_type: Optional[MemoryType] = Query(default=None),
) -> list[MemoryEntry]:
    return manager.list_all([memory_type] if memory_type else None)


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


# ── Graph ─────────────────────────────────────────────────────────────────── #


@app.get("/graph/{entity}", response_model=GraphNeighbors)
def graph_neighbors(entity: str) -> GraphNeighbors:
    return manager.graph_neighbors(entity)


# ── Garbage collection ────────────────────────────────────────────────────── #


@app.post("/gc", response_model=GCStats)
def run_gc() -> GCStats:
    return manager.run_gc()
