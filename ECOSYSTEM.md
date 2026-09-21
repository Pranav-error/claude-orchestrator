# Claude Code ecosystem — skills worth adopting

A survey of widely-adopted Claude Code skills and plugins installable from
GitHub, as candidates for `orc skill adopt` / `orc skill install`.

**Inclusion bar:** >2,000 GitHub stars, actively maintained, and installable
as a Claude Code skill/plugin (not just an article or a tutorial repo).
Star/fork counts were read from the GitHub API on **2026-09-21**, not from
blog posts — several write-ups quote numbers that are months stale.

Everything here is third-party. `orc skill install <name> <git-url>` records
the source and pinned commit in your registry, so an adopted skill's origin
stays traceable and travels with `orc sync`.

---

## Directly relevant to what `orc` already does

These overlap with the memory/context/token problems this tool exists for.

| Skill | Stars | Forks | License | What it does |
|---|---:|---:|---|---|
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 107.1k | 6.2k | mixed (MIT + BSL) | Compresses agent prose output (~65% fewer output tokens) while leaving code, commands, paths and error text untouched. Pairs directly with `orc usage report` — you can measure the before/after yourself. |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | 120.0k | 11.6k | Apache-2.0 | Turns a codebase (plus docs, SQL schemas, configs, PDFs) into a queryable knowledge graph. Already installed in this setup. Conceptually adjacent to `orc memory graph` — that one graphs *your memories*, this graphs *your code*. |
| [mksglu/context-mode](https://github.com/mksglu/context-mode) | 23.8k | 1.7k | non-standard | Context-window optimization: sandboxes tool output (claims ~98% reduction), persists session memory, enforces routing across platforms. Closest thing to a direct competitor for `orc`'s memory role — worth reading before building more in that direction. |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27.0k | 2.3k | MIT | File-based persistent planning that survives `/clear` and compaction. Same underlying instinct as `orc memory sync` — keep state on disk, not in the context window. |

## Broader capability skills

| Skill | Stars | Forks | License | What it does |
|---|---:|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 289.5k | 25.9k | — | The largest Claude Code skills library — testing, debugging, collaboration, meta-skills. Installable as a plugin. |
| [github/spec-kit](https://github.com/github/spec-kit) | 138.1k | 12.4k | — | GitHub's spec-driven development toolkit. |
| [upstash/context7](https://github.com/upstash/context7) | 62.3k | 3.0k | — | MCP server pulling version-specific library docs into context, so the model stops guessing at stale APIs. |
| [oraios/serena](https://github.com/oraios/serena) | 29.7k | 2.0k | — | LSP-backed semantic code retrieval and editing via MCP. |
| [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) | 3.9k | 635 | — | Reference patterns for Claude Code hooks — relevant to how `orc` wires its own `SessionStart`/`SessionEnd` sync. |

## Catalogs (to find more)

| Catalog | Stars | Forks | Notes |
|---|---:|---:|---|
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | 75.4k | 8.7k | Curated skills list. |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 54.4k | 4.7k | The broadest hand-picked resource list. |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 36.6k | 4.1k | Anthropic's own plugin directory — already a registered marketplace in most setups. |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 34.7k | 3.7k | MIT-licensed, agent-skills-focused. |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 26.2k | 3.7k | 380+ skills spanning engineering and non-engineering domains. |
| [rohitg00/awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit) | 2.6k | 964 | Agents, commands, hooks, MCP configs. |

---

## Notes before installing anything

- **Star count is popularity, not an audit.** A skill runs with your Claude
  Code session's permissions. Read `SKILL.md` before adopting — especially
  for anything that shells out, writes files, or wires up hooks.
- **Licenses vary and some are non-standard.** `caveman` is MIT *except* for
  Engine-linked directories under BSL 1.1; `context7-mode` and the Composio
  catalog report no standard SPDX license. Check before redistributing or
  using commercially.
- **Overlap is real.** `context-mode` and `planning-with-files` solve
  problems adjacent to `orc memory`. Running several context-management
  tools at once can mean competing rules and duplicated state.
- **Token cost is per-session.** Every enabled skill adds to the always-on
  context budget. `claude plugin details <name>` reports the projected cost
  before you commit.

## Adopting one with `orc`

```bash
orc skill install caveman https://github.com/JuliusBrussee/caveman.git
orc skill list          # source and pinned commit are now recorded
orc skill disable caveman   # content stays in your data repo
```
