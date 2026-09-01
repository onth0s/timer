"""Keyboard input interpretation."""


def is_pause_key(key: str) -> bool:
    """Check if the given key is a pause/resume key (Space, p, k, Enter)."""
    return key in (" ", "p", "k", "\r", "\n")


def is_time_adjust_key(key: str) -> bool:
    """Check if the given key is a time adjustment key (+, =, -)."""
    return key in ("+", "=", "-")


def get_time_adjustment(key: str) -> int:
    """Return the time adjustment in seconds for the given key."""
    if key in ("+", "="):
        return 30  # Add 30 seconds
    elif key == "-":
        return -30  # Subtract 30 seconds
    return 0


__all__ = ["is_pause_key", "is_time_adjust_key", "get_time_adjustment"]
