# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [semver](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-09-21

### Added
- **`orc memory graph`** — ranks memories by `[[link]]` count (in + out) as colored bars, in the same visual language as the usage chart. Unlinked memories are excluded. Also available from the interactive menu.
- **`orc memory here`** — surfaces memories recorded from the current project. Anchors to the enclosing repo root (`.git`/`.hg`/`.svn`), so running it anywhere inside a repo shows that whole repo's memories.
- **Type-ahead menu selection** — the interactive menu now accepts any substring of an option's label (`search`, `dash`, `graph`) as well as its number. Exact label matches win; an ambiguous substring lists the candidates instead of guessing.
- **`orc version`** — version, install/data paths, and the startup banner.
- **Startup banner** — an original pixel-art cat (Unicode half-block trick, fixed brand colors) with a tail that wags for ~1s in a live terminal and settles into a curled rest pose. Skipped entirely in plain-text/piped output, where it would be meaningless. Toggle with `orc config set banner false`.
- **`ECOSYSTEM.md`** — a survey of widely-adopted third-party Claude Code skills worth adopting via `orc skill install`, with star counts verified against the GitHub API rather than blog posts.
- **README mascot** — `assets/mascot.svg`/`mascot-animated.svg`, pixel-perfect SVG renders of the actual startup banner's cat (same grid data as `banner.py`, including a real tail-wag animation via SMIL), plus a "What it looks like" dashboard example and an FAQ section.

### Changed
- **Search results are now relevance-ranked** rather than filesystem-ordered: name matches score above description matches, which score above body-frequency matches (capped, so a repeated word can't outrank a real title match). Ties break on name so ordering is stable across machines. Previously, searching `verification` returned 59 hits with the memories actually *named* `verification-*` at positions 21 and 23.
- **Interactive menu redesigned** to match the dashboard — boxed header showing live identity and sync state, theme-colored numbers, compact flat list.
- **Preferences flow** validates the setting key before asking for a value (instead of after), and its valid-key list is generated from the settings themselves so it can't drift stale. Each key shows a type-specific value hint.
- **Ambiguous memory queries** now raise a structured `AmbiguousMemoryQuery` carrying the match list, rendered as a numbered list — and in the menu, as a pickable one. Previously dumped every match as a single unreadable comma-separated line.

### Fixed
- **`bin/orc` destroyed the caller's working directory** by `cd`-ing into its own `src/` before exec'ing, which silently broke `orc memory here` (the first cwd-relative command). Now passes `PYTHONPATH` instead.
- **Non-deterministic memory-graph ordering** broke CI on Python 3.11 and would have numbered an ambiguous query's matches differently on different machines: `_all_files_by_stem()` built its dict from an unsorted `rglob()`, and filesystem walk order differs between APFS and ext4.
- **`Ctrl+C` during the startup animation** raised a traceback out of the program; it now settles on the rest pose.

## [0.1.0] - 2026-09-20

Initial public release.

### Added
- `orc identity {set,show,log}` — track which account is active on this machine, independent of Claude Code's own auth
- `orc memory {sync,search,links,link}` — mirror Claude Code's per-project memory into one topic-keyed, deduped store; full-text search; `[[wiki-link]]` cross-references
- `orc usage report --by {day,project,model,identity}` — real token usage read directly from Claude Code's session transcripts
- `orc skill {list,adopt,install,enable,disable}` — a registry for hand-installed/downloaded skills, with recorded source and version
- `orc agent {log,list}` — append-only subagent run history
- `orc sync {push,pull,status}` — git-based sync of your private data directory across machines
- `orc dashboard` — a colored, box-drawn snapshot rendered directly in the terminal; `--html` for a shareable file
- `orc config {show,set}` — themes (amber/ocean/sunset/mono), icons, usage window, forced color
- `orc init` — bootstrap a fresh private data repo
- Interactive numbered menu (bare `orc`)
- `/orc` Claude Code slash command, mapping natural-language-ish arguments to the right flag command
- `claude-orchestrator` Claude Code skill — auto-invoked without the user typing `/orc`
- Installable via `pip`/`pipx` (a real `orc` console script) and as a Claude Code plugin (`/plugin marketplace add`)
- 64 automated tests, fully isolated from real `~/.claude` and data-repo state
