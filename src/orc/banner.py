"""Startup banner — a small pixel-art mark plus name/version, the same
idea other AI CLIs show on launch (Claude Code's own colored icon,
Gemini CLI's compact ASCII icon). Since this tool is literally named
`orc`, the mark is a small green orc face rather than an abstract shape.

Purely cosmetic: toggle it off with `orc config set banner false`.
"""

from . import __version__, settings as settings_mod
from .dashboard import BOLD, DIM, RESET, _resolve_color

# 7 wide x 8 tall pixel grid, legend below. Rendered two rows at a time
# using the Unicode half-block trick (▀ = top half foreground, bottom
# half background) to get roughly square pixels out of terminal cells
# that are normally about twice as tall as they are wide.
PIXELS = [
    ".OOOOO.",
    "OSSSSSO",
    "OSESESO",
    "OSSSSSO",
    "OSDDDSO",
    "OTSSSTO",
    "OTSSSTO",
    ".OSSSO.",
]

# Fixed brand colors, independent of the user's dashboard theme — a logo
# should stay recognizable, the way Claude's icon is always orange and
# Gemini's is always blue, regardless of the terminal's color scheme.
PALETTE = {
    ".": None,     # transparent — lets the terminal's own background show
    "O": 233,      # near-black outline
    "S": 28,       # skin (green)
    "D": 22,       # skin shadow (darker green)
    "E": 196,      # eyes (red)
    "T": 230,      # tusks (cream)
}


def _half_block(top_ch: str, bottom_ch: str) -> str:
    top, bottom = PALETTE.get(top_ch), PALETTE.get(bottom_ch)
    if top is None and bottom is None:
        return " "
    if top is not None and bottom is not None:
        return f"\033[38;5;{top}m\033[48;5;{bottom}m▀{RESET}"
    if top is not None:
        return f"\033[38;5;{top}m▀{RESET}"
    return f"\033[38;5;{bottom}m▄{RESET}"


def _face_lines() -> list[str]:
    lines = []
    for i in range(0, len(PIXELS), 2):
        top_row = PIXELS[i]
        bottom_row = PIXELS[i + 1] if i + 1 < len(PIXELS) else "." * len(top_row)
        lines.append("".join(_half_block(t, b) for t, b in zip(top_row, bottom_row)))
    return lines


def render(color: bool = None) -> str:
    color = _resolve_color(color)

    def c(code, text):
        return f"{code}{text}{RESET}" if (color and code) else text

    text_lines = [
        c(BOLD, "claude-orchestrator"),
        c(DIM, f"v{__version__} · orc"),
        c(DIM, "a personal control plane for Claude Code"),
        "",
    ]

    if not color:
        # The pixel art only means anything in color — in plain-text mode
        # (piped, NO_COLOR, non-tty) skip straight to the text, same as
        # the dashboard's own plain fallback.
        return "\n".join(line for line in text_lines if line)

    face = _face_lines()
    rows = [f"{face_row}  {text_row}" for face_row, text_row in zip(face, text_lines)]
    return "\n".join(rows)


def enabled() -> bool:
    return bool(settings_mod.get("banner"))
