<p align="center">
  <img src="assets/mascot-animated.svg" width="220" alt="orc mascot: a pixel-art cat with a wagging tail" />
</p>

<h1 align="center">claude-orchestrator</h1>
<p align="center"><em>the same cat that greets you on <code>orc</code> startup — wagging its tail right here in the README, no screenshot required</em></p>

[![PyPI](https://img.shields.io/pypi/v/claude-orc)](https://pypi.org/project/claude-orc/)
[![Python versions](https://img.shields.io/pypi/pyversions/claude-orc)](https://pypi.org/project/claude-orc/)
[![Tests](https://github.com/Pranav-error/claude-orchestrator/actions/workflows/test.yml/badge.svg)](https://github.com/Pranav-error/claude-orchestrator/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A personal control plane for a [Claude Code](https://claude.com/claude-code) setup that spans multiple accounts, multiple machines, and a pile of hand-installed skills — so none of that state is pinned to whichever login happens to be active right now.

`orc` never calls the Anthropic API and never checks your subscription. It only reads and writes local files: your existing `~/.claude/projects/*/memory/*.md`, your session transcripts (`~/.claude/projects/*/*.jsonl`, where real token-usage numbers come from), your `~/.claude/skills/*`, and its own small private data store. It works with no Claude account logged in at all — the only network call anywhere in it is `orc sync`, and that talks to your own git remote, not Anthropic.

## Why

Three problems, one root cause — state trapped on a single machine/account instead of following the person:

1. **Memory is fragmented and misfiled.** Claude Code's own per-project memory is keyed by working-directory path, not topic. Notes about one long-running effort end up scattered across a dozen unrelated project folders purely because of whatever `cwd` you happened to be in.
2. **Accounts rotate.** Your own account, a shared one, a client's — swapped whenever one hits a rate limit. Nothing should leak into someone else's environment, and nothing should vanish when you step away from your own login.
3. **Skills are ad-hoc.** Some come from a marketplace, some are hand-downloaded from random GitHub repos with no record of source, version, or whether they're still wanted.

## What it looks like

`orc dashboard` in a plain-text terminal (colored in a real one — theme picked with `orc config set theme`):

```
╭────────────────────────────────────────────────────────────────────────────╮
│ claude-orchestrator                                                        │
│ ❯ work on client-laptop   ·   main                                         │
╰────────────────────────────────────────────────────────────────────────────╯

┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│      212       │ │      6/9       │ │     18,442     │ │       37       │
│  memory files  │ │ skills enabled │ │ messages (14d) │ │   agent runs   │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘

── USAGE · last 14 days ──────────────────────────────────────────────────────
  2026-09-15  ██████████████░░░░░░░░░░░░░░░░     612,340  740 msgs
  2026-09-16  ██████████████████████████████   1,304,912  1,588 msgs
  2026-09-17  ████████░░░░░░░░░░░░░░░░░░░░░░     351,220  402 msgs
  ...

── SKILLS ────────────────────────────────────────────────────────────────────
  caveman        ● enabled     orc-managed
  graphify       ● enabled     unmanaged
  superpowers    ○ disabled    orc-managed

── RECENT AGENT RUNS ─────────────────────────────────────────────────────────
  2026-09-21  fix-flaky-test        work        ✓ succeeded
  2026-09-20  migrate-schema        client-acct ✓ succeeded

orc config for themes/options  ·  orc --help for every command
```

## Architecture: two repos, on purpose

This code is public. Your actual data is not — and never touches this repo.

```mermaid
flowchart TB
    subgraph Code["This repo (public, code only)"]
        CLI["src/orc — the orc CLI"]
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

Pick one:

**As a Python package** (recommended — gives you a real `orc` command, no PATH setup):
```bash
pip install claude-orc          # or: pipx install claude-orc
```

**Zero-install, from a clone:**
```bash
git clone https://github.com/Pranav-error/claude-orchestrator ~/claude-orchestrator
echo 'export PATH="$HOME/claude-orchestrator/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
source ~/.zshrc
```

Either way, then:
```bash
orc init          # bootstraps your private data directory + git repo
orc identity set mine
orc dashboard
```

`orc init` prints the one manual step left (creating an actual private remote — `gh repo create --private` or any git host) so your data can sync across machines too. No dependencies beyond Python 3.10+ and git — the CLI is stdlib-only.

**As a Claude Code plugin** (adds `/orc` and an auto-invoked skill that reaches for `orc` on its own when relevant — install the CLI above first, this just teaches Claude about it):
```
/plugin marketplace add Pranav-error/claude-orchestrator
/plugin install claude-orchestrator@claude-orchestrator
```

## What it does

| | |
|---|---|
| **Memory** | `orc memory sync` mirrors Claude Code's scattered per-project memory into one topic-keyed, deduped store. `orc memory search` (relevance-ranked), `orc memory links`/`link` for `[[wiki-style]]` cross-references, `orc memory graph` to see which memories are hubs, `orc memory here` for the current project's memories. |
| **Identity** | `orc identity set <label>` records which account is active on this machine right now — since Claude Code itself never does, and a filesystem never changes on an account swap on the same box (only a different *machine* needs `orc sync`). |
| **Usage** | `orc usage report --by day\|project\|model\|identity` — real token counts read straight from Claude Code's own transcripts. Nothing tracked manually. |
| **Skills** | `orc skill adopt/install/enable/disable` — takes custody of a skill (moves it into your data repo, symlinks it back), so hand-downloaded skills have a recorded source and travel with `orc sync` instead of needing manual reinstall per machine. |
| **Agent log** | `orc agent log/list` — append-only record of subagent runs, filterable by account/outcome/date. |
| **Sync** | `orc sync push/pull/status` — wraps git for your private data repo. Refuses to pull over uncommitted local changes rather than guessing how to merge them. |
| **Dashboard** | `orc dashboard` — a colored snapshot rendered directly in your terminal (boxed header, usage bar chart, skills, recent runs). No browser, no server. `--html` opts into a shareable file instead. |
| **Config** | `orc config show/set` — theme (amber/ocean/sunset/mono), icons on/off, usage window, forced color, startup banner on/off. |

Full command reference: [USAGE.md](USAGE.md). Third-party skills worth adding alongside it: `orc ecosystem` (also in the interactive menu), or read it straight from the repo at [src/orc/data/ECOSYSTEM.md](src/orc/data/ECOSYSTEM.md).

Bare `orc` (no arguments) drops into an interactive menu covering all of the above — pick by number, or just type part of an option's name (`search`, `dash`, `graph`) and it resolves the same way a shell's tab-completion would; an ambiguous substring lists the candidates instead of guessing.

## FAQ

**Does this touch Anthropic's API or my subscription?** No. Every command reads/writes local files only. The one exception is `orc sync`, which talks to *your own* git remote — nothing ever leaves your machine toward Anthropic.

**What happens if I run this under the wrong account?** Nothing leaks by construction: `orc identity set <label>` is a label you set per machine, not a credential, and it's stored in your private data repo — never in this public one. Memory, skills, and agent-log entries all live under `ORC_DATA_DIR`, so switching Claude accounts on the same machine doesn't touch `orc`'s state at all; only switching *machines* needs `orc sync`.

**Will this conflict with Claude Code's own memory/skills?** No — `orc memory sync` *reads* `~/.claude/projects/*/memory/*.md` and mirrors it into a separate, topic-keyed store; it never rewrites Claude Code's own files. `orc skill adopt` moves a skill's actual files into your data repo and leaves a symlink behind, so Claude Code still sees it in the same place.

**Do I need a GitHub account or a paid plan?** No. `ORC_DATA_DIR` can be any git repo — GitHub, GitLab, a self-hosted server, or even just a local bare repo for offline use between two machines you can `scp` between.

**Is the pixel-art cat load-bearing?** Purely cosmetic — `orc config set banner false` turns it off, and it's already skipped automatically in piped/non-interactive output.

## Using it from inside Claude Code

Installing the plugin (above) gives you both pieces automatically:

- **`/orc <words>`** — a slash command that maps plain words onto the right `orc` invocation: `/orc status`, `/orc search <query>`, `/orc dashboard`, etc. See `commands/orc.md` for how the mapping works, and why `orc dashboard` specifically needs `--color always` when run through Claude's own Bash tool.
- **A skill named `claude-orchestrator`** (`skills/claude-orchestrator/SKILL.md`) that Claude can reach for *on its own* — ask "how much have I used today" or "search my memory for X" without typing `/orc` at all.

Not using the plugin system? Copy or symlink `commands/orc.md` to `~/.claude/commands/orc.md` for just the slash command.

To make sync automatic at the start/end of every Claude Code session (any account, any project), add to your `~/.claude/settings.json`:

```json
"hooks": {
  "SessionStart": [{ "hooks": [{ "type": "command",
    "command": "~/claude-orchestrator/bin/orc sync pull >> ~/.orc-sync.log 2>&1 || true" }] }],
  "SessionEnd": [{ "hooks": [{ "type": "command",
    "command": "~/claude-orchestrator/bin/orc sync push >> ~/.orc-sync.log 2>&1 || true" }] }]
}
```

## Roadmap

Ideas under consideration for future releases, not yet built:

- **`orc memory prune`** — flag memories that no longer match the live codebase (a referenced file was deleted, a function was renamed) so stale entries get surfaced instead of silently misleading a later session.
- **`orc usage report --by session`** — break usage down per Claude Code session rather than just day/project/model/identity, useful for spotting one runaway conversation.
- **Multi-remote sync** — let `ORC_DATA_DIR` push/pull against more than one remote (e.g. a personal GitLab mirror alongside GitHub) for redundancy.
- **`orc dashboard --watch`** — a live-refreshing terminal dashboard instead of a one-shot snapshot.

Opinions and PRs on any of these welcome — see [CHANGELOG.md](CHANGELOG.md) for what has already shipped.

## Testing

```bash
python3 -m unittest discover -s tests -v
```

125 tests, stdlib `unittest` only, fully isolated via tmp-dir path overrides — none of them touch your real `~/.claude` or your data repo. Includes a real two-machine push/pull simulation over a local bare git remote. Runs automatically on every push across Python 3.10–3.13 via GitHub Actions (badge above).

## Releases & versioning

This follows [semver](https://semver.org/). See [CHANGELOG.md](CHANGELOG.md) for what changed in each version, and [RELEASING.md](RELEASING.md) for the maintainer release process (tag a version, CI builds and publishes to PyPI automatically via trusted publishing — no manual upload step). `pip install --upgrade claude-orchestrator` to get the latest.

## License

MIT — see [LICENSE](LICENSE).
