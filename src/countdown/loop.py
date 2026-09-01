"""The countdown/count-up run loop.

Extracted from ``__main__`` (F1) so timing, rendering, and pulse orchestration
live apart from the Click command tree. Timing goes through a :class:`Clock`
(:data:`STDCLOCK`) so tests can inject a fake clock without touching real time.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.console import Console
from rich.panel import Panel

from . import timer as timer_mod
from .clock import Clock, SystemClock
from .display import (
    DISABLE_ALT_BUFFER,
    ENABLE_ALT_BUFFER,
    HIDE_CURSOR,
    SHOW_CURSOR,
    enable_ansi_escape_codes,
    get_chars_for_terminal,
    print_full_screen,
)
from .keys import get_time_adjustment, is_pause_key, is_time_adjust_key
from .terminal import (
    check_for_keypress,
    drain_keypresses,
    read_key,
    restore_terminal,
    setup_terminal,
)

# Wall clock used by the loop; tests replace this with a fake clock.
STDCLOCK: Clock = SystemClock()


def _render_lines(
    seconds: int,
    *,
    show_hours: bool = False,
    count_up: bool = False,
    raw_seconds: bool = False,
) -> list[str]:
    """Return the glyph lines for ``seconds`` using the terminal-matching font."""
    return timer_mod.get_number_lines(
        seconds,
        get_chars_for_terminal(seconds, show_hours=show_hours),
        show_hours=show_hours,
        count_up=count_up,
        raw_seconds=raw_seconds,
    )


def run_countdown(
    total_seconds: int | None,
    pulse_fn: Callable[[list[str]], None] | None = None,
    max_pulses: int | None = None,
    *,
    show_hours: bool = False,
    count_up: bool = False,
    raw_seconds: bool = False,
    dur_str: str | None = None,
    clock: Clock | None = None,
) -> None:
    """Run the countdown or count-up timer.

    Args:
        total_seconds: Duration in seconds to count down from (or None for count-up)
        pulse_fn: Callable(lines) called after countdown reaches 0
        max_pulses: Maximum pulse iterations before exiting.
        show_hours: If True, display as HH:MM:SS.
        count_up: If True, count up starting from 0 (stopwatch mode).
        raw_seconds: If True, display as bare seconds (e.g. 300) without colons.
        dur_str: Explicit formatted duration string for summary display.
        clock: Inject a Clock; defaults to :data:`STDCLOCK`.
    """
    from .pulses.ansi import pulse_ansi

    if pulse_fn is None:
        pulse_fn = pulse_ansi

    if clock is None:
        clock = STDCLOCK

    time = clock.time
    sleep = clock.sleep

    console = Console()
    enable_ansi_escape_codes()
    old_settings = setup_terminal()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")

    zero_epoch = None
    exit_delay = None
    final_seconds = 0

    try:
        paused = False
        if count_up:
            n = 0
            pause_accum = 0.0
            pause_start = None
            while True:
                lines = _render_lines(
                    n,
                    show_hours=show_hours,
                    count_up=True,
                    raw_seconds=raw_seconds,
                )
                print_full_screen(lines, paused=paused)

                if check_for_keypress():
                    key = read_key()
                    if key == "q" or key == "\x1b":  # q or Esc
                        final_seconds = n
                        break
                    elif is_pause_key(key):
                        if paused:
                            pause_accum += time() - pause_start
                            pause_start = None
                        else:
                            pause_start = time()
                        paused = not paused
                        drain_keypresses()

                if not paused:
                    sleep(1.0)
                    n += 1
                    final_seconds = n
                else:
                    sleep(0.05)
        else:
            n = total_seconds
            sleep_until = time() + total_seconds
            pause_start = None
            while n >= 0 or paused:
                lines = _render_lines(
                    n, show_hours=show_hours, raw_seconds=raw_seconds
                )
                print_full_screen(lines, paused=paused)

                if check_for_keypress():
                    key = read_key()
                    if key == "q" or key == "\x1b":  # q or Esc
                        break
                    elif is_pause_key(key):
                        if paused:
                            sleep_until += time() - pause_start
                            pause_start = None
                        else:
                            pause_start = time()
                        paused = not paused
                        drain_keypresses()
                        lines = _render_lines(
                            n, show_hours=show_hours, raw_seconds=raw_seconds
                        )
                        print_full_screen(lines, paused=paused)
                    elif is_time_adjust_key(key):
                        adjustment = get_time_adjustment(key)
                        new_n = max(0, n + adjustment)
                        sleep_until += new_n - n
                        n = new_n
                        drain_keypresses()
                        lines = _render_lines(
                            n, show_hours=show_hours, raw_seconds=raw_seconds
                        )
                        print_full_screen(lines, paused=paused)

                if not paused:
                    display_this_second_until = sleep_until - n + 1
                    remaining = display_this_second_until - time()
                    if remaining > 0:
                        sleep(remaining)
                    n -= 1
                else:
                    if not check_for_keypress():
                        sleep(1.0)
                    else:
                        sleep(0.05)

            # Record epoch timestamp when reaching zero
            zero_epoch = time()

            if getattr(pulse_fn, "__name__", "") == "pulse_asciimatics":
                print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="", flush=True)
                pulse_fn(
                    _render_lines(
                        0, show_hours=show_hours, raw_seconds=raw_seconds
                    )
                )
                exit_delay = time() - zero_epoch
                return

            pulse_count = 0
            while (
                max_pulses is None or pulse_count < max_pulses
            ) and not check_for_keypress():
                pulse_fn(
                    _render_lines(
                        0, show_hours=show_hours, raw_seconds=raw_seconds
                    )
                )
                sleep(0.05)
                pulse_count += 1

            exit_delay = time() - zero_epoch

    except KeyboardInterrupt:
        if zero_epoch is not None and exit_delay is None:
            exit_delay = time() - zero_epoch
    finally:
        restore_terminal(old_settings)
        print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="")

        # Persistent summary log using rich
        if count_up:
            final_dur = dur_str or timer_mod.format_duration(
                timer_mod.compact(timer_mod.duration(f"{final_seconds}s"))
            )
            console.print(
                Panel(
                    f"[bold green]Timer ran for {final_dur}[/bold green]",
                    title="[bold cyan]Timer Summary[/bold cyan]",
                    expand=False,
                )
            )
        else:
            if dur_str:
                total_ran = dur_str
            elif raw_seconds:
                total_ran = f"{total_seconds}s"
            else:
                total_ran = timer_mod.format_duration(
                    timer_mod.compact(timer_mod.duration(f"{total_seconds}s"))
                )
            if exit_delay is not None:
                if exit_delay < 1:
                    delay_str = f"{exit_delay:.2f}s"
                else:
                    delay_str = timer_mod.format_duration(
                        timer_mod.compact(
                            timer_mod.duration(f"{int(exit_delay)}s")
                        )
                    )
                console.print(
                    Panel(
                        f"[bold green]Timer completed ({total_ran})[/bold green]\n"
                        f"[bold yellow]Time to exit after timeout: {delay_str}[/bold yellow]",
                        title="[bold cyan]Timer Summary[/bold cyan]",
                        expand=False,
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[bold yellow]Timer stopped early ({total_ran} configured)[/bold yellow]",
                        title="[bold cyan]Timer Summary[/bold cyan]",
                        expand=False,
                    )
                )


__all__ = ["STDCLOCK", "run_countdown"]
