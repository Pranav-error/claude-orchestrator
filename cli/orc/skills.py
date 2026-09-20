"""Tracks and manages skills/plugins installed under ~/.claude/skills/.

Most of these were hand-downloaded from random GitHub repos with no source
recorded anywhere, so this can't just introspect what's live and infer
where it came from. Instead it takes custody: `orc skill adopt` moves an
existing skill directory into this repo's skills-registry/store/ and
replaces it with a symlink, `orc skill install` clones a fresh one straight
into the store. Either way, once a skill is under management, disable/
enable just removes/recreates the symlink — the content lives in the repo,
so it now travels with the sync clone instead of being reinstalled by hand
on every machine.
"""

import json
import shutil
import subprocess
from datetime import datetime, timezone

from . import config, identity


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if not config.SKILLS_MANIFEST.exists():
        return {"skills": {}}
    return json.loads(config.SKILLS_MANIFEST.read_text())


def _save(manifest: dict) -> None:
    config.SKILLS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    config.SKILLS_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def _who() -> str:
    cur = identity.current()
    return cur["label"] if cur else "unknown"


def list_skills() -> list[dict]:
    manifest = _load()["skills"]
    live = {p.name for p in config.CLAUDE_SKILLS.glob("*") if p.is_dir() or p.is_symlink()} if config.CLAUDE_SKILLS.exists() else set()

    rows = []
    seen = set()
    for name, entry in manifest.items():
        seen.add(name)
        live_path = config.CLAUDE_SKILLS / name
        is_symlinked_to_store = live_path.is_symlink() and live_path.resolve() == (config.SKILLS_STORE / name).resolve()
        rows.append({
            "name": name,
            "source": entry.get("source", "unknown"),
            "version": entry.get("version", "unknown"),
            "managed": True,
            "enabled": is_symlinked_to_store,
        })

    for name in sorted(live - seen):
        rows.append({"name": name, "source": "unmanaged", "version": "-", "managed": False, "enabled": True})

    return sorted(rows, key=lambda r: r["name"])


def adopt(name: str, source: str = "unknown") -> dict:
    """Bring an already-installed, unmanaged skill under registry control."""
    live_path = config.CLAUDE_SKILLS / name
    if not live_path.exists() or live_path.is_symlink():
        raise ValueError(f"{name}: not a plain installed directory at {live_path} — nothing to adopt")

    config.SKILLS_STORE.mkdir(parents=True, exist_ok=True)
    store_path = config.SKILLS_STORE / name
    if store_path.exists():
        raise ValueError(f"{name}: already present in the store at {store_path}")

    shutil.move(str(live_path), str(store_path))
    live_path.symlink_to(store_path)

    manifest = _load()
    manifest["skills"][name] = {
        "source": source,
        "version": "unmanaged-adopted",
        "adopted_at": _now(),
        "adopted_by": _who(),
    }
    _save(manifest)
    return manifest["skills"][name]


def install(name: str, source_url: str) -> dict:
    """Clone a skill fresh from its source straight into the store, then enable it."""
    config.SKILLS_STORE.mkdir(parents=True, exist_ok=True)
    store_path = config.SKILLS_STORE / name
    if store_path.exists():
        raise ValueError(f"{name}: already in the store at {store_path}")

    subprocess.run(["git", "clone", "--depth", "1", source_url, str(store_path)], check=True)
    sha = subprocess.run(
        ["git", "-C", str(store_path), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    live_path = config.CLAUDE_SKILLS / name
    if live_path.exists() or live_path.is_symlink():
        raise ValueError(f"{name}: {live_path} already exists — remove it first")
    config.CLAUDE_SKILLS.mkdir(parents=True, exist_ok=True)
    live_path.symlink_to(store_path)

    manifest = _load()
    manifest["skills"][name] = {
        "source": source_url,
        "version": sha,
        "adopted_at": _now(),
        "adopted_by": _who(),
    }
    _save(manifest)
    return manifest["skills"][name]


def enable(name: str) -> None:
    manifest = _load()
    if name not in manifest["skills"]:
        raise ValueError(f"{name}: not managed — `orc skill adopt` or `orc skill install` it first")
    store_path = config.SKILLS_STORE / name
    if not store_path.exists():
        raise ValueError(f"{name}: manifest entry exists but {store_path} is missing")
    live_path = config.CLAUDE_SKILLS / name
    if live_path.exists() or live_path.is_symlink():
        if live_path.is_symlink() and live_path.resolve() == store_path.resolve():
            return  # already enabled
        raise ValueError(f"{name}: {live_path} exists and isn't the managed symlink — remove it first")
    live_path.symlink_to(store_path)


def disable(name: str) -> None:
    manifest = _load()
    if name not in manifest["skills"]:
        raise ValueError(f"{name}: not managed — nothing to disable")
    live_path = config.CLAUDE_SKILLS / name
    store_path = config.SKILLS_STORE / name
    if live_path.is_symlink() and live_path.resolve() == store_path.resolve():
        live_path.unlink()
    # if it's already not linked, disabling is a no-op — content stays safe in the store
