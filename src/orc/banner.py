"""Startup banner — a small pixel-art mascot plus name/version, the same
idea other AI CLIs show on launch (Claude Code's own colored icon,
Gemini CLI's compact icon, GitHub's Octocat). An original cat design (not
a copy of Octocat), with a tail that actually wiggles when the terminal
supports it.

Purely cosmetic: toggle it off with `orc config set banner false`.
"""

import copy
import itertools
import sys
import time

from . import __version__, settings as settings_mod
from .dashboard import BOLD, DIM, RESET, _resolve_color

# 9x12 head, plus 4 extra columns of "tail workspace" appended to every
# row (all transparent in the base grid) so the tail can extend outside
# the head silhouette and move between frames without resizing anything.
_HEAD = [
    "..O...O..",
    ".OFO.OFO.",
    "OFFFFFFFO",
    "OFEFFFEFO",
    "OFFFFFFFO",
    "OFFFPFFFO",
    "OFFFFFFFO",
    "OFFFFFFFO",
    ".OFFFFFO.",
    "..OFFFO..",
    "...OFO...",
    "....O....",
]
_TAIL_WORKSPACE = "...."  # 4 transparent columns appended to each head row

BASE_GRID = [list(row + _TAIL_WORKSPACE) for row in _HEAD]

# The tail's attachment point is fixed; only the outer two pixels move
# across frames, which is what actually reads as a wag rather than a
# random flicker.
_TAIL_BASE = [(7, 9, "T")]
TAIL_FRAMES = [
    [(6, 10, "T"), (5, 11, "T")],  # tip up
    [(7, 10, "T"), (7, 11, "T")],  # tip out
    [(8, 10, "T"), (9, 11, "T")],  # tip down
]

# Fixed brand colors, independent of the user's dashboard theme — a logo
# should stay recognizable, the way Claude's icon is always orange and
# GitHub's Octocat is always the same palette, regardless of terminal theme.
PALETTE = {
    ".": None,   # transparent — lets the terminal's own background show
    "O": 233,    # near-black outline
    "F": 208,    # fur (orange)
    "T": 172,    # tail (slightly darker orange, reads as a distinct part)
    "E": 34,     # eyes (green)
    "P": 211,    # nose (pink)
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


def _build_frame(tail_overlay: list[tuple[int, int, str]]) -> list[str]:
    grid = copy.deepcopy(BASE_GRID)
    for r, col, ch in _TAIL_BASE + tail_overlay:
        grid[r][col] = ch
    return ["".join(row) for row in grid]


def _face_lines(grid_rows: list[str]) -> list[str]:
    lines = []
    for i in range(0, len(grid_rows), 2):
        top_row = grid_rows[i]
        bottom_row = grid_rows[i + 1] if i + 1 < len(grid_rows) else "." * len(top_row)
        lines.append("".join(_half_block(t, b) for t, b in zip(top_row, bottom_row)))
    return lines


def _text_lines(color: bool):
    def c(code, text):
        return f"{code}{text}{RESET}" if (color and code) else text

    return [
        c(BOLD, "claude-orchestrator"),
        c(DIM, f"v{__version__} · orc"),
        c(DIM, "a personal control plane for Claude Code"),
        "",
    ]


def render(color: bool = None) -> str:
    color = _resolve_color(color)
    text_lines = _text_lines(color)

    if not color:
        # The pixel art only means anything in color — in plain-text mode
        # (piped, NO_COLOR, non-tty) skip straight to the text.
        return "\n".join(line for line in text_lines if line)

    face = _face_lines(_build_frame(TAIL_FRAMES[1]))  # tail "out" as the static pose
    rows = [f"{f}  {t}" for f, t in itertools.zip_longest(face, text_lines, fillvalue="")]
    return "\n".join(rows)


def render_animated(cycles: int = 2, delay: float = 0.12) -> None:
    """Prints the wag in place using cursor-up redraws. Only does anything
    live in a real interactive terminal — a captured/non-tty context (a
    pipe, a redirect, Claude's own Bash tool output) can't display a
    redraw animation meaningfully, so it just prints the static banner."""
    color = _resolve_color(None)
    if not (color and sys.stdout.isatty()):
        print(render(color=color))
        return

    text_lines = _text_lines(color=True)
    first = True
    for _ in range(cycles):
        for overlay in TAIL_FRAMES:
            face = _face_lines(_build_frame(overlay))
            rows = [f"{f}  {t}" for f, t in itertools.zip_longest(face, text_lines, fillvalue="")]
            if not first:
                print(f"\033[{len(rows)}A", end="")
            print("\n".join(rows))
            sys.stdout.flush()
            first = False
            time.sleep(delay)


def enabled() -> bool:
    return bool(settings_mod.get("banner"))
