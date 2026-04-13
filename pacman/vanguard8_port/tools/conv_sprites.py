#!/usr/bin/env python3

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from _common import ASSETS_DIR, REPO_ROOT, asset_relpath, require_input, run_tool, write_output


SPRITE_WIDTH = 16
SPRITE_HEIGHT = 16
SPRITE_COUNT = 64
SPRITE_PATTERN_BYTES = 32
SPRITE_COLOR_ROWS = 16
SPRITE_COLOR_SLOTS = 32
INVISIBLE_COLOR_BYTE = 0x40

PALETTE_MAP_PATH = REPO_ROOT / "assets" / "src" / "palette_map.md"
SPRITE_MANIFEST_PATH = ASSETS_DIR / "sprites_manifest.txt"
EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T008-sprites"
SPRITE_DIFF_PATH = EVIDENCE_DIR / "sprite_diff.png"


@dataclass(frozen=True)
class RowColor:
    byte: int
    selected_slot: int
    visible_slots: tuple[int, ...]
    counts: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class ColorProfile:
    name: str
    source_sprite: int
    clut_id: int


COLOR_PROFILES = (
    ColorProfile("pacman_yellow_static_slot", 0x30, 9),
    ColorProfile("blinky_red_static_slot", 0x20, 1),
    ColorProfile("pinky_pink_static_slot", 0x20, 3),
    ColorProfile("inky_cyan_static_slot", 0x20, 5),
    ColorProfile("clyde_orange_static_slot", 0x20, 7),
    ColorProfile("fruit_red_green_preview_slot", 0x00, 15),
    ColorProfile("ghost_eye_detail_preview_slot", 0x28, 1),
    ColorProfile("pacman_death_yellow_preview_slot", 0x3C, 9),
)


def get_bit(data: bytes, bit_offset: int) -> int:
    byte = data[bit_offset >> 3]
    return (byte >> (7 - (bit_offset & 7))) & 1


def decode_sprites(rom: bytes) -> list[tuple[tuple[int, ...], ...]]:
    if len(rom) != 4096:
        raise RuntimeError(f"expected 4096-byte pacman.5f sprite ROM, found {len(rom)} bytes")

    plane_offsets = (0, 4)
    x_offsets = (
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
    y_offsets = tuple(i * 8 for i in range(8)) + tuple(32 * 8 + i * 8 for i in range(8))
    char_inc = 64 * 8

    sprites: list[tuple[tuple[int, ...], ...]] = []
    for sprite_id in range(SPRITE_COUNT):
        base = sprite_id * char_inc
        rows: list[tuple[int, ...]] = []
        for y in range(SPRITE_HEIGHT):
            row: list[int] = []
            for x in range(SPRITE_WIDTH):
                pixel = 0
                for plane, plane_offset in enumerate(plane_offsets):
                    bit = get_bit(rom, base + y_offsets[y] + x_offsets[x] + plane_offset)
                    pixel |= bit << plane
                row.append(pixel)
            rows.append(tuple(row))
        sprites.append(tuple(rows))

    return sprites


def decode_clut(prom: bytes) -> list[tuple[int, int, int, int]]:
    if len(prom) != 256:
        raise RuntimeError(f"expected 256-byte 82s126.4a CLUT PROM, found {len(prom)} bytes")
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


def source_display_clut(sprite_id: int) -> int:
    if 0x08 <= sprite_id <= 0x1D or 0x20 <= sprite_id <= 0x27:
        return 1
    if 0x28 <= sprite_id <= 0x2B:
        return 1
    if 0x2C <= sprite_id <= 0x3E:
        return 9
    if sprite_id == 0x3F:
        return 0
    return 15


def clut_slots(
    clut_row: tuple[int, int, int, int],
    prom_to_slot: dict[int, int],
) -> tuple[int, int, int, int]:
    slots = []
    for prom_index in clut_row:
        try:
            slots.append(prom_to_slot[prom_index])
        except KeyError as error:
            raise RuntimeError(
                f"CLUT references PROM color {prom_index}, which has no T004 palette slot"
            ) from error
    return tuple(slots)


def pack_8x8_pattern(sprite: tuple[tuple[int, ...], ...], x0: int, y0: int) -> bytes:
    packed = bytearray()
    for y in range(y0, y0 + 8):
        value = 0
        for x in range(x0, x0 + 8):
            if sprite[y][x] != 0:
                value |= 1 << (7 - (x - x0))
        packed.append(value)
    return bytes(packed)


def pack_sprite_pattern(sprite: tuple[tuple[int, ...], ...]) -> bytes:
    packed = b"".join(
        (
            pack_8x8_pattern(sprite, 0, 0),
            pack_8x8_pattern(sprite, 8, 0),
            pack_8x8_pattern(sprite, 0, 8),
            pack_8x8_pattern(sprite, 8, 8),
        )
    )
    if len(packed) != SPRITE_PATTERN_BYTES:
        raise AssertionError(f"packed sprite pattern size mismatch: {len(packed)}")
    return packed


def choose_row_colors(
    sprite: tuple[tuple[int, ...], ...],
    palette_slots: tuple[int, int, int, int],
) -> list[RowColor]:
    row_colors: list[RowColor] = []
    for row in sprite:
        counts: Counter[int] = Counter()
        for pixel in row:
            if pixel != 0:
                counts[palette_slots[pixel]] += 1
        if not counts:
            row_colors.append(RowColor(INVISIBLE_COLOR_BYTE, 0, tuple(), tuple()))
            continue

        selected_slot, _count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
        row_colors.append(
            RowColor(
                selected_slot & 0x0F,
                selected_slot,
                tuple(sorted(counts)),
                tuple(sorted(counts.items())),
            )
        )
    return row_colors


def build_color_table(
    sprites: list[tuple[tuple[int, ...], ...]],
    clut: list[tuple[int, int, int, int]],
    prom_to_slot: dict[int, int],
) -> tuple[bytes, list[str]]:
    profiles = list(COLOR_PROFILES)
    while len(profiles) < SPRITE_COLOR_SLOTS:
        profiles.append(ColorProfile(f"hidden_unused_slot_{len(profiles):02d}", 0x3F, 0))

    payload = bytearray()
    lines = ["Sprite color table profiles (VDP-B 0x7A00, 32 entries x 16 rows):"]
    for slot, profile in enumerate(profiles):
        row_colors = choose_row_colors(
            sprites[profile.source_sprite],
            clut_slots(clut[profile.clut_id], prom_to_slot),
        )
        color_bytes = bytes(row.byte for row in row_colors)
        payload.extend(color_bytes)
        lines.append(
            f"slot {slot:02d}: {profile.name}; source sprite ${profile.source_sprite:02X}; "
            f"CLUT {profile.clut_id:02d}; bytes "
            + " ".join(f"{byte:02X}" for byte in color_bytes)
        )

    if len(payload) != SPRITE_COLOR_SLOTS * SPRITE_COLOR_ROWS:
        raise AssertionError(f"sprite color table size mismatch: {len(payload)}")
    return bytes(payload), lines


def render_sprite(
    sprite: tuple[tuple[int, ...], ...],
    palette_slots: tuple[int, int, int, int],
    slot_rgb: dict[int, tuple[int, int, int]],
) -> Image.Image:
    image = Image.new("RGB", (SPRITE_WIDTH, SPRITE_HEIGHT), slot_rgb[0])
    pixels = image.load()
    for y, row in enumerate(sprite):
        for x, pixel in enumerate(row):
            pixels[x, y] = slot_rgb[palette_slots[pixel]]
    return image


def render_converted_sprite(
    sprite: tuple[tuple[int, ...], ...],
    row_colors: list[RowColor],
    slot_rgb: dict[int, tuple[int, int, int]],
) -> Image.Image:
    image = Image.new("RGB", (SPRITE_WIDTH, SPRITE_HEIGHT), slot_rgb[0])
    pixels = image.load()
    for y, row in enumerate(sprite):
        if row_colors[y].byte & INVISIBLE_COLOR_BYTE:
            continue
        rgb = slot_rgb[row_colors[y].selected_slot]
        for x, pixel in enumerate(row):
            if pixel != 0:
                pixels[x, y] = rgb
    return image


def render_diff_png(
    sprites: list[tuple[tuple[int, ...], ...]],
    clut: list[tuple[int, int, int, int]],
    prom_to_slot: dict[int, int],
    slot_rgb: dict[int, tuple[int, int, int]],
) -> None:
    zoom = 3
    columns = 8
    sprite_pair_width = SPRITE_WIDTH * zoom * 2 + 8
    label_height = 20
    cell_width = sprite_pair_width + 24
    cell_height = SPRITE_HEIGHT * zoom + label_height
    rows = math.ceil(len(sprites) / columns)
    image = Image.new("RGB", (columns * cell_width, rows * cell_height), (18, 18, 18))
    draw = ImageDraw.Draw(image)

    for sprite_id, sprite in enumerate(sprites):
        clut_id = source_display_clut(sprite_id)
        palette_slots = clut_slots(clut[clut_id], prom_to_slot)
        row_colors = choose_row_colors(sprite, palette_slots)
        source_image = render_sprite(sprite, palette_slots, slot_rgb).resize(
            (SPRITE_WIDTH * zoom, SPRITE_HEIGHT * zoom),
            Image.Resampling.NEAREST,
        )
        converted_image = render_converted_sprite(sprite, row_colors, slot_rgb).resize(
            (SPRITE_WIDTH * zoom, SPRITE_HEIGHT * zoom),
            Image.Resampling.NEAREST,
        )

        column = sprite_id % columns
        row = sprite_id // columns
        ox = column * cell_width
        oy = row * cell_height
        image.paste(source_image, (ox, oy))
        image.paste(converted_image, (ox + SPRITE_WIDTH * zoom + 8, oy))
        draw.text((ox, oy + SPRITE_HEIGHT * zoom + 2), f"${sprite_id:02X} clut {clut_id:02d}", fill=(235, 235, 210))

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    image.save(SPRITE_DIFF_PATH)


def count_visible_pixels(sprite: tuple[tuple[int, ...], ...]) -> int:
    return sum(1 for row in sprite for pixel in row if pixel != 0)


def format_multi_color_rows(row_colors: list[RowColor]) -> str:
    notes = []
    for row_index, row_color in enumerate(row_colors):
        if len(row_color.visible_slots) <= 1:
            continue
        counts = ",".join(f"{slot}:{count}" for slot, count in row_color.counts)
        notes.append(f"y{row_index:02d}[{counts}->slot{row_color.selected_slot}]")
    return " ".join(notes) if notes else "none"


def write_manifest(
    sprites: list[tuple[tuple[int, ...], ...]],
    clut: list[tuple[int, int, int, int]],
    prom_to_slot: dict[int, int],
    color_profile_lines: list[str],
) -> None:
    lines = [
        "# Vanguard 8 sprite conversion manifest",
        "",
        "Generated from `source_rom/pacman.5f` and `source_rom/82s126.4a`.",
        "Sprite art is kept upright; only non-zero source pixels become opaque",
        "V9938 sprite pattern bits.",
        "",
        f"sprites converted: {len(sprites)}",
        f"pattern bytes: {len(sprites) * SPRITE_PATTERN_BYTES}",
        f"color table bytes: {SPRITE_COLOR_SLOTS * SPRITE_COLOR_ROWS}",
        "pattern group order per 16x16 sprite: top-left, top-right, bottom-left, bottom-right",
        "",
    ]
    lines.extend(color_profile_lines)
    lines.extend(["", "Per-source sprite pattern audit:"])

    for sprite_id, sprite in enumerate(sprites):
        clut_id = source_display_clut(sprite_id)
        palette_slots = clut_slots(clut[clut_id], prom_to_slot)
        row_colors = choose_row_colors(sprite, palette_slots)
        row_bytes = " ".join(f"{row.byte:02X}" for row in row_colors)
        lines.append(
            f"source ${sprite_id:02X}: pattern_offset=0x{sprite_id * SPRITE_PATTERN_BYTES:04X}; "
            f"display_clut={clut_id:02d}; clut_slots={palette_slots}; "
            f"visible_pixels={count_visible_pixels(sprite)}; row_bytes={row_bytes}; "
            f"multi_color_rows={format_multi_color_rows(row_colors)}"
        )

    manifest = "\n".join(lines) + "\n"
    SPRITE_MANIFEST_PATH.write_text(manifest, encoding="utf-8")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "sprite_manifest.txt").write_text(manifest, encoding="utf-8")


def main() -> int:
    def action() -> None:
        sprite_rom = require_input("pacman.5f")
        clut_prom = require_input("82s126.4a")
        sprites = decode_sprites(sprite_rom)
        clut = decode_clut(clut_prom)
        prom_to_slot = load_prom_to_slot_map(PALETTE_MAP_PATH)
        slot_rgb = load_slot_rgb(PALETTE_MAP_PATH)

        patterns = b"".join(pack_sprite_pattern(sprite) for sprite in sprites)
        colors, color_profile_lines = build_color_table(sprites, clut, prom_to_slot)
        patterns_path = write_output("sprites_patterns.bin", patterns)
        colors_path = write_output("sprites_colors.bin", colors)

        render_diff_png(sprites, clut, prom_to_slot, slot_rgb)
        write_manifest(sprites, clut, prom_to_slot, color_profile_lines)

        multi_color_source_rows = 0
        for sprite_id, sprite in enumerate(sprites):
            row_colors = choose_row_colors(
                sprite,
                clut_slots(clut[source_display_clut(sprite_id)], prom_to_slot),
            )
            multi_color_source_rows += sum(1 for row in row_colors if len(row.visible_slots) > 1)

        print(f"conv_sprites: total source sprites decoded: {len(sprites)}")
        print(f"conv_sprites: bytes written: {len(patterns)} patterns + {len(colors)} colors")
        print(f"conv_sprites: multi-color source rows flagged: {multi_color_source_rows}")
        print(
            "conv_sprites: "
            f"{len(patterns)} + {len(colors)} bytes written to "
            f"{asset_relpath(patterns_path)}, {asset_relpath(colors_path)}"
        )
        print(f"conv_sprites: manifest written to {asset_relpath(SPRITE_MANIFEST_PATH)}")
        print(f"conv_sprites: evidence PNG written to {SPRITE_DIFF_PATH.relative_to(REPO_ROOT)}")

    return run_tool("conv_sprites", action)


if __name__ == "__main__":
    raise SystemExit(main())
