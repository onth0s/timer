"""Time parsing and formatting utilities."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta


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


_UNITS = ["d", "h", "m", "s"]
_SECONDS_PER = {"d": 86400, "h": 3600, "m": 60, "s": 1}


# Regex alternatives in priority order:
#   1.  Xd Yh Zm Ws   — all explicit units (d→h→m→s, each optional)
#   2.  XdY           — X days, Y hours (bare after d)
#   3.  XdYhZ         — X days, Y hours, Z minutes (bare after h)
#   4.  XhY           — X hours, Y minutes (bare after h)
#   5.  XmY           — X minutes, Y seconds (bare after m)
#   6.  XhYmZ         — X hours, Y minutes, Z seconds (bare after m)
#   7.  X             — bare number → seconds
DURATION_RE = re.compile(
    r"""
    ^
    (?: (\d+) d )?      # 1. days (explicit)
    (?: (\d+) h )?      # 2. hours (explicit)
    (?: (\d+) m )?      # 3. minutes (explicit)
    (?: (\d+) s )?      # 4. seconds (explicit)
    $
    |
    ^ (\d+) d (\d+) $   # 5,6. XdY → Xd Yh
    |
    ^ (\d+) d (\d+) h (\d+) $   # 7,8,9. XdYhZ → Xd Yh Zm
    |
    ^ (\d+) h (\d+) $   # 10,11. XhY → Xh Ym
    |
    ^ (\d+) m (\d+) $   # 12,13. XmY → Xm Ys
    |
    ^ (\d+) h (\d+) m (\d+) $  # 14,15,16. XhYmZ → Xh Ym Zs
    |
    ^ (\d+) $           # 17. bare number → seconds
    """,
    re.VERBOSE,
)


TARGET_CLOCK_12_RE = re.compile(
    r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([aA][mM]|[pP][mM])$"
)
TARGET_CLOCK_24_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")
LEADING_COLON_RE = re.compile(r"^:(\d{1,2})(?::(\d{2}))?$")
COLON_DURATION_RE = re.compile(r"^(\d+):(\d{2})(?::(\d{2}))?$")


def _build_components(*pairs):
    """Build components dict from (value, unit) pairs, omitting None/0."""
    comps = {}
    for val, unit in pairs:
        if val is not None and int(val) != 0:
            comps[unit] = int(val)
    return comps


def duration(string, now=None):
    """Parse a duration or target time string into a Duration.

    Supported formats:
      - Leading '-' prefix: Target clock time ("until this time"):
          * -4:40PM, -04:40:00 PM (12-hour)
          * -16:40, -16:40:30 (24-hour)
          * -4:40 (04:40 clock time)
          * Also strips '-' for standard duration strings (e.g. -5m -> 5m)
      - Non '-' prefix: Amount of time:
          * XdYhZmWs (days, hours, minutes, seconds; e.g. 2d1h30m)
          * HH:MM (e.g. 4:40 -> 4h40m, 16:40 -> 16h40m)
          * HH:MM:SS (e.g. 1:02:03 -> 1h2m3s)
          * :MM:SS or :SS (e.g. :01:20 -> 1m20s, :45 -> 45s)
          * XhYmZs, XhY, XmY, XhYmZ, X (bare number = seconds)

    Raises ValueError if the string cannot be parsed.
    """
    if not string:
        raise ValueError(f"Invalid duration: {string}")

    has_dash = string.startswith("-")
    clean_str = string[1:] if has_dash else string

    if has_dash:
        # Check target clock time (12-hour format)
        match_12 = TARGET_CLOCK_12_RE.match(clean_str)
        if match_12:
            h_str, m_str, s_str, ampm = match_12.groups()
            hours = int(h_str)
            minutes = int(m_str)
            seconds = int(s_str) if s_str else 0
            if hours < 1 or hours > 12 or minutes >= 60 or seconds >= 60:
                raise ValueError(f"Invalid target time: {string}")
            if ampm.upper() == "PM" and hours < 12:
                hours += 12
            elif ampm.upper() == "AM" and hours == 12:
                hours = 0
            if now is None:
                now = datetime.now()
            target_dt = now.replace(
                hour=hours, minute=minutes, second=seconds, microsecond=0
            )
            if target_dt <= now:
                target_dt += timedelta(days=1)
            diff_sec = int((target_dt - now).total_seconds())
            return compact(
                Duration(total_seconds=diff_sec, components={"s": diff_sec})
            )

        # Check target clock time (24-hour format)
        match_24 = TARGET_CLOCK_24_RE.match(clean_str)
        if match_24:
            h_str, m_str, s_str = match_24.groups()
            hours = int(h_str)
            minutes = int(m_str)
            seconds = int(s_str) if s_str else 0
            if hours >= 24 or minutes >= 60 or seconds >= 60:
                raise ValueError(f"Invalid target time: {string}")
            if now is None:
                now = datetime.now()
            target_dt = now.replace(
                hour=hours, minute=minutes, second=seconds, microsecond=0
            )
            if target_dt <= now:
                target_dt += timedelta(days=1)
            diff_sec = int((target_dt - now).total_seconds())
            return compact(
                Duration(total_seconds=diff_sec, components={"s": diff_sec})
            )

    # Parsing amounts of time (without leading dash, or fallback after stripping leading dash)
    # Check leading colon format (:MM:SS or :SS)
    match_leading_colon = LEADING_COLON_RE.match(clean_str)
    if match_leading_colon:
        g1, g2 = match_leading_colon.groups()
        if g2 is not None:
            minutes, seconds = int(g1), int(g2)
        else:
            minutes, seconds = 0, int(g1)
        if minutes >= 60 or seconds >= 60:
            raise ValueError(f"Invalid duration: {string}")
        total = minutes * 60 + seconds
        return compact(
            Duration(
                total_seconds=total,
                components=_build_components((minutes, "m"), (seconds, "s")),
            )
        )

    # Check colon format (HH:MM or HH:MM:SS)
    match_colon = COLON_DURATION_RE.match(clean_str)
    if match_colon:
        h_str, m_str, s_str = match_colon.groups()
        hours = int(h_str)
        minutes = int(m_str)
        seconds = int(s_str) if s_str is not None else 0
        if minutes >= 60 or seconds >= 60:
            raise ValueError(f"Invalid duration: {string}")
        total = hours * 3600 + minutes * 60 + seconds
        pairs = [(hours, "h"), (minutes, "m")]
        if s_str is not None:
            pairs.append((seconds, "s"))
        return compact(
            Duration(
                total_seconds=total,
                components=_build_components(*pairs),
            )
        )

    # Standard duration parsing
    match = DURATION_RE.search(clean_str)
    if not match:
        raise ValueError(f"Invalid duration: {string}")

    (
        day,
        hour,
        minute,
        second,
        d_y,
        hy,
        dd,
        dhh,
        dmm,
        h_y,
        my,
        m_y,
        sy,
        hx,
        mx,
        sx,
        bare,
    ) = match.groups()

    if bare is not None:
        total = int(bare)
        return Duration(total_seconds=total, components={"s": total})

    if dd is not None:
        total = int(dd) * 86400 + int(dhh) * 3600 + int(dmm) * 60
        return Duration(
            total_seconds=total,
            components=_build_components((dd, "d"), (dhh, "h"), (dmm, "m")),
        )

    if d_y is not None:
        total = int(d_y) * 86400 + int(hy) * 3600
        return Duration(
            total_seconds=total,
            components=_build_components((d_y, "d"), (hy, "h")),
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

    total = (
        int(day or 0) * 86400
        + int(hour or 0) * 3600
        + int(minute or 0) * 60
        + int(second or 0)
    )
    return Duration(
        total_seconds=total,
        components=_build_components(
            (day, "d"), (hour, "h"), (minute, "m"), (second, "s")
        ),
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


def _format_time_string(
    seconds, *, show_hours=False, count_up=False, raw_seconds=False
):
    """Return the display time string (SS, MM:SS, or HH:MM:SS) for ``seconds``."""
    seconds = max(0, int(seconds))
    if raw_seconds:
        return f"{seconds}"
    if count_up:
        if seconds < 60:
            return f"{seconds:02d}"
        elif seconds < 3600 and not show_hours:
            minutes, secs = divmod(seconds, 60)
            return f"{minutes:02d}:{secs:02d}"
        else:
            hours, rest = divmod(seconds, 3600)
            minutes, secs = divmod(rest, 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    if show_hours:
        hours, rest = divmod(seconds, 3600)
        minutes, secs = divmod(rest, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def get_number_lines(
    seconds, chars, *, show_hours=False, count_up=False, raw_seconds=False
):
    """Return list of lines which make large glyphs for the time display.

    Args:
        seconds: The time in seconds to format
        chars: Dictionary of character glyphs to use for rendering
        show_hours: If True, format as HH:MM:SS instead of MM:SS
        count_up: If True, format dynamically (SS under 60s, MM:SS under 1h, HH:MM:SS at 1h+)
        raw_seconds: If True, format as bare seconds (e.g. "300") without colons

    Returns:
        List of strings, one per line of the ASCII art display
    """
    digit_height = len(next(iter(chars.values())).splitlines())
    lines = [""] * digit_height
    seconds = max(0, int(seconds))
    time = _format_time_string(
        seconds,
        show_hours=show_hours,
        count_up=count_up,
        raw_seconds=raw_seconds,
    )

    for j, char in enumerate(time):
        if char not in chars:
            continue
        char_lines = chars[char].splitlines()
        for i, line in enumerate(char_lines):
            if j > 0:
                lines[i] += " "
            lines[i] += line
    return lines
