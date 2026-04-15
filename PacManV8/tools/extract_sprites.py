#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib
from collections import Counter
from dataclasses import dataclass


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ROM_PATH = REPO_ROOT / "pacman" / "pacman.5f"
DEFAULT_PATTERN_PATH = REPO_ROOT / "assets" / "sprites.bin"
DEFAULT_COLOR_PATH = REPO_ROOT / "assets" / "sprite_colors.bin"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "assets" / "sprites_manifest.txt"
DEFAULT_SUMMARY_PATH = REPO_ROOT / "assets" / "sprites_summary.txt"

SPRITE_COUNT = 64
SOURCE_BYTES_PER_SPRITE = 64
PATTERN_BYTES_PER_SPRITE = 32
COLOR_BYTES_PER_SPRITE = 16
SPRITE_SIZE = 16
EXPECTED_ROM_SIZE = SPRITE_COUNT * SOURCE_BYTES_PER_SPRITE

X_BIT_OFFSETS = (
    8 * 8 + 0,
    8 * 8 + 1,
    8 * 8 + 2,
    8 * 8 + 3,
    16 * 8 + 0,
    16 * 8 + 1,
    16 * 8 + 2,
    16 * 8 + 3,
    24 * 8 + 0,
    24 * 8 + 1,
    24 * 8 + 2,
    24 * 8 + 3,
    0,
    1,
    2,
    3,
)
Y_BIT_OFFSETS = (
    0 * 8,
    1 * 8,
    2 * 8,
    3 * 8,
    4 * 8,
    5 * 8,
    6 * 8,
    7 * 8,
    32 * 8,
    33 * 8,
    34 * 8,
    35 * 8,
    36 * 8,
    37 * 8,
    38 * 8,
    39 * 8,
)


@dataclass(frozen=True)
class SpriteMetadata:
    sprite_id: int
    nonzero_pixels: int
    colors: tuple[int, ...]
    bbox: tuple[int, int, int, int] | None
    blank_rows: int
    multicolor_rows: int
    row_colors: tuple[int, ...]
    row_mask: str
    pattern_sha256: str
    color_sha256: str


def read_bit(data: bytes, bit_offset: int) -> int:
    byte_index = bit_offset // 8
    bit_index = bit_offset % 8
    return (data[byte_index] >> bit_index) & 0x01


def decode_sprite(sprite_bytes: bytes) -> list[list[int]]:
    if len(sprite_bytes) != SOURCE_BYTES_PER_SPRITE:
        raise ValueError(f"Expected {SOURCE_BYTES_PER_SPRITE} bytes per sprite.")

    pixels = [[0 for _ in range(SPRITE_SIZE)] for _ in range(SPRITE_SIZE)]

    for y in range(SPRITE_SIZE):
        for x in range(SPRITE_SIZE):
            base_offset = Y_BIT_OFFSETS[y] + X_BIT_OFFSETS[x]
            low = read_bit(sprite_bytes, base_offset)
            high = read_bit(sprite_bytes, base_offset + 4)
            pixels[y][x] = low | (high << 1)

    return pixels


def pack_mode2_pattern(pixels: list[list[int]]) -> bytes:
    row_pairs: list[tuple[int, int]] = []

    for row in pixels:
        if len(row) != SPRITE_SIZE:
            raise ValueError("Sprite row width is not 16 pixels.")

        left_byte = 0
        right_byte = 0
        for x in range(8):
            if row[x] != 0:
                left_byte |= 1 << (7 - x)
        for x in range(8, 16):
            if row[x] != 0:
                right_byte |= 1 << (15 - x)

        row_pairs.append((left_byte, right_byte))

    packed = bytearray()
    packed.extend(left for left, _ in row_pairs[:8])
    packed.extend(right for _, right in row_pairs[:8])
    packed.extend(left for left, _ in row_pairs[8:])
    packed.extend(right for _, right in row_pairs[8:])

    if len(packed) != PATTERN_BYTES_PER_SPRITE:
        raise ValueError("Sprite Mode 2 pattern output had unexpected size.")

    return bytes(packed)


def dominant_row_color(row: list[int]) -> int:
    counts = Counter(value for value in row if value != 0)
    if not counts:
        return 0

    return min(
        counts,
        key=lambda color: (-counts[color], color),
    )


def pack_mode2_colors(pixels: list[list[int]]) -> tuple[bytes, tuple[int, ...], int, int]:
    row_colors: list[int] = []
    blank_rows = 0
    multicolor_rows = 0

    for row in pixels:
        nonzero_colors = {value for value in row if value != 0}
        if not nonzero_colors:
            blank_rows += 1
        elif len(nonzero_colors) > 1:
            multicolor_rows += 1
        row_colors.append(dominant_row_color(row))

    if len(row_colors) != COLOR_BYTES_PER_SPRITE:
        raise ValueError("Sprite Mode 2 color output had unexpected size.")

    return bytes(row_colors), tuple(row_colors), blank_rows, multicolor_rows


def sprite_bbox(pixels: list[list[int]]) -> tuple[int, int, int, int] | None:
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


def sprite_row_mask(pixels: list[list[int]]) -> str:
    rows: list[str] = []
    for row in pixels:
        mask = 0
        for x, value in enumerate(row):
            if value != 0:
                mask |= 1 << (SPRITE_SIZE - 1 - x)
        rows.append(f"{mask:04X}")
    return " ".join(rows)


def metadata_for_sprite(
    sprite_id: int,
    pixels: list[list[int]],
    pattern: bytes,
    colors: bytes,
    row_colors: tuple[int, ...],
    blank_rows: int,
    multicolor_rows: int,
) -> SpriteMetadata:
    return SpriteMetadata(
        sprite_id=sprite_id,
        nonzero_pixels=sum(1 for row in pixels for value in row if value != 0),
        colors=tuple(sorted({value for row in pixels for value in row})),
        bbox=sprite_bbox(pixels),
        blank_rows=blank_rows,
        multicolor_rows=multicolor_rows,
        row_colors=row_colors,
        row_mask=sprite_row_mask(pixels),
        pattern_sha256=hashlib.sha256(pattern).hexdigest(),
        color_sha256=hashlib.sha256(colors).hexdigest(),
    )


def decode_sprites(rom_data: bytes) -> tuple[bytes, bytes, list[SpriteMetadata]]:
    if len(rom_data) != EXPECTED_ROM_SIZE:
        raise ValueError(
            f"{DEFAULT_ROM_PATH.relative_to(REPO_ROOT)} must be {EXPECTED_ROM_SIZE} bytes; "
            f"got {len(rom_data)} bytes."
        )

    patterns = bytearray()
    color_rows = bytearray()
    manifest: list[SpriteMetadata] = []

    for sprite_id in range(SPRITE_COUNT):
        start = sprite_id * SOURCE_BYTES_PER_SPRITE
        sprite_bytes = rom_data[start : start + SOURCE_BYTES_PER_SPRITE]
        pixels = decode_sprite(sprite_bytes)
        pattern = pack_mode2_pattern(pixels)
        colors, row_colors, blank_rows, multicolor_rows = pack_mode2_colors(pixels)

        patterns.extend(pattern)
        color_rows.extend(colors)
        manifest.append(
            metadata_for_sprite(
                sprite_id,
                pixels,
                pattern,
                colors,
                row_colors,
                blank_rows,
                multicolor_rows,
            )
        )

    return bytes(patterns), bytes(color_rows), manifest


def write_manifest(path: pathlib.Path, manifest: list[SpriteMetadata]) -> None:
    lines = [
        "# Pac-Man sprite ROM manifest",
        "# columns: sprite_id nonzero_pixels colors bbox blank_rows "
        "multicolor_rows row_colors row_mask pattern_sha256 color_sha256",
    ]

    for item in manifest:
        colors = ",".join(str(color) for color in item.colors)
        bbox = "none" if item.bbox is None else ",".join(str(part) for part in item.bbox)
        row_colors = ",".join(f"{color:X}" for color in item.row_colors)
        lines.append(
            f"{item.sprite_id:02d} {item.nonzero_pixels:03d} {colors:<7} "
            f"{bbox:<11} {item.blank_rows:02d} {item.multicolor_rows:02d} "
            f"{row_colors:<31} {item.row_mask} "
            f"{item.pattern_sha256} {item.color_sha256}"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    path: pathlib.Path,
    rom_data: bytes,
    pattern_data: bytes,
    color_data: bytes,
    manifest: list[SpriteMetadata],
    rom_path: pathlib.Path,
    pattern_path: pathlib.Path,
    color_path: pathlib.Path,
    manifest_path: pathlib.Path,
) -> None:
    row_color_counts = Counter(color for item in manifest for color in item.row_colors)
    lines = [
        "Pac-Man sprite extraction summary",
        f"Source ROM: {rom_path.relative_to(REPO_ROOT)}",
        f"Source ROM bytes: {len(rom_data)}",
        f"Source ROM SHA-256: {hashlib.sha256(rom_data).hexdigest()}",
        f"Output pattern bank: {pattern_path.relative_to(REPO_ROOT)}",
        f"Output pattern bank bytes: {len(pattern_data)}",
        f"Output pattern bank SHA-256: {hashlib.sha256(pattern_data).hexdigest()}",
        f"Output color table: {color_path.relative_to(REPO_ROOT)}",
        f"Output color table bytes: {len(color_data)}",
        f"Output color table SHA-256: {hashlib.sha256(color_data).hexdigest()}",
        f"Manifest: {manifest_path.relative_to(REPO_ROOT)}",
        f"Manifest sprite rows: {len(manifest)}",
        f"Total opaque pixels: {sum(item.nonzero_pixels for item in manifest)}",
        f"Blank sprites: {sum(1 for item in manifest if item.nonzero_pixels == 0)}",
        f"Blank sprite rows: {sum(item.blank_rows for item in manifest)}",
        f"Rows with multiple non-transparent colors: {sum(item.multicolor_rows for item in manifest)}",
        "Dominant row color counts:",
    ]

    for color in range(4):
        lines.append(f"  {color}: {row_color_counts[color]}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode pacman.5f sprite ROM into Vanguard 8 Sprite Mode 2 data."
    )
    parser.add_argument("--rom", type=pathlib.Path, default=DEFAULT_ROM_PATH)
    parser.add_argument("--patterns", type=pathlib.Path, default=DEFAULT_PATTERN_PATH)
    parser.add_argument("--colors", type=pathlib.Path, default=DEFAULT_COLOR_PATH)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--summary", type=pathlib.Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rom_path = args.rom.resolve()
    pattern_path = args.patterns.resolve()
    color_path = args.colors.resolve()
    manifest_path = args.manifest.resolve()
    summary_path = args.summary.resolve()

    rom_data = rom_path.read_bytes()
    pattern_data, color_data, manifest = decode_sprites(rom_data)

    pattern_path.parent.mkdir(parents=True, exist_ok=True)
    color_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    pattern_path.write_bytes(pattern_data)
    color_path.write_bytes(color_data)
    write_manifest(manifest_path, manifest)
    write_summary(
        summary_path,
        rom_data,
        pattern_data,
        color_data,
        manifest,
        rom_path,
        pattern_path,
        color_path,
        manifest_path,
    )

    print(f"Read {len(rom_data)} bytes from {rom_path.relative_to(REPO_ROOT)}")
    print(f"Decoded {len(manifest)} sprites")
    print(f"Wrote {len(pattern_data)} pattern bytes to {pattern_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(color_data)} color bytes to {color_path.relative_to(REPO_ROOT)}")
    print(f"Wrote manifest to {manifest_path.relative_to(REPO_ROOT)}")
    print(f"Wrote summary to {summary_path.relative_to(REPO_ROOT)}")
    print(f"Pattern SHA-256: {hashlib.sha256(pattern_data).hexdigest()}")
    print(f"Color SHA-256: {hashlib.sha256(color_data).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
