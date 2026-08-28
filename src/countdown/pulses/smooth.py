"""Sine-wave driven pulse animation.

Per-cell brightness modulated by a radial sine wave. Each cell's brightness
oscillates smoothly through 3 levels creating a visible breathing pulse.
"""

import math
from time import time

from ..display import FULL_CLEAR_HOME, HOME, centered_frame, get_terminal_size

_BRIGHTNESS_STYLES = [
    "\x1b[2m",  # dim
    "\x1b[0m",  # normal
    "\x1b[1m",  # bold
]
_RESET = "\x1b[0m"
_START = [None]


def style_lines(lines, phase):
    """Return styled copies of ``lines`` with radial-wave brightness per cell."""
    content_height = len(lines)
    content_widths = [len(line.rstrip()) for line in lines]
    max_width = max(content_widths) if content_widths else 0

    cx = max_width / 2
    cy = content_height / 2

    body = []
    for y, line in enumerate(lines):
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
        body.append("".join(styled).rstrip())
    return body


def build_frame(lines, phase):
    """Render glyphs with per-cell brightness from a radial sine wave.

    Returns the centered frame as a string (no CLEAR prefix, no HOME suffix).
    """
    term_width, term_height = get_terminal_size()
    return centered_frame(style_lines(lines, phase), term_width, term_height)


def pulse_smooth(lines):
    """Render one frame of radial sine-wave pulse."""
    if _START[0] is None:
        _START[0] = time()
    phase = (time() - _START[0]) * 2.5
    print(
        FULL_CLEAR_HOME + build_frame(lines, phase) + HOME, flush=True, end=""
    )


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
