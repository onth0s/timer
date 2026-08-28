"""Command-line interface."""

import difflib

import click
import rich_click  # noqa: F401 — patches Click for Rich-styled --help

from . import timer
from .config import Config
from .pulses import VALID_ANIM_MODES, get_pulse_fn
from .schedule import wall_clock
from .schedules_cli import (
    add_schedule,
    check_schedule,
    load_store,
    render_schedule_list,
    render_schedule_live,
)

# rich-click configuration
rich_click.USE_RICH_MARKUP = True
rich_click.STYLE_HELPTEXT = ""


def run_countdown(
    total_seconds,
    pulse_fn=None,
    max_pulses=None,
    *,
    show_hours=False,
    count_up=False,
    raw_seconds=False,
    dur_str=None,
):
    """Run the countdown or count-up timer.

    Thin adapter over :func:`countdown.loop.run_countdown`, which owns the
    actual loop, timing (:data:`countdown.loop.STDCLOCK`), and pulse
    orchestration. Kept here as the public entry point so the Click tree and
    tests keep a stable call surface.

    Args:
        total_seconds: Duration in seconds to count down from (or None for count-up)
        pulse_fn: Callable(lines) called after countdown reaches 0
        max_pulses: Maximum pulse iterations before exiting.
        show_hours: If True, display as HH:MM:SS.
        count_up: If True, count up starting from 0 (stopwatch mode).
        raw_seconds: If True, display as bare seconds (e.g. 300) without colons.
        dur_str: Explicit formatted duration string for summary display.
    """
    from .loop import run_countdown as _loop_run_countdown

    return _loop_run_countdown(
        total_seconds,
        pulse_fn=pulse_fn,
        max_pulses=max_pulses,
        show_hours=show_hours,
        count_up=count_up,
        raw_seconds=raw_seconds,
        dur_str=dur_str,
    )


# Store original on the function for tests to bypass the default wrapper.
run_countdown._original = run_countdown  # type: ignore[attr-defined]


# ====================================================================
# Click subcommands
# ====================================================================


def _fix_dash_args(cmd: click.Command, args: list[str]) -> list[str]:
    """Insert '--' before positional arguments starting with '-' that aren't recognized options."""
    if not args or "--" in args:
        return args

    opt_names = set()
    for param in cmd.params:
        if isinstance(param, click.Option):
            opt_names.update(param.opts)
            opt_names.update(param.secondary_opts)
    opt_names.update({"-h", "--help"})

    new_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("-") and arg not in opt_names:
            new_args.append("--")
            new_args.extend(args[i:])
            return new_args

        new_args.append(arg)
        for param in cmd.params:
            if isinstance(param, click.Option) and (
                arg in param.opts or arg in param.secondary_opts
            ):
                if not param.is_flag and i + 1 < len(args):
                    i += 1
                    new_args.append(args[i])
                break
        i += 1

    return new_args


def _is_duration_token(token: str) -> bool:
    """Return True if ``token`` parses as a timer duration."""
    try:
        timer.duration(token)
    except ValueError:
        return False
    return True


def _command_suggestions(token: str, commands: dict) -> list[str]:
    """Return close command-name matches for ``token``, capped at 3."""
    return difflib.get_close_matches(token, commands, n=3, cutoff=0.5)


def _resolve_typo_command(token: str, commands: dict) -> str | None:
    """Return the command ``token`` most likely means, or None.

    Only non-duration tokens that fuzzy-match a command name are resolved, so
    `timer 5` / `timer -4:40PM` still count as durations (routed to ``run``)
    while `timer sch` -- which is *not* a duration -- dispatches to
    ``schedule``.
    """
    if _is_duration_token(token):
        return None
    suggestions = _command_suggestions(token, commands)
    if not suggestions:
        return None
    return suggestions[0]


class RunCommand(click.Command):
    """Command subclass for `run` that pre-processes dash-prefixed duration arguments."""

    def parse_args(self, ctx, args):
        """Pre-process dash-prefixed positional arguments before Click option parsing."""
        fixed_args = _fix_dash_args(self, args)
        return super().parse_args(ctx, fixed_args)


class SmartGroup(click.Group):
    """Group that forwards unmatched positional args to a matching subcommand.

    Lets ``timer 5`` / ``timer -4:40PM`` work as aliases for ``timer run ...``,
    and routes ambiguous spellings like ``timer sch`` straight to ``schedule``.
    """

    def _route(self, args):
        """Return subcommand-prefixed args for an unknown leading token, or None."""
        first = args[0]
        target = _resolve_typo_command(first, self.commands)
        if target:
            return [target] + list(args[1:])
        if "run" in self.commands:
            fixed_args = _fix_dash_args(self.commands["run"], args)
            return ["run"] + fixed_args
        return None

    def parse_args(self, ctx, args):
        """Forward non-subcommand arguments to a matching subcommand."""
        if args:
            first = args[0]
            group_opts = {"-h", "--help", "--version"}
            if first not in self.commands and first not in group_opts:
                routed = self._route(args)
                if routed is not None:
                    return super().parse_args(ctx, routed)
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx, args):
        """Route non-subcommand positional args to a matching subcommand."""
        if args and args[0] not in self.commands:
            routed = self._route(args)
            if routed is not None:
                return routed[0], self.commands[routed[0]], routed[1:]
        return super().resolve_command(ctx, args)


@click.group(invoke_without_command=True, cls=SmartGroup)
@click.version_option(package_name="timer")
@click.pass_context
def main(ctx):
    """Countdown timer for the terminal with configurable pulse animations."""
    if ctx.invoked_subcommand is None:
        # Default bare 'timer' execution to count-up mode
        config = Config.load()
        try:
            mode = config.get("anim") or "rich"
            pulse_fn = get_pulse_fn(mode)
        except ValueError as exc:
            raise click.UsageError(str(exc)) from exc
        run_countdown(0, pulse_fn=pulse_fn, count_up=True)


@main.command(name="run", cls=RunCommand)
@click.option(
    "--anim",
    type=click.Choice(list(VALID_ANIM_MODES)),
    help="Override animation mode for this run.",
)
@click.option(
    "--raw",
    "-r",
    is_flag=True,
    help="Force raw seconds display.",
)
@click.argument("duration", required=False)
def countdown(anim, raw, duration):
    r"""Run the countdown timer for the given DURATION.

    DURATION supports hours (h), minutes (m), and seconds (s).
    A bare number is interpreted as seconds.
    If no duration is provided, starts counting up from 0s.
    """
    from . import timer as timer_mod

    config = Config.load()
    try:
        mode = anim if anim is not None else config.get("anim") or "rich"
        pulse_fn = get_pulse_fn(mode)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    if duration is None:
        run_countdown(0, pulse_fn=pulse_fn, count_up=True, raw_seconds=raw)
        return

    try:
        dur = timer_mod.duration(duration)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    raw_seconds = raw
    dur_str = None

    if not raw and timer_mod.needs_prompt(dur):
        compact_dur = timer_mod.compact(dur)
        old = timer_mod.format_duration(dur)
        new = timer_mod.format_duration(compact_dur)
        click.echo(f"  {old} = {new}")
        click.echo(f"  [1] {new}")
        click.echo(f"  [2] {old}")
        choice = click.prompt(
            "  Choice",
            type=click.Choice(["1", "2"]),
            show_choices=False,
            prompt_suffix=" ",
        )
        if choice == "1":
            dur = compact_dur
            dur_str = new
        else:
            raw_seconds = True
            dur_str = old
    else:
        dur_str = (
            f"{dur.total_seconds}s" if raw else timer_mod.format_duration(dur)
        )

    show_hours = dur.total_seconds >= 3600
    run_countdown(
        dur.total_seconds,
        pulse_fn=pulse_fn,
        show_hours=show_hours,
        raw_seconds=raw_seconds,
        dur_str=dur_str,
    )


@main.group()
def config():
    """View and edit timer configuration."""


@config.command()
def init():
    """Create default config.yaml if missing."""
    cfg = Config()
    cfg.save()
    click.echo(f"\u2713 Wrote {Config.path}", color=True)


@config.command()
def show():
    """Show current resolved configuration."""
    from rich.console import Console
    from rich.table import Table

    cfg = Config.load()
    table = Table(title=f"Config ({Config.path})")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    for k, v in cfg.as_dict().items():
        table.add_row(k, v)
    Console().print(table)


@config.command()
def path():
    """Print path to config.yaml."""
    click.echo(str(Config.path))


@config.command()
@click.argument("mode", required=False)
def anim(mode):
    """Set or show the pulse animation mode.

    With no argument, prints the current mode.
    With a MODE argument, sets and persists the mode.
    """
    cfg = Config.load()
    if mode is None:
        click.echo(cfg.get("anim"))
        return
    try:
        cfg.set("anim", mode)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    cfg.save()
    click.echo(f"\u2713 anim set to {mode}", color=True)


# ====================================================================
# Schedule subcommands
# ====================================================================


class ScheduleGroup(click.Group):
    """Group that routes non-subcommand tokens to the catch-all ``at`` command.

    Protects dash-prefixed target times (e.g. ``-23:45``) from Click's option
    parser, mirroring how ``SmartGroup`` forwards to ``run``.
    """

    def parse_args(self, ctx, args):
        """Rewrite unrecognized first tokens into the catch-all command."""
        if args:
            first = args[0]
            group_opts = {"-h", "--help"}
            if first not in self.commands and first not in group_opts:
                at_cmd = self.commands.get("at")
                if at_cmd:
                    fixed_args = _fix_dash_args(at_cmd, args)
                    return super().parse_args(ctx, ["at"] + fixed_args)
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx, args):
        """Route non-subcommand tokens to the catch-all command."""
        if args and args[0] not in self.commands:
            return "at", self.commands["at"], args
        return super().resolve_command(ctx, args)


class ScheduleAtCommand(click.Command):
    """Catch-all command whose dash-prefixed positionals survive Click."""

    def parse_args(self, ctx, args):
        """Re-protect dash-prefixed positionals (idempotent)."""
        fixed_args = _fix_dash_args(self, args)
        return super().parse_args(ctx, fixed_args)


@main.group(cls=ScheduleGroup, invoke_without_command=True)
@click.pass_context
def schedule(ctx):
    """Schedule deadlines that never run in the background. Check in anytime.

    A schedule stores only an epoch; nothing ticks between check-ins. Use
    `timer schedule` for the live ticking stack (any key to exit; --now for a
    static snapshot), or check in on one by its list number or alias for the
    full-screen countdown to the deadline.
    """
    if ctx.invoked_subcommand is None:
        render_schedule_live(load_store())


@schedule.command(name="list")
@click.option(
    "--now",
    is_flag=True,
    help="Print the listing once as a static snapshot instead of the live view.",
)
def schedule_list(now):
    """List all schedules, newest first, with selection numbers.

    Defaults to the live view: remaining times tick down every second in
    place. Pass --now for a one-shot static snapshot.
    """
    if now:
        render_schedule_list(load_store())
    else:
        render_schedule_live(load_store())


@schedule.command()
def nuke():
    """Remove all schedules after a yes/no confirmation."""
    store = load_store()
    count = len(store)
    if count == 0:
        from rich.console import Console

        Console().print("[bold yellow]No schedules to remove.[/bold yellow]")
        return
    if click.confirm(f"Remove all {count} schedules?", abort=True):
        store.clear()
        store.save()
        from rich.console import Console

        Console().print(
            f"[bold green]Removed all {count} schedules[/bold green] "
            f"[dim]from {store.resolve_path()}[/dim]"
        )


@schedule.command()
@click.argument("target", metavar="ALIAS|NUMBER")
def rm(target):
    """Remove one schedule by its list NUMBER or ALIAS."""
    store = load_store()
    if len(store) == 0:
        raise click.UsageError("No schedules to remove.")
    if target.isdigit():
        position = int(target)
        schedule = store.by_number(position)
        if schedule is None:
            raise click.UsageError(
                f"No schedule #{target} - valid range is 1..{len(store)}."
            )
    else:
        schedule = store.by_alias(target)
        if schedule is None:
            raise click.UsageError(f"No schedule named {target!r}.")
        position = store.ordered().index(schedule) + 1
    label = schedule.alias or schedule.spec
    store.remove(schedule)
    store.save()
    from rich.console import Console
    from rich.text import Text

    Console().print(
        Text.assemble(
            ("Removed ", "bold green"),
            (f"#{position} ", "bold cyan"),
            (f"{label} ", "bold white"),
            (f"- due {wall_clock(schedule.due)} ", ""),
            (f"from {store.resolve_path()}", "dim"),
        )
    )


@schedule.command(name="at", cls=ScheduleAtCommand, hidden=True)
@click.option(
    "--now",
    is_flag=True,
    help="Print the current status once instead of an animated countdown.",
)
@click.option(
    "--expand",
    "-e",
    "expand",
    is_flag=True,
    help="Run the full-screen big timer (normally the default for check-in; "
    "with a DURATION it adds first, then immediately launches).",
)
@click.argument("args", nargs=-1, required=False)
def schedule_at(now, expand, args):
    r"""Add, list, or check in on a schedule.

    \b
    - `timer schedule 1h [alias]`            add a relative deadline
    - `timer schedule -23:45 [alias]`        add a clock-time deadline
    - `timer schedule 1h x --expand, -e`     add, then launch the big timer
    - `timer schedule <NUMBER|ALIAS>`        check in (big timer; --now static)
    - `timer schedule`                       live ticking stack (--now static)
    """
    if now and expand:
        raise click.UsageError("--now and --expand are mutually exclusive.")
    store = load_store()
    args = list(args)

    if not args:
        if expand:
            raise click.UsageError(
                "Nothing to expand. Pass a NUMBER, ALIAS, or DURATION."
            )
        render_schedule_list(store)
        return

    if len(args) == 1:
        token = args[0]
        if token.isdigit():
            position = int(token)
            schedule = store.by_number(position)
            if schedule is None:
                raise click.UsageError(
                    f"No schedule #{token} - valid range is 1..{len(store)}."
                )
            check_schedule(schedule, now_flag=now, position=position)
            return
        schedule = store.by_alias(token)
        if schedule is not None:
            position = store.ordered().index(schedule) + 1
            check_schedule(schedule, now_flag=now, position=position)
            return
        try:
            timer.duration(token)
        except ValueError:
            raise click.UsageError(
                f"Unknown schedule or duration: {token!r}. Use a stack "
                "NUMBER, an ALIAS, a DURATION (e.g. 25m, 2h), or -HH:MM."
            ) from None
        add_schedule(store, token, None)
        if expand:
            check_schedule(store.ordered()[0], now_flag=False, position=1)
        return

    if len(args) > 2:
        raise click.UsageError(
            "Expected DURATION [ALIAS] - too many arguments."
        )
    add_schedule(store, args[0], args[1])
    if expand:
        check_schedule(store.ordered()[0], now_flag=False, position=1)


@main.command()
@click.option(
    "--time",
    "-t",
    "time_per_mode",
    type=click.FloatRange(min=0.1, max=300),
    default=None,
    help="Seconds per mode (overrides positional DURATION).",
)
@click.option(
    "--random",
    "shuffle",
    is_flag=True,
    help="Shuffle mode order each cycle.",
)
@click.option(
    "--once",
    "-o",
    is_flag=True,
    help="Cycle through modes once then exit (default: infinite loop).",
)
@click.argument(
    "duration",
    type=click.FloatRange(min=0.1, max=300),
    required=False,
    metavar="[DURATION]",
)
def showcase(time_per_mode, shuffle, once, duration):
    r"""Cycle through every pulse animation mode.

    Displays each animation in turn for INTERVAL seconds (default 3),
    switching automatically. Useful for comparing animations or just
    watching them cycle. Press q or Ctrl+C to exit.

    \b
    Examples:
      timer showcase           # cycle all 6 modes, 3s each, infinite loop
      timer showcase 1         # 1 second per mode
      timer showcase -t 5      # 5 seconds per mode
      timer showcase --random  # shuffle the order each cycle
      timer showcase --once    # cycle once then exit
    """
    interval = (
        time_per_mode
        if time_per_mode is not None
        else (duration if duration is not None else 3.0)
    )
    from .showcase import run_showcase

    run_showcase(interval, shuffle, once)


@main.command()
def test():
    """Print a centering geometry map for the current terminal."""
    from .tests_cmd import run_tests_cmd

    run_tests_cmd()


if __name__ == "__main__":
    main(prog_name="countdown")  # pragma: no cover
