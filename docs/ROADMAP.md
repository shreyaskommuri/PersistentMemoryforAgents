# Roadmap

## v0.1 — Foundation (current)
- [x] Four-tier memory system: working / episodic / semantic / archived
- [x] TF-IDF retrieval with composite scoring (importance + recency + frequency + semantic)
- [x] Token-budget context assembly
- [x] Tag + entity graph memory with lateral traversal
- [x] Score- and age-based garbage collection with tier migration
- [x] FastAPI REST interface with OpenAPI docs
- [x] Thread-safe in-memory storage
- [x] Unit tests with FastAPI TestClient

## v0.2 — Persistence
- [ ] SQLite backend via SQLAlchemy (one-file swap for `storage.py`)
- [ ] Memory snapshots: export/import to JSON
- [ ] Configurable storage backend via environment variable

## v0.3 — Smarter retrieval
- [ ] Local dense embeddings with `sentence-transformers`
- [ ] Hybrid BM25 + dense re-rank
- [ ] Approximate nearest-neighbor index (FAISS or `usearch`)
- [ ] Cross-session memory deduplication

## v0.4 — Agent integration
- [x] MCP server endpoint for direct Claude Code / Claude Desktop integration
- [ ] OpenAI-compatible function-call interface (`remember`, `recall`, `forget`)
- [x] Agent session namespacing (multi-tenant memory) — `namespace` field on all memories; `PMA_NAMESPACE` env var scopes MCP server per-project
- [ ] Streaming context assembly for large budgets

## v0.5 — Observability
- [ ] Prometheus `/metrics` endpoint
- [ ] Per-memory audit log (access history)
- [ ] GC run history and tier-migration event stream
- [ ] Dashboard (simple HTML/JS served by FastAPI)

## v1.0 — Production
- [ ] Redis-backed store for horizontal scaling
- [ ] Multi-agent shared memory with conflict resolution
- [ ] Access control and scoped memory per agent ID
- [ ] Docker image + `docker-compose.yml`
- [ ] Full async FastAPI with async storage backend
