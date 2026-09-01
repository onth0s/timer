"""Sine-wave driven pulse animation.

Per-cell brightness modulated by a radial sine wave. Each cell's brightness
oscillates smoothly through 3 levels creating a visible breathing pulse.
"""

import math

from ..display import centered_frame, get_terminal_size
from .base import make_pulse

_BRIGHTNESS_STYLES = [
    "\x1b[2m",  # dim
    "\x1b[0m",  # normal
    "\x1b[1m",  # bold
]
_RESET = "\x1b[0m"


def style_lines(lines: list[str], phase: float) -> list[str]:
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


def build_frame(lines: list[str], phase: float) -> str:
    """Render glyphs with per-cell brightness from a radial sine wave.

    Returns the centered frame as a string (no CLEAR prefix, no HOME suffix).
    """
    term_width, term_height = get_terminal_size()
    return centered_frame(style_lines(lines, phase), term_width, term_height)


pulse_smooth, reset_state = make_pulse(
    build_frame,
    phase_scale=2.5,
    doc="Render one frame of radial sine-wave pulse.",
)

__all__ = ["build_frame", "pulse_smooth", "reset_state", "style_lines"]
