"""BDD step definitions for glyph_width.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from countdown import timer
from countdown.digits import CHARS_BY_SIZE, DIGIT_SIZES

scenarios("glyph_width.feature")

_TEST_CHARS = CHARS_BY_SIZE[min(DIGIT_SIZES)]


@pytest.fixture
def ctx():
    return {}


# ---------------------------------------------------------------------------
# Count-up rendering
# ---------------------------------------------------------------------------


@given(
    parsers.parse("the time value {seconds:d}"),
    target_fixture="ctx",
)
def given_time_value(seconds):
    return {"seconds": seconds, "lines_a": None, "lines_b": None}


@when("I render it as a count-up display")
def when_render_countup(ctx):
    ctx["lines_a"] = timer.get_number_lines(
        ctx["seconds"], _TEST_CHARS, count_up=True
    )


@when("I render it as a countdown display")
def when_render_countdown(ctx):
    ctx["lines_a"] = timer.get_number_lines(
        ctx["seconds"], _TEST_CHARS, show_hours=False
    )


@then("every line in the glyph output should have the same width")
def then_uniform_width(ctx):
    lines = ctx["lines_a"]
    assert lines, "No lines rendered"
    widths = [len(line) for line in lines]
    assert len(set(widths)) == 1, (
        f"Lines have unequal widths at {ctx['seconds']}s: {widths}"
    )


# ---------------------------------------------------------------------------
# No-jitter scenario (compares two consecutive values)
# ---------------------------------------------------------------------------


@given("the time values 9 and 10 rendered as count-up", target_fixture="ctx")
def given_jitter_values():
    lines_9 = timer.get_number_lines(9, _TEST_CHARS, count_up=True)
    lines_10 = timer.get_number_lines(10, _TEST_CHARS, count_up=True)
    return {"lines_a": lines_9, "lines_b": lines_10}


@then("both renderings should have the same total width")
def then_same_total_width(ctx):
    width_a = max(len(line) for line in ctx["lines_a"])
    width_b = max(len(line) for line in ctx["lines_b"])
    assert width_a == width_b, (
        f"Jitter detected: width at 9s={width_a}, width at 10s={width_b}"
    )
