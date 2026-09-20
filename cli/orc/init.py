"""Bootstraps a fresh private data repo for a new user.

The tool itself (this code) is public. Your actual memory/skills/agent-log
content needs somewhere private to live — this creates that directory,
turns it into a git repo, and tells you the one manual step left (creating
the actual private remote is your call, not something to do silently).
"""

import subprocess

from . import config


def run() -> dict:
    data_root = config.DATA_ROOT

    if (data_root / ".git").exists():
        return {"already_initialized": True, "path": data_root}

    for sub in ("memory", "skills-registry/store", "agent-log"):
        (data_root / sub).mkdir(parents=True, exist_ok=True)

    (data_root / ".gitignore").write_text("dashboard.html\n__pycache__/\n*.pyc\n")

    subprocess.run(["git", "init", "-q", "-b", "main", str(data_root)], check=True)
    subprocess.run(["git", "-C", str(data_root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(data_root), "commit", "-q", "-m", "orc init: bootstrap private data repo"],
        check=True,
    )

    return {"already_initialized": False, "path": data_root}
