#!/usr/bin/env python3
"""Solve the Printables Evil Cube as an exact-cover polycube puzzle.

The Evil Cube is a 4x4x4 packing puzzle with brick inventory:

    Z S S S S R L A A B B B

This script uses a depth-first exact-cover search over all rotations and
translations of those bricks.  It prints the first solution it finds as four
z-layers plus per-piece placements.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import itertools
import math
from pathlib import Path
from typing import Iterable


Coord = tuple[int, int, int]


# Normalized unit-cell coordinates.  These definitions are derived from the
# author's public Friendly Cube solution OBJs, which are ordered as
# ZSRLLLLAABBB on the Printables page.  Use --validate-reference to re-check
# them against the downloaded reference_bricks/ OBJ files.
SHAPES: dict[str, tuple[Coord, ...]] = {
    "A": ((0, 0, 0), (1, 0, 0), (1, 0, 1), (1, 1, 0), (2, 0, 0), (2, 1, 0)),
    "B": ((0, 1, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1), (2, 1, 0), (2, 1, 1)),
    "L": ((0, 0, 0), (0, 1, 0), (0, 1, 1), (1, 1, 0), (2, 1, 0)),
    "R": ((0, 0, 0), (0, 1, 0), (0, 2, 0), (0, 3, 0)),
    "S": ((0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 1, 0)),
    "Z": ((0, 1, 0), (1, 0, 0), (1, 0, 1), (1, 1, 0), (2, 0, 0)),
}

EVIL_INVENTORY = "ZSSSSRLAABBB"
FRIENDLY_REFERENCE_IDS = [
    ("Z", "17"),
    ("S", "469"),
    ("R", "880"),
    ("L", "960"),
    ("L", "968"),
    ("L", "988"),
    ("L", "1199"),
    ("A", "1353"),
    ("A", "1697"),
    ("B", "1791"),
    ("B", "1843"),
    ("B", "1853"),
]


@dataclass(frozen=True)
class Placement:
    instance: str
    shape: str
    cells: tuple[Coord, ...]
    orientation: int
    offset: Coord


def parse_obj(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            _, x, y, z = line.split()
            vertices.append((float(x), float(y), float(z)))
        elif line.startswith("f "):
            parts = line.split()[1:]
            if len(parts) != 3:
                raise ValueError(f"{path}: expected triangulated OBJ faces")
            faces.append(tuple(int(part.split("/", 1)[0]) - 1 for part in parts))
    return vertices, faces


def ray_intersects_triangle(
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    tri: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> float | None:
    eps = 1e-9
    v0, v1, v2 = tri
    edge1 = subf(v1, v0)
    edge2 = subf(v2, v0)
    h = crossf(direction, edge2)
    det = dotf(edge1, h)
    if -eps < det < eps:
        return None
    inv_det = 1.0 / det
    s = subf(origin, v0)
    u = inv_det * dotf(s, h)
    if u < -eps or u > 1.0 + eps:
        return None
    q = crossf(s, edge1)
    v = inv_det * dotf(direction, q)
    if v < -eps or u + v > 1.0 + eps:
        return None
    t = inv_det * dotf(edge2, q)
    if t <= eps:
        return None
    return t


def obj_to_cells(path: Path) -> tuple[Coord, ...]:
    vertices, faces = parse_obj(path)
    triangles = [(vertices[a], vertices[b], vertices[c]) for a, b, c in faces]
    direction = normalizef((1.0, 0.371390676354, 0.529998940004))
    max_x = math.ceil(max(v[0] for v in vertices))
    max_y = math.ceil(max(v[1] for v in vertices))
    max_z = math.ceil(max(v[2] for v in vertices))
    cells: list[Coord] = []
    for x in range(max_x):
        for y in range(max_y):
            for z in range(max_z):
                center = (x + 0.5, y + 0.5, z + 0.5)
                hits = {
                    round(t, 8)
                    for tri in triangles
                    if (t := ray_intersects_triangle(center, direction, tri)) is not None
                }
                if len(hits) % 2 == 1:
                    cells.append((x, y, z))
    return normalize_cells(cells)


def derive_shapes(reference_dir: Path) -> dict[str, tuple[Coord, ...]]:
    derived: dict[str, tuple[Coord, ...]] = {}
    for name, obj_id in FRIENDLY_REFERENCE_IDS:
        cells = obj_to_cells(reference_dir / f"{obj_id}.obj")
        existing = derived.get(name)
        if existing is None:
            derived[name] = cells
        elif canonical(cells) != canonical(existing):
            # Multiple same-type pieces appear in different rotations/translations.
            # Their canonical form should match if the type mapping is right.
            raise ValueError(
                f"reference brick {obj_id} does not match derived shape {name}: "
                f"{cells} vs {existing}"
            )
    return derived


def add(a: Coord, b: Coord) -> Coord:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subf(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dotf(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def crossf(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalizef(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(dotf(v, v))
    return (v[0] / length, v[1] / length, v[2] / length)


def normalize_cells(cells: Iterable[Coord]) -> tuple[Coord, ...]:
    cell_list = list(cells)
    min_x = min(x for x, _, _ in cell_list)
    min_y = min(y for _, y, _ in cell_list)
    min_z = min(z for _, _, z in cell_list)
    return tuple(sorted((x - min_x, y - min_y, z - min_z) for x, y, z in cell_list))


def rotate_cell(cell: Coord, perm: tuple[int, int, int], signs: tuple[int, int, int]) -> Coord:
    values = [cell[0], cell[1], cell[2]]
    return (
        signs[0] * values[perm[0]],
        signs[1] * values[perm[1]],
        signs[2] * values[perm[2]],
    )


def permutation_parity(perm: tuple[int, int, int]) -> int:
    inversions = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            inversions += perm[i] > perm[j]
    return -1 if inversions % 2 else 1


def orientations(cells: tuple[Coord, ...]) -> list[tuple[Coord, ...]]:
    result = set()
    for perm in itertools.permutations((0, 1, 2)):
        parity = permutation_parity(perm)
        for signs in itertools.product((-1, 1), repeat=3):
            if signs[0] * signs[1] * signs[2] * parity != 1:
                continue
            rotated = [rotate_cell(cell, perm, signs) for cell in cells]
            result.add(normalize_cells(rotated))
    return sorted(result)


def canonical(cells: tuple[Coord, ...]) -> tuple[Coord, ...]:
    return min(orientations(cells))


def build_instances(inventory: str) -> list[tuple[str, str]]:
    counts: dict[str, int] = {}
    instances: list[tuple[str, str]] = []
    for shape in inventory:
        counts[shape] = counts.get(shape, 0) + 1
        instances.append((f"{shape}{counts[shape]}", shape))
    return instances


def generate_placements(
    instances: list[tuple[str, str]],
    shapes: dict[str, tuple[Coord, ...]],
    size: int,
) -> tuple[list[Placement], dict[Coord, list[int]], dict[str, list[int]]]:
    placements: list[Placement] = []
    by_cell: dict[Coord, list[int]] = {
        (x, y, z): [] for x in range(size) for y in range(size) for z in range(size)
    }
    by_instance: dict[str, list[int]] = {instance: [] for instance, _ in instances}
    for instance, shape_name in instances:
        for orientation_index, oriented in enumerate(orientations(shapes[shape_name])):
            max_x = max(x for x, _, _ in oriented)
            max_y = max(y for _, y, _ in oriented)
            max_z = max(z for _, _, z in oriented)
            for ox in range(size - max_x):
                for oy in range(size - max_y):
                    for oz in range(size - max_z):
                        cells = tuple(sorted(add(cell, (ox, oy, oz)) for cell in oriented))
                        index = len(placements)
                        placements.append(
                            Placement(
                                instance=instance,
                                shape=shape_name,
                                cells=cells,
                                orientation=orientation_index,
                                offset=(ox, oy, oz),
                            )
                        )
                        by_instance[instance].append(index)
                        for cell in cells:
                            by_cell[cell].append(index)
    return placements, by_cell, by_instance


def solve(
    shapes: dict[str, tuple[Coord, ...]],
    inventory: str = EVIL_INVENTORY,
    size: int = 4,
    max_solutions: int = 1,
) -> list[list[Placement]]:
    instances = build_instances(inventory)
    expected_volume = size**3
    actual_volume = sum(len(shapes[shape]) for _, shape in instances)
    if actual_volume != expected_volume:
        raise ValueError(f"inventory volume is {actual_volume}, expected {expected_volume}")

    placements, by_cell, by_instance = generate_placements(instances, shapes, size)
    all_cells = set(by_cell)
    unused_instances = {instance for instance, _ in instances}
    occupied: dict[Coord, str] = {}
    chosen: list[Placement] = []
    solutions: list[list[Placement]] = []

    def search() -> bool:
        if len(solutions) >= max_solutions:
            return True
        if not unused_instances:
            if len(occupied) == expected_volume:
                solutions.append(chosen.copy())
            return len(solutions) >= max_solutions

        empty_cells = all_cells - occupied.keys()
        best_cell = None
        best_options: list[int] | None = None
        for cell in empty_cells:
            unique_options: dict[tuple[str, tuple[Coord, ...]], int] = {}
            for index in by_cell[cell]:
                placement = placements[index]
                if placement.instance not in unused_instances:
                    continue
                if any(c in occupied for c in placement.cells):
                    continue
                unique_options.setdefault((placement.shape, placement.cells), index)
            options = list(unique_options.values())
            if best_options is None or len(options) < len(best_options):
                best_cell = cell
                best_options = options
                if not options:
                    break
        if best_cell is None or best_options is None or not best_options:
            return False

        best_options.sort(key=lambda index: placements[index].instance)
        for index in best_options:
            placement = placements[index]
            if placement.instance not in unused_instances:
                continue
            if any(cell in occupied for cell in placement.cells):
                continue
            unused_instances.remove(placement.instance)
            for cell in placement.cells:
                occupied[cell] = placement.instance
            chosen.append(placement)

            if search():
                return True

            chosen.pop()
            for cell in placement.cells:
                del occupied[cell]
            unused_instances.add(placement.instance)
        return False

    search()
    return solutions


def render_solution(solution: list[Placement], size: int = 4) -> str:
    labels = {cell: placement.instance for placement in solution for cell in placement.cells}
    lines: list[str] = []
    for z in range(size):
        lines.append(f"z={z}")
        for y in range(size):
            lines.append(" ".join(f"{labels[(x, y, z)]:>2}" for x in range(size)))
        lines.append("")
    lines.append("placements:")
    for placement in sorted(solution, key=lambda p: p.instance):
        cells = " ".join(f"({x},{y},{z})" for x, y, z in placement.cells)
        lines.append(
            f"{placement.instance}: shape={placement.shape} "
            f"orientation={placement.orientation} offset={placement.offset} cells={cells}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path("reference_bricks"),
        help="Directory containing the Friendly Cube OBJ files used to derive shapes.",
    )
    parser.add_argument(
        "--show-shapes",
        action="store_true",
        help="Print derived normalized shape cells before solving.",
    )
    parser.add_argument(
        "--validate-reference",
        action="store_true",
        help="Validate hardcoded shapes against OBJ files in --reference-dir.",
    )
    parser.add_argument("--max-solutions", type=int, default=1)
    args = parser.parse_args()

    shapes = dict(SHAPES)
    if args.validate_reference:
        if not args.reference_dir.exists():
            raise SystemExit(f"reference directory not found: {args.reference_dir}")
        derived = derive_shapes(args.reference_dir)
        mismatches = [
            name
            for name, cells in derived.items()
            if canonical(cells) != canonical(shapes[name])
        ]
        if mismatches:
            raise SystemExit(f"reference shape mismatch: {', '.join(mismatches)}")
        print(f"validated {len(derived)} shape types from {args.reference_dir}")

    missing = sorted(set(EVIL_INVENTORY) - set(shapes))
    if missing:
        raise SystemExit(
            f"missing shapes {missing}; run from the workspace with {args.reference_dir}/ present"
        )

    if args.show_shapes:
        for name in sorted(shapes):
            print(f"{name}: {shapes[name]} volume={len(shapes[name])}")
        print()

    solutions = solve(shapes, max_solutions=args.max_solutions)
    if not solutions:
        raise SystemExit("no solution found")
    print(render_solution(solutions[0]))


if __name__ == "__main__":
    main()
