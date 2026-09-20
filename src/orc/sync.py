"""Cross-machine sync: the local clone follows you across machines by
pushing at session end and pulling at session start, independent of which
Claude account is logged in (see README — account switches on the SAME
machine need no sync at all, only a different machine does).

This deliberately does not auto-resolve conflicts. The synced state is
mostly append-only logs and memory files, which is exactly the kind of
content a silent --theirs/--ours resolution can quietly corrupt — a
conflict here should stop and tell you, not guess.
"""

import subprocess

from . import config, identity


def _run(args):
    return subprocess.run(
        ["git", "-C", str(config.DATA_ROOT), *args],
        capture_output=True, text=True,
    )


def _has_changes() -> bool:
    result = _run(["status", "--porcelain"])
    return bool(result.stdout.strip())


def push() -> dict:
    _run(["add", "-A"])
    committed = False

    if _has_changes():
        who = identity.current()
        label = who["label"] if who else "unknown"
        message = f"orc sync: {label} on {config.hostname()}"
        commit = _run(["commit", "-m", message])
        if commit.returncode != 0:
            return {"committed": False, "pushed": False, "ok": False, "detail": commit.stderr.strip()}
        committed = True

    push_result = _run(["push"])
    if push_result.returncode != 0:
        return {"committed": committed, "pushed": False, "ok": False, "detail": push_result.stderr.strip()}

    detail = push_result.stdout.strip() or push_result.stderr.strip() or "already up to date"
    return {"committed": committed, "pushed": True, "ok": True, "detail": detail}


def pull() -> dict:
    if _has_changes():
        return {
            "ok": False,
            "detail": "local changes are uncommitted — run `orc sync push` first, or they may be overwritten",
        }

    result = _run(["pull"])
    if result.returncode != 0:
        return {"ok": False, "detail": (result.stdout + result.stderr).strip()}
    return {"ok": True, "detail": result.stdout.strip() or "already up to date"}


def status() -> dict:
    branch = _run(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    ahead_behind = _run(["rev-list", "--left-right", "--count", "HEAD...@{u}"])
    dirty = _has_changes()
    ahead, behind = "?", "?"
    if ahead_behind.returncode == 0 and ahead_behind.stdout.strip():
        parts = ahead_behind.stdout.strip().split()
        if len(parts) == 2:
            ahead, behind = parts
    return {"branch": branch, "ahead": ahead, "behind": behind, "dirty": dirty}
