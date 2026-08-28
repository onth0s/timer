"""Command-line interface."""

from time import sleep, time

import click
import rich_click  # noqa: F401 — patches Click for Rich-styled --help

from . import timer
from .config import Config
from .display import (
    DISABLE_ALT_BUFFER,
    ENABLE_ALT_BUFFER,
    HIDE_CURSOR,
    SHOW_CURSOR,
    enable_ansi_escape_codes,
    get_chars_for_terminal,
    print_full_screen,
)
from .keys import get_time_adjustment, is_pause_key, is_time_adjust_key
from .pulses import VALID_ANIM_MODES, get_pulse_fn
from .schedule import ScheduleStore, format_remaining, wall_clock
from .terminal import (
    check_for_keypress,
    drain_keypresses,
    read_key,
    restore_terminal,
    setup_terminal,
)

# rich-click configuration
rich_click.USE_RICH_MARKUP = True
rich_click.STYLE_HELPTEXT = ""


def get_number_lines(
    seconds, *, show_hours=False, count_up=False, raw_seconds=False
):
    """Return list of lines which make large glyphs for the time display."""
    return timer.get_number_lines(
        seconds,
        get_chars_for_terminal(seconds, show_hours=show_hours),
        show_hours=show_hours,
        count_up=count_up,
        raw_seconds=raw_seconds,
    )


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

    Args:
        total_seconds: Duration in seconds to count down from (or None for count-up)
        pulse_fn: Callable(lines) called after countdown reaches 0
        max_pulses: Maximum pulse iterations before exiting.
        show_hours: If True, display as HH:MM:SS.
        count_up: If True, count up starting from 0 (stopwatch mode).
        raw_seconds: If True, display as bare seconds (e.g. 300) without colons.
        dur_str: Explicit formatted duration string for summary display.
    """
    from rich.console import Console
    from rich.panel import Panel

    from .pulses.ansi import pulse_ansi

    if pulse_fn is None:
        pulse_fn = pulse_ansi

    console = Console()
    enable_ansi_escape_codes()
    old_settings = setup_terminal()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")

    zero_epoch = None
    exit_delay = None
    final_seconds = 0

    try:
        paused = False
        if count_up:
            n = 0
            pause_accum = 0.0
            pause_start = None
            while True:
                lines = get_number_lines(
                    n, show_hours=show_hours, count_up=True, raw_seconds=raw_seconds
                )
                print_full_screen(lines, paused=paused)

                if check_for_keypress():
                    key = read_key()
                    if key == "q" or key == "\x1b":  # q or Esc
                        final_seconds = n
                        break
                    elif is_pause_key(key):
                        if paused:
                            pause_accum += time() - pause_start
                            pause_start = None
                        else:
                            pause_start = time()
                        paused = not paused
                        drain_keypresses()

                if not paused:
                    sleep(1.0)
                    n += 1
                    final_seconds = n
                else:
                    sleep(0.05)
        else:
            n = total_seconds
            sleep_until = time() + total_seconds
            pause_start = None
            while n >= 0 or paused:
                lines = get_number_lines(
                    n, show_hours=show_hours, raw_seconds=raw_seconds
                )
                print_full_screen(lines, paused=paused)

                if check_for_keypress():
                    key = read_key()
                    if key == "q" or key == "\x1b":  # q or Esc
                        break
                    elif is_pause_key(key):
                        if paused:
                            sleep_until += time() - pause_start
                            pause_start = None
                        else:
                            pause_start = time()
                        paused = not paused
                        drain_keypresses()
                        lines = get_number_lines(
                            n, show_hours=show_hours, raw_seconds=raw_seconds
                        )
                        print_full_screen(lines, paused=paused)
                    elif is_time_adjust_key(key):
                        adjustment = get_time_adjustment(key)
                        new_n = max(0, n + adjustment)
                        sleep_until += new_n - n
                        n = new_n
                        drain_keypresses()
                        lines = get_number_lines(
                            n, show_hours=show_hours, raw_seconds=raw_seconds
                        )
                        print_full_screen(lines, paused=paused)

                if not paused:
                    display_this_second_until = sleep_until - n + 1
                    remaining = display_this_second_until - time()
                    if remaining > 0:
                        sleep(remaining)
                    n -= 1
                else:
                    if not check_for_keypress():
                        sleep(1.0)
                    else:
                        sleep(0.05)

            # Record epoch timestamp when reaching zero
            zero_epoch = time()

            if getattr(pulse_fn, "__name__", "") == "pulse_asciimatics":
                print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="", flush=True)
                pulse_fn(
                    get_number_lines(
                        0, show_hours=show_hours, raw_seconds=raw_seconds
                    )
                )
                exit_delay = time() - zero_epoch
                return

            pulse_count = 0
            while (
                max_pulses is None or pulse_count < max_pulses
            ) and not check_for_keypress():
                pulse_fn(
                    get_number_lines(
                        0, show_hours=show_hours, raw_seconds=raw_seconds
                    )
                )
                sleep(0.05)
                pulse_count += 1

            exit_delay = time() - zero_epoch

    except KeyboardInterrupt:
        if zero_epoch is not None and exit_delay is None:
            exit_delay = time() - zero_epoch
    finally:
        restore_terminal(old_settings)
        print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="")

        # Persistent summary log using rich
        if count_up:
            final_dur = dur_str or timer.format_duration(
                timer.compact(timer.duration(f"{final_seconds}s"))
            )
            console.print(
                Panel(
                    f"[bold green]Timer ran for {final_dur}[/bold green]",
                    title="[bold cyan]Timer Summary[/bold cyan]",
                    expand=False,
                )
            )
        else:
            if dur_str:
                total_ran = dur_str
            elif raw_seconds:
                total_ran = f"{total_seconds}s"
            else:
                total_ran = timer.format_duration(
                    timer.compact(timer.duration(f"{total_seconds}s"))
                )
            if exit_delay is not None:
                if exit_delay < 1:
                    delay_str = f"{exit_delay:.2f}s"
                else:
                    delay_str = timer.format_duration(
                        timer.compact(timer.duration(f"{int(exit_delay)}s"))
                    )
                console.print(
                    Panel(
                        f"[bold green]Timer completed ({total_ran})[/bold green]\n"
                        f"[bold yellow]Time to exit after timeout: {delay_str}[/bold yellow]",
                        title="[bold cyan]Timer Summary[/bold cyan]",
                        expand=False,
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[bold yellow]Timer stopped early ({total_ran} configured)[/bold yellow]",
                        title="[bold cyan]Timer Summary[/bold cyan]",
                        expand=False,
                    )
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


class RunCommand(click.Command):
    """Command subclass for `run` that pre-processes dash-prefixed duration arguments."""

    def parse_args(self, ctx, args):
        """Pre-process dash-prefixed positional arguments before Click option parsing."""
        fixed_args = _fix_dash_args(self, args)
        return super().parse_args(ctx, fixed_args)


class SmartGroup(click.Group):
    """Group that forwards unmatched positional args to the ``run`` subcommand.

    Lets ``timer 5`` or ``timer -4:40PM`` work as an alias for ``timer run ...``.
    """

    def parse_args(self, ctx, args):
        """Forward non-subcommand arguments to `run` subcommand with dash fix applied."""
        if args:
            first = args[0]
            group_opts = {"-h", "--help", "--version"}
            if first not in self.commands and first not in group_opts:
                run_cmd = self.commands.get("run")
                if run_cmd:
                    fixed_args = _fix_dash_args(run_cmd, args)
                    return super().parse_args(ctx, ["run"] + fixed_args)
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx, args):
        """Route non-subcommand positional args to the run subcommand."""
        if args and args[0] not in self.commands:
            return "run", self.commands["run"], args
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
        dur_str = f"{dur.total_seconds}s" if raw else timer_mod.format_duration(dur)

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


def load_store() -> ScheduleStore:
    """Load the schedule store, surfacing file errors as ``UsageError``."""
    try:
        return ScheduleStore.load()
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc


def _schedule_table(store, now):
    """Build the FILO schedule stack as a rich table at a given clock time."""
    from rich.table import Table
    from rich.text import Text

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
    from rich.console import Console
    from rich.panel import Panel

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
    from rich.console import Console
    from rich.live import Live
    from rich.text import Text

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
    timed_out = sum(
        1 for s in store.ordered() if s.remaining(finished) <= 0
    )
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

    from rich.console import Console
    from rich.text import Text

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


def check_schedule(schedule, *, now_flag, position=None):
    """Check in on a schedule: big-timer countdown, or a one-shot ``--now``.

    Expired schedules still launch the big timer (00:00 + pulse) unless
    ``--now`` was passed; no code path is ever silent.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    now = time()
    remaining = schedule.remaining(now)
    label = schedule.alias or schedule.spec
    tag = f"#{position} " if position else ""
    console = Console()

    config = Config.load()
    try:
        mode = config.get("anim") or "rich"
        pulse_fn = get_pulse_fn(mode)
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
        run_countdown(
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
    run_countdown(
        int(remaining),
        pulse_fn=pulse_fn,
        show_hours=remaining >= 3600,
        dur_str=format_remaining(remaining),
    )


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
        raise click.UsageError("Expected DURATION [ALIAS] - too many arguments.")
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
    interval = time_per_mode if time_per_mode is not None else (
        duration if duration is not None else 3.0
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
