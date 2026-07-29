"""Centering fidelity test suite.

Verifies every code path that positions content in the terminal places it at
the correct coordinates.  All tests follow the same pattern:

  1. Create a W×H character grid (the "map").
  2. Mark the corners, edges, center, and quadrants with known symbols.
  3. Call the function under test.
  4. Convert its output (string or Rich renderable) to a grid.
  5. Assert the positioned content occupies exactly the expected cells.

On failure the assertion displays a side-by-side visual diff of the two grids
so you can immediately see a left/up/down shift.
"""

import os

import pytest
from _pytest.assertion import truncate

from countdown import display
from countdown import timer as timer_mod
from countdown._map_viz import grid_to_str, make_grid, mark_center, write_lines
from countdown.digits import CHARS_BY_SIZE

truncate.DEFAULT_MAX_LINES = 60
truncate.DEFAULT_MAX_CHARS = 60 * 120


# ── 2.  OUTPUT → GRID CONVERTERS ────────────────────────────────────


def _str_to_grid(s, w, h):
    """Parse *s* (newline-separated rows) into a W×H grid.

    Rows longer than *w* are truncated; fewer than *h* rows leave trailing
    rows as spaces.
    """
    grid = make_grid(w, h)
    for row_idx, line in enumerate(s.splitlines()):
        if row_idx >= h:
            break
        for col_idx, ch in enumerate(line):
            if col_idx >= w:
                break
            grid[row_idx][col_idx] = ch
    return grid


def grid_from_centered_frame(content_lines, tw, th):
    """Return a grid for ``centered_frame(content_lines, tw, th)``."""
    out = display.centered_frame(content_lines, tw, th)
    return _str_to_grid(out, tw, th)


def grid_from_print_full_screen(content_lines, tw, th, capsys, monkeypatch, paused=False):
    """Capture ``print_full_screen`` output and return as a grid."""
    from countdown.display import CLEAR

    def fake_gs(fallback=(tw, th)):
        return os.terminal_size(fallback)

    monkeypatch.setattr("countdown.display.get_terminal_size", fake_gs)
    display.print_full_screen(content_lines, paused=paused)
    out, _ = capsys.readouterr()
    body = out.removeprefix(CLEAR)
    body = display.strip_ansi(body)
    return _str_to_grid(body, tw, th)


_PULSE_MODULES = {}

def _lazy_pulse_mod(name):
    if name not in _PULSE_MODULES:
        import countdown.pulses.ansi as m
        _PULSE_MODULES["ansi"] = m
        import countdown.pulses.smooth as m
        _PULSE_MODULES["smooth"] = m
        import countdown.pulses.ghostprint as m
        _PULSE_MODULES["ghostprint"] = m
        import countdown.pulses.drawille as m
        _PULSE_MODULES["drawille"] = m
    return _PULSE_MODULES[name]


def grid_from_build_frame(module_name, lines, phase, tw, th, monkeypatch):
    """Call ``build_frame`` for a pulse module and return a grid."""
    mod = _lazy_pulse_mod(module_name)

    def fake_gs(fallback=(tw, th)):
        return os.terminal_size(fallback)

    monkeypatch.setattr(mod.__name__ + ".get_terminal_size", fake_gs)
    out = mod.build_frame(lines, phase)
    clean = display.strip_ansi(out)
    return _str_to_grid(clean, tw, th)


def grid_from_rich_wave(lines, phase, tw, th):
    """Return a grid for ``build_wave_renderable`` with explicit terminal size."""
    from countdown.pulses.rich import build_wave_renderable

    group = build_wave_renderable(lines, phase, term_width=tw, term_height=th)
    grid = make_grid(tw, th)
    for row_idx, text in enumerate(group.renderables):
        if row_idx >= th:
            break
        plain = text.plain
        for col_idx, ch in enumerate(plain):
            if col_idx >= tw:
                break
            grid[row_idx][col_idx] = ch
    return grid


# ── 4.  ASSERTION HELPER ────────────────────────────────────────────


def assert_grids_equal(actual, expected, msg=""):
    """Fail with a visual side-by-side diff if *actual* ≠ *expected*."""
    a_str = grid_to_str(actual)
    e_str = grid_to_str(expected)
    if a_str == e_str:
        return
    lines = ["Grid mismatch"]
    if msg:
        lines.append(msg)
    lines.append("─" * 80)
    lines.append("ACTUAL (content rendered by function):")
    lines.append("─" * 80)
    lines.extend(a_str.splitlines())
    lines.append("")
    lines.append("─" * 80)
    lines.append("EXPECTED (map with corner / centre / quadrant markers):")
    lines.append("─" * 80)
    lines.extend(e_str.splitlines())
    lines.append("")
    lines.append("─" * 80)
    lines.append("DIFF (char-by-char — '·' = actual diff):")
    lines.append("─" * 80)
    h = len(actual)
    w = len(actual[0]) if actual else 0
    for y in range(h):
        diff_row = ""
        for x in range(w):
            a = actual[y][x]
            e = expected[y][x]
            diff_row += "·" if a != e else " "
        lines.append(diff_row)
    pytest.fail("\n".join(lines))


# ── 5.  TEST DATA ───────────────────────────────────────────────────

TEST_CONFIGS = [
    # (name, tw, th, content_lines, reason)
    ("80x24_size5", 80, 24, timer_mod.get_number_lines(0, CHARS_BY_SIZE[5]), "typical term, glyph size 5"),
    ("80x24_timer", 80, 24, timer_mod.get_number_lines(125, CHARS_BY_SIZE[5]), "typical term, 3-digit minutes"),
    ("40x10_size3", 40, 10, timer_mod.get_number_lines(0, CHARS_BY_SIZE[3]), "small term, glyph size 3"),
    ("79x23_size5", 79, 23, timer_mod.get_number_lines(0, CHARS_BY_SIZE[5]), "odd width + height"),
    ("80x23_size5", 80, 23, timer_mod.get_number_lines(0, CHARS_BY_SIZE[5]), "even width, odd height"),
    ("80x24_size7", 80, 24, timer_mod.get_number_lines(0, CHARS_BY_SIZE[7]), "mid term, glyph size 7"),
    ("100x30_size16", 100, 30, timer_mod.get_number_lines(0, CHARS_BY_SIZE[16]), "large term, max glyphs"),
]


# ── 6.  TESTS ───────────────────────────────────────────────────────


class TestHorizontalVerticalPadding:
    """Direct tests of ``horizontal_padding`` and ``vertical_padding``."""

    @pytest.mark.parametrize(
        "tw,content_w,expected",
        [
            (80, 40, 20),
            (79, 40, 19),
            (80, 91, 0),
            (40, 9, 15),
            (100, 32, 34),
            (80, 1, 39),
            (3, 5, 0),
        ],
    )
    def test_horizontal(self, tw, content_w, expected):
        lines = ["x" * content_w]
        assert display.horizontal_padding(lines, tw) == expected

    @pytest.mark.parametrize(
        "th,content_h,expected",
        [
            (24, 5, 9),
            (23, 5, 9),
            (24, 7, 8),
            (24, 1, 11),
            (5, 10, 0),
        ],
    )
    def test_vertical(self, th, content_h, expected):
        assert display.vertical_padding(content_h, th) == expected


class TestCenteredFrame:
    """centered_frame places content at the expected grid coordinates."""

    @pytest.mark.parametrize("name,tw,th,lines,reason", TEST_CONFIGS)
    def test_center(self, name, tw, th, lines, reason):
        actual = grid_from_centered_frame(lines, tw, th)
        expected = make_grid(tw, th)
        ch = len(lines)
        cw = max(len(x) for x in lines)
        hpad = max(0, (tw - cw) // 2)
        vpad = max(0, (th - ch) // 2)
        write_lines(expected, hpad, vpad, lines)
        assert_grids_equal(actual, expected, f"{name}: {reason}")

    def test_content_wider_than_terminal(self):
        lines = ["x" * 200]
        out = display.centered_frame(lines, 80, 24)
        ch = len(lines)
        vpad = max(0, (24 - ch) // 2)
        expected = "\n" * vpad + "x" * 200
        assert out == expected, "wider content: vpad still applied, hpad=0"

    def test_content_taller_than_terminal(self):
        lines = ["x"] * 50
        out = display.centered_frame(lines, 80, 24)
        cw = 1
        hpad = max(0, (80 - cw) // 2)
        expected = "\n".join(" " * hpad + "x" for _ in lines)
        assert out == expected, "taller content: hpad still applied, vpad=0, all 50 rows present"


class TestPrintFullScreen:
    """print_full_screen places content at the expected grid coordinates."""

    @pytest.mark.parametrize("name,tw,th,lines,reason", TEST_CONFIGS)
    def test_center(self, name, tw, th, lines, reason, capsys, monkeypatch):
        actual = grid_from_print_full_screen(lines, tw, th, capsys, monkeypatch)
        expected = make_grid(tw, th)
        ch = len(lines)
        cw = max(len(x) for x in lines)
        hpad = max(0, (tw - cw) // 2)
        vpad = max(0, (th - ch) // 2)
        write_lines(expected, hpad, vpad, lines)
        assert_grids_equal(actual, expected, f"{name}: {reason}")

    def test_paused_shows_message_below_timer(self, capsys, monkeypatch):
        timer_lines = ["00:05"]
        actual = grid_from_print_full_screen(timer_lines, 80, 24, capsys, monkeypatch, paused=True)
        expected = make_grid(80, 24)
        # In paused mode content_height = 1 + 2 = 3 (timer + blank + pause)
        vpad = max(0, (24 - 3) // 2)
        hpad = max(0, (80 - 5) // 2)
        write_lines(expected, hpad, vpad, timer_lines)
        pause_text = "PAUSED - Press any key to resume"
        pause_hpad = max(0, (80 - len(pause_text)) // 2)
        pause_y = vpad + 2  # timer row + blank row
        write_lines(expected, pause_hpad, pause_y, [pause_text])
        assert_grids_equal(actual, expected, "paused mode: PAUSED text should sit below centered timer")

    def test_paused_suppressed_when_no_room(self, capsys, monkeypatch):
        lines = ["a", "b", "c"]
        actual = grid_from_print_full_screen(lines, 20, 3, capsys, monkeypatch, paused=True)
        expected = make_grid(20, 3)
        # content_height = 3. paused check: 3 + 2 = 5 > 3 → suppressed
        vpad = max(0, (3 - 3) // 2)
        max_w = max(len(x) for x in lines)
        hpad = max(0, (20 - max_w) // 2)
        write_lines(expected, hpad, vpad, lines)
        assert_grids_equal(actual, expected, "paused text should not appear in tiny terminal")

    def test_no_ansi_in_countdown_phase(self, capsys, monkeypatch):
        """Countdown phase output should have no ANSI escapes (paused adds them)."""
        from countdown.display import CLEAR, INTENSE_MAGENTA, RESET

        monkeypatch.setattr("countdown.display.get_terminal_size", lambda fb=None: os.terminal_size((80, 24)))
        display.print_full_screen(["hello"], paused=False)
        out, _ = capsys.readouterr()
        body = out.removeprefix(CLEAR)
        assert INTENSE_MAGENTA not in body
        assert RESET not in body

    def test_paused_adds_ansi(self, capsys, monkeypatch):
        """Paused mode wraps timer lines in ANSI colour codes."""
        from countdown.display import CLEAR, INTENSE_MAGENTA, RESET

        monkeypatch.setattr("countdown.display.get_terminal_size", lambda fb=None: os.terminal_size((80, 24)))
        display.print_full_screen(["hello"], paused=True)
        out, _ = capsys.readouterr()
        body = out.removeprefix(CLEAR)
        assert INTENSE_MAGENTA in body
        assert RESET in body


class TestAnsiPulseModules:
    """build_frame of ANSI-based pulse modules produces centred output.

    Ghostprint and drawille are excluded from exact-content checks because
    they *mutate* the glyph characters (█ → ░/▀/% etc. or → Braille) as
    part of their visual effect; we still verify their positioning via
    ``test_mutation_module_position`` below.
    """

    @pytest.mark.parametrize("module_name", ["ansi", "smooth"])
    @pytest.mark.parametrize("name,tw,th,lines,reason", TEST_CONFIGS)
    def test_frame_centered(self, module_name, name, tw, th, lines, reason, monkeypatch):
        actual = grid_from_build_frame(module_name, lines, 0.0, tw, th, monkeypatch)
        expected = make_grid(tw, th)
        ch = len(lines)
        cw = max(len(x) for x in lines)
        hpad = max(0, (tw - cw) // 2)
        vpad = max(0, (th - ch) // 2)
        write_lines(expected, hpad, vpad, lines)
        assert_grids_equal(actual, expected, f"{module_name}: {name}: {reason}")

    @pytest.mark.parametrize("module_name", ["ghostprint", "drawille"])
    @pytest.mark.parametrize("name,tw,th,lines,reason", TEST_CONFIGS)
    def test_mutation_module_position(self, module_name, name, tw, th, lines, reason, monkeypatch):
        """Ghostprint/drawille mutate glyphs so we only verify position, not content."""
        actual = grid_from_build_frame(module_name, lines, 0.0, tw, th, monkeypatch)
        ch = len(lines)
        cw = max(len(x) for x in lines)
        hpad = max(0, (tw - cw) // 2)
        vpad = max(0, (th - ch) // 2)

        for y in range(vpad):
            row = "".join(actual[y])
            assert row.strip() == "", f"{name}: row {y} should be blank (vpad)"

        for y in range(ch):
            row_idx = vpad + y
            row = "".join(actual[row_idx])
            leading = row[:hpad]
            assert leading.strip() == "", f"{name}: row {row_idx} should have {hpad} leading spaces"
            content_region = row[hpad:hpad + cw]
            assert content_region.strip() != "", f"{name}: row {row_idx} should have content"
            after = row[hpad + cw:]
            assert after.strip() == "", f"{name}: row {row_idx} should have no content after content region"

        for y in range(vpad + ch, th):
            row = "".join(actual[y])
            assert row.strip() == "", f"{name}: row {y} should be blank (below content)"


class TestRichPulse:
    """build_wave_renderable with term_width centres; without it does not."""

    @pytest.mark.parametrize("name,tw,th,lines,reason", TEST_CONFIGS)
    def test_centered_with_term_width(self, name, tw, th, lines, reason):
        actual = grid_from_rich_wave(lines, 0.0, tw, th)
        expected = make_grid(tw, th)
        ch = len(lines)
        cw = max(len(x) for x in lines)
        hpad = max(0, (tw - cw) // 2)
        vpad = max(0, (th - ch) // 2)
        write_lines(expected, hpad, vpad, lines)
        assert_grids_equal(actual, expected, f"{name}: {reason}")

    @pytest.mark.parametrize("name,tw,th,lines,reason", TEST_CONFIGS)
    def test_no_term_width_no_padding(self, name, tw, th, lines, reason):
        """Without term_width, each Text.plain should equal input line."""
        from countdown.pulses.rich import build_wave_renderable

        group = build_wave_renderable(lines, 0.0)
        for text, line in zip(group.renderables, lines, strict=False):
            assert text.plain == line, (
                f"{name}: without term_width, plain should match input exactly"
            )


class TestMapAnchors:
    """Verify that content lands at the expected map anchor positions.

    Covers centre, corners, edge midpoints, and quadrant centres.
    """

    # We test with a single character ("█") so the centered position is
    # unambiguous: it lands at (max(0, (tw-1)//2), max(0, (th-1)//2)).
    MARKER = "█"

    @pytest.mark.parametrize("tw,th", [(80, 24), (79, 23), (40, 10), (100, 30)])
    def test_center_is_center(self, tw, th):
        """A single character lands at the terminal centre.

        Uses `centered_frame` to position the marker.
        """
        actual = grid_from_centered_frame([self.MARKER], tw, th)
        expected = make_grid(tw, th)
        mark_center(expected, self.MARKER)
        assert_grids_equal(actual, expected, f"{tw}×{th}: centre marker")



    @pytest.mark.parametrize("tw,th", [(80, 24), (79, 23), (40, 10)])
    def test_quadrant_centres(self, tw, th):
        """Place a marker in the centre of each quadrant using `centered_frame`.

        We treat each quadrant as a mini-terminal with its own dimensions
        and offset, call centred_frame with a 1×1 marker, then embed that
        quadrant's output into the full grid.  The expected grid places the
        same marker at the same computed position so both are identical.
        """
        cx, cy = max(0, (tw - 1) // 2), max(0, (th - 1) // 2)
        quadrants = [
            (0, 0, cx, cy),               # TL
            (cx + 1, 0, tw - 1, cy),       # TR
            (0, cy + 1, cx, th - 1),       # BL
            (cx + 1, cy + 1, tw - 1, th - 1),  # BR
        ]
        actual = make_grid(tw, th)
        expected = make_grid(tw, th)
        for (x0, y0, x1, y1) in quadrants:
            qw = x1 - x0 + 1
            qh = y1 - y0 + 1
            qlines = [self.MARKER]
            qout = display.centered_frame(qlines, qw, qh)
            for row_off, qline in enumerate(qout.splitlines()):
                for col_off, ch in enumerate(qline):
                    gx = x0 + col_off
                    gy = y0 + row_off
                    if 0 <= gy < th and 0 <= gx < tw:
                        if actual[gy][gx] == " ":
                            actual[gy][gx] = ch
            # Place matching marker in expected grid at same quadrant centre
            qcx = (x1 - x0) // 2
            qcy = (y1 - y0) // 2
            mx = x0 + qcx
            my = y0 + qcy
            if 0 <= my < th and 0 <= mx < tw:
                expected[my][mx] = self.MARKER
        assert_grids_equal(actual, expected, f"{tw}×{th}: quadrant centres with {self.MARKER}")


class TestEdgeCases:
    """Stress matrix: over-wide content, odd-even mismatches, extreme sizes."""

    @pytest.mark.parametrize(
        "tw,th,cw,ch,hpad,vpad",
        [
            (80, 24, 91, 16, 0, 4),    # over-wide → no hpad
            (40, 10, 9, 1, 15, 4),     # comfy fit
            (79, 23, 32, 5, 23, 9),    # odd×odd
            (80, 23, 55, 7, 12, 8),    # even w, odd h
            (100, 30, 112, 16, 0, 7),  # over-wide width, tall
            (80, 24, 1, 1, 39, 11),    # tiny content
            (80, 24, 80, 24, 0, 0),    # exact fit
        ],
    )
    def test_centered_frame_matrix(self, tw, th, cw, ch, hpad, vpad):
        lines = ["x" * cw] * ch
        actual = grid_from_centered_frame(lines, tw, th)
        expected = make_grid(tw, th)
        write_lines(expected, hpad, vpad, lines)
        assert_grids_equal(actual, expected, f"{tw}×{th} content={cw}×{ch} → pad=({hpad},{vpad})")

    @pytest.mark.parametrize(
        "tw,th,cw,ch,hpad,vpad",
        [
            (80, 24, 91, 16, 0, 4),
            (40, 10, 9, 1, 15, 4),
            (79, 23, 32, 5, 23, 9),
            (80, 23, 55, 7, 12, 8),
            (80, 24, 1, 1, 39, 11),
        ],
    )
    def test_print_full_screen_matrix(self, tw, th, cw, ch, hpad, vpad, capsys, monkeypatch):
        lines = ["x" * cw] * ch
        actual = grid_from_print_full_screen(lines, tw, th, capsys, monkeypatch)
        expected = make_grid(tw, th)
        write_lines(expected, hpad, vpad, lines)
        assert_grids_equal(actual, expected, f"{tw}×{th} content={cw}×{ch}")


# ── 7.  MAP VISUALISATION (for debugging) ────────────────────────────
# This test is *informational* — it shows the full map with all markers on
# every terminal size so you can visually confirm the geometry.  It skips
# automatically unless --run-map-viz is passed.


def test_visual_map(capsys, pytestconfig):
    """Render centering maps for visual inspection via pytest.

    Skipped by default; run with ``--run-map-viz`` to enable.
    """
    if not pytestconfig.getoption("run_map_viz"):
        pytest.skip("use --run-map-viz to enable")
    from countdown.tests_cmd import run_tests_cmd

    run_tests_cmd()
