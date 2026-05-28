# Architecture

PersistentMemoryforAgents is an OS-inspired memory management layer for long-running AI agents. It organizes agent memory into four tiers modeled after the CPU/OS memory hierarchy, with automatic promotion, demotion, and garbage collection driven by composite importance scores.

---

## Memory tiers

| Tier | OS analogy | Approx. token limit | Max idle age |
|------|-----------|---------------------|--------------|
| `working` | L1 CPU cache | 2,000 | 4 hours |
| `episodic` | L2 CPU cache | 8,000 | 72 hours |
| `semantic` | RAM | 32,000 | 30 days |
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

- Token count uses `tiktoken` (`cl100k_base`) when available, falling back to `ceil(word_count × 1.3)`.
- Memories are packed greedily in descending score order until the budget is exhausted.
- The `GET /memories/context` endpoint exposes this as a one-call context-window builder for agent use.

---

## Garbage collector

`GarbageCollector` (in `app/garbage_collector.py`) runs synchronously on `POST /gc` and on every auto-save when the store exceeds 80 memories. It evaluates each memory in this order:

1. **Age demotion** — if a memory has been idle longer than its tier's max age *and* its composite score is ≤ `DEMOTION_THRESHOLD` (0.25), move it one tier down. Score takes priority: a high-importance memory is never evicted solely because it is old.
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
├── storage.py           SQLite backend (SQLAlchemy) + in-memory backend for tests
├── retrieval.py         TF-IDF search + composite_score
├── graph_memory.py      Tag/entity graph traversal
├── token_budget.py      Token counting (tiktoken) + budget allocation
├── garbage_collector.py Tier promotion/demotion/deletion
└── mcp_server.py        MCP tool server (remember/recall/forget/load_context)

scripts/
├── memory_hook.py       UserPromptSubmit hook — injects relevant memories as context
└── save_hook.py         Stop hook — auto-saves each exchange as an episodic memory
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

`MemoryStore` (in `app/storage.py`) is a factory that returns one of two backends selected by the `PMA_STORAGE` environment variable:

- **`sqlite`** (default) — durable SQLite file at `~/.pma_store.db` via SQLAlchemy. All writes commit immediately; no explicit flush needed.
- **`memory`** — in-process `dict` protected by `threading.RLock`, used by tests and ephemeral dev runs.

## Namespacing

Every `MemoryEntry` carries a `namespace` field (default `"default"`). All read and write operations accept a `namespace` parameter to filter to one scope.

In practice:
- `scripts/save_hook.py` writes episodic memories into the **cwd namespace** (the absolute path of the active project), so exchanges from different projects never mix.
- `scripts/memory_hook.py` queries the **cwd namespace** (project-specific episodic memories) and the **`"default"` namespace** (global working/semantic rules) separately, then merges the results.
- `app/mcp_server.py` resolves its namespace from `PMA_NAMESPACE` env var → `PWD` → `"default"` at startup.

To isolate a project manually, set `PMA_NAMESPACE=/absolute/path/to/project` in the MCP server's env block in `.mcp.json`.

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
