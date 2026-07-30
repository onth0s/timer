"""Tests for count-up mode, timeout epoch recording, and exit duration summary."""

from countdown import __main__, timer


def test_get_number_lines_count_up_dynamic_formatting():
    """Verify dynamic glyph scaling in count-up mode."""
    chars = {
        "0": "000\n000\n000",
        "1": "111\n111\n111",
        "5": "555\n555\n555",
        ":": " : \n : \n : ",
    }
    # < 60s -> SS (e.g. '05')
    lines_5s = timer.get_number_lines(5, chars, count_up=True)
    assert len(lines_5s) == 3
    # 60s -> 1m00s (01:00)
    lines_60s = timer.get_number_lines(60, chars, count_up=True)
    assert ":" in lines_60s[0]
    # 3600s -> 1h00m00s (01:00:00)
    lines_1h = timer.get_number_lines(3600, chars, count_up=True)
    assert lines_1h[0].count(":") == 2


def test_count_up_mode_exit_summary(runner, fake_terminal_size, fake_clock, monkeypatch):
    """Verify bare timer invocation runs in count-up mode and outputs rich summary."""
    fake_terminal_size(40, 20)

    # Trigger exit after 2 seconds fake clock
    fake_clock.raises = {2: KeyboardInterrupt()}

    result = runner.invoke(__main__.main, [])
    assert result.exit_code == 0
    assert "Timer Summary" in result.output
    assert "Timer ran for" in result.output


def test_countdown_timeout_exit_delay_summary(runner, fake_terminal_size, fake_clock):
    """Verify countdown records zero epoch and displays time to exit after timeout."""
    fake_terminal_size(40, 20)

    result = runner.invoke(__main__.main, ["run", "2s"])
    assert result.exit_code == 0
    assert "Timer Summary" in result.output
    assert "Timer completed" in result.output
    assert "Time to exit after timeout" in result.output
