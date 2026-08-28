"""Non-background schedules: deadlines stored as epochs in timer.yaml.

Each schedule is just two numbers — when it was created and when it is due.
Checking in is pure arithmetic (``due - now``); nothing runs in the background
between check-ins.

Storage precedence: a ``timer.yaml`` in the current directory wins; otherwise
the store lives at ``~/.config/timer.yaml``.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import yaml

from . import timer as timer_mod

STORE_FILENAME = "timer.yaml"

RESERVED_ALIASES = frozenset({"list", "nuke", "at", "rm"})


@dataclass
class Schedule:
    """A single deadline: due epoch, creation epoch, and original spec."""

    due: float
    created: float
    spec: str
    alias: str | None = None

    def remaining(self, now: float) -> float:
        """Seconds until due; negative once expired."""
        return self.due - now


def format_remaining(seconds: float) -> str:
    """Format ``seconds`` (may be negative) as a compact duration string.

    Positive values show time remaining (e.g. ``1h25m``); negative values are
    prefixed with ``-`` to indicate elapsed time (e.g. ``-5m``).
    """
    total = int(abs(seconds))
    dur = timer_mod.compact(
        timer_mod.Duration(total_seconds=total, components={"s": total})
    )
    text = timer_mod.format_duration(dur)
    return f"-{text}" if seconds < 0 else text


def wall_clock(epoch: float) -> str:
    """Render an epoch as a compact local wall-clock label (e.g. ``Wed 17:45``)."""
    return datetime.fromtimestamp(epoch).strftime("%a %H:%M")


class ScheduleStore:
    """Reads/writes ``timer.yaml`` with CWD → ~/.config/timer.yaml precedence.

    Test knobs live at class level (mirrors ``Config.path``):
    - ``base_dir`` is the CWD searched for a local ``timer.yaml``.
    - ``home_config_dir`` overrides ``~/.config`` when the local file is absent.
    """

    base_dir: Path = Path.cwd()
    home_config_dir: Path | None = None

    def __init__(self, schedules=None):
        self._schedules = list(schedules) if schedules else []

    # -- paths ------------------------------------------------------------

    @classmethod
    def _fallback_dir(cls) -> Path:
        if cls.home_config_dir is not None:
            return cls.home_config_dir
        return Path.home() / ".config"

    @classmethod
    def resolve_path(cls) -> Path:
        """Return the authoritative store path (CWD wins when present)."""
        local = cls.base_dir / STORE_FILENAME
        if local.exists():
            return local
        return cls._fallback_dir() / STORE_FILENAME

    # -- persistence ------------------------------------------------------

    @classmethod
    def load(cls) -> "ScheduleStore":
        """Load schedules from the resolved path; missing file → empty store."""
        path = cls.resolve_path()
        if not path.exists():
            return cls()
        with path.open() as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            raise ValueError(
                f"Invalid {STORE_FILENAME}: expected mapping, got {type(raw).__name__}"
            )
        entries = raw.get("schedules", [])
        if not isinstance(entries, list):
            raise ValueError(
                f"Invalid {STORE_FILENAME}: 'schedules' must be a list"
            )
        schedules = []
        seen_aliases: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Invalid {STORE_FILENAME}: each schedule must be a mapping"
                )
            try:
                schedule = Schedule(
                    due=float(entry["due"]),
                    created=float(entry["created"]),
                    spec=str(entry["spec"]),
                    alias=entry.get("alias"),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid schedule in {STORE_FILENAME}: {entry!r}"
                ) from exc
            if schedule.alias is not None:
                if schedule.alias in seen_aliases:
                    raise ValueError(
                        f"Duplicate alias in {STORE_FILENAME}: "
                        f"{schedule.alias!r}"
                    )
                seen_aliases.add(schedule.alias)
            schedules.append(schedule)
        return cls(schedules)

    def save(self) -> None:
        """Persist to the resolved path, creating parent dirs as needed."""
        path = self.resolve_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schedules": [asdict(s) for s in self._schedules]}
        with path.open("w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

    # -- mutation ---------------------------------------------------------

    def add(
        self, due: float, created: float, spec: str, alias=None
    ) -> Schedule:
        """Append a validated schedule and return it."""
        if alias is not None:
            self._validate_alias(alias)
            if self.by_alias(alias) is not None:
                raise ValueError(f"Alias already in use: {alias!r}")
        schedule = Schedule(due=due, created=created, spec=spec, alias=alias)
        self._schedules.append(schedule)
        return schedule

    def clear(self) -> None:
        """Remove every schedule."""
        self._schedules.clear()

    def remove(self, schedule: Schedule) -> None:
        """Remove a single schedule by identity (no-op if already gone)."""
        try:
            self._schedules.remove(schedule)
        except ValueError:
            pass

    # -- queries ----------------------------------------------------------

    def ordered(self) -> list[Schedule]:
        """Schedules newest-first (FILO stack: most recently added is #1).

        Ordering follows insertion order (entries are appended on add; the CWD
        store is append-only), so FILO holds even when two schedules are
        created in the same wall-clock second.
        """
        return list(reversed(self._schedules))

    def by_number(self, number: int) -> Schedule | None:
        """Return the schedule at ``number`` (1-based list order) or None."""
        ordered = self.ordered()
        if 1 <= number <= len(ordered):
            return ordered[number - 1]
        return None

    def by_alias(self, alias: str) -> Schedule | None:
        """Return the schedule with ``alias`` (aliases are unique) or None."""
        for s in self._schedules:
            if s.alias == alias:
                return s
        return None

    def __len__(self) -> int:
        """Return the number of stored schedules."""
        return len(self._schedules)

    # -- validation -------------------------------------------------------

    def _validate_alias(self, alias: str) -> None:
        """Raise ValueError if ``alias`` would be ambiguous on the CLI."""
        plain = str(alias)
        if not plain.strip():
            raise ValueError("Alias must not be empty.")
        if plain.isdigit():
            raise ValueError(f"Alias must not be a number: {plain!r}.")
        if plain.startswith("-"):
            raise ValueError(f"Alias must not start with '-': {plain!r}.")
        if plain in RESERVED_ALIASES:
            raise ValueError(f"Alias must not be a reserved word: {plain!r}.")
        try:
            timer_mod.duration(plain)
        except ValueError:
            return
        raise ValueError(f"Alias must not look like a duration: {plain!r}.")


__all__ = ["Schedule", "ScheduleStore", "format_remaining", "wall_clock"]
