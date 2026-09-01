"""Pulse animation registry — selects one of 6 pulse modes.

Each mode maps to a module that optionally exposes a ``build_frame`` /
``reset_state`` pair for showcase segments, plus a ``pulse`` function for the
live loop. Imports are lazy so unused libraries don't slow startup.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module

VALID_ANIM_MODES = (
    "ansi",
    "rich",
    "drawille",
    "smooth",
    "ghostprint",
    "asciimatics",
)

# Modes with a dedicated showcase segment (asciimatics owns the screen and is
# handled separately). Alphabetical; matches showcase's historical order.
SHOWCASE_MODES = ("ansi", "drawille", "ghostprint", "rich", "smooth")

# mode -> attribute names. "builder"/"reset" are None for screen-owned modes.
_PULSE_SPECS: dict[str, dict[str, str | None]] = {
    "ansi": {"pulse": "pulse_ansi", "builder": "build_frame", "reset": "reset_state"},
    "rich": {"pulse": "pulse_rich", "builder": "build_frame", "reset": "reset_state"},
    "drawille": {
        "pulse": "pulse_drawille",
        "builder": "build_frame",
        "reset": "reset_state",
    },
    "smooth": {
        "pulse": "pulse_smooth",
        "builder": "build_frame",
        "reset": "reset_state",
    },
    "ghostprint": {
        "pulse": "pulse_ghostprint",
        "builder": "build_frame",
        "reset": "reset_state",
    },
    "asciimatics": {"pulse": "pulse_asciimatics", "builder": None, "reset": None},
}


def _load_module(name: str):
    """Import and return the pulse module for ``name``."""
    return import_module(f".{name}", __name__)


def get_pulse_fn(name: str) -> Callable[[list[str]], None]:
    """Return the pulse function for ``name``.

    Raises ``ValueError`` with a list of valid modes if ``name`` is unknown.
    Imports are lazy so unused libraries don't slow startup.
    """
    spec = _PULSE_SPECS.get(name)
    if spec is None:
        valid = ", ".join(VALID_ANIM_MODES)
        raise ValueError(f"Invalid anim mode: {name!r}. Valid modes: {valid}")
    return getattr(_load_module(name), spec["pulse"])


def get_showcase_builder(name: str) -> Callable[[list[str], float], str]:
    """Return the ``build_frame`` callable for a showcase mode."""
    spec = _PULSE_SPECS.get(name)
    if spec is None or spec["builder"] is None:
        valid = ", ".join(SHOWCASE_MODES)
        raise ValueError(f"Invalid showcase mode: {name!r}. Valid modes: {valid}")
    return getattr(_load_module(name), spec["builder"])


def get_showcase_resetter(name: str) -> Callable[[], None]:
    """Return the ``reset_state`` callable for a showcase mode."""
    spec = _PULSE_SPECS.get(name)
    if spec is None or spec["reset"] is None:
        valid = ", ".join(SHOWCASE_MODES)
        raise ValueError(f"Invalid showcase mode: {name!r}. Valid modes: {valid}")
    return getattr(_load_module(name), spec["reset"])


def validate_anim_mode(name: str) -> None:
    """Raise ``ValueError`` if ``name`` is not a valid animation mode."""
    if name not in VALID_ANIM_MODES:
        valid = ", ".join(VALID_ANIM_MODES)
        raise ValueError(f"Invalid anim mode: {name!r}. Valid modes: {valid}")


__all__ = [
    "SHOWCASE_MODES",
    "VALID_ANIM_MODES",
    "get_pulse_fn",
    "get_showcase_builder",
    "get_showcase_resetter",
    "validate_anim_mode",
]
