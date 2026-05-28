#!/usr/bin/env python3
"""
Stop hook for Claude Code.

Fires after every Claude response. Saves the last exchange (user prompt +
assistant response) as an episodic memory so nothing is lost to auto-compaction.

The loop:
  UserPromptSubmit hook  →  inject relevant memories into context
  Stop hook              →  save this exchange back to the store

This means compaction doesn't matter: every substantial exchange is already
in PMA before the context window fills up.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MIN_RESPONSE_LENGTH = 250   # skip one-liners and trivial acks
MAX_PROMPT_CHARS    = 200   # how much of the prompt to store
MAX_RESPONSE_CHARS  = 500   # how much of the response to store
GC_THRESHOLD        = 80    # run GC when store exceeds this many memories


def _read_last_exchange(transcript_path: str) -> tuple[str, str] | None:
    """Return (user_prompt, full_assistant_response) for the most recent exchange.

    A single Claude turn produces multiple assistant entries in the transcript
    (one per reasoning step / tool use). This collects all of them between
    two user turns and concatenates them into one response string.
    """
    try:
        lines = [l.strip() for l in Path(transcript_path).read_text().splitlines() if l.strip()]
    except Exception:
        return None

    messages = []
    for line in lines:
        try:
            messages.append(json.loads(line))
        except Exception:
            continue

    def extract_text(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()
        return ""

    # Find the last user turn that has real text
    last_user_idx = None
    last_user_text = ""
    for i, msg in enumerate(messages):
        if msg.get("type") == "user":
            text = extract_text(msg.get("message", {}).get("content", ""))
            if text.strip():
                last_user_idx = i
                last_user_text = text

    if last_user_idx is None:
        return None

    # Collect all assistant text produced after that user turn
    assistant_parts = []
    for msg in messages[last_user_idx + 1:]:
        if msg.get("type") == "user":
            break  # next user turn started — stop
        if msg.get("type") == "assistant":
            text = extract_text(msg.get("message", {}).get("content", ""))
            if text.strip():
                assistant_parts.append(text.strip())

    assistant_text = " ".join(assistant_parts)
    return (last_user_text, assistant_text) if assistant_text else None


def _prompt_hash(prompt: str) -> str:
    return hashlib.md5(prompt[:200].encode()).hexdigest()[:12]


def _extract_response_summary(response: str, max_chars: int) -> str:
    """Take the first substantive paragraph from Claude's response."""
    for para in response.split("\n\n"):
        para = para.strip()
        if len(para) > 60:
            return para[:max_chars]
    return response[:max_chars]


def _importance(prompt: str, response: str) -> float:
    combined = prompt + response
    if len(combined) > 3000:
        score = 0.75
    elif len(combined) > 1000:
        score = 0.65
    else:
        score = 0.50

    # Boost for responses that contain real work
    work_signals = ["```", "def ", "class ", "fixed", "implement", "decided",
                    "error", "bug", "updated", "added", "removed"]
    if any(sig in combined.lower() for sig in work_signals):
        score = min(0.90, score + 0.10)

    return score


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        sys.exit(0)

    cwd = data.get("cwd", "").strip()
    namespace = cwd if cwd else "default"

    exchange = _read_last_exchange(transcript_path)
    if not exchange:
        sys.exit(0)

    user_prompt, assistant_response = exchange

    if len(assistant_response) < MIN_RESPONSE_LENGTH:
        sys.exit(0)  # too short to be worth saving

    try:
        from app.memory_manager import MemoryManager
        from app.models import AddMemoryRequest, MemoryType

        manager = MemoryManager()

        # Dedup by prompt hash stored in metadata
        ph = _prompt_hash(user_prompt)
        existing_hashes = {
            e.metadata.get("prompt_hash")
            for e in manager._store.all(namespace=namespace)
        }
        if ph in existing_hashes:
            sys.exit(0)

        summary = _extract_response_summary(assistant_response, MAX_RESPONSE_CHARS)
        content = (
            f"User: {user_prompt[:MAX_PROMPT_CHARS].strip()}\n"
            f"Claude: {summary}"
        )

        manager.add(AddMemoryRequest(
            content=content,
            memory_type=MemoryType.episodic,
            importance=_importance(user_prompt, assistant_response),
            tags=["session", "auto-saved"],
            namespace=namespace,
            metadata={"prompt_hash": ph, "project": cwd},
        ))

        # Periodically GC to evict low-scoring stale memories
        if manager._store.count() > GC_THRESHOLD:
            manager.run_gc()

    except Exception:
        pass


if __name__ == "__main__":
    main()
