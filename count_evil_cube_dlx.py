#!/usr/bin/env python3
"""Fast exact-cover count for Evil Cube family inventories using Algorithm X."""

from __future__ import annotations

import argparse
from collections import Counter
from math import factorial
from time import monotonic

from solve_evil_cube import (
    EVIL_INVENTORY,
    PUZZLE_INVENTORIES,
    SHAPES,
    Coord,
    build_instances,
    orientations,
)


SIZE = 4


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


def add(a: Coord, b: Coord) -> Coord:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def build_exact_cover(inventory: str = EVIL_INVENTORY) -> tuple[list[set[int]], list[set[int]], int]:
    instances = build_instances(inventory)
    piece_column = {instance: 64 + i for i, (instance, _) in enumerate(instances)}
    column_count = 64 + len(instances)
    columns = [set() for _ in range(column_count)]
    rows: list[set[int]] = []

    for instance, shape in instances:
        seen_masks: set[tuple[int, ...]] = set()
        for oriented in orientations(SHAPES[shape]):
            max_x = max(x for x, _, _ in oriented)
            max_y = max(y for _, y, _ in oriented)
            max_z = max(z for _, _, z in oriented)
            for ox in range(SIZE - max_x):
                for oy in range(SIZE - max_y):
                    for oz in range(SIZE - max_z):
                        cells = tuple(sorted(cell_index(add(c, (ox, oy, oz))) for c in oriented))
                        if cells in seen_masks:
                            continue
                        seen_masks.add(cells)
                        row = set(cells)
                        row.add(piece_column[instance])
                        row_id = len(rows)
                        rows.append(row)
                        for col in row:
                            columns[col].add(row_id)

    return rows, columns, column_count


def count_labelled(
    inventory: str = EVIL_INVENTORY,
    progress_every: int = 0,
    heartbeat_seconds: float = 30.0,
    progress_file: str | None = None,
) -> int:
    rows, columns, column_count = build_exact_cover(inventory)
    active_columns = set(range(column_count))
    count = 0
    nodes = 0
    started = monotonic()
    last_heartbeat = started
    progress_print(
        f"start counter=dlx_labelled inventory={inventory} "
        f"rows={len(rows)} columns={column_count} "
        f"progress_every={progress_every} heartbeat_seconds={heartbeat_seconds}",
        progress_file,
    )

    def report_heartbeat(depth: int) -> None:
        nonlocal last_heartbeat
        now = monotonic()
        if heartbeat_seconds and now - last_heartbeat >= heartbeat_seconds:
            progress_print(
                f"heartbeat labelled_solutions={count} nodes={nodes} "
                f"depth={depth} active_columns={len(active_columns)} "
                f"elapsed_seconds={now - started:.1f}",
                progress_file,
            )
            last_heartbeat = now

    def cover(col: int) -> list[tuple[int, list[tuple[int, int]]]]:
        active_columns.remove(col)
        removed: list[tuple[int, list[tuple[int, int]]]] = []
        for row_id in list(columns[col]):
            row_removed: list[tuple[int, int]] = []
            for other_col in rows[row_id]:
                if other_col == col:
                    continue
                if row_id in columns[other_col]:
                    columns[other_col].remove(row_id)
                    row_removed.append((other_col, row_id))
            removed.append((row_id, row_removed))
        return removed

    def uncover(col: int, removed: list[tuple[int, list[tuple[int, int]]]]) -> None:
        for _row_id, row_removed in reversed(removed):
            for other_col, row_id in reversed(row_removed):
                columns[other_col].add(row_id)
        active_columns.add(col)

    def search(depth: int = 0) -> None:
        nonlocal count, nodes
        nodes += 1
        report_heartbeat(depth)
        if not active_columns:
            count += 1
            if progress_every and count % progress_every == 0:
                elapsed = monotonic() - started
                progress_print(
                    f"progress labelled_solutions={count} "
                    f"nodes={nodes} elapsed_seconds={elapsed:.1f}",
                    progress_file,
                )
            return

        col = min(active_columns, key=lambda c: len(columns[c]))
        if not columns[col]:
            return

        for row_id in list(columns[col]):
            report_heartbeat(depth)
            covered = []
            for row_col in rows[row_id]:
                if row_col in active_columns:
                    covered.append((row_col, cover(row_col)))
            search(depth + 1)
            for row_col, removed in reversed(covered):
                uncover(row_col, removed)

    search()
    return count


def duplicate_label_factor(inventory: str) -> int:
    duplicate_factor = 1
    for count in Counter(inventory).values():
        duplicate_factor *= factorial(count)
    return duplicate_factor


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
        help="Print progress every N labelled exact-cover solutions. Use 0 to disable.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=30.0,
        help="Print a heartbeat every N seconds even if no solution has been found. Use 0 to disable.",
    )
    parser.add_argument(
        "--progress-file",
        default="evil_cube_dlx_count_progress.txt",
        help="Append progress reports to this text file. Use an empty string to disable.",
    )
    args = parser.parse_args()
    inventory = args.inventory or PUZZLE_INVENTORIES[args.puzzle]
    progress_file = args.progress_file or None
    if progress_file:
        open(progress_file, "w", encoding="utf-8").close()

    labelled = count_labelled(
        inventory=inventory,
        progress_every=args.progress_every,
        heartbeat_seconds=args.heartbeat_seconds,
        progress_file=progress_file,
    )
    duplicate_factor = duplicate_label_factor(inventory)
    raw = labelled // duplicate_factor
    print(f"inventory={inventory}")
    print(f"labelled_solutions={labelled}")
    print(f"duplicate_label_factor={duplicate_factor}")
    print(f"raw_fixed_cube_solutions={raw}")
    print(f"unique_up_to_cube_rotation={raw // 24}")
    if progress_file:
        progress_print(
            f"final inventory={inventory} labelled_solutions={labelled} "
            f"duplicate_label_factor={duplicate_factor} "
            f"raw_fixed_cube_solutions={raw} unique_up_to_cube_rotation={raw // 24}",
            progress_file,
        )


if __name__ == "__main__":
    main()
