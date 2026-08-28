"""Showcase mode: cycle through every pulse animation.

Each mode gets ``interval`` seconds to play, then we switch to the next.
Exits on q keypress or Ctrl+C. asciimatics runs as a separate screen segment
(via exit-and-restart) since its Screen.wrapper owns the terminal.
"""

import random
from time import sleep, time

from .display import (
    CLEAR,
    DISABLE_ALT_BUFFER,
    ENABLE_ALT_BUFFER,
    HIDE_CURSOR,
    SHOW_CURSOR,
)
from .pulses import ansi as ansi_mod
from .pulses import drawille as drawille_mod
from .pulses import ghostprint as ghostprint_mod
from .pulses import rich as rich_mod
from .pulses import smooth as smooth_mod
from .pulses.ansi import build_frame as build_ansi
from .pulses.asciimatics import pulse_asciimatics_timed
from .pulses.drawille import build_frame as build_drawille
from .pulses.ghostprint import build_frame as build_ghostprint
from .pulses.rich import build_frame as build_rich
from .pulses.smooth import build_frame as build_smooth
from .terminal import check_for_keypress, restore_terminal, setup_terminal

# Modes showcase cycles through (alphabetical; asciimatics handled separately)
SHOWCASE_MODES = ("ansi", "drawille", "ghostprint", "rich", "smooth")

# Each mode's build_frame + reset_state for clean visual between segments
_BUILDERS = {
    "ansi": build_ansi,
    "drawille": build_drawille,
    "ghostprint": build_ghostprint,
    "rich": build_rich,
    "smooth": build_smooth,
}
_RESETTERS = {
    "ansi": ansi_mod.reset_state,
    "drawille": drawille_mod.reset_state,
    "ghostprint": ghostprint_mod.reset_state,
    "rich": rich_mod.reset_state,
    "smooth": smooth_mod.reset_state,
}


def _render_segment(mode, lines, interval):
    """Render one mode for ``interval`` seconds, with a top-left label."""
    if check_for_keypress():
        return False

    _RESETTERS[mode]()
    label = mode
    builder = _BUILDERS[mode]
    mode_start = time()
    while True:
        elapsed = time() - mode_start
        if elapsed >= interval:
            return True  # segment complete
        if check_for_keypress():
            return False
        phase = elapsed
        frame = builder(lines, phase)
        # Label on row 1, frame's leading padding starts at row 2.
        # No newline between label and frame — frame already starts with
        # the leading newlines that center the content vertically.
        print(CLEAR + label + frame, flush=True, end="")
        sleep(0.05)


def run_showcase(interval: float, shuffle: bool, once: bool):
    """Cycle through pulse animations, switching every ``interval`` seconds."""
    from . import display as display_mod

    display_mod.enable_ansi_escape_codes()
    old_settings = setup_terminal()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")

    try:
        from . import timer as timer_mod
        from .display import get_chars_for_terminal

        zero_lines = timer_mod.get_number_lines(0, get_chars_for_terminal(0))
        iteration = 0
        while True:
            order = list(SHOWCASE_MODES)
            if shuffle:
                random.shuffle(order)

            for mode in order:
                if mode == "asciimatics":
                    # asciimatics owns its own screen; segment with exit-and-restart
                    if not _render_asciimatics_segment(zero_lines, interval):
                        return
                    continue

                if not _render_segment(mode, zero_lines, interval):
                    return

            # asciimatics last; segment with exit-and-restart
            if not _render_asciimatics_segment(zero_lines, interval):
                return

            iteration += 1
            if once:
                return
    except KeyboardInterrupt:
        pass
    finally:
        restore_terminal(old_settings)
        print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="")


def _render_asciimatics_segment(lines, interval):
    """Run asciimatics for its own bounded segment."""
    if check_for_keypress():
        return False
    pulse_asciimatics_timed(lines, interval)
    # After Screen.wrapper returns, restore alt buffer for next segment
    from .display import enable_ansi_escape_codes

    enable_ansi_escape_codes()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")
    return not check_for_keypress()
