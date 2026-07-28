"""Rich Live sine-wave pulse animation.

Each glyph cell gets its own color computed from a radial sine wave emanating
from the center of the display. The hue cycles over time and the wave's
amplitude modulates brightness. Returns a Rich Text renderable so run_countdown
can drive the Live display.
"""

import math
from shutil import get_terminal_size
from time import time

from rich.console import Console
from rich.text import Text

from ._wave import hsl_to_rgb, radial_wave

_START = [None]


def _build_wave_text(lines, phase):
    """Build a Rich Text with per-cell RGB color from a radial sine wave."""
    term_width, term_height = get_terminal_size()
    content_height = len(lines)
    vertical_padding = max(0, (term_height - content_height) // 2)
    max_line_width = max(len(line) for line in lines)
    horizontal_padding = max(0, (term_width - max_line_width) // 2)
    pad = " " * horizontal_padding

    cx = max_line_width / 2
    cy = content_height / 2
    hue = (phase / (2 * math.pi)) * 360 % 360

    body_parts = []
    for y, line in enumerate(lines):
        if body_parts:
            body_parts.append("\n")
        styled = []
        for x, ch in enumerate(line):
            if ch == " ":
                styled.append(" ")
                continue
            intensity = radial_wave(x, y, cx, cy, phase, frequency=0.5)
            lightness = 0.4 + 0.4 * (intensity + 1) / 2
            r, g, b = hsl_to_rgb(hue, 0.9, lightness)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            bold = intensity > 0.4
            style = f"{'bold ' if bold else ''}{hex_color}"
            styled.append(f"[{style}]{ch}[/]")
        body_parts.append(pad + "".join(styled))

    body = "".join(body_parts)
    if vertical_padding:
        body = "\n" * vertical_padding + body
    return Text.from_markup(body)


def build_frame(lines, phase):
    """Render frame as an ANSI-escaped string (for showcase / stdout printing).

    Uses a private Rich Console to capture the Text renderable as ANSI codes.
    force_terminal=True ensures ANSI escapes are emitted even when stdout isn't
    a real terminal; we capture to a private buffer to avoid double-output
    when the caller also prints the result.
    """
    term_width, _ = get_terminal_size()
    text = _build_wave_text(lines, phase)
    import io

    buf = io.StringIO()
    console = Console(
        file=buf,
        record=True,
        force_terminal=True,
        width=term_width,
        color_system="truecolor",
    )
    console.print(text)
    return console.export_text(styles=True)


def pulse_rich(lines):
    """Render one frame of radial sine-wave pulse. Returns a Rich Text renderable."""
    if _START[0] is None:
        _START[0] = time()
    phase = (time() - _START[0]) * 4
    return _build_wave_text(lines, phase)


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
