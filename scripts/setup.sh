#!/usr/bin/env bash
# One-time setup for PersistentMemoryforAgents.
# Safe to re-run — merges into existing configs rather than overwriting.
#
# What it does:
#   1. Creates .venv and installs Python dependencies
#   2. Writes .claude/settings.json for this project (MCP server + hook)
#   3. Merges persistent-memory into ~/.mcp.json  (global MCP server)
#   4. Merges the UserPromptSubmit hook into ~/.claude/settings.json  (global hook)
#   5. Seeds the memory store from project docs

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"

# ── Colors ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "  ${GREEN}✓${NC} $*"; }
pending() { echo -e "  ${YELLOW}→${NC} $*"; }

echo ""
echo -e "${BOLD}PersistentMemoryforAgents — setup${NC}"
echo "  Repo: $REPO_ROOT"
echo ""

# ── 1. Python venv ──────────────────────────────────────────────────────────
if [ -f "$VENV/bin/python3" ]; then
    info "venv already exists, skipping creation"
else
    pending "Creating venv..."
    python3 -m venv "$VENV"
    info "venv created at $VENV"
fi

PYTHON="$VENV/bin/python3"

pending "Installing dependencies..."
"$PYTHON" -m pip install -q -r "$REPO_ROOT/requirements.txt"
info "Dependencies installed"

# ── 2. Project .claude/settings.json ────────────────────────────────────────
pending "Writing .claude/settings.json..."
mkdir -p "$REPO_ROOT/.claude"
cat > "$REPO_ROOT/.claude/settings.json" << EOF
{
  "mcpServers": {
    "persistent-memory": {
      "type": "stdio",
      "command": "$PYTHON",
      "args": ["$REPO_ROOT/app/mcp_server.py"]
    }
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$PYTHON $REPO_ROOT/scripts/memory_hook.py"
          }
        ]
      }
    ]
  }
}
EOF
info "Wrote .claude/settings.json"

# ── 3. Global ~/.mcp.json ───────────────────────────────────────────────────
pending "Updating ~/.mcp.json..."
"$PYTHON" - "$PYTHON" "$REPO_ROOT/app/mcp_server.py" << 'PYEOF'
import json, sys, pathlib

python_path, server_script = sys.argv[1], sys.argv[2]
mcp_path = pathlib.Path.home() / ".mcp.json"
try:
    existing = json.loads(mcp_path.read_text()) if mcp_path.exists() else {}
except Exception:
    existing = {}
existing.setdefault("mcpServers", {})["persistent-memory"] = {
    "type": "stdio",
    "command": python_path,
    "args": [server_script],
}
mcp_path.write_text(json.dumps(existing, indent=2) + "\n")
PYEOF
info "Updated ~/.mcp.json"

# ── 4. Global ~/.claude/settings.json (hook only — mcpServers not allowed) ──
pending "Updating ~/.claude/settings.json..."
"$PYTHON" - "$PYTHON" "$REPO_ROOT/scripts/memory_hook.py" << 'PYEOF'
import json, sys, pathlib

python_path, hook_script = sys.argv[1], sys.argv[2]
settings_path = pathlib.Path.home() / ".claude" / "settings.json"
try:
    existing = json.loads(settings_path.read_text()) if settings_path.exists() else {}
except Exception:
    existing = {}

hook_command = f"{python_path} {hook_script}"
new_entry = {"matcher": "", "hooks": [{"type": "command", "command": hook_command}]}

existing.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
# Replace any prior persistent-memory hook, append the updated one.
kept = [h for h in existing["hooks"]["UserPromptSubmit"]
        if "memory_hook.py" not in str(h)]
existing["hooks"]["UserPromptSubmit"] = kept + [new_entry]

settings_path.write_text(json.dumps(existing, indent=2) + "\n")
PYEOF
info "Updated ~/.claude/settings.json"

# ── 5. Seed memory store from project docs ──────────────────────────────────
pending "Seeding memory store from project docs..."
SEEDED=$("$PYTHON" "$REPO_ROOT/scripts/init_memory.py" 2>&1 | grep "Seeded" | head -1)
info "${SEEDED:-Memory store already seeded}"

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Setup complete.${NC} Restart Claude Code for changes to take effect."
echo ""
echo "  Memory tools available in any project:"
echo "    remember / recall / load_context / forget / memory_stats"
echo ""
echo "  Context is injected automatically on every prompt."
echo ""
