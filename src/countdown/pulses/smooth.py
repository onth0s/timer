"""Sine-wave driven pulse animation.

Per-cell brightness modulated by a radial sine wave. Each cell's brightness
oscillates smoothly through 3 levels creating a visible breathing pulse.
"""

import math
from shutil import get_terminal_size
from time import time

from ..display import CLEAR

_BRIGHTNESS_STYLES = [
    "\x1b[2m",  # dim
    "\x1b[0m",  # normal
    "\x1b[1m",  # bold
]
_RESET = "\x1b[0m"
_START = [None]


def build_frame(lines, phase):
    """Render glyphs with per-cell brightness from a radial sine wave.

    Returns the frame as a string with ANSI escape codes (no CLEAR prefix).
    """
    term_width, term_height = get_terminal_size()
    content_height = len(lines)
    vertical_padding = max(0, (term_height - content_height) // 2)
    max_line_width = max(len(line) for line in lines)
    horizontal_padding = max(0, (term_width - max_line_width) // 2)

    cx = max_line_width / 2
    cy = content_height / 2

    body = []
    for y, line in enumerate(lines):
        prefix = " " * horizontal_padding
        styled = []
        for x, ch in enumerate(line):
            if ch == " ":
                styled.append(ch)
                continue
            distance = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            wave = math.sin(phase - distance * 0.7)
            level = int((wave + 1) / 2 * len(_BRIGHTNESS_STYLES))
            level = max(0, min(len(_BRIGHTNESS_STYLES) - 1, level))
            styled.append(_BRIGHTNESS_STYLES[level] + ch + _RESET)
        body.append(prefix + "".join(styled))

    vertical_pad = "\n" * vertical_padding
    return vertical_pad + "\n".join(body)


def pulse_smooth(lines):
    """Render one frame of radial sine-wave pulse."""
    if _START[0] is None:
        _START[0] = time()
    phase = (time() - _START[0]) * 2.5
    print(CLEAR + build_frame(lines, phase), flush=True, end="")


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
