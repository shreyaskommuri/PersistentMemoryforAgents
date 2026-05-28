#!/usr/bin/env python3
"""
MCP server for PersistentMemoryforAgents.

Exposes memory tools Claude Code (and any MCP-compatible agent) can call
natively during conversations. Memories persist to ~/.pma_store.db (SQLite)
across sessions.

Usage (Claude Code wires this up automatically via .mcp.json):
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

PROJECT_ROOT = str(Path(__file__).parent.parent)

# Resolve namespace once at startup: explicit env override → cwd → "default".
# Set PMA_NAMESPACE in the MCP server env block (per-project in .mcp.json) to
# pin a specific namespace; otherwise the working directory at launch is used so
# each project gets isolated episodic memories automatically.
def _resolve_namespace() -> str:
    explicit = os.environ.get("PMA_NAMESPACE", "").strip()
    if explicit:
        return explicit
    cwd = os.environ.get("PWD", "").strip()
    return cwd if cwd else "default"

NAMESPACE = _resolve_namespace()

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

# Auto-seed from project docs on first run in this namespace.
if len(_manager._store.all(namespace=NAMESPACE)) == 0:
    _manager.seed_from_project(PROJECT_ROOT, namespace=NAMESPACE)


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

    req = AddMemoryRequest(
        content=content,
        importance=importance,
        memory_type=tier,
        tags=tags,
        linked_entities=linked_entities,
        namespace=NAMESPACE,
    )
    entry = _manager.add(req)
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

    results = _manager.search(SearchQuery(query=query, limit=limit, memory_types=types, namespace=NAMESPACE))
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
    req = ContextRequest(query=query or None, token_budget=token_budget, namespace=NAMESPACE)
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
    exact = _manager._store.get(memory_id_prefix)
    if exact and exact.namespace == NAMESPACE:
        _manager.delete(exact.id)
        return f"Deleted [{exact.id[:8]}]: {exact.content[:60]}"

    matches = [e for e in _manager.list_all(namespace=NAMESPACE) if e.id.startswith(memory_id_prefix)]
    if not matches:
        return f"No memory found with ID prefix '{memory_id_prefix}'."
    if len(matches) > 1:
        return f"Ambiguous: {len(matches)} memories share that prefix. Use more characters."

    _manager.delete(matches[0].id)
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
    count = _manager.seed_from_project(root, namespace=NAMESPACE)
    if count == 0:
        return "No new memories added (already seeded or no docs found)."
    return f"Seeded {count} memories from {root}"


@mcp.tool()
def memory_stats() -> str:
    """Show memory system stats for the current namespace: tier counts, token usage, and GC pressure."""
    entries = _manager.list_all(namespace=NAMESPACE)
    by_tier: dict[str, dict] = {}
    total_tokens = 0
    for e in entries:
        t = e.memory_type.value
        bucket = by_tier.setdefault(t, {"count": 0, "tokens": 0})
        bucket["count"] += 1
        bucket["tokens"] += e.token_count
        total_tokens += e.token_count
    lines = [
        f"Namespace: {NAMESPACE}",
        f"Total: {len(entries)} memories | {total_tokens} tokens",
        "",
        "Tier breakdown:",
    ]
    for tier in ("working", "episodic", "semantic", "archived"):
        b = by_tier.get(tier, {"count": 0, "tokens": 0})
        if b["count"] > 0:
            lines.append(f"  {tier:10s} {b['count']:3d} memories  {b['tokens']:5d} tokens")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
