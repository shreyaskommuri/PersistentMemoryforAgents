#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

On every user prompt, retrieves relevant memories from the shared store and
injects them as additionalContext so Claude sees prior knowledge automatically.

Also auto-seeds the current project's docs (CLAUDE.md, README.md, etc.) the
first time Claude Code opens in a directory that hasn't been seen before.

Fails silently — if the store is empty or missing, no context is injected.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Resolve project root from this file's location (scripts/ → project root).
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STORE_PATH = Path.home() / ".pma_store.json"
SEEN_PROJECTS_PATH = Path.home() / ".pma_seen_projects.json"


def _load_seen_projects() -> set[str]:
    try:
        with open(SEEN_PROJECTS_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_seen_projects(seen: set[str]) -> None:
    try:
        with open(SEEN_PROJECTS_PATH, "w") as f:
            json.dump(sorted(seen), f)
    except Exception:
        pass


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = data.get("prompt", "").strip()
    cwd = data.get("cwd", "").strip()
    if not prompt:
        sys.exit(0)

    try:
        from app.memory_manager import MemoryManager
        from app.models import ContextRequest

        manager = MemoryManager()
        manager._store.load_from_file(str(STORE_PATH))

        # Auto-seed docs from the current project if it's new.
        if cwd:
            seen = _load_seen_projects()
            if cwd not in seen:
                count = manager.seed_from_project(cwd)
                if count > 0:
                    manager._store.save_to_file(str(STORE_PATH))
                seen.add(cwd)
                _save_seen_projects(seen)

        if manager._store.count() == 0:
            sys.exit(0)

        resp = manager.get_context(ContextRequest(query=prompt, token_budget=2000))
        if not resp.memories:
            sys.exit(0)

        lines = [
            f"- [{m.memory_type} | imp={m.importance:.1f}] {m.content}"
            for m in resp.memories
        ]
        context = (
            f"Relevant memories from prior sessions ({resp.total_tokens} tokens):\n"
            + "\n".join(lines)
        )
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }
        print(json.dumps(output))

    except Exception:
        pass  # never block the user's prompt


if __name__ == "__main__":
    main()
