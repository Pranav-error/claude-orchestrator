"""Append-only log of subagent runs.

Subagents are ephemeral — there's no live state worth polling once they've
finished. What's worth keeping is a record of what ran, under which
account, and how it turned out, so `orc agent list` can answer "what did I
have running on the client's account last Tuesday" after the fact.
"""

import json
from datetime import datetime, timezone

from . import config, identity

VALID_OUTCOMES = {"success", "failed", "partial"}


def _runs_log_path():
    # Resolved at call time, not import time, so tests (and any future
    # config override) can redirect config.AGENT_LOG_DIR and have it apply.
    return config.AGENT_LOG_DIR / "runs.jsonl"


def log_run(task: str, outcome: str, notes: str = "") -> dict:
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(VALID_OUTCOMES)}, got {outcome!r}")

    who = identity.current()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account": who["label"] if who else "unknown",
        "machine": config.hostname(),
        "task": task,
        "outcome": outcome,
        "notes": notes,
    }

    config.AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _runs_log_path().open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def list_runs(since: str | None = None, account: str | None = None, outcome: str | None = None) -> list[dict]:
    runs_log = _runs_log_path()
    if not runs_log.exists():
        return []

    cutoff = _parse(since) if since else None
    rows = []
    for line in runs_log.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if cutoff and _parse(entry["timestamp"]) < cutoff:
            continue
        if account and entry["account"] != account:
            continue
        if outcome and entry["outcome"] != outcome:
            continue
        rows.append(entry)
    return rows
