"""BDD step definitions for countdown_display.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from countdown import timer
from countdown.digits import CHARS_BY_SIZE, DIGIT_SIZES

scenarios("countdown_display.feature")

# Smallest glyph size for testing (size 3) — always fits
_TEST_CHARS = CHARS_BY_SIZE[min(DIGIT_SIZES)]


@pytest.fixture
def ctx():
    return {}


@given(
    parsers.parse("the timer is counting down from {seconds:d} seconds"),
    target_fixture="ctx",
)
def given_countdown_from(seconds):
    show_hours = seconds >= 3600
    return {
        "total": seconds,
        "show_hours": show_hours,
        "lines": None,
        "time_str": None,
    }


@when(parsers.parse("the display renders at second {at_second:d}"))
def when_render_at_second(ctx, at_second):
    show_hours = ctx["show_hours"]
    lines = timer.get_number_lines(
        at_second, _TEST_CHARS, show_hours=show_hours
    )
    ctx["lines"] = lines
    # Derive the rendered time string from the first line content
    # (we check _format_time_string directly for the canonical form)
    from countdown.display import _format_time_string

    ctx["time_str"] = _format_time_string(at_second, show_hours=show_hours)


@then(parsers.parse('the rendered time string should be "{expected}"'))
def then_rendered_time_string(ctx, expected):
    assert ctx["time_str"] == expected, (
        f"Got {ctx['time_str']!r}, expected {expected!r}"
    )


@then("the format should be MM:SS")
def then_format_mmss(ctx):
    assert ":" in ctx["time_str"], "Expected MM:SS format (with colon)"
    assert ctx["time_str"].count(":") == 1, (
        "Expected exactly one colon for MM:SS"
    )


@then("the format should be HH:MM:SS")
def then_format_hhmmss(ctx):
    assert ctx["time_str"].count(":") == 2, "Expected two colons for HH:MM:SS"


def test_raw_seconds_display():
    lines = timer.get_number_lines(300, _TEST_CHARS, raw_seconds=True)
    assert lines is not None
    from countdown.display import _format_time_string

    assert _format_time_string(300, raw_seconds=True) == "300"
