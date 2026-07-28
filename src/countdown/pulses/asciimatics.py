"""asciimatics sine-wave pulse animation.

Custom Effect that computes per-cell color via a radial sine wave and
re-renders the glyphs to the asciimatics screen each frame.
"""

import math
from time import sleep, time

from asciimatics.effects import Effect
from asciimatics.screen import Screen


class SineWaveEffect(Effect):
    """Render glyphs with sine-wave-modulated colors."""

    def __init__(self, screen, lines, y, label=None, **kwargs):
        super().__init__(screen, **kwargs)
        self._lines = lines
        self._y = y
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
        cx = max(len(line) for line in self._lines) / 2
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
            for col, ch in enumerate(line):
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
                self._screen.print_at(ch, col, self._y + row, colour=colour, attr=attr)


def _run_screen(lines, duration, label=None):
    """Run the asciimatics pulse for ``duration`` seconds, then exit.

    Polls input with a timeout so the demo exits when the duration elapses
    even if no key is pressed.
    """
    lines_len = len(lines)

    def _demo(screen):
        y = screen.height // 2 - lines_len // 2
        effect = SineWaveEffect(screen, lines, y, label=label)
        start = time()
        while True:
            elapsed = time() - start
            if elapsed >= duration:
                return
            screen.clear()
            effect.update(0)
            screen.refresh()
            # Use wait_for_input to poll for q without blocking forever
            remaining = max(0.05, duration - elapsed)
            if screen.wait_for_input(remaining):
                key = screen.get_event()
                if key is not None and getattr(key, "key_code", None) in (ord("q"), ord("Q")):
                    return
            sleep(0.05)

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
