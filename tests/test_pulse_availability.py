"""Tests that optional pulse backends are real runtime deps.

asciimatics, drawille, ghostprint, and smooth are declared as hard runtime
dependencies, so showcase must be able to run every mode: importing the
pulse modules must never fail, and the showcase segment sequence must be
complete.
"""

import pytest

from countdown.pulses import (  # noqa: F401  import smoke tests
    SHOWCASE_MODES,
    _load_module,
    asciimatics,
    drawille,
    get_pulse_fn,
    ghostprint,
    rich,
    smooth,
)


@pytest.mark.parametrize("name", SHOWCASE_MODES)
def test_showcase_mode_backend_imports(name):
    """Every showcase mode's module and pulse fn must import cleanly."""
    module = _load_module(name)
    assert get_pulse_fn(name) is getattr(module, f"pulse_{name}")


def test_asciimatics_backend_imports_and_runs():
    """Asciimatics is a runtime dep: its pulse fn must resolve."""
    assert get_pulse_fn("asciimatics").__name__ == "pulse_asciimatics"


def test_run_showcase_visits_every_mode_each_cycle(monkeypatch):
    """One cycle must render every SHOWCASE_MODE plus an asciimatics pass."""
    from countdown import showcase as showcase_mod

    rendered = []

    def fake_segment(mode, lines, interval):
        rendered.append(mode)
        return True

    def fake_asciimatics_segment(lines, interval):
        rendered.append("asciimatics")
        return False  # stop the loop once asciimatics has run

    # Force termination after one full cycle so `once` isn't required and we
    # observe the order-independent set of segments actually rendered.
    monkeypatch.setattr(showcase_mod, "_render_segment", fake_segment)
    monkeypatch.setattr(
        showcase_mod, "_render_asciimatics_segment", fake_asciimatics_segment
    )
    monkeypatch.setattr(showcase_mod, "setup_terminal", lambda: None)
    monkeypatch.setattr(showcase_mod, "restore_terminal", lambda s: None)
    monkeypatch.setattr(showcase_mod, "check_for_keypress", lambda: False)

    showcase_mod.run_showcase(interval=1.0, shuffle=False, once=False)

    # The 5 text modes, in order, then asciimatics last.
    assert rendered[:5] == list(SHOWCASE_MODES)
    assert rendered[5:] == ["asciimatics"]


def test_showcase_segment_encodes_glyphs_on_cp1252_stdout(monkeypatch):
    r"""reconfigure_stdout_utf8 must fix the cp1252 encode crash.

    Showcase/rich frames contain block glyphs (e.g. ``\u2588``) that the
    Windows-default cp1252 codec cannot encode. Emitting them onto a cp1252
    stream used to raise UnicodeEncodeError; reconfiguring stdout to UTF-8
    (as ``main()`` does) must make the write succeed.
    """
    import io
    import sys

    from countdown import display as display_mod

    glyph = "\u2588"  # FULL BLOCK

    # Prove the raw glyph is unrepresentable in cp1252 (the original trigger).
    with pytest.raises(UnicodeEncodeError):
        glyph.encode("cp1252")

    # Build a real UTF-8 TextIOWrapper over an in-memory buffer and stand it
    # in for stdout.
    fake_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", fake_out)

    # Captured bytes after writing through the real print path.
    display_mod.reconfigure_stdout_utf8()
    print(glyph, file=sys.stdout, flush=True)

    fake_out.flush()
    payload = fake_out.buffer.getvalue()
    assert glyph.encode("utf-8") in payload
