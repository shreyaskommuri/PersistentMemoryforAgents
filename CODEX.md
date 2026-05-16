# CODEX.md — Coding agent contribution guide

This document orients automated coding agents (GitHub Copilot, Claude, Cursor, etc.) contributing to PersistentMemoryforAgents.

## Project goals

Build a lightweight, local-first memory layer that any AI agent can use to persist, retrieve, and manage memories across long-running sessions — without cloud APIs or proprietary dependencies.

## Architecture rules

| Rule | Reason |
|------|--------|
| One module, one responsibility | Keeps diffs small and reviewable |
| No cross-module side effects | `storage.py` does not know about `retrieval.py` |
| Pydantic for all data boundaries | Validate at the edge, not scattered across callsites |
| Thread-safe storage | `MemoryStore` uses `threading.RLock` — do not bypass it |
| No global mutable state outside `MemoryManager` | `main.py` holds exactly one `MemoryManager` instance |

## Module responsibilities

| Module | Owns | Does not own |
|--------|------|--------------|
| `models.py` | Pydantic schemas | Business logic |
| `storage.py` | CRUD on the in-memory dict | Scoring, retrieval |
| `retrieval.py` | TF-IDF search + composite scoring | Storage mutations |
| `token_budget.py` | Token counting + budget allocation | Retrieval, ranking |
| `graph_memory.py` | Tag/entity graph traversal | Memory mutations |
| `garbage_collector.py` | Tier demotion, archival, deletion | Query-time retrieval |
| `memory_manager.py` | Orchestrates all components | Component internals |
| `main.py` | HTTP routing and request parsing | Business logic |

## Testing expectations

- Every new endpoint → at least one happy-path test and one error/404 test.
- Every scoring change → a test asserting rank order (higher importance = higher rank for equal queries).
- Every GC rule change → a test with a manufactured scenario that exercises the specific threshold.
- Run `pytest tests/ -v` before committing. All tests must pass.

## Style guidelines

- Max line length: 100 characters.
- Type hints on all public functions and method signatures.
- No comments explaining *what* the code does — only *why* when non-obvious (hidden invariant, workaround, subtle constraint).
- No docstrings on trivial getters and setters.
- Import order: stdlib → third-party → local, each group separated by a blank line.
- Prefer `datetime.now(timezone.utc)` over deprecated `datetime.utcnow()`.

## Safe refactor rules

1. Do not rename public `MemoryEntry` fields without a migration plan — clients depend on the field names.
2. Do not change scoring weights in `composite_score` without updating `docs/ARCHITECTURE.md` and adding a rank-order test.
3. Do not change GC thresholds (`PROMOTION_THRESHOLD`, etc.) without updating `docs/ARCHITECTURE.md`.
4. Do not add required fields to `AddMemoryRequest` without providing a default value.
5. Do not change `MemoryType` enum values without updating existing stored data or providing a migration.

## Roadmap priorities

The current focus is **v0.2 — Persistence**. When choosing between two valid approaches, prefer the one that makes swapping in a SQLite backend easiest. Storage logic is intentionally isolated in `storage.py` for this reason. See `docs/ROADMAP.md` for the full plan.
