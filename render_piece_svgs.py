#!/usr/bin/env python3
"""Render isometric SVG previews for the embedded Evil Cube pieces."""

from __future__ import annotations

from pathlib import Path

from solve_evil_cube import SHAPES, Coord


ASSET_DIR = Path("assets/pieces")
PROJECT_X = 38.0
PROJECT_Y = 22.0
PROJECT_Z = 42.0

PALETTE = {
    "A": "#2f80ed",
    "B": "#27ae60",
    "L": "#eb5757",
    "R": "#f2c94c",
    "S": "#9b51e0",
    "Z": "#00a7a7",
}


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in rgb)


def mix(color: str, other: str, amount: float) -> str:
    r1, g1, b1 = hex_to_rgb(color)
    r2, g2, b2 = hex_to_rgb(other)
    return rgb_to_hex(
        (
            round(r1 + (r2 - r1) * amount),
            round(g1 + (g2 - g1) * amount),
            round(b1 + (b2 - b1) * amount),
        )
    )


def project(point: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = point
    return ((x - y) * PROJECT_X, (x + y) * PROJECT_Y - z * PROJECT_Z)


def cube_corners(cell: Coord) -> dict[str, tuple[float, float, float]]:
    x, y, z = cell
    return {
        "000": (x, y, z),
        "100": (x + 1, y, z),
        "010": (x, y + 1, z),
        "110": (x + 1, y + 1, z),
        "001": (x, y, z + 1),
        "101": (x + 1, y, z + 1),
        "011": (x, y + 1, z + 1),
        "111": (x + 1, y + 1, z + 1),
    }


def polygon(points: list[tuple[float, float]], fill: str) -> str:
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<polygon points="{point_text}" fill="{fill}" '
        'stroke="#242424" stroke-width="1.4" stroke-linejoin="round" />'
    )


def visible_faces(cells: tuple[Coord, ...], color: str) -> list[tuple[float, str]]:
    cell_set = set(cells)
    faces: list[tuple[float, str]] = []
    face_defs = [
        ((0, 0, 1), ["001", "101", "111", "011"], mix(color, "#ffffff", 0.25)),
        ((1, 0, 0), ["100", "110", "111", "101"], color),
        ((0, 1, 0), ["010", "110", "111", "011"], mix(color, "#000000", 0.18)),
    ]
    for cell in cells:
        corners = cube_corners(cell)
        for neighbor_delta, corner_keys, fill in face_defs:
            neighbor = (
                cell[0] + neighbor_delta[0],
                cell[1] + neighbor_delta[1],
                cell[2] + neighbor_delta[2],
            )
            if neighbor in cell_set:
                continue
            points_3d = [corners[key] for key in corner_keys]
            depth = sum(x + y + z for x, y, z in points_3d) / len(points_3d)
            faces.append((depth, polygon([project(point) for point in points_3d], fill)))
    return sorted(faces, key=lambda item: item[0])


def render_piece(name: str, cells: tuple[Coord, ...]) -> str:
    color = PALETTE[name]
    faces = visible_faces(cells, color)

    all_projected = []
    for cell in cells:
        all_projected.extend(project(point) for point in cube_corners(cell).values())

    min_x = min(x for x, _ in all_projected)
    max_x = max(x for x, _ in all_projected)
    min_y = min(y for _, y in all_projected)
    max_y = max(y for _, y in all_projected)
    margin = 26
    label_height = 42
    view_x = min_x - margin
    view_y = min_y - label_height
    view_w = max_x - min_x + margin * 2
    view_h = max_y - min_y + margin + label_height

    face_markup = "\n  ".join(face for _depth, face in faces)
    label_x = view_x + 6
    label_y = view_y + 24
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_x:.1f} {view_y:.1f} {view_w:.1f} {view_h:.1f}" role="img" aria-labelledby="title desc">
  <title id="title">Evil Cube {name} piece</title>
  <desc id="desc">Isometric rendering of the {name} brick made from {len(cells)} unit cubes.</desc>
  <rect x="{view_x:.1f}" y="{view_y:.1f}" width="{view_w:.1f}" height="{view_h:.1f}" rx="8" fill="#fafafa" />
  <text x="{label_x:.1f}" y="{label_y:.1f}" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700" fill="#1f1f1f">{name} piece</text>
  {face_markup}
</svg>
"""


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for name, cells in sorted(SHAPES.items()):
        (ASSET_DIR / f"{name}.svg").write_text(render_piece(name, cells), encoding="utf-8")
    print(f"wrote {len(SHAPES)} SVG files to {ASSET_DIR}")


if __name__ == "__main__":
    main()
