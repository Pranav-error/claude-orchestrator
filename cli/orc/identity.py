"""Tracks which account is active on this machine, right now.

The account you're logged into Claude Code as is never recorded by Claude
Code itself, so orc keeps its own thin log: every time you switch accounts
you tell orc with `orc identity set <label>`, and that switch (label,
machine, timestamp) gets appended to the synced identity-log. Everything
else in this repo (memory entries, usage reports) can then be attributed
to "whoever was active" during a given time window, without ever touching
credentials.
"""

import json
from datetime import datetime, timezone

from . import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current() -> dict | None:
    if not config.LOCAL_IDENTITY_FILE.exists():
        return None
    return json.loads(config.LOCAL_IDENTITY_FILE.read_text())


def set_identity(label: str) -> dict:
    entry = {
        "label": label,
        "machine": config.hostname(),
        "since": _now(),
    }
    config.LOCAL_IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.LOCAL_IDENTITY_FILE.write_text(json.dumps(entry, indent=2) + "\n")

    config.AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with config.IDENTITY_LOG.open("a") as f:
        f.write(json.dumps({"event": "identity_switch", **entry}) + "\n")

    return entry


def history() -> list[dict]:
    if not config.IDENTITY_LOG.exists():
        return []
    lines = config.IDENTITY_LOG.read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def label_at(timestamp_iso: str) -> str | None:
    """Best-effort: which identity label was active at a given UTC timestamp,
    based on the synced identity-log (works across machines once pulled)."""
    target = _parse(timestamp_iso)
    candidates = [h for h in history() if _parse(h["since"]) <= target]
    if not candidates:
        return None
    return max(candidates, key=lambda h: _parse(h["since"]))["label"]
