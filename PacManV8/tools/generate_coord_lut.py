#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib

import coordinate_transform as transform


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "assets" / "coord_lut.bin"
SUMMARY_PATH = REPO_ROOT / "assets" / "coord_lut_summary.txt"

X_TABLE_BYTES = transform.ARCADE_MAZE_WIDTH_PX
Y_TABLE_BYTES = 256
Y_THRESHOLD_BYTES = 256
LUT_BYTES = X_TABLE_BYTES + Y_TABLE_BYTES + Y_THRESHOLD_BYTES
FRACTION_THRESHOLD_NEVER = 0x00
HIDDEN_SPRITE_Y = 0xD0


def build_x_table(coordmap: bytes) -> bytes:
    values = bytearray()
    for x_px in range(transform.ARCADE_MAZE_WIDTH_PX):
        result = transform.transform_entity(coordmap, x_px << 8, transform.fixed_tile_center(transform.MAZE_TOP))
        values.append(result.sprite_x & 0xFF)
    return bytes(values)


def wrapped_arcade_y_from_byte(y_px_byte: int) -> int:
    wrapped_mapped_pixels = (
        transform.MAZE_TOP + transform.MAZE_ROWS
    ) * transform.ARCADE_TILE_SIZE - 256
    if y_px_byte < wrapped_mapped_pixels:
        return y_px_byte + 256
    return y_px_byte


def build_y_tables(coordmap: bytes) -> tuple[bytes, bytes]:
    y_base = bytearray()
    y_threshold = bytearray()

    for y_px_byte in range(256):
        arcade_y_px = wrapped_arcade_y_from_byte(y_px_byte)
        tile_y = arcade_y_px // transform.ARCADE_TILE_SIZE
        if not (0 <= tile_y < transform.ARCADE_HEIGHT):
            y_base.append(HIDDEN_SPRITE_Y)
            y_threshold.append(FRACTION_THRESHOLD_NEVER)
            continue

        cell = transform.record_at(coordmap, 0, tile_y)
        if not cell.mapped:
            y_base.append(HIDDEN_SPRITE_Y)
            y_threshold.append(FRACTION_THRESHOLD_NEVER)
            continue

        within_px = arcade_y_px - tile_y * transform.ARCADE_TILE_SIZE
        base_scaled = (within_px * cell.height) // transform.ARCADE_TILE_SIZE
        y_base.append((cell.y + base_scaled - transform.SPRITE_ANCHOR_OFFSET) & 0xFF)

        remainder = (within_px * cell.height) % transform.ARCADE_TILE_SIZE
        if remainder == 0:
            y_threshold.append(FRACTION_THRESHOLD_NEVER)
            continue

        threshold = ((transform.ARCADE_TILE_SIZE - remainder) << 8) + cell.height - 1
        threshold //= cell.height
        if threshold > 0xFF:
            y_threshold.append(FRACTION_THRESHOLD_NEVER)
        else:
            y_threshold.append(threshold)

    return bytes(y_base), bytes(y_threshold)


def build_lut(coordmap: bytes) -> bytes:
    x_table = build_x_table(coordmap)
    y_base, y_threshold = build_y_tables(coordmap)
    lut = x_table + y_base + y_threshold
    if len(lut) != LUT_BYTES:
        raise ValueError(f"coord LUT must be {LUT_BYTES} bytes; got {len(lut)}.")
    return lut


def write_summary(path: pathlib.Path, coordmap: bytes, lut: bytes) -> None:
    x_table = lut[:X_TABLE_BYTES]
    y_base = lut[X_TABLE_BYTES : X_TABLE_BYTES + Y_TABLE_BYTES]
    y_threshold = lut[X_TABLE_BYTES + Y_TABLE_BYTES :]
    lines = [
        "T026 runtime coordinate transform LUT",
        "",
        f"coordmap: assets/maze_v8_coordmap.bin bytes={len(coordmap)} sha256={hashlib.sha256(coordmap).hexdigest()}",
        f"coord_lut: assets/coord_lut.bin bytes={len(lut)} sha256={hashlib.sha256(lut).hexdigest()}",
        f"x_table: offset=0 bytes={len(x_table)} input=arcade X high byte after modulo 224 output=SAT X",
        f"y_base: offset={X_TABLE_BYTES} bytes={len(y_base)} input=arcade Y high byte modulo 256 output=SAT Y base",
        f"y_threshold: offset={X_TABLE_BYTES + Y_TABLE_BYTES} bytes={len(y_threshold)} input=arcade Y high byte modulo 256 output=fractional carry threshold",
        "unmapped_y: 0xD0 Sprite Mode 2 terminator Y",
        "wrapped_y: high-byte values 0x00-0x0F map to arcade pixels 256-271 for rows 32-33; rows 0-2 are unmapped.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate runtime arcade-to-V8 coordinate transform LUT.")
    parser.add_argument("--output", type=pathlib.Path, default=OUTPUT_PATH)
    parser.add_argument("--summary-output", type=pathlib.Path, default=SUMMARY_PATH)
    args = parser.parse_args()

    coordmap = transform.load_coordmap()
    lut = build_lut(coordmap)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(lut)
    write_summary(args.summary_output, coordmap, lut)

    print(f"coord_lut bytes: {len(lut)}")
    print(f"coord_lut SHA-256: {hashlib.sha256(lut).hexdigest()}")
    print(f"summary: {args.summary_output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
