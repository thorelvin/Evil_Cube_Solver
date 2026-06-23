#!/usr/bin/env python3
"""Count physical fixed-cube solutions for the Ultra Cube."""

from __future__ import annotations

import argparse

from count_evil_cube_solutions import ROTATIONS, count_raw_solutions, progress_print
from solve_evil_cube import ULTRA_INVENTORY


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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
        default="ultra_cube_raw_count_progress.txt",
        help="Append progress reports to this text file. Use an empty string to disable.",
    )
    args = parser.parse_args()

    progress_file = args.progress_file or None
    if progress_file:
        open(progress_file, "w", encoding="utf-8").close()

    raw = count_raw_solutions(
        inventory=ULTRA_INVENTORY,
        progress_every=args.progress_every,
        heartbeat_seconds=args.heartbeat_seconds,
        progress_file=progress_file,
    )
    unique = raw // len(ROTATIONS)
    print(f"inventory={ULTRA_INVENTORY}")
    print(f"raw_fixed_cube_solutions={raw}")
    print(f"unique_up_to_cube_rotation={unique}")
    print(f"cube_rotations={len(ROTATIONS)}")
    if progress_file:
        progress_print(
            f"final inventory={ULTRA_INVENTORY} raw_fixed_cube_solutions={raw} "
            f"unique_up_to_cube_rotation={unique} cube_rotations={len(ROTATIONS)}",
            progress_file,
        )


if __name__ == "__main__":
    main()
