# Claude Code ecosystem — skills worth adopting

A survey of widely-adopted Claude Code skills and plugins installable from
GitHub, as candidates for `orc skill adopt` / `orc skill install`.

**Inclusion bar:** >2,000 GitHub stars, actively maintained, and installable
as a Claude Code skill/plugin (not just an article or a tutorial repo).
Star/fork counts were read from the GitHub API on **2026-09-21**, not from
blog posts — several write-ups quote numbers that are months stale. This list
was widened on the same date via GitHub topic search (`topic:claude-code`,
`topic:claude-skills`, `topic:claude-code-plugin`), not just curated
awesome-lists, which is why it's larger than the first pass. A number of
high-star hits were deliberately left out — see *Filtered out* at the bottom
— because a `claude-code` topic tag alone doesn't mean the repo is actually a
Claude Code skill/plugin.

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
| [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | 94.4k | 8.3k | Apache-2.0 | Persistent cross-session context/memory specifically for Claude Code. The closest thing to a direct competitor for `orc`'s core memory feature — worth reading before extending `orc memory` further. |
| [Egonex-AI/Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) | 83.5k | 7.0k | MIT | Turns any codebase into an interactive knowledge graph. Same space as `graphify`, different implementation — worth comparing if `graphify` output ever falls short. |

## Domain-specific skill packs

Larger, opinionated skill collections — install the whole pack, not one file.

| Skill | Stars | Forks | License | What it does |
|---|---:|---:|---|---|
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 129.5k | 13.8k | MIT | Design-intelligence skill for UI/UX work across frameworks — layout, spacing, and visual-hierarchy judgment baked into the skill rather than left to prompting. |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 98.1k | 10.3k | MIT | Production-grade engineering skills (performance, testing, code review) from a well-known web-perf engineer. |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 89.0k | 6.1k | MIT | Pushes the model away from generic/"AI slop" output toward more deliberate design and prose choices — same instinct this repo's own `artifact-design` skill encodes, from a different angle. |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 45.9k | 4.2k | MIT | Turns a general coding agent into a science-focused one — literature search, data analysis, figure generation. Only relevant if that's your domain. |
| [wshobson/agents](https://github.com/wshobson/agents) | 39.8k | 4.2k | MIT | A plugin marketplace of subagents spanning Claude Code, Codex, Cursor, and other harnesses — useful if you also drive non-Claude tools and want one agent-definition source. |
| [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) | 49.7k | 2.9k | MIT | Forces the model to lead with the answer instead of burying it in preamble. Small, single-purpose, easy to audit. |
| [titanwings/distilly](https://github.com/titanwings/distilly) | 24.9k | 2.2k | MIT | Distills how a specific person/team thinks into a reusable skill, from examples of their own work. |
| [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master) | 13.5k | 1.6k | MIT | A Claude skill that writes prompts for *other* AI tools, without spending tokens/credits on the target tool itself. |
| [revfactory/harness](https://github.com/revfactory/harness) | 9.0k | 1.3k | Apache-2.0 | Meta-skill: designs a domain-specific team of subagents and generates their definitions, rather than being a fixed skill itself. |

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
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 34.7k | 3.7k | MIT-licensed, 1000+ skills from official dev teams and the community. |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 26.2k | 3.7k | 380+ skills spanning engineering and non-engineering domains. |
| [rohitg00/awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit) | 2.6k | 964 | Agents, commands, hooks, MCP configs. |

## Filtered out (high stars, not actually a Claude Code skill/plugin)

The `claude-code`/`claude-skills` GitHub topics are noisy — plenty of
unrelated tools tag themselves to ride search traffic. These cleared
2,000+ stars in the same search but were left off the tables above because
they're general agent frameworks, desktop apps, or CLIs rather than
something you `orc skill install`:

- **farion1231/cc-switch** (134.0k) — a desktop app for switching between
  Claude Code/Codex/OpenCode accounts. Solves a problem adjacent to `orc
  identity`, not a skill — worth knowing about, not worth listing as one.
- **DietrichGebert/ponytail** (143.6k), **ruvnet/ruflo** (73.0k),
  **stablyai/orca** (74.5k), **shareAI-lab/learn-claude-code** (77.4k) —
  general agent-harness/orchestration frameworks, not skills or plugins you
  install into an existing Claude Code setup.
- **rtk-ai/rtk** (81.3k), **headroomlabs-ai/headroom** (73.4k) — token/output
  compression CLIs and proxies; useful adjacent tools, but not Claude Code
  skills.
- **affaan-m/ECC** (264.6k), **NousResearch/hermes-agent** (247.7k) — very
  high star counts but vague, non-specific descriptions with nothing
  concretely tying them to Claude Code as an installable skill; excluded
  pending a closer look.
- **feder-cr/AIHawk** (31.6k), **nanocoai/nanoclaw** (30.8k),
  **career-ops-hq/career-ops** (72.3k), **diegosouzapw/OmniRoute** (68.9k) —
  legitimate projects, but domain tools (job search, browser automation, a
  model-routing gateway) that happen to carry a `claude-code` tag, not
  Claude Code skills themselves.

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
