"""asciimatics sine-wave pulse animation.

Custom Effect that computes per-cell color via a radial sine wave and
re-renders the glyphs to the asciimatics screen each frame.
"""

import math
from time import time

from asciimatics.effects import Effect
from asciimatics.screen import Screen


class SineWaveEffect(Effect):
    """Render glyphs with sine-wave-modulated colors."""

    def __init__(self, screen, lines, y, x_offset, label=None, **kwargs):
        super().__init__(screen, **kwargs)
        self._lines = lines
        self._y = y
        self._x_offset = x_offset
        self._start = time()
        self._label = label

    def reset(self):
        """Reset effect state."""
        self._start = time()

    @property
    def stop_frame(self):
        """No specific end frame (run until duration)."""
        return 0

    def _update(self, frame_no):
        """Render the frame for ``frame_no``."""
        t = time() - self._start
        phase = t * 3
        visible_widths = [len(line.rstrip()) for line in self._lines]
        max_visible = max(visible_widths) if visible_widths else 0
        cx = max_visible / 2
        cy = len(self._lines) / 2
        # Label at top-left
        if self._label:
            self._screen.print_at(
                self._label,
                0,
                0,
                colour=Screen.COLOUR_WHITE,
                attr=Screen.A_BOLD,
            )
        for row, line in enumerate(self._lines):
            for col, ch in enumerate(line.rstrip()):
                if ch == " ":
                    continue
                distance = math.sqrt((col - cx) ** 2 + (row - cy) ** 2)
                wave = math.sin(phase - distance * 0.5)
                if wave > 0.4:
                    colour = Screen.COLOUR_MAGENTA
                    attr = Screen.A_BOLD
                elif wave > 0.0:
                    colour = Screen.COLOUR_WHITE
                    attr = Screen.A_NORMAL
                else:
                    colour = Screen.COLOUR_CYAN
                    attr = Screen.A_NORMAL
                self._screen.print_at(
                    ch,
                    self._x_offset + col,
                    self._y + row,
                    colour=colour,
                    attr=attr,
                )


def _run_screen(lines, duration, label=None):
    """Run the asciimatics pulse for ``duration`` seconds, then exit.

    Polls input with a timeout so the demo exits when the duration elapses
    even if no key is pressed.
    """
    lines_len = len(lines)
    visible_width = max(len(line.rstrip()) for line in lines) if lines else 0

    def _demo(screen):
        y = screen.height // 2 - lines_len // 2
        x_offset = max(0, (screen.width - visible_width) // 2)
        effect = SineWaveEffect(screen, lines, y, x_offset, label=label)
        start = time()
        while True:
            elapsed = time() - start
            if elapsed >= duration:
                return
            screen.clear_buffer(fg=Screen.COLOUR_WHITE, attr=Screen.A_NORMAL, bg=Screen.COLOUR_BLACK)
            effect.update(0)
            screen.refresh()
            # Use wait_for_input to poll for q without blocking forever
            remaining = max(0.05, duration - elapsed)
            if screen.wait_for_input(remaining):
                key = screen.get_event()
                if key is not None and getattr(key, "key_code", None) in (ord("q"), ord("Q")):
                    return

    Screen.wrapper(_demo)


def pulse_asciimatics(lines):
    """Render the sine-wave pulse via asciimatics Screen.wrapper.

    Runs until the user presses q (up to 30 seconds).
    """
    _run_screen(lines, duration=30.0)


def pulse_asciimatics_timed(lines, duration):
    """Run the asciimatics pulse for exactly ``duration`` seconds.

    Used by ``timer showcase`` to give asciimatics its own bounded segment.
    """
    _run_screen(lines, duration=duration, label="asciimatics")
