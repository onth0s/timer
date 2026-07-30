# timer

Full-screen terminal countdown timer with stopwatch mode and configurable pulse-on-timeout animations.

## Quick start

```bash
timer 6m30s        # count down from 6 minutes 30 seconds
timer               # count up (stopwatch mode)
```

## Duration formats

A bare number counts seconds. Use `h`, `m`, and `s` suffixes:

```bash
timer 90            # 90 seconds
timer 5m            # 5 minutes
timer 1m30s         # 1 minute 30 seconds
timer 1h            # 1 hour
timer 1h30          # 1 hour 30 minutes (short form)
timer 2m45          # 2 minutes 45 seconds (short form)
```

## Stopwatch mode

Running `timer` with no duration starts the stopwatch, counting up from zero:

```bash
timer
timer run           # equivalent
```

The display grows naturally with elapsed time:

| Elapsed      | Display    |
|--------------|------------|
| 0 – 59 s     | `SS`       |
| 60 s – 59:59 | `MM:SS`    |
| 1 h+         | `HH:MM:SS` |

On exit a summary panel shows how long the stopwatch ran.

## Countdown behaviour

When the countdown reaches zero, a pulse animation fires. On any subsequent keypress or interrupt, the terminal prints how long it took to exit after the timeout:

```
╭── Timer Summary ──────────────────────────────╮
│ Timer completed (5m)                          │
│ Time to exit after timeout: 1.24s             │
╰───────────────────────────────────────────────╯
```

If you quit early:

```
╭── Timer Summary ──────────────────────────────╮
│ Timer stopped early (5m configured)           │
╰───────────────────────────────────────────────╯
```

## Controls

| Key                          | Action              |
|------------------------------|---------------------|
| `Space`, `p`, `k`, `Enter`   | Pause / resume      |
| `+` / `=`                    | Add 30 seconds      |
| `-`                          | Subtract 30 seconds |
| `q`, `Esc`                   | Quit                |
| `Ctrl+C`                     | Quit                |

## Animation modes

Each mode drives a **radial sine wave** per cell, so the pulse is a visible wave rather than a static flicker:

| Mode          | Description                                                 |
|---------------|-------------------------------------------------------------|
| `rich`        | Per-cell HSL color cycling via Rich `Live` (default)        |
| `ansi`        | 8-level ANSI brightness gradient (no extra deps)            |
| `braille`     | Braille pixels displaced by interfering sine waves          |
| `drawille`    | Braille canvas with drawille library                        |
| `smooth`      | 3-level brightness pulse via radial wave                    |
| `ghostprint`  | CRT flicker — sine-wave brightness + character glitch       |
| `asciimatics` | TUI animation engine with sine-wave colors                  |

## Configuration

`config.yaml` in the project root (created automatically by `timer config init`):

```yaml
anim: rich
```

Override for a single run without touching config:

```bash
timer --anim drawille 5m
```

Invalid `anim` values fail loudly — no silent fallback:

```
$ timer config anim neon-rave
Error: Invalid anim mode: 'neon-rave'. Valid modes: ansi, rich, drawille, smooth, ghostprint, asciimatics
```

## Subcommands

| Command                       | Description                                      |
|-------------------------------|--------------------------------------------------|
| `timer DURATION`              | Count down (e.g. `timer 5`, `timer 1m30s`)       |
| `timer`                       | Count up from 0 (stopwatch)                      |
| `timer run [DURATION]`        | Explicit run subcommand; no duration = stopwatch |
| `timer --anim MODE DURATION`  | Override animation for this run                  |
| `timer showcase [DURATION]`   | Cycle through every pulse animation mode         |
| `timer config init`           | Create default `config.yaml`                     |
| `timer config show`           | Show resolved config                             |
| `timer config path`           | Print path to `config.yaml`                      |
| `timer config anim [MODE]`    | Show or set animation mode                       |

### `timer showcase`

Cycles through every pulse animation mode (default 3 seconds each). Useful for comparing animations or just watching them cycle.

```bash
timer showcase              # 3 s per mode, infinite loop, alphabetical order
timer showcase 1            # 1 second per mode (positional)
timer showcase -t 5         # 5 seconds per mode (flag)
timer showcase --random     # shuffle the mode order each cycle
timer showcase --once       # cycle through once then exit
```

Exit any time with `q` or `Ctrl+C`.

## Installation

```bash
pip install timer
```

For development:

```bash
git clone https://github.com/onth0s/timer
cd timer
uv sync
uv run timer 5
```

Run the test suite:

```bash
python -m pytest
```
