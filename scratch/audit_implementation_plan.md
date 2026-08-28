# Codebase Audit & Refactoring Implementation Plan — `timer`

Audit date: 2026-08-28
Baseline: `ruff check .` clean · `pytest` **176 passed** in 0.62s · no real-time calls in tests (FakeClock)

---

## Part 1 — Codebase Audit

### 1.1 Inventory

| Path | Lines | Responsibility |
|------|------:|----------------|
| `src/countdown/__main__.py` | 954 | CLI (Click groups/commands), run loop, summary rendering |
| `src/countdown/timer.py` | 338 | Duration parse/format, `get_number_lines`, `Duration` |
| `src/countdown/display.py` | 232 | ANSI control, centering, `get_chars_for_terminal`, full-screen print |
| `src/countdown/schedule.py` | 216 | Non-background schedules store + helpers |
| `src/countdown/pulses/__init__.py` | 64 | Pulse mode registry + validation |
| `src/countdown/showcase.py` | 128 | Showcase cycling loop |
| `src/countdown/digits.py` | 66 | Glyph constants built from `glyphs.txt` |
| `src/countdown/terminal.py` | 60 | Platform terminal/keyboard I/O (no cover) |
| `src/countdown/config.py` | 67 | `config.yaml` loader with strict anim validation |
| `src/countdown/keys.py` | 20 | Key classification |
| `src/countdown/tests_cmd.py` | 39 | `timer test` verbose command |
| `src/countdown/_map_viz.py` | 111 | Centering grid helpers |
| `src/countdown/pulses/_wave.py` | 59 | Shared wave math |
| `src/countdown/pulses/{ansi,rich,smooth,drawille,ghostprint,asciimatics}.py` | ~100 ea | Pulse animation modes |
| `tests/` | ~46 KB | BDD + unit tests (13 step-def files, 11 features) |

### 1.2 Architecture
Layered, single-purpose modules with a thin application core:
- **Domain/types:** `timer.py` (Duration), `keys.py`, `digits.py`
- **I/O:** `terminal.py`, `display.py`
- **Config/state:** `config.py`, `schedule.py`
- **Rendering/effects:** `pulses/`, `showcase.py`
- **Application/CLI:** `__main__.py`
- **Support/diagnostic:** `tests_cmd.py`, `_map_viz.py`

Overall structure is sound. The dominant problem is **module bloat and duplication concentrated in `__main__.py`** (954 lines), which mixes Click command definitions, the timing/pulse run loop, and six different rendering helpers that create feedback loops in tests.

### 1.3 Findings

**F1 — `__main__.py` is a 954-line god module (high severity).**
It mixes:
1. Click groups/commands + several bespoke `Command`/`Group` subclasses (`RunCommand`, `SmartGroup`, `ScheduleGroup`, `ScheduleAtCommand`) + `_fix_dash_args`.
2. The full countdown/count-up run loop (`run_countdown`) — timing, pause, time-adjust, pulse orchestration, summary rendering.
3. Six schedule-rendering/helper functions (`load_store`, `_schedule_table`, `render_schedule_list`, `render_schedule_live`, `add_schedule`, `check_schedule`).
4. A re-export shim `get_number_lines` that just calls `timer.get_number_lines` (see F2).

**F2 — `get_number_lines` duplicated (medium).**
`__main__.py:35` wraps `timer.get_number_lines`, but `display.py` and pulse modules also reach into `timer.get_number_lines` directly. The `__main__` wrapper adds a layer that tests must patch and provides no new behaviour. The `_format_time_string` logic is **also** re-implemented inside `timer.get_number_lines` (timer.py:310-328) — two independent copies of the same time-format branch chain that must stay in sync.

**F3 — Duplicate `validate_anim_mode` (low/medium).**
`config.py:10` and `pulses/__init__.py:51` define identical functions with identical error text. Two sources of truth for one rule.

**F4 — Rendering helpers & summary embedded in `__main__` (medium).**
The `run_countdown` `finally` block (lines 197-244) builds Rich `Panel` summaries inline, mixing presentation with control flow. `_schedule_table`/`render_*`/`add_schedule`/`check_schedule` (lines 516-731) are presentation logic that belong in a view layer.

**F5 — Duplicative centering implementations (medium).**
`display.centered_frame` (display.py:88) and `print_full_screen` (display.py:196) both independently compute vertical/horizontal padding with subtly different rules (padding allowance `size == 3`, pause-text handling). Two rounding behaviours can disagree about placement.

**F6 — Dead/experimental code (low).**
- `notes`-style docstrings in `terminal.py` don't match the repo's Google convention (noted for docs pass, not a bug).
- `rich.py` keeps a "legacy Rich-object API" (`_style_row`, `_h_pad`, `build_wave_renderable`) explicitly marked "not used by the pulse-hot-path", retained only for tests (lines 119-188).
- `tests_cmd.py` / `_map_viz.py` are diagnostic-only (`timer test`), useful but out of the main flow.

**F7 — Tests couple to implementation, not behaviour (medium).**
Tests monkeypatch `countdown.__main__.{time,sleep,get_number_lines,print_full_screen,check_for_keypress,read_key,setup_terminal,restore_terminal,enable_ansi_escape_codes,run_countdown}` and `builtins.print`. The suite is robust (176 passing, zero real time) but is tightly bound to `__main__`'s internal names, which makes the refactor heavier to land and any renames costly.

**F8 — `pulses/__init__.py` `get_pulse_fn` is an if/elif dispatch chain (low).**
A registry dict mapping mode → lazy importer would remove 7 branches and keep lazy import behaviour.

**F9 — `time` module imported at module top of `__main__.py` (`sleep`, `time`) (low).**
Necessary and fine for the CLI, but the run loop's use of module-level `time`/`sleep` is exactly what tests patch; factoring the loop into `timer.py` lets the loop be tested without `__main__` patching.

### 1.4 Strengths (preserve)
- Reliable FakeClock/MockKeys test strategy — zero real OS time/sleep in tests (satisfies AGENTS.md timer rule).
- Strict config validation with no silent fallback (AGENTS.md requirement) — correctly surfaced as `click.UsageError`.
- Lazy imports in `get_pulse_fn` and inside Click commands keep startup fast.
- Clear module boundaries for domain (`timer.py`) vs I/O (`terminal.py`).
- Consistent Rich styling for user-facing output.

### 1.5 Refactor Goals
1. SHRINK `__main__.py` to pure Click wiring (command definitions + argument parsing).
2. Extract the run loop into `timer.py` so timing/state tie to a `Clock` abstraction (testable without `__main__` patch).
3. Extract schedule CLI presentation into a `schedules_cli` / view helper module.
4. Collapse duplicate `get_number_lines`/`_format_time_string` into one source of truth.
5. Single source of truth for `validate_anim_mode`.
6. Keep **all 176 tests green** after each phase; add/adjust tests only where the public surface legitimately changes.
7. Preserve the rich, high-contrast terminal styling and BANZAI! messaging convention.

---

## Part 2 — Implementation Plan (executed sequentially, phase by phase)

Each phase is self-contained, compiles, and keeps the suite green before the next phase begins.

### Phase 0 — Establish test-safety net (no production change)
- Confirm `uv run ruff check .` and `uv run pytest` pass.
- Run `uv run pytest --cov=countdown` (excluding the omitted `pulses/*`) to capture the pre-refactor coverage baseline for the 60% `fail_under` gate and `coverage/report` omit list.
- **Exit criteria:** baseline numbers recorded; no code changed.

### Phase 1 — Single source of truth for animation validation
- Delete `validate_anim_mode` from `pulses/__init__.py:51`; keep `get_pulse_fn` (still raises the same `ValueError`).
- Make `config.py` import `validate_anim_mode` — but instead of a separate function, have `config.validate_anim_mode` delegate to the canonical validator owned by `pulses` (e.g. keep `pulses.validate_anim_mode` and have `config` re-export/import it), OR invert: define the validator in `config` and have `get_pulse_fn` call it.
- **Decision:** canonicalize in `pulses/__init__.py` (the registry owns valid modes). `config.py` imports `from .pulses import validate_anim_mode` and drops its local copy; re-export via `__all__` for backward compat.
- Update `tests/step_defs/test_config.py` if it references the old symbol (it tests via `Config`, so no change expected).
- **Exit criteria:** `ruff` clean, `pytest` 176 green, no duplicate validator.

### Phase 2 — Collapse `get_number_lines` & `_format_time_string` duplication
- In `timer.get_number_lines`, replace the inline format-branch block (timer.py:310-328) with a call to a single private `_format_time_string(seconds, ...)` that lives in `timer.py` (port the logic from `display._format_time_string`).
- Keep `display._format_time_string` as a **thin re-export** of the `timer` helper (it is imported directly by `test_countdown_display.py` and `test_countup_display.py`; removing the name outright would break the suite). Over time, retarget those tests at `timer`, then drop the re-export.
- Point `display.get_chars_for_terminal` at the canonical `timer` helper.
- Remove the `__main__.get_number_lines` shim (F2): update the two call sites in `__main__.py` to call `timer.get_number_lines(...)` directly with the chars from `display.get_chars_for_terminal` (and undo the level of indirection tests relied on, if any).
- Run the glyph-width + countdown/countup display tests (they exercise `get_number_lines` directly) to confirm identical output.
- **Exit criteria:** one copy of the time-format branch logic (plus a compat re-export in `display.py`); `ruff` / `pytest` green.

### Phase 3 — Unify centering logic (F5)
- Keep `centered_frame` (used by pulses) and `print_full_screen` (used by the run loop) as the two entry points, but extract the shared vertical/horizontal padding math into a single `centering_padding(content_width, content_height, term_width, term_height)` helper in `display.py`.
- Have both consumers use it so the two no longer drift. Preserve the `size == 3` and pause-text rules faithfully so rendered placement is identical.
- Add a short unit test asserting `centered_frame` and `print_full_screen` agree on padding for identical inputs (capture printed output via capsys).
- **Exit criteria:** identical rendered placement; suite green.

### Phase 4 — Extract the run loop into `timer.py` (biggest win for F1/F9)
Introduce a `Clock` protocol and move `run_countdown`'s timing/pulse logic out of `__main__`:
- Define `Clock` in a small `clock.py` (or in `timer.py`): `time() -> float`, `sleep(sec) -> None`.
- Add `countdown.run(total_seconds, pulse_fn, *, clock, show_hours, count_up, raw_seconds, dur_str, max_pulses)` that contains the loop currently in `__main__.run_countdown`.
- `__main__.run_countdown` becomes a thin adapter that constructs a real `Clock` (using `time`/`sleep` from stdlib) and delegates.
- Move the summary panel construction into `timer.py` (F4 presentation) as a `build_summary_panel(...) -> Panel` so the loop stays pure; `__main__` just prints it.
- **CRITICAL — keep behaviour identical.** Every test still passes because `__main__.run_countdown` keeps its name and signature; tests that patch `countdown.__main__.{time,sleep,...}` still work (the adapter still calls those names) — but prefer to also add `clock`-driven unit tests that patch `countdown.timer.Clock` instead.
- Extension point: pass the `Clock` into `check_for_keypress/read_key` via the callers, or keep the existing patch surface. Keep change minimal.
- **Exit criteria:** `__main__.py` no longer contains the loop body; suite green.

### Phase 5 — Extract schedule CLI presentation (F4)
Move `_schedule_table`, `render_schedule_list`, `render_schedule_live`, `add_schedule`, `check_schedule`, and `load_store` from `__main__.py` into a new module `src/countdown/schedules_cli.py` (or a `cli/` package).
- `__main__` imports them; the `schedule` Click group's command bodies become thin calls.
- `load_store` stays small (Validation → UsageError) and lives with the view helpers.
- Keep error surfacing as `click.UsageError`; keep Rich styling and all output strings byte-for-byte identical (schedule tests assert on substrings and paths).
- **Exit criteria:** `__main__.py` shrinks further; schedule + cli features green.

### Phase 6 — Registry-driven pulse dispatch (F8)
Refactor `get_pulse_fn` in `pulses/__init__.py` to iterate a dict of mode → lazy importer callable (still imports only on demand), preserving the same `ValueError` message.
- Keep `VALID_ANIM_MODES` and `validate_anim_mode` as-is.
- Selection/validation behavior unchanged.
- **Exit criteria:** pulse/config tests green; lazy import preserved.

### Phase 7 — Prune dead/experimental surface (F6)
- Remove the marked "legacy" Rich-object API in `pulses/rich.py` (`_style_row`, `_h_pad`, `build_wave_renderable`) **only if** the corresponding tests (`test_rich_pulse.py` / `rich_pulse.feature`) are first migrated or conditionally kept. If removal would drop coverage below `fail_under=60`, move these behind a `# pragma: no cover` or keep them. **Defer this phase until coverage is re-verified.**
- Blacklist/consolidate `tests_cmd.py` + `_map_viz.py` only if desired; otherwise leave (they are functional diagnostics).
- Confirm the coverage omit list in `pyproject.toml` still matches reality (e.g. `redirect_patch.py` referenced nowhere — verify it doesn't exist / is omitted correctly).
- **Exit criteria:** no dead symbols referenced by live code; coverage ≥ 60%.

### Phase 8 — Final harden & polish
- Re-run `uv run ruff check .` and `uv run ruff format --check .`.
- Run `uv run pytest` and full coverage; confirm `fail_under=60` passes.
- Run `just check` (format, lint, test) end-to-end.
- Print the cute BANZAI! message (kaomojis avoiding `\(` / `\$`) once all tests pass.
- Update `README.md` only if CLI surface changed (it should not).
- **Exit criteria:** `just check` green, coverage ≥ 60%, 176+ tests green.

---

## Part 3 — Explicit Non-Goals / Deferred
- No new CLI features, flags, or subcommands.
- No change to `config.yaml` schema or `anim` validation semantics.
- No behavior/summary-string changes (tests pin them).
- asciimatics/drawille/ghostprint pulse internals left as-is unless dead code removal (Phase 7) requires touching them.
- Timer tests will NEVER use real timers > 3s; all loop tests stay on FakeClock.

## Part 4 — Risk Register
| Risk | Mitigation |
|------|-----------|
| Behavior drift during loop extraction (Phase 4) | Keep `__main__.run_countdown` signature; snapshot summaries; rely on 176-test suite + schedule/cli features that assert exact strings. |
| Coverage drops below 60% after dead-code removal (Phase 7) | Re-check coverage before finalizing; keep legacy API or add `pragma: no cover` as needed. |
| `display._format_time_string` is imported by tests (Phase 2) | Keep a compat re-export in `display.py` so tests keep green; retarget tests at `timer` before removing. |
| Test suite couples to `__main__` internals (F7) | Phases 2/4 introduce a `Clock` and move logic; add `clock`-driven tests incrementally so old patches can be retired gradually, not all at once. |
| Glyph-width regression | Phase 2 explicitly runs glyph-width/countdown/countup display tests; glyph width features cover every digit size. |
