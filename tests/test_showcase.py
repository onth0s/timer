"""Tests for the showcase subcommand and run_showcase helper."""

from unittest.mock import patch

import pytest

from countdown import showcase as showcase_mod
from countdown.__main__ import main

# ============================================================================
# Constants
# ============================================================================


def test_showcase_modes_alphabetical():
    """SHOWCASE_MODES is sorted alphabetically."""
    assert showcase_mod.SHOWCASE_MODES == ("ansi", "drawille", "ghostprint", "rich", "smooth")


def test_showcase_builders_and_resetters_complete():
    """Every showcase mode has a builder and a resetter."""
    for mode in showcase_mod.SHOWCASE_MODES:
        assert mode in showcase_mod._BUILDERS
        assert mode in showcase_mod._RESETTERS
    for builder in showcase_mod._BUILDERS.values():
        assert callable(builder)


# ============================================================================
# build_frame public exports
# ============================================================================


def test_ansi_build_frame_returns_string():
    from countdown.pulses.ansi import build_frame

    lines = ["ab", "cd"]
    out = build_frame(lines, 0.0)
    assert isinstance(out, str)
    assert "\x1b[" in out


def test_smooth_build_frame_returns_string():
    from countdown.pulses.smooth import build_frame

    lines = ["ab", "cd"]
    out = build_frame(lines, 0.0)
    assert isinstance(out, str)
    assert "\x1b[" in out


def test_ghostprint_build_frame_returns_string():
    from countdown.pulses.ghostprint import build_frame

    lines = ["ab", "cd"]
    out = build_frame(lines, 0.0)
    assert isinstance(out, str)


def test_drawille_build_frame_returns_string():
    from countdown.pulses.drawille import build_frame

    lines = ["ab", "cd"]
    out = build_frame(lines, 0.0)
    assert isinstance(out, str)


def test_rich_build_frame_returns_string():
    from countdown.pulses.rich import build_frame

    lines = ["ab", "cd"]
    out = build_frame(lines, 0.0)
    assert isinstance(out, str)


# ============================================================================
# CLI command
# ============================================================================


def test_showcase_help(runner):
    result = runner.invoke(main, ["showcase", "--help"])
    assert result.exit_code == 0
    assert "time" in result.output.lower()
    assert "random" in result.output.lower()
    assert "once" in result.output.lower()


def test_showcase_positional_duration_calls_run_showcase(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase", "1"])
        assert result.exit_code == 0
        assert mock_run.called
        assert mock_run.call_args[0][0] == pytest.approx(1.0)


def test_showcase_time_flag_overrides_positional(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase", "1", "--time", "5"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][0] == pytest.approx(5.0)


def test_showcase_short_flag_overrides_positional(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase", "1", "-t", "3"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][0] == pytest.approx(3.0)


def test_showcase_default_interval_is_three(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][0] == pytest.approx(3.0)


def test_showcase_invalid_interval_rejected(runner):
    result = runner.invoke(main, ["showcase", "--time", "0"])
    assert result.exit_code != 0


def test_showcase_negative_interval_rejected(runner):
    result = runner.invoke(main, ["showcase", "--time", "-1"])
    assert result.exit_code != 0


def test_showcase_invalid_positional_rejected(runner):
    result = runner.invoke(main, ["showcase", "foo"])
    assert result.exit_code != 0


def test_showcase_once_flag_passed(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase", "--once"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][2] is True


def test_showcase_short_once_flag(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase", "-o"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][2] is True


def test_showcase_random_flag_passed(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase", "--random"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][1] is True


def test_showcase_default_shuffle_is_false(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][1] is False


def test_showcase_default_once_is_false(runner):
    with patch("countdown.showcase.run_showcase") as mock_run:
        result = runner.invoke(main, ["showcase"])
        assert result.exit_code == 0
        assert mock_run.call_args[0][2] is False


# ============================================================================
# run_showcase integration (mocked)
# ============================================================================


def _patch_run_showcase_io(monkeypatch):
    """Patch terminal/print setup so run_showcase runs without a real TTY."""
    monkeypatch.setattr(showcase_mod, "setup_terminal", lambda: None)
    monkeypatch.setattr(showcase_mod, "restore_terminal", lambda x: None)
    import builtins

    monkeypatch.setattr(builtins, "print", lambda *a, **kw: None)


def test_run_showcase_cycles_modes(
    fake_terminal_size, fake_clock, monkeypatch
):
    fake_terminal_size(40, 20)

    calls = []

    def fake_render(mode, lines, interval):
        calls.append(mode)
        return True  # segment completed

    monkeypatch.setattr(showcase_mod, "_render_segment", fake_render)
    monkeypatch.setattr(showcase_mod, "_render_asciimatics_segment", lambda lines, _i: True)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", lambda: False)
    _patch_run_showcase_io(monkeypatch)

    showcase_mod.run_showcase(interval=1.0, shuffle=False, once=True)

    assert sorted(calls) == sorted(["ansi", "drawille", "ghostprint", "rich", "smooth"])


def test_run_showcase_once_exits_after_one_cycle(
    fake_terminal_size, fake_clock, monkeypatch
):
    fake_terminal_size(40, 20)

    cycles = []

    def fake_render(mode, lines, interval):
        cycles.append(mode)
        return True  # segment completed

    monkeypatch.setattr(showcase_mod, "_render_segment", fake_render)
    monkeypatch.setattr(showcase_mod, "_render_asciimatics_segment", lambda lines, _i: True)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", lambda: False)
    _patch_run_showcase_io(monkeypatch)

    showcase_mod.run_showcase(interval=0.01, shuffle=False, once=True)

    # 5 standard modes (asciimatics is separate, not counted here)
    assert len(cycles) == 5


def test_run_showcase_exits_on_keypress(
    fake_terminal_size, fake_clock, monkeypatch
):
    fake_terminal_size(40, 20)

    visited = []

    def fake_render(mode, lines, interval):
        visited.append(mode)
        return False  # keypress triggered exit

    def fake_check():
        return True

    monkeypatch.setattr(showcase_mod, "_render_segment", fake_render)
    monkeypatch.setattr(showcase_mod, "_render_asciimatics_segment", lambda lines, _i: False)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", fake_check)
    _patch_run_showcase_io(monkeypatch)

    showcase_mod.run_showcase(interval=0.01, shuffle=False, once=False)

    assert len(visited) == 1


def test_run_showcase_handles_keyboard_interrupt(
    fake_terminal_size, fake_clock, monkeypatch
):
    fake_terminal_size(40, 20)

    def fake_render(mode, lines, interval):
        raise KeyboardInterrupt

    monkeypatch.setattr(showcase_mod, "_render_segment", fake_render)
    monkeypatch.setattr(showcase_mod, "_render_asciimatics_segment", lambda lines, _i: True)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", lambda: False)
    _patch_run_showcase_io(monkeypatch)

    showcase_mod.run_showcase(interval=0.01, shuffle=False, once=True)


def test_run_showcase_random_shuffles_each_cycle(
    fake_terminal_size, fake_clock, monkeypatch
):
    fake_terminal_size(40, 20)

    def fake_shuffle(seq):
        seq.reverse()

    monkeypatch.setattr(showcase_mod.random, "shuffle", fake_shuffle)

    cycles = []

    def fake_render(mode, lines, interval):
        cycles.append(mode)
        return True  # segment completed

    monkeypatch.setattr(showcase_mod, "_render_segment", fake_render)
    monkeypatch.setattr(showcase_mod, "_render_asciimatics_segment", lambda lines, _i: True)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", lambda: False)
    _patch_run_showcase_io(monkeypatch)

    # Patch time/sleep so the infinite loop eventually exits
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])
    monkeypatch.setattr(
        showcase_mod,
        "sleep",
        lambda s: elapsed.__setitem__(0, elapsed[0] + s),
    )

    # Run until we've done at least one full cycle
    import builtins

    original_print = builtins.print

    call_count = [0]

    def counting_print(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] > 1000:
            raise KeyboardInterrupt
        original_print(*args, **kwargs)

    # Override with a counting print that bails after enough frames
    monkeypatch.setattr(builtins, "print", lambda *a, **kw: None)

    # Bounded iterations: monkeypatch _render_segment to bail after 10 calls
    cycles.clear()
    iteration = [0]

    def bounded_render(mode, lines, interval):
        cycles.append(mode)
        iteration[0] += 1
        if iteration[0] >= 10:
            return False
        return True

    monkeypatch.setattr(showcase_mod, "_render_segment", bounded_render)

    showcase_mod.run_showcase(interval=0.01, shuffle=True, once=False)

    assert len(cycles) >= 5
    assert sorted(set(cycles)) == ["ansi", "drawille", "ghostprint", "rich", "smooth"]


# ============================================================================
# _render_segment helper
# ============================================================================


def test_render_segment_resets_phase_before_rendering(monkeypatch):
    calls = []

    def fake_resetter():
        calls.append("reset")

    def fake_check():
        return False

    fake_lines = ["a", "b"]
    monkeypatch.setattr(showcase_mod, "_RESETTERS", {"ansi": fake_resetter})
    monkeypatch.setattr(showcase_mod, "_BUILDERS", {"ansi": lambda lines, p: "frame"})
    monkeypatch.setattr(showcase_mod, "check_for_keypress", fake_check)
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])
    monkeypatch.setattr(
        showcase_mod,
        "sleep",
        lambda s: elapsed.__setitem__(0, elapsed[0] + s),
    )

    showcase_mod._render_segment("ansi", fake_lines, interval=0.001)

    assert "reset" in calls


def test_render_segment_exits_early_on_keypress(monkeypatch):
    check_calls = [False, True]

    def fake_check():
        return check_calls.pop(0) if check_calls else False

    fake_lines = ["a"]
    monkeypatch.setattr(showcase_mod, "_RESETTERS", {"ansi": lambda: None})
    monkeypatch.setattr(showcase_mod, "_BUILDERS", {"ansi": lambda lines, p: "f"})
    monkeypatch.setattr(showcase_mod, "check_for_keypress", fake_check)
    monkeypatch.setattr(showcase_mod, "sleep", lambda s: None)
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])

    result = showcase_mod._render_segment("ansi", fake_lines, interval=10.0)
    assert result is False


def test_render_segment_returns_true_on_completion(monkeypatch):
    fake_lines = ["a"]
    monkeypatch.setattr(showcase_mod, "_RESETTERS", {"ansi": lambda: None})
    monkeypatch.setattr(showcase_mod, "_BUILDERS", {"ansi": lambda lines, p: "f"})
    monkeypatch.setattr(showcase_mod, "check_for_keypress", lambda: False)
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])
    monkeypatch.setattr(
        showcase_mod,
        "sleep",
        lambda s: elapsed.__setitem__(0, elapsed[0] + s),
    )

    result = showcase_mod._render_segment("ansi", fake_lines, interval=0.001)
    assert result is True


def test_render_segment_prepends_label(monkeypatch):
    """Each frame output starts with the mode name label."""
    captured_frames = []

    def fake_check():
        return False

    def fake_print(*args, **kwargs):
        if args:
            captured_frames.append(args[0])

    import builtins

    monkeypatch.setattr(builtins, "print", fake_print)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", fake_check)
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])
    monkeypatch.setattr(
        showcase_mod,
        "sleep",
        lambda s: elapsed.__setitem__(0, elapsed[0] + s),
    )

    fake_lines = ["a"]
    monkeypatch.setattr(showcase_mod, "_RESETTERS", {"ansi": lambda: None})
    monkeypatch.setattr(showcase_mod, "_BUILDERS", {"ansi": lambda lines, p: "frame"})

    showcase_mod._render_segment("ansi", fake_lines, interval=0.001)

    assert any("ansi" in f for f in captured_frames)


def test_render_segment_clears_before_each_frame(monkeypatch):
    """Every frame starts with CLEAR escape."""
    frames = []

    def fake_check():
        return False

    def fake_print(*args, **kwargs):
        if args:
            frames.append(args[0])

    import builtins

    monkeypatch.setattr(builtins, "print", fake_print)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", fake_check)
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])
    monkeypatch.setattr(
        showcase_mod,
        "sleep",
        lambda s: elapsed.__setitem__(0, elapsed[0] + s),
    )

    fake_lines = ["a"]
    monkeypatch.setattr(showcase_mod, "_RESETTERS", {"ansi": lambda: None})
    monkeypatch.setattr(showcase_mod, "_BUILDERS", {"ansi": lambda lines, p: "frame"})

    showcase_mod._render_segment("ansi", fake_lines, interval=0.001)

    assert all("\x1b[H\x1b[J" in f for f in frames)


def test_render_segment_preserves_leading_newlines(monkeypatch):
    """Builder output's leading newlines preserve proper centering.

    Showcase prints the label then the frame. Each builder's frame includes
    vertical centering padding (leading newlines). The label sits on row 1,
    and the frame's leading padding + content creates the centered layout.
    """
    captured = []

    def fake_check():
        return False

    def fake_print(*args, **kwargs):
        if args:
            captured.append(args[0])

    import builtins

    monkeypatch.setattr(builtins, "print", fake_print)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", fake_check)
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])
    monkeypatch.setattr(
        showcase_mod,
        "sleep",
        lambda s: elapsed.__setitem__(0, elapsed[0] + s),
    )

    fake_lines = ["a"]
    monkeypatch.setattr(showcase_mod, "_RESETTERS", {"ansi": lambda: None})

    def fake_builder(lines, phase):
        # Builder produces frame with vertical padding (8 newlines) + content
        return "\n" * 8 + "frame-content"

    monkeypatch.setattr(showcase_mod, "_BUILDERS", {"ansi": fake_builder})

    showcase_mod._render_segment("ansi", fake_lines, interval=0.001)

    assert captured, "should have captured at least one frame"
    output = captured[0]
    # Output structure: CLEAR + label + frame (no separator newline)
    clear_prefix = "\x1b[H\x1b[J"
    assert output.startswith(clear_prefix)
    after_clear = output[len(clear_prefix):]
    # Label appears immediately after CLEAR
    assert after_clear.startswith("ansi"), (
        f"expected 'ansi' label after CLEAR, got: {after_clear[:30]!r}"
    )
    # Frame's leading newlines should be preserved (not stripped)
    assert "\n\n\n\n\n" in output, "frame leading padding should be preserved"


def test_render_segment_handles_builder_without_leading_newlines(monkeypatch):
    """Builders that don't include padding should still work correctly."""
    captured = []

    def fake_check():
        return False

    def fake_print(*args, **kwargs):
        if args:
            captured.append(args[0])

    import builtins

    monkeypatch.setattr(builtins, "print", fake_print)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", fake_check)
    elapsed = [0.0]
    monkeypatch.setattr(showcase_mod, "time", lambda: elapsed[0])
    monkeypatch.setattr(
        showcase_mod,
        "sleep",
        lambda s: elapsed.__setitem__(0, elapsed[0] + s),
    )

    fake_lines = ["a"]
    monkeypatch.setattr(showcase_mod, "_RESETTERS", {"ansi": lambda: None})
    # No leading newlines
    monkeypatch.setattr(showcase_mod, "_BUILDERS", {"ansi": lambda lines, p: "content"})

    showcase_mod._render_segment("ansi", fake_lines, interval=0.001)

    assert captured
    # Output: CLEAR + label + frame (no double-newline issues)
    assert captured[0] == "\x1b[H\x1b[Jansicontent"
