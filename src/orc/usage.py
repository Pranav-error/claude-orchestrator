"""Token usage, aggregated from Claude Code's own session transcripts.

Claude Code writes one JSONL transcript per session under
~/.claude/projects/<project>/<session-id>.jsonl. Every assistant message in
there carries a `usage` block (input/output/cache tokens) and a timestamp.
Nothing needs to be tracked manually — this just reads what already exists
and, if an identity-log is present, attributes each message to whichever
account label was active at that moment.
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config, identity


def _project_label(cwd: str | None, fallback_dir_name: str) -> str:
    """Claude Code names each project directory after the cwd with every
    '/' replaced by '-' (e.g. ~/Documents/GitHub/foo -> -Users-x-Documents-
    GitHub-foo), which is unreadable. The transcripts carry the real `cwd`,
    so prefer that — but keep the FULL path (just with $HOME shortened to
    '~'), not only its basename: two unrelated repos can share a subfolder
    name (backend/, frontend/, app/, core/...), and collapsing to a bare
    basename would silently merge their usage into one misleading bucket.
    Falls back to the raw encoded name for the rare entry missing cwd."""
    if cwd:
        home = str(Path.home())
        return "~" + cwd[len(home):] if cwd.startswith(home) else cwd
    return fallback_dir_name.lstrip("-") or fallback_dir_name


def _iter_usage_events():
    if not config.CLAUDE_PROJECTS.exists():
        return
    for jsonl_path in config.CLAUDE_PROJECTS.glob("*/*.jsonl"):
        try:
            with jsonl_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = entry.get("message")
                    ts = entry.get("timestamp")
                    if not (isinstance(msg, dict) and ts):
                        continue
                    usage = msg.get("usage")
                    if not usage:
                        continue
                    yield {
                        "timestamp": ts,
                        "project": _project_label(entry.get("cwd"), jsonl_path.parent.name),
                        "session": jsonl_path.stem,
                        "model": msg.get("model", "unknown"),
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                    }
        except OSError:
            continue


def report(since: str | None = None, group_by: str = "day"):
    """group_by: 'day', 'project', 'model', or 'identity'."""
    cutoff = datetime.fromisoformat(since).replace(tzinfo=timezone.utc) if since else None
    buckets = defaultdict(lambda: {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0, "messages": 0})

    for ev in _iter_usage_events():
        ts = datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00"))
        if cutoff and ts < cutoff:
            continue

        if group_by == "day":
            key = ts.date().isoformat()
        elif group_by == "project":
            key = ev["project"]
        elif group_by == "model":
            key = ev["model"]
        elif group_by == "identity":
            key = identity.label_at(ev["timestamp"]) or "unattributed"
        else:
            raise ValueError(f"unknown group_by: {group_by}")

        b = buckets[key]
        b["input"] += ev["input_tokens"]
        b["output"] += ev["output_tokens"]
        b["cache_write"] += ev["cache_creation_input_tokens"]
        b["cache_read"] += ev["cache_read_input_tokens"]
        b["messages"] += 1

    return dict(sorted(buckets.items()))
