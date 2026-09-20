"""Mirrors Claude Code's scattered per-cwd memory files into this repo's
canonical, topic-keyed store.

Source files are left untouched. Each file is re-homed under memory/<type>/
by its frontmatter `name`, tagged with which project it came from and who
mirrored it (account label + machine), and deduped by the hash of its body
so re-running sync never creates copies of something already imported.
"""

import hashlib
import re
from datetime import datetime, timezone

from . import config, identity

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "untitled"


def content_hash(body: str) -> str:
    # Normalize before hashing: a source file's raw body and the body written
    # back out after a previous sync (which is lstripped) must hash equal,
    # or every already-mirrored file looks "new" on the next sync.
    return hashlib.sha256(body.strip().encode()).hexdigest()[:12]


def discover_source_files():
    if not config.CLAUDE_PROJECTS.exists():
        return
    for mem_dir in sorted(config.CLAUDE_PROJECTS.glob("*/memory")):
        project = mem_dir.parent.name
        for f in sorted(mem_dir.glob("*.md")):
            if f.name == "MEMORY.md":
                continue
            yield project, f


def sync(dry_run: bool = False) -> dict:
    config.MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    existing_hashes = {}
    for f in config.MEMORY_DIR.rglob("*.md"):
        _, body = parse_frontmatter(f.read_text())
        existing_hashes[content_hash(body)] = f

    who = identity.current()
    account_label = who["label"] if who else "unknown"

    imported, skipped_duplicate = [], []

    for project, src in discover_source_files():
        text = src.read_text()
        meta, body = parse_frontmatter(text)
        mtype = meta.get("type", "uncategorized")
        name = meta.get("name", src.stem)
        h = content_hash(body)

        if h in existing_hashes:
            skipped_duplicate.append({"project": project, "file": src.name})
            continue

        dest_dir = config.MEMORY_DIR / mtype
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{slugify(name)}.md"
        if dest.exists():
            dest = dest_dir / f"{slugify(name)}--{project}.md"

        header = "\n".join([
            "---",
            f"name: {name}",
            f"description: {meta.get('description', '')}",
            f"type: {mtype}",
            f"source_project: {project}",
            f"mirrored_by: {account_label}",
            f"mirrored_on: {config.hostname()}",
            f"mirrored_at: {datetime.now(timezone.utc).isoformat()}",
            "---",
            "",
        ])
        new_text = header + body.lstrip("\n")

        if not dry_run:
            dest.write_text(new_text)
        existing_hashes[h] = dest
        imported.append({
            "project": project,
            "file": src.name,
            "mirrored_to": str(dest.relative_to(config.MEMORY_DIR)),
        })

    return {"imported": imported, "skipped_duplicate": skipped_duplicate}


def _link_targets(text: str) -> list[str]:
    return [slugify(m) for m in LINK_RE.findall(text)]


def _all_files_by_stem() -> dict:
    if not config.MEMORY_DIR.exists():
        return {}
    return {f.stem: f for f in config.MEMORY_DIR.rglob("*.md")}


def _resolve_stem(target_slug: str, by_stem: dict) -> list[str]:
    """A [[link]] slug may match a plain file, or one disambiguated with
    --project when two sources shared a name — match either."""
    return [stem for stem in by_stem if stem == target_slug or stem.startswith(target_slug + "--")]


def build_link_graph() -> dict:
    """stem -> {name, path, outgoing: [stems], incoming: [stems]}"""
    by_stem = _all_files_by_stem()
    graph = {stem: {"path": path, "outgoing": [], "incoming": []} for stem, path in by_stem.items()}

    for stem, path in by_stem.items():
        meta, body = parse_frontmatter(path.read_text())
        graph[stem]["name"] = meta.get("name", stem)
        for target_slug in _link_targets(body):
            for resolved in _resolve_stem(target_slug, by_stem):
                if resolved != stem and resolved not in graph[stem]["outgoing"]:
                    graph[stem]["outgoing"].append(resolved)

    for stem, data in graph.items():
        for other_stem, other_data in graph.items():
            if stem in other_data["outgoing"]:
                data["incoming"].append(other_stem)

    return graph


def _find_one(query: str, graph: dict) -> str:
    q_slug = slugify(query)
    exact = [s for s in graph if s == q_slug]
    if exact:
        return exact[0]
    matches = [s for s in graph if q_slug in s or q_slug in slugify(graph[s]["name"])]
    if not matches:
        raise ValueError(f"no memory matches {query!r}")
    if len(matches) > 1:
        raise ValueError(f"{query!r} is ambiguous, matches: {', '.join(matches)}")
    return matches[0]


def links_for(query: str) -> dict:
    graph = build_link_graph()
    stem = _find_one(query, graph)
    data = graph[stem]
    return {
        "stem": stem,
        "name": data["name"],
        "outgoing": [{"stem": s, "name": graph[s]["name"]} for s in data["outgoing"]],
        "incoming": [{"stem": s, "name": graph[s]["name"]} for s in data["incoming"]],
    }


def add_link(from_query: str, to_query: str) -> dict:
    graph = build_link_graph()
    from_stem = _find_one(from_query, graph)
    to_stem = _find_one(to_query, graph)

    path = graph[from_stem]["path"]
    text = path.read_text()
    if f"[[{to_stem}]]" in text:
        return {"from": from_stem, "to": to_stem, "already_linked": True}

    if not text.endswith("\n"):
        text += "\n"
    text += f"\nSee also: [[{to_stem}]]\n"
    path.write_text(text)
    return {"from": from_stem, "to": to_stem, "already_linked": False}


def search(query: str) -> list[dict]:
    if not config.MEMORY_DIR.exists():
        return []
    query_l = query.lower()
    hits = []
    for f in sorted(config.MEMORY_DIR.rglob("*.md")):
        text = f.read_text()
        if query_l not in text.lower():
            continue
        meta, _ = parse_frontmatter(text)
        hits.append({
            "path": str(f.relative_to(config.MEMORY_DIR)),
            "name": meta.get("name", f.stem),
            "description": meta.get("description", ""),
        })
    return hits
