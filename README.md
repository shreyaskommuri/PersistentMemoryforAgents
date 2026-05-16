# PersistentMemoryforAgents

An adaptive memory runtime for long-running AI agents. Organizes agent knowledge into four tiers — working, episodic, semantic, and archived — with automatic promotion, demotion, TF-IDF retrieval, and semantic garbage collection.

Runs fully locally. No cloud APIs required.

---

## Features

| | |
|---|---|
| **Four-tier memory hierarchy** | Working → Episodic → Semantic → Archived, modeled after OS memory management |
| **Composite scoring** | Blends semantic similarity, importance, recency decay, and access frequency |
| **Token-aware context assembly** | Fills a configurable token budget greedily by score — one API call gives an agent its full context window |
| **Graph memory** | Tag- and entity-linked graph for lateral context expansion beyond keyword search |
| **Semantic garbage collector** | Promotes hot memories, demotes stale ones, archives low-scoring entries |
| **Explainable GC** | Preview what the garbage collector would do and why, with per-memory score breakdowns |
| **Memory lineage** | Full audit trail of tier promotions, demotions, and access events per memory |
| **REST API** | FastAPI with auto-generated OpenAPI docs at `/docs` |
| **Local-first** | In-memory storage, no external services, no API keys |

---

## Quick start

```bash
git clone https://github.com/shreyaskommuri/PersistentMemoryforAgents
cd PersistentMemoryforAgents
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/memories` | Add a new memory |
| `GET` | `/memories` | List all memories (optional `?memory_type=` filter) |
| `GET` | `/memories/search` | TF-IDF semantic search with scoring |
| `GET` | `/memories/context` | Token-budgeted context window for agent injection |
| `GET` | `/memories/{id}` | Fetch a memory by ID (increments access count) |
| `DELETE` | `/memories/{id}` | Delete a memory |
| `GET` | `/memories/{id}/linked` | Graph-linked memories (shared tags/entities) |
| `GET` | `/graph/{entity}` | Traverse graph from a tag or entity name |
| `POST` | `/gc` | Run the garbage collector |
| `GET` | `/stats` | Total count, by-tier breakdown, token usage |
| `GET` | `/health` | Health check |
| **Observability** | | |
| `GET` | `/memory/stats` | Detailed per-tier stats + GC pressure indicator |
| `GET` | `/memory/inspect/{id}` | Score breakdown + GC prediction for one memory |
| `GET` | `/memory/gc/preview` | Dry-run GC — see all decisions without applying them |
| `GET` | `/memory/lineage/{id}` | Full event history: creates, accesses, promotions, demotions |

### Add a memory

```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The transformer architecture uses self-attention.",
    "importance": 0.9,
    "tags": ["ml", "architecture"],
    "linked_entities": ["transformer", "attention"]
  }'
```

### Search

```bash
curl "http://localhost:8000/memories/search?q=attention+mechanism&limit=5"
```

### Get a token-budgeted context window

```bash
curl "http://localhost:8000/memories/context?q=transformers&token_budget=2048"
```

---

## Memory model

```json
{
  "id": "uuid",
  "content": "string",
  "memory_type": "working | episodic | semantic | archived",
  "importance": 0.0–1.0,
  "tags": ["string"],
  "linked_entities": ["string"],
  "token_count": 12,
  "access_count": 3,
  "created_at": "2024-01-01T00:00:00Z",
  "accessed_at": "2024-01-01T01:00:00Z",
  "metadata": {}
}
```

---

## Scoring formula

```
score = 0.4 × semantic_similarity   ← TF-IDF cosine sim vs. query
      + 0.3 × importance             ← user-supplied weight
      + 0.2 × recency_score          ← exp(-0.1 × age_hours)
      + 0.1 × access_frequency       ← log-normalized access count
```

This score drives both retrieval ranking and garbage-collector tier decisions.

---

## Memory tiers

| Tier | Token limit | Max idle age | Analogy |
|------|------------|--------------|---------|
| `working` | ~2,000 | 1 hour | L1 CPU cache |
| `episodic` | ~8,000 | 24 hours | L2 CPU cache |
| `semantic` | ~32,000 | 7 days | RAM |
| `archived` | Unlimited | Indefinite | Disk |

The garbage collector runs on `POST /gc` and migrates memories between tiers automatically.

---

## Observability demo

```bash
# Add a high-value and a low-value memory
curl -s -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Attention is all you need — the transformer paper.", "importance": 0.95, "tags": ["ml"], "linked_entities": ["transformer", "attention"]}'

curl -s -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Reminder to buy groceries.", "importance": 0.05}'

# See what GC would do to every memory, and why — without changing anything
curl -s http://localhost:8000/memory/gc/preview | python3 -m json.tool

# Inspect a specific memory's score breakdown and GC prediction
curl -s http://localhost:8000/memory/inspect/<id> | python3 -m json.tool

# See the full lifecycle of a memory (creates, accesses, promotions)
curl -s http://localhost:8000/memory/lineage/<id> | python3 -m json.tool

# Per-tier stats + GC pressure indicator
curl -s http://localhost:8000/memory/stats | python3 -m json.tool
```

---

## Running tests

```bash
pytest tests/ -v
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full component breakdown, data flow diagrams, and scoring details.

---

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md). Next milestone: SQLite persistence (v0.2).

---

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) — REST framework
- [Pydantic v2](https://docs.pydantic.dev/) — data validation and serialization
- [scikit-learn](https://scikit-learn.org/) — TF-IDF vectorization
- [NumPy](https://numpy.org/) — vector math
- [pytest](https://pytest.org/) + [httpx](https://www.python-httpx.org/) — testing

---

## License

MIT
