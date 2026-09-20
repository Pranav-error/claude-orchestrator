# Releasing

## One-time setup (only needed once, before the very first release)

PyPI publishing uses [trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API token is ever stored in this repo or typed into any tool. Instead, PyPI trusts GitHub Actions runs coming specifically from this repo's `publish.yml` workflow. This has to be configured once, by hand, on pypi.org (requires logging into your own PyPI account — not something anyone else can do for you):

1. Log into [pypi.org](https://pypi.org) (create an account first if you don't have one).
2. Go to **Your account → Publishing** ([pypi.org/manage/account/publishing/](https://pypi.org/manage/account/publishing/)).
3. Add a new **pending publisher** with:
   - PyPI project name: `claude-orc`
   - Owner: `Pranav-error`
   - Repository name: `claude-orchestrator`
   - Workflow filename: `publish.yml`
   - Environment name: `pypi`
4. Save. Nothing else to configure — the first tag push that triggers `publish.yml` will claim the project name and publish it.

## Every release after that

1. Decide the new version number ([semver](https://semver.org/): patch for fixes, minor for new features, major for breaking changes).
2. Bump the version in **all three** places (they must agree):
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `.claude-plugin/plugin.json` → `"version": "X.Y.Z"`
   - `.claude-plugin/marketplace.json` → `plugins[0].version`
3. Add an entry to `CHANGELOG.md` under a new `## [X.Y.Z] - YYYY-MM-DD` heading.
4. Run the test suite one more time: `python3 -m unittest discover -s tests -v`
5. Commit: `git commit -m "Release vX.Y.Z"`
6. Tag and push:
   ```bash
   git tag vX.Y.Z
   git push && git push --tags
   ```
7. Pushing the tag triggers `.github/workflows/publish.yml`, which builds and publishes to PyPI automatically. Watch the run under the repo's **Actions** tab.
8. Once published, `pip install --upgrade claude-orchestrator` picks up the new version. The Claude Code plugin marketplace (`.claude-plugin/marketplace.json`) is read live from `main`, so no separate publish step is needed for `/plugin` users — they get the new version next time Claude Code refreshes the marketplace (`claude plugin marketplace update`).

## If a release goes wrong

PyPI does not allow re-uploading a version number once published, even after deleting it. If you botched a release, bump to the next patch version and try again — don't try to reuse the broken version number.
