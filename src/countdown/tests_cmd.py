"""``timer test`` CLI command — print centering geometry map."""

from rich.console import Console
from rich.text import Text

from countdown._map_viz import (
    grid_to_str,
    make_grid,
    mark_center,
    mark_corners,
    mark_edge_midpoints,
    mark_quadrant_boundaries,
    mark_quadrants,
)
from countdown.display import get_terminal_size


def run_tests_cmd() -> None:
    """Build and print a centering geometry map for the current terminal.

    The map is printed as a raw grid whose width matches the terminal
    exactly, so every cell position is true to the coordinates.
    """
    ts = get_terminal_size()
    tw, th = ts.columns, ts.lines
    grid = make_grid(tw, th)
    mark_corners(grid, "+")
    mark_center(grid, "+")
    mark_edge_midpoints(grid, "+")
    mark_quadrant_boundaries(grid, "|", "-", "+")
    mark_quadrants(grid)

    title = f" Centering Map {tw}x{th} "
    left = "-" * ((tw - len(title)) // 2)
    right = "-" * (tw - len(title) - len(left))

    console = Console()
    console.out(left + title + right)
    console.out(Text(grid_to_str(grid)))


__all__ = ["run_tests_cmd"]
