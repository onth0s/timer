"""Shared plumbing for the pulse animation modules.

Every text-based pulse module (ansi, rich, smooth, ghostprint, drawille)
exposes the same three-callable contract:

    * ``build_frame(lines, phase) -> str`` — render one frame as a string
    * ``pulse_<mode>(lines)`` — render one real-time frame to stdout
    * ``reset_state()`` — clear the module's internal phase marker (for tests)

``make_pulse`` centralizes the real-time wrapper those five modules otherwise
duplicate (phase tracking plus the CLEAR/HOME framing).
"""

from collections.abc import Callable
from time import time

from ..display import FULL_CLEAR_HOME, HOME


def make_pulse(
    build_frame: Callable[[list[str], float], str],
    phase_scale: float = 1.0,
    doc: str | None = None,
) -> tuple[Callable[[list[str]], None], Callable[[], None]]:
    """Build a ``pulse``/``reset_state`` pair around ``build_frame``.

    Args:
        build_frame: Callable ``(lines, phase) -> str`` producing one frame.
            The phase advances at ``phase_scale`` radian-seconds from the
            first call (tracked per returned pair).
        phase_scale: Multiplier applied to elapsed time when computing phase.
        doc: Optional docstring for the returned pulse callable.

    Returns:
        A ``(pulse, reset_state)`` tuple. ``pulse(lines)`` prints one frame to
        stdout; ``reset_state()`` clears the phase marker for the pair.
    """
    start: list[float | None] = [None]

    def pulse(lines: list[str]) -> None:
        if start[0] is None:
            start[0] = time()
        phase = (time() - start[0]) * phase_scale
        print(
            FULL_CLEAR_HOME + build_frame(lines, phase) + HOME, flush=True, end=""
        )

    def reset_state() -> None:
        start[0] = None

    if doc:
        pulse.__doc__ = doc
    return pulse, reset_state


__all__ = ["make_pulse"]
