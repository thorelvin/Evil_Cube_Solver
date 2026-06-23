"""Render the Evil Cube solution animation as a README GIF.

This helper is only needed when regenerating the committed GIF asset. The
solver itself does not depend on Pillow.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


SIZE = 4
FRAMES_PER_PIECE = 8
FINAL_FRAMES = 10
FRAME_DURATION_MS = 85

LAYERS = [
    [
        ["S4", "B3", "B3", "B1"],
        ["S4", "B3", "B2", "B2"],
        ["L1", "S3", "B2", "B2"],
        ["L1", "L1", "B2", "R1"],
    ],
    [
        ["B3", "B3", "B3", "B1"],
        ["S4", "S4", "B1", "B1"],
        ["S4", "S3", "S3", "B2"],
        ["L1", "S3", "S2", "R1"],
    ],
    [
        ["A2", "A2", "A2", "B1"],
        ["A1", "A2", "S1", "B1"],
        ["A1", "S2", "S3", "Z1"],
        ["L1", "S2", "S2", "R1"],
    ],
    [
        ["A2", "A2", "S1", "S1"],
        ["A1", "S1", "S1", "Z1"],
        ["A1", "A1", "Z1", "Z1"],
        ["A1", "S2", "Z1", "R1"],
    ],
]

BASE_COLORS = {
    "A": "#2f80ed",
    "B": "#27ae60",
    "L": "#eb5757",
    "R": "#f2c94c",
    "S": "#9b51e0",
    "Z": "#00a7a7",
}

ENTRY_DIRECTIONS = [
    ("+x", "right face"),
    ("-x", "left face"),
    ("+y", "back face"),
    ("-y", "front face"),
    ("+z", "top"),
]


@dataclass(frozen=True)
class Cell:
    x: float
    y: float
    z: float


@dataclass
class Piece:
    label: str
    cells: list[Cell]
    color: str
    entry: str = ""
    entry_label: str = ""
    entry_offset: Cell = Cell(0, 0, 0)

    @property
    def min_x(self) -> float:
        return min(cell.x for cell in self.cells)

    @property
    def max_x(self) -> float:
        return max(cell.x for cell in self.cells)

    @property
    def min_y(self) -> float:
        return min(cell.y for cell in self.cells)

    @property
    def max_y(self) -> float:
        return max(cell.y for cell in self.cells)

    @property
    def min_z(self) -> float:
        return min(cell.z for cell in self.cells)

    @property
    def max_z(self) -> float:
        return max(cell.z for cell in self.cells)

    @property
    def avg_z(self) -> float:
        return sum(cell.z for cell in self.cells) / len(self.cells)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/animations/evil_cube_solution.gif"),
        help="GIF path to write.",
    )
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=390)
    args = parser.parse_args()

    pieces = plan_assembly(sorted(build_pieces(), key=piece_sort_key))
    frames = build_frames(pieces, args.width, args.height)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    paletted = [
        frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=96)
        for frame in frames
    ]
    paletted[0].save(
        args.output,
        save_all=True,
        append_images=paletted[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )

    route_summary = ", ".join(
        f"{index + 1}:{piece.label} from {piece.entry_label}"
        for index, piece in enumerate(pieces)
    )
    print(f"wrote {args.output} ({len(frames)} frames)")
    print(route_summary)


def build_pieces() -> list[Piece]:
    pieces: dict[str, list[Cell]] = {}
    for layer_z, rows in enumerate(LAYERS):
        for y, row in enumerate(rows):
            for x, label in enumerate(row):
                # The saved solution uses z=0 as the physical top layer.
                pieces.setdefault(label, []).append(Cell(x, y, SIZE - 1 - layer_z))

    return [
        Piece(label=label, cells=cells, color=color_for(label))
        for label, cells in pieces.items()
    ]


def piece_sort_key(piece: Piece) -> tuple[float, float, float, str]:
    return (piece.min_z, piece.avg_z, piece.max_z, piece.label)


def plan_assembly(pieces: list[Piece]) -> list[Piece]:
    locked: list[Cell] = []
    for piece in pieces:
        for direction, label in ENTRY_DIRECTIONS:
            if can_slide_from(piece, direction, locked):
                piece.entry = direction
                piece.entry_label = label
                piece.entry_offset = entry_offset_for(piece, direction)
                locked.extend(piece.cells)
                break
        else:
            raise RuntimeError(f"No clear entry path found for {piece.label}")
    return pieces


def can_slide_from(piece: Piece, direction: str, locked: list[Cell]) -> bool:
    return not any(
        would_sweep_through(cell, other, direction)
        for cell in piece.cells
        for other in locked
    )


def would_sweep_through(cell: Cell, locked: Cell, direction: str) -> bool:
    if direction == "+x":
        return cell.y == locked.y and cell.z == locked.z and locked.x >= cell.x
    if direction == "-x":
        return cell.y == locked.y and cell.z == locked.z and locked.x <= cell.x
    if direction == "+y":
        return cell.x == locked.x and cell.z == locked.z and locked.y >= cell.y
    if direction == "-y":
        return cell.x == locked.x and cell.z == locked.z and locked.y <= cell.y
    if direction == "+z":
        return cell.x == locked.x and cell.y == locked.y and locked.z >= cell.z
    raise ValueError(f"Unknown direction {direction}")


def entry_offset_for(piece: Piece, direction: str) -> Cell:
    margin = 2.25
    if direction == "+x":
        return Cell(SIZE + margin - piece.min_x, 0, 0)
    if direction == "-x":
        return Cell(-piece.max_x - margin, 0, 0)
    if direction == "+y":
        return Cell(0, SIZE + margin - piece.min_y, 0)
    if direction == "-y":
        return Cell(0, -piece.max_y - margin, 0)
    if direction == "+z":
        return Cell(0, 0, SIZE + margin - piece.min_z)
    raise ValueError(f"Unknown direction {direction}")


def build_frames(pieces: list[Piece], width: int, height: int) -> list[Image.Image]:
    frames: list[Image.Image] = []
    total_motion_frames = len(pieces) * FRAMES_PER_PIECE
    for frame_index in range(total_motion_frames + FINAL_FRAMES):
        if frame_index >= total_motion_frames:
            done_count = len(pieces)
            current_index = len(pieces)
            current_t = 1.0
        else:
            done_count = frame_index // FRAMES_PER_PIECE
            current_index = done_count
            local_index = frame_index % FRAMES_PER_PIECE
            current_t = ease_out_cubic(local_index / (FRAMES_PER_PIECE - 1))

        items: list[tuple[Piece, float, bool]] = [
            (pieces[index], 1.0, False) for index in range(done_count)
        ]
        if current_index < len(pieces):
            items.append((pieces[current_index], current_t, True))
        frames.append(draw_frame(items, width, height))
    return frames


def draw_frame(items: list[tuple[Piece, float, bool]], width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), "#f5f7f8")
    draw = ImageDraw.Draw(image)
    draw_background(draw, width, height)
    draw_bounding_box(draw, width, height)

    visible_set: set[tuple[int, int, int]] = set()
    draw_cells: list[tuple[Cell, Piece, float]] = []
    for piece, t, active in items:
        offset = offset_at(piece, t)
        for cell in piece.cells:
            moved = Cell(cell.x + offset.x, cell.y + offset.y, cell.z + offset.z)
            if t > 0.98:
                visible_set.add((int(cell.x), int(cell.y), int(cell.z)))
            alpha = 0.9 + 0.1 * t if active else 1.0
            draw_cells.append((moved, piece, alpha))

    approximate_set = {
        (round(cell.x), round(cell.y), round(cell.z)) for cell, _, _ in draw_cells
    }
    draw_cells.sort(key=lambda item: (item[0].x + item[0].y + item[0].z, item[1].label))

    for cell, piece, alpha in draw_cells:
        blockers = visible_set if alpha > 0.99 else approximate_set
        draw_cube(draw, cell, piece.color, blockers, alpha, width, height)
    return image


def draw_background(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    for y in range(height):
        amount = y / max(1, height - 1)
        color = mix("#ffffff", "#eef3f5", amount)
        draw.line([(0, y), (width, y)], fill=color)


def draw_bounding_box(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    bottom = [project(Cell(x, y, 0), width, height) for x, y in [(0, 0), (SIZE, 0), (SIZE, SIZE), (0, SIZE)]]
    top = [project(Cell(x, y, SIZE), width, height) for x, y in [(0, 0), (SIZE, 0), (SIZE, SIZE), (0, SIZE)]]
    line = "#bcc7d1"
    draw.line(bottom + [bottom[0]], fill=line, width=2)
    draw.line(top + [top[0]], fill=line, width=2)
    for index in range(4):
        draw.line([bottom[index], top[index]], fill=line, width=2)


def draw_cube(
    draw: ImageDraw.ImageDraw,
    cell: Cell,
    color: str,
    visible_set: set[tuple[int, int, int]],
    alpha: float,
    width: int,
    height: int,
) -> None:
    corners = cube_corners(cell)
    faces = [
        (
            (round(cell.x + 1), round(cell.y), round(cell.z)),
            color,
            [corners["c100"], corners["c110"], corners["c111"], corners["c101"]],
        ),
        (
            (round(cell.x), round(cell.y + 1), round(cell.z)),
            mix(color, "#000000", 0.20),
            [corners["c010"], corners["c110"], corners["c111"], corners["c011"]],
        ),
        (
            (round(cell.x), round(cell.y), round(cell.z + 1)),
            mix(color, "#ffffff", 0.26),
            [corners["c001"], corners["c101"], corners["c111"], corners["c011"]],
        ),
    ]
    for neighbor, fill, points in faces:
        if neighbor in visible_set:
            continue
        fill = mix("#ffffff", fill, alpha)
        polygon = [project(point, width, height) for point in points]
        draw.polygon(polygon, fill=fill, outline="#202833")


def cube_corners(cell: Cell) -> dict[str, Cell]:
    x, y, z = cell.x, cell.y, cell.z
    return {
        "c000": Cell(x, y, z),
        "c100": Cell(x + 1, y, z),
        "c010": Cell(x, y + 1, z),
        "c110": Cell(x + 1, y + 1, z),
        "c001": Cell(x, y, z + 1),
        "c101": Cell(x + 1, y, z + 1),
        "c011": Cell(x, y + 1, z + 1),
        "c111": Cell(x + 1, y + 1, z + 1),
    }


def offset_at(piece: Piece, t: float) -> Cell:
    remaining = 1 - t
    return Cell(
        piece.entry_offset.x * remaining,
        piece.entry_offset.y * remaining,
        piece.entry_offset.z * remaining,
    )


def project(point: Cell, width: int, height: int) -> tuple[int, int]:
    scale_base = min(width / 8.0, height / 6.4)
    scale_x = scale_base * 0.78
    scale_y = scale_base * 0.43
    scale_z = scale_base * 0.83
    origin_x = width * 0.5
    origin_y = height * 0.65
    return (
        round(origin_x + (point.x - point.y) * scale_x),
        round(origin_y + (point.x + point.y) * scale_y - point.z * scale_z),
    )


def color_for(label: str) -> str:
    amount = ((int(label[1:]) if label[1:].isdigit() else 1) - 1) * 0.07
    return shift_color(BASE_COLORS[label[0]], amount)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    normalized = hex_color.lstrip("#")
    return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(value))):02x}" for value in rgb)


def mix(a: str, b: str, amount: float) -> str:
    ar, ag, ab = hex_to_rgb(a)
    br, bg, bb = hex_to_rgb(b)
    return rgb_to_hex(
        (
            ar + (br - ar) * amount,
            ag + (bg - ag) * amount,
            ab + (bb - ab) * amount,
        )
    )


def shift_color(hex_color: str, amount: float) -> str:
    target = "#000000" if amount > 0.14 else "#ffffff"
    return mix(hex_color, target, min(0.22, amount))


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


if __name__ == "__main__":
    main()
