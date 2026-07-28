# AGENTS.md

## Rules

- After editing any `.py` file, run `ruff check <file>` to catch lint issues. Run `ruff check .` and `python -m pytest` to verify changes across the codebase.
- Use `rich` (`rich.console.Console`, `rich.table.Table`, `rich.panel.Panel`, `rich.text.Text`) for all user-facing CLI logs, status messages, table outputs, and error/warning prompts to maintain vibrant, high-contrast, structured styling across terminal outputs.
- All output must be human-readable if it is to be read by a user.
- Write a cute BANZAI! message after all tests pass. NEVER HARDCODE THIS. Ensure kaomojis do not use `\(` or `\$` to prevent triggering KaTeX/LaTeX math syntax errors.
- When asked a DIRECT QUESTION, you MUST RESPOND IMMEDIATELY.
- **NEVER use real timers in tests longer than 3 seconds.** Any timer test must use `fake_clock` mocks or short durations (3s or less). Tests with `60m`, `10m`, etc. without proper mocking will hang the test suite.
- **Strict validation in `config.yaml`** — invalid `anim` values raise `ValueError` listing valid options. Never silently fall back. Validate at `set()` time AND at `load()` time. CLI surfaces the error as a `click.UsageError` so it appears in `--help` and `result.output`.


## Scratch

Use `scratch/` for temporary files, one-off scripts, experiments, and anything not meant for the final deliverable.
