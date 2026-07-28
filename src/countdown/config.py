"""Configuration loader/writer for ./config.yaml with strict validation."""

from pathlib import Path

import yaml

from .pulses import VALID_ANIM_MODES


def validate_anim_mode(name: str) -> None:
    """Raise ``ValueError`` if ``name`` is not a valid animation mode."""
    if name not in VALID_ANIM_MODES:
        valid = ", ".join(VALID_ANIM_MODES)
        raise ValueError(
            f"Invalid anim mode: {name!r}. Valid modes: {valid}"
        )


class Config:
    """Reads/writes ./config.yaml with strict validation."""

    path: Path = Path("config.yaml")
    DEFAULT: dict[str, str] = {"anim": "rich"}

    def __init__(self, data: dict[str, str] | None = None):
        self._data = dict(data) if data else dict(self.DEFAULT)

    @classmethod
    def load(cls) -> "Config":
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


__all__ = ["Config", "validate_anim_mode"]
