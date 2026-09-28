---
description: Run claude-orchestrator (memory/skills/usage/identity/sync). Usage examples: /orc, /orc status, /orc search gsoc, /orc usage, /orc identity friend-x, /orc skills, /orc sync
---

`orc` (`~/Documents/GitHub/claude-orchestrator`) manages cross-account/cross-machine memory, skills, usage, and sync. Its interactive menu can't run in a chat turn, so map the argument text below onto the matching flag command, run it once with Bash, and add only a short caption — don't over-narrate.

User's argument text: $ARGUMENTS

Map case-insensitively, first word decides:

- empty, or "status" → `orc status` (identity + today's usage + model, one call). Don't also run `orc identity show`/`orc usage report` on top of it, and don't re-summarize the output.
- "search <query>" or "find <query>" → `orc memory search "<query>"`
- "links <name>" → `orc memory links "<name>"`
- "link <from> <to>" → `orc memory link "<from>" "<to>"`
- "suggest <name>" or "related to <name>" → `orc memory suggest "<name>"`
- "related" alone → `orc memory related`
- "browse" → don't run via Bash (no tty, it'd hang) — tell the user to run `orc memory browse` themselves.
- "sync-memory" or "sync memory" → `orc memory sync`
- "usage" [optional: "by day|project|model|identity"] → `orc usage report --by <that, default day>`
- "identity" alone → `orc identity show`
- "identity <label>" / "switch <label>" / "account <label>" → `orc identity set "<label>"`
- "identity log" or "accounts" → `orc identity log`
- "skills" or "skill list" → `orc skill list`
- "adopt <name> [source]" → `orc skill adopt "<name>"` (add `--source "<source>"` if given)
- "enable <name>" → `orc skill enable "<name>"`
- "disable <name>" → `orc skill disable "<name>"`
- "log <task> <success|failed|partial> [notes...]" → `orc agent log "<task>" <outcome> --notes "<notes>"`
- "runs" or "agent log" alone → `orc agent list`
- "sync" or "sync status" → `orc sync status`
- "push" or "sync push" → `orc sync push`
- "pull" or "sync pull" → `orc sync pull`
- "dashboard" or "dash" → `orc dashboard --color always` (see note below)
- "config" / "preferences" / "theme <name>" / "set <key> <value>" → `orc config show`, or `orc config set <key> <value>` if a key/value was named (keys: theme, icons, usage_days, color; themes: amber, ocean, sunset, mono)
- "update" → `orc update` (updates the tool's own code checkout, not the data repo — that's `sync`)
- anything else → don't guess destructively; show the options above and ask which one was meant.

Run via Bash from any directory (`orc` is on PATH; fall back to `~/Documents/GitHub/claude-orchestrator/bin/orc <args>` if not).

Never re-print or code-fence the raw output — a fence doesn't render ANSI, so colored/box-drawn output would show as broken escape codes instead. Let the Bash result panel be the visual; add one short caption line.

Pass `--color always` on `dashboard` specifically: Bash's stdout isn't a real tty, so `orc` would otherwise silently fall back to plain text there even though a real terminal shows full color.
