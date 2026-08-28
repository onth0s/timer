"""Unit tests asserting centered framing and full-screen printing agree."""

from countdown.display import CLEAR, centered_frame, print_full_screen


def test_print_full_screen_matches_centered_frame(capsys, monkeypatch):
    """For plain (non-paused) input, print_full_screen must equal CLEAR + centered_frame.

    Both paths now share the same padding helpers; this locks that invariant so
    the two centering routes cannot drift apart again.
    """
    import os

    monkeypatch.setattr(
        "countdown.display.get_terminal_size",
        lambda *a, **kw: os.terminal_size((50, 20)),
    )
    lines = ["abc", "defg", "hij"]

    print_full_screen(lines)

    expected = CLEAR + centered_frame(lines, 50, 20)
    assert capsys.readouterr().out == expected
