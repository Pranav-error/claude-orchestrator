"""Updates the tool's own code checkout (CODE_ROOT) -- distinct from `orc
sync`, which pushes/pulls the *private data* repo. `orc update` is a plain
`git pull --ff-only` in CODE_ROOT for the normal case (a git clone, or
`pip install -e .`); a checkout that isn't a git working tree at all (a
plain `pip install claude-orc`) has no git history to pull, so this
reports that instead of failing confusingly.

A second, easy-to-miss install path exists on top of this: installing the
Claude Code *plugin* (`claude plugin install claude-orchestrator@...`)
copies the code into `~/.claude/plugins/cache/...`, a separate snapshot
`git pull` here never touches. If PATH happens to resolve `orc` to that
copy instead of this checkout, `orc update` would silently update the
wrong thing -- so this also checks for that and says so.
"""

import json
import subprocess

from . import config


def _run(args):
    return subprocess.run(
        ["git", "-C", str(config.CODE_ROOT), *args],
        capture_output=True, text=True,
    )


def is_git_checkout() -> bool:
    result = _run(["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def plugin_install_note() -> str | None:
    """If claude-orchestrator is *also* installed as a Claude Code plugin
    (a separate copy under ~/.claude/plugins/cache/, not this checkout),
    return a note that `orc update` doesn't touch it -- else None."""
    if not config.CLAUDE_PLUGINS_MANIFEST.exists():
        return None
    try:
        manifest = json.loads(config.CLAUDE_PLUGINS_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for plugin_key, records in manifest.get("plugins", {}).items():
        if plugin_key.split("@")[0] != "claude-orchestrator":
            continue
        version = records[0].get("version", "unknown") if records else "unknown"
        return (
            f"note: claude-orchestrator is also installed as a Claude Code plugin ({plugin_key}, v{version}) -- "
            f"that's a separate copy this command doesn't touch; run `claude plugin update {plugin_key}` "
            f"if `orc` on your PATH resolves there instead of this checkout (check with `which orc`)"
        )
    return None


def apply() -> dict:
    if not is_git_checkout():
        return {
            "is_git": False, "ok": False,
            "detail": f"{config.CODE_ROOT} isn't a git checkout -- update with `pip install --upgrade claude-orc` (or `pipx upgrade claude-orc`) instead",
        }

    dirty = _run(["status", "--porcelain"])
    if dirty.stdout.strip():
        return {
            "is_git": True, "ok": False,
            "detail": f"uncommitted changes in {config.CODE_ROOT} -- commit or stash them before updating",
        }

    result = _run(["pull", "--ff-only"])
    ok = result.returncode == 0
    detail = (result.stdout + result.stderr).strip() or "already up to date"
    return {"is_git": True, "ok": ok, "detail": detail}
