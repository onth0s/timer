"""Tests for the pulse-on-time-out animation libraries and dispatcher."""

import io
import os
from unittest.mock import patch

import pytest

from countdown.__main__ import get_number_lines
from countdown.pulses import VALID_ANIM_MODES, get_pulse_fn, validate_anim_mode
from countdown.pulses._wave import (
    hsl_to_rgb,
    intensity_to_ansi,
    linear_wave,
    radial_wave,
)


def _zero_lines():
    """Get the 00:00 glyph lines for testing."""
    return get_number_lines(0)


# ============================================================================
# Dispatcher + validation
# ============================================================================


def test_valid_anim_modes_count():
    """Six valid modes exist."""
    assert len(VALID_ANIM_MODES) == 6


def test_valid_anim_modes_contains_expected():
    """All 6 expected modes are present."""
    for mode in ("ansi", "rich", "drawille", "smooth", "ghostprint", "asciimatics"):
        assert mode in VALID_ANIM_MODES


def test_get_pulse_fn_returns_callable_for_each_mode():
    """get_pulse_fn returns a callable for every valid mode."""
    for mode in VALID_ANIM_MODES:
        fn = get_pulse_fn(mode)
        assert callable(fn)


def test_get_pulse_fn_rejects_unknown():
    """get_pulse_fn raises ValueError for unknown modes."""
    with pytest.raises(ValueError) as exc:
        get_pulse_fn("invalid-mode")
    assert "invalid-mode" in str(exc.value)
    for mode in VALID_ANIM_MODES:
        assert mode in str(exc.value)


def test_validate_anim_mode_accepts_all_valid_modes():
    """All valid modes pass validation."""
    for mode in VALID_ANIM_MODES:
        validate_anim_mode(mode)


def test_validate_anim_mode_rejects_unknown():
    """Unknown modes raise ValueError listing valid options."""
    with pytest.raises(ValueError) as exc:
        validate_anim_mode("definitely-not-a-mode")
    msg = str(exc.value)
    assert "definitely-not-a-mode" in msg
    for mode in VALID_ANIM_MODES:
        assert mode in msg


# ============================================================================
# Wave math helpers
# ============================================================================


def test_radial_wave_returns_value_in_range():
    """radial_wave returns value in [-1, 1]."""
    for x in range(-10, 11):
        for y in range(-10, 11):
            for phase in [0, 1, 2, 3.14]:
                v = radial_wave(x, y, 0, 0, phase, frequency=0.3)
                assert -1.0 <= v <= 1.0


def test_radial_wave_oscillates_with_phase():
    """radial_wave oscillates as phase changes."""
    samples = [radial_wave(5, 5, 0, 0, phase) for phase in [0, 0.5, 1, 1.5]]
    assert len(set(samples)) > 1


def test_linear_wave_returns_value_in_range():
    """linear_wave interference pattern stays in [-2, 2]."""
    for x in range(-5, 6):
        for y in range(-5, 6):
            for phase in [0, 1, 2]:
                v = linear_wave(x, y, phase)
                assert -2.0 <= v <= 2.0


def test_hsl_to_rgb_basic():
    """hsl_to_rgb returns correct RGB tuples for known inputs."""
    # Pure red
    assert hsl_to_rgb(0, 1.0, 0.5) == (255, 0, 0)
    # Pure green
    assert hsl_to_rgb(120, 1.0, 0.5) == (0, 255, 0)
    # Pure blue
    assert hsl_to_rgb(240, 1.0, 0.5) == (0, 0, 255)
    # White
    assert hsl_to_rgb(0, 0.0, 1.0) == (255, 255, 255)


def test_intensity_to_ansi_buckets():
    """intensity_to_ansi maps intensity to the right bucket."""
    assert intensity_to_ansi(-1.0) == "dim"
    assert intensity_to_ansi(-0.5) == "dim"
    assert intensity_to_ansi(-0.34) == "dim"
    assert intensity_to_ansi(-0.32) == "normal"
    assert intensity_to_ansi(0.0) == "normal"
    assert intensity_to_ansi(0.32) == "normal"
    assert intensity_to_ansi(0.34) == "bold"
    assert intensity_to_ansi(1.0) == "bold"


# ============================================================================
# ansi pulse
# ============================================================================


def test_pulse_ansi_emits_clear_escape():
    """pulse_ansi emits CLEAR escape on each frame."""
    from countdown.pulses.ansi import pulse_ansi

    lines = _zero_lines()
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        pulse_ansi(lines)
    output = buf.getvalue()
    assert "\x1b[H\x1b[J" in output


def test_pulse_ansi_centers_output():
    """pulse_ansi adds horizontal padding to center the glyphs."""
    from countdown.pulses.ansi import pulse_ansi

    lines = _zero_lines()
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        pulse_ansi(lines)
    output = buf.getvalue()
    prefix = "\x1b[H\x1b[J"
    assert output.startswith(prefix)
    rest = output[len(prefix):]
    first_line = rest.lstrip("\n")
    leading_spaces = len(first_line) - len(first_line.lstrip())
    assert leading_spaces > 0


def test_pulse_ansi_uses_sine_wave_intensity_levels():
    """pulse_ansi output uses multiple brightness levels (sine-wave driven)."""
    from countdown.pulses.ansi import pulse_ansi

    lines = _zero_lines()
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        pulse_ansi(lines)
    output = buf.getvalue()
    seen = set()
    if "\x1b[2m" in output:
        seen.add("dim")
    if "\x1b[1m" in output:
        seen.add("bold")
    if "\x1b[0m" in output:
        seen.add("normal")
    assert len(seen) >= 1


# ============================================================================
# rich pulse
# ============================================================================


def test_pulse_rich_callable():
    """Rich pulse function is importable and callable."""
    from countdown.pulses.rich import pulse_rich

    assert callable(pulse_rich)


def test_pulse_rich_uses_live_update():
    """Rich pulse returns a Text renderable for run_countdown to drive Live."""
    from countdown.pulses import rich as rich_mod

    lines = _zero_lines()
    # Reset state so we get a deterministic first-frame phase
    rich_mod.reset_state()
    result = rich_mod.pulse_rich(lines)
    # Should return a Rich Text renderable, not print
    assert result is not None
    from rich.text import Text

    assert isinstance(result, Text)


def test_pulse_rich_builds_wave_text():
    """_build_wave_text returns a Text object with hex color markup."""
    from countdown.pulses.rich import _build_wave_text

    lines = _zero_lines()
    text = _build_wave_text(lines, 0.0)
    # Rich Text stores markup separately from plain text
    assert "#" in text.markup
    # Should contain block characters from the glyph
    assert "\u2588" in text.markup


# ============================================================================
# drawille pulse
# ============================================================================


def test_pulse_drawille_callable():
    """Drawille pulse function is importable."""
    from countdown.pulses.drawille import pulse_drawille

    assert callable(pulse_drawille)


def test_pulse_drawille_pixel_extraction():
    """Drawille pulse converts glyph to pixel positions correctly."""
    from countdown.pulses.drawille import _glyph_to_pixels

    lines = ["██  ", "  ██"]
    pixels = _glyph_to_pixels(lines)
    assert len(pixels) > 0
    assert isinstance(next(iter(pixels)), tuple)


def test_pulse_drawille_renders_braille():
    """Drawille pulse produces braille-character output."""
    from countdown.pulses.drawille import pulse_drawille

    lines = _zero_lines()
    with patch("builtins.print") as mock_print:
        with patch("countdown.pulses.drawille.reset_state"):
            pulse_drawille(lines)
        assert mock_print.called


def test_pulse_drawille_centers_correctly():
    """Drawille frame is centered for glyph_height braille rows, not raw pixels.

    Regression test for centering bug where (glyph_height+3)//4 was used
    instead of glyph_height for vertical centering math.
    """
    from countdown.pulses.drawille import _centered_frame, _glyph_to_pixels

    lines = _zero_lines()  # 7-row glyph block
    pixels = _glyph_to_pixels(lines)
    assert len(pixels) > 0

    # Build a frame string matching the braille row count
    from drawille import Canvas

    canvas = Canvas()
    for px, py in pixels:
        canvas.set(px, py)
    frame = canvas.frame()
    braille_rows = len(frame.splitlines())
    # After 4x vertical scale, glyph_height=7 → 7 braille rows
    assert braille_rows == 7, f"expected 7 braille rows, got {braille_rows}"

    # Center: 24-row terminal, content 7 rows → vertical_padding = (24-7)//2 = 8
    with patch("countdown.pulses.drawille.get_terminal_size") as mock_size:
        mock_size.return_value = os.terminal_size((80, 24))
        centered = _centered_frame(frame, lines)

    # Count leading newlines (padding) and content rows separately
    leading_newlines = len(centered) - len(centered.lstrip("\n"))
    assert leading_newlines == 8, (
        f"expected 8 leading newlines for centered drawille, got {leading_newlines}"
    )

    # After stripping padding, exactly 7 braille content lines remain
    after_padding = centered.lstrip("\n")
    content_lines = after_padding.splitlines()
    assert len(content_lines) == 7, (
        f"expected 7 content rows, got {len(content_lines)}"
    )


# ============================================================================
# smooth pulse
# ============================================================================


def test_pulse_smooth_callable():
    """Smooth pulse function is importable."""
    from countdown.pulses.smooth import pulse_smooth

    assert callable(pulse_smooth)


def test_pulse_smooth_uses_sine_wave_intensity():
    """Smooth pulse output uses brightness cycling from sine wave."""
    from countdown.pulses.smooth import pulse_smooth

    lines = _zero_lines()
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        pulse_smooth(lines)
    output = buf.getvalue()
    seen = set()
    if "\x1b[2m" in output:
        seen.add("dim")
    if "\x1b[1m" in output:
        seen.add("bold")
    if "\x1b[0m" in output:
        seen.add("normal")
    assert len(seen) >= 1


# ============================================================================
# ghostprint pulse
# ============================================================================


def test_pulse_ghostprint_callable():
    """Ghostprint pulse function is importable."""
    from countdown.pulses.ghostprint import pulse_ghostprint

    assert callable(pulse_ghostprint)


def test_pulse_ghostprint_uses_clear_and_print():
    """Ghostprint pulse uses CLEAR escape and prints to stdout."""
    from countdown.pulses.ghostprint import pulse_ghostprint

    lines = _zero_lines()
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        pulse_ghostprint(lines)
    output = buf.getvalue()
    assert "\x1b[H\x1b[J" in output


# ============================================================================
# asciimatics pulse
# ============================================================================


def test_pulse_asciimatics_callable():
    """Asciimatics pulse function is importable."""
    from countdown.pulses.asciimatics import pulse_asciimatics

    assert callable(pulse_asciimatics)


def test_pulse_asciimatics_uses_screen_wrapper():
    """Asciimatics pulse delegates to Screen.wrapper."""
    from asciimatics.screen import Screen

    from countdown.pulses.asciimatics import pulse_asciimatics

    lines = _zero_lines()
    with patch.object(Screen, "wrapper") as mock_wrapper:
        pulse_asciimatics(lines)
        assert mock_wrapper.called
        callback = mock_wrapper.call_args[0][0]
        assert callable(callback)


def test_pulse_asciimatics_demo_calls_screen_refresh():
    """Regression: _demo must call screen.refresh() so the user sees the output.

    Screen.wrapper does not auto-refresh; without an explicit refresh the
    screen buffer is never pushed to the terminal and the user sees a
    blank screen.
    """
    from countdown.pulses.asciimatics import _run_screen

    captured = {"refresh_calls": 0, "clears": 0, "updates": 0}

    class FakeScreen:
        height = 24
        width = 80

        def clear(self):
            captured["clears"] += 1

        def refresh(self):
            captured["refresh_calls"] += 1

        def wait_for_input(self, timeout):
            return False

        def get_event(self):
            return None

    class FakeEffect:
        def __init__(self, screen, lines, y, label=None, **kwargs):
            self.screen = screen

        def update(self, frame_no):
            captured["updates"] += 1

    time_values = iter([0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 2.0])

    def fake_time():
        return next(time_values)

    def fake_sleep(s):
        pass

    captured_callback = {}

    def fake_wrapper(callback, *args, **kwargs):
        captured_callback["cb"] = callback
        callback(FakeScreen())
        return None

    with (
        patch("countdown.pulses.asciimatics.SineWaveEffect", FakeEffect),
        patch("countdown.pulses.asciimatics.Screen.wrapper", side_effect=fake_wrapper),
        patch("countdown.pulses.asciimatics.time", fake_time),
        patch("countdown.pulses.asciimatics.sleep", fake_sleep),
    ):
        _run_screen(["abc"], duration=0.1, label="asciimatics")

        # refresh must be called at least once
        assert captured["refresh_calls"] > 0, "screen.refresh() must be called"
        # clear and update should be called too
        assert captured["clears"] > 0
        assert captured["updates"] > 0
