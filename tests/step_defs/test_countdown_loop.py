"""BDD step definitions for countdown_loop.feature.

ZERO real time calls. Every tick is FakeClock.sleep(n) which does clock.t += n.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import FakeClock, MockKeys
from tests.helpers import run_loop_mocked

scenarios("countdown_loop.feature")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clock():
    return FakeClock()


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("a mock clock starting at 0", target_fixture="clock")
def given_mock_clock_at_0(clock):
    clock.t = 0.0
    return clock


@given("a mock sleep that increments the clock by the requested amount")
def given_mock_sleep(clock):
    pass


@given("no real system time is used")
def given_no_real_time():
    pass


# ---------------------------------------------------------------------------
# Scenario: Full countdown visits every second in order
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a countdown of {seconds:d} seconds"), target_fixture="ctx"
)
def given_countdown_seconds(seconds, clock):
    keys = MockKeys(clock)
    return {"total": seconds, "clock": clock, "keys": keys, "displayed": []}


@when("the countdown loop runs to completion")
def when_countdown_runs(ctx, monkeypatch):
    ctx["displayed"] = run_loop_mocked(
        ctx["clock"], ctx["keys"], monkeypatch, total_seconds=ctx["total"]
    )


@then(parsers.parse("the seconds displayed should be {sequence} in order"))
def then_displayed_sequence(ctx, sequence):
    expected = [int(x.strip()) for x in sequence.strip("[]").split(",")]
    assert ctx["displayed"] == expected, (
        f"Displayed: {ctx['displayed']}, expected: {expected}"
    )


@then("the minimum displayed value should be 0")
def then_min_is_zero(ctx):
    assert 0 in ctx["displayed"], (
        f"0 not reached — displayed: {ctx['displayed']}"
    )
    assert min(ctx["displayed"]) == 0


# ---------------------------------------------------------------------------
# Scenario: Quit key exits the loop before countdown reaches zero
# ---------------------------------------------------------------------------


@given(parsers.parse('a keypress of "{key}" is queued at second {n:d}'))
def given_keypress_at_second(ctx, key, n):
    # At second n displayed, clock.t = total - n
    t_trigger = ctx["total"] - n
    ctx["keys"].queue_at(t=t_trigger, key=key)


@when("the countdown loop runs")
def when_countdown_runs_interrupted(ctx, monkeypatch):
    ctx["displayed"] = run_loop_mocked(
        ctx["clock"], ctx["keys"], monkeypatch, total_seconds=ctx["total"]
    )


@then("the loop exits before reaching 0")
def then_exits_before_zero(ctx):
    assert 0 not in ctx["displayed"], (
        f"Loop reached 0 but should have exited early. Displayed: {ctx['displayed']}"
    )


# ---------------------------------------------------------------------------
# Scenario: Pause halts countdown time while paused
# ---------------------------------------------------------------------------


@given(parsers.parse("a pause keypress is queued at second {n:d}"))
def given_pause_at_second(ctx, n):
    t_trigger = ctx["total"] - n
    ctx["keys"].queue_at(t=float(t_trigger), key=" ")


@given(
    parsers.parse(
        "a resume keypress is queued after the equivalent of {s:d} fake seconds"
    )
)
def given_resume_after_seconds(ctx, s):
    last_t = max(t for t, _ in ctx["keys"]._presses)
    ctx["keys"].queue_at(t=last_t + float(s), key=" ")


@then("the seconds displayed should still reach 0")
def then_reaches_zero(ctx):
    assert 0 in ctx["displayed"], (
        f"0 not reached — displayed: {ctx['displayed']}"
    )


# ---------------------------------------------------------------------------
# Scenario: Adding time extends the deadline
# ---------------------------------------------------------------------------


@given(parsers.parse('a "{key}" keypress is queued at second {n:d}'))
def given_adjust_key_at_second(ctx, key, n):
    t_trigger = ctx["total"] - n
    ctx["keys"].queue_at(t=float(t_trigger), key=key)


@then(parsers.parse("the total seconds displayed should be more than {base:d}"))
def then_more_than_base(ctx, base):
    assert len(ctx["displayed"]) > base + 1, (
        f"Expected more than {base + 1} frames, got {len(ctx['displayed'])}"
    )


# ---------------------------------------------------------------------------
# Scenario: Subtracting time shortens the deadline
# ---------------------------------------------------------------------------


@then(
    parsers.parse(
        "the countdown should end sooner than {total:d} seconds from start"
    )
)
def then_ends_sooner(ctx, total):
    assert ctx["clock"].t < total, (
        f"Expected clock < {total} at exit, got {ctx['clock'].t}"
    )
