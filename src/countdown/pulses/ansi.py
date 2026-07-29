"""ANSI sine-wave pulse animation.

Renders one frame of per-cell intensity driven by a radial sine wave. The
outer run_countdown loop handles timing and keypress checks.
"""

import math
from time import time

from ..display import FULL_CLEAR_HOME, HOME, centered_frame, get_terminal_size

# 8 brightness levels cycled by the wave (dim -> bright)
_INTENSITY_STYLES = [
    "\x1b[2m\x1b[30m",  # dim black
    "\x1b[2m\x1b[37m",  # dim white
    "\x1b[0m\x1b[37m",  # normal white
    "\x1b[0m\x1b[97m",  # bright white
    "\x1b[1m\x1b[97m",  # bold bright white
    "\x1b[1m\x1b[95m",  # bold magenta
    "\x1b[0m\x1b[35m",  # magenta
    "\x1b[2m\x1b[35m",  # dim magenta
]
_RESET = "\x1b[0m"
_START = [None]


def style_lines(lines, phase):
    """Return styled copies of ``lines`` with per-cell sine-wave intensity.

    Uses the visual width of each line (trailing whitespace preserved) as the
    radial-wave x-axis. The wave's center sits on the visual midpoint of the
    content box, so the brightest cell is centered on the glyph cluster.
    """
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
            intensity = math.sin(phase - ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 * 0.6)
            level = int((intensity + 1) / 2 * (len(_INTENSITY_STYLES) - 1))
            level = max(0, min(len(_INTENSITY_STYLES) - 1, level))
            styled.append(_INTENSITY_STYLES[level] + ch + _RESET)
        body.append("".join(styled).rstrip())
    return body


def build_frame(lines, phase):
    """Render glyphs with per-cell intensity from a radial sine wave.

    Returns the centered frame as a string (no CLEAR prefix, no HOME suffix).
    """
    term_width, term_height = get_terminal_size()
    return centered_frame(style_lines(lines, phase), term_width, term_height)


def pulse_ansi(lines):
    """Render one frame of radial sine-wave pulse. Returns None (prints directly)."""
    if _START[0] is None:
        _START[0] = time()
    phase = (time() - _START[0]) * 3
    print(FULL_CLEAR_HOME + build_frame(lines, phase) + HOME, flush=True, end="")


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
