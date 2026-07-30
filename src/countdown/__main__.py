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


def get_number_lines(seconds, *, show_hours=False, count_up=False):
    """Return list of lines which make large glyphs for the time display."""
    return timer.get_number_lines(
        seconds,
        get_chars_for_terminal(seconds, show_hours=show_hours),
        show_hours=show_hours,
        count_up=count_up,
    )


def run_countdown(
    total_seconds,
    pulse_fn=None,
    max_pulses=None,
    *,
    show_hours=False,
    count_up=False,
):
    """Run the countdown or count-up timer.

    Args:
        total_seconds: Duration in seconds to count down from (or None for count-up)
        pulse_fn: Callable(lines) called after countdown reaches 0
        max_pulses: Maximum pulse iterations before exiting.
        show_hours: If True, display as HH:MM:SS.
        count_up: If True, count up starting from 0 (stopwatch mode).
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
            start_time = time()
            pause_accum = 0.0
            pause_start = None
            while True:
                lines = get_number_lines(n, show_hours=show_hours, count_up=True)
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
                    sleep(0.05)
                    n = int(time() - start_time - pause_accum)
                else:
                    sleep(0.05)
        else:
            n = total_seconds
            sleep_until = time() + total_seconds
            pause_start = None
            while n >= 0 or paused:
                lines = get_number_lines(n, show_hours=show_hours)
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
                        lines = get_number_lines(n, show_hours=show_hours)
                        print_full_screen(lines, paused=paused)
                    elif is_time_adjust_key(key):
                        adjustment = get_time_adjustment(key)
                        new_n = max(0, n + adjustment)
                        sleep_until += new_n - n
                        n = new_n
                        drain_keypresses()
                        lines = get_number_lines(n, show_hours=show_hours)
                        print_full_screen(lines, paused=paused)

                if not paused:
                    display_this_second_until = sleep_until - n + 1
                    while time() < display_this_second_until:
                        # Sleep remainder or step up to display_this_second_until
                        remaining = display_this_second_until - time()
                        sleep(min(0.05, max(0.001, remaining)))
                        if check_for_keypress():
                            break
                    n -= 1
                else:
                    sleep(0.05)

            # Record epoch timestamp when reaching zero
            zero_epoch = time()

            if getattr(pulse_fn, "__name__", "") == "pulse_asciimatics":
                print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="", flush=True)
                pulse_fn(get_number_lines(0, show_hours=show_hours))
                exit_delay = time() - zero_epoch
                return

            pulse_count = 0
            while not check_for_keypress():
                if max_pulses is not None and pulse_count >= max_pulses:
                    break
                pulse_fn(get_number_lines(0, show_hours=show_hours))
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
            dur_str = timer.format_duration(timer.duration(f"{final_seconds}s"))
            console.print(
                Panel(
                    f"[bold green]Timer ran for {dur_str}[/bold green]",
                    title="[bold cyan]Timer Summary[/bold cyan]",
                    expand=False,
                )
            )
        else:
            total_ran = timer.format_duration(timer.duration(f"{total_seconds}s"))
            if exit_delay is not None:
                delay_str = f"{exit_delay:.2f}s"
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


class SmartGroup(click.Group):
    """Group that forwards unmatched positional args to the ``run`` subcommand.

    Lets ``timer 5`` work as an alias for ``timer run 5``.
    """

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


@main.command(name="run")
@click.option(
    "--anim",
    type=click.Choice(list(VALID_ANIM_MODES)),
    help="Override animation mode for this run.",
)
@click.argument("duration", required=False)
def countdown(anim, duration):
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
        run_countdown(0, pulse_fn=pulse_fn, count_up=True)
        return

    try:
        dur = timer_mod.duration(duration)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    if timer_mod.needs_prompt(dur):
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

    show_hours = "h" in dur.components
    run_countdown(dur.total_seconds, pulse_fn=pulse_fn, show_hours=show_hours)


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
