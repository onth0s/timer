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
