---
description: Run claude-orchestrator (memory/skills/usage/identity/sync). Usage examples: /orc, /orc status, /orc search gsoc, /orc usage, /orc identity friend-x, /orc skills, /orc sync
---

`orc` is a personal tool (`~/Documents/GitHub/claude-orchestrator`) for cross-account/cross-machine memory, skills, usage tracking, and sync. It has an interactive menu, but that menu can't be driven from inside a chat turn — so this command maps what the user typed after `/orc` onto the equivalent one-shot flag command and runs it with Bash, then reports the result plainly (don't over-narrate).

User's argument text: $ARGUMENTS

Map it like this (case-insensitively, first word decides):

- empty, or "status" → `orc identity show` AND a one-day `orc usage report --by day` (today's row only), summarized together as a quick status.
- "search <query>" or "find <query>" → `orc memory search "<query>"`
- "links <name>" → `orc memory links "<name>"`
- "link <from> <to>" → `orc memory link "<from>" "<to>"`
- "sync-memory" or "sync memory" → `orc memory sync`
- "usage" [optional: "by day|project|model|identity"] → `orc usage report --by <that, default day>`
- "identity" with no more words → `orc identity show`
- "identity <label>" or "switch <label>" or "account <label>" → `orc identity set "<label>"`
- "identity log" or "accounts" → `orc identity log`
- "skills" or "skill list" → `orc skill list`
- "adopt <name> [source]" → `orc skill adopt "<name>"` (add `--source "<source>"` if given)
- "enable <name>" → `orc skill enable "<name>"`
- "disable <name>" → `orc skill disable "<name>"`
- "log <task> <success|failed|partial> [notes...]" → `orc agent log "<task>" <outcome> --notes "<notes>"`
- "runs" or "agent log" (no more words) → `orc agent list`
- "sync" or "sync status" → `orc sync status`
- "push" or "sync push" → `orc sync push`
- "pull" or "sync pull" → `orc sync pull`
- "dashboard" or "dash" → `orc dashboard --color always` (see note below on why `--color always`)
- "config" or "preferences" or "theme <name>" or "set <key> <value>" → `orc config show`, or `orc config set <key> <value>` if the user named a key/value (valid keys: theme, icons, usage_days, color; themes: amber, ocean, sunset, mono)
- anything else / unclear → don't guess destructively; show the user the option list above and ask which one they meant.

Run the mapped command with Bash from any directory (it's a full path or already on PATH as `orc`). If `orc` isn't found on PATH, fall back to running it via `~/Documents/GitHub/claude-orchestrator/bin/orc <args>` directly.

**Never re-print the raw output yourself, and never wrap it in a fenced code block.** The Bash tool's own result panel is the correct place for it — Claude Code renders that panel's ANSI color and box-drawing characters correctly, but a markdown code fence in your reply does not interpret ANSI at all, so retyping colored output into one would show broken escape-code noise (`\033[38;5;208m` etc.) instead of the colors. Let the tool result stand as the visual; your job is a short one- or two-line caption underneath it (what it shows, anything notable) — not a restatement of its contents, and never a substitute for it.

**Always pass `--color always` on the dashboard command specifically.** Bash tool output isn't a real tty, so `orc`'s auto-detection would otherwise silently fall back to plain text here even though the same command shows full color in a real terminal. `--color always` (or `orc config set color always` to make it the persistent default) makes `/orc dashboard` and `!orc dashboard` render identically to running it directly in a terminal — but only inside the tool result panel itself, not in anything you retype.
