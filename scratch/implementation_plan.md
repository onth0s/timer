# Implementation Plan — Count-up Elapsed Time Fix & Glyph Width Uniformity

## Problem Statement

1. **Count-up Summary Showing `0s`:**
   In [__main__.py](file:///c:/Users/Leonardo/001/00__DEV/Timer/src/countdown/__main__.py#L92), `final_seconds = n` was only assigned when quitting via `q` or `Esc`. Quitting via `Ctrl+C` or exiting via `SystemExit` bypassed this assignment, leaving `final_seconds = 0`.

2. **Glyph & Terminal Shift Inconsistency (Width Variations):**
   - In `get_number_lines`, trailing spaces were stripped with `[line.rstrip() for line in lines]`. When numbers with varying right-side character widths (such as digit `1` vs `8` or `0`) changed during countdown/count-up ticks, the overall width of the ASCII art string varied, causing horizontal terminal layout shifts.
   - For constant width alignment without layout shifting, all assembled lines for a given time format (`SS`, `MM:SS`, or `HH:MM:SS`) within a specific digit font size must maintain an exact, constant total line width.

---

## Proposed Changes

### Component 1: Count-up Exit Summary Tracking

#### [MODIFY] [__main__.py](file:///c:/Users/Leonardo/001/00__DEV/Timer/src/countdown/__main__.py)
- Continuously update `final_seconds = n` inside the count-up loop during each tick.
- Ensure that regardless of whether the user exits via `q`, `Esc`, or `Ctrl+C` (`KeyboardInterrupt`), `final_seconds` accurately reflects the exact elapsed seconds.

---

### Component 2: Uniform Glyph Width Padding (Zero Layout Shift)

#### [MODIFY] [timer.py](file:///c:/Users/Leonardo/001/00__DEV/Timer/src/countdown/timer.py#L178)
- Modify `get_number_lines` to preserve uniform padding across all digits in a size set:
  - Do not call `rstrip()` on individual lines if it causes line-to-line width variance.
  - Calculate the maximum full line width for the current time string structure in the active font size set, and right-pad/center lines evenly so that changing numbers (`1` -> `0` -> `8`) produces zero horizontal layout shift on the terminal screen.

---

### Component 3: Test Suite & Layout Fidelity Tests

#### [NEW] [test_glyph_width.py](file:///c:/Users/Leonardo/001/00__DEV/Timer/tests/test_glyph_width.py)
- Write unit tests verifying that for every digit size (all sizes in `DIGIT_SIZES`):
  - Rendering any digit combination (`00` through `99`, `00:00` through `59:59`, `00:00:00` through `23:59:59`) yields **100% constant line width** for all rendered lines.
  - Test count-up summary output accuracy when interrupted via `KeyboardInterrupt`.

---

## Verification Plan

### Automated Tests
1. Run `python -m pytest tests/test_glyph_width.py` to verify constant width across all digits and time formats.
2. Run full pytest suite (`python -m pytest`) to ensure all tests pass cleanly.

### Linting
1. Run `ruff check .` to verify zero linting errors.
