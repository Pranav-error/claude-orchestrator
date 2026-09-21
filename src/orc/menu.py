"""The `orc` menu: running `orc` with no arguments drops into this instead
of printing argparse usage. Every option here just calls the same functions
the `orc <command> <subcommand>` CLI uses — this is a friendlier front door,
not a second implementation.
"""

from . import agentlog, banner, dashboard, ecosystem, identity, memory, settings, skills, sync, usage
from .dashboard import BOLD, DIM, RESET, _resolve_color, _term_width, _visible_len


def _pause():
    input("\n[enter to continue] ")


def _header(title: str):
    print(f"\n== {title} ==\n")


def show_status():
    _header("Status")
    cur = identity.current()
    print(f"Account:  {cur['label'] if cur else '(not set)'}")
    print(f"Machine:  {cur['machine'] if cur else '-'}")

    today = usage.report(group_by="day")
    todays_key = sorted(today.keys())[-1] if today else None
    if todays_key:
        b = today[todays_key]
        print(f"Usage today ({todays_key}): {b['input']:,} in / {b['output']:,} out / {b['messages']} messages")

    skill_rows = skills.list_skills()
    enabled = sum(1 for r in skill_rows if r["enabled"])
    print(f"Skills:   {enabled} enabled, {len(skill_rows)} tracked")

    mem_count = len(list(memory.config.MEMORY_DIR.rglob("*.md"))) if memory.config.MEMORY_DIR.exists() else 0
    print(f"Memory:   {mem_count} files mirrored")

    recent = agentlog.list_runs()[-3:]
    if recent:
        print("\nRecent agent runs:")
        for r in recent:
            print(f"  [{r['outcome']}] {r['task']}")


def switch_identity():
    _header("Switch account")
    cur = identity.current()
    print(f"Currently: {cur['label'] if cur else '(not set)'}")
    label = input("New account label (e.g. mine / friend-x / client-y): ").strip()
    if not label:
        print("cancelled")
        return
    entry = identity.set_identity(label)
    print(f"switched to {entry['label']}")


def search_memory():
    _header("Search memory")
    query = input("Search for: ").strip()
    if not query:
        return
    hits = memory.search(query)
    if not hits:
        print("no matches")
        return
    for h in hits:
        print(f"\n{h['name']}  ({h['path']})")
        if h["description"]:
            print(f"  {h['description']}")


def memory_here():
    _header("Memories from this directory")
    hits = memory.for_project()
    if not hits:
        print("no memories recorded from this directory")
        return
    for h in hits:
        print(f"  [{h['type']}] {h['name']}")
        if h["description"]:
            print(f"    {h['description'][:100]}")


def memory_graph():
    print("\n" + dashboard.render_memory_graph())


def browse_ecosystem():
    print("\n" + ecosystem.text())


def memory_links():
    _header("Memory links")
    query = input("Show links for: ").strip()
    if not query:
        return
    try:
        data = memory.links_for(query)
    except memory.AmbiguousMemoryQuery as e:
        shown = e.matches[:15]
        print(f"\n{len(e.matches)} memories match {query!r} — pick one:")
        for i, m in enumerate(shown, 1):
            print(f"  {i}. {m}")
        if len(e.matches) > len(shown):
            print(f"  ... and {len(e.matches) - len(shown)} more — try a more specific query")
        choice = input("\n> ").strip()
        try:
            picked = shown[int(choice) - 1]
        except (ValueError, IndexError):
            print("cancelled")
            return
        data = memory.links_for(picked)  # exact stem always resolves uniquely
    except ValueError as e:
        print(f"error: {e}")
        return
    print(f"\n{data['name']}")
    print(f"\nlinks to ({len(data['outgoing'])}):")
    for l in data["outgoing"]:
        print(f"  -> {l['name']}")
    print(f"\nlinked from ({len(data['incoming'])}):")
    for l in data["incoming"]:
        print(f"  <- {l['name']}")

    if input("\nAdd a new link from here? (y/n) ").strip().lower() == "y":
        to_query = input("Link to: ").strip()
        if to_query:
            try:
                result = memory.add_link(query, to_query)
                print("already linked" if result["already_linked"] else f"linked -> {result['to']}")
            except ValueError as e:
                print(f"error: {e}")


def sync_memory():
    _header("Sync memory")
    result = memory.sync()
    print(f"{len(result['imported'])} mirrored, {len(result['skipped_duplicate'])} already present")


def usage_report():
    _header("Usage report")
    print("Group by: 1) day  2) project  3) model  4) identity")
    choice = input("> ").strip()
    group_by = {"1": "day", "2": "project", "3": "model", "4": "identity"}.get(choice, "day")
    data = usage.report(group_by=group_by)
    if not data:
        print("no usage data found")
        return
    for key, b in data.items():
        print(f"{key:<28} in={b['input']:>10}  out={b['output']:>10}  msgs={b['messages']}")


def manage_skills():
    _header("Skills")
    rows = skills.list_skills()
    for i, r in enumerate(rows, 1):
        status = "enabled" if r["enabled"] else ("disabled" if r["managed"] else "unmanaged")
        print(f"{i}. {r['name']:<24} [{status}]")

    print("\na) adopt an unmanaged skill   e) enable   d) disable   (enter to go back)")
    action = input("> ").strip().lower()
    if not action:
        return
    name = input("skill name: ").strip()
    if not name:
        return
    try:
        if action == "a":
            source = input("source (URL, or leave blank for 'unknown'): ").strip() or "unknown"
            skills.adopt(name, source=source)
            print(f"adopted {name}")
        elif action == "e":
            skills.enable(name)
            print(f"enabled {name}")
        elif action == "d":
            skills.disable(name)
            print(f"disabled {name}")
        else:
            print("unrecognized action")
    except ValueError as e:
        print(f"error: {e}")


def sync_repo():
    _header("Sync (cross-machine)")
    s = sync.status()
    dirty = "dirty" if s["dirty"] else "clean"
    print(f"branch={s['branch']}  ahead={s['ahead']}  behind={s['behind']}  {dirty}")
    print("\n1) pull  2) push")
    choice = input("> ").strip()
    if choice == "1":
        result = sync.pull()
    elif choice == "2":
        result = sync.push()
    else:
        return
    print(("ok: " if result["ok"] else "failed: ") + result["detail"])


def open_dashboard():
    print("\n" + dashboard.render_terminal())


_VALUE_HINTS = {
    "theme": lambda: ", ".join(settings.THEMES),
    "color": lambda: "auto, always, never",
    "icons": lambda: "true, false",
    "banner": lambda: "true, false",
    "usage_days": lambda: "a number, e.g. 7",
}


def preferences():
    _header("Preferences")
    current = settings.load()
    for k, v in current.items():
        print(f"  {k} = {v}")
    print(f"\nWhich to change? ({', '.join(settings.DEFAULTS)}, or enter to skip)")
    key = input("> ").strip()
    if not key:
        return
    if key not in settings.DEFAULTS:
        print(f"error: unknown setting {key!r} — valid keys: {', '.join(settings.DEFAULTS)}")
        return
    hint = _VALUE_HINTS[key]()
    value = input(f"new value for {key} ({hint}): ").strip()
    try:
        settings.set_value(key, value)
        print("saved")
    except ValueError as e:
        print(f"error: {e}")


def log_agent_run():
    _header("Log an agent run")
    task = input("What ran: ").strip()
    if not task:
        return
    print("Outcome: 1) success  2) failed  3) partial")
    outcome = {"1": "success", "2": "failed", "3": "partial"}.get(input("> ").strip(), "success")
    notes = input("Notes (optional): ").strip()
    agentlog.log_run(task, outcome, notes=notes)
    print("logged")


MENU = [
    ("Status at a glance", show_status),
    ("Dashboard", open_dashboard),
    ("Switch account", switch_identity),
    ("Search memory", search_memory),
    ("Show/add memory links", memory_links),
    ("Memory graph (most-connected)", memory_graph),
    ("Memories from this directory", memory_here),
    ("Sync memory", sync_memory),
    ("Manage skills", manage_skills),
    ("Browse third-party skills (ecosystem)", browse_ecosystem),
    ("Usage report", usage_report),
    ("Log an agent run", log_agent_run),
    ("Sync (push/pull to other machines)", sync_repo),
    ("Preferences (theme, icons, colors)", preferences),
]


def render_menu_screen(color: bool = None) -> str:
    """Pure — no input() — so it's testable like dashboard.render_terminal().
    Boxed header (identity + sync state, same language as the dashboard)
    plus a compact numbered menu — tried grouping into labeled sections
    with blank lines between them, but for 11 items that just made the
    whole thing tall without earning it, so back to a flat list."""
    color = _resolve_color(color)

    def c(code, text):
        return f"{code}{text}{RESET}" if (color and code) else text

    width = _term_width()
    theme = settings.theme()
    prompt_color = theme["prompt"]

    who = identity.current()
    identity_label = who["label"] if who else "(not set)"
    machine = who["machine"] if who else "-"
    s = sync.status()
    sync_bit = f"{s['branch']} ({'dirty' if s['dirty'] else 'clean'})"

    def pad(content: str, inner_width: int) -> str:
        return content + " " * max(0, inner_width - _visible_len(content))

    title = c(BOLD, "claude-orchestrator")
    meta = f"{c(prompt_color, '❯')} {identity_label} {c(DIM, 'on')} {machine}   {c(DIM, '·')}   {sync_bit}"
    box_w = width - 2

    lines = [
        c(DIM, "╭" + "─" * box_w + "╮"),
        c(DIM, "│ ") + pad(title, box_w - 2) + c(DIM, " │"),
        c(DIM, "│ ") + pad(meta, box_w - 2) + c(DIM, " │"),
        c(DIM, "╰" + "─" * box_w + "╯"),
        "",
    ]

    for n, (label, _) in enumerate(MENU, 1):
        lines.append(f"  {c(prompt_color, str(n))}  {label}")
    lines.append(f"  {c(DIM, '0')}  Quit")

    return "\n".join(lines)


QUIT = object()  # sentinel distinct from any real menu index


def resolve_choice(text: str):
    """Pure — no I/O — so it's testable without mocking input(). Returns
    (index, None) on a clean match, (QUIT, None) to quit, (None, None) for
    no match at all, or (None, [labels]) when a typed name matches more
    than one item and needs a more specific word.

    Accepts a number (the original interface, unchanged) OR any substring
    of an item's label, case-insensitive — typing "search" or "dash" is
    faster than scanning the list for which digit that was."""
    text = text.strip()
    if not text:
        return None, None
    if text == "0" or text.lower() in ("q", "quit", "exit"):
        return QUIT, None
    if text.isdigit():
        n = int(text)
        if 1 <= n <= len(MENU):
            return n - 1, None
        return None, None

    text_l = text.lower()
    exact = [i for i, (label, _) in enumerate(MENU) if label.lower() == text_l]
    if exact:
        return exact[0], None
    matches = [i for i, (label, _) in enumerate(MENU) if text_l in label.lower()]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, [MENU[i][0] for i in matches]
    return None, None


def run():
    if banner.enabled():
        banner.render_animated()

    while True:
        print("\n" + render_menu_screen())

        choice = input("\n> ").strip()
        idx, ambiguous = resolve_choice(choice)
        if idx is QUIT:
            break
        if idx is None:
            if ambiguous:
                print(f"matches more than one: {', '.join(ambiguous)} — try a more specific word")
            else:
                print("pick a number, or type part of an option's name")
            continue

        _, action = MENU[idx]
        try:
            action()
        except (KeyboardInterrupt, EOFError):
            print()
            continue
        _pause()
