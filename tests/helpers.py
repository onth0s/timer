"""Shared test helpers for the loop BDD step definitions.

``run_loop_mocked`` runs ``countdown.__main__.run_countdown`` with every
OS-touching call (clock, terminal, keypresses, ANSI, output) replaced by
FakeClock / MockKeys / no-op mocks so ZERO real time or I/O happens.
"""

from __future__ import annotations

from unittest.mock import patch


def run_loop_mocked(
    clock,
    keys,
    monkeypatch,
    *,
    total_seconds=0,
    count_up=False,
    max_pulses=0,
):
    """Run ``run_countdown`` with every OS-touching call replaced by mocks.

    Returns the list of integers that were 'displayed' during the loop.
    """
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

    from countdown.__main__ import run_countdown

    null_pulse = lambda lines: None  # noqa: E731
    with patch("builtins.print"):  # suppress ANSI escape codes
        run_countdown(
            total_seconds,
            pulse_fn=null_pulse,
            count_up=count_up,
            max_pulses=max_pulses,
        )

    return displayed
