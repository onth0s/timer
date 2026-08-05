"""Sine-wave pulse animation with per-cell colour via ANSI 256-color escapes.

Each glyph cell gets its own colour from a radial sine wave emanating from the
center of the display. Hue cycles over time; brightness oscillates with wave
intensity.  Uses the 6×6×6 colour cube (indexes 16-231) so each escape is only
~10 bytes versus ~20 for truecolor.

Renders direct ANSI escape sequences — no Rich Console in the hot path. The
frame pipeline is IDENTICAL to ansi.py / smooth.py:
    FULL_CLEAR_HOME + centered_frame(style_lines(...)) + HOME
"""

import math
from time import time

from ..display import FULL_CLEAR_HOME, HOME, centered_frame, get_terminal_size
from ._wave import hsl_to_rgb, radial_wave

_START = [None]
_RESET = "\033[0m"


def _color_seq(idx):
    """256-colour SGR escape."""
    return f"\033[38;5;{idx}m"


def _idx_for_cell(x, y, cx, cy, hue):
    """Return a 256-colour index for cell at (x, y) using the 6×6×6 cube.

    Index range 16-231 gives 6 levels per channel — enough variation to
    keep the radial wave looking rich while keeping escapes short.
    """
    intensity = radial_wave(x, y, cx, cy, hue / 360 * (2 * math.pi), frequency=0.5)
    lightness = 0.4 + 0.4 * (intensity + 1) / 2
    r, g, b = hsl_to_rgb(hue, 0.9, lightness)
    ri = min(5, int(r / 43))
    gi = min(5, int(g / 43))
    bi = min(5, int(b / 43))
    return 16 + ri * 36 + gi * 6 + bi


def style_lines(lines, phase):
    """Return styled copies of ``lines`` with per-cell 256-colour ANSI escapes.

    Consecutive cells with the same colour index share a single ANSI code.
    Reset only at the end of each line — between colour runs we just switch.
    """
    content_height = len(lines)
    content_widths = [len(line.rstrip()) for line in lines]
    max_width = max(content_widths) if content_widths else 0

    cx = max_width / 2
    cy = content_height / 2
    hue = (phase / (2 * math.pi)) * 360 % 360

    body = []
    for y, line in enumerate(lines):
        styled = []
        run = []
        run_idx = None
        has_colour = False
        for x, ch in enumerate(line):
            if ch == " ":
                if run:
                    styled.append(f"{_color_seq(run_idx)}")
                    styled.append("".join(run))
                    run = []
                    run_idx = None
                styled.append(ch)
                continue
            idx = _idx_for_cell(x, y, cx, cy, hue)
            if idx == run_idx:
                run.append(ch)
            else:
                if run:
                    styled.append(f"{_color_seq(run_idx)}")
                    styled.append("".join(run))
                run = [ch]
                run_idx = idx
                has_colour = True
        if run:
            styled.append(f"{_color_seq(run_idx)}")
            styled.append("".join(run))
        # Strip trailing spaces BEFORE the reset escape, otherwise they are
        # shielded from rstrip() by the trailing "\033[0m" and inflate the
        # visible width by one column, shifting the frame off-center.
        while styled and styled[-1] == " ":
            styled.pop()
        if has_colour:
            styled.append(_RESET)
        body.append("".join(styled))
    return body


def build_frame(lines, phase):
    """Render glyphs with per-cell 256-colour from a radial sine wave.

    Returns the centered frame as a string (no CLEAR prefix, no HOME suffix).
    Matches the pattern of ansi.py / smooth.py build_frame.
    """
    term_width, term_height = get_terminal_size()
    return centered_frame(style_lines(lines, phase), term_width, term_height)


def pulse_rich(lines):
    """Render one frame of radial sine-wave pulse. Prints directly to stdout."""
    if _START[0] is None:
        _START[0] = time()
    phase = (time() - _START[0]) * 4
    print(FULL_CLEAR_HOME + build_frame(lines, phase) + HOME, flush=True, end="")


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None


# ---------------------------------------------------------------------------
# Legacy Rich-object API — kept for tests that exercise build_wave_renderable
# and the Text-based helpers.  Not used by the pulse-hot-path above.
# ---------------------------------------------------------------------------

from rich.console import Group  # noqa: E402
from rich.text import Text  # noqa: E402


def _style_row(line, y, cx, cy, hue):
    """Style a single glyph line as a Rich Text with per-cell RGB color."""
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
