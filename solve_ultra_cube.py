#!/usr/bin/env python3
"""Solve the Ultra Cube variant.

Ultra Cube inventory:

    Z R L L L L L L L L L L L

That is one Z brick, one R brick, and eleven L bricks.
"""

from __future__ import annotations

import argparse

from solve_evil_cube import SHAPES, ULTRA_INVENTORY, render_solution, solve


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-solutions", type=int, default=1)
    args = parser.parse_args()

    solutions = solve(SHAPES, inventory=ULTRA_INVENTORY, max_solutions=args.max_solutions)
    if not solutions:
        raise SystemExit("no Ultra Cube solution found")

    print(render_solution(solutions[0]))


if __name__ == "__main__":
    main()
