---
name: claude-orchestrator
description: Use when the user asks about their own token/usage stats across projects, wants to search or cross-reference their Claude Code memory, asks what Claude Code skills they have installed or wants to adopt/enable/disable one, asks to switch which account they're using, wants a status/dashboard view of their setup, or wants to sync that setup across machines. Only relevant if the `orc` CLI (claude-orchestrator) is actually installed — check before using it.
version: 0.1.0
---

# orc (claude-orchestrator)

`orc` is a separate, real CLI tool (not part of Claude Code itself) that
some users install to manage a Claude Code setup spanning multiple
accounts and machines: memory search, a skills registry, real token-usage
reporting read from Claude Code's own session transcripts, an agent-run
log, and git-based sync of their private data.

## Before using it

Check it's actually installed and has data before assuming any of this
works — this skill being enabled does not mean the CLI is present:

```bash
command -v orc
```

If that fails, tell the user `orc` isn't installed rather than guessing —
point them at https://github.com/Pranav-error/claude-orchestrator
(`pip install claude-orc`, or `pipx install claude-orc`)
and don't fabricate output.

## When to reach for it

- "how much have I used today/this week/on project X" → `orc usage report --by day` (or `--by project`, `--by model`, `--by identity`)
- "search my memory/notes for X" → `orc memory search "X"`
- "what's related to X" / "what links to X" → `orc memory links "X"`
- "what skills do I have" → `orc skill list`
- "adopt/enable/disable skill X" → `orc skill adopt "X"` / `orc skill enable "X"` / `orc skill disable "X"`
- "switch to my other account" / "I'm on a client's account now" → `orc identity set "<label>"`
- "give me a status/overview/dashboard" → `orc dashboard --color always`
- "sync my setup" → `orc sync status`, then `push`/`pull` as appropriate

## How to run it

Every one of these is a single, non-interactive command — run with Bash,
don't try to drive the interactive menu (`orc` with no arguments) since
that waits on keyboard input a tool call can't provide.

**Never retype colored/box-drawn output** (`orc dashboard`, mainly) into
your reply — a markdown code fence doesn't interpret ANSI color, so it
would show broken escape-code noise instead of the actual colors. Let the
Bash tool's own result panel be the visual; add only a short caption.

Always pass `--color always` on `orc dashboard` specifically, since your
Bash tool's output isn't a real terminal and `orc`'s auto-detection would
otherwise silently show plain text even though a real terminal gets full
color.

Full command reference: https://github.com/Pranav-error/claude-orchestrator/blob/main/USAGE.md
