# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [semver](https://semver.org/).

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
