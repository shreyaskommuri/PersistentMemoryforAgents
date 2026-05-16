# Architecture

PersistentMemoryforAgents is an OS-inspired memory management layer for long-running AI agents. It organizes agent memory into four tiers modeled after the CPU/OS memory hierarchy, with automatic promotion, demotion, and garbage collection driven by composite importance scores.

---

## Memory tiers

| Tier | OS analogy | Approx. token limit | Max idle age |
|------|-----------|---------------------|--------------|
| `working` | L1 CPU cache | 2,000 | 1 hour |
| `episodic` | L2 CPU cache | 8,000 | 24 hours |
| `semantic` | RAM | 32,000 | 7 days |
| `archived` | Disk | Unlimited | Indefinite |

Memories start in the tier specified at creation time and migrate automatically. A hot memory (high access frequency, high importance) climbs toward `working`; a cold one sinks toward `archived` and eventually gets deleted.

---

## Composite scoring

Every memory receives a score in **[0, 1]** computed at query time:

```
score = 0.4 × semantic_similarity
      + 0.3 × importance
      + 0.2 × recency_score
      + 0.1 × access_frequency
```

| Component | Formula | Notes |
|-----------|---------|-------|
| `semantic_similarity` | TF-IDF cosine sim vs. query | 0.0 when no query |
| `importance` | User-supplied, in [0, 1] | Set at creation |
| `recency_score` | `exp(-0.1 × age_hours)` | Half-life ≈ 7 h |
| `access_frequency` | `min(log1p(count) / 10, 1.0)` | Log-normalized |

Weights sum to 1.0. Changing them changes every retrieval and GC decision — see `app/retrieval.py:composite_score`.

---

## Retrieval

`Retriever` (in `app/retrieval.py`) builds a fresh TF-IDF matrix over the candidate corpus using scikit-learn's `TfidfVectorizer`, then computes cosine similarity against the query vector. Results are re-ranked with `composite_score` to balance semantic relevance with recency and importance.

Filtering happens before vectorization:
1. Filter by `memory_type` (if specified)
2. Filter by tag intersection (if specified)
3. Compute TF-IDF over remaining corpus
4. Sort by `composite_score`, return top-k above `min_score`

---

## Graph memory

`GraphMemory` (in `app/graph_memory.py`) maintains an implicit bipartite graph:

```
memory ──tagged_with──> tag
memory ──links_to──>    entity
```

Edges are derived at query time from `MemoryEntry.tags` and `MemoryEntry.linked_entities` — no separate edge store. `neighbors(entity)` returns all memories touching that tag or entity, plus the union of their other tags/entities as related nodes. This enables lateral context expansion beyond keyword matching.

---

## Token budget

`TokenBudgetManager` (in `app/token_budget.py`) enforces a configurable token ceiling when assembling a context window:

- Token count is estimated as `ceil(word_count × 1.3)` — no tokenizer dependency.
- Memories are packed greedily in descending score order until the budget is exhausted.
- The `GET /memories/context` endpoint exposes this as a one-call context-window builder for agent use.

---

## Garbage collector

`GarbageCollector` (in `app/garbage_collector.py`) runs synchronously on `POST /gc` and applies three passes in order:

1. **Age demotion** — if a memory has been idle longer than its tier's max age, move it one tier down.
2. **Score promotion** — if `composite_score ≥ 0.45`, promote one tier up.
3. **Score archival / deletion**:
   - `score < 0.10` → move to `archived`
   - `score < 0.05` AND already `archived` → delete permanently

GC thresholds live in `app/garbage_collector.py` as module-level constants.

---

## Component map

```
app/
├── main.py              FastAPI routes (HTTP boundary only)
├── memory_manager.py    Orchestrator — the only place all components meet
├── models.py            Pydantic schemas shared across all modules
├── storage.py           Thread-safe in-memory dict store
├── retrieval.py         TF-IDF search + composite_score
├── graph_memory.py      Tag/entity graph traversal
├── token_budget.py      Token estimation + budget allocation
└── garbage_collector.py Tier promotion/demotion/deletion
```

`main.py` holds a single `MemoryManager` instance. Routes parse requests, delegate to `MemoryManager`, and return responses — no business logic in routes.

---

## Data flow: add → search → context

```
POST /memories
  AddMemoryRequest → MemoryManager.add()
    → count tokens (token_budget.py)
    → MemoryStore.add()
    ← MemoryEntry

GET /memories/search?q=...
  → MemoryManager.search()
    → MemoryStore.all()          (snapshot)
    → Retriever.search()         (TF-IDF + composite_score)
    → bump access_count          (MemoryStore.update)
    ← list[MemorySearchResult]

GET /memories/context?q=...&token_budget=4096
  → MemoryManager.get_context()
    → Retriever.search() or score-sort
    → TokenBudgetManager.allocate()
    ← ContextResponse {memories, total_tokens, budget_used}
```

---

## Storage

`MemoryStore` (in `app/storage.py`) is a plain `dict[str, MemoryEntry]` protected by `threading.RLock`. It is intentionally minimal — the design makes swapping in a SQLite or Redis backend a one-file change. See `docs/ROADMAP.md` for the persistence milestone.

---

## Observability layer

Four endpoints expose the internal decision-making of the memory runtime:

### `GET /memory/inspect/{id}`
Returns a `MemoryInspect` with:
- Full `ScoreBreakdown`: `semantic_sim`, `importance`, `recency`, `access_frequency`, `composite`, `age_hours`
- `gc_action` and `gc_reason`: what GC would do to this memory and why
- `predicted_tier`: the tier it would land in after GC

### `GET /memory/gc/preview`
Dry-run of the garbage collector. Returns `GCPreview` with five classified lists (`to_promote`, `to_demote`, `to_archive`, `to_delete`, `to_keep`), each entry containing the score breakdown and the human-readable reason for the decision. Also returns `token_delta` (tokens freed from active tiers) and a `summary` string. **No side effects.**

### `GET /memory/lineage/{id}`
Full audit trail for a memory: every `created`, `accessed`, `promote`, `demote`, `archive`, and `deleted` event with timestamps, tier transitions, and scores. Events are recorded by `MemoryManager` in an in-process `_lifecycle` dict. Lineage persists even after the memory is deleted.

### `GET /memory/stats`
Richer than `GET /stats`: per-tier `TierStats` (count, total tokens, avg score), `gc_pressure` (count of memories that would change tier in the next GC run), and `avg_composite_score` across all tiers.

### Score breakdown formula (reminder)
```
composite = 0.4 × semantic_sim + 0.3 × importance + 0.2 × recency + 0.1 × access_frequency
```
In GC context (no query), `semantic_sim = 0.0` → max reachable score = 0.6.
