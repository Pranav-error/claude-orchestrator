# claude-orchestrator

A personal control plane for a [Claude Code](https://claude.com/claude-code) setup that spans multiple accounts, multiple machines, and a pile of hand-installed skills — so none of that state is pinned to whichever login happens to be active right now.

`orc` never calls the Anthropic API and never checks your subscription. It only reads and writes local files: your existing `~/.claude/projects/*/memory/*.md`, your session transcripts (`~/.claude/projects/*/*.jsonl`, where real token-usage numbers come from), your `~/.claude/skills/*`, and its own small private data store. It works with no Claude account logged in at all — the only network call anywhere in it is `orc sync`, and that talks to your own git remote, not Anthropic.

## Why

Three problems, one root cause — state trapped on a single machine/account instead of following the person:

1. **Memory is fragmented and misfiled.** Claude Code's own per-project memory is keyed by working-directory path, not topic. Notes about one long-running effort end up scattered across a dozen unrelated project folders purely because of whatever `cwd` you happened to be in.
2. **Accounts rotate.** Your own account, a shared one, a client's — swapped whenever one hits a rate limit. Nothing should leak into someone else's environment, and nothing should vanish when you step away from your own login.
3. **Skills are ad-hoc.** Some come from a marketplace, some are hand-downloaded from random GitHub repos with no record of source, version, or whether they're still wanted.

## Architecture: two repos, on purpose

This code is public. Your actual data is not — and never touches this repo.

```mermaid
flowchart TB
    subgraph Code["This repo (public, code only)"]
        CLI["cli/orc — the orc CLI"]
    end

    subgraph Data["Your own private repo (ORC_DATA_DIR)"]
        Memory["memory/ — topic-keyed, deduped"]
        Skills["skills-registry/ — adopted/installed skills"]
        AgentLog["agent-log/ — run history, identity log"]
    end

    subgraph ClaudeHome["~/.claude (Claude Code's own files)"]
        Transcripts["projects/*/*.jsonl — session transcripts"]
        LocalMemory["projects/*/memory/*.md"]
        LocalSkills["skills/*"]
    end

    CLI -- "reads (never writes)" --> Transcripts
    CLI -- "orc memory sync" --> LocalMemory
    CLI -- "orc skill adopt/enable/disable" --> LocalSkills
    CLI -- reads/writes --> Memory
    CLI -- reads/writes --> Skills
    CLI -- reads/writes --> AgentLog
    CLI -- "orc sync push/pull" --> Data

    style Code fill:#1e293b,color:#fff,stroke:#64748b
    style Data fill:#0f172a,color:#fff,stroke:#64748b
    style ClaudeHome fill:#111827,color:#fff,stroke:#374151
```

`ORC_DATA_DIR` (default `~/.orc-data`) points at your private data repo. Update this tool with a normal `git pull` on this repo; sync *your* data with `orc sync`, which operates on `ORC_DATA_DIR`, never on this checkout.

## Install

```bash
git clone https://github.com/Pranav-error/claude-orchestrator ~/claude-orchestrator
echo 'export PATH="$HOME/claude-orchestrator/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
source ~/.zshrc

orc init          # bootstraps your private data directory + git repo
orc identity set mine
orc dashboard
```

`orc init` prints the one manual step left (creating an actual private remote — `gh repo create --private` or any git host) so your data can sync across machines too. No dependencies beyond Python 3.10+ and git — the CLI is stdlib-only.

## What it does

| | |
|---|---|
| **Memory** | `orc memory sync` mirrors Claude Code's scattered per-project memory into one topic-keyed, deduped store. `orc memory search`, `orc memory links`/`link` for `[[wiki-style]]` cross-references. |
| **Identity** | `orc identity set <label>` records which account is active on this machine right now — since Claude Code itself never does, and a filesystem never changes on an account swap on the same box (only a different *machine* needs `orc sync`). |
| **Usage** | `orc usage report --by day\|project\|model\|identity` — real token counts read straight from Claude Code's own transcripts. Nothing tracked manually. |
| **Skills** | `orc skill adopt/install/enable/disable` — takes custody of a skill (moves it into your data repo, symlinks it back), so hand-downloaded skills have a recorded source and travel with `orc sync` instead of needing manual reinstall per machine. |
| **Agent log** | `orc agent log/list` — append-only record of subagent runs, filterable by account/outcome/date. |
| **Sync** | `orc sync push/pull/status` — wraps git for your private data repo. Refuses to pull over uncommitted local changes rather than guessing how to merge them. |
| **Dashboard** | `orc dashboard` — a colored snapshot rendered directly in your terminal (boxed header, usage bar chart, skills, recent runs). No browser, no server. `--html` opts into a shareable file instead. |
| **Config** | `orc config show/set` — theme (amber/ocean/sunset/mono), icons on/off, usage window, forced color. |

Full command reference: [USAGE.md](USAGE.md).

Bare `orc` (no arguments) drops into a numbered interactive menu covering all of the above — useful when you don't want to remember flag names.

## Using it from inside Claude Code

Copy (or symlink) `claude-commands/orc.md` to `~/.claude/commands/orc.md` to get a `/orc` slash command usable directly in a Claude Code chat — `/orc status`, `/orc search <query>`, `/orc dashboard`, etc. See the top of that file for how the argument mapping works, and why `orc dashboard` specifically needs `--color always` when run through Claude's own Bash tool.

To make sync automatic at the start/end of every Claude Code session (any account, any project), add to your `~/.claude/settings.json`:

```json
"hooks": {
  "SessionStart": [{ "hooks": [{ "type": "command",
    "command": "~/claude-orchestrator/bin/orc sync pull >> ~/.orc-sync.log 2>&1 || true" }] }],
  "SessionEnd": [{ "hooks": [{ "type": "command",
    "command": "~/claude-orchestrator/bin/orc sync push >> ~/.orc-sync.log 2>&1 || true" }] }]
}
```

## Testing

```bash
cd cli && python3 -m unittest tests.test_orc -v
```

64 tests, stdlib `unittest` only, fully isolated via tmp-dir path overrides — none of them touch your real `~/.claude` or your data repo. Includes a real two-machine push/pull simulation over a local bare git remote.

## License

MIT — see [LICENSE](LICENSE).
