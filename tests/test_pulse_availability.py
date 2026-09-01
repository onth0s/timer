"""Regression tests for graceful handling of missing optional animation libs.

asciimatics, drawille, ghostprint, and smooth are *optional* backends: they
only appear in the dev dependency group, so an end user's ``timer`` install
may lack them. Showcase must skip those modes instead of tracebacking at
import time, and ``get_pulse_fn`` must surface a friendly error.
"""

import pytest

from countdown.pulses import (
    SHOWCASE_MODES,
    _load_module,
    get_pulse_fn,
    is_mode_available,
)


@pytest.mark.parametrize(
    "name",
    ["asciimatics", "drawille", "ghostprint", "smooth"],
)
def test_is_mode_available_false_when_lib_missing(
    monkeypatch, name
):
    def fake_load(mod_name):
        if mod_name == name:
            raise ModuleNotFoundError(
                f"No module named {name!r}", name=name
            )
        return _load_module(mod_name)

    monkeypatch.setattr(
        "countdown.pulses._load_module", fake_load
    )
    assert is_mode_available(name) is False
    assert all(is_mode_available(m) for m in SHOWCASE_MODES if m != name)


def test_showcase_available_modes_skip_missing_libs(monkeypatch):
    def fake_load(mod_name):
        if mod_name in ("drawille", "asciimatics"):
            raise ModuleNotFoundError(
                f"No module named {mod_name!r}", name=mod_name
            )
        return _load_module(mod_name)

    monkeypatch.setattr(
        "countdown.pulses._load_module", fake_load
    )

    from countdown import showcase as showcase_mod

    assert showcase_mod._available_showcase_modes() == [
        "ansi",
        "ghostprint",
        "rich",
        "smooth",
    ]


def test_get_pulse_fn_friendly_error_when_lib_missing(monkeypatch):
    def fake_load(mod_name):
        if mod_name == "asciimatics":
            raise ModuleNotFoundError(
                "No module named 'asciimatics'", name="asciimatics"
            )
        return _load_module(mod_name)

    monkeypatch.setattr(
        "countdown.pulses._load_module", fake_load
    )

    with pytest.raises(ValueError, match="not installed"):
        get_pulse_fn("asciimatics")
