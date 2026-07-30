"""Time parsing and formatting utilities."""

import re
from dataclasses import dataclass


@dataclass
class Duration:
    """Parsed duration with total seconds and component breakdown."""

    total_seconds: int
    components: dict[str, int]

    def __eq__(self, other):
        """Compare by total_seconds when compared to int or Duration."""
        if isinstance(other, int):
            return self.total_seconds == other
        if isinstance(other, Duration):
            return self.total_seconds == other.total_seconds
        return NotImplemented


_UNITS = ["h", "m", "s"]
_SECONDS_PER = {"h": 3600, "m": 60, "s": 1}


# Regex alternatives in priority order:
#   1.  Xh Ym Zs   — all explicit units (h→m→s, each optional)
#   2.  XhY        — X hours, Y minutes (bare after h)
#   3.  XmY        — X minutes, Y seconds (bare after m)
#   4.  XhYmZ      — X hours, Y minutes, Z seconds  (bare after m)
#   5.  X          — bare number → seconds
DURATION_RE = re.compile(
    r"""
    ^
    (?: (\d+) h )?      # 1. hours (explicit)
    (?: (\d+) m )?      # 2. minutes (explicit)
    (?: (\d+) s )?      # 3. seconds (explicit)
    $
    |
    ^ (\d+) h (\d+) $   # 4,5. XhY → Xh Ym
    |
    ^ (\d+) m (\d+) $   # 6,7. XmY → Xm Ys
    |
    ^ (\d+) h (\d+) m (\d+) $  # 8,9,10. XhYmZ → Xh Ym Zs
    |
    ^ (\d+) $           # 11. bare number → seconds
    """,
    re.VERBOSE,
)


def _build_components(*pairs):
    """Build components dict from (value, unit) pairs, omitting None/0."""
    comps = {}
    for val, unit in pairs:
        if val is not None and int(val) != 0:
            comps[unit] = int(val)
    return comps


def duration(string):
    """Parse a duration string into a Duration.

    Supported formats:
      - XhYmZs  (any unit optional)
      - XhY     → Xh Ym       (bare after h)
      - XmY     → Xm Ys       (bare after m)
      - XhYmZ   → Xh Ym Zs    (bare after m in hours context)
      - X       → X seconds   (bare number)

    Raises ValueError if the string cannot be parsed.
    """
    match = DURATION_RE.search(string)
    if not match:
        raise ValueError(f"Invalid duration: {string}")

    h, m, s, h_y, my, m_y, sy, h2, m2, s2, bare = match.groups()

    if bare is not None:
        total = int(bare)
        return Duration(total_seconds=total, components={"s": total})

    if h2 is not None:
        total = int(h2) * 3600 + int(m2) * 60 + int(s2)
        return Duration(
            total_seconds=total,
            components=_build_components((h2, "h"), (m2, "m"), (s2, "s")),
        )

    if h_y is not None:
        total = int(h_y) * 3600 + int(my) * 60
        return Duration(
            total_seconds=total,
            components=_build_components((h_y, "h"), (my, "m")),
        )

    if m_y is not None:
        total = int(m_y) * 60 + int(sy)
        return Duration(
            total_seconds=total,
            components=_build_components((m_y, "m"), (sy, "s")),
        )

    total = int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)
    return Duration(
        total_seconds=total,
        components=_build_components((h, "h"), (m, "m"), (s, "s")),
    )


def compact(dur):
    """Return a new Duration using the largest possible units.

    E.g. 130s → 2m10s, 90m → 1h30m, 60s → 1m.
    """
    remaining = dur.total_seconds
    comps = {}
    for unit in _UNITS:
        value = remaining // _SECONDS_PER[unit]
        if value:
            comps[unit] = value
            remaining -= value * _SECONDS_PER[unit]
    return Duration(total_seconds=dur.total_seconds, components=comps)


def needs_prompt(dur):
    """Return True if any minute or second component is >= 60."""
    return dur.components.get("m", 0) >= 60 or dur.components.get("s", 0) >= 60


def format_duration(dur):
    """Return a human-readable string from Duration components.

    E.g. 1h47m, 2m10s, 90m, 130s.
    """
    parts = []
    for unit in _UNITS:
        value = dur.components.get(unit)
        if value:
            parts.append(f"{value}{unit}")
    return "".join(parts) if parts else "0s"


def get_number_lines(seconds, chars, *, show_hours=False, count_up=False):
    """Return list of lines which make large glyphs for the time display.

    Args:
        seconds: The time in seconds to format
        chars: Dictionary of character glyphs to use for rendering
        show_hours: If True, format as HH:MM:SS instead of MM:SS
        count_up: If True, format dynamically (SS under 60s, MM:SS under 1h, HH:MM:SS at 1h+)

    Returns:
        List of strings, one per line of the ASCII art display
    """
    digit_height = len(next(iter(chars.values())).splitlines())
    lines = [""] * digit_height
    seconds = max(0, int(seconds))
    if count_up:
        if seconds < 60:
            time = f"{seconds:02d}"
        elif seconds < 3600 and not show_hours:
            minutes, secs = divmod(seconds, 60)
            time = f"{minutes:02d}:{secs:02d}"
        else:
            hours, rest = divmod(seconds, 3600)
            minutes, secs = divmod(rest, 60)
            time = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    elif show_hours:
        hours, rest = divmod(seconds, 3600)
        minutes, secs = divmod(abs(rest), 60)
        time = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        minutes, secs = divmod(seconds, 60)
        time = f"{minutes:02d}:{secs:02d}"

    for j, char in enumerate(time):
        if char not in chars:
            continue
        char_lines = chars[char].splitlines()
        for i, line in enumerate(char_lines):
            if j > 0:
                lines[i] += " "
            lines[i] += line
    return [line.rstrip() for line in lines]
