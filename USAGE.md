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
Opens the menu (works from any directory once `bin/` is on `PATH`).
Pick an item by number — or just type part of its name, which is usually
faster than scanning for the right digit:

```
> search        # -> Search memory
> dash          # -> Dashboard
> graph         # -> Memory graph
> 0  /  q       # quit
```

Matching is case-insensitive. An exact label match always wins; a
substring that matches several options lists them rather than guessing
(typing `sync` reports both "Sync memory" and "Sync (push/pull…)").

### 2. Flag commands — best for scripts, one-liners, or from inside Claude's `!` prompt

| Command | What it does |
|---|---|
| `orc init` | Bootstrap `$ORC_DATA_DIR` as a fresh private data repo — run this once, first |
| `orc status` | Identity + today's usage (with model), in one call |
| `orc identity show` | Which account/machine is "active" right now, per your own tracking |
| `orc identity set <label>` | Record an account switch (e.g. `orc identity set client-x`) |
| `orc identity log` | Every switch you've ever recorded |
| `orc memory search "<query>"` | Full-text search across every mirrored memory file |
| `orc memory sync` | Pull any new memory files from all your Claude Code projects into the canonical store |
| `orc memory links "<name>"` | Show what a memory links to / is linked from (`[[wiki-links]]`) |
| `orc memory link "<from>" "<to>"` | Add a link between two memories |
| `orc memory suggest "<name>" [--top N]` | Candidates worth manually linking to, by text overlap -- never applied automatically |
| `orc memory related [--quiet-if-none]` | Confirmed cross-project links for the current project -- safe for a `SessionStart` hook |
| `orc memory graph [--top N]` | Rank memories by link count — which ones are hubs |
| `orc memory here [--limit N]` | Memories belonging to the current project |
| `orc memory browse` | Interactive terminal browser (needs a real tty -- run directly, not via `!orc`/`/orc`) |
| `orc usage report --by day\|project\|model\|identity` | Real token usage (and which model(s) produced it) read straight from Claude Code's own transcripts |
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
| `orc config set <key> <value>` | Persist a preference — `theme` (amber/ocean/sunset/mono), `icons` (true/false), `usage_days`, `color` (auto/always/never), `banner` (true/false) |
| `orc version` | Show the startup banner, version, and install/data paths |

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
| Cross-project linking | Never automatic — a false-positive link is worse than a missed one | `orc memory link`, or `^L` inside `orc memory browse` |
| Cross-project nudge at session start | If you add the second `SessionStart` hook (see README) — but only echoes links you already confirmed, never a guess | `orc memory related` any other time |

## Worked example: giving a new project context from an old one

The scenario this was built for: you start a new project that's similar
to one you've already done work on, and you want a future Claude Code
session in the new project to be nudged toward what you already learned
in the old one — without re-explaining it, and without the tool ever
*guessing* a connection on your behalf.

**1. Find the candidate.** From inside the new project (or via `orc
memory browse`, searching for its memory file), ask what it's similar
to:

```
$ orc memory suggest darapana-v2-overview
 41%  production-notes           (~/Documents/GitHub/darapana)
 33%  registration-fixes         (~/Documents/GitHub/darapana)
```

This is a ranked guess (word overlap, nothing smarter) — a nomination
for you to look at, not a claim. Open `orc memory browse` instead of the
raw command if you want to read the candidate's content before deciding:
search for `darapana-v2-overview`, and its preview pane shows the same
suggestions inline, live, next to the file itself.

**2. Confirm it, either way.**

```
$ orc memory link darapana-v2-overview production-notes
linked: darapana-v2-overview -> production-notes
```

Or, from inside `orc memory browse` with `darapana-v2-overview`
selected: `^L` (Ctrl-L), type `production-notes` to filter the second
search box, `Enter` to confirm. Same underlying call either way — the
browser is just a faster way to search-then-link without leaving the
preview.

**3. It's now a real, permanent `[[link]]`** in
`darapana-v2-overview.md`'s body, synced like any other memory content.
`orc memory links darapana-v2-overview` shows it from either direction.

**4. Get it surfaced without asking.** Because this link crosses a
project boundary (`darapana-v2` -> `darapana`), it shows up in:

```
$ orc memory related
darapana-v2-overview  ->  production-notes  (~/Documents/GitHub/darapana)
```

Wire the optional second `SessionStart` hook (README → "Using it from
inside Claude Code") and this line — or nothing, via `--quiet-if-none`,
when there's nothing to report — becomes part of what Claude Code sees
at the start of every session in `darapana-v2`, without you having to
ask for it that session.

## Features in depth

### Memory

Claude Code already writes memory files under
`~/.claude/projects/<encoded-cwd>/memory/*.md` — but keyed by whatever
directory you happened to be in, so one ongoing effort's notes end up
scattered across every project you ever ran Claude from while thinking
about it. `orc memory sync` mirrors every one of those files into
`$ORC_DATA_DIR/memory/<type>/`, organized by the `type:` field in each
file's frontmatter (`user`, `feedback`, `project`, `reference`) instead
of by path. It's idempotent and content-hash deduped — running it
again after nothing changed mirrors nothing new, and two projects that
happen to have identical memory content (a cloned starter repo, say)
collapse into one entry instead of two.

```
$ orc memory sync
mirrored: my-project/notes.md -> memory/project/notes.md
2 mirrored, 41 already present
```

Search is full-text across name, description, and body:

```
$ orc memory search "auth flow"
feedback/auth-retry-logic.md          auth-retry-logic
  Retries must back off exponentially — a flat retry loop caused a real outage.
```

Memories can reference each other with `[[wiki-link]]` syntax (the
same convention Claude itself uses when told to link related memories).
`orc memory links "<name>"` resolves both directions — what a memory
links *to*, and what links back to *it* — even across a name collision
that forced a file to live as `name--project.md`:

```
$ orc memory links "auth-retry-logic"
auth-retry-logic

  links to (1):
    -> incident-2026-08-postmortem

  linked from (3):
    <- session-handoff-2026-08-19
    <- verification-habits
    <- pr-body-conventions
```

`orc memory link "<from>" "<to>"` adds a link by hand (idempotent — a
repeat call reports "already linked" instead of duplicating it).

**Suggesting a link, and echoing confirmed ones.** `orc memory suggest
"<name>"` nominates candidates worth manually linking to, ranked by
crude word overlap with every other unlinked memory — it never writes
anything itself, since a wrong link is worse than a missed one and
there's no way to verify from text alone that two memories are
genuinely about the same kind of project rather than just sharing
vocabulary:

```
$ orc memory suggest darapana-v2-overview
 41%  production-notes           (~/Documents/GitHub/darapana)
 33%  registration-fixes         (~/Documents/GitHub/darapana)
```

(The project shown in parentheses is recovered from a session
transcript under that memory's source project, not just the dashes in
`source_project` swapped back to slashes — a real directory name can
contain a literal dash too, so that swap alone is ambiguous. See
`memory.readable_project` if you're curious.)

Once you've confirmed one with `orc memory link`, it's a real,
persisted `[[link]]` — and if it crosses a project boundary, `orc
memory related` (run from inside either project) echoes it:

```
$ orc memory related
darapana-v2-overview  ->  production-notes  (~/Documents/GitHub/darapana)
```

`--quiet-if-none` prints nothing when there's nothing to report, which
is what makes it safe to wire into a `SessionStart` hook (see README) —
every other session's start stays silent.

When a query matches several memories, you get a numbered list rather
than a guess — and in the interactive menu, one you can pick from
directly:

```
$ orc memory links "pranav"
error: 'pranav' is ambiguous — 11 matches:
  1. user-profile-r-sai-pranav
  2. user-pranav-and-kartik
  ...
```

**Search is relevance-ranked.** A hit in the title means the memory is
*about* that term; a hit buried in the body might be an aside. Name
matches score above description matches, which score above body
frequency (capped, so a word repeated 40 times can't outrank a real
title match). Ties break on name, so ordering is identical on every
machine.

This is deliberately a weighted count rather than a real search index
(SQLite FTS5 + BM25). For a few hundred markdown files the ranking
quality is indistinguishable, and an index would add a schema to
migrate, keep in sync on every edit, and repair when it drifts — for a
tool whose whole premise is that your data is plain files you can
`cat` and `grep` without it.

### Memory graph

`orc memory graph` ranks memories by how connected they are — total
`[[link]]` count, in plus out — so the hubs of your notes are obvious
at a glance. Memories with no links are excluded; a hub ranking of
unconnected files isn't a ranking.

```
$ orc memory graph --top 5
── MEMORY GRAPH · top 5 most-connected ───────────────────────────────
  contribution-state          ████████  26 links (11 in / 15 out)
  contribution-strategy       ████████  26 links (9 in / 17 out)
  pg-family-state             ██████░░  20 links (10 in / 10 out)
  ai-use-policies             █████░░░  17 links (11 in / 6 out)
  jesper-direction            █████░░░  17 links (9 in / 8 out)
```

Two memories can end up sharing a display name (a collision that sync
resolved into `slug--project.md`); those rows fall back to their unique
stem so they don't read as duplicates.

### Memory browse

`orc memory browse` is an interactive terminal browser over the whole
store — needs a real terminal (curses attaches to a tty), so run it
directly rather than through `!orc` or `/orc`, which have none.

With an empty search box it doesn't dump the whole store at you — it
shows how many memories exist per type, and the most recently touched
ones, so you're oriented before you start typing:

```
orc memory browse

 search: _
 user 10  feedback 45  project 170  reference 21

 recent:
   contribution-state.md                   2h ago
   grass-next-action-when-slot-frees.md    1d ago
```

Type anything and it filters to matches (name, description, type, or
stem), name hits ranked first. The right-hand pane renders the selected
file's body, its existing `[[links]]`, and — this is the point of the
whole thing — a "related, not linked" list from `orc memory suggest`
for that file:

```
 search: darapana-v2                          1 match

  ▸ darapana-v2-overview   project │ # darapana-v2-overview
                                    │
                                    │ (file body...)
                                    │
                                    │ Related, not linked (^L to link):
                                    │   41%  production-notes
                                    │   33%  registration-fixes
```

**`^L` (Ctrl-L)** opens a second search box to pick a memory to link
the selected one to — confirming with Enter writes a real `[[link]]`
(the same thing `orc memory link` does) and returns to the list. **Not
plain `l`**: that has to stay typeable into the search box. `Enter`
opens the selected file in `$EDITOR`; `Esc` quits (also not `q`, for
the same reason).

### Memories for the current project

`orc memory here` shows what you've recorded while working in the
project you're standing in — useful when returning to a repo after a
gap.

```
$ cd ~/code/my-app/backend
$ orc memory here --limit 3
3 memories from this project:

  [project] deploy-runbook
    The exact promote/rollback sequence, and the one step that's easy to skip.
  [feedback] pr-review-conventions
    ...
```

It anchors to the enclosing **repo root** (`.git`/`.hg`/`.svn`) rather
than the literal working directory, so running it from
`my-app/backend/src` still surfaces the whole repo's memories. Being
deeper inside a project should show you more of its context, not less.

### Identity

Claude Code never records which of *your* accounts a session ran
under — it just authenticates and goes. If you rotate between your own
account, a shared one, and a client's, `orc identity set <label>` is
the only record of "who was active when," kept in a small machine-local
file (`~/.claude-orchestrator-identity.json`) plus an append-only log
in your data repo (`identity-log.jsonl`) so it also carries across
machines via `orc sync`.

Switching accounts on the *same* machine needs nothing beyond
`orc identity set` — the filesystem doesn't change when you log into a
different Claude account, so there's nothing to sync. Only a genuinely
different physical machine needs `orc sync push/pull`.

```
$ orc identity set client-acme
identity set: client-acme on my-laptop (since 2026-09-20T10:15:00+00:00)
$ orc identity log
2026-09-18T09:00:00+00:00  mine                  my-laptop
2026-09-20T10:15:00+00:00  client-acme           my-laptop
```

### Status

`orc status` is the one-call version of "am I set up right and what did
I use today" — the active identity plus today's usage, model included:

```
$ orc status
identity: mine on my-laptop (since 2026-09-20T10:15:00+00:00)
usage today (2026-09-28): 106 in / 31,816 out / 54 msgs  ·  model: claude-sonnet-5
```

This is what `/orc` with no arguments runs (see `commands/orc.md`) —
one Bash call instead of `orc identity show` plus a separate
`orc usage report --by day`, since Claude Code would otherwise have to
read both and stitch them into prose itself, at a real token cost for
something this cheap to compute directly.

### Usage

Token counts come straight from Claude Code's own session transcripts
(`~/.claude/projects/*/*.jsonl`) — every assistant message already
carries an exact `usage` block. Nothing is estimated or tracked
separately; `orc` just reads what's already on disk and aggregates it.
Timestamps in those transcripts are UTC; day-grouping converts to your
system's local time first, so "today" means the same thing `orc status`
and your own clock mean by it.

```
$ orc usage report --by day --since 2026-09-15
key            input      output     cache_r     cache_w    msgs  models
2026-09-15      1252      389779   234437519     5879759      628  claude-opus-5, claude-sonnet-5
2026-09-16       842      327137   260835562     6949025      421  claude-sonnet-5
...
```

`--by project` groups by the real working directory (shortened to `~`
for readability) rather than Claude Code's dash-encoded folder name —
`~/code/my-app`, not `-Users-you-code-my-app`. Two unrelated repos that
happen to share a subfolder name (`backend/`, `frontend/`) stay
distinct rows rather than silently merging.

`--by identity` cross-references the identity log above, so you can
see exactly how much was used under which account:

```
$ orc usage report --by identity
key             input      output     cache_r     cache_w    msgs  models
client-acme       472      190295    57369527      427323      236  claude-sonnet-5
mine              809      289596   176988218     4786873      405  claude-opus-5, claude-sonnet-5
unattributed    38464    16390562  8010690230   194017070    19222  claude-opus-5
```

(`unattributed` is any usage from before you ever ran `orc identity set` —
there's no way to retroactively know who was active.) The `models`
column lists every distinct model seen in that row — a day or identity
can span a model switch, which the token totals alone would hide.
`--by model` skips the column since it's already the row's key.

### Skills

Most Claude Code skills people install by hand come from a random
GitHub repo with zero record of where they came from. `orc skill
adopt <name>` takes custody of an already-installed skill: it moves
the real directory out of `~/.claude/skills/<name>` into
`$ORC_DATA_DIR/skills-registry/store/<name>` and replaces it with a
symlink, recording source/version/who-adopted-it in
`skills-registry/manifest.json`. `orc skill install <name> <git-url>`
does the same for a *new* skill, cloning it straight into the store.

Once managed, `enable`/`disable` is just adding/removing that symlink —
the content stays safe in the store either way, so disabling never
risks losing it.

```
$ orc skill list
name             status      source                          version
banner-design    enabled     github.com/example/banner-skill  a1b2c3d
brand            unmanaged   unmanaged                        -
```

Because the content lives in your data repo now, `orc sync` carries
adopted skills across machines — no more re-downloading the same
GitHub repo by hand on every new laptop.

**Skills that came from `claude plugin install` show up too, marked
`plugin`** — read straight from Claude Code's own
`~/.claude/plugins/installed_plugins.json`, not adopted into orc's
store:

```
$ orc skill list
name             status      source                          version
ponytail         plugin      plugin:ponytail@ponytail         4.10.0
ponytail-review  plugin      plugin:ponytail@ponytail         4.10.0
banner-design     enabled     github.com/example/banner-skill  a1b2c3d
```

This is deliberately read-only: `orc skill adopt`/`enable`/`disable`
refuse a plugin-provided skill with a clear error rather than a
generic "nothing to adopt" one, because Claude's plugin manager already
owns that skill's version and update path — copying it into orc's store
on top of that would just be a second copy that can silently drift from
the one `claude plugin update` actually keeps current. Manage those
with `claude plugin` (enable/disable/uninstall), not `orc skill`; a
`status: blocked` row means the plugin is in your `blocklist.json`, not
that anything is wrong with orc's view of it.

### Ecosystem

`orc ecosystem` prints a survey of widely-adopted third-party Claude
Code skills worth installing via `orc skill install` — real GitHub
star/fork counts, licenses, and what each one does. It's the same
content as [ECOSYSTEM.md](src/orc/data/ECOSYSTEM.md), shipped inside
the package itself (not just this git checkout) so it's readable
after a plain `pip install claude-orc` too. Also reachable from the
interactive menu as "Browse third-party skills".

### Agent log

Subagents are ephemeral — once one finishes there's no live state left
to poll, so "tracking" them means keeping a record after the fact, not
watching them run. `orc agent log "<task>" success|failed|partial
[--notes]` appends one line (timestamp, account, machine, task,
outcome, notes) to `agent-log/runs.jsonl`. `orc agent list` filters by
`--since`, `--account`, or `--outcome`.

```
$ orc agent log "refactor auth module" success --notes "3 files changed"
logged: [success] refactor auth module (account=mine, machine=my-laptop)
$ orc agent list --outcome failed --since 2026-09-01
2026-09-05T14:22:00+00:00  [failed ]  mine            migrate database schema
  connection timeout after 30s, rolled back
```

### Sync

`orc sync push/pull/status` wraps git for `$ORC_DATA_DIR`. `push`
stages and commits anything dirty (tagged with the active identity and
machine in the commit message) then pushes; `pull` refuses outright if
you have uncommitted local changes rather than guessing how to merge
them — conflicts on append-only logs and memory files are exactly the
kind a silent `--theirs`/`--ours` resolution can quietly corrupt.

```
$ orc sync status
branch: main   ahead: 0   behind: 1   clean
$ orc sync pull
pulled: Fast-forward, 3 files changed
```

Wire it to Claude Code's own `SessionStart`/`SessionEnd` hooks (see
README) and this becomes fully automatic — pull at the start of every
session, push at the end, regardless of which account is logged in.

### Dashboard

`orc dashboard` renders a colored snapshot directly in the terminal:
a boxed header (identity, sync branch/dirty state), a row of stat
cards (memory file count, skills enabled, messages in the usage
window, agent runs logged), a gradient-colored bar chart of daily
token usage, a skills table, and recent agent runs. No browser, no
server — `--html` opts into a shareable static file instead, for the
rare time you actually want to send someone a link.

Respects `NO_COLOR` and non-tty output automatically (falls back to
plain text when piped or redirected); `--color always` forces color
even then, which is exactly what makes it render properly inside
Claude Code's own Bash tool output (see the `/orc` section above).

### Config

Preferences persist in `~/.claude-orchestrator-settings.json`
(machine-local, like identity — terminal capabilities and taste are a
per-machine thing):

```
$ orc config show
theme = amber
icons = True
usage_days = 14
color = auto
banner = True

themes: amber, ocean, sunset, mono
$ orc config set theme ocean
theme = ocean
```

The interactive Preferences screen validates the key before asking for
a value, and shows what that key accepts (`theme` offers the theme
list, `icons`/`banner` offer true/false, and so on).

Any dashboard flag (`--theme`, `--color`, `--days`) overrides the
saved preference for that one run without touching the saved config.

### Startup banner

Like Claude Code's own colored icon-and-version header, or Gemini
CLI's compact ASCII icon: a small pixel-art cat (drawn with the Unicode
half-block trick for roughly square pixels), whose tail wags for about
a second before settling into a curled rest pose. Fixed brand colors,
independent of your dashboard theme — a logo should stay recognizable
the way Claude's icon is always orange regardless of your terminal
theme.

Shown by `orc` (the interactive menu) and `orc version`. The animation
only runs in a real interactive terminal; piped or captured output gets
the static text, since a cursor-redraw animation can't render there.
`Ctrl+C` during it settles the pose rather than interrupting the
program.

```
$ orc version
[pixel-art cat]  claude-orchestrator
[tail wagging]   v0.1.0 · orc
                 a personal control plane for Claude Code

orc 0.1.0
code:    /path/to/claude-orchestrator
data:    /path/to/your/data/repo
```

(Run it yourself to see the actual colors and motion — this file can't
render ANSI.)

Purely cosmetic — turn it off for a quieter start with
`orc config set banner false`.

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

1. `pip install claude-orc` (or clone + `PATH` — see README)
2. If you already have a private data repo from another machine: `export ORC_DATA_DIR="/path/to/it"` then `orc sync pull`. Otherwise: `orc init`.
3. Manually copy the `hooks` block from another machine's `~/.claude/settings.json` if you want sync automatic there too — it's machine-local Claude Code config, not something `orc sync` carries.
4. `/plugin marketplace add Pranav-error/claude-orchestrator` then `/plugin install claude-orchestrator@claude-orchestrator` if you want `/orc` and the auto-invoked skill there too.
5. `orc identity set <label>` to tell it which account you're using on this machine.
