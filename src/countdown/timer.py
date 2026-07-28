"""Time parsing and formatting utilities."""

import re

DURATION_RE = re.compile(
    r"""
    ^
    (?:
        (?: (\d+) m )?    # Optional minutes
        (?: (\d+) s )?    # Optional seconds
    )
    $
    |
    ^ (\d+) $             # Bare number (interpreted as seconds)
""",
    re.VERBOSE,
)


def duration(string):
    """Convert given XmXs or bare number string to seconds (as an integer).

    Bare numbers are interpreted as seconds.
    """
    match = DURATION_RE.search(string)
    if not match:
        raise ValueError(f"Invalid duration: {string}")
    minutes, seconds, bare = match.groups()
    if bare is not None:
        return int(bare)
    return int(minutes or 0) * 60 + int(seconds or 0)


def get_number_lines(seconds, chars):
    """Return list of lines which make large MM:SS glyphs for given seconds.

    Args:
        seconds: The time in seconds to format
        chars: Dictionary of character glyphs to use for rendering

    Returns:
        List of strings, one per line of the ASCII art display
    """
    digit_height = len(next(iter(chars.values())).splitlines())
    lines = [""] * digit_height
    minutes, seconds = divmod(seconds, 60)
    time = f"{minutes:02d}:{seconds:02d}"
    for char in time:
        char_lines = chars[char].splitlines()
        for i, line in enumerate(char_lines):
            lines[i] += line + " "
    return lines
