#!/usr/bin/env python3
"""Count solutions for the regular Printables Evil Cube.

Counts exact 4x4x4 packings of the regular inventory:

    Z S S S S R L A A B B B

Identical bricks are treated as indistinguishable.  The script reports:

* raw fixed-cube solutions, where rotating the entire solved cube counts again
* unique solutions up to the 24 rotations of the cube
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import itertools
from dataclasses import dataclass
from functools import lru_cache
from time import monotonic

from solve_evil_cube import EVIL_INVENTORY, PUZZLE_INVENTORIES, SHAPES, Coord, orientations


SIZE = 4
CELL_COUNT = SIZE**3
ALL_MASK = (1 << CELL_COUNT) - 1
NEIGHBOR_MASKS: tuple[int, ...] = ()


@dataclass(frozen=True)
class Placement:
    shape: str
    mask: int
    cells: tuple[Coord, ...]


def progress_print(message: str, progress_file: str | None = None) -> None:
    try:
        print(message, flush=True)
    except OSError:
        pass
    if progress_file:
        try:
            with open(progress_file, "a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except OSError:
            pass


def cell_index(cell: Coord) -> int:
    x, y, z = cell
    return x + SIZE * y + SIZE * SIZE * z


def index_cell(index: int) -> Coord:
    z, rem = divmod(index, SIZE * SIZE)
    y, x = divmod(rem, SIZE)
    return (x, y, z)


def build_neighbor_masks() -> tuple[int, ...]:
    masks: list[int] = []
    for index in range(CELL_COUNT):
        x, y, z = index_cell(index)
        mask = 0
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nx, ny, nz = x + dx, y + dy, z + dz
            if 0 <= nx < SIZE and 0 <= ny < SIZE and 0 <= nz < SIZE:
                mask |= 1 << cell_index((nx, ny, nz))
        masks.append(mask)
    return tuple(masks)


NEIGHBOR_MASKS = build_neighbor_masks()


def cell_mask(cells: tuple[Coord, ...]) -> int:
    mask = 0
    for cell in cells:
        mask |= 1 << cell_index(cell)
    return mask


def add(a: Coord, b: Coord) -> Coord:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def generate_placements(inventory: str = EVIL_INVENTORY) -> tuple[list[Placement], dict[int, list[int]]]:
    placements: list[Placement] = []
    by_cell: dict[int, list[int]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    for shape in sorted(set(inventory)):
        cells = SHAPES[shape]
        for oriented in orientations(cells):
            max_x = max(x for x, _, _ in oriented)
            max_y = max(y for _, y, _ in oriented)
            max_z = max(z for _, _, z in oriented)
            for ox in range(SIZE - max_x):
                for oy in range(SIZE - max_y):
                    for oz in range(SIZE - max_z):
                        moved = tuple(sorted(add(cell, (ox, oy, oz)) for cell in oriented))
                        mask = cell_mask(moved)
                        key = (shape, mask)
                        if key in seen:
                            continue
                        seen.add(key)
                        index = len(placements)
                        placements.append(Placement(shape=shape, mask=mask, cells=moved))
                        for cell in moved:
                            by_cell[cell_index(cell)].append(index)
    return placements, by_cell


def cube_rotations() -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    rotations: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = []
    for perm in itertools.permutations((0, 1, 2)):
        inversions = sum(perm[i] > perm[j] for i in range(3) for j in range(i + 1, 3))
        parity = -1 if inversions % 2 else 1
        for signs in itertools.product((-1, 1), repeat=3):
            if signs[0] * signs[1] * signs[2] * parity == 1:
                rotations.append((perm, signs))
    return rotations


def rotate_cell(cell: Coord, rotation: tuple[tuple[int, int, int], tuple[int, int, int]]) -> Coord:
    perm, signs = rotation
    centered = (2 * cell[0] - (SIZE - 1), 2 * cell[1] - (SIZE - 1), 2 * cell[2] - (SIZE - 1))
    values = [centered[0], centered[1], centered[2]]
    rotated = [signs[i] * values[perm[i]] for i in range(3)]
    return tuple((value + (SIZE - 1)) // 2 for value in rotated)  # type: ignore[return-value]


ROTATIONS = cube_rotations()


def canonical_solution(solution: list[Placement]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    variants = []
    for rotation in ROTATIONS:
        rotated_pieces = []
        for placement in solution:
            cells = tuple(sorted(cell_index(rotate_cell(cell, rotation)) for cell in placement.cells))
            rotated_pieces.append((placement.shape, cells))
        variants.append(tuple(sorted(rotated_pieces)))
    return min(variants)


def count_raw_solutions(
    inventory: str = EVIL_INVENTORY,
    progress_every: int = 0,
    heartbeat_seconds: float = 30.0,
    progress_file: str | None = None,
) -> int:
    placements, by_cell = generate_placements(inventory)
    shape_order = tuple(sorted(Counter(inventory)))
    initial_counts = tuple(Counter(inventory)[shape] for shape in shape_order)
    shape_index = {shape: index for index, shape in enumerate(shape_order)}
    shape_volumes = tuple(len(SHAPES[shape]) for shape in shape_order)
    terminal_solutions_seen = 0
    counted_solutions = 0
    last_reported_counted_solutions = 0
    root_branches_done = 0
    root_branch_total: int | None = None
    nodes = 0
    started = monotonic()
    last_heartbeat = started
    progress_print(
        f"start counter=raw_fixed_cube inventory={inventory} "
        f"placements={len(placements)} shapes={','.join(shape_order)} "
        f"progress_every={progress_every} heartbeat_seconds={heartbeat_seconds}",
        progress_file,
    )

    def report_counted_solutions(branch_total: int) -> None:
        nonlocal last_reported_counted_solutions
        if progress_every and counted_solutions - last_reported_counted_solutions >= progress_every:
            elapsed = monotonic() - started
            progress_print(
                f"progress raw_fixed_cube_solutions_counted={counted_solutions} "
                f"last_branch_solutions={branch_total} "
                f"root_branches={root_branches_done}/{root_branch_total} "
                f"terminal_solutions_seen={terminal_solutions_seen} "
                f"nodes={nodes} elapsed_seconds={elapsed:.1f}",
                progress_file,
            )
            last_reported_counted_solutions = counted_solutions

    def report_terminal_solution() -> None:
        if progress_every and terminal_solutions_seen % progress_every == 0:
            elapsed = monotonic() - started
            progress_print(
                f"progress terminal_solutions_seen={terminal_solutions_seen} "
                f"raw_fixed_cube_solutions_counted={counted_solutions} "
                f"root_branches={root_branches_done}/{root_branch_total} "
                f"nodes={nodes} elapsed_seconds={elapsed:.1f}",
                progress_file,
            )

    @lru_cache(maxsize=None)
    def possible_component_volumes(counts: tuple[int, ...]) -> frozenset[int]:
        possible = {0}
        for count, volume in zip(counts, shape_volumes):
            next_possible = set(possible)
            for n in range(1, count + 1):
                for existing in possible:
                    next_possible.add(existing + n * volume)
            possible = next_possible
        return frozenset(possible)

    def empty_component_volumes(empty_mask: int) -> list[int]:
        volumes: list[int] = []
        remaining = empty_mask
        while remaining:
            start = remaining & -remaining
            frontier = start
            component = 0
            while frontier:
                bit = frontier & -frontier
                frontier ^= bit
                if component & bit:
                    continue
                component |= bit
                index = bit.bit_length() - 1
                frontier |= NEIGHBOR_MASKS[index] & remaining & ~component
            remaining &= ~component
            volumes.append(component.bit_count())
        return volumes

    @lru_cache(maxsize=None)
    def search(occupied: int, counts: tuple[int, ...]) -> int:
        nonlocal terminal_solutions_seen, counted_solutions, root_branches_done
        nonlocal root_branch_total, nodes, last_heartbeat
        nodes += 1
        now = monotonic()
        if heartbeat_seconds and now - last_heartbeat >= heartbeat_seconds:
            progress_print(
                f"heartbeat raw_fixed_cube_solutions_counted={counted_solutions} "
                f"terminal_solutions_seen={terminal_solutions_seen} "
                f"root_branches={root_branches_done}/{root_branch_total} "
                f"nodes={nodes} occupied_cells={occupied.bit_count()} "
                f"elapsed_seconds={now - started:.1f}",
                progress_file,
            )
            last_heartbeat = now
        if occupied == ALL_MASK:
            terminal_solutions_seen += 1
            report_terminal_solution()
            return 1

        empty_mask = ALL_MASK ^ occupied
        possible_volumes = possible_component_volumes(counts)
        for volume in empty_component_volumes(empty_mask):
            if volume not in possible_volumes:
                return 0

        best_options: list[int] | None = None
        probe = empty_mask
        while probe:
            bit = probe & -probe
            cell = bit.bit_length() - 1
            options = [
                index
                for index in by_cell[cell]
                if counts[shape_index[placements[index].shape]] > 0
                and placements[index].mask & occupied == 0
            ]
            if best_options is None or len(options) < len(best_options):
                best_options = options
                if not options:
                    return 0
            probe ^= bit

        assert best_options is not None
        total = 0
        best_options.sort(key=lambda index: (placements[index].shape, placements[index].mask))
        if occupied == 0:
            root_branch_total = len(best_options)
        for index in best_options:
            placement = placements[index]
            count_index = shape_index[placement.shape]
            if counts[count_index] <= 0 or placement.mask & occupied:
                continue
            next_counts = list(counts)
            next_counts[count_index] -= 1
            branch_total = search(occupied | placement.mask, tuple(next_counts))
            total += branch_total
            if occupied == 0:
                root_branches_done += 1
                counted_solutions += branch_total
                report_counted_solutions(branch_total)
        return total

    return search(0, initial_counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--puzzle",
        choices=sorted(PUZZLE_INVENTORIES),
        default="evil",
        help="Named puzzle inventory to count.",
    )
    parser.add_argument(
        "--inventory",
        help="Custom inventory string, overriding --puzzle.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1,
        help="Print progress every N raw fixed-cube solutions. Use 0 to disable.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=30.0,
        help="Print a heartbeat every N seconds even if no solution has been found. Use 0 to disable.",
    )
    parser.add_argument(
        "--progress-file",
        default="evil_cube_raw_count_progress.txt",
        help="Append progress reports to this text file. Use an empty string to disable.",
    )
    args = parser.parse_args()
    inventory = args.inventory or PUZZLE_INVENTORIES[args.puzzle]
    progress_file = args.progress_file or None
    if progress_file:
        open(progress_file, "w", encoding="utf-8").close()

    raw = count_raw_solutions(
        inventory=inventory,
        progress_every=args.progress_every,
        heartbeat_seconds=args.heartbeat_seconds,
        progress_file=progress_file,
    )
    unique = raw // len(ROTATIONS)
    print(f"inventory={inventory}")
    print(f"raw_fixed_cube_solutions={raw}")
    print(f"unique_up_to_cube_rotation={unique}")
    print(f"cube_rotations={len(ROTATIONS)}")
    if progress_file:
        progress_print(
            f"final inventory={inventory} raw_fixed_cube_solutions={raw} "
            f"unique_up_to_cube_rotation={unique} cube_rotations={len(ROTATIONS)}",
            progress_file,
        )


if __name__ == "__main__":
    main()
