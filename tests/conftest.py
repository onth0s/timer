"""Shared test infrastructure — FakeClock, MockKeys, and fixtures.

No real time calls anywhere in the test suite.
Every tick of the timer loop is driven by FakeClock, a plain integer counter.
"""

from __future__ import annotations

import pytest


class FakeClock:
    """Drop-in replacement for time.time / time.sleep — zero OS calls.

    Advancing time:
        clock.sleep(5)           # instantly adds 5.0 to internal counter
        clock.tick()             # adds 1
        clock.t = 42             # set directly

    Queued exceptions:
        clock.raise_at(10, KeyboardInterrupt())
        # Next sleep() whose range covers t=10 raises the exception.
    """

    def __init__(self) -> None:
        self.t: float = 0.0
        self._raises: dict[float, BaseException] = {}

    def time(self) -> float:
        """Return the current fake time."""
        return self.t

    def sleep(self, seconds: float) -> None:
        """Advance the clock by seconds; raise any exception queued in range."""
        target = self.t + seconds
        for trigger in sorted(k for k in self._raises if self.t <= k <= target):
            exc = self._raises.pop(trigger)
            self.t = trigger
            raise exc
        self.t = target

    def tick(self) -> None:
        """Advance the clock by exactly 1 second."""
        self.sleep(1.0)

    def raise_at(self, t: float, exc: BaseException) -> None:
        """Queue an exception to be raised when the clock passes t."""
        self._raises[t] = exc


class MockKeys:
    """Queued keypress source — pure lists, zero OS calls.

    Usage:
        keys = MockKeys(clock)
        keys.queue_at(t=2.0, key="q")
        monkeypatch.setattr("countdown.__main__.check_for_keypress", keys.check)
        monkeypatch.setattr("countdown.__main__.read_key", keys.read)
    """

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self._presses: list[tuple[float, str]] = []

    def queue_at(self, t: float, key: str) -> None:
        """Queue a keypress to fire when clock.t >= t."""
        self._presses.append((t, key))

    def check(self) -> bool:
        """Return True if any queued key is ready to fire."""
        return any(self._clock.t >= trig for trig, _ in self._presses)

    def read(self) -> str:
        """Pop and return the first ready keypress, or empty string."""
        for i, (trig, key) in enumerate(self._presses):
            if self._clock.t >= trig:
                self._presses.pop(i)
                return key
        return ""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_clock() -> FakeClock:
    """Return a fresh FakeClock."""
    return FakeClock()


@pytest.fixture
def fake_terminal_size(monkeypatch):
    """Return a callable that patches get_terminal_size to a fixed (w, h)."""
    import os

    def _set(w: int, h: int):
        monkeypatch.setattr(
            "countdown.display.get_terminal_size",
            lambda **_: os.terminal_size((w, h)),
        )

    return _set


@pytest.fixture
def runner():
    """Return a Click CliRunner."""
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def ctx() -> dict:
    """Shared mutable context dict for BDD step communication."""
    return {}
