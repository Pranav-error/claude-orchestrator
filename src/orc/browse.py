"""`orc memory browse` -- an interactive terminal browser over the memory
store: a type-to-search list on the left, the selected file's rendered
content on the right.

curses (stdlib), not textual/rich/urwid: this repo stays dependency-free,
and a filtered list plus a text pane is well within what curses does on
its own. Needs a real terminal -- there is no tty for curses to attach to
when run through Claude's Bash tool, so `commands/orc.md` and the skill
both point people at running this directly instead.
"""

import curses
import os
import subprocess
import textwrap
from datetime import datetime

from . import memory

QUIT_KEYS = (27,)  # Esc. Not 'q' -- that has to be typeable into the search box.
ENTER_KEYS = (curses.KEY_ENTER, 10, 13)
BACKSPACE_KEYS = (curses.KEY_BACKSPACE, 127, 8)
LINK_MODE_KEY = 12  # Ctrl-L. A mnemonic control char, again so plain 'l' stays typeable.


def _matches(entries: list[dict], query: str) -> list[dict]:
    """Substring filter across name/description/type/stem, name hits
    ranked above description/type/stem hits. Reuses no code from
    memory.search() on purpose: that scores against file bodies too,
    which for an interactively-typed, per-keystroke filter would make
    the ranking jump around in a way that's hard to type against."""
    if not query:
        return entries
    q = query.lower()
    scored = []
    for e in entries:
        name_hit = q in e["name"].lower()
        other_hit = q in f"{e['description']} {e['type']} {e['stem']}".lower()
        if not (name_hit or other_hit):
            continue
        scored.append((0 if name_hit else 1, e["name"].lower(), e))
    scored.sort(key=lambda t: t[:2])
    return [e for *_ , e in scored]


def _clip(s: str, width: int) -> str:
    return s[: max(0, width)]


def _safe_addstr(stdscr, y: int, x: int, s: str, attr=0):
    height, width = stdscr.getmaxyx()
    if y < 0 or y >= height or x >= width:
        return
    try:
        stdscr.addstr(y, x, _clip(s, width - x), attr)
    except curses.error:
        pass  # bottom-right cell of the terminal; curses refuses the last column/row, harmless


def _type_counts(entries: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for e in entries:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    return counts


def _draw_landing(stdscr, entries: list[dict], query: str, message: str):
    height, _width = stdscr.getmaxyx()
    _safe_addstr(stdscr, 0, 0, "orc memory browse", curses.A_BOLD)
    _safe_addstr(stdscr, 2, 0, f"search: {query}_")

    counts = _type_counts(entries)
    _safe_addstr(stdscr, 4, 2, "  ".join(f"{t} {n}" for t, n in sorted(counts.items())), curses.A_DIM)

    recent = sorted(entries, key=lambda e: -e["mtime"])[:8]
    _safe_addstr(stdscr, 6, 2, "recent:", curses.A_DIM)
    for i, e in enumerate(recent):
        age = datetime.now().timestamp() - e["mtime"]
        age_str = f"{int(age // 86400)}d ago" if age > 86400 else f"{int(age // 3600)}h ago"
        _safe_addstr(stdscr, 7 + i, 4, f"{e['name']:<40} {age_str:>8}")

    footer_row = height - 1
    footer = "type to search  ·  Esc quit"
    if message:
        footer = f"{message}  ·  {footer}"
    _safe_addstr(stdscr, footer_row, 0, footer, curses.A_DIM)


def _preview_lines(entry: dict, graph: dict, suggestions: list[dict], project_labels: dict, width: int) -> list[str]:
    lines: list[str] = [f"# {entry['name']}", ""]
    for line in entry["body"].strip().splitlines():
        lines.extend(textwrap.wrap(line, width) or [""])
    lines.append("")

    data = graph.get(entry["stem"], {"outgoing": [], "incoming": []})
    if data["outgoing"] or data["incoming"]:
        lines.append("Linked:")
        for other_stem in data["outgoing"]:
            lines.append(f"  -> {graph[other_stem]['name']}")
        for other_stem in data["incoming"]:
            lines.append(f"  <- {graph[other_stem]['name']}")
        lines.append("")

    if suggestions:
        lines.append("Related, not linked (^L to link):")
        for s in suggestions:
            label = project_labels.get(s["source_project"], "")
            proj = f", {label}" if label else ""
            lines.append(f"  {s['score']:>3}%  {s['name']}{proj}")

    return lines


def _draw_list(stdscr, filtered: list[dict], selected: int, query: str, preview_lines: list[str], message: str):
    height, width = stdscr.getmaxyx()
    list_w = min(38, width // 3)
    _safe_addstr(stdscr, 0, 0, f"search: {query}_    {len(filtered)} matches")

    for row in range(1, height - 1):
        idx = row - 1
        if idx < len(filtered):
            e = filtered[idx]
            marker = "▸ " if idx == selected else "  "
            label = f"{marker}{e['name']}"[: list_w - 1]
            attr = curses.A_REVERSE if idx == selected else 0
            _safe_addstr(stdscr, row, 0, label.ljust(list_w - 1), attr)
        _safe_addstr(stdscr, row, list_w, "│")
        line_idx = idx if idx < len(preview_lines) else None
        if line_idx is not None:
            _safe_addstr(stdscr, row, list_w + 2, preview_lines[line_idx])

    footer = "↑↓ move  · type to search  · ^L link to…  · ⏎ open  · Esc quit"
    if message:
        footer = f"{message}  ·  {footer}"
    _safe_addstr(stdscr, height - 1, 0, footer, curses.A_DIM)


def _draw_link_picker(stdscr, from_name: str, candidates: list[dict], selected: int, query: str, project_labels: dict):
    height, _width = stdscr.getmaxyx()
    _safe_addstr(stdscr, 0, 0, f"link '{from_name}' to: {query}_", curses.A_BOLD)
    for row in range(1, height - 1):
        idx = row - 1
        if idx >= len(candidates):
            continue
        e = candidates[idx]
        marker = "▸ " if idx == selected else "  "
        label = project_labels.get(e["source_project"], "")
        proj = f"  ({label})" if label else ""
        attr = curses.A_REVERSE if idx == selected else 0
        _safe_addstr(stdscr, row, 0, f"{marker}{e['name']}{proj}", attr)
    _safe_addstr(stdscr, height - 1, 0, "↑↓ move  · type to search  · ⏎ confirm  · Esc cancel", curses.A_DIM)


def _open_in_editor(stdscr, path):
    editor = os.environ.get("EDITOR", "vi")
    curses.def_prog_mode()
    curses.endwin()
    try:
        subprocess.call([editor, str(path)])
    finally:
        stdscr.refresh()
        curses.reset_prog_mode()


def run(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()

    entries = memory.list_all()
    graph = memory.build_link_graph()
    # Precomputed once: readable_project() reads transcript files, so
    # calling it per-row on every redraw (as the naive version did) would
    # mean re-reading disk on every keystroke.
    project_labels = {p: memory.readable_project(p) for p in {e["source_project"] for e in entries if e["source_project"]}}
    mode = "list"
    query = ""
    selected = 0
    link_query = ""
    link_selected = 0
    link_from = None
    message = ""

    while True:
        stdscr.erase()
        _height, width = stdscr.getmaxyx()

        if mode == "list":
            filtered = _matches(entries, query)
            selected = min(selected, max(0, len(filtered) - 1))
            if not query:
                _draw_landing(stdscr, entries, query, message)
            else:
                preview_lines = []
                if filtered:
                    current = filtered[selected]
                    try:
                        suggestions = memory.suggest_related(current["stem"], top_n=3, entries=entries, graph=graph)
                    except ValueError:
                        suggestions = []
                    preview_lines = _preview_lines(current, graph, suggestions, project_labels, max(10, width - min(38, width // 3) - 3))
                _draw_list(stdscr, filtered, selected, query, preview_lines, message)
        else:
            candidates = _matches([e for e in entries if e["stem"] != link_from], link_query)
            link_selected = min(link_selected, max(0, len(candidates) - 1))
            from_entry = next((e for e in entries if e["stem"] == link_from), None)
            _draw_link_picker(stdscr, from_entry["name"] if from_entry else link_from, candidates, link_selected, link_query, project_labels)

        stdscr.refresh()
        message = ""
        ch = stdscr.getch()

        if mode == "list":
            filtered = _matches(entries, query)
            if ch in QUIT_KEYS:
                return
            elif ch in ENTER_KEYS:
                if filtered:
                    _open_in_editor(stdscr, filtered[selected]["path"])
            elif ch == LINK_MODE_KEY:
                if filtered:
                    mode = "link"
                    link_from = filtered[selected]["stem"]
                    link_query, link_selected = "", 0
            elif ch in BACKSPACE_KEYS:
                query, selected = query[:-1], 0
            elif ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(max(0, len(filtered) - 1), selected + 1)
            elif 32 <= ch <= 126:
                query, selected = query + chr(ch), 0
        else:
            candidates = _matches([e for e in entries if e["stem"] != link_from], link_query)
            if ch in QUIT_KEYS:
                mode = "list"
            elif ch in ENTER_KEYS:
                if candidates:
                    result = memory.add_link(link_from, candidates[link_selected]["stem"])
                    message = "already linked" if result["already_linked"] else f"linked -> {candidates[link_selected]['name']}"
                    graph = memory.build_link_graph()  # refresh so the preview's Linked section picks it up
                mode = "list"
            elif ch in BACKSPACE_KEYS:
                link_query, link_selected = link_query[:-1], 0
            elif ch == curses.KEY_UP:
                link_selected = max(0, link_selected - 1)
            elif ch == curses.KEY_DOWN:
                link_selected = min(max(0, len(candidates) - 1), link_selected + 1)
            elif 32 <= ch <= 126:
                link_query, link_selected = link_query + chr(ch), 0


def main():
    if not os.isatty(0):
        print("orc memory browse needs a real terminal -- run it directly, not through a script or Claude's Bash tool")
        return
    curses.wrapper(run)
