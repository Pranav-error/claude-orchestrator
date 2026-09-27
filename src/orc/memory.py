"""Mirrors Claude Code's scattered per-cwd memory files into this repo's
canonical, topic-keyed store.

Source files are left untouched. Each file is re-homed under memory/<type>/
by its frontmatter `name`, tagged with which project it came from and who
mirrored it (account label + machine), and deduped by the hash of its body
so re-running sync never creates copies of something already imported.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

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
    # Sorted so the graph, and anything derived from it, has a stable order.
    # rglob returns directory order, which differs between filesystems, so an
    # ambiguous query would otherwise number its matches differently per machine.
    return {f.stem: f for f in sorted(config.MEMORY_DIR.rglob("*.md"))}


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


class AmbiguousMemoryQuery(ValueError):
    """Raised instead of a plain ValueError when a query matches more than
    one memory, so callers can offer a numbered picker instead of just
    printing a wall of comma-separated names."""

    def __init__(self, query: str, matches: list[str]):
        self.query = query
        self.matches = matches
        shown = matches[:15]
        lines = [f"{query!r} is ambiguous — {len(matches)} matches:"]
        lines += [f"  {i}. {m}" for i, m in enumerate(shown, 1)]
        if len(matches) > len(shown):
            lines.append(f"  ... and {len(matches) - len(shown)} more — try a more specific query")
        super().__init__("\n".join(lines))


def _find_one(query: str, graph: dict) -> str:
    q_slug = slugify(query)
    exact = [s for s in graph if s == q_slug]
    if exact:
        return exact[0]
    matches = [s for s in graph if q_slug in s or q_slug in slugify(graph[s]["name"])]
    if not matches:
        raise ValueError(f"no memory matches {query!r}")
    if len(matches) > 1:
        raise AmbiguousMemoryQuery(query, matches)
    return matches[0]


def encode_project_dir(path) -> str:
    """Claude Code names each project dir after the cwd with every '/'
    replaced by '-'. Mirrored memories record that encoded name in their
    `source_project` frontmatter, so encoding a path the same way is how
    we match memories to a directory."""
    return str(Path(path).resolve()).replace("/", "-")


def readable_project(encoded: str) -> str:
    """A `source_project` value (Claude Code's dash-encoded dir name,
    e.g. `-Users-you-Documents-GitHub-my-app`) is illegible as-is, and
    can't be decoded by just swapping dashes back to slashes -- a literal
    dash in a real directory name (`contract-review-saas`) looks
    identical to an encoded slash, so the encoding is lossy in general.

    Session transcripts under that same project directory carry the real
    `cwd` un-encoded (this is the same trick usage.py's `_project_label`
    uses), so this looks one up there instead of guessing from the
    string. Display only -- matching memories to a directory still goes
    through `encode_project_dir`/`_candidate_subdir_encodings`, which
    resolve the ambiguity by walking the real filesystem instead.
    """
    proj_dir = config.CLAUDE_PROJECTS / encoded
    if not proj_dir.exists():
        return encoded
    for jsonl_path in sorted(proj_dir.glob("*.jsonl")):
        try:
            with jsonl_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    cwd = json.loads(line).get("cwd")
                    if cwd:
                        home = str(Path.home())
                        return "~" + cwd[len(home):] if cwd.startswith(home) else cwd
        except (OSError, json.JSONDecodeError):
            continue
    return encoded


def _candidate_subdir_encodings(target: Path) -> set[str]:
    """Encodings of `target` and every directory beneath it that actually
    exists on disk.

    Why not just string-prefix match the encoded names: the encoding is
    lossy. A literal '-' in a directory name and an encoded '/' are the
    same character afterwards, so '-repo-one-extra' is simultaneously a
    valid encoding of 'repo-one-extra' (a SIBLING of repo-one) and of
    'repo/one/extra' (a child). No amount of string manipulation can tell
    those apart. Walking the real filesystem can — we only ever match
    encodings of paths that genuinely exist under the target.
    """
    encodings = {encode_project_dir(target)}
    try:
        for sub in target.rglob("*"):
            if sub.is_dir():
                encodings.add(encode_project_dir(sub))
    except OSError:
        pass
    return encodings


_PROJECT_ROOT_MARKERS = (".git", ".hg", ".svn")


def project_root(path=None) -> Path:
    """The repo root at or above `path`, or `path` itself if none is found.

    Without this, `orc memory here` run from repo/backend/src found
    nothing — it only looked at that exact directory and below, while the
    memories were recorded at the repo root. Being deeper inside a project
    should surface more of its context, not less. Borrowed from how
    context-mode anchors session events to a project rather than to
    whatever directory a command happened to run in.
    """
    start = Path(path or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if any((candidate / marker).exists() for marker in _PROJECT_ROOT_MARKERS):
            return candidate
    return start


def for_project(path=None, limit: int = 10) -> list[dict]:
    """Memories belonging to a given directory's project (default: cwd),
    most recently mirrored first.

    Anchors to the enclosing repo root, then matches that directory and
    everything beneath it — so running this from anywhere inside a repo
    surfaces the whole repo's memories, not just the current folder's.
    """
    if not config.MEMORY_DIR.exists():
        return []

    target = project_root(path)
    valid = _candidate_subdir_encodings(target)
    hits = []
    for f in sorted(config.MEMORY_DIR.rglob("*.md")):
        meta, _ = parse_frontmatter(f.read_text())
        source = meta.get("source_project", "")
        if not source:
            continue
        if source in valid:
            hits.append({
                "stem": f.stem,
                "name": meta.get("name", f.stem),
                "description": meta.get("description", ""),
                "type": meta.get("type", "uncategorized"),
                "mirrored_at": meta.get("mirrored_at", ""),
            })

    hits.sort(key=lambda h: h["mirrored_at"], reverse=True)
    return hits[:limit]


def hub_ranking(top_n: int = 10) -> list[dict]:
    """The most-connected memories — [[link]] count in + out — as a ranked
    list. Pure data (no rendering); dashboard.render_memory_graph turns
    this into the colored terminal view. Memories with zero links are
    excluded: a hub ranking of unconnected files isn't a ranking."""
    graph = build_link_graph()
    ranked = []
    for stem, data in graph.items():
        total = len(data["outgoing"]) + len(data["incoming"])
        if total == 0:
            continue
        ranked.append({
            "stem": stem,
            "name": data["name"],
            "incoming": len(data["incoming"]),
            "outgoing": len(data["outgoing"]),
            "total": total,
        })
    ranked.sort(key=lambda r: (-r["total"], r["name"]))
    return ranked[:top_n]


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


# Relevance weights for search. A hit in the title means the memory is
# ABOUT the term; a hit buried in the body might be an aside. Weighting
# them equally is why searching "verification" used to bury the memories
# actually named verification-* below unrelated alphabetically-earlier
# files.
#
# Deliberately a simple weighted count rather than a real index
# (SQLite FTS5 + BM25, which is what context-mode uses): for a few
# hundred plain markdown files the ranking quality is indistinguishable,
# and an index would add a schema to migrate, keep in sync on every
# sync/edit, and repair when it drifts. This tool stays stdlib-only and
# reads the files that are already on disk.
_SCORE_NAME = 10
_SCORE_DESCRIPTION = 4
_SCORE_BODY_HIT = 1
_SCORE_BODY_CAP = 5  # a term repeated 50x isn't 50x more relevant


def _score(query_l: str, name: str, description: str, body: str) -> int:
    score = 0
    if query_l in name.lower():
        score += _SCORE_NAME
    if query_l in description.lower():
        score += _SCORE_DESCRIPTION
    score += min(body.lower().count(query_l), _SCORE_BODY_CAP) * _SCORE_BODY_HIT
    return score


def search(query: str) -> list[dict]:
    """Full-text search, best matches first. Ties break on name so the
    order is stable across machines (filesystem walk order is not)."""
    if not config.MEMORY_DIR.exists():
        return []
    query_l = query.lower()
    hits = []
    for f in sorted(config.MEMORY_DIR.rglob("*.md")):
        text = f.read_text()
        if query_l not in text.lower():
            continue
        meta, body = parse_frontmatter(text)
        name = meta.get("name", f.stem)
        description = meta.get("description", "")
        hits.append({
            "path": str(f.relative_to(config.MEMORY_DIR)),
            "name": name,
            "description": description,
            "score": _score(query_l, name, description, body),
        })
    hits.sort(key=lambda h: (-h["score"], h["name"]))
    return hits


def list_all() -> list[dict]:
    """Every memory, pre-loaded (name/description/type/body/mtime), for
    the interactive browser and anything doing text comparison across the
    whole store. Reading a few hundred small markdown files upfront is
    simpler than caching them piecemeal, and this only runs once per
    `orc memory browse` session, not per keystroke."""
    if not config.MEMORY_DIR.exists():
        return []
    entries = []
    for f in sorted(config.MEMORY_DIR.rglob("*.md")):
        meta, body = parse_frontmatter(f.read_text())
        entries.append({
            "stem": f.stem,
            "path": f,
            "name": meta.get("name", f.stem),
            "description": meta.get("description", ""),
            "type": meta.get("type", "uncategorized"),
            "source_project": meta.get("source_project", ""),
            "body": body,
            "mtime": f.stat().st_mtime,
        })
    return entries


_WORD_RE = re.compile(r"[a-z]{4,}")


def _tokens(*texts: str) -> set:
    words = set()
    for t in texts:
        words.update(_WORD_RE.findall(t.lower()))
    return words


def suggest_related(query: str, top_n: int = 5, entries: list[dict] | None = None, graph: dict | None = None) -> list[dict]:
    """Candidates worth manually [[linking]] the queried memory to,
    ranked by crude word overlap (Jaccard similarity over words of 4+
    letters — no stemming, no TF-IDF weighting). This is a *nomination*
    for a person to confirm via `orc memory link` or the browse UI's link
    picker, never applied automatically: a false-positive link (two
    unrelated projects that happen to share vocabulary) is worse than a
    missed one, and there's no way to verify from text alone that two
    memories are actually about "the same kind of project" rather than
    just using similar words.

    `entries`/`graph` let a caller that already loaded them (the browse
    UI, redrawing on every keystroke) pass them in instead of this
    function re-reading every file from disk each time it's called.
    """
    entries_by_stem = {e["stem"]: e for e in (entries if entries is not None else list_all())}
    graph = graph if graph is not None else build_link_graph()
    stem = _find_one(query, graph)
    if stem not in entries_by_stem:
        return []

    already_linked = set(graph[stem]["outgoing"]) | set(graph[stem]["incoming"])
    target = entries_by_stem[stem]
    target_tokens = _tokens(target["name"], target["description"], target["body"])
    if not target_tokens:
        return []

    scored = []
    for other_stem, other in entries_by_stem.items():
        if other_stem == stem or other_stem in already_linked:
            continue
        other_tokens = _tokens(other["name"], other["description"], other["body"])
        overlap = target_tokens & other_tokens
        if not overlap:
            continue
        jaccard = len(overlap) / len(target_tokens | other_tokens)
        scored.append({
            "stem": other_stem,
            "name": other["name"],
            "source_project": other["source_project"],
            "score": round(jaccard * 100),
        })
    scored.sort(key=lambda s: (-s["score"], s["name"]))
    return scored[:top_n]


def cross_project_links(path=None) -> list[dict]:
    """Already-[[linked]] memories that cross a project boundary — e.g. a
    memory recorded from `darapana-v2` explicitly linked to one from
    `darapana`. This is what a session-start hook can safely echo
    unprompted: every entry here came from a deliberate `orc memory
    link` (or the browse UI's link picker) call, never a guess, so
    surfacing it costs nothing in false positives — unlike
    `suggest_related`, which is a nomination for a human to confirm."""
    target = project_root(path)
    valid = _candidate_subdir_encodings(target)
    graph = build_link_graph()

    own_stems = set()
    for stem, data in graph.items():
        meta, _ = parse_frontmatter(data["path"].read_text())
        if meta.get("source_project", "") in valid:
            own_stems.add(stem)

    results = []
    for stem in own_stems:
        data = graph[stem]
        for direction, others in (("outgoing", data["outgoing"]), ("incoming", data["incoming"])):
            for other_stem in others:
                if other_stem in own_stems:
                    continue  # linked to another memory of this SAME project -- not cross-project
                other_meta, _ = parse_frontmatter(graph[other_stem]["path"].read_text())
                results.append({
                    "from_stem": stem,
                    "from_name": data["name"],
                    "direction": direction,
                    "other_stem": other_stem,
                    "other_name": graph[other_stem]["name"],
                    "other_project": other_meta.get("source_project", "unknown"),
                })
    results.sort(key=lambda r: (r["from_name"], r["other_name"]))
    return results
