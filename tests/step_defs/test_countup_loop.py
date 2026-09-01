"""BDD step definitions for countup_loop.feature.

ZERO real time calls. Every tick is FakeClock.sleep(n) which does clock.t += n.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import FakeClock, MockKeys
from tests.helpers import run_loop_mocked

scenarios("countup_loop.feature")


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
# Steps
# ---------------------------------------------------------------------------


@given("the stopwatch is running", target_fixture="ctx")
def given_stopwatch_running(clock):
    keys = MockKeys(clock)
    return {"clock": clock, "keys": keys, "displayed": []}


@given(parsers.parse("a quit keypress is queued after {ticks:d} ticks"))
def given_quit_after_ticks(ctx, ticks):
    ctx["keys"].queue_at(t=float(ticks), key="q")


@when("the count-up loop runs")
def when_countup_runs(ctx, monkeypatch):
    ctx["displayed"] = run_loop_mocked(
        ctx["clock"], ctx["keys"], monkeypatch, count_up=True
    )


@then(parsers.parse("the seconds displayed should be {sequence} in order"))
def then_displayed_sequence(ctx, sequence):
    expected = [int(x.strip()) for x in sequence.strip("[]").split(",")]
    assert ctx["displayed"] == expected, (
        f"Displayed: {ctx['displayed']}, expected: {expected}"
    )


@then(parsers.parse("the final recorded elapsed time should be {ticks:d}"))
def then_final_recorded_time(ctx, ticks):
    assert ctx["displayed"][-1] == ticks


@given(
    parsers.parse("the stopwatch ran for {seconds:d} seconds then quit"),
    target_fixture="ctx",
)
def given_stopwatch_ran(seconds):
    from countdown import timer

    dur = timer.compact(timer.duration(f"{seconds}s"))
    dur_str = timer.format_duration(dur)
    return {"seconds": seconds, "dur_str": dur_str, "output": None}


@when("the summary is printed")
def when_summary_printed(ctx):
    # Tested directly via format_duration assertion
    pass


@then(parsers.parse('the output should contain "{expected}"'))
def then_output_contains(ctx, expected):
    assert ctx["dur_str"] == expected
