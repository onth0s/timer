"""Full-screen terminal digital wall clock command and run loop."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel

from .clock import Clock, SystemClock
from .display import (
    BRIGHT_WHITE,
    DISABLE_ALT_BUFFER,
    ENABLE_ALT_BUFFER,
    FULL_CLEAR_HOME,
    HIDE_CURSOR,
    INTENSE_MAGENTA,
    RESET,
    SHOW_CURSOR,
    enable_ansi_escape_codes,
    get_clock_chars_for_terminal,
    get_terminal_size,
    vertical_padding,
    visual_width,
)
from .loop import STDCLOCK
from .terminal import (
    check_for_keypress,
    drain_keypresses,
    read_key,
    restore_terminal,
    setup_terminal,
)
from .timer import render_time_string_glyphs


def format_clock_time(
    dt: datetime,
    *,
    show_seconds: bool = True,
    twelve_hour: bool = False,
) -> tuple[str, str | None]:
    """Format datetime into a display string and optional AM/PM indicator.

    Args:
        dt: The datetime to format.
        show_seconds: If True, include seconds (HH:MM:SS), else HH:MM.
        twelve_hour: If True, format in 12-hour notation with AM/PM.

    Returns:
        tuple of (time_string, ampm_string_or_none)
    """
    if twelve_hour:
        h = dt.hour % 12
        if h == 0:
            h = 12
        ampm = "AM" if dt.hour < 12 else "PM"
        if show_seconds:
            return f"{h:02d}:{dt.minute:02d}:{dt.second:02d}", ampm
        return f"{h:02d}:{dt.minute:02d}", ampm
    else:
        if show_seconds:
            return f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}", None
        return f"{dt.hour:02d}:{dt.minute:02d}", None


def format_clock_date(dt: datetime) -> str:
    """Format datetime into a readable date string.

    Args:
        dt: The datetime to format.

    Returns:
        Formatted date string, e.g. 'Friday, September 4, 2026'.
    """
    return f"{dt.strftime('%A, %B')} {dt.day}, {dt.year}"


def render_clock_frame(
    time_str: str,
    chars: dict[str, str],
    *,
    ampm: str | None = None,
    date_str: str | None = None,
    paused: bool = False,
    term_size: tuple[int, int] | None = None,
) -> str:
    """Build a centered full-screen frame string for the clock display.

    Args:
        time_str: The formatted time string (e.g. '14:24:29').
        chars: Font dictionary for rendering digits and colons.
        ampm: Optional AM/PM subtitle indicator.
        date_str: Optional date subtitle string.
        paused: Whether the clock is currently paused.
        term_size: Optional (width, height) terminal override.

    Returns:
        The complete terminal frame string ready for printing.
    """
    if term_size is None:
        term_width, term_height = get_terminal_size()
    else:
        term_width, term_height = term_size

    glyph_lines = render_time_string_glyphs(time_str, chars)
    if paused:
        colored_lines = [INTENSE_MAGENTA + line + RESET for line in glyph_lines]
    else:
        colored_lines = [BRIGHT_WHITE + line + RESET for line in glyph_lines]

    all_lines = list(colored_lines)

    if ampm:
        all_lines.append("")
        all_lines.append(f"\x1b[1;36m{ampm}\x1b[0m")

    if date_str:
        all_lines.append("")
        all_lines.append(f"\x1b[2;37m{date_str}\x1b[0m")

    if paused:
        all_lines.append("")
        all_lines.append(
            f"{INTENSE_MAGENTA}PAUSED - Press Space to resume{RESET}"
        )

    centered_lines = [
        (" " * max(0, (term_width - visual_width(line)) // 2)) + line
        for line in all_lines
    ]
    v_pad = "\n" * vertical_padding(len(centered_lines), term_height)
    return FULL_CLEAR_HOME + v_pad + "\n".join(centered_lines)


def print_clock_screen(frame: str) -> None:
    """Print the rendered frame string to terminal output."""
    print(frame, end="", flush=True)


def run_clock(
    *,
    show_seconds: bool = True,
    twelve_hour: bool = False,
    show_date: bool = False,
    utc: bool = False,
    clock: Clock | None = None,
) -> None:
    """Run the full-screen terminal wall clock.

    Args:
        show_seconds: Whether to display seconds.
        twelve_hour: Whether to use 12-hour format with AM/PM.
        show_date: Whether to display the date below the time.
        utc: Whether to display UTC time.
        clock: Injected clock instance (defaults to STDCLOCK).
    """
    if clock is None:
        clock = STDCLOCK

    time_fn = clock.time
    sleep_fn = clock.sleep

    console = Console()
    enable_ansi_escape_codes()
    old_settings = setup_terminal()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="", flush=True)

    start_time = time_fn()
    paused = False
    paused_dt: datetime | None = None

    sec_flag = show_seconds
    is_12h = twelve_hour
    date_flag = show_date

    try:
        while True:
            if check_for_keypress():
                key = read_key()
                if key in ("q", "\x1b"):  # q or Esc
                    break
                elif key in (" ", "p", "P"):
                    if paused:
                        paused = False
                        paused_dt = None
                    else:
                        paused = True
                        paused_dt = datetime.fromtimestamp(
                            time_fn(), timezone.utc if utc else None
                        )
                    drain_keypresses()
                elif key in ("s", "S"):
                    sec_flag = not sec_flag
                    drain_keypresses()
                elif key in ("t", "T"):
                    is_12h = not is_12h
                    drain_keypresses()
                elif key in ("d", "D"):
                    date_flag = not date_flag
                    drain_keypresses()

            if paused and paused_dt is not None:
                dt = paused_dt
            else:
                dt = datetime.fromtimestamp(
                    time_fn(), timezone.utc if utc else None
                )

            time_str, ampm = format_clock_time(
                dt, show_seconds=sec_flag, twelve_hour=is_12h
            )
            date_str = format_clock_date(dt) if date_flag else None

            extra_h = 0
            if ampm:
                extra_h += 2
            if date_str:
                extra_h += 2
            if paused:
                extra_h += 2

            chars = get_clock_chars_for_terminal(time_str, extra_height=extra_h)
            frame = render_clock_frame(
                time_str,
                chars,
                ampm=ampm,
                date_str=date_str,
                paused=paused,
            )
            print_clock_screen(frame)

            if isinstance(clock, SystemClock):
                target = time_fn() + 1.0
                while time_fn() < target:
                    if check_for_keypress():
                        break
                    sleep_fn(min(0.05, max(0.001, target - time_fn())))
            else:
                if paused:
                    sleep_fn(0.05)
                else:
                    sleep_fn(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        restore_terminal(old_settings)
        print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="", flush=True)

        elapsed_seconds = int(time_fn() - start_time)
        from . import timer as timer_mod

        final_dur = timer_mod.format_duration(
            timer_mod.compact(timer_mod.duration(f"{max(0, elapsed_seconds)}s"))
        )
        console.print(
            Panel(
                f"[bold green]Clock ran for {final_dur}[/bold green]",
                title="[bold cyan]Clock Summary[/bold cyan]",
                expand=False,
            )
        )


__all__ = [
    "format_clock_date",
    "format_clock_time",
    "print_clock_screen",
    "render_clock_frame",
    "run_clock",
]
