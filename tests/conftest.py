"""PyTest configuration."""

import os

import pytest
from _pytest.assertion import truncate
from click.testing import CliRunner

truncate.DEFAULT_MAX_LINES = 40
truncate.DEFAULT_MAX_CHARS = 40 * 80


def pytest_assertrepr_compare(
    op,
    left,
    right,
):  # pragma: nocover
    if (
        isinstance(left, str)
        and isinstance(right, str)
        and "█" in right
        and op == "=="
    ):
        return [
            "Big number string comparison doesn't match",
            "Got:",
            *left.splitlines(),
            "Expected:",
            *right.splitlines(),
            "",
            f"Repr Comparison: {left!r} != {right!r}",
        ]
    return None


class FakeClock:
    """Fake time.time() and time.sleep() that advance together.

    Since run_countdown uses time() for loop control and sleep() for pacing,
    both must be faked in sync to avoid tests running in real time.
    """

    def __init__(self, *, raises={}, drift_per_sleep=0.0):  # noqa: B006
        self.start = 1_000_000.0
        self.current = self.start
        self.slept = 0
        self.raises = dict(raises)
        self.drift_per_sleep = drift_per_sleep

    @property
    def elapsed(self):
        """Total wall clock time elapsed (including any drift)."""
        return self.current - self.start

    def time(self):
        return self.current

    def sleep(self, seconds):
        self.current += seconds + self.drift_per_sleep
        self.slept += seconds
        # Check for exception with floating point tolerance
        for trigger_time, exception in self.raises.items():
            if abs(self.slept - trigger_time) < 0.001:
                raise exception


@pytest.fixture
def fake_clock(monkeypatch):
    """Fixture that patches time/sleep with a FakeClock.

    Returns the clock instance. Set attributes like ``raises`` or
    ``drift_per_sleep`` before invoking the CLI to customize behavior.
    """
    clock = FakeClock()
    monkeypatch.setattr("countdown.__main__.sleep", clock.sleep)
    monkeypatch.setattr("countdown.__main__.time", clock.time)
    return clock


@pytest.fixture
def fake_terminal_size(monkeypatch):
    """Factory fixture: sets a fake terminal size for display calculations."""

    def _set_size(columns, lines):
        def get_terminal_size(fallback=(columns, lines)):
            return os.terminal_size(fallback)

        monkeypatch.setattr(
            "countdown.display.get_terminal_size", get_terminal_size
        )

    return _set_size


@pytest.fixture
def runner():
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


@pytest.fixture(autouse=True)
def no_pulse(monkeypatch):
    """Auto-disable pulse phase so existing tests don't hang on keypress.

    Tests that exercise the pulse phase explicitly should set max_pulses
    on the patched run_countdown. Returns the unwrapped run_countdown
    for use by tests that want to bypass the default.
    """
    from countdown import __main__
    from countdown.pulses.ansi import pulse_ansi

    original = __main__.run_countdown._original  # type: ignore[attr-defined]

    def wrapped(total_seconds, pulse_fn=None, max_pulses=0):
        if pulse_fn is None:
            pulse_fn = pulse_ansi
        return original(total_seconds, pulse_fn=pulse_fn, max_pulses=max_pulses)

    monkeypatch.setattr(__main__, "run_countdown", wrapped)
    return original


@pytest.fixture
def unwrapped_run_countdown(no_pulse):
    """Provide direct access to the unwrapped run_countdown."""
    return no_pulse


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirect Config.path to a tmp file for the duration of the test."""
    from countdown import config as config_mod

    target = tmp_path / "config.yaml"
    monkeypatch.setattr(config_mod.Config, "path", target)
    return target
