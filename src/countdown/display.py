"""Visual rendering and ANSI terminal control."""

import os
import re
import sys
from collections.abc import Iterable
from shutil import get_terminal_size as _shutil_get_terminal_size

from .digits import CHARS_BY_SIZE, DIGIT_SIZES

# ANSI escape codes for terminal control
ENABLE_ALT_BUFFER = "\033[?1049h"
DISABLE_ALT_BUFFER = "\033[?1049l"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR = "\033[H\033[J"
HOME = "\033[H"

# Full-screen clear for pulse animations. Clears the entire visible canvas
# (not just cursor-to-end) and homes the cursor so frames never ghost the
# previous frame's tail row.
FULL_CLEAR_HOME = "\033[2J\033[H"

# ANSI color codes
INTENSE_MAGENTA = "\x1b[95m"
BRIGHT_WHITE = "\x1b[97m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\033[0m"

# Matches all CSI sequences: ESC [ + optional ?/digits/semicolons + final byte.
_ANSI_CSI_RE = re.compile(r"\033\[[\?]?[\d;]*[A-Za-z]")


def get_terminal_size(
    fallback: tuple[int, int] = (80, 24),
) -> os.terminal_size:
    """Return the visible window size (not screen buffer).

    On Windows ``shutil.get_terminal_size()`` returns the *buffer* size, which
    can be much wider than the visible window (e.g. 209 columns vs 120 columns
    visible).  This function reads ``GetConsoleScreenBufferInfo.srWindow`` to
    get the actual visible dimensions and falls back to ``shutil`` elsewhere.
    """
    if sys.platform == "win32":
        try:
            from ctypes import create_string_buffer, windll

            h = windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            csbi = create_string_buffer(
                22
            )  # sizeof(CONSOLE_SCREEN_BUFFER_INFO)
            if windll.kernel32.GetConsoleScreenBufferInfo(h, csbi):
                import struct

                left, top, right, bottom = struct.unpack_from(
                    "HHHH", csbi, offset=10
                )
                tw = right - left + 1
                th = bottom - top + 1
                if tw > 0 and th > 0:
                    return os.terminal_size((tw, th))
        except Exception:  # noqa: S110
            pass
    return _shutil_get_terminal_size(fallback=fallback)


def strip_ansi(text: str) -> str:
    """Return ``text`` with all ANSI CSI escape sequences removed.

    Used for measuring the visible width of a styled line so that centering
    math ignores SGR codes and other invisible bytes.
    """
    return _ANSI_CSI_RE.sub("", text)


def visual_width(line: str) -> int:
    """Return the visible width of ``line`` after stripping ANSI escapes."""
    return len(strip_ansi(line))


def horizontal_padding(
    content_lines: Iterable[str], term_width: int
) -> int:
    """Return spaces to prepend so content_lines sit centered horizontally."""
    if not content_lines:
        return 0
    widest = max(visual_width(line) for line in content_lines)
    return max(0, (term_width - widest) // 2)


def vertical_padding(content_height: int, term_height: int) -> int:
    """Return lines of leading padding so content_height rows sit centered."""
    return max(0, (term_height - content_height) // 2)


def centered_frame(
    content_lines: list[str],
    term_width: int,
    term_height: int,
    indent: str = " ",
) -> str:
    r"""Return a single string with content_lines centered on the terminal.

    ``content_lines`` is a list of strings (each may contain ANSI escapes).
    Visible width is computed by stripping ANSI codes. ``indent`` is the
    character used for horizontal padding (default: space).

    The returned string starts with vertical newlines, has each content line
    prepended with horizontal-padding characters, and is joined by ``\n``.
    No trailing newline. Pair with ``FULL_CLEAR_HOME`` for flicker-free frames.
    """
    if not content_lines:
        return ""
    v_pad = "\n" * vertical_padding(len(content_lines), term_height)
    h_pad = horizontal_padding(content_lines, term_width) * indent
    if h_pad:
        body = "\n".join(f"{h_pad}{line}" for line in content_lines)
    else:
        body = "\n".join(content_lines)
    return f"{v_pad}{body}"


def enable_ansi_escape_codes() -> None:  # pragma: no cover
    """If running on Windows, enable ANSI escape codes."""
    if sys.platform == "win32":
        from ctypes import windll

        k = windll.kernel32
        stdout = -11
        enable_processed_output = 0x0001
        enable_wrap_at_eol_output = 0x0002
        enable_virtual_terminal_processing = 0x0004
        k.SetConsoleMode(
            k.GetStdHandle(stdout),
            enable_processed_output
            | enable_wrap_at_eol_output
            | enable_virtual_terminal_processing,
        )


def get_required_width(
    chars: dict[str, str], time_string: str, *, show_hours: bool = False
) -> int:
    """Calculate the minimum width required to display the given time string.

    Returns the actual rendered width by building ``get_number_lines`` and
    measuring the widest line, so the check in ``get_chars_for_terminal``
    exactly matches what ``print_full_screen`` will display.
    """
    from . import timer as timer_mod

    seconds = _parse_time_string(time_string)
    lines = timer_mod.get_number_lines(seconds, chars, show_hours=show_hours)
    return max(len(line) for line in lines) if lines else 0


def _parse_time_string(time_string: str) -> int:
    """Convert an MM:SS or HH:MM:SS string to total seconds."""
    parts = time_string.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0


def get_chars_for_terminal(
    seconds: int = 0, *, show_hours: bool = False
) -> dict[str, str]:
    """Return the largest CHARS dictionary that fits in the current terminal.

    Args:
        seconds: Current countdown value, used to account for wide minute values.
        show_hours: If True, measure width for HH:MM:SS instead of MM:SS.
    """
    width, height = get_terminal_size()
    from . import timer as timer_mod

    time_string = timer_mod._format_time_string(
        seconds, show_hours=show_hours
    )
    for size in DIGIT_SIZES:
        chars = CHARS_BY_SIZE[size]
        required_width = get_required_width(
            chars, time_string, show_hours=show_hours
        )
        # For size 3 (smallest multi-line), allow it without padding
        # For larger sizes, require 1 line of padding on top and bottom (2 total)
        padding_needed = 0 if size == 3 else 2
        if size + padding_needed <= height and required_width <= width:
            return chars
    # If terminal is too small, return the smallest available
    return CHARS_BY_SIZE[min(DIGIT_SIZES)]


def print_full_screen(lines: list[str], paused: bool = False) -> None:
    """Print the given lines centered in the middle of the terminal window."""
    term_width, term_height = get_terminal_size()

    # Calculate total content height
    content_height = len(lines)
    show_pause_text = False
    if paused and content_height + 2 <= term_height:
        # Only show PAUSED text if there's room
        content_height += 2  # Blank line + PAUSED text
        show_pause_text = True

    v_pad = "\n" * vertical_padding(content_height, term_height)
    h_pad = " " * horizontal_padding(lines, term_width)

    # Apply red color to timer if paused
    if paused:
        colored_lines = [INTENSE_MAGENTA + line + RESET for line in lines]
    else:
        colored_lines = lines

    # Build the output
    padded_text = "\n".join(h_pad + line for line in colored_lines)

    if show_pause_text:
        pause_text = "PAUSED - Press any key to resume"
        pause_padding = " " * max(0, (term_width - len(pause_text)) // 2)
        padded_text += "\n\n" + pause_padding + pause_text

    print(CLEAR + v_pad + padded_text, flush=True, end="")


__all__ = [
    "BRIGHT_WHITE",
    "CLEAR",
    "DIM",
    "DISABLE_ALT_BUFFER",
    "ENABLE_ALT_BUFFER",
    "BOLD",
    "FULL_CLEAR_HOME",
    "HIDE_CURSOR",
    "HOME",
    "INTENSE_MAGENTA",
    "RESET",
    "SHOW_CURSOR",
    "centered_frame",
    "enable_ansi_escape_codes",
    "get_chars_for_terminal",
    "get_required_width",
    "get_terminal_size",
    "horizontal_padding",
    "print_full_screen",
    "strip_ansi",
    "vertical_padding",
    "visual_width",
]
