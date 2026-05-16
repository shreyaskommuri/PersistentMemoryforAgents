#!/usr/bin/env python3
"""
MCP server for PersistentMemoryforAgents.

Exposes memory tools Claude Code (and any MCP-compatible agent) can call
natively during conversations. Memories persist to ~/.pma_store.json across
sessions.

Usage (Claude Code wires this up automatically via .claude/settings.json):
  python3 app/mcp_server.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running directly from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

from app.memory_manager import MemoryManager
from app.models import AddMemoryRequest, ContextRequest, MemoryType, SearchQuery

STORE_PATH = os.path.expanduser("~/.pma_store.json")
PROJECT_ROOT = str(Path(__file__).parent.parent)

mcp = FastMCP(
    "PersistentMemory",
    instructions=(
        "You have access to a persistent memory store. "
        "Call load_context at the start of a session to recall relevant prior knowledge. "
        "Call remember to save important facts, decisions, or conclusions. "
        "Call recall to search for specific information. "
        "Call forget to remove outdated or incorrect memories."
    ),
)

_manager = MemoryManager()
_manager._store.load_from_file(STORE_PATH)

# Auto-seed from project docs on first run (empty store).
if _manager._store.count() == 0:
    _seeded = _manager.seed_from_project(PROJECT_ROOT)
    if _seeded > 0:
        _manager._store.save_to_file(STORE_PATH)


def _save() -> None:
    _manager._store.save_to_file(STORE_PATH)


# ── Tools ──────────────────────────────────────────────────────────────────


@mcp.tool()
def remember(
    content: str,
    importance: float = 0.5,
    memory_type: str = "episodic",
    tags: list[str] = [],
    linked_entities: list[str] = [],
) -> str:
    """
    Save a memory for future retrieval.

    Args:
        content: The text to remember.
        importance: How important this is, 0.0–1.0. Higher = less likely to be GC'd.
        memory_type: working | episodic | semantic | archived. Default episodic.
        tags: Optional category labels (e.g. ["python", "bug"]).
        linked_entities: Names of people, projects, or concepts this is about.
    """
    try:
        tier = MemoryType(memory_type)
    except ValueError:
        tier = MemoryType.episodic

    _manager._store.load_from_file(STORE_PATH)  # pick up any changes since startup
    req = AddMemoryRequest(
        content=content,
        importance=importance,
        memory_type=tier,
        tags=tags,
        linked_entities=linked_entities,
    )
    entry = _manager.add(req)
    _save()
    return f"Saved [{entry.id[:8]}] ({entry.memory_type}, importance={entry.importance})"


@mcp.tool()
def recall(query: str, limit: int = 5, memory_type: str = "") -> str:
    """
    Search memories by semantic similarity to the query.

    Args:
        query: What to search for.
        limit: Max results to return (default 5).
        memory_type: Optional filter: working | episodic | semantic | archived.
    """
    types = None
    if memory_type:
        try:
            types = [MemoryType(memory_type)]
        except ValueError:
            pass

    results = _manager.search(SearchQuery(query=query, limit=limit, memory_types=types))
    if not results:
        return "No memories found."

    lines = [
        f"[{r.memory.memory_type} | score={r.score:.2f} | imp={r.memory.importance:.1f}] {r.memory.content}"
        for r in results
    ]
    return "\n".join(lines)


@mcp.tool()
def load_context(query: str = "", token_budget: int = 2048) -> str:
    """
    Retrieve a token-budgeted context window of the most relevant memories.
    Call this at the start of a session or task to load relevant prior knowledge.

    Args:
        query: Optional query to rank memories by relevance to current task.
        token_budget: Max tokens to return (default 2048).
    """
    req = ContextRequest(query=query or None, token_budget=token_budget)
    resp = _manager.get_context(req)

    if not resp.memories:
        return "Memory store is empty."

    lines = [
        f"[{m.memory_type} | imp={m.importance:.1f}] {m.content}"
        for m in resp.memories
    ]
    header = (
        f"Loaded {len(resp.memories)} memories "
        f"({resp.total_tokens} tokens, {resp.budget_used:.0%} of budget used):"
    )
    return header + "\n" + "\n".join(lines)


@mcp.tool()
def forget(memory_id_prefix: str) -> str:
    """
    Delete a memory by its ID (or the first few characters of it).

    Args:
        memory_id_prefix: Full ID or unique prefix (e.g. "a3f1b2c4").
    """
    _manager._store.load_from_file(STORE_PATH)  # pick up any changes since startup
    matches = [e for e in _manager.list_all() if e.id.startswith(memory_id_prefix)]
    if not matches:
        return f"No memory found with ID prefix '{memory_id_prefix}'."
    if len(matches) > 1:
        return f"Ambiguous: {len(matches)} memories share that prefix. Use more characters."

    _manager.delete(matches[0].id)
    _save()
    return f"Deleted [{matches[0].id[:8]}]: {matches[0].content[:60]}"


@mcp.tool()
def seed_project(project_path: str = "") -> str:
    """
    Seed the memory store from a project's documentation files.
    Reads CLAUDE.md, CODEX.md, docs/ARCHITECTURE.md, docs/ROADMAP.md, README.md
    and saves key sections as semantic memories. Safe to re-run — skips duplicates.

    Args:
        project_path: Absolute path to the project root. Defaults to this project.
    """
    root = project_path or PROJECT_ROOT
    count = _manager.seed_from_project(root)
    _save()
    if count == 0:
        return "No new memories added (already seeded or no docs found)."
    return f"Seeded {count} memories from {root}"


@mcp.tool()
def memory_stats() -> str:
    """Show memory system stats: tier counts, token usage, and GC pressure."""
    stats = _manager.detailed_stats()
    lines = [
        f"Total: {stats.total} memories | {stats.total_tokens} tokens | avg score {stats.avg_composite_score:.3f}",
        f"GC pressure: {stats.gc_pressure} memories would change tier on next run",
        "",
        "Tier breakdown:",
    ]
    for tier, ts in stats.by_tier.items():
        if ts.count > 0:
            lines.append(
                f"  {tier:10s} {ts.count:3d} memories  {ts.total_tokens:5d} tokens  avg_score={ts.avg_score:.3f}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
