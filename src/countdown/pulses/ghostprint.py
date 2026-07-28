"""CRT flicker pulse with sine-wave brightness + random character glitches.

Each cell's brightness oscillates with a sine wave, and a small fraction of
cells swap to glitch characters per frame to simulate CRT interference.
"""

import math
import random
from shutil import get_terminal_size
from time import time

from ..display import CLEAR

_GLITCH_CHARS = "\u2588\u2593\u2592\u2591\u2580#@&$%*"
_START = [None]


def build_frame(lines, phase, glitch_rate=0.08):
    """Render glyphs with sine-wave brightness + occasional glitch swaps.

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
            wave = math.sin(phase * 4 - distance * 0.6)
            if random.random() < glitch_rate:
                ch = random.choice(_GLITCH_CHARS)
            if wave > 0.3:
                styled.append(f"\x1b[1m\x1b[95m{ch}\x1b[0m")
            elif wave > -0.3:
                styled.append(f"\x1b[95m{ch}\x1b[0m")
            else:
                styled.append(f"\x1b[2m\x1b[35m{ch}\x1b[0m")
        body.append(prefix + "".join(styled))

    vertical_pad = "\n" * vertical_padding
    return vertical_pad + "\n".join(body)


def pulse_ghostprint(lines):
    """Render one frame of CRT flicker pulse."""
    if _START[0] is None:
        _START[0] = time()
    phase = time() - _START[0]
    print(CLEAR + build_frame(lines, phase), flush=True, end="")


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
