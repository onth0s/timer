# timer

Full-screen terminal countdown timer with configurable pulse-on-time-out animations.

## Quick start

```bash
timer 6m30s
```

A bare number counts seconds. Use `m` and `s` suffixes for minutes and seconds:

```bash
timer 90        # 90 seconds
timer 5m        # 5 minutes
timer 1m30s     # 1 minute 30 seconds
```

## Controls

| Key                | Action                  |
|--------------------|-------------------------|
| `Space`, `p`, `k`, `Enter` | Pause / resume    |
| `+` / `=`          | Add 30 seconds          |
| `-`                | Subtract 30 seconds     |
| `q`                | Quit                    |

## Animation modes

Each pulse mode uses a **radial sine wave** to drive per-cell brightness/color,
so the pulse is visibly a wave, not a static flicker:

| Mode         | Description                                                |
|--------------|------------------------------------------------------------|
| `ansi`       | 8-level ANSI brightness gradient (no extra deps)            |
| `rich`       | Rich `Live` with per-cell HSL color cycling (default)     |
| `drawille`   | Braille pixels displaced by interfering sine waves          |
| `smooth`     | 3-level brightness pulse via radial wave                   |
| `ghostprint` | CRT flicker with sine-wave brightness + character glitch    |
| `asciimatics`| TUI animation engine with sine-wave colors                |

## Configuration

Create `config.yaml` in the project root:

```yaml
anim: rich
```

Override the animation for one run without changing config:

```bash
timer --anim drawille 5
```

Invalid `anim` values fail loudly (no silent fallback):

```
$ timer config anim neon-rave
Usage: timer config anim [MODE]
Try 'timer config anim --help' for help.

Error: Invalid anim mode: 'neon-rave'. Valid modes: ansi, rich, drawille, smooth, ghostprint, asciimatics
```

## Subcommands

| Command | Description |
|---------|-------------|
| `timer DURATION` | Run countdown (e.g. `timer 5`, `timer 1m30s`) |
| `timer --anim MODE DURATION` | Override animation for this run |
| `timer showcase [DURATION]` | Cycle through every pulse animation mode |
| `timer config init` | Create default `config.yaml` |
| `timer config show` | Show resolved config |
| `timer config path` | Print path to `config.yaml` |
| `timer config anim [MODE]` | Show or set animation mode |

### `timer showcase`

Cycles through every pulse animation mode (default 3 seconds each),
displaying the mode name in the top-left corner. Useful for comparing
animations or just watching them cycle.

```bash
timer showcase              # 3s per mode, infinite loop, alphabetical order
timer showcase 1            # 1 second per mode (positional)
timer showcase -t 5         # 5 seconds per mode
timer showcase --random     # shuffle the mode order each cycle
timer showcase --once       # cycle through once and exit
```

Exit any time with `q` or `Ctrl+C`. The asciimatics segment runs as its own
bounded screen exit-and-restart per cycle.

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
