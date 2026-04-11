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
EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T005-tiles"
TILE_BANK_PNG_PATH = EVIDENCE_DIR / "tile_bank.png"

TILE_WIDTH = 8
TILE_HEIGHT = 8
TILE_BYTES = 32
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


def get_bit(data: bytes, bit_offset: int) -> int:
    return (data[bit_offset >> 3] >> (7 - (bit_offset & 7))) & 1


def decode_tiles(rom: bytes) -> list[list[list[int]]]:
    plane_offsets = (0, 4)
    x_offsets = (8 * 8 + 0, 8 * 8 + 1, 8 * 8 + 2, 8 * 8 + 3, 0, 1, 2, 3)
    y_offsets = tuple(i * 8 for i in range(TILE_HEIGHT))
    char_inc = 16 * 8
    count = (len(rom) * 8) // char_inc
    tiles: list[list[list[int]]] = []

    for tile_id in range(count):
        base = tile_id * char_inc
        tile = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pixel = 0
                for plane, plane_offset in enumerate(plane_offsets):
                    pixel |= (
                        get_bit(rom, base + y_offsets[y] + x_offsets[x] + plane_offset)
                        << plane
                    )
                tile[y][x] = pixel
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
            rotated[x][7 - y] = tile[y][x]
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
) -> tuple[list[ConvertedTile], list[str]]:
    converted: list[ConvertedTile] = []
    warnings: list[str] = []
    seen: dict[bytes, ConvertedTile] = {}

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
            continue

        name = source.name
        if name.startswith("maze_wall_"):
            name = f"{name}_{edge_mask(colored)}"
        tile = ConvertedTile(len(converted), TileSource(source.tile_id, source.clut_id, name), colored, packed)
        converted.append(tile)
        seen[packed] = tile

    return converted, warnings


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


def main() -> int:
    def action() -> None:
        tile_rom = require_input("pacman.5e")
        clut_prom = require_input("82s126.4a")
        tiles = decode_tiles(tile_rom)
        clut = decode_clut(clut_prom)
        prom_to_slot = load_prom_to_slot_map(PALETTE_MAP_PATH)
        slot_rgb = load_slot_rgb(PALETTE_MAP_PATH)
        converted, warnings = convert_tiles(tiles, clut, prom_to_slot)

        payload = b"".join(tile.packed for tile in converted)
        tiles_path = write_output("tiles_vdpb.bin", payload)
        nametable_path = write_output("tile_nametable.bin", b"")
        write_index(converted)
        render_tile_bank_png(converted, slot_rgb)

        print(f"conv_tiles: total source tiles decoded: {len(tiles)}")
        print(f"conv_tiles: audited source references: {len(make_tile_sources())}")
        print(f"conv_tiles: unique maze tiles kept: {len(converted)}")
        print(f"conv_tiles: bytes written: {len(payload)}")
        print(
            "conv_tiles: "
            f"{len(payload)} + 0 bytes written to {asset_relpath(tiles_path)}, "
            f"{asset_relpath(nametable_path)}"
        )
        print(f"conv_tiles: index written to {asset_relpath(TILE_INDEX_PATH)}")
        print(f"conv_tiles: evidence PNG written to {TILE_BANK_PNG_PATH.relative_to(REPO_ROOT)}")
        for warning in warnings:
            print(f"conv_tiles warning: {warning}")

    return run_tool("conv_tiles", action)


if __name__ == "__main__":
    raise SystemExit(main())
