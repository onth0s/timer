"""drawille braille canvas pulse driven by interfering sine waves.

Each pixel's position is offset by the sum of three orthogonal sine waves,
creating a proper visible wave pattern. Renders one frame per call.
"""

import math
from shutil import get_terminal_size
from time import time

from drawille import Canvas

from ..display import CLEAR


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


def _centered_frame(frame, glyph_lines):
    """Pad the braille frame so the glyphs sit centered in the terminal."""
    term_width, term_height = get_terminal_size()
    glyph_width = max(len(line) for line in glyph_lines)
    # Use the actual frame row count (displacement can extend the canvas)
    braille_width = (glyph_width + 1) // 2
    braille_rows = len(frame.splitlines())
    vertical_padding = max(0, (term_height - braille_rows) // 2)
    horizontal_padding = max(0, (term_width - braille_width) // 2)
    vertical_pad = "\n" * vertical_padding
    # Strip trailing \r from each line (drawille Canvas emits \r\n)
    indented = "\n".join(
        " " * horizontal_padding + line.rstrip("\r")
        for line in frame.splitlines()
    )
    return vertical_pad + indented


_BASE_PIXELS_CACHE: dict = {}


def _get_base_pixels(lines):
    """Memoize base pixel positions for these lines."""
    key = tuple(lines)
    if key not in _BASE_PIXELS_CACHE:
        _BASE_PIXELS_CACHE[key] = _glyph_to_pixels(lines)
    return _BASE_PIXELS_CACHE[key]


_START = [None]


def build_frame(lines, phase):
    """Render braille frame with pixels displaced by interfering sine waves.

    Returns the centered frame as a string (no CLEAR prefix).
    """
    base_pixels = _get_base_pixels(lines)
    canvas = Canvas()
    t = phase

    for px, py in base_pixels:
        # Small sub-pixel displacement so canvas bounds don't grow
        dx = 0.5 * math.sin(t * 3 + py * 0.4) + 0.5 * math.cos(t * 1.7 + px * 0.2)
        dy = 0.5 * math.cos(t * 2.5 + px * 0.3) + 0.5 * math.sin(t * 1.3 + py * 0.5)
        canvas.set(int(px + dx), int(py + dy))

    return _centered_frame(canvas.frame(), lines)


def pulse_drawille(lines):
    """Render one frame: pixels displaced by interfering sine waves."""
    if _START[0] is None:
        _START[0] = time()
    phase = time() - _START[0]
    print(CLEAR + build_frame(lines, phase), flush=True, end="")


def reset_state():
    """Reset pulse phase (for tests)."""
    _START[0] = None
