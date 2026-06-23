#!/usr/bin/env python3
"""Fast labelled exact-cover count for the Ultra Cube using Algorithm X."""

from __future__ import annotations

import argparse

from count_evil_cube_dlx import count_labelled, duplicate_label_factor, progress_print
from solve_evil_cube import ULTRA_INVENTORY


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
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
        default="ultra_cube_dlx_count_progress.txt",
        help="Append progress reports to this text file. Use an empty string to disable.",
    )
    args = parser.parse_args()

    progress_file = args.progress_file or None
    if progress_file:
        open(progress_file, "w", encoding="utf-8").close()

    labelled = count_labelled(
        inventory=ULTRA_INVENTORY,
        progress_every=args.progress_every,
        heartbeat_seconds=args.heartbeat_seconds,
        progress_file=progress_file,
    )
    duplicate_factor = duplicate_label_factor(ULTRA_INVENTORY)
    raw = labelled // duplicate_factor
    print(f"inventory={ULTRA_INVENTORY}")
    print(f"labelled_solutions={labelled}")
    print(f"duplicate_label_factor={duplicate_factor}")
    print(f"raw_fixed_cube_solutions={raw}")
    print(f"unique_up_to_cube_rotation={raw // 24}")
    if progress_file:
        progress_print(
            f"final inventory={ULTRA_INVENTORY} labelled_solutions={labelled} "
            f"duplicate_label_factor={duplicate_factor} "
            f"raw_fixed_cube_solutions={raw} unique_up_to_cube_rotation={raw // 24}",
            progress_file,
        )


if __name__ == "__main__":
    main()
