"""Schedule CLI presentation helpers (extracted from ``__main__``).

These render the schedule stack (static + live views), add new schedules, and
check in on one. Error surfacing stays as ``click.UsageError`` so failures show
up in Click output; all strings and Rich styling are identical to what the CLI
previously produced inline.
"""

from __future__ import annotations

from time import sleep, time

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import timer
from .config import resolve_pulse
from .schedule import ScheduleStore, format_remaining, wall_clock
from .terminal import check_for_keypress


def load_store() -> ScheduleStore:
    """Load the schedule store, surfacing file errors as ``UsageError``."""
    try:
        return ScheduleStore.load()
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc


def _schedule_table(store, now):
    """Build the FILO schedule stack as a rich table at a given clock time."""
    table = Table(
        title=f"Schedules ({len(store)})",
        border_style="cyan",
    )
    table.add_column("#", justify="right", style="bold cyan", no_wrap=True)
    table.add_column("Remaining", no_wrap=True)
    table.add_column("Due", style="white", no_wrap=True)
    table.add_column("Alias", style="bold bright_cyan", no_wrap=True)

    for position, schedule in enumerate(store.ordered(), start=1):
        remaining = schedule.remaining(now)
        if remaining > 0:
            remaining_cell = Text(
                format_remaining(remaining), style="bold green"
            )
            due_cell = Text(wall_clock(schedule.due), style="white")
        else:
            remaining_cell = Text("Timeout!", style="bold yellow")
            due_cell = Text(f"ended {wall_clock(schedule.due)}", style="dim")
        if schedule.alias:
            alias_cell = Text(schedule.alias, style="bold bright_cyan")
        else:
            alias_cell = Text("null", style="dim italic")
        table.add_row(str(position), remaining_cell, due_cell, alias_cell)
    return table


def render_schedule_list(store):
    """Render the FILO schedule stack as a static rich table."""
    console = Console()
    if len(store) == 0:
        console.print(
            Panel(
                "No schedules yet - add one with e.g. [bold]timer schedule 1h[/bold] "
                "or [bold]timer schedule -23:45[/bold].",
                title="[bold cyan]Schedules[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
        )
        return
    console.print(_schedule_table(store, time()))


def render_schedule_live(store):
    """Render the schedule stack as a live table that ticks down in place.

    Remaining times refresh every second and rows flip to ``Timeout!`` as their
    deadlines pass. Press any key (or Ctrl+C) to exit; a summary line is always
    printed so the view never ends silently.
    """
    console = Console()
    if len(store) == 0:
        render_schedule_list(store)
        return

    started = time()
    try:
        with Live(
            _schedule_table(store, started),
            console=console,
            screen=False,
            auto_refresh=False,
        ) as live:
            while True:
                live.update(_schedule_table(store, time()))
                live.refresh()
                if check_for_keypress():
                    break
                sleep(1.0)
    except KeyboardInterrupt:
        pass
    finished = time()
    timed_out = sum(1 for s in store.ordered() if s.remaining(finished) <= 0)
    console.print(
        Text.assemble(
            ("Stopped schedule live view ", "bold green"),
            (f"(watched {format_remaining(int(finished - started))}, ", ""),
            (f"{timed_out} timed out).", ""),
        )
    )


def add_schedule(store, spec, alias):
    """Parse ``spec``, append a new schedule, persist, and report clearly."""
    try:
        dur = timer.duration(spec)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    now = time()
    try:
        schedule = store.add(
            due=now + dur.total_seconds, created=now, spec=spec, alias=alias
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    store.save()

    message = Text.assemble(
        ("Scheduled ", "bold green"),
        (schedule.alias or schedule.spec, "bold white"),
        (" :: due ", ""),
        (wall_clock(schedule.due), "bold cyan"),
        (" :: stack #1", ""),
        (f" :: saved to {store.resolve_path()}", "dim"),
    )
    Console().print(message)
    return schedule


def check_schedule(schedule, *, now_flag, position=None, run_timer=None):
    """Check in on a schedule: big-timer countdown, or a one-shot ``--now``.

    Expired schedules still launch the big timer (00:00 + pulse) unless
    ``--now`` was passed; no code path is ever silent.

    Args:
        schedule: The ``Schedule`` to check in on.
        now_flag: If True, print a static status panel instead of the timer.
        position: Stack position (for display labels).
        run_timer: Callable(total_seconds, **kwargs) launching the big timer.
            Defaults to ``countdown.loop.run_countdown``; the Click tree passes
            its own wrapper so tests can stub the entry point in one place.
    """
    if run_timer is None:
        from .loop import run_countdown as run_timer

    now = time()
    remaining = schedule.remaining(now)
    label = schedule.alias or schedule.spec
    tag = f"#{position} " if position else ""
    console = Console()

    try:
        pulse_fn = resolve_pulse()
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    if remaining <= 0:
        if now_flag:
            body = Text.assemble(
                ("Timeout! ", "bold yellow"),
                (f"{tag}{label} ended {wall_clock(schedule.due)} ", ""),
                (f"({format_remaining(remaining).lstrip('-')} ago).", "dim"),
            )
            console.print(
                Panel(
                    body,
                    title="[bold cyan]Schedule[/bold cyan]",
                    border_style="yellow",
                    expand=False,
                )
            )
            return
        console.print(
            Text.assemble(
                ("Timed out ", "bold yellow"),
                (f"{tag}{label} ", "bold white"),
                (f"({format_remaining(remaining).lstrip('-')} ago) ", "dim"),
                ("- running 00:00, press q to exit.", ""),
            )
        )
        run_timer(
            0,
            pulse_fn=pulse_fn,
            show_hours=False,
            dur_str="0s",
        )
        return

    if now_flag:
        body = Text.assemble(
            (f"{tag}", "bold cyan"),
            (f"{label} - ", "bold green"),
            (f"{format_remaining(remaining)} remaining", "bold white"),
            (f"\ndue {wall_clock(schedule.due)}", "dim"),
        )
        console.print(
            Panel(
                body,
                title="[bold cyan]Schedule[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
        )
        return

    console.print(
        Text.assemble(
            ("Checking in on ", ""),
            (f"{tag}", "bold cyan"),
            (f"{label} ", "bold white"),
            (f"- {format_remaining(remaining)} left, ", ""),
            (f"due {wall_clock(schedule.due)}", "dim"),
        )
    )
    run_timer(
        int(remaining),
        pulse_fn=pulse_fn,
        show_hours=remaining >= 3600,
        dur_str=format_remaining(remaining),
    )


__all__ = [
    "load_store",
    "render_schedule_list",
    "render_schedule_live",
    "add_schedule",
    "check_schedule",
]
