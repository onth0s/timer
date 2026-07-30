"""BDD step definitions for keys.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from countdown.keys import get_time_adjustment, is_pause_key, is_time_adjust_key

scenarios("keys.feature")

# Map Gherkin table labels → actual key characters
_KEY_MAP = {
    "space": " ",
    "p": "p",
    "k": "k",
    "enter": "\r",
    "newline": "\n",
    "q": "q",
    "+": "+",
    "=": "=",
    "-": "-",
    "esc": "\x1b",
}


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse("the key {key_label}"), target_fixture="ctx")
def given_key(key_label):
    raw = key_label.strip('"')
    if raw == "\\r":
        key_char = "\r"
    elif raw == "\\n":
        key_char = "\n"
    else:
        key_char = _KEY_MAP.get(raw, raw)
    return {"key": key_char, "result": None}


@when("I check if it is a pause key")
def when_check_pause(ctx):
    ctx["result"] = is_pause_key(ctx["key"])


@when("I check if it is a time-adjust key")
def when_check_time_adjust(ctx):
    ctx["result"] = is_time_adjust_key(ctx["key"])


@when("I get the time adjustment")
def when_get_adjustment(ctx):
    ctx["result"] = get_time_adjustment(ctx["key"])


@then(parsers.parse("the result should be {expected}"))
def then_result_bool(ctx, expected):
    expected_val = expected.strip() == "true"
    assert ctx["result"] == expected_val, (
        f"Key {ctx['key']!r}: got {ctx['result']}, expected {expected_val}"
    )


@then(parsers.parse("the adjustment should be {delta:d} seconds"))
def then_adjustment_seconds(ctx, delta):
    assert ctx["result"] == delta, (
        f"Key {ctx['key']!r}: got adjustment {ctx['result']}, expected {delta}"
    )
