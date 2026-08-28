"""Pulse animation dispatch — selects one of 6 pulse modes."""

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


def _lazy_pulse(module_name: str, attr: str) -> Callable[[], Callable]:
    """Return a loader that imports ``attr`` from ``.<module_name>`` on demand."""

    def _load() -> Callable:
        module = import_module(f".{module_name}", __name__)
        return getattr(module, attr)

    return _load


_PULSE_LOADERS: dict[str, Callable[[], Callable]] = {
    "ansi": _lazy_pulse("ansi", "pulse_ansi"),
    "rich": _lazy_pulse("rich", "pulse_rich"),
    "drawille": _lazy_pulse("drawille", "pulse_drawille"),
    "smooth": _lazy_pulse("smooth", "pulse_smooth"),
    "ghostprint": _lazy_pulse("ghostprint", "pulse_ghostprint"),
    "asciimatics": _lazy_pulse("asciimatics", "pulse_asciimatics"),
}


def get_pulse_fn(name: str) -> Callable[[list[str]], None]:
    """Return the pulse function for ``name``.

    Raises ``ValueError`` with a list of valid modes if ``name`` is unknown.
    Imports are lazy so unused libraries don't slow startup.
    """
    loader = _PULSE_LOADERS.get(name)
    if loader is None:
        valid = ", ".join(VALID_ANIM_MODES)
        raise ValueError(f"Invalid anim mode: {name!r}. Valid modes: {valid}")
    return loader()


def validate_anim_mode(name: str) -> None:
    """Raise ``ValueError`` if ``name`` is not a valid animation mode."""
    if name not in VALID_ANIM_MODES:
        valid = ", ".join(VALID_ANIM_MODES)
        raise ValueError(f"Invalid anim mode: {name!r}. Valid modes: {valid}")


__all__ = [
    "VALID_ANIM_MODES",
    "get_pulse_fn",
    "validate_anim_mode",
]
