#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass

from _common import ASSETS_DIR, REPO_ROOT, asset_relpath, require_input, run_tool, write_output


# Slot assignment for both VDP palettes.
# Slot 0 stays black on both chips; VDP-A transparency comes from TP=1, not from
# a different color value. Slots 10/12/15 intentionally preserve arcade role
# aliases that share source colors with slots 3/8/0.
#
#   0  black (maze backdrop / VDP-A transparent color)
#   1  maze wall blue
#   2  Pac-Man yellow
#   3  Blinky red
#   4  Pinky pink
#   5  Inky cyan
#   6  Clyde orange
#   7  frightened blue
#   8  frightened white
#   9  dot / pellet peach
#   10 cherry red alias
#   11 fruit stem green
#   12 HUD white alias
#   13 reserved warm peach
#   14 reserved teal
#   15 reserved black alias

RGB = tuple[int, int, int]
V9938RGB = tuple[int, int, int]

V9938_LEVELS = (0, 36, 73, 109, 146, 182, 219, 255)
PALETTE_DOC_PATH = REPO_ROOT / "assets" / "src" / "palette_map.md"
SLOT_MAP_PATH = ASSETS_DIR / "palette_slot_map.txt"


@dataclass(frozen=True)
class PaletteSlot:
    slot: int
    prom_index: int
    name: str
    role: str


SLOT_LAYOUT = [
    PaletteSlot(0, 0, "black", "maze backdrop / VDP-A transparent color"),
    PaletteSlot(1, 11, "maze_blue", "maze wall blue"),
    PaletteSlot(2, 9, "pacman_yellow", "Pac-Man yellow"),
    PaletteSlot(3, 1, "blinky_red", "Blinky red"),
    PaletteSlot(4, 3, "pinky_pink", "Pinky pink"),
    PaletteSlot(5, 5, "inky_cyan", "Inky cyan"),
    PaletteSlot(6, 7, "clyde_orange", "Clyde orange"),
    PaletteSlot(7, 6, "frightened_blue", "frightened blue"),
    PaletteSlot(8, 15, "frightened_white", "frightened white"),
    PaletteSlot(9, 2, "dot_peach", "dot / pellet peach"),
    PaletteSlot(10, 1, "cherry_red", "fruit red alias"),
    PaletteSlot(11, 12, "fruit_green", "fruit stem green"),
    PaletteSlot(12, 15, "hud_white", "HUD white alias"),
    PaletteSlot(13, 14, "reserved_warm_peach", "reserved warm peach"),
    PaletteSlot(14, 13, "reserved_teal", "reserved teal"),
    PaletteSlot(15, 0, "reserved_black", "reserved black alias"),
]


def decode_master_palette(prom: bytes) -> list[RGB]:
    rw = (0x21, 0x47, 0x97)
    gw = (0x21, 0x47, 0x97)
    bw = (0x51, 0xAE)
    palette: list[RGB] = []

    for value in prom:
        red = rw[0] * ((value >> 0) & 1) + rw[1] * ((value >> 1) & 1) + rw[2] * ((value >> 2) & 1)
        green = gw[0] * ((value >> 3) & 1) + gw[1] * ((value >> 4) & 1) + gw[2] * ((value >> 5) & 1)
        blue = bw[0] * ((value >> 6) & 1) + bw[1] * ((value >> 7) & 1)
        palette.append((min(red, 255), min(green, 255), min(blue, 255)))

    return palette


def quantize_channel(value: int) -> int:
    return min(range(8), key=lambda level: abs(V9938_LEVELS[level] - value))


def quantize_rgb(color: RGB) -> V9938RGB:
    return tuple(quantize_channel(channel) for channel in color)


def pack_v9938_entry(color: V9938RGB) -> bytes:
    red, green, blue = color
    return bytes(((red << 4) | green, blue))


def build_slot_lines(master_palette: list[RGB]) -> tuple[list[str], bytes, list[str]]:
    slot_lines = ["slot | arcade RGB (hex) | v9938 RGB (0..7) | role"]
    payload = bytearray()
    warnings: list[str] = []
    quantized_sources: dict[V9938RGB, RGB] = {}

    for slot in SLOT_LAYOUT:
        arcade_rgb = master_palette[slot.prom_index]
        v9938_rgb = quantize_rgb(arcade_rgb)
        prior_source = quantized_sources.get(v9938_rgb)
        if prior_source is None:
            quantized_sources[v9938_rgb] = arcade_rgb
        elif prior_source != arcade_rgb:
            warnings.append(
                "quantization collision: "
                f"{slot.name} {arcade_rgb!r} -> {v9938_rgb} already used by {prior_source!r}"
            )

        payload.extend(pack_v9938_entry(v9938_rgb))
        slot_lines.append(
            f"{slot.slot:02d} | #{arcade_rgb[0]:02X}{arcade_rgb[1]:02X}{arcade_rgb[2]:02X} | "
            f"{v9938_rgb[0]},{v9938_rgb[1]},{v9938_rgb[2]} | {slot.role}"
        )

    return slot_lines, bytes(payload), warnings


def render_palette_doc(master_palette: list[RGB]) -> str:
    lines = [
        "# Pac-Man Palette Slot Map",
        "",
        "Generated from `source_rom/82s123.7f` by `tools/conv_palette.py`.",
        "",
        "| Slot | PROM index | Arcade RGB | V9938 RGB | Role |",
        "|---|---:|---|---|---|",
    ]

    for slot in SLOT_LAYOUT:
        arcade_rgb = master_palette[slot.prom_index]
        v9938_rgb = quantize_rgb(arcade_rgb)
        lines.append(
            f"| {slot.slot} | {slot.prom_index} | "
            f"`#{arcade_rgb[0]:02X}{arcade_rgb[1]:02X}{arcade_rgb[2]:02X}` | "
            f"`{v9938_rgb[0]},{v9938_rgb[1]},{v9938_rgb[2]}` | {slot.role} |"
        )

    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- Slot 0 is black on both VDPs. VDP-A transparency comes from TP=1 in R#8.",
            "- Slots 10, 12, and 15 intentionally keep arcade role aliases even though",
            "  they share source RGB values with slots 3, 8, and 0.",
            "- Slots 13 and 14 preserve the remaining distinct non-black colors present",
            "  in PROM entries 0-15 so the swatch exercises every unique converted hue.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    def action() -> None:
        prom = require_input("82s123.7f")
        master_palette = decode_master_palette(prom)
        slot_map_lines, palette_payload, warnings = build_slot_lines(master_palette)

        palette_a_path = write_output("palette_a.bin", palette_payload)
        palette_b_path = write_output("palette_b.bin", palette_payload)

        SLOT_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        SLOT_MAP_PATH.write_text("\n".join(slot_map_lines) + "\n", encoding="utf-8")

        PALETTE_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
        PALETTE_DOC_PATH.write_text(render_palette_doc(master_palette), encoding="utf-8")

        print(
            "conv_palette: 32 + 32 bytes written to "
            f"{asset_relpath(palette_a_path)}, {asset_relpath(palette_b_path)}"
        )
        print(f"conv_palette: slot map written to {asset_relpath(SLOT_MAP_PATH)}")
        print(f"conv_palette: palette doc written to {asset_relpath(PALETTE_DOC_PATH)}")
        for warning in warnings:
            print(f"conv_palette warning: {warning}")

    return run_tool("conv_palette", action)


if __name__ == "__main__":
    raise SystemExit(main())
