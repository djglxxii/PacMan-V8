#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib
from dataclasses import dataclass


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_RGB_PROM_PATH = REPO_ROOT / "pacman" / "82s123.7f"
DEFAULT_LOOKUP_PROM_PATH = REPO_ROOT / "pacman" / "82s126.4a"
DEFAULT_PALETTE_A_PATH = REPO_ROOT / "assets" / "palette_a.bin"
DEFAULT_PALETTE_B_PATH = REPO_ROOT / "assets" / "palette_b.bin"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "assets" / "palette_manifest.txt"
DEFAULT_SUMMARY_PATH = REPO_ROOT / "assets" / "palette_summary.txt"

RGB_PROM_SIZE = 32
LOOKUP_PROM_SIZE = 256
LOOKUP_GROUP_COUNT = 64
LOOKUP_COLORS_PER_GROUP = 4
V8_PALETTE_ENTRIES = 16
V8_BYTES_PER_ENTRY = 2

ALLOWED_PROM_NAMES = frozenset({"82s123.7f", "82s126.4a"})
RESTRICTED_PROM_NAMES = frozenset(
    {
        "pacman.6e",
        "pacman.6f",
        "pacman.6h",
        "pacman.6j",
        "82s126.1m",
        "82s126.3m",
    }
)

RESISTOR_WEIGHTS_RGB = (1000, 470, 220)
RESISTOR_WEIGHTS_BLUE = (470, 220)


@dataclass(frozen=True)
class ArcadeColor:
    index: int
    prom_byte: int
    rgb888: tuple[int, int, int]
    v8_rgb: tuple[int, int, int]
    v8_bytes: tuple[int, int]


@dataclass(frozen=True)
class PaletteAssignment:
    vdp: str
    entry: int
    role: str
    source_index: int


VDP_A_ASSIGNMENTS = (
    PaletteAssignment("A", 0, "transparent_black", 0x00),
    PaletteAssignment("A", 1, "pacman_yellow", 0x09),
    PaletteAssignment("A", 2, "ghost_blinky_red", 0x01),
    PaletteAssignment("A", 3, "ghost_pinky_pink", 0x03),
    PaletteAssignment("A", 4, "ghost_inky_cyan", 0x05),
    PaletteAssignment("A", 5, "ghost_clyde_orange", 0x07),
    PaletteAssignment("A", 6, "eyes_white", 0x0F),
    PaletteAssignment("A", 7, "eyes_blue", 0x0B),
    PaletteAssignment("A", 8, "frightened_blue", 0x0B),
    PaletteAssignment("A", 9, "frightened_flash_white", 0x0F),
    PaletteAssignment("A", 10, "hud_text_white", 0x0F),
    PaletteAssignment("A", 11, "hud_text_red", 0x01),
    PaletteAssignment("A", 12, "hud_text_cyan", 0x05),
    PaletteAssignment("A", 13, "fruit_green", 0x0C),
    PaletteAssignment("A", 14, "fruit_peach", 0x0E),
    PaletteAssignment("A", 15, "fruit_shadow", 0x02),
)

VDP_B_ASSIGNMENTS = (
    PaletteAssignment("B", 0, "background_black", 0x00),
    PaletteAssignment("B", 1, "maze_wall_blue", 0x0B),
    PaletteAssignment("B", 2, "maze_wall_highlight", 0x06),
    PaletteAssignment("B", 3, "pellet_white", 0x0F),
    PaletteAssignment("B", 4, "energizer_white", 0x0F),
    PaletteAssignment("B", 5, "ghost_house_door", 0x03),
    PaletteAssignment("B", 6, "ready_text_yellow", 0x09),
    PaletteAssignment("B", 7, "score_text_white", 0x0F),
    PaletteAssignment("B", 8, "bonus_text_red", 0x01),
    PaletteAssignment("B", 9, "bonus_text_cyan", 0x05),
    PaletteAssignment("B", 10, "maze_flash_white", 0x0F),
    PaletteAssignment("B", 11, "maze_flash_blue", 0x0B),
    PaletteAssignment("B", 12, "unused_green", 0x0C),
    PaletteAssignment("B", 13, "unused_teal", 0x0D),
    PaletteAssignment("B", 14, "unused_pink", 0x0E),
    PaletteAssignment("B", 15, "debug_white", 0x0F),
)


def resistor_weights(resistances: tuple[int, ...]) -> tuple[int, ...]:
    conductances = tuple(1.0 / resistance for resistance in resistances)
    conductance_sum = sum(conductances)
    return tuple(int((conductance / conductance_sum * 255.0) + 0.5) for conductance in conductances)


def combine_weights(weights: tuple[int, ...], bits: tuple[int, ...]) -> int:
    return min(255, sum(weight for weight, bit in zip(weights, bits) if bit))


def scale_to_v8_channel(value: int) -> int:
    return min(7, int((value * 7 / 255) + 0.5))


def pack_v8_palette_entry(v8_rgb: tuple[int, int, int]) -> tuple[int, int]:
    red, green, blue = v8_rgb
    return ((red & 0x07) << 4) | (green & 0x07), blue & 0x07


def decode_rgb_prom(rgb_prom: bytes) -> list[ArcadeColor]:
    if len(rgb_prom) != RGB_PROM_SIZE:
        raise ValueError(f"RGB PROM must be {RGB_PROM_SIZE} bytes; got {len(rgb_prom)} bytes.")

    rgb_weights = resistor_weights(RESISTOR_WEIGHTS_RGB)
    blue_weights = resistor_weights(RESISTOR_WEIGHTS_BLUE)
    colors: list[ArcadeColor] = []

    for index, value in enumerate(rgb_prom):
        red = combine_weights(rgb_weights, tuple((value >> bit) & 0x01 for bit in range(3)))
        green = combine_weights(rgb_weights, tuple((value >> bit) & 0x01 for bit in range(3, 6)))
        blue = combine_weights(blue_weights, tuple((value >> bit) & 0x01 for bit in range(6, 8)))
        v8_rgb = (
            scale_to_v8_channel(red),
            scale_to_v8_channel(green),
            scale_to_v8_channel(blue),
        )

        colors.append(
            ArcadeColor(
                index=index,
                prom_byte=value,
                rgb888=(red, green, blue),
                v8_rgb=v8_rgb,
                v8_bytes=pack_v8_palette_entry(v8_rgb),
            )
        )

    return colors


def decode_lookup_prom(lookup_prom: bytes) -> list[tuple[int, tuple[int, int, int, int]]]:
    if len(lookup_prom) != LOOKUP_PROM_SIZE:
        raise ValueError(
            f"Color lookup PROM must be {LOOKUP_PROM_SIZE} bytes; got {len(lookup_prom)} bytes."
        )

    groups: list[tuple[int, tuple[int, int, int, int]]] = []
    for group_id in range(LOOKUP_GROUP_COUNT):
        start = group_id * LOOKUP_COLORS_PER_GROUP
        entries = tuple(value & 0x0F for value in lookup_prom[start : start + LOOKUP_COLORS_PER_GROUP])
        if len(entries) != LOOKUP_COLORS_PER_GROUP:
            raise ValueError(f"Lookup group {group_id} had unexpected length.")
        groups.append((group_id, entries))

    return groups


def palette_from_assignments(colors: list[ArcadeColor], assignments: tuple[PaletteAssignment, ...]) -> bytes:
    if len(assignments) != V8_PALETTE_ENTRIES:
        raise ValueError(f"Expected {V8_PALETTE_ENTRIES} palette assignments.")

    packed = bytearray()
    for expected_entry, assignment in enumerate(assignments):
        if assignment.entry != expected_entry:
            raise ValueError(f"Palette assignment out of order at entry {expected_entry}.")
        color = colors[assignment.source_index]
        packed.extend(color.v8_bytes)

    expected_size = V8_PALETTE_ENTRIES * V8_BYTES_PER_ENTRY
    if len(packed) != expected_size:
        raise ValueError(f"Packed V8 palette had unexpected size {len(packed)}.")

    return bytes(packed)


def validate_prom_path(path: pathlib.Path, expected_name: str) -> pathlib.Path:
    resolved = path.resolve()
    if resolved.name in RESTRICTED_PROM_NAMES:
        raise ValueError(f"Refusing to read restricted PROM: {resolved.relative_to(REPO_ROOT)}")
    if resolved.name not in ALLOWED_PROM_NAMES:
        raise ValueError(f"Refusing to read non-color PROM: {resolved}")
    if resolved.name != expected_name:
        raise ValueError(f"Expected {expected_name}; got {resolved.name}.")
    return resolved


def format_color(color: ArcadeColor) -> str:
    r, g, b = color.rgb888
    vr, vg, vb = color.v8_rgb
    byte0, byte1 = color.v8_bytes
    return (
        f"{color.index:02X} prom={color.prom_byte:02X} "
        f"rgb888={r:03},{g:03},{b:03} "
        f"v8rgb={vr},{vg},{vb} packed={byte0:02X} {byte1:02X}"
    )


def write_manifest(
    path: pathlib.Path,
    rgb_prom: bytes,
    lookup_prom: bytes,
    colors: list[ArcadeColor],
    lookup_groups: list[tuple[int, tuple[int, int, int, int]]],
    palette_a: bytes,
    palette_b: bytes,
    rgb_prom_path: pathlib.Path,
    lookup_prom_path: pathlib.Path,
) -> None:
    lines = [
        "# Pac-Man palette extraction manifest",
        "# Source roles confirmed against MAME pacman_v.cpp pacman_palette().",
        f"RGB palette PROM: {rgb_prom_path.relative_to(REPO_ROOT)}",
        f"RGB palette PROM bytes: {len(rgb_prom)}",
        f"RGB palette PROM SHA-256: {hashlib.sha256(rgb_prom).hexdigest()}",
        f"Color lookup PROM: {lookup_prom_path.relative_to(REPO_ROOT)}",
        f"Color lookup PROM bytes: {len(lookup_prom)}",
        f"Color lookup PROM SHA-256: {hashlib.sha256(lookup_prom).hexdigest()}",
        "",
        "Arcade RGB entries:",
    ]

    lines.extend(format_color(color) for color in colors)
    lines.extend(["", "Arcade lookup groups:"])
    for group_id, entries in lookup_groups:
        colors_text = " ".join(f"{entry:02X}" for entry in entries)
        lines.append(f"{group_id:02X}: {colors_text}")

    lines.extend(["", "VDP-A palette assignments:"])
    lines.extend(format_assignment(colors, assignment) for assignment in VDP_A_ASSIGNMENTS)
    lines.append(f"VDP-A palette SHA-256: {hashlib.sha256(palette_a).hexdigest()}")

    lines.extend(["", "VDP-B palette assignments:"])
    lines.extend(format_assignment(colors, assignment) for assignment in VDP_B_ASSIGNMENTS)
    lines.append(f"VDP-B palette SHA-256: {hashlib.sha256(palette_b).hexdigest()}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_assignment(colors: list[ArcadeColor], assignment: PaletteAssignment) -> str:
    color = colors[assignment.source_index]
    r, g, b = color.rgb888
    vr, vg, vb = color.v8_rgb
    byte0, byte1 = color.v8_bytes
    return (
        f"{assignment.entry:02X} {assignment.role:<24} "
        f"source={assignment.source_index:02X} "
        f"rgb888={r:03},{g:03},{b:03} "
        f"v8rgb={vr},{vg},{vb} packed={byte0:02X} {byte1:02X}"
    )


def write_summary(
    path: pathlib.Path,
    rgb_prom: bytes,
    lookup_prom: bytes,
    palette_a: bytes,
    palette_b: bytes,
    rgb_prom_path: pathlib.Path,
    lookup_prom_path: pathlib.Path,
    palette_a_path: pathlib.Path,
    palette_b_path: pathlib.Path,
    manifest_path: pathlib.Path,
) -> None:
    lines = [
        "Pac-Man palette extraction summary",
        f"RGB palette PROM: {rgb_prom_path.relative_to(REPO_ROOT)}",
        f"RGB palette PROM bytes: {len(rgb_prom)}",
        f"RGB palette PROM SHA-256: {hashlib.sha256(rgb_prom).hexdigest()}",
        f"Color lookup PROM: {lookup_prom_path.relative_to(REPO_ROOT)}",
        f"Color lookup PROM bytes: {len(lookup_prom)}",
        f"Color lookup PROM SHA-256: {hashlib.sha256(lookup_prom).hexdigest()}",
        f"Decoded RGB entries: {RGB_PROM_SIZE}",
        f"Decoded lookup groups: {LOOKUP_GROUP_COUNT}",
        f"Output VDP-A palette: {palette_a_path.relative_to(REPO_ROOT)}",
        f"Output VDP-A palette bytes: {len(palette_a)}",
        f"Output VDP-A palette SHA-256: {hashlib.sha256(palette_a).hexdigest()}",
        f"Output VDP-B palette: {palette_b_path.relative_to(REPO_ROOT)}",
        f"Output VDP-B palette bytes: {len(palette_b)}",
        f"Output VDP-B palette SHA-256: {hashlib.sha256(palette_b).hexdigest()}",
        f"Manifest: {manifest_path.relative_to(REPO_ROOT)}",
        "PROMs read:",
        f"  {rgb_prom_path.relative_to(REPO_ROOT)}",
        f"  {lookup_prom_path.relative_to(REPO_ROOT)}",
        "Restricted PROMs read: none",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode Pac-Man color PROMs into Vanguard 8 V9938 palettes."
    )
    parser.add_argument("--rgb-prom", type=pathlib.Path, default=DEFAULT_RGB_PROM_PATH)
    parser.add_argument("--lookup-prom", type=pathlib.Path, default=DEFAULT_LOOKUP_PROM_PATH)
    parser.add_argument("--palette-a", type=pathlib.Path, default=DEFAULT_PALETTE_A_PATH)
    parser.add_argument("--palette-b", type=pathlib.Path, default=DEFAULT_PALETTE_B_PATH)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--summary", type=pathlib.Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rgb_prom_path = validate_prom_path(args.rgb_prom, "82s123.7f")
    lookup_prom_path = validate_prom_path(args.lookup_prom, "82s126.4a")
    palette_a_path = args.palette_a.resolve()
    palette_b_path = args.palette_b.resolve()
    manifest_path = args.manifest.resolve()
    summary_path = args.summary.resolve()

    rgb_prom = rgb_prom_path.read_bytes()
    lookup_prom = lookup_prom_path.read_bytes()
    colors = decode_rgb_prom(rgb_prom)
    lookup_groups = decode_lookup_prom(lookup_prom)
    palette_a = palette_from_assignments(colors, VDP_A_ASSIGNMENTS)
    palette_b = palette_from_assignments(colors, VDP_B_ASSIGNMENTS)

    palette_a_path.parent.mkdir(parents=True, exist_ok=True)
    palette_b_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    palette_a_path.write_bytes(palette_a)
    palette_b_path.write_bytes(palette_b)
    write_manifest(
        manifest_path,
        rgb_prom,
        lookup_prom,
        colors,
        lookup_groups,
        palette_a,
        palette_b,
        rgb_prom_path,
        lookup_prom_path,
    )
    write_summary(
        summary_path,
        rgb_prom,
        lookup_prom,
        palette_a,
        palette_b,
        rgb_prom_path,
        lookup_prom_path,
        palette_a_path,
        palette_b_path,
        manifest_path,
    )

    print(f"Read {len(rgb_prom)} bytes from {rgb_prom_path.relative_to(REPO_ROOT)}")
    print(f"Read {len(lookup_prom)} bytes from {lookup_prom_path.relative_to(REPO_ROOT)}")
    print(f"Decoded {len(colors)} RGB entries")
    print(f"Decoded {len(lookup_groups)} lookup groups")
    print(f"Wrote {len(palette_a)} bytes to {palette_a_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(palette_b)} bytes to {palette_b_path.relative_to(REPO_ROOT)}")
    print(f"Wrote manifest to {manifest_path.relative_to(REPO_ROOT)}")
    print(f"Wrote summary to {summary_path.relative_to(REPO_ROOT)}")
    print(f"VDP-A palette SHA-256: {hashlib.sha256(palette_a).hexdigest()}")
    print(f"VDP-B palette SHA-256: {hashlib.sha256(palette_b).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
