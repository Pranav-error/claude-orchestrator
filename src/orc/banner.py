"""Startup banner — a small colored mark plus name/version, the same idea
other AI CLIs show on launch (Claude Code's own icon-and-version header,
Gemini CLI's compact ASCII icon). Purely cosmetic: toggle it off with
`orc config set banner false` for a quieter start.
"""

from . import __version__, settings as settings_mod
from .dashboard import BOLD, DIM, RESET, _resolve_color

# A small abstract hub mark (an orchestrator sits at the center of several
# things) rather than literal letters — reads at a glance, doesn't compete
# with the text next to it.
MARK = [
    "◤   ◥",
    "  ◆  ",
    "◣   ◢",
]


def render(color: bool = None, theme_name: str = None) -> str:
    color = _resolve_color(color)
    theme = settings_mod.theme(theme_name)
    gradient = theme["gradient"]

    def c(code, text):
        return f"{code}{text}{RESET}" if (color and code) else text

    def grad(idx: int) -> str:
        code = gradient[min(idx, len(gradient) - 1)]
        return f"\033[38;5;{code}m" if code != "" else ""

    text_lines = [
        c(BOLD, "claude-orchestrator"),
        c(DIM, f"v{__version__} · orc"),
        c(DIM, "a personal control plane for Claude Code"),
    ]

    rows = []
    for i, (mark_row, text_row) in enumerate(zip(MARK, text_lines)):
        rows.append(f"{c(grad(1 + i * 2), mark_row)}  {text_row}")
    return "\n".join(rows)


def enabled() -> bool:
    return bool(settings_mod.get("banner"))
