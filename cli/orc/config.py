"""Paths shared by every orc module.

Two separate roots, deliberately:

- CODE_ROOT is wherever this checkout of the tool lives — public,
  shared, updated by a normal `git pull` on the tool's own repo.
- DATA_ROOT is a *different*, private git repo holding your actual
  memory/skills/agent-log content. It defaults to ~/.orc-data, or set
  ORC_DATA_DIR to point at your own private repo (e.g. one you created
  with `orc init` or already had from before this split existed).

This is what lets the tool itself be open source while every user's
actual data stays in their own private repo, never touching this one.
"""

import os
import socket
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[2]

DATA_ROOT = Path(os.environ.get("ORC_DATA_DIR", str(Path.home() / ".orc-data"))).expanduser()
MEMORY_DIR = DATA_ROOT / "memory"
SKILLS_MANIFEST = DATA_ROOT / "skills-registry" / "manifest.json"
SKILLS_STORE = DATA_ROOT / "skills-registry" / "store"
AGENT_LOG_DIR = DATA_ROOT / "agent-log"
IDENTITY_LOG = AGENT_LOG_DIR / "identity-log.jsonl"

CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_PROJECTS = CLAUDE_HOME / "projects"
CLAUDE_SKILLS = CLAUDE_HOME / "skills"

# Machine-local, never synced: which account is active on THIS machine right now.
LOCAL_IDENTITY_FILE = Path.home() / ".claude-orchestrator-identity.json"


def hostname() -> str:
    return socket.gethostname().split(".")[0]
