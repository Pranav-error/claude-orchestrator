"""The `orc` menu: running `orc` with no arguments drops into this instead
of printing argparse usage. Every option here just calls the same functions
the `orc <command> <subcommand>` CLI uses — this is a friendlier front door,
not a second implementation.
"""

from . import agentlog, banner, dashboard, identity, memory, settings, skills, sync, usage


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


def memory_links():
    _header("Memory links")
    query = input("Show links for: ").strip()
    if not query:
        return
    try:
        data = memory.links_for(query)
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


def preferences():
    _header("Preferences")
    current = settings.load()
    for k, v in current.items():
        print(f"  {k} = {v}")
    print(f"\nthemes available: {', '.join(settings.THEMES)}")
    print("\nWhich to change? (theme / icons / usage_days / color, or enter to skip)")
    key = input("> ").strip()
    if not key:
        return
    value = input(f"new value for {key}: ").strip()
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
    ("Switch account", switch_identity),
    ("Search memory", search_memory),
    ("Show/add memory links", memory_links),
    ("Sync memory", sync_memory),
    ("Usage report", usage_report),
    ("Manage skills", manage_skills),
    ("Log an agent run", log_agent_run),
    ("Sync (push/pull to other machines)", sync_repo),
    ("Dashboard", open_dashboard),
    ("Preferences (theme, icons, colors)", preferences),
]


def run():
    if banner.enabled():
        banner.render_animated()

    while True:
        print("\n" + "=" * 40)
        print(" claude-orchestrator")
        print("=" * 40)
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i}. {label}")
        print("  0. Quit")

        choice = input("\n> ").strip()
        if choice == "0" or choice.lower() in ("q", "quit", "exit"):
            break
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(MENU):
                raise ValueError
        except ValueError:
            print("pick a number from the list")
            continue

        _, action = MENU[idx]
        try:
            action()
        except (KeyboardInterrupt, EOFError):
            print()
            continue
        _pause()
