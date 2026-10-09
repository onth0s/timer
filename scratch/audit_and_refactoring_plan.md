# Codebase Audit, Review & Phased Refactoring Implementation Plan

**Repository:** `timer` (Terminal countdown timer, stopwatch, wall clock, scheduler, and pulse animator)  
**Date:** October 9, 2026  
**Baseline Health:**
- `uv run ruff check .` → **Clean (0 errors, 0 warnings)**
- `uv run pytest` → **199 passed in 0.80s** (100% passing, 0 slow/real timers)
- Test Coverage → **79.60%** (Passing threshold `>= 60.0%`)

---

## Part 1: Comprehensive Codebase Audit & Architecture Review

### 1.1 Architectural Overview & Module Responsibilities

The codebase is structured around several functional layers under `src/countdown/`:

```
src/countdown/
├── __main__.py          # Click CLI command definitions and CLI entrypoint
├── cli.py               # Custom Click Command/Group subclasses & dash-prefixed argument munging
├── clock.py             # Clock abstraction protocol & SystemClock implementation
├── clock_cmd.py         # Full-screen terminal digital wall clock loop & rendering
├── loop.py              # Countdown & count-up (stopwatch) run loop and pulse orchestrator
├── timer.py             # Duration parsing, unit compaction, and glyph conversion shims
├── display.py           # ANSI escapes, screen geometry, centering math, and terminal sizing
├── digits.py            # ASCII digit glyph dictionary loader (glyphs.txt)
├── config.py            # YAML configuration reader/writer with strict anim validation
├── schedule.py          # Deadline store data model, YAML persistence, remaining time math
├── schedules_cli.py     # Static & live schedule table rendering and management helpers
├── showcase.py          # Animation preview cycler loop
├── terminal.py          # Low-level platform terminal setup and raw keyboard polling
├── tests_cmd.py         # Terminal centering visualization command (`timer test`)
├── _map_viz.py          # 2D ASCII grid geometry map generator for terminal visualization
└── pulses/              # Pulse animation engine
    ├── __init__.py      # Lazy module registry, validation, and loader
    ├── base.py          # `make_pulse` frame-rate and phase generator
    ├── _wave.py         # Radial wave mathematics and HSL-to-RGB conversion
    └── {ansi, rich, smooth, drawille, ghostprint, asciimatics}.py
```

---

### 1.2 Detailed Audit Findings & Code Smells

#### 1. Architecture & Single Responsibility Principle (SRP)
- **F1: `__main__.py` remains oversized (555 lines) and mixes CLI declaration with orchestration:**
  - Defines 7 CLI command/group handlers (`main`, `countdown`/`run`, `config`, `schedule`, `showcase`, `test`, `clock`) with nested subcommands (`config init/show/path/anim`, `schedule list/nuke/rm/at`).
  - Contains inline business logic: interactive choice prompting for ambiguous duration units (lines 157–176), schedule argument dispatching, and error transformations.
  - Carries test-coupling compatibility shims (`run_countdown._original = run_countdown`, `run_clock._original = run_clock`) because tests patch wrapper functions rather than injecting dependencies.
- **F2: Leaky boundary between Time Domain (`timer.py`) and Visual Display (`display.py`):**
  - `src/countdown/timer.py` states its purpose as *"Time parsing and formatting utilities"*, but contains `render_time_string_glyphs()` and `get_number_lines()`, which convert strings to multi-line ASCII art fonts.
  - This couples domain duration logic directly to visual terminal font rendering.

#### 2. Code Duplication & Consistency
- **F3: Triplicated Terminal Lifecycle Setup/Teardown:**
  - Three distinct modules (`loop.py:91-94 / 214-215`, `clock_cmd.py:164-168 / 247-248`, and `showcase.py:68-71 / 97-98`) manually invoke:
    ```python
    enable_ansi_escape_codes()
    old_settings = setup_terminal()
    print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="")
    ...
    restore_terminal(old_settings)
    print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="")
    ```
  - Lacks a unified context manager (e.g. `terminal_session()` or `alt_screen()`), forcing repetitive mock boilerplate across step definitions and test helpers.
- **F4: Redundant Font Resolution & Bizarre Circular Conversion in `display.py`:**
  - `get_chars_for_terminal` and `get_clock_chars_for_terminal` duplicate font size selection loops across `DIGIT_SIZES`.
  - In `get_chars_for_terminal`, `get_required_width` takes a formatted `time_string`, passes it to `_parse_time_string` (which only parses `MM:SS` or `HH:MM:SS`), converts it back to integer seconds, and calls `get_number_lines` which formats it *again*.
  - Direct calculation of glyph dimensions from the time string without round-tripping through seconds is simpler, faster, and less error-prone.
- **F5: Disparity in Keyboard Responsiveness between Loops:**
  - In `src/countdown/loop.py`, `count_up` uses `sleep(1.0)` directly when unpaused. Pressing `q` or `Esc` during stopwatch mode can lag up to 1 second before the keypress is detected.
  - In `src/countdown/clock_cmd.py`, responsive sub-interval polling (`sleep_fn(min(0.05, max(0.001, target - time_fn())))`) checks `check_for_keypress()` continuously.

#### 3. Dead Code & Incomplete Abstractions
- **F6: Dead variable in `loop.py`:**
  - In `count_up` mode, `pause_accum = 0.0` is initialized (line 103) and updated (`pause_accum += time() - pause_start`, line 121), but `pause_accum` is never read anywhere.
- **F7: Clock Abstraction Inconsistencies:**
  - `Clock` protocol (`clock.py`) was introduced for dependency injection, but `clock_cmd.py` contains `if isinstance(clock, SystemClock):` branching, violating the Liskov Substitution Principle.
  - `schedules_cli.py`, `showcase.py`, and `pulses/base.py` do not use `Clock` at all, importing `time` and `sleep` directly from the standard library and necessitating module-level monkeypatching in tests.
- **F8: 0% Test Coverage for Geometry Diagnostic Modules:**
  - `src/countdown/_map_viz.py` (68 statements) and `src/countdown/tests_cmd.py` (20 statements) have **0% test coverage**.
  - The CLI command `timer test` is misleadingly named (it prints a centering terminal map, not a test suite).

#### 4. User-Facing Styling & Rule Compliance (AGENTS.md)
- **F9: Plain `click.echo` instead of Rich in `config` & prompt commands:**
  - AGENTS.md explicitly mandates: *"Use rich (rich.console.Console, rich.table.Table, rich.panel.Panel, rich.text.Text) for all user-facing CLI logs, status messages, table outputs, and error/warning prompts to maintain vibrant, high-contrast, structured styling across terminal outputs."*
  - `__main__.py` currently uses unstyled `click.echo()` and `click.prompt()` in `config init`, `config path`, `config anim`, and the ambiguous duration prompt (lines 161–169, 201, 219, 232, 239).

---

## Part 2: Phased Sequential Refactoring Implementation Plan

The refactoring is structured into **6 discrete, sequential phases**. Each phase preserves 100% backward compatibility, keeps all 199 tests passing at every step, and adheres to zero-real-time test rules.

```
┌────────────────────────────────────────────────────────┐
│ Phase 1: CLI Modernization & Rich Output Alignment     │
│ - Extract command definitions from __main__.py         │
│ - Upgrade raw click.echo to Rich Console / Panels      │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ Phase 2: Terminal Session Context Manager              │
│ - Deduplicate alt-buffer & cursor lifecycle            │
│ - Unify terminal_session across loop, clock, showcase  │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ Phase 3: Display & Glyph Engine Consolidation          │
│ - Move glyph rendering to visual layer                 │
│ - Deduplicate get_chars_for_terminal font selection    │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ Phase 4: Event Loop & Clock Protocol Unification       │
│ - Eliminate dead pause_accum & loop responsiveness lag │
│ - Standardize Clock injection across CLI tools         │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ Phase 5: Diagnostic Geometry & Test Coverage           │
│ - Add unit tests for _map_viz.py and tests_cmd.py      │
│ - Boost total codebase coverage > 85%                  │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ Phase 6: Typing & Static Analysis Hardening            │
│ - Add complete type hints across all modules           │
│ - Validate via `ruff check` and `just check`           │
└────────────────────────────────────────────────────────┘
```

---

### Phase 1: CLI Modernization & Rich Output Alignment

**Goal:** Shrink `__main__.py` into a thin CLI routing entrypoint; replace unstyled `click.echo` with high-contrast `rich` styling in accordance with `AGENTS.md`.

#### Tasks:
1. **Rich Output Alignment (AGENTS.md):**
   - Replace `click.echo` in `config init`, `config path`, and `config anim` with `Console().print(...)` using styled `Text` or `Panel`.
   - Upgrade the ambiguous duration interactive prompt in `countdown` (`needs_prompt`) to a styled Rich Panel/Prompt.
2. **Subcommand Extraction:**
   - Move `config` command definitions to `src/countdown/config_cli.py` (or integrate into `src/countdown/config.py`).
   - Move `schedule` group and command wiring into `src/countdown/schedules_cli.py`.
   - Retain public top-level imports in `__main__.py` (`main`, `run_countdown`, `run_clock`) so existing Click entrypoints and test harnesses remain unbroken.
3. **Verification Gate:**
   - Run `uv run ruff check .`
   - Run `uv run pytest` (all 199 tests must pass).

---

### Phase 2: Terminal Session Context Manager

**Goal:** Deduplicate terminal screen lifecycle management across `loop.py`, `clock_cmd.py`, and `showcase.py`.

#### Tasks:
1. **Implement `terminal_session()` in `src/countdown/terminal.py` or `display.py`:**
   ```python
   @contextmanager
   def terminal_session():
       """Context manager configuring ANSI alt-buffer and raw keyboard mode."""
       enable_ansi_escape_codes()
       old_settings = setup_terminal()
       print(ENABLE_ALT_BUFFER + HIDE_CURSOR, end="", flush=True)
       try:
           yield
       finally:
           restore_terminal(old_settings)
           print(SHOW_CURSOR + DISABLE_ALT_BUFFER, end="", flush=True)
   ```
2. **Refactor Call Sites:**
   - Refactor `loop.py`, `clock_cmd.py`, and `showcase.py` to use `with terminal_session():`.
   - Update `tests/helpers.py` so mocking `terminal_session` simplifies the 6 individual monkeypatches currently required.
3. **Verification Gate:**
   - Run `uv run ruff check .`
   - Run `uv run pytest`.

---

### Phase 3: Display & Glyph Engine Consolidation

**Goal:** Eliminate redundant font calculation, remove the circular duration-to-string-to-seconds roundtrip, and establish clean boundaries between duration math and ASCII art.

#### Tasks:
1. **Unify Font Selection in `display.py`:**
   - Consolidate `get_chars_for_terminal` and `get_clock_chars_for_terminal` into a single canonical `get_best_font_size(time_str: str, extra_height: int = 0)`.
   - Remove `_parse_time_string` in `display.py` and measure the glyph dimensions directly from the target `time_str`.
   - Maintain `get_chars_for_terminal` and `get_clock_chars_for_terminal` as thin backward-compatible delegates.
2. **Re-export Cleanly:**
   - Retain re-exports of `get_number_lines` and `render_time_string_glyphs` in `timer.py` for backward compatibility with existing tests.
3. **Verification Gate:**
   - Run `uv run pytest tests/step_defs/test_glyph_width.py` (ensure zero layout jitter).
   - Run `uv run pytest` across the full test suite.

---

### Phase 4: Event Loop & Clock Protocol Unification

**Goal:** Remove dead state, ensure uniform keypress responsiveness in stopwatch mode, and standardize clock injection.

#### Tasks:
1. **Clean up `loop.py`:**
   - Remove the unused `pause_accum` variable in count-up mode.
   - Refactor count-up sleeping so that keypresses (`q`, `Esc`, `p`) are polled at 50ms intervals rather than blocking for 1.0 full second on `sleep(1.0)`.
2. **Clean up `clock_cmd.py`:**
   - Replace the `isinstance(clock, SystemClock)` branch with uniform clock polling that works cleanly with both `SystemClock` and `FakeClock`.
3. **Inject Clock into `schedules_cli.py`:**
   - Allow passing a `Clock` instance to `render_schedule_live` (defaulting to `STDCLOCK`), reducing module-level monkeypatching in `test_schedule.py`.
4. **Verification Gate:**
   - Run `uv run pytest tests/step_defs/test_countup_loop.py tests/step_defs/test_countdown_loop.py tests/step_defs/test_clock.py`.
   - Run `uv run pytest`.

---

### Phase 5: Diagnostic Geometry & Test Coverage Hardening

**Goal:** Elevate test coverage for untested geometry modules and clarify diagnostic CLI tooling.

#### Tasks:
1. **Test `_map_viz.py` and `tests_cmd.py`:**
   - Add unit tests in `tests/test_map_viz.py` covering grid construction, corner marking, edge midpoints, quadrant boundaries, and string serialization.
   - Test `run_tests_cmd()` execution with a mocked terminal size to eliminate the 0% coverage gap.
2. **Verify Coverage:**
   - Run `uv run pytest --cov=countdown --cov-report=term-missing`.
   - Confirm total project coverage increases from ~79.6% to > 85%.
3. **Verification Gate:**
   - Run `uv run ruff check .`
   - Run `uv run pytest`.

---

### Phase 6: Typing & Static Analysis Hardening

**Goal:** Add complete type annotations across all modules, maintain clean linting, and ratify the entire test suite.

#### Tasks:
1. **Type Annotations:**
   - Add complete type signatures (parameters and return types) across `timer.py`, `display.py`, `schedules_cli.py`, and `loop.py`.
2. **Lint & Formatting Pass:**
   - Run `uv run ruff check --fix .`
   - Run `uv run ruff format --check .`
   - Run `just check` end-to-end.
3. **Banzai Celebration:**
   - Output dynamic BANZAI message upon full completion with KaTeX-safe kaomojis (avoiding unescaped `(` and `$`).

---

## Part 3: Explicit Invariants & Non-Goals

1. **Non-Goals:**
   - No breaking changes to CLI command syntax or flag names (`timer run`, `timer schedule`, `timer clock`, `timer config`).
   - No changes to `config.yaml` strict validation behavior (`validate_anim_mode` remains strict and authoritative).
   - No introduction of external runtime dependencies.
2. **Strict Invariants:**
   - **Zero real time > 3s in tests:** All tests must continue executing in under 2 seconds total via `FakeClock`.
   - **High-contrast Rich styling:** All user-facing terminal logs, tables, and panels must use `rich`.
   - **100% test pass rate:** Every phase must leave all 199+ tests green.
