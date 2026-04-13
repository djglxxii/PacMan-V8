#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from _common import ASSETS_DIR, REPO_ROOT, asset_relpath, require_input, run_tool, write_output
from conv_tiles import decode_tiles


TILE_WIDTH = 8
TILE_HEIGHT = 8
NAME_TABLE_WIDTH = 32
NAME_TABLE_HEIGHT = 24
NAME_TABLE_BYTES = NAME_TABLE_WIDTH * NAME_TABLE_HEIGHT
PATTERN_BANK_BYTES = 256 * TILE_HEIGHT
G3_BANKS = 3
PATTERN_TABLE_BASE = 0x0300
COLOR_TABLE_BASE = 0x1800
HUD_WHITE_SLOT = 12
PACMAN_YELLOW_SLOT = 2
FRUIT_RED_SLOT = 10
HUD_LETTERS = "CEGHIORS"

MANIFEST_PATH = ASSETS_DIR / "hud_font_manifest.txt"


@dataclass(frozen=True)
class GlyphSource:
    name: str
    tile_id: int | None
    color_slot: int


@dataclass(frozen=True)
class Glyph:
    name: str
    index: int
    source: GlyphSource
    pattern_rows: tuple[int, ...]
    color_rows: tuple[int, ...]


def source_glyphs() -> list[GlyphSource]:
    glyphs = [GlyphSource("space", None, HUD_WHITE_SLOT)]
    glyphs.extend(GlyphSource(str(value), value, HUD_WHITE_SLOT) for value in range(10))
    glyphs.extend(GlyphSource(letter, 0x41 + ord(letter) - ord("A"), HUD_WHITE_SLOT) for letter in HUD_LETTERS)
    glyphs.extend(
        [
            GlyphSource("life", 0x20, PACMAN_YELLOW_SLOT),
            GlyphSource("fruit", 0x14, FRUIT_RED_SLOT),
        ]
    )
    return glyphs


def pattern_rows_for_tile(tile: list[list[int]]) -> tuple[int, ...]:
    rows: list[int] = []
    for source_row in tile:
        packed = 0
        for pixel in source_row:
            packed = (packed << 1) | (1 if pixel else 0)
        rows.append(packed)
    if len(rows) != TILE_HEIGHT:
        raise AssertionError(f"glyph pattern height mismatch: {len(rows)}")
    return tuple(rows)


def build_glyphs(tiles: list[list[list[int]]]) -> dict[str, Glyph]:
    glyphs: dict[str, Glyph] = {}
    for index, source in enumerate(source_glyphs()):
        if source.tile_id is None:
            pattern_rows = (0,) * TILE_HEIGHT
        else:
            try:
                tile = tiles[source.tile_id]
            except IndexError as error:
                raise RuntimeError(f"HUD glyph {source.name!r} references missing tile ${source.tile_id:02X}") from error
            pattern_rows = pattern_rows_for_tile(tile)

        color_rows = tuple((source.color_slot << 4) | 0 for _ in range(TILE_HEIGHT))
        glyphs[source.name] = Glyph(source.name, index, source, pattern_rows, color_rows)

    return glyphs


def glyph_index(glyphs: dict[str, Glyph], character: str) -> int:
    key = "space" if character == " " else character
    try:
        return glyphs[key].index
    except KeyError as error:
        raise RuntimeError(f"HUD layout references unknown glyph {character!r}") from error


def place_text(
    name_table: bytearray,
    glyphs: dict[str, Glyph],
    row: int,
    column: int,
    text: str,
) -> list[tuple[int, int, str]]:
    if row < 0 or row >= NAME_TABLE_HEIGHT:
        raise RuntimeError(f"HUD row out of range: {row}")
    if column < 0 or column + len(text) > NAME_TABLE_WIDTH:
        raise RuntimeError(f"HUD text {text!r} does not fit at column {column}")

    occupied: list[tuple[int, int, str]] = []
    for offset, character in enumerate(text):
        index = row * NAME_TABLE_WIDTH + column + offset
        name_table[index] = glyph_index(glyphs, character)
        if character != " ":
            occupied.append((row, column + offset, character))
    return occupied


def build_name_table(glyphs: dict[str, Glyph]) -> tuple[bytes, list[tuple[int, int, str]]]:
    name_table = bytearray(NAME_TABLE_BYTES)
    occupied: list[tuple[int, int, str]] = []

    occupied.extend(place_text(name_table, glyphs, 0, 11, "HIGH SCORE"))
    occupied.extend(place_text(name_table, glyphs, 1, 13, "00000"))
    occupied.extend(place_text(name_table, glyphs, 22, 13, "SCORE"))
    occupied.extend(place_text(name_table, glyphs, 23, 13, "00000"))

    for row in (3, 4):
        name_table[row * NAME_TABLE_WIDTH] = glyphs["life"].index
        occupied.append((row, 0, "life"))
    name_table[6 * NAME_TABLE_WIDTH] = glyphs["fruit"].index
    occupied.append((6, 0, "fruit"))

    return bytes(name_table), occupied


def compact_repeated_table(glyphs: dict[str, Glyph], attr: str) -> bytes:
    glyph_count = len(glyphs)
    payload = bytearray()
    ordered = sorted(glyphs.values(), key=lambda item: item.index)
    for bank in range(G3_BANKS):
        for glyph in glyphs.values():
            if glyph.index >= glyph_count:
                raise AssertionError(f"non-contiguous glyph index: {glyph.index}")
        for glyph in ordered:
            rows = getattr(glyph, attr)
            payload.extend(bytes(rows))
    return bytes(payload)


def render_manifest(glyphs: dict[str, Glyph], occupied: list[tuple[int, int, str]], total_bytes: int) -> str:
    lines = [
        "# HUD Font Manifest",
        "",
        "Generated from `source_rom/pacman.5e` by `tools/conv_hud_font.py`.",
        "",
        "## Glyphs",
        "",
        "| Glyph | Pattern index | Source tile | Foreground slot |",
        "|---|---:|---:|---:|",
    ]
    for glyph in sorted(glyphs.values(), key=lambda item: item.index):
        tile = "n/a" if glyph.source.tile_id is None else f"${glyph.source.tile_id:02X}"
        lines.append(f"| {glyph.name} | {glyph.index} | {tile} | {glyph.source.color_slot} |")

    lines.extend(
        [
            "",
            "## Static HUD Cells",
            "",
            "| Row | Column | Glyph |",
            "|---:|---:|---|",
        ]
    )
    for row, column, label in occupied:
        lines.append(f"| {row} | {column} | {label} |")

    lines.extend(
        [
            "",
            "## Output Layout",
            "",
            f"- Pattern Name Table payload: {NAME_TABLE_BYTES} bytes for VDP-A VRAM `0x0000`.",
            f"- Pattern slices: {len(glyphs) * TILE_HEIGHT} bytes per bank for VDP-A VRAM `0x0300`, `0x0B00`, `0x1300`.",
            f"- Color slices: {len(glyphs) * TILE_HEIGHT} bytes per bank for VDP-A VRAM `0x1800`, `0x2000`, `0x2800`.",
            f"- Compact `hud_font.bin`: {total_bytes} bytes.",
            "- Color index 0 is the transparent background; TP is set by ROM init.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    def action() -> None:
        tile_rom = require_input("pacman.5e")
        tiles = decode_tiles(tile_rom)
        glyphs = build_glyphs(tiles)
        name_table, occupied = build_name_table(glyphs)
        pattern_slices = compact_repeated_table(glyphs, "pattern_rows")
        color_slices = compact_repeated_table(glyphs, "color_rows")
        payload = name_table + pattern_slices + color_slices

        font_path = write_output("hud_font.bin", payload)
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(render_manifest(glyphs, occupied, len(payload)), encoding="utf-8")

        print(f"conv_hud_font: glyphs kept: {len(glyphs)}")
        print(f"conv_hud_font: static HUD occupied cells: {len(occupied)}")
        print(f"conv_hud_font: {len(payload)} bytes written to {asset_relpath(font_path)}")
        print(f"conv_hud_font: manifest written to {asset_relpath(MANIFEST_PATH)}")

    return run_tool("conv_hud_font", action)


if __name__ == "__main__":
    raise SystemExit(main())
