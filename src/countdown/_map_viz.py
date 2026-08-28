"""Grid helpers and map markers for centering visualisation.

Used by both the ``tests`` CLI command and the centering fidelity test suite.
"""


def make_grid(w, h):
    """Return an empty W×H grid filled with spaces."""
    return [[" " for _ in range(w)] for _ in range(h)]


def grid_to_str(grid):
    r"""Dump a grid to a single string (rows joined by ``\\n``)."""
    return "\n".join("".join(row) for row in grid)


def write_lines(grid, x, y, lines):
    """Blit *lines* (list of str) onto *grid* at top-left (x, y)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    for row_off, line in enumerate(lines):
        for col_off, ch in enumerate(line):
            gy = y + row_off
            gx = x + col_off
            if 0 <= gy < h and 0 <= gx < w:
                grid[gy][gx] = ch


def mark_center(grid, ch="+"):
    """Place *ch* at the centre of the terminal (defined by grid dimensions)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    cx, cy = max(0, (w - 1) // 2), max(0, (h - 1) // 2)
    grid[cy][cx] = ch
    return (cx, cy)


def mark_corners(grid, ch="+"):
    """Place *ch* at the four corners."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    positions = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for x, y in positions:
        if 0 <= y < h and 0 <= x < w:
            grid[y][x] = ch


def mark_edge_midpoints(grid, ch="+"):
    """Place *ch* at the midpoint of each edge."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    positions = [
        (w // 2, 0),
        (w // 2, h - 1),
        (0, h // 2),
        (w - 1, h // 2),
    ]
    for x, y in positions:
        if 0 <= y < h and 0 <= x < w:
            grid[y][x] = ch


def mark_quadrant_boundaries(grid, ch_v="│", ch_h="─", ch_cross="┼"):
    """Draw quadrant-dividing lines at the centre axes."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    cx, cy = max(0, (w - 1) // 2), max(0, (h - 1) // 2)
    for y in range(h):
        if 0 <= cx < w:
            grid[y][cx] = ch_v
    for x in range(w):
        if 0 <= cy < h:
            grid[cy][x] = ch_h
    grid[cy][cx] = ch_cross


def mark_quadrants(grid, size=1):
    """Place digits 1-4 at the centre of each quadrant."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    cx, cy = max(0, (w - 1) // 2), max(0, (h - 1) // 2)
    quadrants = [
        (0, 0, cx, cy),
        (cx + 1, 0, w - 1, cy),
        (0, cy + 1, cx, h - 1),
        (cx + 1, cy + 1, w - 1, h - 1),
    ]
    marks = "1234"
    for (x0, y0, x1, y1), m in zip(quadrants, marks, strict=False):
        qcx = max(0, (x1 - x0) // 2)
        qcy = max(0, (y1 - y0) // 2)
        mx = x0 + qcx
        my = y0 + qcy
        if 0 <= my < h and 0 <= mx < w:
            grid[my][mx] = m


def mark_quadrant_corners(grid):
    """Place ``o`` at each quadrant's inner corners."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    cx, cy = max(0, (w - 1) // 2), max(0, (h - 1) // 2)
    corners = [
        (0, 0),
        (cx, 0),
        (0, cy),
        (cx, cy),
        (cx + 1, 0),
        (w - 1, 0),
        (cx + 1, cy),
        (w - 1, cy),
        (0, cy + 1),
        (cx, cy + 1),
        (0, h - 1),
        (cx, h - 1),
        (cx + 1, cy + 1),
        (w - 1, cy + 1),
        (cx + 1, h - 1),
        (w - 1, h - 1),
    ]
    for x, y in corners:
        if 0 <= y < h and 0 <= x < w:
            grid[y][x] = "o"
