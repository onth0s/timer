"""drawille braille canvas pulse driven by interfering sine waves.

Each pixel's position is offset by the sum of three orthogonal sine waves,
creating a proper visible wave pattern. Renders one frame per call.
"""

import math
from time import time

from drawille import Canvas

from ..display import FULL_CLEAR_HOME, HOME, get_terminal_size


def _glyph_to_pixels(lines):
    """Convert glyph lines to a set of (x,y) pixel positions."""
    pixels = set()
    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            if ch != " ":
                for dy in range(4):
                    for dx in range(2):
                        pixels.add((x * 2 + dx, y * 4 + dy))
    return pixels


_BASE_PIXELS_CACHE: dict = {}


def _get_base_pixels(lines):
    """Memoize base pixel positions for these lines."""
    key = tuple(lines)
    if key not in _BASE_PIXELS_CACHE:
        _BASE_PIXELS_CACHE[key] = _glyph_to_pixels(lines)
    return _BASE_PIXELS_CACHE[key]


_START = [None]


def _render_braille(lines, phase):
    """Build a drawille Canvas from ``lines`` displaced by sine waves.

    Returns the rendered frame as a list of strings (one per braille row).
    Rows are stripped of carriage returns and trailing whitespace so the
    visible width matches the actual cell width.
    """
    base_pixels = _get_base_pixels(lines)
    canvas = Canvas()
    t = phase

    for px, py in base_pixels:
        dx = 0.5 * math.sin(t * 3 + py * 0.4) + 0.5 * math.cos(
            t * 1.7 + px * 0.2
        )
        dy = 0.5 * math.cos(t * 2.5 + px * 0.3) + 0.5 * math.sin(
            t * 1.3 + py * 0.5
        )
        canvas.set(int(px + dx), int(py + dy))

    raw_rows = canvas.frame().splitlines()
    return [row.rstrip("\r").rstrip() for row in raw_rows]


def _centered_braille_frame(rows, glyph_lines):
    """Pad the braille frame so the glyphs sit centered in the terminal."""
    from ..display import centered_frame

    term_width, term_height = get_terminal_size()
    visible_rows = [row for row in rows if row]
    if not visible_rows:
        return centered_frame([""], term_width, term_height)
    return centered_frame(visible_rows, term_width, term_height)


def build_frame(lines, phase):
    """Render braille frame with pixels displaced by interfering sine waves.

    Returns the centered frame as a string (no CLEAR prefix, no HOME suffix).
    """
    return _centered_braille_frame(_render_braille(lines, phase), lines)


def pulse_drawille(lines):
    """Render one frame: pixels displaced by interfering sine waves."""
    if _START[0] is None:
        _START[0] = time()
    phase = time() - _START[0]
    print(
        FULL_CLEAR_HOME + build_frame(lines, phase) + HOME, flush=True, end=""
    )


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
