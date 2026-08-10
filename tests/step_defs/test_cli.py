"""BDD step definitions for cli.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from countdown.__main__ import main
from countdown.config import Config
from tests.conftest import FakeClock, MockKeys

scenarios("cli.feature")


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse('the CLI is invoked with "{args}"'), target_fixture="ctx")
def given_cli_invoked(args, runner, tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    monkeypatch.setattr(Config, "path", p)
    clock = FakeClock()
    keys = MockKeys(clock)
    return {
        "args": args.split(),
        "runner": runner,
        "clock": clock,
        "keys": keys,
        "result": None,
    }


@given("the CLI is invoked with no arguments", target_fixture="ctx")
def given_cli_invoked_bare(runner, tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    monkeypatch.setattr(Config, "path", p)
    clock = FakeClock()
    keys = MockKeys(clock)
    return {
        "args": [],
        "runner": runner,
        "clock": clock,
        "keys": keys,
        "result": None,
    }


@given("the clock is mocked (integer counter, no real sleep)")
def given_clock_mocked(ctx, monkeypatch):
    monkeypatch.setattr("countdown.__main__.time", ctx["clock"].time)
    monkeypatch.setattr("countdown.__main__.sleep", ctx["clock"].sleep)


@given("the clock is mocked")
def given_clock_mocked_short(ctx, monkeypatch):
    monkeypatch.setattr("countdown.__main__.time", ctx["clock"].time)
    monkeypatch.setattr("countdown.__main__.sleep", ctx["clock"].sleep)


@given("keypresses are mocked to never fire", target_fixture="ctx")
def given_no_keypresses(ctx, monkeypatch):
    monkeypatch.setattr("countdown.__main__.check_for_keypress", lambda: False)
    monkeypatch.setattr("countdown.terminal.check_for_keypress", lambda: False)
    monkeypatch.setattr("countdown.__main__.setup_terminal", lambda: None)
    monkeypatch.setattr("countdown.__main__.restore_terminal", lambda s: None)
    monkeypatch.setattr("countdown.__main__.enable_ansi_escape_codes", lambda: None)

    original_rc = ctx.get("_original_rc")
    if not original_rc:
        from countdown import __main__ as main_mod

        orig = main_mod.run_countdown

        def wrapped(total_seconds, pulse_fn=None, max_pulses=1, **kwargs):
            return orig(total_seconds, pulse_fn=pulse_fn, max_pulses=1, **kwargs)

        monkeypatch.setattr(main_mod, "run_countdown", wrapped)
    return ctx


@given(parsers.parse("a quit keypress fires after {ticks:d} ticks"))
def given_quit_after_ticks_cli(ctx, ticks, monkeypatch):
    ctx["keys"].queue_at(t=float(ticks), key="q")
    monkeypatch.setattr("countdown.__main__.check_for_keypress", ctx["keys"].check)
    monkeypatch.setattr("countdown.__main__.read_key", ctx["keys"].read)
    monkeypatch.setattr("countdown.__main__.drain_keypresses", lambda: None)
    monkeypatch.setattr("countdown.__main__.setup_terminal", lambda: None)
    monkeypatch.setattr("countdown.__main__.restore_terminal", lambda s: None)
    monkeypatch.setattr("countdown.__main__.enable_ansi_escape_codes", lambda: None)


@when("the command completes")
def when_command_completes(ctx):
    # Pass input if prompt might be triggered
    ctx["result"] = ctx["runner"].invoke(main, ctx["args"])


@then(parsers.parse("the exit code should be {code:d}"))
def then_exit_code(ctx, code):
    assert ctx["result"].exit_code == code, (
        f"Expected exit code {code}, got {ctx['result'].exit_code}. Output:\n{ctx['result'].output}"
    )


@then("the exit code should not be 0")
def then_exit_code_non_zero(ctx):
    assert ctx["result"].exit_code != 0


@then("the output should contain summary text")
def then_output_contains_summary(ctx):
    output = ctx["result"].output
    assert "Timer stopped early" in output or "Timer completed" in output, (
        f"Expected summary in output. Actual output:\n{output}"
    )


@then(parsers.parse('the output should contain "{text}"'))
def then_output_contains_text(ctx, text):
    assert text in ctx["result"].output, (
        f"Expected {text!r} in output. Actual output:\n{ctx['result'].output}"
    )


def test_cli_target_time_and_dash_args(runner, tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    monkeypatch.setattr(Config, "path", p)

    from countdown import __main__ as main_mod

    ran_seconds = []

    def mock_run_countdown(total_seconds, **kwargs):
        ran_seconds.append(total_seconds)

    monkeypatch.setattr(main_mod, "run_countdown", mock_run_countdown)

    from datetime import datetime

    now = datetime(2026, 8, 10, 15, 0, 0)

    class MockDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr("countdown.timer.datetime", MockDateTime)

    res1 = runner.invoke(main, ["-16:40"])
    assert res1.exit_code == 0
    assert ran_seconds[-1] == 6000

    res2 = runner.invoke(main, ["-4:40PM"])
    assert res2.exit_code == 0
    assert ran_seconds[-1] == 6000

    res3 = runner.invoke(main, [":01:20"])
    assert res3.exit_code == 0
    assert ran_seconds[-1] == 80

    res4 = runner.invoke(main, ["4:40"])
    assert res4.exit_code == 0
    assert ran_seconds[-1] == 16800

    res5 = runner.invoke(main, ["-5s"])
    assert res5.exit_code == 0
    assert ran_seconds[-1] == 5

