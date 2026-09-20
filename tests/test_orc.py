"""Isolated tests for orc. Every test runs against a throwaway tmp tree —
none of them touch the real ~/.claude or the real repo's memory/skills/logs.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import contextlib
import copy
import io
import subprocess

from orc import agentlog, banner, config, dashboard, identity, init, memory, settings, skills, sync, usage  # noqa: E402
from orc.cli import main as cli_main  # noqa: E402


class OrcTestCase(unittest.TestCase):
    """Redirects every config path into a fresh tmp dir per test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)

        self._orig = {
            k: getattr(config, k)
            for k in [
                "DATA_ROOT", "MEMORY_DIR", "SKILLS_MANIFEST", "SKILLS_STORE", "AGENT_LOG_DIR",
                "IDENTITY_LOG", "CLAUDE_PROJECTS", "CLAUDE_SKILLS", "LOCAL_IDENTITY_FILE",
            ]
        }

        config.DATA_ROOT = root / "repo"
        config.MEMORY_DIR = root / "repo" / "memory"
        config.SKILLS_MANIFEST = root / "repo" / "skills-registry" / "manifest.json"
        config.SKILLS_STORE = root / "repo" / "skills-registry" / "store"
        config.AGENT_LOG_DIR = root / "repo" / "agent-log"
        config.IDENTITY_LOG = config.AGENT_LOG_DIR / "identity-log.jsonl"
        config.CLAUDE_PROJECTS = root / "claude-home" / "projects"
        config.CLAUDE_SKILLS = root / "claude-home" / "skills"
        config.LOCAL_IDENTITY_FILE = root / "claude-home" / "identity.json"

        self._orig_settings_file = settings.SETTINGS_FILE
        settings.SETTINGS_FILE = root / "claude-home" / "settings.json"

        self.root = root

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(config, k, v)
        settings.SETTINGS_FILE = self._orig_settings_file
        self._tmp.cleanup()

    # -- helpers --------------------------------------------------------

    def write_memory_file(self, project: str, filename: str, name: str, mtype: str, body: str):
        d = config.CLAUDE_PROJECTS / project / "memory"
        d.mkdir(parents=True, exist_ok=True)
        text = f"---\nname: {name}\ndescription: test entry\ntype: {mtype}\n---\n\n{body}\n"
        (d / filename).write_text(text)

    def write_transcript(self, project: str, session: str, events: list[dict]):
        d = config.CLAUDE_PROJECTS / project
        d.mkdir(parents=True, exist_ok=True)
        with (d / f"{session}.jsonl").open("w") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")


class IdentityTests(OrcTestCase):
    def test_no_identity_set_returns_none(self):
        self.assertIsNone(identity.current())

    def test_set_then_current_roundtrip(self):
        identity.set_identity("mine")
        cur = identity.current()
        self.assertEqual(cur["label"], "mine")
        self.assertIn("machine", cur)
        self.assertIn("since", cur)

    def test_history_accumulates_every_switch(self):
        identity.set_identity("mine")
        identity.set_identity("friend")
        identity.set_identity("mine")
        hist = identity.history()
        self.assertEqual([h["label"] for h in hist], ["mine", "friend", "mine"])

    def test_label_at_picks_the_switch_active_at_that_moment(self):
        identity.set_identity("mine")
        first_switch_time = identity.current()["since"]
        identity.set_identity("client")

        # a timestamp between the two switches should resolve to "mine"
        mid = "2026-01-01T00:00:00+00:00"  # arbitrary, but before either real switch in CI time
        # use actual recorded times instead of guessing wall-clock ordering
        hist = identity.history()
        self.assertEqual(identity.label_at(hist[0]["since"]), "mine")
        self.assertEqual(identity.label_at(hist[1]["since"]), "client")

    def test_label_at_before_any_switch_is_none(self):
        self.assertIsNone(identity.label_at("2000-01-01T00:00:00Z"))


class MemoryTests(OrcTestCase):
    def test_sync_mirrors_a_new_file(self):
        self.write_memory_file("proj-a", "user_profile.md", "User Profile", "user", "some background")
        result = memory.sync()
        self.assertEqual(len(result["imported"]), 1)
        self.assertEqual(len(result["skipped_duplicate"]), 0)
        dest = config.MEMORY_DIR / "user" / "user-profile.md"
        self.assertTrue(dest.exists())
        self.assertIn("some background", dest.read_text())
        self.assertIn("source_project: proj-a", dest.read_text())

    def test_sync_is_idempotent_across_repeated_runs(self):
        """Regression test for the real bug found in manual testing: a
        second sync must mirror nothing new once a file is already in."""
        self.write_memory_file("proj-a", "notes.md", "Notes", "project", "body text here")

        first = memory.sync()
        self.assertEqual(len(first["imported"]), 1)

        second = memory.sync()
        self.assertEqual(len(second["imported"]), 0, "second sync must not re-mirror an already-synced file")
        third = memory.sync()
        self.assertEqual(len(third["imported"]), 0)

        # exactly one file should exist under memory/, not a duplicate
        all_files = list(config.MEMORY_DIR.rglob("*.md"))
        self.assertEqual(len(all_files), 1)

    def test_identical_content_from_two_projects_is_deduped(self):
        self.write_memory_file("proj-a", "shared.md", "Shared Note", "feedback", "identical body")
        self.write_memory_file("proj-b", "shared.md", "Shared Note", "feedback", "identical body")
        result = memory.sync()
        self.assertEqual(len(result["imported"]), 1)
        self.assertEqual(len(result["skipped_duplicate"]), 1)

    def test_same_name_different_content_gets_disambiguated(self):
        self.write_memory_file("proj-a", "notes.md", "Notes", "project", "content A")
        self.write_memory_file("proj-b", "notes.md", "Notes", "project", "content B")
        result = memory.sync()
        self.assertEqual(len(result["imported"]), 2)
        files = sorted(p.name for p in (config.MEMORY_DIR / "project").glob("*.md"))
        self.assertEqual(files, ["notes--proj-b.md", "notes.md"])

    def test_memory_md_index_file_itself_is_never_mirrored(self):
        d = config.CLAUDE_PROJECTS / "proj-a" / "memory"
        d.mkdir(parents=True, exist_ok=True)
        (d / "MEMORY.md").write_text("- [something](x.md)\n")
        result = memory.sync()
        self.assertEqual(len(result["imported"]), 0)

    def test_search_matches_body_and_frontmatter(self):
        self.write_memory_file("proj-a", "a.md", "Alpha", "project", "mentions gsoc contribution work")
        self.write_memory_file("proj-a", "b.md", "Beta", "project", "unrelated content")
        memory.sync()
        hits = memory.search("gsoc")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["name"], "Alpha")
        self.assertEqual(memory.search("nonexistent_zzz"), [])


class MemoryLinksTests(OrcTestCase):
    def test_outgoing_and_incoming_resolve_both_ways(self):
        self.write_memory_file("proj-a", "a.md", "Alpha", "project", "see also [[beta]]")
        self.write_memory_file("proj-a", "b.md", "Beta", "project", "no links here")
        memory.sync()

        alpha_links = memory.links_for("alpha")
        self.assertEqual(len(alpha_links["outgoing"]), 1)
        self.assertEqual(alpha_links["outgoing"][0]["name"], "Beta")

        beta_links = memory.links_for("beta")
        self.assertEqual(len(beta_links["incoming"]), 1)
        self.assertEqual(beta_links["incoming"][0]["name"], "Alpha")

    def test_link_resolves_to_disambiguated_file(self):
        self.write_memory_file("proj-a", "notes.md", "Notes", "project", "body A, see [[shared-target]]")
        self.write_memory_file("proj-b", "notes.md", "Notes", "project", "body B")
        self.write_memory_file("proj-a", "target.md", "Shared Target", "project", "target body")
        memory.sync()

        # the "notes--proj-b" disambiguated file should still be findable and link-free
        links = memory.links_for("shared-target")
        self.assertEqual(len(links["incoming"]), 1)

    def test_links_for_unknown_query_raises(self):
        with self.assertRaises(ValueError):
            memory.links_for("nothing-like-this-exists")

    def test_add_link_appends_and_is_idempotent(self):
        self.write_memory_file("proj-a", "a.md", "Alpha", "project", "alpha body, no links yet")
        self.write_memory_file("proj-a", "b.md", "Beta", "project", "beta body, no links yet")
        memory.sync()

        result = memory.add_link("alpha", "beta")
        self.assertFalse(result["already_linked"])
        self.assertIn("[[beta]]", (config.MEMORY_DIR / "project" / "alpha.md").read_text())

        # adding again must not duplicate the link
        result2 = memory.add_link("alpha", "beta")
        self.assertTrue(result2["already_linked"])
        text = (config.MEMORY_DIR / "project" / "alpha.md").read_text()
        self.assertEqual(text.count("[[beta]]"), 1)

    def test_ambiguous_query_raises(self):
        self.write_memory_file("proj-a", "one.md", "Test Alpha", "project", "x")
        self.write_memory_file("proj-a", "two.md", "Test Beta", "project", "y")
        memory.sync()
        with self.assertRaises(ValueError):
            memory.links_for("test")


class SkillsTests(OrcTestCase):
    def _make_live_skill(self, name: str, filename: str = "SKILL.md", content: str = "skill content"):
        d = config.CLAUDE_SKILLS / name
        d.mkdir(parents=True, exist_ok=True)
        (d / filename).write_text(content)
        return d

    def test_adopt_moves_content_and_symlinks_back(self):
        self._make_live_skill("banner-design", content="original content")
        entry = skills.adopt("banner-design", source="github.com/example/banner")
        self.assertEqual(entry["source"], "github.com/example/banner")

        live = config.CLAUDE_SKILLS / "banner-design"
        self.assertTrue(live.is_symlink())
        self.assertEqual((live / "SKILL.md").read_text(), "original content")
        self.assertTrue((config.SKILLS_STORE / "banner-design" / "SKILL.md").exists())

    def test_adopt_on_missing_skill_raises(self):
        with self.assertRaises(ValueError):
            skills.adopt("does-not-exist")

    def test_adopt_on_already_symlinked_skill_raises(self):
        self._make_live_skill("dup")
        skills.adopt("dup")
        with self.assertRaises(ValueError):
            skills.adopt("dup")

    def test_disable_then_enable_roundtrip_preserves_content(self):
        self._make_live_skill("brand", content="brand guide v1")
        skills.adopt("brand")

        skills.disable("brand")
        live = config.CLAUDE_SKILLS / "brand"
        self.assertFalse(live.exists())
        self.assertTrue((config.SKILLS_STORE / "brand" / "SKILL.md").exists(), "content must survive disable")

        skills.enable("brand")
        self.assertTrue(live.is_symlink())
        self.assertEqual((live / "SKILL.md").read_text(), "brand guide v1")

    def test_enable_unmanaged_skill_raises(self):
        with self.assertRaises(ValueError):
            skills.enable("never-adopted")

    def test_list_reports_managed_enabled_disabled_and_unmanaged(self):
        self._make_live_skill("managed-one")
        skills.adopt("managed-one")
        skills.disable("managed-one")
        self._make_live_skill("wild-one")  # never adopted

        rows = {r["name"]: r for r in skills.list_skills()}
        self.assertFalse(rows["managed-one"]["enabled"])
        self.assertTrue(rows["managed-one"]["managed"])
        self.assertFalse(rows["wild-one"]["managed"])
        self.assertTrue(rows["wild-one"]["enabled"])


class AgentLogTests(OrcTestCase):
    def test_log_rejects_invalid_outcome(self):
        with self.assertRaises(ValueError):
            agentlog.log_run("some task", "maybe")

    def test_log_then_list_roundtrip(self):
        identity.set_identity("mine")
        agentlog.log_run("built the skills registry", "success", notes="phase 2")
        rows = agentlog.list_runs()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["task"], "built the skills registry")
        self.assertEqual(rows[0]["account"], "mine")

    def test_list_filters_by_account_and_outcome(self):
        identity.set_identity("mine")
        agentlog.log_run("task A", "success")
        identity.set_identity("friend")
        agentlog.log_run("task B", "failed")

        self.assertEqual(len(agentlog.list_runs(account="mine")), 1)
        self.assertEqual(len(agentlog.list_runs(account="friend")), 1)
        self.assertEqual(len(agentlog.list_runs(outcome="failed")), 1)
        self.assertEqual(agentlog.list_runs(account="mine")[0]["outcome"], "success")

    def test_list_filters_by_since(self):
        agentlog.log_run("old-ish task", "success")
        future_cutoff = "2999-01-01T00:00:00+00:00"
        self.assertEqual(agentlog.list_runs(since=future_cutoff), [])
        self.assertEqual(len(agentlog.list_runs(since="2000-01-01T00:00:00+00:00")), 1)


class UsageTests(OrcTestCase):
    def _msg(self, ts, model, input_t, output_t, cache_w=0, cache_r=0):
        return {
            "timestamp": ts,
            "message": {
                "model": model,
                "usage": {
                    "input_tokens": input_t,
                    "output_tokens": output_t,
                    "cache_creation_input_tokens": cache_w,
                    "cache_read_input_tokens": cache_r,
                },
            },
        }

    def test_report_groups_by_day(self):
        self.write_transcript("proj-a", "s1", [
            self._msg("2026-09-01T10:00:00Z", "claude-opus-5", 10, 20),
            self._msg("2026-09-01T12:00:00Z", "claude-opus-5", 5, 5),
            self._msg("2026-09-02T09:00:00Z", "claude-sonnet-5", 100, 200),
        ])
        report = usage.report(group_by="day")
        self.assertEqual(report["2026-09-01"]["input"], 15)
        self.assertEqual(report["2026-09-01"]["output"], 25)
        self.assertEqual(report["2026-09-01"]["messages"], 2)
        self.assertEqual(report["2026-09-02"]["input"], 100)

    def test_project_label_prefers_real_cwd_over_encoded_dir_name(self):
        """Regression test: `orc usage report --by project` used to show the
        raw Claude Code directory name (-Users-x-Documents-GitHub-foo)
        instead of a readable project name — illegible, as a real user
        screenshot showed. The transcript's own `cwd` field fixes this."""
        import os

        d = config.CLAUDE_PROJECTS / "-Users-saipranav-Documents-GitHub-contract-review-saas"
        d.mkdir(parents=True, exist_ok=True)
        entry = self._msg("2026-09-01T00:00:00Z", "claude-opus-5", 1, 1)
        real_cwd = os.path.join(str(Path.home()), "Documents/GitHub/contract-review-saas")
        entry["cwd"] = real_cwd
        (d / "s1.jsonl").write_text(json.dumps(entry) + "\n")

        by_project = usage.report(group_by="project")
        self.assertEqual(list(by_project.keys()), ["~/Documents/GitHub/contract-review-saas"])
        self.assertNotIn("-Users-saipranav-Documents-GitHub-contract-review-saas", by_project)

    def test_project_label_does_not_collapse_unrelated_repos_sharing_a_subfolder_name(self):
        """Regression test for a bug in the FIRST fix attempt: using bare
        basename(cwd) merged e.g. repo-a/backend and repo-b/backend into one
        'backend' bucket, silently combining unrelated projects' usage."""
        import os

        home = str(Path.home())
        d1 = config.CLAUDE_PROJECTS / "-repo-a-encoded"
        d1.mkdir(parents=True, exist_ok=True)
        e1 = self._msg("2026-09-01T00:00:00Z", "claude-opus-5", 1, 1)
        e1["cwd"] = os.path.join(home, "repo-a", "backend")
        (d1 / "s1.jsonl").write_text(json.dumps(e1) + "\n")

        d2 = config.CLAUDE_PROJECTS / "-repo-b-encoded"
        d2.mkdir(parents=True, exist_ok=True)
        e2 = self._msg("2026-09-01T00:00:00Z", "claude-opus-5", 2, 2)
        e2["cwd"] = os.path.join(home, "repo-b", "backend")
        (d2 / "s1.jsonl").write_text(json.dumps(e2) + "\n")

        by_project = usage.report(group_by="project")
        self.assertEqual(len(by_project), 2, f"expected 2 distinct projects, got: {list(by_project)}")
        self.assertIn("~/repo-a/backend", by_project)
        self.assertIn("~/repo-b/backend", by_project)

    def test_project_label_falls_back_to_stripped_dir_name_without_cwd(self):
        d = config.CLAUDE_PROJECTS / "-some-encoded-path"
        d.mkdir(parents=True, exist_ok=True)
        (d / "s1.jsonl").write_text(json.dumps(self._msg("2026-09-01T00:00:00Z", "claude-opus-5", 1, 1)) + "\n")

        by_project = usage.report(group_by="project")
        self.assertEqual(list(by_project.keys()), ["some-encoded-path"])

    def test_report_groups_by_project_and_model(self):
        self.write_transcript("proj-a", "s1", [self._msg("2026-09-01T00:00:00Z", "claude-opus-5", 1, 1)])
        self.write_transcript("proj-b", "s2", [self._msg("2026-09-01T00:00:00Z", "claude-sonnet-5", 2, 2)])

        by_project = usage.report(group_by="project")
        self.assertEqual(set(by_project.keys()), {"proj-a", "proj-b"})

        by_model = usage.report(group_by="model")
        self.assertEqual(set(by_model.keys()), {"claude-opus-5", "claude-sonnet-5"})

    def test_report_since_filters_out_older_events(self):
        self.write_transcript("proj-a", "s1", [
            self._msg("2026-01-01T00:00:00Z", "claude-opus-5", 1, 1),
            self._msg("2026-09-01T00:00:00Z", "claude-opus-5", 1, 1),
        ])
        report = usage.report(since="2026-06-01", group_by="day")
        self.assertEqual(list(report.keys()), ["2026-09-01"])

    def test_report_by_identity_attributes_correctly_and_falls_back_to_unattributed(self):
        self.write_transcript("proj-a", "s1", [
            self._msg("2026-01-01T00:00:00Z", "claude-opus-5", 1, 1),  # before any identity set
        ])
        identity.set_identity("mine")
        switch_time = identity.current()["since"]
        self.write_transcript("proj-a", "s2", [
            self._msg(switch_time, "claude-opus-5", 2, 2),
        ])
        report = usage.report(group_by="identity")
        self.assertIn("unattributed", report)
        self.assertIn("mine", report)

    def test_malformed_transcript_lines_are_skipped_not_fatal(self):
        d = config.CLAUDE_PROJECTS / "proj-a"
        d.mkdir(parents=True, exist_ok=True)
        (d / "s1.jsonl").write_text("not json at all\n" + json.dumps(self._msg("2026-09-01T00:00:00Z", "claude-opus-5", 3, 3)) + "\n")
        report = usage.report(group_by="day")
        self.assertEqual(report["2026-09-01"]["input"], 3)


class SyncTests(OrcTestCase):
    """Simulates two machines sharing one git remote, to prove push/pull
    actually carry state between them — not just that git commands run."""

    def _git(self, cwd, *args, check=True):
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=check)

    def setUp(self):
        super().setUp()
        world = self.root / "sync-world"
        world.mkdir()

        self.remote = world / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(self.remote)], capture_output=True, text=True, check=True)

        seed = world / "seed"
        self._git(world, "init", "-b", "main", str(seed))
        (seed / "README.md").write_text("seed\n")
        self._git(seed, "add", "-A")
        self._git(seed, "commit", "-m", "init")
        self._git(seed, "remote", "add", "origin", str(self.remote))
        self._git(seed, "push", "-u", "origin", "main")

        self.machine_a = world / "machine_a"
        self.machine_b = world / "machine_b"
        self._git(world, "clone", str(self.remote), str(self.machine_a))
        self._git(world, "clone", str(self.remote), str(self.machine_b))

    def test_push_from_one_machine_reaches_another_via_pull(self):
        config.DATA_ROOT = self.machine_a
        (self.machine_a / "new_file.txt").write_text("hello from machine A\n")
        result = sync.push()
        self.assertTrue(result["ok"], result.get("detail"))
        self.assertTrue(result["committed"])
        self.assertTrue(result["pushed"])

        config.DATA_ROOT = self.machine_b
        pulled = sync.pull()
        self.assertTrue(pulled["ok"], pulled.get("detail"))
        self.assertEqual((self.machine_b / "new_file.txt").read_text(), "hello from machine A\n")

    def test_push_with_nothing_to_commit_still_succeeds(self):
        config.DATA_ROOT = self.machine_a
        result = sync.push()
        self.assertTrue(result["ok"])
        self.assertFalse(result["committed"])

    def test_pull_refuses_when_local_changes_are_uncommitted(self):
        config.DATA_ROOT = self.machine_b
        (self.machine_b / "dirty.txt").write_text("uncommitted\n")
        result = sync.pull()
        self.assertFalse(result["ok"])
        self.assertIn("uncommitted", result["detail"])

    def test_status_reports_behind_after_fetching_a_remote_push(self):
        config.DATA_ROOT = self.machine_a
        (self.machine_a / "another.txt").write_text("x\n")
        sync.push()

        config.DATA_ROOT = self.machine_b
        self._git(self.machine_b, "fetch")
        s = sync.status()
        self.assertEqual(s["behind"], "1")
        self.assertEqual(s["ahead"], "0")
        self.assertFalse(s["dirty"])


class SettingsTests(OrcTestCase):
    def test_load_with_no_file_returns_defaults(self):
        s = settings.load()
        self.assertEqual(s, settings.DEFAULTS)

    def test_set_then_load_roundtrip(self):
        settings.set_value("theme", "ocean")
        self.assertEqual(settings.get("theme"), "ocean")
        self.assertEqual(settings.load()["theme"], "ocean")

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            settings.set_value("nonexistent", "x")

    def test_unknown_theme_rejected(self):
        with self.assertRaises(ValueError):
            settings.set_value("theme", "not-a-real-theme")

    def test_invalid_color_mode_rejected(self):
        with self.assertRaises(ValueError):
            settings.set_value("color", "sometimes")

    def test_icons_coerced_to_bool_from_string(self):
        settings.set_value("icons", "false")
        self.assertIs(settings.get("icons"), False)
        settings.set_value("icons", "true")
        self.assertIs(settings.get("icons"), True)

    def test_usage_days_coerced_to_int(self):
        settings.set_value("usage_days", "7")
        self.assertEqual(settings.get("usage_days"), 7)
        self.assertIsInstance(settings.get("usage_days"), int)

    def test_corrupt_settings_file_falls_back_to_defaults(self):
        settings.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        settings.SETTINGS_FILE.write_text("{ not valid json")
        self.assertEqual(settings.load(), settings.DEFAULTS)

    def test_all_theme_names_resolve_to_a_theme_dict(self):
        for name in settings.THEMES:
            th = settings.theme(name)
            self.assertIn("gradient", th)
            self.assertIn("good", th)

    def test_banner_defaults_on_and_coerces_from_string(self):
        self.assertIs(settings.get("banner"), True)
        settings.set_value("banner", "false")
        self.assertIs(settings.get("banner"), False)
        settings.set_value("banner", "true")
        self.assertIs(settings.get("banner"), True)


class BannerTests(OrcTestCase):
    def test_render_contains_name_and_version(self):
        text = banner.render(color=False)
        self.assertIn("claude-orchestrator", text)
        self.assertIn("orc", text)

    def test_plain_mode_has_no_color_codes(self):
        text = banner.render(color=False)
        self.assertNotIn("\033[", text)

    def test_color_mode_renders_the_pixel_face_with_ansi(self):
        text = banner.render(color=True)
        self.assertIn("\033[38;5;", text)

    def test_base_grid_rows_are_all_equal_width(self):
        widths = {len(row) for row in banner.BASE_GRID}
        self.assertEqual(len(widths), 1, f"BASE_GRID rows have mismatched widths: {widths}")

    def test_every_legend_character_in_base_grid_has_a_palette_entry(self):
        used = {ch for row in banner.BASE_GRID for ch in row}
        self.assertTrue(used.issubset(set(banner.PALETTE.keys())))

    def test_every_tail_frame_overlay_is_within_grid_bounds(self):
        height = len(banner.BASE_GRID)
        width = len(banner.BASE_GRID[0])
        for overlay in banner.TAIL_FRAMES:
            for r, col, ch in overlay:
                self.assertTrue(0 <= r < height, f"row {r} out of bounds (height {height})")
                self.assertTrue(0 <= col < width, f"col {col} out of bounds (width {width})")
                self.assertIn(ch, banner.PALETTE)

    def test_build_frame_applies_base_and_overlay(self):
        frame = banner._build_frame(banner.TAIL_FRAMES[0])
        r, col, ch = banner._TAIL_BASE[0]
        self.assertEqual(frame[r][col], ch)
        r2, col2, ch2 = banner.TAIL_FRAMES[0][0]
        self.assertEqual(frame[r2][col2], ch2)

    def test_build_frame_does_not_mutate_base_grid(self):
        original = copy.deepcopy(banner.BASE_GRID)
        banner._build_frame(banner.TAIL_FRAMES[2])
        self.assertEqual(banner.BASE_GRID, original)

    def test_transparent_pixel_pairs_render_as_plain_space(self):
        self.assertEqual(banner._half_block(".", "."), " ")

    def test_pingpong_swings_back_through_the_middle_not_a_snap(self):
        result = banner._pingpong([0, 1, 2])
        self.assertEqual(result, [0, 1, 2, 1])

    def test_pingpong_repeated_never_jumps_directly_from_last_to_first(self):
        sequence = banner._pingpong(banner.TAIL_FRAMES) * 3
        for i in range(len(sequence) - 1):
            # consecutive entries must be adjacent positions in TAIL_FRAMES
            # (or the same), never a jump from the last frame to the first
            a, b = sequence[i], sequence[i + 1]
            ia, ib = banner.TAIL_FRAMES.index(a), banner.TAIL_FRAMES.index(b)
            self.assertLessEqual(abs(ia - ib), 1)

    def test_render_animated_falls_back_to_static_when_not_a_live_tty(self):
        # test runner's stdout is never a real tty, so this must not hang
        # in a sleep loop or attempt cursor-movement redraws -- it should
        # just behave like render().
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            banner.render_animated(cycles=5, delay=1.0)
        self.assertIn("claude-orchestrator", buf.getvalue())

    def test_enabled_reflects_setting(self):
        settings.set_value("banner", True)
        self.assertTrue(banner.enabled())
        settings.set_value("banner", False)
        self.assertFalse(banner.enabled())


class DashboardTests(OrcTestCase):
    def _make_skill(self, name):
        d = config.CLAUDE_SKILLS / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("x")

    def test_terminal_render_with_no_data_does_not_crash(self):
        text = dashboard.render_terminal(color=False)
        self.assertIn("claude-orchestrator", text)
        self.assertIn("(not set)", text)  # no identity set yet
        self.assertIn("no runs logged yet", text)

    def test_terminal_render_reflects_real_state(self):
        identity.set_identity("mine")
        self.write_memory_file("proj-a", "a.md", "Alpha", "project", "body")
        memory.sync()
        self._make_skill("demo")
        skills.adopt("demo")
        agentlog.log_run("did a thing", "success", notes="test note")

        text = dashboard.render_terminal(color=False)
        self.assertIn("mine", text)
        self.assertIn("did a thing", text)
        self.assertIn("demo", text)
        self.assertIn("enabled", text)

    def test_terminal_render_color_mode_wraps_with_ansi_codes(self):
        colored = dashboard.render_terminal(color=True)
        plain = dashboard.render_terminal(color=False)
        self.assertIn("\033[", colored)
        self.assertNotIn("\033[", plain)
        # stripping ANSI-heavy formatting still leaves the same substance
        self.assertIn("claude-orchestrator", colored)

    def test_html_export_with_no_data_does_not_crash(self):
        path = dashboard.generate_html(out_path=self.root / "out.html")
        self.assertTrue(path.exists())
        text = path.read_text()
        self.assertIn("claude-orchestrator", text)
        self.assertIn("(not set)", text)

    def test_color_always_forces_ansi_even_when_not_a_tty(self):
        text = dashboard.render_terminal(color=None)  # test runner stdout isn't a tty -> plain
        self.assertNotIn("\033[", text)
        settings.set_value("color", "always")
        forced = dashboard.render_terminal(color=None)
        self.assertIn("\033[", forced)

    def test_theme_override_changes_gradient_without_persisting(self):
        default_text = dashboard.render_terminal(color=True, theme_name="amber")
        ocean_text = dashboard.render_terminal(color=True, theme_name="ocean")
        self.assertNotEqual(default_text, ocean_text)
        self.assertEqual(settings.get("theme"), "amber")  # override didn't persist

    def test_usage_days_override(self):
        self.write_transcript("proj-a", "s1", [
            self._usage_msg(f"2026-09-{d:02d}T00:00:00Z") for d in range(10, 15)
        ])
        text = dashboard.render_terminal(color=False, usage_days=3)
        self.assertIn("last 3 days", text)
        self.assertNotIn("2026-09-10", text)  # outside the 3-day window
        self.assertIn("2026-09-14", text)

    def _usage_msg(self, ts):
        return {"timestamp": ts, "message": {"model": "claude-opus-5",
                "usage": {"input_tokens": 1, "output_tokens": 1}}}

    def test_icons_off_hides_bullet_and_check_marks(self):
        self._make_skill("demo")
        skills.adopt("demo")
        with_icons = dashboard.render_terminal(color=False, icons=True)
        without_icons = dashboard.render_terminal(color=False, icons=False)
        self.assertIn("●", with_icons)
        self.assertNotIn("●", without_icons)

    def test_html_export_reflects_real_state(self):
        identity.set_identity("mine")
        self._make_skill("demo")
        skills.adopt("demo")
        agentlog.log_run("did a thing", "success", notes="test note")

        path = dashboard.generate_html(out_path=self.root / "out2.html")
        text = path.read_text()
        self.assertIn("mine", text)
        self.assertIn("did a thing", text)
        self.assertIn("demo", text)


class InitTests(OrcTestCase):
    def test_init_creates_data_dirs_and_git_repo(self):
        result = init.run()
        self.assertFalse(result["already_initialized"])
        self.assertTrue((config.DATA_ROOT / ".git").exists())
        self.assertTrue((config.DATA_ROOT / "memory").is_dir())
        self.assertTrue((config.DATA_ROOT / "skills-registry" / "store").is_dir())
        self.assertTrue((config.DATA_ROOT / "agent-log").is_dir())

    def test_init_makes_an_initial_commit(self):
        init.run()
        log = subprocess.run(
            ["git", "-C", str(config.DATA_ROOT), "log", "--oneline"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("orc init", log.stdout)

    def test_init_twice_is_a_safe_no_op(self):
        init.run()
        second = init.run()
        self.assertTrue(second["already_initialized"])


class CliErrorHandlingTests(OrcTestCase):
    """Exercises the argparse/cli.py layer directly, not just the underlying
    module functions — a real bug slipped through here: skills.py raised
    clean ValueErrors that were fully tested, but the cli.py command
    handlers for adopt/install/enable/disable never caught them, so the
    CLI crashed with a raw traceback on totally expected inputs (a name
    that isn't installed, a skill that's already adopted, etc.), while
    `orc config set` had already been fixed to handle exactly this."""

    def _run(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_main(argv)  # must not raise
        return out.getvalue()

    def test_skill_adopt_missing_directory_prints_clean_error(self):
        text = self._run(["skill", "adopt", "does-not-exist"])
        self.assertIn("error:", text)

    def test_skill_enable_unmanaged_prints_clean_error(self):
        text = self._run(["skill", "enable", "never-adopted"])
        self.assertIn("error:", text)

    def test_skill_disable_unmanaged_prints_clean_error(self):
        text = self._run(["skill", "disable", "never-adopted"])
        self.assertIn("error:", text)

    def test_skill_adopt_already_symlinked_prints_clean_error(self):
        d = config.CLAUDE_SKILLS / "dup"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("x")
        self._run(["skill", "adopt", "dup"])
        text = self._run(["skill", "adopt", "dup"])  # second adopt must not crash
        self.assertIn("error:", text)

    def test_config_set_bad_value_prints_clean_error_via_cli(self):
        text = self._run(["config", "set", "usage_days", "not-a-number"])
        self.assertIn("error:", text)


if __name__ == "__main__":
    unittest.main()
