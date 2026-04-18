#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HUD_TILES_PATH = REPO_ROOT / "assets" / "hud_tiles.bin"
HUD_PATCH_PATH = REPO_ROOT / "assets" / "hud_patch.bin"
HUD_SUMMARY_PATH = REPO_ROOT / "assets" / "hud_assets_summary.txt"
HUD_DRAW_INCLUDE_PATH = REPO_ROOT / "src" / "hud_review_draw.inc"

ATLAS_TILES = 32
TILE_SIZE = 8
TILE_BYTES = 32
ATLAS_ROW_BYTES = 128
ATLAS_BYTES = ATLAS_ROW_BYTES * TILE_SIZE
PATCH_BAND_BYTES = ATLAS_ROW_BYTES * TILE_SIZE
PATCH_BYTES = PATCH_BAND_BYTES * 2
HUD_SOURCE_Y = 212
TOP_ROW_Y = 0
BOTTOM_ROW_Y = 204

COLOR_TRANSPARENT = 0
COLOR_TEXT = 6
COLOR_SCORE = 1
COLOR_YELLOW = 1
COLOR_RED = 2
COLOR_PINK = 3
COLOR_GREEN = 13
COLOR_ORANGE = 15

FONT_5X7 = {
    "0": ["11111", "10001", "10011", "10101", "11001", "10001", "11111"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["11110", "00001", "00001", "11110", "10000", "10000", "11111"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
}

TOP_SEQUENCE = "1UP 000120 HIGH SCORE 001000 2UP"
BOTTOM_SEQUENCE = "LIVES  @@@       FRUIT  #$%     "


def glyph_pixels(pattern: list[str], color: int) -> list[list[int]]:
    pixels = [[COLOR_TRANSPARENT for _ in range(TILE_SIZE)] for _ in range(TILE_SIZE)]
    for y, row in enumerate(pattern, start=0):
        for x, bit in enumerate(row, start=1):
            if bit == "1":
                pixels[y][x] = color
    return pixels


def pacman_life_icon() -> list[list[int]]:
    pattern = [
        "00111100",
        "01111110",
        "11111000",
        "11100000",
        "11111000",
        "01111110",
        "00111100",
        "00000000",
    ]
    return [[COLOR_YELLOW if char == "1" else 0 for char in row] for row in pattern]


def cherry_icon() -> list[list[int]]:
    rows = [
        "0000G000",
        "000G0000",
        "00G00000",
        "0R0R0000",
        "RRRR0000",
        "RRRR0000",
        "0R0R0000",
        "00000000",
    ]
    return icon_from_rows(rows)


def strawberry_icon() -> list[list[int]]:
    rows = [
        "00GG0000",
        "0GRRG000",
        "RRRRRR00",
        "RPRRPR00",
        "RRPRRR00",
        "0RRRR000",
        "00RR0000",
        "00000000",
    ]
    return icon_from_rows(rows)


def orange_icon() -> list[list[int]]:
    rows = [
        "000G0000",
        "00GOO000",
        "0OOOOO00",
        "OOOOOO00",
        "OOOOOO00",
        "0OOOOO00",
        "00OO0000",
        "00000000",
    ]
    return icon_from_rows(rows)


def icon_from_rows(rows: list[str]) -> list[list[int]]:
    color_by_char = {
        "0": COLOR_TRANSPARENT,
        "R": COLOR_RED,
        "P": COLOR_PINK,
        "G": COLOR_GREEN,
        "O": COLOR_ORANGE,
    }
    return [[color_by_char[char] for char in row] for row in rows]


def pack_tile(pixels: list[list[int]]) -> bytes:
    packed = bytearray()
    for row in pixels:
        if len(row) != TILE_SIZE:
            raise ValueError("HUD tile row width must be 8 pixels.")
        for x in range(0, TILE_SIZE, 2):
            packed.append(((row[x] & 0x0F) << 4) | (row[x + 1] & 0x0F))
    if len(packed) != TILE_BYTES:
        raise ValueError(f"HUD tile packed to {len(packed)} bytes, expected {TILE_BYTES}.")
    return bytes(packed)


def collect_tiles() -> tuple[dict[str, int], list[tuple[str, bytes]]]:
    tiles: list[tuple[str, bytes]] = []
    index_by_key: dict[str, int] = {}

    def add(key: str, pixels: list[list[int]]) -> None:
        if key in index_by_key:
            return
        if len(tiles) >= ATLAS_TILES:
            raise ValueError("HUD atlas exceeded one 32-tile row.")
        index_by_key[key] = len(tiles)
        tiles.append((key, pack_tile(pixels)))

    add("SPACE", [[0 for _ in range(TILE_SIZE)] for _ in range(TILE_SIZE)])

    for char in sorted(set(TOP_SEQUENCE + BOTTOM_SEQUENCE)):
        if char == " ":
            continue
        if char.isdigit():
            add(f"LABEL_{char}", glyph_pixels(FONT_5X7[char], COLOR_TEXT))
            add(f"SCORE_{char}", glyph_pixels(FONT_5X7[char], COLOR_SCORE))
        elif char.isalpha():
            add(f"LABEL_{char}", glyph_pixels(FONT_5X7[char], COLOR_TEXT))

    add("ICON_LIFE", pacman_life_icon())
    add("ICON_CHERRY", cherry_icon())
    add("ICON_STRAWBERRY", strawberry_icon())
    add("ICON_ORANGE", orange_icon())
    return index_by_key, tiles


def token_key(char: str, *, score_digit: bool) -> str:
    if char == " ":
        return "SPACE"
    if char == "@":
        return "ICON_LIFE"
    if char == "#":
        return "ICON_CHERRY"
    if char == "$":
        return "ICON_STRAWBERRY"
    if char == "%":
        return "ICON_ORANGE"
    if char.isdigit() and score_digit:
        return f"SCORE_{char}"
    if char.isdigit() or char.isalpha():
        return f"LABEL_{char}"
    raise ValueError(f"Unsupported HUD token {char!r}")


def top_score_columns() -> set[int]:
    columns: set[int] = set()
    for start, length in ((4, 6), (22, 6)):
        columns.update(range(start, start + length))
    return columns


def sequence_entries(sequence: str, y: int, index_by_key: dict[str, int]) -> list[dict[str, int | str]]:
    if len(sequence) != 32:
        raise ValueError(f"HUD row must be exactly 32 tiles; got {len(sequence)}")
    score_columns = top_score_columns() if y == TOP_ROW_Y else set()
    entries: list[dict[str, int | str]] = []
    for col, char in enumerate(sequence):
        key = token_key(char, score_digit=col in score_columns)
        tile_index = index_by_key[key]
        if key == "SPACE":
            continue
        entries.append(
            {
                "col": col,
                "x": col * 8,
                "y": y,
                "char": char,
                "key": key,
                "tile": tile_index,
            }
        )
    return entries


def build_atlas(tiles: list[tuple[str, bytes]]) -> bytes:
    atlas = bytearray([0] * ATLAS_BYTES)
    for tile_index, (_key, tile_bytes) in enumerate(tiles):
        tile_x = tile_index * 4
        for row in range(TILE_SIZE):
            src = row * 4
            dst = row * ATLAS_ROW_BYTES + tile_x
            atlas[dst : dst + 4] = tile_bytes[src : src + 4]
    return bytes(atlas)


def build_patch(tiles: list[tuple[str, bytes]], entries: list[dict[str, int | str]]) -> bytes:
    patch = bytearray([0] * PATCH_BYTES)
    for entry in entries:
        tile_bytes = tiles[int(entry["tile"])][1]
        band_base = 0 if int(entry["y"]) == TOP_ROW_Y else PATCH_BAND_BYTES
        x_byte = int(entry["col"]) * 4
        for row in range(TILE_SIZE):
            src = row * 4
            dst = band_base + row * ATLAS_ROW_BYTES + x_byte
            patch[dst : dst + 4] = tile_bytes[src : src + 4]
    return bytes(patch)


def write_draw_include(path: pathlib.Path, entries: list[dict[str, int | str]]) -> None:
    lines = [
        "; Generated by tools/generate_hud_assets.py.",
        "; Source: deterministic T014 HUD strings and built-in 5x7/icon pixel maps.",
        "",
    ]
    for entry in entries:
        lines.append(
            f"        HUD_PATCH_TILE 0x{int(entry['tile']):02X}, "
            f"0x{int(entry['x']):02X}, 0x{int(entry['y']):02X} "
            f"; {entry['key']} col={entry['col']} token={entry['char']}"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="ascii")


def write_summary(
    path: pathlib.Path,
    atlas: bytes,
    patch: bytes,
    tiles: list[tuple[str, bytes]],
    entries: list[dict[str, int | str]],
) -> None:
    lines = [
        "T014 HUD asset summary",
        f"Atlas: assets/hud_tiles.bin bytes={len(atlas)} sha256={hashlib.sha256(atlas).hexdigest()}",
        f"Patch: assets/hud_patch.bin bytes={len(patch)} sha256={hashlib.sha256(patch).hexdigest()}",
        "Patch placement: VDP-A framebuffer top band 0x0000 and bottom band 0x6600",
        f"Reference atlas layout: source_y={HUD_SOURCE_Y}, one 32-tile row",
        f"Top HUD string: {TOP_SEQUENCE!r}",
        f"Bottom HUD string: {BOTTOM_SEQUENCE!r}",
        "",
        "Palette indices:",
        f"- transparent: {COLOR_TRANSPARENT}",
        f"- label text: {COLOR_TEXT}",
        f"- score digits and life icons: {COLOR_SCORE}",
        f"- fruit red/pink/green/orange: {COLOR_RED}/{COLOR_PINK}/{COLOR_GREEN}/{COLOR_ORANGE}",
        "",
        "Tiles:",
    ]
    for index, (key, tile_bytes) in enumerate(tiles):
        lines.append(f"- {index:02d}: {key} sha256={hashlib.sha256(tile_bytes).hexdigest()}")
    lines.extend([
        "",
        "Dirty regions / CPU VRAM blits:",
        "- top band: dst=(0,0), bytes=128x8",
        "- bottom band: dst=(0,204), bytes=128x8",
        "",
        "Non-space glyph/icon placements:",
    ])
    for entry in entries:
        lines.append(
            f"- {entry['key']}: src=({int(entry['tile']) * 8},{HUD_SOURCE_Y}) "
            f"dst=({int(entry['x'])},{int(entry['y'])}) bytes=4x8 "
            f"col={entry['col']} token={entry['char']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic T014 HUD assets.")
    parser.add_argument("--tiles-output", type=pathlib.Path, default=HUD_TILES_PATH)
    parser.add_argument("--patch-output", type=pathlib.Path, default=HUD_PATCH_PATH)
    parser.add_argument("--draw-output", type=pathlib.Path, default=HUD_DRAW_INCLUDE_PATH)
    parser.add_argument("--summary-output", type=pathlib.Path, default=HUD_SUMMARY_PATH)
    args = parser.parse_args()

    index_by_key, tiles = collect_tiles()
    atlas = build_atlas(tiles)
    entries = sequence_entries(TOP_SEQUENCE, TOP_ROW_Y, index_by_key)
    entries.extend(sequence_entries(BOTTOM_SEQUENCE, BOTTOM_ROW_Y, index_by_key))
    patch = build_patch(tiles, entries)

    args.tiles_output.parent.mkdir(parents=True, exist_ok=True)
    args.patch_output.parent.mkdir(parents=True, exist_ok=True)
    args.draw_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.tiles_output.write_bytes(atlas)
    args.patch_output.write_bytes(patch)
    write_draw_include(args.draw_output, entries)
    write_summary(args.summary_output, atlas, patch, tiles, entries)

    print(f"Wrote {args.tiles_output.relative_to(REPO_ROOT)}")
    print(f"Wrote {args.patch_output.relative_to(REPO_ROOT)}")
    print(f"Wrote {args.draw_output.relative_to(REPO_ROOT)}")
    print(f"Wrote {args.summary_output.relative_to(REPO_ROOT)}")
    print(f"HUD tile atlas SHA-256: {hashlib.sha256(atlas).hexdigest()}")
    print(f"HUD patch SHA-256: {hashlib.sha256(patch).hexdigest()}")
    print(f"HUD blit count: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
