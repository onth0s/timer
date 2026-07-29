"""Integration test cases for the CLI."""

import re

import pytest

from countdown import __main__


def clean_main_output(output):
    """Remove ANSI escape codes and whitespace at ends of lines."""
    output = re.sub(r"\033\[(\?\d+[hl]|[HJ])", "", output)
    output = re.sub(r" *\n", "\n", output)
    return output


def test_main_with_no_arguments(runner):
    """It shows help when run without arguments."""
    result = runner.invoke(__main__.main)
    # Should show help (not error)
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "config" in result.output  # config subcommand listed
    assert "timer" in result.output  # timer subcommand listed


def test_version_works(runner):
    """It can print the version."""
    result = runner.invoke(__main__.main, ["--version"])
    assert ", version" in result.stdout
    assert result.exit_code == 0


def test_main_3_seconds(runner, fake_terminal_size, fake_clock):
    # Use 40x20 terminal to select size 5 digits (33w <= 40, 5h+2 <= 20)
    fake_terminal_size(40, 20)
    result = runner.invoke(__main__.main, ["run", "3s"])
    assert result.exit_code == 0
    got = clean_main_output(result.stdout)
    # 3-second countdown shows 4 frames (3s + 00:00); verify the invariants
    # that protect against centering regressions:
    #   * exactly 4 frames of digit content separated by blank-row groups
    #   * each content line has 4 leading spaces (horizontal pad for 32-col
    #     content on a 40-col terminal: (40-32)//2 == 4)
    #   * no line ends with a trailing space after the final character.
    frames = got.split("\n\n\n\n\n\n\n")
    rendered_frames = [f for f in frames if "█" in f]
    assert len(rendered_frames) == 4, (
        f"expected 4 rendered frames, got {len(rendered_frames)}"
    )
    blocks = rendered_frames
    for block in blocks:
        if not block.strip():
            continue
        lines = block.splitlines()
        for line in lines:
            if "█" in line:
                assert not line.endswith("█ "), (
                    f"line should not have trailing space after glyph: {line!r}"
                )
                leading = len(line) - len(line.lstrip())
                # Acceptable horizontal pad: (40 - content_width)//2 where
                # content_width varies per row depending on which digits are
                # shown. Size-5 content on a 40-col terminal ranges from
                # 28 cols (narrow chars) to 32 cols (all zeros), so pad is in
                # [4, 6] inclusive.
                assert 4 <= leading <= 6, (
                    f"expected horizontal pad in [4, 6] for size-5 content on "
                    f"40-col terminal, got {leading}: {line!r}"
                )
    # 3 seconds + 1 to display 00:00, each sleeping ~1 second
    assert fake_clock.slept == pytest.approx(3 + 1, abs=0.01)
    assert fake_clock.elapsed == pytest.approx(3 + 1, abs=0.01)


def test_main_1_minute(runner, fake_terminal_size, fake_clock):
    # Use 40x10 terminal to select size 5 digits (33w <= 40, 5h+2 <= 10)
    fake_terminal_size(40, 10)

    # Raise exception after 11 seconds of fake sleep
    fake_clock.raises = {11: SystemExit(0)}

    result = runner.invoke(__main__.main, ["run", "1m"])
    got = clean_main_output(result.stdout)
    # 11 frames displayed before the SystemExit; verify centering/flicker
    # invariants: each content block has consistent horizontal pad (4 spaces
    # for 32-col content on 40-col terminal) and no trailing whitespace on
    # the final character of each line.
    rendered = [b for b in got.split("\n\n") if "█" in b]
    assert len(rendered) >= 10, (
        f"expected at least 10 rendered frames before exit, got {len(rendered)}"
    )
    for block in rendered:
        for line in block.splitlines():
            if "█" not in line:
                continue
            assert not line.endswith("█ "), (
                f"line should not have trailing space after glyph: {line!r}"
            )
            leading = len(line) - len(line.lstrip())
            assert 4 <= leading <= 6, (
                f"expected horizontal pad in [4, 6] for size-5 content on "
                f"40-col terminal, got {leading}: {line!r}"
            )


def test_main_10_minutes_has_600_clear_screens(
    runner,
    fake_terminal_size,
    fake_clock,
):
    fake_terminal_size(32, 10)
    result = runner.invoke(__main__.main, ["run", "10m"])
    # 10 minutes = 600 seconds + 1 to display 00:00
    assert fake_clock.slept == pytest.approx(10 * 60 + 1, abs=0.1)
    assert fake_clock.elapsed == pytest.approx(10 * 60 + 1, abs=0.1)
    assert result.stdout.count("\033[H\033[J") == 10 * 60 + 1


def test_main_enables_alt_buffer_and_hides_cursor_at_beginning(
    runner,
    fake_terminal_size,
    fake_clock,
):
    fake_terminal_size(32, 10)
    result = runner.invoke(__main__.main, ["run", "5m"])
    assert result.stdout.startswith("\033[?1049h\033[?25l")


def test_main_disable_alt_buffer_and_show_cursor_at_end(
    runner,
    fake_terminal_size,
    fake_clock,
):
    fake_terminal_size(32, 10)
    result = runner.invoke(__main__.main, ["run", "5m"])
    assert result.stdout.endswith("\033[?25h\033[?1049l")


def test_main_early_exit_still_shows_cursor_at_end(
    runner,
    fake_terminal_size,
    fake_clock,
):
    # Use 40x10 terminal to select size 5 digits (33w <= 40, 5h+2 <= 10)
    fake_terminal_size(40, 10)

    # Hit Ctrl+C after 4 seconds total sleep time (chunked sleep)
    fake_clock.raises = {4: KeyboardInterrupt()}

    result = runner.invoke(__main__.main, ["run", "15m"])
    # 4 iterations x 6 newlines each (2 padding + 4 between 5 content lines)
    # = 24 newlines, no trailing newline (end=""), so splitlines() gives 25
    assert len(result.stdout.splitlines()) == 25
    assert result.stdout.endswith("\033[?25h\033[?1049l")


def test_pause_key_triggers_pause(
    runner,
    fake_terminal_size,
    fake_clock,
    monkeypatch,
):
    """Test that pressing a pause key triggers the pause logic."""
    fake_terminal_size(40, 20)

    # Exit after a short time
    fake_clock.raises = {1: KeyboardInterrupt()}

    # Track whether pause key was detected
    pause_key_detected = [False]
    read_key_called = [False]

    def fake_check_for_keypress():
        # Return True once to simulate a keypress during first iteration
        if not pause_key_detected[0]:
            pause_key_detected[0] = True
            return True
        return False

    def fake_read_key():
        read_key_called[0] = True
        return " "  # Space bar (a pause key)

    def fake_drain():
        pass  # No additional keys to drain

    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)
    monkeypatch.setattr(__main__, "drain_keypresses", fake_drain)

    result = runner.invoke(__main__.main, ["run", "5s"])

    # The pause key should have been detected and read
    assert pause_key_detected[0], "Pause key detection should have been called"
    assert read_key_called[0], "read_key should have been called"
    # Output should contain the paused color since we pressed a pause key
    assert "\x1b[95m" in result.stdout, (
        "Should show paused color when pause key pressed"
    )


def test_non_pause_key_ignored(
    runner,
    fake_terminal_size,
    fake_clock,
    monkeypatch,
):
    """Test that non-pause keys are ignored during countdown."""
    fake_terminal_size(40, 20)
    fake_clock.raises = {1: KeyboardInterrupt()}

    # Track keypresses
    check_called = [False]
    read_key_called = [False]

    def fake_check_for_keypress():
        if not check_called[0]:
            check_called[0] = True
            return True
        return False

    def fake_read_key():
        read_key_called[0] = True
        return "x"  # Not a pause key

    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)

    result = runner.invoke(__main__.main, ["run", "5s"])

    # The key should have been read
    assert read_key_called[0], "read_key should have been called"
    # Output should NOT contain paused color since 'x' is not a pause key
    assert "\x1b[95m" not in result.stdout, (
        "Should not show paused color for non-pause key"
    )
    assert result.exit_code == 0


def test_sleep_exits_early_on_keypress(
    runner,
    fake_terminal_size,
    fake_clock,
    monkeypatch,
):
    """Test that sleep loop exits early when a key is pressed mid-sleep."""
    fake_terminal_size(40, 20)

    # Track sleep calls and use FakeClock for time control
    sleep_calls = []
    original_sleep = fake_clock.sleep

    def tracking_sleep(seconds):
        sleep_calls.append(seconds)
        original_sleep(seconds)
        if len(sleep_calls) >= 5:
            raise KeyboardInterrupt()

    monkeypatch.setattr("countdown.__main__.sleep", tracking_sleep)

    # Simulate keypress after 3rd sleep call
    def fake_check_for_keypress():
        # Return True on the 3rd sleep chunk to simulate keypress mid-sleep
        return len(sleep_calls) == 3

    def fake_read_key():
        return " "  # Pause key

    def fake_drain():
        pass

    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)
    monkeypatch.setattr(__main__, "drain_keypresses", fake_drain)

    result = runner.invoke(__main__.main, ["run", "10s"])
    assert result.exit_code == 0, result.output

    # Should have broken out of sleep loop early
    assert len(sleep_calls) >= 3, "Should have at least 3 sleep calls"
    first_iteration_sleeps = [s for s in sleep_calls[:3] if s == 0.05]
    assert len(first_iteration_sleeps) == 3, (
        "Should have 3 chunks of 0.05s before breaking"
    )


def test_resume_from_pause_exits_early(
    runner,
    fake_terminal_size,
    fake_clock,
    monkeypatch,
):
    """Test that when paused, pressing a key to resume exits the 0.05s sleep loop."""
    fake_terminal_size(40, 20)

    sleep_calls = []
    paused_state = [False]
    original_sleep = fake_clock.sleep

    def tracking_sleep(seconds):
        sleep_calls.append((seconds, paused_state[0]))
        original_sleep(seconds)
        if len(sleep_calls) >= 10:
            raise KeyboardInterrupt()

    monkeypatch.setattr("countdown.__main__.sleep", tracking_sleep)

    # Simulate: pause immediately, then resume after a few paused sleeps
    keypress_count = [0]

    def fake_check_for_keypress():
        keypress_count[0] += 1
        # First keypress: pause immediately (keypress 1)
        # Second keypress: resume after being paused (keypress 2)
        return keypress_count[0] in [1, 5]

    keys_to_return = [" ", " "]  # Space to pause, space to resume
    key_index = [0]

    def fake_read_key():
        key = keys_to_return[key_index[0]]
        key_index[0] = min(key_index[0] + 1, len(keys_to_return) - 1)
        return key

    def fake_drain():
        pass

    # Track pause state transitions
    original_print = __main__.print_full_screen

    def tracking_print(lines, paused=False):
        paused_state[0] = paused
        return original_print(lines, paused=paused)

    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)
    monkeypatch.setattr(__main__, "drain_keypresses", fake_drain)
    monkeypatch.setattr(__main__, "print_full_screen", tracking_print)

    result = runner.invoke(__main__.main, ["run", "10s"])
    assert result.exit_code == 0, result.output

    # Should have some paused sleeps (0.05) and some regular chunked sleeps (0.05)
    paused_sleeps = [s for s, p in sleep_calls if p]
    unpaused_sleeps = [s for s, p in sleep_calls if not p]

    assert len(paused_sleeps) > 0, "Should have some paused sleep periods"
    assert len(unpaused_sleeps) > 0, "Should have some unpaused sleep periods"


def test_add_time_with_plus_key(
    runner, fake_terminal_size, fake_clock, monkeypatch
):
    """Test that pressing + adds 30 seconds to the timer."""
    fake_terminal_size(40, 20)
    fake_clock.raises = {1: KeyboardInterrupt()}

    # Track the displayed times
    displayed_times = []
    original_get_number_lines = __main__.get_number_lines

    def fake_get_number_lines(seconds):
        displayed_times.append(seconds)
        return original_get_number_lines(seconds)

    def fake_check_for_keypress():
        # Return True once to simulate a keypress
        return len(displayed_times) == 1

    def fake_read_key():
        return "+"  # Plus key to add time

    def fake_drain():
        pass

    monkeypatch.setattr(__main__, "get_number_lines", fake_get_number_lines)
    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)
    monkeypatch.setattr(__main__, "drain_keypresses", fake_drain)

    result = runner.invoke(__main__.main, ["run", "1m"])
    assert result.exit_code == 0, result.output

    # Should have displayed 60s initially, then 90s after pressing +
    assert 60 in displayed_times, "Should display initial time of 60s"
    assert 90 in displayed_times, "Should display 90s after adding 30s"


def test_subtract_time_with_minus_key(
    runner,
    fake_terminal_size,
    fake_clock,
    monkeypatch,
):
    """Test that pressing - subtracts 30 seconds from the timer."""
    fake_terminal_size(40, 20)
    fake_clock.raises = {1: KeyboardInterrupt()}

    # Track the displayed times
    displayed_times = []
    original_get_number_lines = __main__.get_number_lines

    def fake_get_number_lines(seconds):
        displayed_times.append(seconds)
        return original_get_number_lines(seconds)

    def fake_check_for_keypress():
        # Return True once to simulate a keypress
        return len(displayed_times) == 1

    def fake_read_key():
        return "-"  # Minus key to subtract time

    def fake_drain():
        pass

    monkeypatch.setattr(__main__, "get_number_lines", fake_get_number_lines)
    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)
    monkeypatch.setattr(__main__, "drain_keypresses", fake_drain)

    result = runner.invoke(__main__.main, ["run", "1m"])
    assert result.exit_code == 0, result.output

    # Should have displayed 60s initially, then 30s after pressing -
    assert 60 in displayed_times, "Should display initial time of 60s"
    assert 30 in displayed_times, "Should display 30s after subtracting 30s"


def test_subtract_time_cannot_go_negative(
    runner,
    fake_terminal_size,
    fake_clock,
    monkeypatch,
):
    """Test that subtracting time stops at 0 (cannot go negative)."""
    fake_terminal_size(40, 20)
    fake_clock.raises = {1: KeyboardInterrupt()}

    # Track the displayed times
    displayed_times = []
    original_get_number_lines = __main__.get_number_lines

    def fake_get_number_lines(seconds):
        displayed_times.append(seconds)
        return original_get_number_lines(seconds)

    def fake_check_for_keypress():
        # Return True once to simulate a keypress
        return len(displayed_times) == 1

    def fake_read_key():
        return "-"  # Minus key to subtract time

    def fake_drain():
        pass

    monkeypatch.setattr(__main__, "get_number_lines", fake_get_number_lines)
    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)
    monkeypatch.setattr(__main__, "drain_keypresses", fake_drain)

    result = runner.invoke(__main__.main, ["run", "10s"])
    assert result.exit_code == 0, result.output

    # Should have displayed 10s initially, then 0s (not -20s) after pressing -
    assert 10 in displayed_times, "Should display initial time of 10s"
    assert 0 in displayed_times, (
        "Should display 0s (not negative) after subtracting 30s"
    )
    assert all(t >= 0 for t in displayed_times), (
        "All displayed times should be non-negative"
    )


def test_q_key_quits_timer(runner, fake_terminal_size, fake_clock, monkeypatch):
    """Test that pressing 'q' exits the timer."""
    fake_terminal_size(40, 20)
    keypress_count = [0]

    def fake_check_for_keypress():
        keypress_count[0] += 1
        # Return True on first check to simulate pressing q
        return keypress_count[0] == 1

    def fake_read_key():
        return "q"  # Press q to quit

    monkeypatch.setattr(__main__, "check_for_keypress", fake_check_for_keypress)
    monkeypatch.setattr(__main__, "read_key", fake_read_key)

    result = runner.invoke(__main__.main, ["run", "10m"])

    # Should exit cleanly with code 0
    assert result.exit_code == 0
    # Should have shown cursor and disabled alt buffer on exit
    assert result.stdout.endswith("\033[?25h\033[?1049l")


def test_no_arguments_shows_help(runner):
    """Test that running without arguments shows help message."""
    result = runner.invoke(__main__.main, [])

    # Should exit with code 0 (not an error)
    assert result.exit_code == 0
    # Should show usage information with subcommands
    assert "Usage:" in result.output
    assert "config" in result.output
    assert "timer" in result.output


def test_bare_duration_forwards_to_timer_subcommand(
    runner, fake_terminal_size, fake_clock
):
    """`timer 3s` (no explicit subcommand) still runs the countdown."""
    fake_terminal_size(40, 20)
    result = runner.invoke(__main__.main, ["3s"])
    assert result.exit_code == 0


def test_bare_invalid_duration_reports_error(runner):
    """`timer bogus` shows error, not 'no such command'."""
    result = runner.invoke(__main__.main, ["bogus"])
    assert result.exit_code != 0
    # Error should mention the bad value, not "no such command"
    output = result.output + (result.stderr or "")
    assert "bogus" in output
    assert "no such command" not in output.lower()


# ============================================================================
# Config subcommand tests
# ============================================================================


def test_config_init_creates_file(runner, tmp_config):
    """Timer config init writes default config.yaml."""
    from countdown.config import Config

    result = runner.invoke(__main__.main, ["config", "init"])
    assert result.exit_code == 0
    assert tmp_config.exists()
    loaded = Config.load()
    assert loaded.get("anim") == "rich"


def test_config_init_when_already_exists(runner, tmp_config):
    """Timer config init overwrites with defaults (idempotent)."""
    tmp_config.write_text("anim: drawille\n")

    result = runner.invoke(__main__.main, ["config", "init"])
    assert result.exit_code == 0
    from countdown.config import Config

    loaded = Config.load()
    assert loaded.get("anim") == "rich"  # overwritten to default


def test_config_path_prints_path(runner, tmp_config):
    """Timer config path prints the config file path."""
    result = runner.invoke(__main__.main, ["config", "path"])
    assert result.exit_code == 0
    assert str(tmp_config) in result.output


def test_config_show_prints_table(runner, tmp_config):
    """Timer config show prints current config."""
    tmp_config.write_text("anim: drawille\n")
    result = runner.invoke(__main__.main, ["config", "show"])
    assert result.exit_code == 0
    assert "anim" in result.output
    assert "drawille" in result.output


def test_config_anim_with_no_arg_shows_current(runner, tmp_config):
    """Timer config anim (no arg) prints current mode."""
    tmp_config.write_text("anim: drawille\n")
    result = runner.invoke(__main__.main, ["config", "anim"])
    assert result.exit_code == 0
    assert "drawille" in result.output


def test_config_anim_persists_valid_mode(runner, tmp_config):
    """Timer config anim <MODE> persists the mode to disk."""
    from countdown.config import Config

    result = runner.invoke(__main__.main, ["config", "anim", "drawille"])
    assert result.exit_code == 0
    assert tmp_config.exists()
    loaded = Config.load()
    assert loaded.get("anim") == "drawille"


def test_config_anim_rejects_invalid_mode(runner, tmp_config):
    """Timer config anim <INVALID> exits non-zero with helpful error."""
    from countdown.pulses import VALID_ANIM_MODES

    result = runner.invoke(__main__.main, ["config", "anim", "neon-rave"])
    assert result.exit_code != 0
    assert "neon-rave" in result.output
    for mode in VALID_ANIM_MODES:
        assert mode in result.output
    # Should NOT have created/written the file
    assert not tmp_config.exists()


def test_timer_subcommand_invalid_anim_exits_error(runner, tmp_config):
    """Timer --anim INVALID exits non-zero listing valid modes."""
    from countdown.pulses import VALID_ANIM_MODES

    result = runner.invoke(__main__.main, ["run", "--anim", "neon-rave", "3s"])
    assert result.exit_code != 0
    output = result.output + (result.stderr or "")
    assert "neon-rave" in output
    for mode in VALID_ANIM_MODES:
        assert mode in output


def test_help_uses_rich_styling(runner):
    """--help output is rendered (rich-click adds markup)."""
    result = runner.invoke(__main__.main, ["--help"])
    assert result.exit_code == 0
    # rich-click may add ANSI markup; we just verify it contains expected text
    assert "Countdown" in result.output or "countdown" in result.output


def test_config_subcommand_help(runner):
    """Timer config --help lists config subcommands."""
    result = runner.invoke(__main__.main, ["config", "--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "show" in result.output
    assert "path" in result.output
    assert "anim" in result.output
