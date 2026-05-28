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
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STORE_PATH = Path.home() / ".pma_store.json"
SEEN_PROJECTS_PATH = Path.home() / ".pma_seen_projects.json"
ACTIVITY_PATH = Path.home() / ".pma_activity.json"
ACTIVITY_MAX = 50


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


def _log_activity(prompt: str, cwd: str, memory_ids: list[str], tokens: int) -> None:
    try:
        try:
            log = json.loads(ACTIVITY_PATH.read_text())
        except Exception:
            log = []
        log.insert(0, {
            "ts": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt[:120],
            "cwd": cwd,
            "count": len(memory_ids),
            "tokens": tokens,
            "ids": memory_ids[:20],
        })
        ACTIVITY_PATH.write_text(json.dumps(log[:ACTIVITY_MAX]))
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

        if cwd:
            seen = _load_seen_projects()
            if cwd not in seen:
                # Seed project docs into the project-scoped namespace
                count = manager.seed_from_project(cwd, namespace=cwd)
                seen.add(cwd)
                _save_seen_projects(seen)

        if manager._store.count() == 0:
            sys.exit(0)

        # Query project-specific memories + global working/semantic memories separately,
        # then merge so cross-project episodic noise doesn't bleed in.
        proj_namespace = cwd if cwd else "default"
        proj_resp = manager.get_context(ContextRequest(
            query=prompt, token_budget=1400, namespace=proj_namespace,
        ))
        global_resp = manager.get_context(ContextRequest(
            query=prompt, token_budget=600, namespace="default",
        ))

        seen_ids: set[str] = set()
        merged = []
        for m in proj_resp.memories + global_resp.memories:
            if m.id not in seen_ids:
                seen_ids.add(m.id)
                merged.append(m)

        if not merged:
            sys.exit(0)

        total_tokens = sum(m.token_count or 0 for m in merged)

        # Re-use resp shape for logging/output
        class _Resp:
            memories = merged
            total_tokens = total_tokens

        resp = _Resp()

        _log_activity(
            prompt=prompt,
            cwd=cwd,
            memory_ids=[m.id for m in resp.memories],
            tokens=resp.total_tokens,
        )

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
        pass


if __name__ == "__main__":
    main()
