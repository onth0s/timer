"""Shared wave math utilities for pulse animations."""

from math import cos, sin, sqrt


def radial_wave(
    x: float, y: float, cx: float, cy: float, phase: float, frequency: float = 0.3
) -> float:
    """Compute sine wave intensity at point (x,y) given phase and center.

    Returns value in [-1, 1].
    """
    distance = sqrt((x - cx) ** 2 + (y - cy) ** 2)
    return sin(phase - distance * frequency)


def linear_wave(
    x: float, y: float, phase: float, freq_x: float = 0.4, freq_y: float = 0.3
) -> float:
    """Compute interference pattern of two orthogonal sine waves.

    Returns value in [-2, 2].
    """
    return sin(phase + x * freq_x) + cos(phase + y * freq_y)


def intensity_to_ansi(intensity: float) -> str:
    """Map [-1, 1] to an ANSI style: dim/normal/bold.

    0.0-0.33  -> dim
    0.33-0.66 -> normal
    0.66-1.0  -> bold
    """
    if intensity < -0.33:
        return "dim"
    if intensity < 0.33:
        return "normal"
    return "bold"


def hsl_to_rgb(
    h: float, s: float, lightness: float
) -> tuple[int, int, int]:
    """Convert HSL (h in 0-360, s/lightness in 0-1) to RGB tuple (0-255)."""
    c = (1 - abs(2 * lightness - 1)) * s
    hp = (h % 360) / 60
    x = c * (1 - abs(hp % 2 - 1))
    if hp < 1:
        r, g, b = c, x, 0
    elif hp < 2:
        r, g, b = x, c, 0
    elif hp < 3:
        r, g, b = 0, c, x
    elif hp < 4:
        r, g, b = 0, x, c
    elif hp < 5:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    m = lightness - c / 2
    return (
        int((r + m) * 255),
        int((g + m) * 255),
        int((b + m) * 255),
    )


__all__ = ["hsl_to_rgb", "intensity_to_ansi", "linear_wave", "radial_wave"]
