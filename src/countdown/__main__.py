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


def get_number_lines(seconds):
    """Return list of lines which make large MM:SS glyphs for given seconds."""
    return timer.get_number_lines(seconds, get_chars_for_terminal(seconds))


def run_countdown(total_seconds, pulse_fn=None, max_pulses=None):
    """Run the countdown timer for the specified duration.

    Args:
        total_seconds: Duration in seconds to count down from
        pulse_fn: Callable(lines) called after countdown reaches 0
                  to animate the finished state. Returns either None (prints
                  to stdout directly) or a Rich Text/Console renderable.
        max_pulses: Maximum pulse iterations before exiting (default: None = infinite).
    """
    from .pulses.ansi import pulse_ansi

    if pulse_fn is None:
        pulse_fn = pulse_ansi

    enable_ansi_escape_codes()
    old_settings = setup_terminal()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")
    try:
        paused = False
        n = total_seconds
        sleep_until = time() + total_seconds
        pause_start = None
        while n >= 0 or paused:
            lines = get_number_lines(n)
            print_full_screen(lines, paused=paused)

            # Check for keypress to toggle pause or adjust time
            if check_for_keypress():
                key = read_key()  # Consume the keypress

                if key == "q":
                    # Quit the timer
                    break
                elif is_pause_key(key):
                    if paused:
                        sleep_until += time() - pause_start
                        pause_start = None
                    else:
                        pause_start = time()
                    paused = not paused
                    drain_keypresses()  # Ignore any additional rapid keypresses
                    lines = get_number_lines(n)
                    print_full_screen(lines, paused=paused)
                elif is_time_adjust_key(key):
                    # Adjust the timer by +/- 30 seconds
                    adjustment = get_time_adjustment(key)
                    new_n = max(0, n + adjustment)  # Don't go below 0
                    sleep_until += new_n - n
                    n = new_n
                    drain_keypresses()  # Ignore any additional rapid keypresses
                    lines = get_number_lines(n)
                    print_full_screen(lines, paused=paused)

            # Only sleep and decrement if not paused
            if not paused:
                # Wall-clock time at which to move from displaying n to n-1
                display_this_second_until = sleep_until - n + 1
                while time() < display_this_second_until:
                    # Sleep in small chunks to check for keypresses more frequently
                    sleep(0.05)
                    if check_for_keypress():
                        break  # Exit sleep early if key is pressed
                n -= 1
            else:
                # Short sleep when paused for responsive keypress checking
                sleep(0.05)

        # Pulse phase: animate the zero state until user presses a key.
        # If pulse_fn returns a renderable, use Rich Live; otherwise pulse_fn
        # is expected to print directly to stdout.
        from rich.console import Console
        from rich.live import Live

        pulse_count = 0
        renderable = None
        live = None

        while not check_for_keypress():
            if max_pulses is not None and pulse_count >= max_pulses:
                break

            new_renderable = pulse_fn(get_number_lines(0))

            if new_renderable is not None:
                if live is None:
                    console = Console()
                    live = Live(
                        console=console,
                        screen=False,
                        refresh_per_second=20,
                        vertical_overflow="visible",
                    )
                    live.__enter__()
                    renderable = new_renderable
                    live.update(renderable)
                elif new_renderable is not renderable:
                    renderable = new_renderable
                    live.update(renderable)
            sleep(0.05)
            pulse_count += 1

        if live is not None:
            live.__exit__(None, None, None)
    except KeyboardInterrupt:
        pass
    finally:
        restore_terminal(old_settings)
        print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="")


# Store original on the function for tests to bypass the default wrapper.
run_countdown._original = run_countdown  # type: ignore[attr-defined]


# ====================================================================
# Click subcommands
# ====================================================================


class SmartGroup(click.Group):
    """Group that forwards unmatched positional args to the ``timer`` subcommand.

    Lets ``timer 5`` work as an alias for ``timer timer 5``.
    """

    def resolve_command(self, ctx, args):
        """Route non-subcommand positional args to the timer subcommand."""
        if args and args[0] not in self.commands:
            return "timer", self.commands["timer"], args
        return super().resolve_command(ctx, args)


@click.group(invoke_without_command=True, cls=SmartGroup)
@click.version_option(package_name="timer")
@click.pass_context
def main(ctx):
    """Countdown timer for the terminal with configurable pulse animations."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command(name="timer")
@click.option(
    "--anim",
    type=click.Choice(list(VALID_ANIM_MODES)),
    help="Override animation mode for this run.",
)
@click.argument("duration", required=False)
def countdown(anim, duration):
    r"""Run the countdown timer for the given DURATION.

    DURATION should be a number followed by m or s for minutes or seconds.
    A bare number is interpreted as seconds.

    Examples:
    \b
    - 10 (10 seconds)
    - 5m (5 minutes)
    - 45s (45 seconds)
    - 2m30s (2 minutes and 30 seconds)

    Press Space, p, k, or Enter to pause/resume the countdown.
    Press +/= to add 30 seconds, - to subtract 30 seconds.
    Press q to quit.
    """
    from . import timer as timer_mod

    if duration is None:
        click.echo(click.get_current_context().get_help())
        return

    try:
        total_seconds = timer_mod.duration(duration)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    config = Config.load()
    try:
        mode = anim if anim is not None else config.get("anim") or "rich"
        pulse_fn = get_pulse_fn(mode)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    run_countdown(total_seconds, pulse_fn=pulse_fn)


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


if __name__ == "__main__":
    main(prog_name="countdown")  # pragma: no cover
