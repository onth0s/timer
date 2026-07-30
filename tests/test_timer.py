"""Test cases for the timer module."""

from textwrap import dedent

import pytest

from countdown import timer
from countdown.digits import CHARS_BY_SIZE


def join_lines(lines):
    """Given list of lines, return string of lines with whitespace stripped."""
    return "\n".join(line.rstrip(" ") for line in lines)


def test_invalid_duration():
    with pytest.raises(ValueError):
        timer.duration("abc")


def test_duration_bare_seconds():
    assert timer.duration("10") == 10


def test_duration_bare_seconds_zero():
    assert timer.duration("0") == 0


def test_duration_bare_seconds_large():
    assert timer.duration("120") == 120


def test_duration_10_seconds():
    assert timer.duration("10s") == 10


def test_duration_60_seconds():
    assert timer.duration("60s") == 60


def test_duration_1_minute():
    assert timer.duration("1m") == 60


def test_duration_10_minutes():
    assert timer.duration("10m") == 600


def test_duration_150_minutes():
    assert timer.duration("150m") == 9000


def test_duration_25_minutes():
    assert timer.duration("25m") == 1500


def test_duration_3_minute_and_30_seconds():
    assert timer.duration("3m30s") == 210


def test_duration_2_minutes_and_8_seconds():
    assert timer.duration("2m8s") == 128


# ── Hours support ──────────────────────────────────────────────────────────


def test_duration_1_hour():
    dur = timer.duration("1h")
    assert dur.total_seconds == 3600
    assert dur.components == {"h": 1}


def test_duration_1h47():
    dur = timer.duration("1h47")
    assert dur.total_seconds == 6420
    assert dur.components == {"h": 1, "m": 47}


def test_duration_1h47m():
    dur = timer.duration("1h47m")
    assert dur.total_seconds == 6420
    assert dur.components == {"h": 1, "m": 47}


def test_duration_1h30s():
    dur = timer.duration("1h30s")
    assert dur.total_seconds == 3630
    assert dur.components == {"h": 1, "s": 30}


def test_duration_1h4m6():
    dur = timer.duration("1h4m6")
    assert dur.total_seconds == 3846
    assert dur.components == {"h": 1, "m": 4, "s": 6}


def test_duration_1h47m30s():
    dur = timer.duration("1h47m30s")
    assert dur.total_seconds == 6450
    assert dur.components == {"h": 1, "m": 47, "s": 30}


def test_duration_1m4():
    dur = timer.duration("1m4")
    assert dur.total_seconds == 64
    assert dur.components == {"m": 1, "s": 4}


def test_duration_4m6():
    dur = timer.duration("4m6")
    assert dur.total_seconds == 246
    assert dur.components == {"m": 4, "s": 6}


# ── compact ────────────────────────────────────────────────────────────────


def test_compact_60s():
    dur = timer.duration("60s")
    c = timer.compact(dur)
    assert c.total_seconds == 60
    assert c.components == {"m": 1}


def test_compact_130s():
    dur = timer.duration("130s")
    c = timer.compact(dur)
    assert c.total_seconds == 130
    assert c.components == {"m": 2, "s": 10}


def test_compact_90m():
    dur = timer.duration("90m")
    c = timer.compact(dur)
    assert c.total_seconds == 5400
    assert c.components == {"h": 1, "m": 30}


def test_compact_70s():
    dur = timer.duration("70s")
    c = timer.compact(dur)
    assert c.total_seconds == 70
    assert c.components == {"m": 1, "s": 10}


def test_compact_already_canonical():
    dur = timer.duration("2m10s")
    c = timer.compact(dur)
    assert c.components == dur.components


# ── needs_prompt ───────────────────────────────────────────────────────────


def test_needs_prompt_60s():
    assert timer.needs_prompt(timer.duration("60s")) is True


def test_needs_prompt_130s():
    assert timer.needs_prompt(timer.duration("130s")) is True


def test_needs_prompt_90m():
    assert timer.needs_prompt(timer.duration("90m")) is True


def test_needs_prompt_2m10s():
    assert timer.needs_prompt(timer.duration("2m10s")) is False


def test_needs_prompt_1h30m():
    assert timer.needs_prompt(timer.duration("1h30m")) is False


def test_needs_prompt_bare_seconds():
    assert timer.needs_prompt(timer.duration("45")) is False


# ── format_duration ────────────────────────────────────────────────────────


def test_format_duration_1h47m():
    assert timer.format_duration(timer.duration("1h47m")) == "1h47m"


def test_format_duration_2m10s():
    assert timer.format_duration(timer.duration("2m10s")) == "2m10s"


def test_format_duration_130s():
    assert timer.format_duration(timer.duration("130s")) == "130s"


def test_format_duration_90m():
    assert timer.format_duration(timer.duration("90m")) == "90m"


def test_format_duration_compact_90m():
    c = timer.compact(timer.duration("90m"))
    assert timer.format_duration(c) == "1h30m"


def test_format_duration_compact_60s():
    c = timer.compact(timer.duration("60s"))
    assert timer.format_duration(c) == "1m"


def test_get_number_lines_10_seconds():
    # Use size 5 digits for consistent rendering
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(10, chars)) == dedent(
        """
        ██████ ██████        ██   ██████
        ██  ██ ██  ██  ██   ███   ██  ██
        ██  ██ ██  ██        ██   ██  ██
        ██  ██ ██  ██  ██    ██   ██  ██
        ██████ ██████        ██   ██████
    """
    ).strip("\n")


def test_get_number_lines_60_seconds():
    # Use size 5 digits
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(60, chars)) == dedent(
        """
        ██████   ██        ██████ ██████
        ██  ██  ███    ██  ██  ██ ██  ██
        ██  ██   ██        ██  ██ ██  ██
        ██  ██   ██    ██  ██  ██ ██  ██
        ██████   ██        ██████ ██████
    """
    ).strip("\n")


def test_get_number_lines_45_minutes():
    # Use size 5 digits
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(2700, chars)) == dedent(
        """
        ██  ██ ██████      ██████ ██████
        ██  ██ ██      ██  ██  ██ ██  ██
        ██████ ██████      ██  ██ ██  ██
            ██     ██  ██  ██  ██ ██  ██
            ██ ██████      ██████ ██████
    """
    ).strip("\n")


def test_get_number_lines_101_minutes():
    # Use size 5 digits
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(6060, chars)) == (
        "  ██   ██████   ██        ██████ ██████\n"
        " ███   ██  ██  ███    ██  ██  ██ ██  ██\n"
        "  ██   ██  ██   ██        ██  ██ ██  ██\n"
        "  ██   ██  ██   ██    ██  ██  ██ ██  ██\n"
        "  ██   ██████   ██        ██████ ██████"
    )


def test_get_number_lines_17_minutes_and_four_seconds():
    # Use size 5 digits
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(1024, chars)) == (
        "  ██   ██████      ██████ ██  ██\n"
        " ███       ██  ██  ██  ██ ██  ██\n"
        "  ██      ██       ██  ██ ██████\n"
        "  ██     ██    ██  ██  ██     ██\n"
        "  ██     ██        ██████     ██"
    )


def test_get_number_lines_8_minutes_and_6_seconds():
    # Use size 5 digits
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(486, chars)) == dedent(
        """
        ██████  ████       ██████ ██████
        ██  ██ ██  ██  ██  ██  ██ ██
        ██  ██  ████       ██  ██ ██████
        ██  ██ ██  ██  ██  ██  ██ ██  ██
        ██████  ████       ██████ ██████
    """
    ).strip("\n")


def test_get_number_lines_9_minutes():
    # Use size 5 digits
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(540, chars)) == dedent(
        """
        ██████ ██████      ██████ ██████
        ██  ██ ██  ██  ██  ██  ██ ██  ██
        ██  ██ ██████      ██  ██ ██  ██
        ██  ██     ██  ██  ██  ██ ██  ██
        ██████  █████      ██████ ██████
    """
    ).strip("\n")


def test_get_number_lines_3478():
    # Use size 5 digits
    chars = CHARS_BY_SIZE[5]
    assert join_lines(timer.get_number_lines(2118, chars)) == dedent(
        """
        ██████ ██████        ██    ████
            ██ ██      ██   ███   ██  ██
         █████ ██████        ██    ████
            ██     ██  ██    ██   ██  ██
        ██████ ██████        ██    ████
    """
    ).strip("\n")


def test_get_number_lines_show_hours():
    """show_hours=True should produce wider lines (HH:MM:SS vs MM:SS)."""
    chars = CHARS_BY_SIZE[5]
    lines_ms = timer.get_number_lines(3661, chars, show_hours=False)
    lines_hms = timer.get_number_lines(3661, chars, show_hours=True)
    assert lines_ms != lines_hms
    assert max(len(line) for line in lines_hms) > max(len(line) for line in lines_ms)
    assert len(lines_ms) == len(lines_hms)
