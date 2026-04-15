#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib
from collections import Counter
from dataclasses import dataclass


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ROM_PATH = REPO_ROOT / "pacman" / "pacman.5e"
DEFAULT_ASSET_PATH = REPO_ROOT / "assets" / "tiles_vdpb.bin"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "assets" / "tiles_manifest.txt"
DEFAULT_SUMMARY_PATH = REPO_ROOT / "assets" / "tiles_summary.txt"

TILE_COUNT = 256
SOURCE_BYTES_PER_TILE = 16
OUTPUT_BYTES_PER_TILE = 32
TILE_SIZE = 8
EXPECTED_ROM_SIZE = TILE_COUNT * SOURCE_BYTES_PER_TILE


@dataclass(frozen=True)
class TileMetadata:
    tile_id: int
    classification: str
    nonzero_pixels: int
    colors: tuple[int, ...]
    bbox: tuple[int, int, int, int] | None
    row_mask: str
    sha256: str


def decode_tile(tile_bytes: bytes) -> list[list[int]]:
    if len(tile_bytes) != SOURCE_BYTES_PER_TILE:
        raise ValueError(f"Expected {SOURCE_BYTES_PER_TILE} bytes per tile.")

    pixels = [[0 for _ in range(TILE_SIZE)] for _ in range(TILE_SIZE)]

    for y in range(TILE_SIZE):
        right_half = tile_bytes[y]
        left_half = tile_bytes[8 + y]

        for x in range(4):
            low = (left_half >> x) & 0x01
            high = (left_half >> (x + 4)) & 0x01
            pixels[y][x] = low | (high << 1)

        for x in range(4):
            low = (right_half >> x) & 0x01
            high = (right_half >> (x + 4)) & 0x01
            pixels[y][x + 4] = low | (high << 1)

    return pixels


def pack_graphic4_tile(pixels: list[list[int]]) -> bytes:
    packed = bytearray()

    for row in pixels:
        if len(row) != TILE_SIZE:
            raise ValueError("Tile row width is not 8 pixels.")

        for x in range(0, TILE_SIZE, 2):
            left = row[x] & 0x0F
            right = row[x + 1] & 0x0F
            packed.append((left << 4) | right)

    if len(packed) != OUTPUT_BYTES_PER_TILE:
        raise ValueError("Graphic 4 tile output had unexpected size.")

    return bytes(packed)


def tile_bbox(pixels: list[list[int]]) -> tuple[int, int, int, int] | None:
    coordinates = [
        (x, y)
        for y, row in enumerate(pixels)
        for x, value in enumerate(row)
        if value != 0
    ]
    if not coordinates:
        return None

    xs = [x for x, _ in coordinates]
    ys = [y for _, y in coordinates]
    return min(xs), min(ys), max(xs), max(ys)


def classify_tile(pixels: list[list[int]], bbox: tuple[int, int, int, int] | None) -> str:
    nonzero_pixels = sum(1 for row in pixels for value in row if value != 0)
    if nonzero_pixels == 0:
        return "blank"

    if bbox is None:
        raise ValueError("Non-blank tile without a bounding box.")

    x0, y0, x1, y1 = bbox
    width = x1 - x0 + 1
    height = y1 - y0 + 1
    touches_edge_count = sum((x0 == 0, y0 == 0, x1 == TILE_SIZE - 1, y1 == TILE_SIZE - 1))

    if nonzero_pixels <= 8 and height <= 4:
        return "pellet"

    if set(value for row in pixels for value in row) <= {0, 1} and nonzero_pixels >= 32:
        return "energizer"

    if touches_edge_count >= 2 and nonzero_pixels >= 12:
        return "wall"

    if nonzero_pixels >= 24 and width >= 6 and height >= 6 and touches_edge_count <= 1:
        return "fruit_icon"

    return "text_character"


def row_mask(pixels: list[list[int]]) -> str:
    rows: list[str] = []
    for row in pixels:
        mask = 0
        for x, value in enumerate(row):
            if value != 0:
                mask |= 1 << (TILE_SIZE - 1 - x)
        rows.append(f"{mask:02X}")
    return " ".join(rows)


def metadata_for_tile(tile_id: int, pixels: list[list[int]], packed: bytes) -> TileMetadata:
    bbox = tile_bbox(pixels)
    colors = tuple(sorted({value for row in pixels for value in row}))
    return TileMetadata(
        tile_id=tile_id,
        classification=classify_tile(pixels, bbox),
        nonzero_pixels=sum(1 for row in pixels for value in row if value != 0),
        colors=colors,
        bbox=bbox,
        row_mask=row_mask(pixels),
        sha256=hashlib.sha256(packed).hexdigest(),
    )


def decode_tiles(rom_data: bytes) -> tuple[bytes, list[TileMetadata]]:
    if len(rom_data) != EXPECTED_ROM_SIZE:
        raise ValueError(
            f"{DEFAULT_ROM_PATH.relative_to(REPO_ROOT)} must be {EXPECTED_ROM_SIZE} bytes; "
            f"got {len(rom_data)} bytes."
        )

    output = bytearray()
    manifest: list[TileMetadata] = []

    for tile_id in range(TILE_COUNT):
        start = tile_id * SOURCE_BYTES_PER_TILE
        tile_bytes = rom_data[start : start + SOURCE_BYTES_PER_TILE]
        pixels = decode_tile(tile_bytes)
        packed = pack_graphic4_tile(pixels)
        output.extend(packed)
        manifest.append(metadata_for_tile(tile_id, pixels, packed))

    return bytes(output), manifest


def write_manifest(path: pathlib.Path, manifest: list[TileMetadata]) -> None:
    lines = [
        "# Pac-Man character ROM tile manifest",
        "# columns: tile_id class nonzero_pixels colors bbox row_mask sha256",
    ]

    for item in manifest:
        colors = ",".join(str(color) for color in item.colors)
        bbox = "none" if item.bbox is None else ",".join(str(part) for part in item.bbox)
        lines.append(
            f"{item.tile_id:03d} {item.classification:<14} "
            f"{item.nonzero_pixels:02d} {colors:<7} {bbox:<9} "
            f"{item.row_mask} {item.sha256}"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    path: pathlib.Path,
    rom_data: bytes,
    tile_data: bytes,
    manifest: list[TileMetadata],
    rom_path: pathlib.Path,
    asset_path: pathlib.Path,
    manifest_path: pathlib.Path,
) -> None:
    class_counts = Counter(item.classification for item in manifest)
    lines = [
        "Pac-Man character tile extraction summary",
        f"Source ROM: {rom_path.relative_to(REPO_ROOT)}",
        f"Source ROM bytes: {len(rom_data)}",
        f"Source ROM SHA-256: {hashlib.sha256(rom_data).hexdigest()}",
        f"Output tile bank: {asset_path.relative_to(REPO_ROOT)}",
        f"Output tile bank bytes: {len(tile_data)}",
        f"Output tile bank SHA-256: {hashlib.sha256(tile_data).hexdigest()}",
        f"Manifest: {manifest_path.relative_to(REPO_ROOT)}",
        f"Manifest tile rows: {len(manifest)}",
        "Classification counts:",
    ]

    for classification in (
        "blank",
        "pellet",
        "energizer",
        "wall",
        "text_character",
        "fruit_icon",
    ):
        lines.append(f"  {classification}: {class_counts[classification]}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode pacman.5e character ROM into Vanguard 8 Graphic 4 tile data."
    )
    parser.add_argument("--rom", type=pathlib.Path, default=DEFAULT_ROM_PATH)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_ASSET_PATH)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--summary", type=pathlib.Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rom_path = args.rom.resolve()
    asset_path = args.out.resolve()
    manifest_path = args.manifest.resolve()
    summary_path = args.summary.resolve()

    rom_data = rom_path.read_bytes()
    tile_data, manifest = decode_tiles(rom_data)

    asset_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    asset_path.write_bytes(tile_data)
    write_manifest(manifest_path, manifest)
    write_summary(summary_path, rom_data, tile_data, manifest, rom_path, asset_path, manifest_path)

    print(f"Read {len(rom_data)} bytes from {rom_path.relative_to(REPO_ROOT)}")
    print(f"Decoded {len(manifest)} tiles")
    print(f"Wrote {len(tile_data)} bytes to {asset_path.relative_to(REPO_ROOT)}")
    print(f"Wrote manifest to {manifest_path.relative_to(REPO_ROOT)}")
    print(f"Wrote summary to {summary_path.relative_to(REPO_ROOT)}")
    print(f"Output SHA-256: {hashlib.sha256(tile_data).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
