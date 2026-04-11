#!/usr/bin/env python3

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from _common import ASSETS_DIR, REPO_ROOT, asset_relpath, require_input, run_tool, write_output


# Audited maze tile source list.
#
# The arcade maze geometry lives in tile IDs 0xC0-0xFF. T005 also keeps the
# core maze-adjacent primitives below so the reviewer can inspect blank
# corridor, dot, power pellet, and ghost-house gate tiles before T006 authors
# the maze nametable.
MAZE_GEOMETRY_TILE_IDS = tuple(range(0xC0, 0x100))
EXTRA_MAZE_TILE_SOURCES = (
    (0x10, 18, "dot"),
    (0x14, 20, "power_pellet"),
    (0x1A, 1, "blank_corridor"),
    (0x2E, 31, "ghost_gate_left"),
    (0x2F, 31, "ghost_gate_right"),
)
MAZE_WALL_CLUT_ID = 16

PALETTE_MAP_PATH = REPO_ROOT / "assets" / "src" / "palette_map.md"
TILE_INDEX_PATH = ASSETS_DIR / "tiles_vdpb.index.txt"
MAZE_LAYOUT_PATH = REPO_ROOT / "assets" / "src" / "maze_layout.txt"
EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T005-tiles"
TILE_BANK_PNG_PATH = EVIDENCE_DIR / "tile_bank.png"

TILE_WIDTH = 8
TILE_HEIGHT = 8
TILE_BYTES = 32
FRAME_WIDTH = 256
FRAME_HEIGHT = 212
FRAME_ROW_BYTES = FRAME_WIDTH // 2
ARCADE_COLUMNS = 28
ARCADE_ROWS = 36
ROTATED_COLUMNS = ARCADE_ROWS
ROTATED_ROWS = ARCADE_COLUMNS
MAZE_CROP_X = 16
MAZE_CROP_Y = 6
ZOOM = 4


@dataclass(frozen=True)
class TileSource:
    tile_id: int
    clut_id: int
    name: str


@dataclass(frozen=True)
class ConvertedTile:
    index: int
    source: TileSource
    pixels: tuple[tuple[int, ...], ...]
    packed: bytes


def decode_tiles(rom: bytes) -> list[list[list[int]]]:
    count = len(rom) // 16
    tiles: list[list[list[int]]] = []

    for tile_id in range(count):
        tile = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
        for x in range(TILE_WIDTH):
            for base_y, row_offset in ((0, 8), (4, 0)):
                byte = rom[tile_id * 16 + row_offset + (7 - x)]
                for y in range(TILE_HEIGHT // 2):
                    high = (byte >> (7 - y)) & 1
                    low = (byte >> (3 - y)) & 1
                    tile[base_y + y][x] = (high << 1) | low
        tiles.append(tile)

    return tiles


def decode_clut(prom: bytes) -> list[tuple[int, int, int, int]]:
    return [tuple(prom[i * 4 + j] & 0x0F for j in range(4)) for i in range(64)]


def load_prom_to_slot_map(path: Path) -> dict[int, int]:
    pattern = re.compile(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|")
    prom_to_slot: dict[int, int] = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match is None:
            continue
        slot = int(match.group(1))
        prom_index = int(match.group(2))
        prom_to_slot.setdefault(prom_index, slot)

    if not prom_to_slot:
        raise RuntimeError(f"no palette slot rows found in {path}")
    return prom_to_slot


def load_slot_rgb(path: Path) -> dict[int, tuple[int, int, int]]:
    pattern = re.compile(r"^\|\s*(\d+)\s*\|\s*\d+\s*\|\s*`#[0-9A-Fa-f]{6}`\s*\|\s*`([0-7]),([0-7]),([0-7])`")
    levels = (0, 36, 73, 109, 146, 182, 219, 255)
    slot_rgb: dict[int, tuple[int, int, int]] = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match is None:
            continue
        slot = int(match.group(1))
        slot_rgb[slot] = tuple(levels[int(match.group(i))] for i in range(2, 5))

    if len(slot_rgb) != 16:
        raise RuntimeError(f"expected 16 palette rows in {path}, found {len(slot_rgb)}")
    return slot_rgb


def rotate_ccw(tile: list[list[int]]) -> list[list[int]]:
    rotated = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
    for y in range(TILE_HEIGHT):
        for x in range(TILE_WIDTH):
            rotated[7 - x][y] = tile[y][x]
    return rotated


def apply_palette(
    rotated_tile: list[list[int]],
    clut_entry: tuple[int, int, int, int],
    prom_to_slot: dict[int, int],
) -> tuple[tuple[int, ...], ...]:
    pixels: list[tuple[int, ...]] = []
    for row in rotated_tile:
        out_row: list[int] = []
        for pixel in row:
            prom_index = clut_entry[pixel]
            try:
                out_row.append(prom_to_slot[prom_index])
            except KeyError as error:
                raise RuntimeError(
                    f"CLUT references PROM color {prom_index}, which has no T004 palette slot"
                ) from error
        pixels.append(tuple(out_row))
    return tuple(pixels)


def pack_graphic4(tile: tuple[tuple[int, ...], ...]) -> bytes:
    packed = bytearray()
    for row in tile:
        for x in range(0, TILE_WIDTH, 2):
            packed.append((row[x] << 4) | row[x + 1])
    if len(packed) != TILE_BYTES:
        raise AssertionError(f"packed tile size mismatch: {len(packed)}")
    return bytes(packed)


def edge_mask(tile: tuple[tuple[int, ...], ...]) -> str:
    top = any(pixel != 0 for pixel in tile[0])
    right = any(row[-1] != 0 for row in tile)
    bottom = any(pixel != 0 for pixel in tile[-1])
    left = any(row[0] != 0 for row in tile)
    mask = "".join(label for label, present in (("n", top), ("e", right), ("s", bottom), ("w", left)) if present)
    return mask or "isolated"


def make_tile_sources() -> list[TileSource]:
    sources = [
        TileSource(tile_id, MAZE_WALL_CLUT_ID, f"maze_wall_{tile_id:02x}")
        for tile_id in MAZE_GEOMETRY_TILE_IDS
    ]
    sources.extend(TileSource(tile_id, clut_id, name) for tile_id, clut_id, name in EXTRA_MAZE_TILE_SOURCES)
    return sources


def convert_tiles(
    tiles: list[list[list[int]]],
    clut: list[tuple[int, int, int, int]],
    prom_to_slot: dict[int, int],
) -> tuple[list[ConvertedTile], list[str], dict[int, int]]:
    converted: list[ConvertedTile] = []
    warnings: list[str] = []
    seen: dict[bytes, ConvertedTile] = {}
    source_to_index: dict[int, int] = {}

    for source in make_tile_sources():
        rotated = rotate_ccw(tiles[source.tile_id])
        colored = apply_palette(rotated, clut[source.clut_id], prom_to_slot)
        packed = pack_graphic4(colored)
        existing = seen.get(packed)
        if existing is not None:
            warnings.append(
                f"dedupe: source ${source.tile_id:02X} {source.name} matches "
                f"tile {existing.index:02d} from source ${existing.source.tile_id:02X}"
            )
            source_to_index[source.tile_id] = existing.index
            continue

        name = source.name
        if name.startswith("maze_wall_"):
            name = f"{name}_{edge_mask(colored)}"
        tile = ConvertedTile(len(converted), TileSource(source.tile_id, source.clut_id, name), colored, packed)
        converted.append(tile)
        seen[packed] = tile
        source_to_index[source.tile_id] = tile.index

    return converted, warnings, source_to_index


def render_tile_bank_png(converted: list[ConvertedTile], slot_rgb: dict[int, tuple[int, int, int]]) -> None:
    label_height = 16
    tile_size = TILE_WIDTH * ZOOM
    cell_width = 150
    cell_height = tile_size + label_height
    columns = 3
    rows = math.ceil(len(converted) / columns)
    image = Image.new("RGB", (columns * cell_width, rows * cell_height), (18, 18, 18))
    draw = ImageDraw.Draw(image)

    for tile in converted:
        column = tile.index % columns
        row = tile.index // columns
        ox = column * cell_width
        oy = row * cell_height
        tile_image = Image.new("RGB", (TILE_WIDTH, TILE_HEIGHT), (0, 0, 0))
        pixels = tile_image.load()
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pixels[x, y] = slot_rgb[tile.pixels[y][x]]
        image.paste(tile_image.resize((tile_size, tile_size), Image.Resampling.NEAREST), (ox, oy))
        draw.text(
            (ox + tile_size + 4, oy + 1),
            f"{tile.index:02d} ${tile.source.tile_id:02X}\n{tile.source.name}",
            fill=(235, 235, 210),
        )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    image.save(TILE_BANK_PNG_PATH)


def write_index(converted: list[ConvertedTile]) -> None:
    lines = ["index | source tile | clut | name | byte offset"]
    for tile in converted:
        lines.append(
            f"{tile.index:02d} | ${tile.source.tile_id:02X} | {tile.source.clut_id:02d} | "
            f"{tile.source.name} | 0x{tile.index * TILE_BYTES:04X}"
        )

    TILE_INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def unpack_graphic4_tiles(payload: bytes) -> list[tuple[tuple[int, ...], ...]]:
    if len(payload) % TILE_BYTES != 0:
        raise RuntimeError(f"tile payload size is not a multiple of {TILE_BYTES}: {len(payload)}")

    tiles: list[tuple[tuple[int, ...], ...]] = []
    for offset in range(0, len(payload), TILE_BYTES):
        rows = []
        tile_bytes = payload[offset : offset + TILE_BYTES]
        for y in range(TILE_HEIGHT):
            row = []
            for value in tile_bytes[y * 4 : y * 4 + 4]:
                row.append(value >> 4)
                row.append(value & 0x0F)
            rows.append(tuple(row))
        tiles.append(tuple(rows))
    return tiles


def load_maze_layout(path: Path) -> list[list[str]]:
    rows = [
        line.split()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if len(rows) != ARCADE_ROWS:
        raise RuntimeError(f"{path} must contain {ARCADE_ROWS} maze rows, found {len(rows)}")
    for row_index, row in enumerate(rows):
        if len(row) != ARCADE_COLUMNS:
            raise RuntimeError(
                f"{path} row {row_index + 1} must contain {ARCADE_COLUMNS} tokens, found {len(row)}"
            )
    return rows


def rotate_arcade_layout_ccw(layout: list[list[str]]) -> list[list[str]]:
    rotated = [["00"] * ROTATED_COLUMNS for _ in range(ROTATED_ROWS)]
    for source_y, row in enumerate(layout):
        for source_x, token in enumerate(row):
            rotated[ARCADE_COLUMNS - 1 - source_x][source_y] = token
    return rotated


def render_static_maze_framebuffer(
    converted_payload: bytes,
    source_to_index: dict[int, int],
) -> bytes:
    tile_pixels = unpack_graphic4_tiles(converted_payload)
    layout = rotate_arcade_layout_ccw(load_maze_layout(MAZE_LAYOUT_PATH))

    full_width = ROTATED_COLUMNS * TILE_WIDTH
    full_height = ROTATED_ROWS * TILE_HEIGHT
    frame = [[0] * full_width for _ in range(full_height)]

    for row_index, row in enumerate(layout):
        for column_index, token in enumerate(row):
            try:
                tile_id = int(token, 16)
            except ValueError as error:
                raise RuntimeError(
                    f"{MAZE_LAYOUT_PATH} row {row_index + 1}, column {column_index + 1}: "
                    f"expected a hex tile source token, found {token!r}"
                ) from error
            try:
                tile_index = source_to_index[tile_id]
            except KeyError as error:
                raise RuntimeError(
                    f"{MAZE_LAYOUT_PATH} row {row_index + 1}, column {column_index + 1}: "
                    f"tile source ${tile_id:02X} is not present in the converted tile bank"
                ) from error

            tile = tile_pixels[tile_index]
            dest_x = column_index * TILE_WIDTH
            dest_y = row_index * TILE_HEIGHT
            for y in range(TILE_HEIGHT):
                for x in range(TILE_WIDTH):
                    frame[dest_y + y][dest_x + x] = tile[y][x]

    cropped = [
        row[MAZE_CROP_X : MAZE_CROP_X + FRAME_WIDTH]
        for row in frame[MAZE_CROP_Y : MAZE_CROP_Y + FRAME_HEIGHT]
    ]
    packed = bytearray()
    for row in cropped:
        for x in range(0, FRAME_WIDTH, 2):
            packed.append((row[x] << 4) | row[x + 1])
    return bytes(packed)


def main() -> int:
    def action() -> None:
        tile_rom = require_input("pacman.5e")
        clut_prom = require_input("82s126.4a")
        tiles = decode_tiles(tile_rom)
        clut = decode_clut(clut_prom)
        prom_to_slot = load_prom_to_slot_map(PALETTE_MAP_PATH)
        slot_rgb = load_slot_rgb(PALETTE_MAP_PATH)
        converted, warnings, source_to_index = convert_tiles(tiles, clut, prom_to_slot)

        payload = b"".join(tile.packed for tile in converted)
        framebuffer = render_static_maze_framebuffer(payload, source_to_index)
        tiles_path = write_output("tiles_vdpb.bin", payload)
        nametable_path = write_output("tile_nametable.bin", framebuffer)
        write_index(converted)
        render_tile_bank_png(converted, slot_rgb)

        print(f"conv_tiles: total source tiles decoded: {len(tiles)}")
        print(f"conv_tiles: audited source references: {len(make_tile_sources())}")
        print(f"conv_tiles: unique maze tiles kept: {len(converted)}")
        print(f"conv_tiles: bytes written: {len(payload)}")
        print(f"conv_tiles: static maze framebuffer bytes: {len(framebuffer)}")
        print(
            "conv_tiles: "
            f"{len(payload)} + {len(framebuffer)} bytes written to "
            f"{asset_relpath(tiles_path)}, {asset_relpath(nametable_path)}"
        )
        print(f"conv_tiles: index written to {asset_relpath(TILE_INDEX_PATH)}")
        print(f"conv_tiles: evidence PNG written to {TILE_BANK_PNG_PATH.relative_to(REPO_ROOT)}")
        for warning in warnings:
            print(f"conv_tiles warning: {warning}")

    return run_tool("conv_tiles", action)


if __name__ == "__main__":
    raise SystemExit(main())
