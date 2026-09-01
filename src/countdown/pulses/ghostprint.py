"""CRT flicker pulse with sine-wave brightness + random character glitches.

Each cell's brightness oscillates with a sine wave, and a small fraction of
cells swap to glitch characters per frame to simulate CRT interference.
"""

import math
import random

from ..display import centered_frame, get_terminal_size
from .base import make_pulse

_GLITCH_CHARS = "\u2588\u2593\u2592\u2591\u2580#@&$%*"


def style_lines(
    lines: list[str], phase: float, glitch_rate: float = 0.08
) -> list[str]:
    """Return styled copies of ``lines`` with sine-wave brightness + glitches."""
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
            wave = math.sin(phase * 4 - distance * 0.6)
            display_ch = (
                random.choice(_GLITCH_CHARS)
                if random.random() < glitch_rate
                else ch
            )
            if wave > 0.3:
                styled.append(f"\x1b[1m\x1b[95m{display_ch}\x1b[0m")
            elif wave > -0.3:
                styled.append(f"\x1b[95m{display_ch}\x1b[0m")
            else:
                styled.append(f"\x1b[2m\x1b[35m{display_ch}\x1b[0m")
        body.append("".join(styled).rstrip())
    return body


def build_frame(
    lines: list[str], phase: float, glitch_rate: float = 0.08
) -> str:
    """Render glyphs with sine-wave brightness + occasional glitch swaps.

    Returns the centered frame as a string (no CLEAR prefix, no HOME suffix).
    """
    term_width, term_height = get_terminal_size()
    return centered_frame(
        style_lines(lines, phase, glitch_rate=glitch_rate),
        term_width,
        term_height,
    )


pulse_ghostprint, reset_state = make_pulse(
    build_frame,
    doc="Render one frame of CRT flicker pulse.",
)

__all__ = ["build_frame", "pulse_ghostprint", "reset_state", "style_lines"]
