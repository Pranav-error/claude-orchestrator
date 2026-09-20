# Using claude-orchestrator

The full command reference. Read `README.md` first for the architecture
(two repos: this public code, plus your own private data repo at
`ORC_DATA_DIR`); this is the day-to-day reference.

## The one thing to understand first

`orc` is a plain Python program plus a git repo. It never calls the
Anthropic API, never checks your Claude subscription, never needs you
logged into anything. It works by reading and writing **local files**:

- `~/.claude/projects/*/memory/*.md` — memory Claude Code already wrote to disk
- `~/.claude/projects/*/*.jsonl` — session transcripts Claude Code already wrote to disk (this is where token usage comes from)
- `~/.claude/skills/*` — skill folders already on disk
- your own `$ORC_DATA_DIR/{memory,skills-registry,agent-log}` — its private state, also on disk

None of that requires a live Claude session, a valid subscription, or
being logged into any particular account. If your Claude subscription
lapses, if you're between accounts, if you're offline — `orc` still
works, because it was never talking to Anthropic in the first place.
The **only** feature that touches a network at all is `orc sync
push/pull`, and that talks to your own git remote, not Anthropic.

**Practical version:** you can open a plain terminal, with no Claude
Code process running anywhere, and run `orc memory search "some term"`
or `cat $ORC_DATA_DIR/memory/project/some-file.md` directly. It's just
text files.

## Three ways to run it

### 1. The interactive menu — best for browsing

```bash
orc
```
Opens a numbered menu (works from any directory once `bin/` is on
`PATH`). Pick a number, answer a prompt or two.

### 2. Flag commands — best for scripts, one-liners, or from inside Claude's `!` prompt

| Command | What it does |
|---|---|
| `orc init` | Bootstrap `$ORC_DATA_DIR` as a fresh private data repo — run this once, first |
| `orc identity show` | Which account/machine is "active" right now, per your own tracking |
| `orc identity set <label>` | Record an account switch (e.g. `orc identity set client-x`) |
| `orc identity log` | Every switch you've ever recorded |
| `orc memory search "<query>"` | Full-text search across every mirrored memory file |
| `orc memory sync` | Pull any new memory files from all your Claude Code projects into the canonical store |
| `orc memory links "<name>"` | Show what a memory links to / is linked from (`[[wiki-links]]`) |
| `orc memory link "<from>" "<to>"` | Add a link between two memories |
| `orc usage report --by day\|project\|model\|identity` | Real token usage, read straight from Claude Code's own transcripts |
| `orc skill list` | Every skill under `~/.claude/skills/`, managed or not, enabled or not |
| `orc skill adopt <name> [--source <url>]` | Bring an already-installed skill under registry control |
| `orc skill install <name> <git-url>` | Clone a new skill straight into the registry, enable it |
| `orc skill enable/disable <name>` | Toggle a managed skill on/off (content stays safe either way) |
| `orc agent log "<task>" success\|failed\|partial [--notes "..."]` | Record a finished subagent run |
| `orc agent list [--since] [--account] [--outcome]` | Query recorded runs |
| `orc sync push` | Commit + push local data-repo changes to your private remote |
| `orc sync pull` | Pull remote changes (refuses if you have uncommitted local changes) |
| `orc sync status` | Branch, ahead/behind, dirty state |
| `orc dashboard` | Print a colored snapshot (usage chart, skills, runs) right in the terminal |
| `orc dashboard --html [--no-open]` | Opt-in: write a shareable HTML file instead, open it in your browser |
| `orc dashboard --theme <name>` / `--color always\|never` / `--days N` | One-off overrides without touching your saved preferences |
| `orc config show` | Print your saved theme/icons/usage-window/color preferences |
| `orc config set <key> <value>` | Persist a preference — `theme` (amber/ocean/sunset/mono), `icons` (true/false), `usage_days`, `color` (auto/always/never) |

### 3. From inside a Claude Code chat prompt

Two different mechanisms, for two different needs:

- **`!orc <flag command>`** — the `!` prefix runs a real shell command
  and shows its output in the conversation. Works for anything from the
  table above: `!orc usage report`, `!orc memory search foo`. Doesn't
  work for the interactive menu — a chat turn can't hold a live,
  numbered back-and-forth with a program waiting on keyboard input.

- **`/orc <words>`** — a slash command that lets Claude itself map plain
  words onto the right flag command and run it for you. Comes with the
  Claude Code plugin (`/plugin install claude-orchestrator@claude-orchestrator`
  after adding the marketplace — see README), or copy/symlink
  `commands/orc.md` to `~/.claude/commands/orc.md` manually:
  ```
  /orc status
  /orc search some-term
  /orc identity client-x
  /orc skills
  /orc dashboard
  /orc sync
  ```
  New slash commands only appear in *new* sessions (started after the
  command file was created) — restart your `claude` session once if
  `/orc` doesn't autocomplete yet.

  For `/orc dashboard` specifically, the command passes `--color
  always` — Claude's Bash tool output isn't a real terminal, so without
  that flag the color would silently drop even though a real terminal
  shows it. The colored, box-drawn output itself lives in the tool
  result panel (expand "Ran 1 shell command" to see it) — Claude adds
  only a short caption underneath, never a retyped copy, since a
  markdown code fence doesn't render ANSI color at all.

- **The `claude-orchestrator` skill** (also bundled with the plugin,
  `skills/claude-orchestrator/SKILL.md`) — Claude can reach for `orc` on
  its own, without you typing `/orc` or `!orc`, when you ask something
  like "how much have I used today" or "search my memory for X". It
  checks `orc` is actually installed before assuming any of this works.

## What's automatic vs. what you trigger

| | Automatic | You trigger |
|---|---|---|
| Sync push/pull | Every `claude` session start/end, if you add the hooks (see README) | `orc sync push/pull` any other time |
| Memory mirroring | Not automatic | `orc memory sync` (safe to run anytime — idempotent, dedupes by content) |
| Skill management | Not automatic | `orc skill adopt/install/enable/disable` |
| Identity tracking | Not automatic — nothing can guess which account you're using | `orc identity set <label>` whenever you switch |
| Agent run logging | Not automatic | `orc agent log ...` |

## Accessing raw data without `orc` at all

Since everything is plain files, you don't strictly need the CLI for
read-only access:

```bash
# Read a memory file directly
cat "$ORC_DATA_DIR/memory/project/some-file.md"

# Grep across all memory without orc
grep -ril "some-term" "$ORC_DATA_DIR/memory/"

# See what identity is currently set
cat ~/.claude-orchestrator-identity.json

# See the raw skill manifest
cat "$ORC_DATA_DIR/skills-registry/manifest.json"

# See raw agent run history
cat "$ORC_DATA_DIR/agent-log/runs.jsonl"
```

`orc` exists to make querying, deduping, and cross-referencing this
data convenient — it isn't the only way in.

## On a new machine

1. `pip install claude-orchestrator` (or clone + `PATH` — see README)
2. If you already have a private data repo from another machine: `export ORC_DATA_DIR="/path/to/it"` then `orc sync pull`. Otherwise: `orc init`.
3. Manually copy the `hooks` block from another machine's `~/.claude/settings.json` if you want sync automatic there too — it's machine-local Claude Code config, not something `orc sync` carries.
4. `/plugin marketplace add Pranav-error/claude-orchestrator` then `/plugin install claude-orchestrator@claude-orchestrator` if you want `/orc` and the auto-invoked skill there too.
5. `orc identity set <label>` to tell it which account you're using on this machine.
