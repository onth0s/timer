"""Wall-clock abstraction so timing is injectable and testable.

The run loop never calls ``time.time`` / ``time.sleep`` directly — it goes
through a ``Clock``. Production uses :class:`SystemClock`; tests inject a
fake clock (see ``tests.conftest.FakeClock``).
"""

from __future__ import annotations

import time as _time


class Clock:
    """Minimal timing interface used by the run loop."""

    def time(self) -> float:
        """Return the current time in seconds (float)."""
        raise NotImplementedError

    def sleep(self, seconds: float) -> None:
        """Block for approximately ``seconds`` seconds."""
        raise NotImplementedError


class SystemClock(Clock):
    """Real wall clock backed by the standard :mod:`time` module."""

    def time(self) -> float:
        """Return the real wall-clock time in seconds."""
        return _time.time()

    def sleep(self, seconds: float) -> None:
        """Block for approximately ``seconds`` seconds."""
        _time.sleep(seconds)


__all__ = ["Clock", "SystemClock"]
