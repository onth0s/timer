"""Showcase mode: cycle through every pulse animation.

Each mode gets ``interval`` seconds to play, then we switch to the next.
Exits on q keypress or Ctrl+C. asciimatics runs as a separate screen segment
(once per cycle, via exit-and-restart) since its Screen.wrapper owns the
terminal. Modes whose optional animation library is not installed are skipped.
"""

import random
from collections.abc import Callable
from time import sleep, time

from rich.console import Console

from .display import (
    CLEAR,
    DISABLE_ALT_BUFFER,
    ENABLE_ALT_BUFFER,
    HIDE_CURSOR,
    SHOW_CURSOR,
)
from .pulses import (
    SHOWCASE_MODES,
    get_showcase_builder,
    get_showcase_resetter,
    is_mode_available,
)
from .terminal import check_for_keypress, restore_terminal, setup_terminal

_STDERR = Console(stderr=True)


def _available_showcase_modes() -> list[str]:
    """Return SHOWCASE_MODES whose animation backend is importable."""
    return [mode for mode in SHOWCASE_MODES if is_mode_available(mode)]


def _showcase_parts(
    mode: str,
) -> tuple[
    Callable[[list[str], float], str], Callable[[], None]
]:
    """Return ``(build_frame, reset_state)`` for a showcase mode."""
    return get_showcase_builder(mode), get_showcase_resetter(mode)


def _render_segment(
    mode: str, lines: list[str], interval: float
) -> bool:
    """Render one mode for ``interval`` seconds, with a top-left label."""
    if check_for_keypress():
        return False

    builder, reset_state = _showcase_parts(mode)
    reset_state()
    label = mode
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

    available = _available_showcase_modes()
    has_asciimatics = is_mode_available("asciimatics")
    if not has_asciimatics:
        _STDERR.print("[yellow]asciimatics not installed: skipping its segment[/yellow]")

    display_mod.enable_ansi_escape_codes()
    old_settings = setup_terminal()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")

    try:
        from . import timer as timer_mod
        from .display import get_chars_for_terminal

        zero_lines = timer_mod.get_number_lines(0, get_chars_for_terminal(0))
        iteration = 0
        while True:
            order = list(available)
            if shuffle:
                random.shuffle(order)

            for mode in order:
                if not _render_segment(mode, zero_lines, interval):
                    return

            if has_asciimatics:
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


def _render_asciimatics_segment(
    lines: list[str], interval: float
) -> bool:
    """Run asciimatics for its own bounded segment."""
    from .pulses.asciimatics import pulse_asciimatics_timed

    if check_for_keypress():
        return False
    pulse_asciimatics_timed(lines, interval)
    # After Screen.wrapper returns, restore alt buffer for next segment
    from .display import enable_ansi_escape_codes

    enable_ansi_escape_codes()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")
    return not check_for_keypress()


__all__ = ["run_showcase"]
