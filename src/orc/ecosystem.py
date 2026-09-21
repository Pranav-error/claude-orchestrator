"""Surfaces ECOSYSTEM.md (the survey of third-party Claude Code skills) as
`orc ecosystem`, so it's readable from a plain `pip install` too, not just
from a git checkout. The file itself lives under package data
(src/orc/data/ECOSYSTEM.md) so it ships inside the wheel.
"""

import importlib.resources


def text() -> str:
    return importlib.resources.files("orc").joinpath("data", "ECOSYSTEM.md").read_text()
