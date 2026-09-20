"""Startup banner — a small pixel-art mascot plus name/version, the same
idea other AI CLIs show on launch (Claude Code's own colored icon,
Gemini CLI's compact icon). An original cat silhouette — clean single-tone
shape rather than a detailed face, which is what actually reads well at
this resolution — with a tail that wags to the side when the terminal
supports a live redraw.

Purely cosmetic: toggle it off with `orc config set banner false`.
"""

import copy
import itertools
import sys
import time

from . import __version__, settings as settings_mod
from .dashboard import BOLD, DIM, RESET, _resolve_color

# Ear tips are isolated peaks for the first 3 rows (a real gap between
# them) and only merge into the rounded cranium below that — a previous
# version merged them immediately into a round top and, fairly, just read
# as a piece of fruit with a stem. Separated pointy ears are what actually
# say "cat" at this resolution. Single solid tone, no outline or face.
_HEAD = [
    ".F.......F.",
    ".FF.....FF.",
    ".FFF...FFF.",
    ".FFFFFFFFF.",
    "FFFFFFFFFFF",
    "FFFFFFFFFFF",
    "FFFFFFFFFFF",
    ".FFFFFFFFF.",
    "..FFFFFFF..",
    "...FFFFF...",
    "....FFF....",
    ".....F.....",
]
_TAIL_WORKSPACE = "...."  # 4 transparent columns, prepended to each row —
                           # the tail curls out to the LEFT of the body.

BASE_GRID = [list(_TAIL_WORKSPACE + row) for row in _HEAD]

# The tail's attachment point (where it meets the body) is fixed; only the
# outer segments move across frames, sweeping from tucked-in to extended
# and curled, which is what actually reads as a wag.
_TAIL_BASE = [(7, 3, "F")]
TAIL_FRAMES = [
    [(8, 2, "F"), (9, 1, "F")],              # tucked down
    [(7, 2, "F"), (7, 1, "F"), (7, 0, "F")],  # extended out
    [(6, 2, "F"), (5, 1, "F"), (4, 0, "F")],  # curled up
]

# Fixed brand color, independent of the user's dashboard theme — a logo
# should stay recognizable regardless of the terminal's color scheme.
# A muted brown/tan instead of orange, which read as literal fruit.
PALETTE = {
    ".": None,   # transparent — lets the terminal's own background show
    "F": 137,    # fur (warm tan/brown), the only color in the silhouette
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

    face = _face_lines(_build_frame(TAIL_FRAMES[1]))  # tail extended as the static pose
    rows = [f"{f}  {t}" for f, t in itertools.zip_longest(face, text_lines, fillvalue="")]
    return "\n".join(rows)


def _pingpong(frames: list) -> list:
    """[0, 1, 2] -> [0, 1, 2, 1] so a repeated sequence swings back and
    forth (a real wag) instead of snapping from the last frame straight
    back to the first every cycle."""
    if len(frames) < 3:
        return list(frames)
    return list(frames) + list(frames[-2:0:-1])


def render_animated(cycles: int = 5, delay: float = 0.15) -> None:
    """Prints the wag in place using cursor-up redraws. Only does anything
    live in a real interactive terminal — a captured/non-tty context (a
    pipe, a redirect, Claude's own Bash tool output) can't display a
    redraw animation meaningfully, so it just prints the static banner."""
    color = _resolve_color(None)
    if not (color and sys.stdout.isatty()):
        print(render(color=color))
        return

    text_lines = _text_lines(color=True)
    sequence = _pingpong(TAIL_FRAMES) * cycles
    first = True
    for overlay in sequence:
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
