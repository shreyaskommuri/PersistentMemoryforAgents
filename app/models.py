from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    working = "working"
    episodic = "episodic"
    semantic = "semantic"
    archived = "archived"


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    memory_type: MemoryType = MemoryType.episodic
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    linked_entities: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    token_count: int = 0
    namespace: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AddMemoryRequest(BaseModel):
    content: str
    memory_type: MemoryType = MemoryType.episodic
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    linked_entities: list[str] = Field(default_factory=list)
    namespace: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    query: str
    memory_types: Optional[list[MemoryType]] = None
    tags: Optional[list[str]] = None
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    namespace: Optional[str] = "default"


class MemorySearchResult(BaseModel):
    memory: MemoryEntry
    score: float


class ContextRequest(BaseModel):
    query: Optional[str] = None
    token_budget: int = Field(default=4096, ge=1, le=32768)
    memory_types: Optional[list[MemoryType]] = None
    namespace: Optional[str] = "default"


class ContextResponse(BaseModel):
    memories: list[MemoryEntry]
    total_tokens: int
    budget_used: float


class GCStats(BaseModel):
    promoted: int
    demoted: int
    archived: int
    deleted: int


class GraphNeighbors(BaseModel):
    entity: str
    memories: list[MemoryEntry]
    related_entities: list[str]


# ── Observability models ───────────────────────────────────────────────────


class GCAction(str, Enum):
    promote = "promote"
    demote = "demote"
    archive = "archive"
    delete = "delete"
    keep = "keep"


class ScoreBreakdown(BaseModel):
    """Component-level decomposition of composite_score for a single memory."""
    semantic_sim: float
    importance: float
    recency: float
    access_frequency: float
    composite: float
    age_hours: float


class MemoryInspect(BaseModel):
    """Full diagnostic view of a single memory: score breakdown + GC prediction."""
    memory: MemoryEntry
    score_breakdown: ScoreBreakdown
    gc_action: GCAction
    gc_reason: str
    predicted_tier: Optional[MemoryType]


class GCPreviewEntry(BaseModel):
    memory_id: str
    content_preview: str
    current_tier: MemoryType
    predicted_tier: Optional[MemoryType]
    action: GCAction
    reason: str
    score: float
    score_breakdown: ScoreBreakdown


class GCPreview(BaseModel):
    """Dry-run result: what the GC would do and why, without modifying anything."""
    to_promote: list[GCPreviewEntry]
    to_demote: list[GCPreviewEntry]
    to_archive: list[GCPreviewEntry]
    to_delete: list[GCPreviewEntry]
    to_keep: list[GCPreviewEntry]
    total_affected: int
    token_delta: int
    summary: str


class TierStats(BaseModel):
    count: int
    total_tokens: int
    avg_score: float


class DetailedStats(BaseModel):
    total: int
    total_tokens: int
    by_tier: dict[str, TierStats]
    gc_pressure: int
    avg_composite_score: float


class LifecycleEvent(BaseModel):
    timestamp: datetime
    event_type: str
    from_tier: Optional[MemoryType] = None
    to_tier: Optional[MemoryType] = None
    trigger: str = ""
    score: Optional[float] = None


class MemoryLineage(BaseModel):
    """Full audit trail of tier migrations and access events for a memory."""
    memory_id: str
    current_tier: MemoryType
    age_hours: float
    total_promotions: int
    total_demotions: int
    total_accesses: int
    events: list[LifecycleEvent]


class SnapshotImportResult(BaseModel):
    imported: int
    skipped: int
    total_in_snapshot: int
