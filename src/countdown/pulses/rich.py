"""Rich Live sine-wave pulse animation.

Each glyph cell gets its own color computed from a radial sine wave emanating
from the center of the display. The hue cycles over time and the wave's
amplitude modulates brightness. Returns a Rich Group renderable so run_countdown
can drive the Live display with manual refreshes.
"""

import math
from time import time

from rich.console import Group
from rich.text import Text

from ..display import HOME, get_terminal_size
from ._wave import hsl_to_rgb, radial_wave

_START = [None]


def _style_row(line, y, cx, cy, hue):
    """Style a single glyph line as a Rich Text with per-cell RGB color.

    Uses the visible cell width (after stripping trailing space) so the radial
    wave centerlines land on the actual visual midpoint of the glyph cluster.
    """
    styled = Text()
    for x, ch in enumerate(line):
        if ch == " ":
            styled.append(ch)
            continue
        intensity = radial_wave(x, y, cx, cy, hue / 360 * (2 * math.pi), frequency=0.5)
        lightness = 0.4 + 0.4 * (intensity + 1) / 2
        r, g, b = hsl_to_rgb(hue, 0.9, lightness)
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        bold = intensity > 0.4
        style = f"{'bold ' if bold else ''}{hex_color}"
        styled.append(ch, style=style)
    return styled


def _h_pad(count):
    """Return a Text of ``count`` spaces."""
    return Text(" " * count)


def build_wave_renderable(lines, phase, term_width=None, term_height=None):
    """Return a Rich Group of styled Text rows for the wave frame.

    Each row is a distinct Text so ``Live`` repaints the full grid cleanly
    without inheriting stale positions from the previous frame. When
    ``term_width`` is given the rows are horizontally centered via leading
    padding so the glyph block sits in the middle of the terminal.
    """
    content_height = len(lines)
    content_widths = [len(line.rstrip()) for line in lines]
    max_width = max(content_widths) if content_widths else 0

    cx = max_width / 2
    cy = content_height / 2
    hue = (phase / (2 * math.pi)) * 360 % 360

    if term_width is not None:
        h_pad = max(0, (term_width - max_width) // 2)
        pad = Text(" " * h_pad)
    else:
        pad = None

    if pad:
        rows = [
            Text.assemble(pad, _style_row(line, y, cx, cy, hue))
            for y, line in enumerate(lines)
        ]
    else:
        rows = [
            _style_row(line, y, cx, cy, hue)
            for y, line in enumerate(lines)
        ]

    if term_height is not None:
        v_pad = max(0, (term_height - content_height) // 2)
        if v_pad:
            v_pad_rows = [Text("") for _ in range(v_pad)]
            rows = [*v_pad_rows, *rows]
    return Group(*rows)


def build_frame(lines, phase):
    """Render frame as an ANSI-escaped string (for showcase / stdout printing).

    Uses a private Rich Console to capture the Group renderable as ANSI codes.
    force_terminal=True ensures ANSI escapes are emitted even when stdout isn't
    a real terminal; we capture to a private buffer to avoid double-output
    when the caller also prints the result.
    """
    import io

    from rich.console import Console

    term_width, term_height = get_terminal_size()
    renderable = build_wave_renderable(lines, phase, term_width, term_height)

    buf = io.StringIO()
    console = Console(
        file=buf,
        record=True,
        force_terminal=True,
        width=term_width,
        height=term_height,
        color_system="truecolor",
    )
    console.print(renderable)
    return console.export_text(styles=True)


def _render_content(lines, phase, tw):
    """Return ANSI string of styled content (no vertical padding)."""
    import io

    from rich.console import Console

    renderable = build_wave_renderable(lines, phase, term_width=tw, term_height=None)
    buf = io.StringIO()
    console = Console(
        file=buf,
        record=True,
        force_terminal=True,
        width=tw,
        color_system="truecolor",
    )
    console.print(renderable)
    return console.export_text(styles=True)


def pulse_rich(lines):
    """Render one frame of radial sine-wave pulse. Prints directly to stdout."""
    if _START[0] is None:
        _START[0] = time()
    phase = (time() - _START[0]) * 4
    tw, th = get_terminal_size()
    ch = len(lines)
    v_pad = max(0, (th - ch) // 2)
    # Position below the blank padding, clear content area, print styled content
    print(HOME + "\n" * v_pad + "\033[J" + _render_content(lines, phase, tw) + HOME, flush=True, end="")


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
