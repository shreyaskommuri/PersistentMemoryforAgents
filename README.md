# PersistentMemoryforAgents

A self-hosted memory server for AI agents. Stores facts, decisions, and context across sessions in a four-tier hierarchy — working, episodic, semantic, archived — with TF-IDF retrieval, composite scoring, and automatic garbage collection.

Works standalone via REST or as an [MCP server](#mcp--claude-code) wired directly into Claude Code.

---

## How it works

Every memory has a score computed from four factors:

```
score = 0.4 × semantic_similarity   (TF-IDF cosine vs. query)
      + 0.3 × importance             (user-supplied, 0–1)
      + 0.2 × recency                (exp decay over age in hours)
      + 0.1 × access_frequency       (log-normalized hit count)
```

This score drives both retrieval ranking and the garbage collector's tier decisions. High-scoring memories get promoted toward `working`; low-scoring ones demote toward `archived` and eventually get deleted.

---

## Quick start

```bash
git clone https://github.com/shreyaskommuri/PersistentMemoryforAgents
cd PersistentMemoryforAgents
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the interactive API.

---

## MCP + Claude Code

The MCP server lets Claude Code call `remember`, `recall`, `load_context`, `forget`, and `seed_project` natively during conversations. Memories persist to `~/.pma_store.db` across sessions.

**Add to `.claude/settings.json`:**

```json
{
  "mcpServers": {
    "persistent-memory": {
      "command": "python3",
      "args": ["/absolute/path/to/PersistentMemoryforAgents/app/mcp_server.py"],
      "env": {
        "PMA_NAMESPACE": "my-project"
      }
    }
  }
}
```

Set `PMA_NAMESPACE` per project so different workspaces don't share memories.

**Available tools:**

| Tool | What it does |
|------|-------------|
| `load_context` | Returns a token-budgeted context window of the most relevant memories. Call at session start. |
| `remember` | Saves a memory with importance, tags, linked entities, and memory type. |
| `recall` | TF-IDF search over stored memories. Returns scored results. |
| `forget` | Deletes a memory by ID prefix. |
| `seed_project` | Seeds memories from project docs (CLAUDE.md, README.md, ARCHITECTURE.md, ROADMAP.md). |
| `memory_stats` | Shows tier counts and token usage for the current namespace. |

---

## Memory tiers

| Tier | Analogy | Max idle age |
|------|---------|-------------|
| `working` | L1 cache | 1 hour |
| `episodic` | L2 cache | 24 hours |
| `semantic` | RAM | 7 days |
| `archived` | Disk | Indefinite |

The garbage collector (`POST /gc`) promotes hot memories up and demotes stale ones down. Use `GET /memory/gc/preview` to see what it would do before running it.

---

## API reference

**Memories**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/memories` | Add a memory. `?namespace=` scopes it to a project. |
| `GET` | `/memories` | List all memories. `?namespace=` filters by project. |
| `GET` | `/memories/search` | TF-IDF search. `?q=`, `?namespace=`, `?limit=`, `?memory_type=` |
| `GET` | `/memories/context` | Token-budgeted context window for agent injection. `?q=`, `?token_budget=` |
| `GET` | `/memories/export` | Export all memories as a JSON snapshot. `?namespace=` to export one project. |
| `POST` | `/memories/import` | Import a JSON snapshot. `?skip_existing=true`, `?namespace=` to override. |
| `GET` | `/memories/{id}` | Fetch one memory (increments access count). |
| `DELETE` | `/memories/{id}` | Delete a memory. |
| `GET` | `/memories/{id}/linked` | Graph-linked memories (shared tags or entities). |

**Graph**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/graph/{entity}` | Traverse the entity graph from a tag or entity name. |

**Garbage collection**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/gc` | Run the garbage collector — promotes, demotes, archives, deletes. |
| `GET` | `/memory/gc/preview` | Dry-run: see every GC decision and reason without applying it. |

**Observability**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stats` | Total count, by-tier breakdown, token usage. |
| `GET` | `/memory/stats` | Detailed per-tier stats + GC pressure indicator. |
| `GET` | `/memory/inspect/{id}` | Score breakdown and GC prediction for one memory. |
| `GET` | `/memory/lineage/{id}` | Full event history: creates, accesses, promotions, demotions. |

---

## Usage examples

**Add a memory**
```bash
curl -X POST "http://localhost:8000/memories?namespace=myproject" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Use async/await for all database calls — sync calls block the event loop.",
    "importance": 0.9,
    "tags": ["python", "async"],
    "linked_entities": ["database", "event-loop"]
  }'
```

**Search**
```bash
curl "http://localhost:8000/memories/search?q=database+async&namespace=myproject&limit=5"
```

**Get a context window for agent injection**
```bash
curl "http://localhost:8000/memories/context?q=database+performance&token_budget=2048&namespace=myproject"
```

**Export a namespace snapshot**
```bash
curl "http://localhost:8000/memories/export?namespace=myproject" > backup.json
```

**Restore from snapshot**
```bash
curl -X POST "http://localhost:8000/memories/import?namespace=myproject" \
  -H "Content-Type: application/json" \
  -d @backup.json
```

**Preview GC decisions before running**
```bash
curl http://localhost:8000/memory/gc/preview | python3 -m json.tool
```

---

## Memory schema

```json
{
  "id": "3f2a1b4c-...",
  "content": "string",
  "memory_type": "working | episodic | semantic | archived",
  "importance": 0.0,
  "tags": ["string"],
  "linked_entities": ["string"],
  "namespace": "default",
  "token_count": 12,
  "access_count": 3,
  "created_at": "2024-01-01T00:00:00Z",
  "accessed_at": "2024-01-01T01:00:00Z",
  "metadata": {}
}
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PMA_STORAGE` | `sqlite` | Backend: `sqlite` for durable storage, `memory` for in-process only (tests) |
| `PMA_DB_PATH` | `~/.pma_store.db` | SQLite database file path |
| `PMA_NAMESPACE` | `default` | Namespace for MCP server — set per project in `.claude/settings.json` |

---

## Running tests

```bash
pytest tests/ -v
```

Tests use `PMA_STORAGE=memory` automatically (set in `tests/conftest.py`) so they never touch the real database.

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the component map and data flow.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md). Currently at v0.2 (SQLite persistence, export/import). Next: v0.3 dense embeddings with `sentence-transformers`.

---

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) + [Pydantic v2](https://docs.pydantic.dev/)
- [SQLAlchemy](https://www.sqlalchemy.org/) — SQLite backend
- [scikit-learn](https://scikit-learn.org/) — TF-IDF vectorization
- [MCP](https://modelcontextprotocol.io/) — Claude Code integration
- [pytest](https://pytest.org/) + [httpx](https://www.python-httpx.org/)

---

## License

MIT
