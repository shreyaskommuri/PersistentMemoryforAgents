#!/usr/bin/env python3
"""
Seed the memory store from project documentation.

Run once after setup (or re-run any time to pick up doc changes).
Reads CLAUDE.md, CODEX.md, docs/ARCHITECTURE.md, docs/ROADMAP.md, README.md
and saves each section as a semantic memory in ~/.pma_store.json.

Usage:
    python3 scripts/init_memory.py
    python3 scripts/init_memory.py /path/to/other/project
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STORE_PATH = Path.home() / ".pma_store.json"


def main() -> None:
    from app.memory_manager import MemoryManager

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT

    manager = MemoryManager()
    manager._store.load_from_file(str(STORE_PATH))

    before = manager._store.count()
    count = manager.seed_from_project(str(target))
    manager._store.save_to_file(str(STORE_PATH))
    after = manager._store.count()

    print(f"Seeded {count} new memories from {target}")
    print(f"Store: {before} → {after} total memories saved to {STORE_PATH}")


if __name__ == "__main__":
    main()
