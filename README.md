# timer

Full-screen terminal countdown timer with stopwatch mode and configurable pulse-on-timeout animations.

## Quick start

```bash
timer 6m30s        # count down from 6 minutes 30 seconds
timer               # count up (stopwatch mode)
```

## Duration & Target Time formats

A bare number counts seconds. Use `h`, `m`, and `s` suffixes, colon notation, or target clock times:

```bash
timer 90            # 90 seconds
timer 5m            # 5 minutes
timer 1m30s         # 1 minute 30 seconds
timer 1h            # 1 hour
timer 2d            # 2 days
timer 2d1h30m       # 2 days 1 hour 30 minutes
timer 1h30          # 1 hour 30 minutes (short form)
timer 2m45          # 2 minutes 45 seconds (short form)
timer 4:40          # 4 hours 40 minutes (HH:MM colon format)
timer 1:02:03       # 1 hour 2 minutes 3 seconds (HH:MM:SS format)
timer :01:20        # 1 minute 20 seconds (:MM:SS format)
timer -4:40PM       # Target time: count down until 4:40 PM
timer -16:40        # Target time: count down until 16:40 (24h clock)
```

A `d` suffix marks days; durations over 24h compact to daytime notation
everywhere (e.g. `timer 26h` summarizes as `1d2h`).

### Target Times (`-` prefix)

A leading `-` prefix indicates a **target clock time** to count down until:

- `timer -4:40PM` / `timer -16:40`: Counts down to the specified time today (or tomorrow if the target time has passed).

### Raw Seconds Display (`--raw` / `-r`)

Force raw bare seconds display without colons:

```bash
timer --raw 5m      # Counts down as 300, 299, 298... instead of 05:00
timer -r 300s       # Equivalent
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
│ Time to exit after timeout: 14m3s             │
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
| `timer --raw DURATION`        | Force raw seconds display (e.g. `timer --raw 5m`)|
| `timer --anim MODE DURATION`  | Override animation for this run                  |
| `timer showcase [DURATION]`   | Cycle through every pulse animation mode         |
| `timer config init`           | Create default `config.yaml`                     |
| `timer config show`           | Show resolved config                             |
| `timer config path`           | Print path to `config.yaml`                      |
| `timer config anim [MODE]`  | Show or set animation mode              |
| `timer schedule ...`        | Lightweight deadlines (never run in the background) |

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

## Schedules

Schedules are deadlines that **never run in the background**. Adding one just
stores an epoch in `timer.yaml`; you check in on it whenever you like and the
remaining time is pure arithmetic. Nothing ticks between check-ins.

```bash
timer schedule 1h pomodoro   # deadline 1 hour from now, alias "pomodoro"
timer schedule 25m           # unnamed (pick it by list number)
timer schedule 2d1h30m bake  # day notation works too
timer schedule -23:45 dinner # clock time today (tomorrow if it has passed)
timer schedule -4:40PM standup
```

Relative durations (`25m`, `2d1h30m`) and dash-prefixed clock times
(`-23:45`, `-4:40PM`) both work; the dash is only for target clock times.

### Checking in

```bash
timer schedule               # same as `timer schedule list`
timer schedule list          # FILO stack: newest first, # column selects it
timer schedule list --now    # accepted; lists are already a static snapshot
timer schedule 1             # full-screen big timer for that row
timer schedule pomodoro      # by alias
timer schedule 1 --now       # one-shot status panel instead of the big timer
timer schedule 1 --expand    # explicit: run the big timer (default for check-in)
timer schedule 1h x -e       # add "x", then immediately launch its big timer
```

Check-in always runs the full-screen animated countdown (config `anim` mode
applies). `--now` prints a static summary instead — it's the only static path.
When the deadline has passed, the row is marked `Timeout!` in the list; a
check-in still runs the big timer at `00:00` with the pulse (static notice
only under `--now`).

Unnamed schedules show an italic `null` in the Alias column — pick them by their
`#`. Every operation prints a clear message naming what happened, the position,
and which `timer.yaml` was touched — nothing happens silently.

### Removing

```bash
timer schedule rm pomodoro   # remove one schedule by alias
timer schedule rm 1          # ...or by list number
timer schedule nuke          # removes everything after a y/N confirmation
```

Aliases must not look like numbers, durations, or the reserved words
`list`/`nuke`/`rm`. Duplicate aliases are rejected when added and when the
file is loaded (hand-edited `timer.yaml` cannot smuggle collisions).

### Storage

Schedules live in `timer.yaml`. A `timer.yaml` in the current directory takes
precedence; otherwise the store falls back to `~/.config/timer.yaml`:

```
$HOME/dev/project/timer.yaml   # CWD wins when present
~/.config/timer.yaml           # otherwise
```

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
