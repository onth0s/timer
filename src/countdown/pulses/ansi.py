"""ANSI sine-wave pulse animation.

Renders one frame of per-cell intensity driven by a radial sine wave. The
outer run_countdown loop handles timing and keypress checks.
"""

import math
from shutil import get_terminal_size
from time import time

from ..display import CLEAR

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


def build_frame(lines, phase):
    """Render glyphs with per-cell intensity from a radial sine wave.

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
            intensity = math.sin(phase - ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 * 0.6)
            level = int((intensity + 1) / 2 * (len(_INTENSITY_STYLES) - 1))
            level = max(0, min(len(_INTENSITY_STYLES) - 1, level))
            styled.append(_INTENSITY_STYLES[level] + ch + _RESET)
        body.append(prefix + "".join(styled))

    vertical_pad = "\n" * vertical_padding
    return vertical_pad + "\n".join(body)


def pulse_ansi(lines):
    """Render one frame of radial sine-wave pulse. Returns None (prints directly)."""
    if _START[0] is None:
        _START[0] = time()
    phase = (time() - _START[0]) * 3
    print(CLEAR + build_frame(lines, phase), flush=True, end="")


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
