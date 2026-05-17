import pytest
from fastapi.testclient import TestClient

from app.main import app, manager, _STORE_PATH

client = TestClient(app)

_REAL_STORE: dict = {}


@pytest.fixture(autouse=True)
def clear_store():
    # Snapshot and restore the real store so tests don't clobber ~/.pma_store.json
    import json
    try:
        _REAL_STORE.update(json.loads(_STORE_PATH.read_text()))
    except Exception:
        pass

    manager._store.clear()
    yield

    manager._store.clear()
    # Restore the store file to its pre-test state
    if _REAL_STORE:
        _STORE_PATH.write_text(json.dumps(_REAL_STORE, indent=2))
        _REAL_STORE.clear()
    else:
        try:
            _STORE_PATH.unlink()
        except FileNotFoundError:
            pass


# ── Health / stats ─────────────────────────────────────────────────────────


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stats_empty():
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert "by_type" in data


def test_stats_after_add():
    client.post("/memories", json={"content": "hello"})
    r = client.get("/stats")
    assert r.json()["total"] == 1


# ── Add / get / delete ─────────────────────────────────────────────────────


def test_add_memory_defaults():
    r = client.post("/memories", json={"content": "The sky is blue."})
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "The sky is blue."
    assert data["memory_type"] == "episodic"
    assert data["importance"] == 0.5
    assert data["token_count"] > 0


def test_add_memory_custom_fields():
    r = client.post(
        "/memories",
        json={
            "content": "Paris is the capital of France.",
            "memory_type": "semantic",
            "importance": 0.9,
            "tags": ["geography", "europe"],
            "linked_entities": ["Paris", "France"],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["memory_type"] == "semantic"
    assert data["importance"] == 0.9
    assert "geography" in data["tags"]
    assert "France" in data["linked_entities"]


def test_get_memory_increments_access_count():
    mid = client.post("/memories", json={"content": "Access me."}).json()["id"]
    initial = client.get(f"/memories/{mid}").json()["access_count"]
    client.get(f"/memories/{mid}")
    updated = client.get(f"/memories/{mid}").json()["access_count"]
    assert updated > initial


def test_get_memory_not_found():
    r = client.get("/memories/does-not-exist")
    assert r.status_code == 404


def test_delete_memory():
    mid = client.post("/memories", json={"content": "Delete me."}).json()["id"]
    assert client.delete(f"/memories/{mid}").status_code == 204
    assert client.get(f"/memories/{mid}").status_code == 404


def test_delete_memory_not_found():
    assert client.delete("/memories/does-not-exist").status_code == 404


def test_list_memories():
    client.post("/memories", json={"content": "A"})
    client.post("/memories", json={"content": "B"})
    r = client.get("/memories")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_memories_filter_by_type():
    client.post("/memories", json={"content": "Working", "memory_type": "working"})
    client.post("/memories", json={"content": "Episodic", "memory_type": "episodic"})
    r = client.get("/memories?memory_type=working")
    assert r.status_code == 200
    assert all(m["memory_type"] == "working" for m in r.json())


# ── Search ─────────────────────────────────────────────────────────────────


def test_search_returns_results():
    client.post("/memories", json={"content": "Python is a programming language."})
    client.post("/memories", json={"content": "FastAPI is a web framework for Python."})
    client.post("/memories", json={"content": "The Eiffel Tower is in Paris."})

    r = client.get("/memories/search?q=python+programming")
    assert r.status_code == 200
    results = r.json()
    assert len(results) > 0
    top_contents = [res["memory"]["content"] for res in results[:2]]
    assert any("Python" in c or "FastAPI" in c for c in top_contents)


def test_search_tag_filter():
    client.post("/memories", json={"content": "API endpoint", "tags": ["api"]})
    client.post("/memories", json={"content": "Database table", "tags": ["db"]})

    r = client.get("/memories/search?q=endpoint&tags=api")
    assert r.status_code == 200
    for res in r.json():
        assert "api" in [t.lower() for t in res["memory"]["tags"]]


def test_search_empty_corpus():
    r = client.get("/memories/search?q=anything")
    assert r.status_code == 200
    assert r.json() == []


def test_search_importance_ranking():
    client.post("/memories", json={"content": "machine learning", "importance": 0.9})
    client.post("/memories", json={"content": "machine learning", "importance": 0.1})

    results = client.get("/memories/search?q=machine+learning").json()
    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]


# ── Context window ─────────────────────────────────────────────────────────


def test_context_respects_token_budget():
    for i in range(10):
        client.post("/memories", json={"content": f"Memory number {i} with some content here."})

    r = client.get("/memories/context?token_budget=50")
    assert r.status_code == 200
    data = r.json()
    assert data["total_tokens"] <= 60  # small overshoot tolerance from estimation
    assert 0.0 <= data["budget_used"] <= 1.0


def test_context_with_query():
    client.post("/memories", json={"content": "Python is great for data science."})
    client.post("/memories", json={"content": "I had eggs for breakfast."})

    r = client.get("/memories/context?q=python+data")
    assert r.status_code == 200
    memories = r.json()["memories"]
    contents = [m["content"] for m in memories]
    assert any("Python" in c for c in contents)


def test_context_empty_store():
    r = client.get("/memories/context")
    assert r.status_code == 200
    assert r.json()["memories"] == []
    assert r.json()["total_tokens"] == 0


# ── Graph memory ───────────────────────────────────────────────────────────


def test_graph_neighbors_by_entity():
    client.post(
        "/memories",
        json={"content": "Plants photosynthesize.", "linked_entities": ["plant", "photosynthesis"]},
    )
    client.post(
        "/memories",
        json={"content": "Plants produce oxygen.", "linked_entities": ["plant", "oxygen"]},
    )

    r = client.get("/graph/plant")
    assert r.status_code == 200
    data = r.json()
    assert data["entity"] == "plant"
    assert len(data["memories"]) == 2
    assert "oxygen" in data["related_entities"] or "photosynthesis" in data["related_entities"]


def test_graph_neighbors_by_tag():
    client.post("/memories", json={"content": "FastAPI tutorial.", "tags": ["python", "web"]})
    client.post("/memories", json={"content": "Django tutorial.", "tags": ["python", "web"]})

    r = client.get("/graph/python")
    assert r.status_code == 200
    assert len(r.json()["memories"]) == 2


def test_graph_empty_entity():
    r = client.get("/graph/nonexistent-entity")
    assert r.status_code == 200
    assert r.json()["memories"] == []


def test_linked_memories():
    id1 = client.post(
        "/memories",
        json={"content": "Alpha memory.", "tags": ["shared"]},
    ).json()["id"]
    client.post("/memories", json={"content": "Beta memory.", "tags": ["shared"]})

    r = client.get(f"/memories/{id1}/linked")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_linked_memories_not_found():
    r = client.get("/memories/does-not-exist/linked")
    assert r.status_code == 404


# ── Garbage collector ──────────────────────────────────────────────────────


def test_gc_runs_and_returns_stats():
    client.post("/memories", json={"content": "Some memory.", "importance": 0.5})
    r = client.post("/gc")
    assert r.status_code == 200
    data = r.json()
    assert all(k in data for k in ("promoted", "demoted", "archived", "deleted"))


def test_gc_promotes_high_importance():
    # High importance + recently accessed → should promote from episodic toward working.
    client.post(
        "/memories",
        json={"content": "Critical fact.", "importance": 1.0, "memory_type": "episodic"},
    )
    client.post("/gc")
    r = client.get("/memories")
    promoted = [m for m in r.json() if m["memory_type"] == "working"]
    assert len(promoted) >= 1


# ── Observability: /memory/stats ───────────────────────────────────────────


def test_detailed_stats_structure():
    client.post("/memories", json={"content": "A memory.", "importance": 0.8})
    r = client.get("/memory/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data and data["total"] >= 1
    assert "total_tokens" in data
    assert "by_tier" in data
    assert "gc_pressure" in data
    assert "avg_composite_score" in data
    for tier in ("working", "episodic", "semantic", "archived"):
        assert tier in data["by_tier"]


def test_detailed_stats_empty_store():
    r = client.get("/memory/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["gc_pressure"] == 0
    assert data["avg_composite_score"] == 0.0


def test_detailed_stats_token_count():
    client.post("/memories", json={"content": "Token counting memory.", "importance": 0.5})
    r = client.get("/memory/stats")
    assert r.json()["total_tokens"] > 0


# ── Observability: /memory/inspect/{id} ────────────────────────────────────


def test_inspect_memory_score_breakdown():
    mid = client.post(
        "/memories",
        json={"content": "Important insight.", "importance": 0.9},
    ).json()["id"]

    r = client.get(f"/memory/inspect/{mid}")
    assert r.status_code == 200
    data = r.json()

    # Score breakdown fields
    breakdown = data["score_breakdown"]
    assert "composite" in breakdown
    assert "importance" in breakdown
    assert "recency" in breakdown
    assert "access_frequency" in breakdown
    assert "age_hours" in breakdown
    assert breakdown["importance"] == pytest.approx(0.9, abs=0.01)
    assert 0.0 <= breakdown["composite"] <= 1.0

    # GC decision fields
    assert "gc_action" in data
    assert "gc_reason" in data
    assert len(data["gc_reason"]) > 0


def test_inspect_memory_not_found():
    r = client.get("/memory/inspect/does-not-exist")
    assert r.status_code == 404


def test_inspect_memory_high_importance_predicts_promotion():
    mid = client.post(
        "/memories",
        json={"content": "Critical data.", "importance": 1.0, "memory_type": "episodic"},
    ).json()["id"]
    r = client.get(f"/memory/inspect/{mid}")
    data = r.json()
    assert data["gc_action"] == "promote"
    assert data["predicted_tier"] == "working"


def test_inspect_memory_low_importance_predicts_archive():
    mid = client.post(
        "/memories",
        json={"content": "Trivial note.", "importance": 0.0},
    ).json()["id"]
    r = client.get(f"/memory/inspect/{mid}")
    data = r.json()
    assert data["gc_action"] in ("archive", "demote", "keep")


# ── Observability: /memory/gc/preview ─────────────────────────────────────


def test_gc_preview_structure():
    client.post("/memories", json={"content": "A memory.", "importance": 0.5})
    r = client.get("/memory/gc/preview")
    assert r.status_code == 200
    data = r.json()
    for key in ("to_promote", "to_demote", "to_archive", "to_delete", "to_keep"):
        assert key in data
    assert "total_affected" in data
    assert "token_delta" in data
    assert "summary" in data
    assert len(data["summary"]) > 0


def test_gc_preview_is_dry_run():
    client.post("/memories", json={"content": "High value.", "importance": 1.0, "memory_type": "episodic"})
    preview = client.get("/memory/gc/preview").json()
    assert len(preview["to_promote"]) >= 1

    # Memories should NOT have changed after the preview
    memories_after = client.get("/memories").json()
    assert all(m["memory_type"] == "episodic" for m in memories_after)


def test_gc_preview_shows_score_breakdowns():
    client.post("/memories", json={"content": "Test memory."})
    data = client.get("/memory/gc/preview").json()
    all_entries = data["to_promote"] + data["to_demote"] + data["to_archive"] + data["to_keep"]
    for entry in all_entries:
        assert "score_breakdown" in entry
        assert "reason" in entry
        assert len(entry["reason"]) > 0


def test_gc_preview_token_delta_nonnegative():
    client.post("/memories", json={"content": "Low value memory.", "importance": 0.0})
    data = client.get("/memory/gc/preview").json()
    assert data["token_delta"] >= 0


def test_gc_preview_empty_store():
    r = client.get("/memory/gc/preview")
    assert r.status_code == 200
    data = r.json()
    assert data["total_affected"] == 0
    assert data["token_delta"] == 0


# ── Observability: /memory/lineage/{id} ────────────────────────────────────


def test_lineage_records_created_event():
    mid = client.post("/memories", json={"content": "Tracked memory."}).json()["id"]
    r = client.get(f"/memory/lineage/{mid}")
    assert r.status_code == 200
    data = r.json()
    event_types = [e["event_type"] for e in data["events"]]
    assert "created" in event_types


def test_lineage_records_accessed_event():
    mid = client.post("/memories", json={"content": "Accessed memory."}).json()["id"]
    client.get(f"/memories/{mid}")  # triggers access
    r = client.get(f"/memory/lineage/{mid}")
    data = r.json()
    event_types = [e["event_type"] for e in data["events"]]
    assert "accessed" in event_types
    assert data["total_accesses"] >= 1


def test_lineage_records_gc_event():
    mid = client.post(
        "/memories",
        json={"content": "GC target.", "importance": 1.0, "memory_type": "episodic"},
    ).json()["id"]
    client.post("/gc")
    r = client.get(f"/memory/lineage/{mid}")
    data = r.json()
    event_types = [e["event_type"] for e in data["events"]]
    assert "promote" in event_types
    assert data["total_promotions"] >= 1


def test_lineage_includes_tier_transitions():
    mid = client.post(
        "/memories",
        json={"content": "Promoted memory.", "importance": 1.0, "memory_type": "semantic"},
    ).json()["id"]
    client.post("/gc")
    r = client.get(f"/memory/lineage/{mid}")
    data = r.json()
    promote_events = [e for e in data["events"] if e["event_type"] == "promote"]
    if promote_events:
        ev = promote_events[0]
        assert ev["from_tier"] is not None
        assert ev["to_tier"] is not None
        assert ev["score"] is not None


def test_lineage_not_found():
    r = client.get("/memory/lineage/does-not-exist")
    assert r.status_code == 404


def test_lineage_age_hours_nonnegative():
    mid = client.post("/memories", json={"content": "Age test."}).json()["id"]
    data = client.get(f"/memory/lineage/{mid}").json()
    assert data["age_hours"] >= 0.0


# ── Namespacing ────────────────────────────────────────────────────────────


def test_namespace_isolates_list():
    client.post("/memories?namespace=proj_a", json={"content": "Project A memory."})
    client.post("/memories?namespace=proj_b", json={"content": "Project B memory."})

    a_mems = client.get("/memories?namespace=proj_a").json()
    b_mems = client.get("/memories?namespace=proj_b").json()

    assert all(m["namespace"] == "proj_a" for m in a_mems)
    assert all(m["namespace"] == "proj_b" for m in b_mems)
    assert len(a_mems) == 1
    assert len(b_mems) == 1


def test_namespace_isolates_search():
    client.post("/memories?namespace=proj_a", json={"content": "Retrieval test alpha."})
    client.post("/memories?namespace=proj_b", json={"content": "Retrieval test beta."})

    results = client.get("/memories/search?q=retrieval+test&namespace=proj_a").json()
    assert all(r["memory"]["namespace"] == "proj_a" for r in results)


def test_namespace_isolates_context():
    client.post("/memories?namespace=proj_a", json={"content": "Context alpha.", "importance": 0.9})
    client.post("/memories?namespace=proj_b", json={"content": "Context beta.", "importance": 0.9})

    resp = client.get("/memories/context?namespace=proj_a").json()
    assert all(m["namespace"] == "proj_a" for m in resp["memories"])


def test_list_all_namespaces_when_omitted():
    client.post("/memories?namespace=proj_a", json={"content": "Alpha."})
    client.post("/memories?namespace=proj_b", json={"content": "Beta."})

    all_mems = client.get("/memories").json()
    namespaces = {m["namespace"] for m in all_mems}
    assert "proj_a" in namespaces
    assert "proj_b" in namespaces


def test_default_namespace_is_default():
    mid = client.post("/memories", json={"content": "Default NS memory."}).json()["id"]
    mem = client.get(f"/memories/{mid}").json()
    assert mem["namespace"] == "default"
