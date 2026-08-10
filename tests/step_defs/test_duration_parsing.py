"""BDD step definitions for duration_parsing.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from countdown import timer

scenarios("duration_parsing.feature")


# ---------------------------------------------------------------------------
# Shared context fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def ctx():
    return {}


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@given(parsers.parse('the duration string "{input}"'), target_fixture="ctx")
def given_duration_string(input):  # noqa: A002
    return {"input": input, "result": None, "error": None}


@when("I parse it")
def when_parse_it(ctx):
    try:
        ctx["result"] = timer.duration(ctx["input"])
    except ValueError as exc:
        ctx["error"] = exc


@then(parsers.parse("the total seconds should be {seconds:d}"))
def then_total_seconds(ctx, seconds):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"
    assert ctx["result"].total_seconds == seconds


@then("a ValueError should be raised")
def then_value_error(ctx):
    assert ctx["error"] is not None, "Expected a ValueError but no error was raised"
    assert isinstance(ctx["error"], ValueError)


def test_target_time_parsing():
    from datetime import datetime

    now = datetime(2026, 8, 10, 15, 0, 0)
    # -16:40 -> 1 hour 40 minutes = 6000 seconds
    d1 = timer.duration("-16:40", now=now)
    assert d1.total_seconds == 6000

    # -4:40PM -> 1 hour 40 minutes = 6000 seconds
    d2 = timer.duration("-4:40PM", now=now)
    assert d2.total_seconds == 6000

    # -14:00 (past) -> tomorrow 14:00 = 23 hours = 82800 seconds
    d3 = timer.duration("-14:00", now=now)
    assert d3.total_seconds == 82800

