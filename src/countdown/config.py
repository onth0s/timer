"""Configuration loader/writer for ./config.yaml with strict validation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .pulses import get_pulse_fn, validate_anim_mode


class Config:
    """Reads/writes ./config.yaml with strict validation."""

    path: Path = Path("config.yaml")
    DEFAULT: dict[str, str] = {"anim": "rich"}

    def __init__(self, data: dict[str, str] | None = None):
        self._data = dict(data) if data else dict(self.DEFAULT)

    @classmethod
    def load(cls) -> Config:
        """Load from disk. Missing file returns defaults."""
        if not cls.path.exists():
            return cls()
        with cls.path.open() as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            raise ValueError(
                f"Invalid config: expected mapping, got {type(raw).__name__}"
            )
        data: dict[str, str] = dict(cls.DEFAULT)
        for key, value in raw.items():
            if key == "anim":
                validate_anim_mode(str(value))
            data[key] = str(value)
        return cls(data)

    def save(self) -> None:
        """Persist to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as f:
            yaml.safe_dump(self._data, f)

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a config value."""
        return self._data.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Validate and set a config value."""
        if key == "anim":
            validate_anim_mode(value)
        self._data[key] = value

    def as_dict(self) -> dict[str, str]:
        """Return a copy of the underlying data."""
        return dict(self._data)


def resolve_pulse(anim_override: str | None = None) -> Callable[[list[str]], None]:
    """Load config, resolve the anim mode, and return the pulse function.

    If *anim_override* is given it takes precedence over the persisted config.
    Raises ``click.UsageError``-compatible ``ValueError`` on invalid modes.
    """
    cfg = Config.load()
    mode = anim_override if anim_override is not None else cfg.get("anim") or "rich"
    return get_pulse_fn(mode)


__all__ = ["Config", "resolve_pulse", "validate_anim_mode"]
