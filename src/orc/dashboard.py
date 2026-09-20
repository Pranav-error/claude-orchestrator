"""Phase 5: a read-only snapshot over everything else — memory, skills,
usage, identity, sync state, recent agent runs. Renders directly in the
terminal (ANSI colors, no browser, no server) since that's where this
tool actually gets used. An HTML export is still available via
`orc dashboard --html` for anyone who wants a shareable file, but the
terminal view is the default."""

import html as html_escape
import os
import shutil
import sys
import webbrowser
from datetime import datetime, timezone

from . import agentlog, config, identity, settings as settings_mod, skills, sync, usage

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def _resolve_color(explicit) -> bool:
    """Precedence: explicit function arg > `orc config set color always|never`
    > auto-detect. 'always' is what lets `!orc dashboard` inside a Claude
    Code chat render in color even though its stdout isn't a real tty."""
    if explicit is not None:
        return explicit
    mode = settings_mod.get("color")
    if mode == "always":
        return True
    if mode == "never":
        return False
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _term_width(default: int = 78) -> int:
    return max(60, min(96, shutil.get_terminal_size((default, 24)).columns))


def _visible_len(s: str) -> int:
    """Length ignoring ANSI escape sequences, for padding math."""
    out, in_escape = 0, False
    for ch in s:
        if ch == "\033":
            in_escape = True
        elif in_escape and ch == "m":
            in_escape = False
        elif not in_escape:
            out += 1
    return out


def _snapshot(usage_days: int):
    who = identity.current()
    s = sync.status()
    by_day = usage.report(group_by="day")
    days = sorted(by_day.items())[-usage_days:]
    skill_rows = skills.list_skills()
    mem_count = len(list(config.MEMORY_DIR.rglob("*.md"))) if config.MEMORY_DIR.exists() else 0
    recent_runs = list(reversed(agentlog.list_runs()[-10:]))
    return who, s, days, skill_rows, mem_count, recent_runs


def render_terminal(color: bool = None, theme_name: str = None, usage_days: int = None, icons: bool = None) -> str:
    color = _resolve_color(color)
    th = settings_mod.theme(theme_name)
    usage_days = usage_days if usage_days is not None else settings_mod.get("usage_days")
    icons = settings_mod.get("icons") if icons is None else icons

    def c(code, text):
        return f"{code}{text}{RESET}" if (color and code) else text

    gradient = th["gradient"]

    def grad(ratio: float) -> str:
        idx = min(len(gradient) - 1, int(ratio * len(gradient)))
        code = gradient[idx]
        return f"\033[38;5;{code}m" if code != "" else ""

    prompt_color, good, bad, warn = th["prompt"], th["good"], th["bad"], th["warn"]

    width = _term_width()
    who, s, days, skill_rows, mem_count, recent_runs = _snapshot(usage_days)
    max_output = max((b["output"] for _, b in days), default=1)
    enabled_count = sum(1 for r in skill_rows if r["enabled"])

    def rule(label: str) -> str:
        # "── LABEL ────────…" filling the rest of the terminal width, like a
        # section divider — cheap to read at a glance, doesn't rely on color.
        head = f"── {label} "
        fill = "─" * max(0, width - len(head))
        return c(DIM, head + fill)

    def pad_line(content: str, inner_width: int) -> str:
        gap = max(0, inner_width - _visible_len(content))
        return content + " " * gap

    lines = []

    # ── header box ─────────────────────────────────────────────
    identity_label = who["label"] if who else "(not set)"
    machine = who["machine"] if who else "-"
    dirty_word = "dirty" if s["dirty"] else "clean"
    dirty_color = warn if s["dirty"] else good
    title = c(BOLD, "claude-orchestrator")
    prompt_glyph = "❯ " if icons else "> "
    meta = (
        f"{c(prompt_color, prompt_glyph.strip())} {identity_label} {c(DIM, 'on')} {machine}"
        f"   {c(DIM, '·')}   {s['branch']} {c(dirty_color, f'({dirty_word})')}"
    )
    box_w = width - 2
    lines.append(c(DIM, "╭" + "─" * box_w + "╮"))
    lines.append(c(DIM, "│ ") + pad_line(title, box_w - 2) + c(DIM, " │"))
    lines.append(c(DIM, "│ ") + pad_line(meta, box_w - 2) + c(DIM, " │"))
    lines.append(c(DIM, "╰" + "─" * box_w + "╯"))
    lines.append("")

    # ── stat row ───────────────────────────────────────────────
    stats = [
        (str(mem_count), "memory files"),
        (f"{enabled_count}/{len(skill_rows)}", "skills enabled"),
        (f"{sum(b['messages'] for _, b in days):,}", f"messages ({usage_days}d)"),
        (str(len(agentlog.list_runs())), "agent runs"),
    ]
    n = len(stats)
    cell_w = max(10, (width - (n - 1) - n * 2) // n)  # 1 separator space + 2 border chars per cell
    top = " ".join(c(DIM, "┌" + "─" * cell_w + "┐") for _ in stats)
    val = " ".join(c(DIM, "│") + c(BOLD, v.center(cell_w)) + c(DIM, "│") for v, _ in stats)
    lab = " ".join(c(DIM, "│") + c(DIM, l.center(cell_w)) + c(DIM, "│") for _, l in stats)
    bot = " ".join(c(DIM, "└" + "─" * cell_w + "┘") for _ in stats)
    lines += [top, val, lab, bot, ""]

    # ── usage ──────────────────────────────────────────────────
    lines.append(rule(f"USAGE · last {len(days)} days"))
    bar_width = min(30, max(12, width - 46))
    for day, b in days:
        ratio = 0.0 if max_output <= 0 else b["output"] / max_output
        filled = 0 if b["output"] <= 0 else max(1, int(bar_width * ratio))
        bar = "█" * filled + "░" * (bar_width - filled)
        msgs_label = f"{b['messages']} msgs"
        lines.append(f"  {c(DIM, day)}  {c(grad(ratio), bar)}  {b['output']:>10,}  {c(DIM, msgs_label)}")
    lines.append("")

    # ── skills ─────────────────────────────────────────────────
    lines.append(rule("SKILLS"))
    name_w = max((len(r["name"]) for r in skill_rows), default=10)
    for r in skill_rows:
        if r["enabled"]:
            dot, status_plain, status_color = "●", "enabled", good
        elif r["managed"]:
            dot, status_plain, status_color = "○", "disabled", DIM
        else:
            dot, status_plain, status_color = "·", "unmanaged", DIM
        prefix = f"{dot} " if icons else ""
        status = c(status_color, f"{prefix}{status_plain:<10}")
        lines.append(f"  {r['name']:<{name_w}}  {status}  {c(DIM, str(r['source']))}")
    lines.append("")

    # ── recent runs ────────────────────────────────────────────
    lines.append(rule("RECENT AGENT RUNS"))
    if not recent_runs:
        lines.append(c(DIM, "  no runs logged yet"))
    for r in recent_runs:
        ts = r["timestamp"][:16].replace("T", " ")
        if r["outcome"] == "success":
            mark, outcome_color = "✓", good
        elif r["outcome"] == "failed":
            mark, outcome_color = "✗", bad
        else:
            mark, outcome_color = "◐", warn
        prefix = f"{mark} " if icons else ""
        outcome = c(outcome_color, f"{prefix}{r['outcome']:<9}")
        lines.append(f"  {c(DIM, ts)}  {outcome}  {r['task']}")
    lines.append("")
    lines.append(c(DIM, "orc config for themes/options  ·  orc --help for every command"))

    return "\n".join(lines)


def _bar_px(value: int, max_value: int, width: int = 200) -> int:
    if max_value <= 0:
        return 0
    return max(2, int(width * value / max_value))


def generate_html(out_path=None):
    out_path = out_path or (config.DATA_ROOT / "dashboard.html")
    who, s, days, skill_rows, mem_count, recent_runs = _snapshot(settings_mod.get("usage_days"))
    max_output = max((b["output"] for _, b in days), default=1)
    enabled_count = sum(1 for r in skill_rows if r["enabled"])

    day_rows = "\n".join(
        f"""<tr>
              <td class="mono">{html_escape.escape(day)}</td>
              <td class="bar-cell"><div class="bar" style="width:{_bar_px(b['output'], max_output)}px"></div>
                <span class="mono dim">{b['output']:,}</span></td>
              <td class="mono dim">{b['messages']}</td>
            </tr>"""
        for day, b in days
    )

    skill_rows_html = "\n".join(
        f"""<tr>
              <td>{html_escape.escape(r['name'])}</td>
              <td><span class="pill {'pill-good' if r['enabled'] else 'pill-dim'}">
                {'enabled' if r['enabled'] else ('disabled' if r['managed'] else 'unmanaged')}</span></td>
              <td class="mono dim">{html_escape.escape(str(r['source']))}</td>
            </tr>"""
        for r in skill_rows
    )

    run_rows = "\n".join(
        f"""<tr>
              <td class="mono dim">{html_escape.escape(r['timestamp'][:16].replace('T', ' '))}</td>
              <td><span class="pill {'pill-good' if r['outcome']=='success' else 'pill-bad' if r['outcome']=='failed' else 'pill-dim'}">{html_escape.escape(r['outcome'])}</span></td>
              <td>{html_escape.escape(r['task'])}</td>
            </tr>"""
        for r in recent_runs
    ) or '<tr><td colspan="3" class="dim">no runs logged yet</td></tr>'

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>claude-orchestrator dashboard</title>
<style>
  :root {{
    --bg:#f4f5f7; --surface:#fff; --border:#d7dbe3; --text:#1b2130;
    --dim:#5b6272; --accent:#a3660f; --good:#2f6b4f; --bad:#a3300f;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#14161c; --surface:#1b1e26; --border:#333748; --text:#e7e9f0;
      --dim:#a4aabb; --accent:#e0a94a; --good:#6fbf95; --bad:#e0714a; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.5; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .dim {{ color:var(--dim); }}
  .page {{ max-width:880px; margin:0 auto; padding:40px 24px 80px; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .meta {{ font-size:12.5px; color:var(--dim); margin-bottom:32px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin-bottom:36px; }}
  .stat {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; }}
  .stat .n {{ font-size:26px; font-weight:600; }}
  .stat .l {{ font-size:12px; color:var(--dim); text-transform:uppercase; letter-spacing:.04em; }}
  section {{ margin-bottom:36px; }}
  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.04em; color:var(--dim); margin-bottom:12px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
  td {{ padding:9px 14px; border-top:1px solid var(--border); font-size:13.5px; }}
  tr:first-child td {{ border-top:none; }}
  .bar-cell {{ display:flex; align-items:center; gap:10px; }}
  .bar {{ height:8px; background:var(--accent); border-radius:4px; }}
  .pill {{ font-size:11px; padding:2px 8px; border-radius:999px; }}
  .pill-good {{ background:rgba(47,107,79,.15); color:var(--good); }}
  .pill-bad {{ background:rgba(163,48,15,.15); color:var(--bad); }}
  .pill-dim {{ background:rgba(120,120,120,.15); color:var(--dim); }}
</style></head>
<body><div class="page">

  <h1>claude-orchestrator</h1>
  <div class="meta">generated {generated_at} &middot; identity:
    <b>{html_escape.escape(who['label']) if who else '(not set)'}</b> on
    <span class="mono">{html_escape.escape(who['machine']) if who else '-'}</span>
    &middot; branch {html_escape.escape(s['branch'])} ({'clean' if not s['dirty'] else 'dirty'})</div>

  <div class="grid">
    <div class="stat"><div class="n">{mem_count}</div><div class="l">memory files</div></div>
    <div class="stat"><div class="n">{enabled_count}/{len(skill_rows)}</div><div class="l">skills enabled</div></div>
    <div class="stat"><div class="n">{sum(b['messages'] for _, b in days)}</div><div class="l">messages, 14d</div></div>
    <div class="stat"><div class="n">{len(agentlog.list_runs())}</div><div class="l">agent runs logged</div></div>
  </div>

  <section>
    <h2>Usage — last {len(days)} days</h2>
    <table><tbody>{day_rows}</tbody></table>
  </section>

  <section>
    <h2>Skills</h2>
    <table><tbody>{skill_rows_html or '<tr><td class="dim">none found</td></tr>'}</tbody></table>
  </section>

  <section>
    <h2>Recent agent runs</h2>
    <table><tbody>{run_rows}</tbody></table>
  </section>

</div></body></html>"""

    out_path.write_text(doc)
    return out_path


def open_in_browser(path) -> None:
    webbrowser.open(f"file://{path}")
