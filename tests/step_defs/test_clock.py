"""BDD step definitions for clock.feature."""

from __future__ import annotations

from datetime import datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from countdown.__main__ import main, run_clock
from countdown.clock_cmd import (
    format_clock_date,
    format_clock_time,
    render_clock_frame,
)
from countdown.config import Config
from countdown.digits import CHARS_BY_SIZE
from tests.conftest import FakeClock, MockKeys

scenarios("clock.feature")


# ---------------------------------------------------------------------------
# Fixtures & State
# ---------------------------------------------------------------------------


@pytest.fixture
def clock_ctx():
    return {}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a mock clock starting at timestamp {ts:d}"),
    target_fixture="clock_ctx",
)
def given_mock_clock(ts):
    clock = FakeClock()
    clock.t = float(ts)
    keys = MockKeys(clock)
    return {
        "clock": clock,
        "keys": keys,
        "frames": [],
        "initial_ts": float(ts),
    }


@given(parsers.parse("a quit keypress is queued at tick {ticks:d}"))
def given_quit_queued(clock_ctx, ticks):
    target = clock_ctx["initial_ts"] + float(ticks)
    clock_ctx["keys"].queue_at(t=target, key="q")


@given(parsers.parse('a keypress "{key}" is queued at tick {ticks:d}'))
def given_key_queued(clock_ctx, key, ticks):
    target = clock_ctx["initial_ts"] + float(ticks)
    clock_ctx["keys"].queue_at(t=target, key=key)


@given(
    parsers.parse('the clock CLI is invoked with "{args}"'),
    target_fixture="cli_ctx",
)
def given_clock_cli_invoked(args, runner, tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    monkeypatch.setattr(Config, "path", p)
    return {
        "args": ["clock"] + args.split(),
        "runner": runner,
        "result": None,
    }


@given(
    parsers.parse("a datetime at {h:d}:{m:d}:{s:d}"),
    target_fixture="dt_ctx",
)
def given_datetime_hms(h, m, s):
    return {"dt": datetime(2026, 9, 4, h, m, s)}


@given(
    parsers.parse("a datetime on {year:d}-{month:d}-{day:d}"),
    target_fixture="dt_ctx",
)
def given_datetime_ymd(year, month, day):
    return {"dt": datetime(year, month, day, 12, 0, 0)}


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


def _setup_clock_mocks(clock_ctx, monkeypatch):
    monkeypatch.setattr(
        "countdown.clock_cmd.check_for_keypress", clock_ctx["keys"].check
    )
    monkeypatch.setattr("countdown.clock_cmd.read_key", clock_ctx["keys"].read)
    monkeypatch.setattr("countdown.clock_cmd.drain_keypresses", lambda: None)
    monkeypatch.setattr("countdown.clock_cmd.setup_terminal", lambda: None)
    monkeypatch.setattr("countdown.clock_cmd.restore_terminal", lambda s: None)
    monkeypatch.setattr(
        "countdown.clock_cmd.enable_ansi_escape_codes", lambda: None
    )
    monkeypatch.setattr(
        "countdown.clock_cmd.print_clock_screen",
        lambda frame: clock_ctx["frames"].append(frame),
    )


@when("the clock loop is executed")
def when_clock_loop_runs(clock_ctx, monkeypatch):
    _setup_clock_mocks(clock_ctx, monkeypatch)
    run_clock(clock=clock_ctx["clock"])


@when("the clock loop is executed with seconds enabled")
def when_clock_loop_seconds(clock_ctx, monkeypatch):
    _setup_clock_mocks(clock_ctx, monkeypatch)
    run_clock(show_seconds=True, clock=clock_ctx["clock"])


@when("the clock loop is executed in 24-hour mode")
def when_clock_loop_24h(clock_ctx, monkeypatch):
    _setup_clock_mocks(clock_ctx, monkeypatch)
    run_clock(twelve_hour=False, clock=clock_ctx["clock"])


@when("the CLI command completes")
def when_cli_completes(cli_ctx):
    cli_ctx["result"] = cli_ctx["runner"].invoke(main, cli_ctx["args"])


@when("formatted in 24-hour mode with seconds")
def when_format_24h_sec(dt_ctx):
    s, ampm = format_clock_time(
        dt_ctx["dt"], show_seconds=True, twelve_hour=False
    )
    dt_ctx["time_str"] = s
    dt_ctx["ampm"] = ampm


@when("formatted in 24-hour mode without seconds")
def when_format_24h_nosec(dt_ctx):
    s, ampm = format_clock_time(
        dt_ctx["dt"], show_seconds=False, twelve_hour=False
    )
    dt_ctx["time_str"] = s
    dt_ctx["ampm"] = ampm


@when("formatted in 12-hour mode with seconds")
def when_format_12h_sec(dt_ctx):
    s, ampm = format_clock_time(
        dt_ctx["dt"], show_seconds=True, twelve_hour=True
    )
    dt_ctx["time_str"] = s
    dt_ctx["ampm"] = ampm


@when("formatted in 12-hour mode without seconds")
def when_format_12h_nosec(dt_ctx):
    s, ampm = format_clock_time(
        dt_ctx["dt"], show_seconds=False, twelve_hour=True
    )
    dt_ctx["time_str"] = s
    dt_ctx["ampm"] = ampm


@when("the clock date is formatted")
def when_format_date(dt_ctx):
    dt_ctx["date_str"] = format_clock_date(dt_ctx["dt"])


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then(parsers.parse("the clock ran for {sec:d} second"))
@then(parsers.parse("the clock ran for {sec:d} seconds"))
def then_clock_ran_seconds(clock_ctx, sec):
    elapsed = int(clock_ctx["clock"].time() - clock_ctx["initial_ts"])
    assert elapsed == sec, f"Expected elapsed {sec}s, got {elapsed}s"


@then("the clock summary is displayed")
def then_summary_displayed(clock_ctx):
    assert len(clock_ctx["frames"]) > 0


@then("the exit code should not be 0")
def then_exit_nonzero(cli_ctx):
    assert cli_ctx["result"].exit_code != 0


@then(parsers.parse('the output should contain "{text}"'))
def then_output_contains(cli_ctx, text):
    assert text in cli_ctx["result"].output


@then(parsers.parse('the time string should be "{expected}"'))
def then_time_str(dt_ctx, expected):
    assert dt_ctx["time_str"] == expected


@then("the ampm string should be none")
def then_ampm_none(dt_ctx):
    assert dt_ctx["ampm"] is None


@then(parsers.parse('the ampm string should be "{expected}"'))
def then_ampm_expected(dt_ctx, expected):
    assert dt_ctx["ampm"] == expected


@then(parsers.parse('the date string should be "{expected}"'))
def then_date_str(dt_ctx, expected):
    assert dt_ctx["date_str"] == expected


# ---------------------------------------------------------------------------
# Additional Unit Tests for Clock Frame Rendering
# ---------------------------------------------------------------------------


def test_render_clock_frame_basic():
    chars = CHARS_BY_SIZE[5]
    frame = render_clock_frame(
        "14:25:30",
        chars,
        ampm=None,
        date_str=None,
        paused=False,
        term_size=(80, 24),
    )
    assert (
        "14:25:30" not in frame
    )  # Glyphs rendered as ASCII art, not raw digits
    assert len(frame) > 0


def test_render_clock_frame_with_ampm_and_date():
    chars = CHARS_BY_SIZE[5]
    frame = render_clock_frame(
        "02:25:30",
        chars,
        ampm="PM",
        date_str="Friday, September 4, 2026",
        paused=False,
        term_size=(80, 24),
    )
    assert "PM" in frame
    assert "Friday, September 4, 2026" in frame


def test_render_clock_frame_paused():
    chars = CHARS_BY_SIZE[5]
    frame = render_clock_frame(
        "14:25:30",
        chars,
        paused=True,
        term_size=(80, 24),
    )
    assert "PAUSED" in frame
