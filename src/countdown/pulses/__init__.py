"""Pulse animation dispatch — selects one of 6 pulse modes."""

from collections.abc import Callable

VALID_ANIM_MODES = (
    "ansi",
    "rich",
    "drawille",
    "smooth",
    "ghostprint",
    "asciimatics",
)


def get_pulse_fn(name: str) -> Callable[[list[str]], None]:
    """Return the pulse function for ``name``.

    Raises ``ValueError`` with a list of valid modes if ``name`` is unknown.
    Imports are lazy so unused libraries don't slow startup.
    """
    if name == "ansi":
        from .ansi import pulse_ansi

        return pulse_ansi
    if name == "rich":
        from .rich import pulse_rich

        return pulse_rich
    if name == "drawille":
        from .drawille import pulse_drawille

        return pulse_drawille
    if name == "smooth":
        from .smooth import pulse_smooth

        return pulse_smooth
    if name == "ghostprint":
        from .ghostprint import pulse_ghostprint

        return pulse_ghostprint
    if name == "asciimatics":
        from .asciimatics import pulse_asciimatics

        return pulse_asciimatics
    valid = ", ".join(VALID_ANIM_MODES)
    raise ValueError(
        f"Invalid anim mode: {name!r}. Valid modes: {valid}"
    )


def validate_anim_mode(name: str) -> None:
    """Raise ``ValueError`` if ``name`` is not a valid animation mode."""
    if name not in VALID_ANIM_MODES:
        valid = ", ".join(VALID_ANIM_MODES)
        raise ValueError(
            f"Invalid anim mode: {name!r}. Valid modes: {valid}"
        )


__all__ = [
    "VALID_ANIM_MODES",
    "get_pulse_fn",
    "validate_anim_mode",
]
