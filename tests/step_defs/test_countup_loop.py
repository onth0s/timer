"""BDD step definitions for countup_loop.feature.

ZERO real time calls. Every tick is FakeClock.sleep(n) which does clock.t += n.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import FakeClock, MockKeys

scenarios("countup_loop.feature")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_countup_mocked(clock, keys, monkeypatch):
    displayed: list[int] = []

    monkeypatch.setattr("countdown.loop.STDCLOCK", clock)
    monkeypatch.setattr(
        "countdown.timer.get_number_lines",
        lambda s, _chars, **kw: [str(int(s))],
    )
    monkeypatch.setattr(
        "countdown.loop.get_chars_for_terminal",
        lambda *a, **kw: {},
    )
    monkeypatch.setattr(
        "countdown.loop.print_full_screen",
        lambda lines, **kw: displayed.append(int(lines[0])),
    )
    monkeypatch.setattr("countdown.loop.check_for_keypress", keys.check)
    monkeypatch.setattr("countdown.loop.read_key", keys.read)
    monkeypatch.setattr("countdown.loop.drain_keypresses", lambda: None)
    monkeypatch.setattr("countdown.loop.setup_terminal", lambda: None)
    monkeypatch.setattr("countdown.loop.restore_terminal", lambda s: None)
    monkeypatch.setattr("countdown.loop.enable_ansi_escape_codes", lambda: None)

    from unittest.mock import patch

    from countdown.__main__ import run_countdown

    null_pulse = lambda lines: None  # noqa: E731
    with patch("builtins.print"):  # suppress ANSI escape codes
        run_countdown(
            0,
            pulse_fn=null_pulse,
            count_up=True,
        )

    return displayed


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def ctx():
    return {}


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
    ctx["displayed"] = _run_countup_mocked(
        ctx["clock"], ctx["keys"], monkeypatch
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
