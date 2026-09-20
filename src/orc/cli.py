import argparse
import json
import sys

from . import __version__, agentlog, banner, config, dashboard, identity, init, memory, menu, settings, skills, sync, usage


def cmd_identity_set(args):
    entry = identity.set_identity(args.label)
    print(f"identity set: {entry['label']} on {entry['machine']} (since {entry['since']})")


def cmd_identity_show(args):
    cur = identity.current()
    if not cur:
        print("no identity set on this machine yet — run `orc identity set <label>`")
        return
    print(f"{cur['label']}  (machine={cur['machine']}, since={cur['since']})")


def cmd_identity_log(args):
    for h in identity.history():
        print(f"{h['since']}  {h['label']:<20}  {h['machine']}")


def cmd_memory_sync(args):
    result = memory.sync(dry_run=args.dry_run)
    verb = "would mirror" if args.dry_run else "mirrored"
    for item in result["imported"]:
        print(f"{verb}: {item['project']}/{item['file']} -> memory/{item['mirrored_to']}")
    print(f"\n{len(result['imported'])} {verb}, {len(result['skipped_duplicate'])} already present")


def cmd_memory_search(args):
    hits = memory.search(args.query)
    if not hits:
        print("no matches")
        return
    for h in hits:
        print(f"{h['path']:<50} {h['name']}")
        if h["description"]:
            print(f"  {h['description']}")


def cmd_memory_links(args):
    try:
        data = memory.links_for(args.query)
    except ValueError as e:
        print(f"error: {e}")
        return
    print(f"{data['name']}  ({data['stem']})")
    print(f"\n  links to ({len(data['outgoing'])}):")
    for l in data["outgoing"]:
        print(f"    -> {l['name']}  ({l['stem']})")
    print(f"\n  linked from ({len(data['incoming'])}):")
    for l in data["incoming"]:
        print(f"    <- {l['name']}  ({l['stem']})")


def cmd_memory_link(args):
    try:
        result = memory.add_link(args.from_, args.to)
    except ValueError as e:
        print(f"error: {e}")
        return
    if result["already_linked"]:
        print(f"already linked: {result['from']} -> {result['to']}")
    else:
        print(f"linked: {result['from']} -> {result['to']}")


def cmd_usage_report(args):
    data = usage.report(since=args.since, group_by=args.by)
    if not data:
        print("no usage data found under ~/.claude/projects")
        return
    print(f"{'key':<28}{'input':>12}{'output':>12}{'cache_r':>12}{'cache_w':>12}{'msgs':>8}")
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "messages": 0}
    for key, b in data.items():
        print(f"{key:<28}{b['input']:>12}{b['output']:>12}{b['cache_read']:>12}{b['cache_write']:>12}{b['messages']:>8}")
        totals["input"] += b["input"]
        totals["output"] += b["output"]
        totals["cache_read"] += b["cache_read"]
        totals["cache_write"] += b["cache_write"]
        totals["messages"] += b["messages"]
    print("-" * 84)
    print(f"{'TOTAL':<28}{totals['input']:>12}{totals['output']:>12}{totals['cache_read']:>12}{totals['cache_write']:>12}{totals['messages']:>8}")


def cmd_skill_list(args):
    rows = skills.list_skills()
    if not rows:
        print("no skills found")
        return
    print(f"{'name':<24}{'status':<10}{'source':<45}{'version'}")
    for r in rows:
        status = "enabled" if r["enabled"] else "disabled"
        if not r["managed"]:
            status = "unmanaged"
        print(f"{r['name']:<24}{status:<10}{r['source']:<45}{r['version']}")


def cmd_skill_adopt(args):
    try:
        entry = skills.adopt(args.name, source=args.source or "unknown")
    except ValueError as e:
        print(f"error: {e}")
        return
    print(f"adopted {args.name} into the registry (source={entry['source']})")


def cmd_skill_install(args):
    try:
        entry = skills.install(args.name, args.source_url)
    except ValueError as e:
        print(f"error: {e}")
        return
    print(f"installed {args.name} @ {entry['version']} and enabled it")


def cmd_skill_enable(args):
    try:
        skills.enable(args.name)
    except ValueError as e:
        print(f"error: {e}")
        return
    print(f"enabled {args.name}")


def cmd_skill_disable(args):
    try:
        skills.disable(args.name)
    except ValueError as e:
        print(f"error: {e}")
        return
    print(f"disabled {args.name}")


def cmd_agent_log(args):
    entry = agentlog.log_run(args.task, args.outcome, notes=args.notes or "")
    print(f"logged: [{entry['outcome']}] {entry['task']} (account={entry['account']}, machine={entry['machine']})")


def cmd_agent_list(args):
    rows = agentlog.list_runs(since=args.since, account=args.account, outcome=args.outcome)
    if not rows:
        print("no runs recorded")
        return
    for r in rows:
        line = f"{r['timestamp']}  [{r['outcome']:<7}]  {r['account']:<14}  {r['task']}"
        print(line)
        if r["notes"]:
            print(f"  {r['notes']}")


def cmd_sync_push(args):
    result = sync.push()
    if not result["ok"]:
        print(f"push failed: {result['detail']}")
        return
    verb = "committed + pushed" if result["committed"] else "pushed"
    print(f"{verb}: {result['detail']}")


def cmd_sync_pull(args):
    result = sync.pull()
    if not result["ok"]:
        print(f"pull failed: {result['detail']}")
        return
    print(f"pulled: {result['detail']}")


def cmd_sync_status(args):
    s = sync.status()
    dirty = "dirty (uncommitted changes)" if s["dirty"] else "clean"
    print(f"branch: {s['branch']}   ahead: {s['ahead']}   behind: {s['behind']}   {dirty}")


def cmd_dashboard(args):
    if args.html:
        path = dashboard.generate_html()
        print(f"dashboard written to {path}")
        if not args.no_open:
            dashboard.open_in_browser(path)
        return
    color = {"always": True, "never": False, None: None}[args.color]
    print(dashboard.render_terminal(color=color, theme_name=args.theme, usage_days=args.days))


def cmd_config_show(args):
    s = settings.load()
    for k, v in s.items():
        print(f"{k} = {v}")
    print(f"\nthemes: {', '.join(settings.THEMES)}")


def cmd_config_set(args):
    try:
        s = settings.set_value(args.key, args.value)
    except ValueError as e:
        print(f"error: {e}")
        return
    print(f"{args.key} = {s[args.key]}")


def cmd_init(args):
    result = init.run()
    if result["already_initialized"]:
        print(f"already initialized at {result['path']}")
        return
    print(f"created a private data repo at {result['path']}")
    print()
    print("Next (your call, not automatic):")
    print(f"  1. cd {result['path']}")
    print("  2. gh repo create --private <name> --source=. --remote=origin --push")
    print("     (or add any other git remote and `git push -u origin main`)")
    print()
    print(f"If you want data somewhere other than {config.DATA_ROOT.parent}, set ORC_DATA_DIR")
    print("before running `orc init` again, e.g.:")
    print('  export ORC_DATA_DIR="$HOME/my-private-orc-data"')


def cmd_version(args):
    if banner.enabled():
        print(banner.render())
        print()
    print(f"orc {__version__}")
    print(f"code:    {config.CODE_ROOT}")
    print(f"data:    {config.DATA_ROOT}")


def build_parser():
    p = argparse.ArgumentParser(prog="orc", description="Personal control plane for a multi-account Claude Code setup.")
    sub = p.add_subparsers(dest="command", required=False)

    version_p = sub.add_parser("version", help="show version, install paths, and the startup banner")
    version_p.set_defaults(func=cmd_version)

    init_p = sub.add_parser("init", help="bootstrap a private data repo (run this first, once)")
    init_p.set_defaults(func=cmd_init)

    id_p = sub.add_parser("identity", help="which account is active on this machine")
    id_sub = id_p.add_subparsers(dest="identity_command", required=True)
    id_set = id_sub.add_parser("set", help="record an account switch on this machine")
    id_set.add_argument("label", help="e.g. 'mine', 'friend-nandan', 'client-amith'")
    id_set.set_defaults(func=cmd_identity_set)
    id_show = id_sub.add_parser("show", help="show the currently active identity")
    id_show.set_defaults(func=cmd_identity_show)
    id_log = id_sub.add_parser("log", help="show every recorded identity switch")
    id_log.set_defaults(func=cmd_identity_log)

    mem_p = sub.add_parser("memory", help="mirror and search memory across all projects")
    mem_sub = mem_p.add_subparsers(dest="memory_command", required=True)
    mem_sync = mem_sub.add_parser("sync", help="mirror new memory files into the canonical store")
    mem_sync.add_argument("--dry-run", action="store_true")
    mem_sync.set_defaults(func=cmd_memory_sync)
    mem_search = mem_sub.add_parser("search", help="search the canonical memory store")
    mem_search.add_argument("query")
    mem_search.set_defaults(func=cmd_memory_search)

    mem_links = mem_sub.add_parser("links", help="show what a memory links to / is linked from")
    mem_links.add_argument("query")
    mem_links.set_defaults(func=cmd_memory_links)

    mem_link = mem_sub.add_parser("link", help="add a [[link]] from one memory to another")
    mem_link.add_argument("from_", metavar="from")
    mem_link.add_argument("to")
    mem_link.set_defaults(func=cmd_memory_link)

    usage_p = sub.add_parser("usage", help="token usage aggregated from Claude Code session transcripts")
    usage_sub = usage_p.add_subparsers(dest="usage_command", required=True)
    usage_report = usage_sub.add_parser("report", help="print a usage table")
    usage_report.add_argument("--since", help="ISO date, e.g. 2026-09-01")
    usage_report.add_argument("--by", choices=["day", "project", "model", "identity"], default="day")
    usage_report.set_defaults(func=cmd_usage_report)

    skill_p = sub.add_parser("skill", help="manage skills/plugins installed under ~/.claude/skills")
    skill_sub = skill_p.add_subparsers(dest="skill_command", required=True)

    skill_list = skill_sub.add_parser("list", help="show managed + unmanaged skills")
    skill_list.set_defaults(func=cmd_skill_list)

    skill_adopt = skill_sub.add_parser("adopt", help="bring an already-installed skill under registry control")
    skill_adopt.add_argument("name")
    skill_adopt.add_argument("--source", help="where it came from, if known")
    skill_adopt.set_defaults(func=cmd_skill_adopt)

    skill_install = skill_sub.add_parser("install", help="git-clone a new skill into the registry and enable it")
    skill_install.add_argument("name")
    skill_install.add_argument("source_url")
    skill_install.set_defaults(func=cmd_skill_install)

    skill_enable = skill_sub.add_parser("enable", help="re-symlink a managed skill into ~/.claude/skills")
    skill_enable.add_argument("name")
    skill_enable.set_defaults(func=cmd_skill_enable)

    skill_disable = skill_sub.add_parser("disable", help="unlink a managed skill from ~/.claude/skills (kept in the store)")
    skill_disable.add_argument("name")
    skill_disable.set_defaults(func=cmd_skill_disable)

    agent_p = sub.add_parser("agent", help="record and query subagent run history")
    agent_sub = agent_p.add_subparsers(dest="agent_command", required=True)

    agent_log = agent_sub.add_parser("log", help="record a finished subagent run")
    agent_log.add_argument("task", help="short description of what ran")
    agent_log.add_argument("outcome", choices=sorted(agentlog.VALID_OUTCOMES))
    agent_log.add_argument("--notes")
    agent_log.set_defaults(func=cmd_agent_log)

    agent_list = agent_sub.add_parser("list", help="show recorded runs")
    agent_list.add_argument("--since", help="ISO date, e.g. 2026-09-01")
    agent_list.add_argument("--account")
    agent_list.add_argument("--outcome", choices=sorted(agentlog.VALID_OUTCOMES))
    agent_list.set_defaults(func=cmd_agent_list)

    sync_p = sub.add_parser("sync", help="push/pull this repo's git remote (cross-machine)")
    sync_sub = sync_p.add_subparsers(dest="sync_command", required=True)
    sync_push = sync_sub.add_parser("push", help="commit any local changes and push")
    sync_push.set_defaults(func=cmd_sync_push)
    sync_pull = sync_sub.add_parser("pull", help="pull remote changes (refuses if you have uncommitted local changes)")
    sync_pull.set_defaults(func=cmd_sync_pull)
    sync_status = sync_sub.add_parser("status", help="branch, ahead/behind, dirty state")
    sync_status.set_defaults(func=cmd_sync_status)

    dash_p = sub.add_parser("dashboard", help="show a read-only snapshot of everything (in the terminal by default)")
    dash_p.add_argument("--html", action="store_true", help="write an HTML file instead of printing to the terminal")
    dash_p.add_argument("--no-open", action="store_true", help="with --html, don't auto-open it in a browser")
    dash_p.add_argument("--theme", choices=sorted(settings.THEMES), help="override the configured theme for this run")
    dash_p.add_argument("--color", choices=["always", "never"], default=None,
                         help="force color on/off for this run (use 'always' inside Claude's !orc / /orc so it's not treated as a non-tty pipe)")
    dash_p.add_argument("--days", type=int, help="override how many days of usage to show")
    dash_p.set_defaults(func=cmd_dashboard)

    config_p = sub.add_parser("config", help="view/change display preferences (theme, icons, color, usage window)")
    config_sub = config_p.add_subparsers(dest="config_command", required=True)
    config_show = config_sub.add_parser("show", help="print current settings")
    config_show.set_defaults(func=cmd_config_show)
    config_set = config_sub.add_parser("set", help="e.g. orc config set theme ocean")
    config_set.add_argument("key", choices=sorted(settings.DEFAULTS))
    config_set.add_argument("value")
    config_set.set_defaults(func=cmd_config_set)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        menu.run()
        return
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
