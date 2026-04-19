#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

import generate_sprite_review_shadow as review


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SPRITES_PATH = REPO_ROOT / "assets" / "sprites.bin"
SPRITE_COLORS_PATH = REPO_ROOT / "assets" / "sprite_colors.bin"
PALETTE_A_PATH = REPO_ROOT / "assets" / "palette_a.bin"
SHADOW_INCLUDE_PATH = REPO_ROOT / "src" / "sprite_review_shadow.inc"
SHADOW_SUMMARY_PATH = REPO_ROOT / "assets" / "sprite_review_shadow_summary.txt"

EXPECTED_HASHES = {
    "assets/sprites.bin": "28e586b9ff65658f94928b190aff143a514cace76a5c95409ad989666407304b",
    "assets/sprite_colors.bin": "8795faea939d4fffaef5cb60fbf94bfaade78540deafb919564b17eec9bb5308",
    "assets/palette_a.bin": "7e821cb405d1d30ae6ef29bf75fde5a87637c7e381566eaf750f895dc834b78f",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: pathlib.Path) -> pathlib.Path:
    return path.resolve().relative_to(REPO_ROOT)


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def parse_ppm(path: pathlib.Path) -> tuple[int, int, str]:
    data = path.read_bytes()
    parts = data.split(b"\n", 3)
    if len(parts) != 4:
        raise ValueError("PPM header is incomplete.")
    magic, dimensions, max_value, body = parts
    if magic != b"P6":
        raise ValueError(f"Unexpected PPM magic {magic!r}.")
    width_text, height_text = dimensions.split()
    width = int(width_text)
    height = int(height_text)
    if max_value != b"255":
        raise ValueError(f"Unexpected PPM max value {max_value!r}.")
    expected_bytes = width * height * 3
    if len(body) != expected_bytes:
        raise ValueError(f"PPM body is {len(body)} bytes; expected {expected_bytes}.")
    return width, height, hashlib.sha256(data).hexdigest()


def format_hex(values: list[int]) -> str:
    return " ".join(f"{value:02X}" for value in values)


def generated_include_matches(sat: list[int], colors: list[int]) -> bool:
    expected = "\n".join(review.include_lines(sat, colors))
    return SHADOW_INCLUDE_PATH.read_text(encoding="ascii") == expected


def write_vectors(
    path: pathlib.Path,
    sat: list[int],
    colors: list[int],
    sprite_records: list[dict[str, int | str]],
    frame_hash: str | None,
    frame_dimensions: tuple[int, int] | None,
) -> None:
    lines = [
        "T013/T015 sprite render vectors",
        "",
        "VRAM layout:",
        "- pattern generator: 0x7000, R#6=0x0E",
        "- color table: 0x7A00, SAT base minus 512 bytes",
        "- attribute table: 0x7C00, R#5=0xF8/R#11=0x00",
        "",
        "Asset hashes:",
    ]
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        actual = sha256(REPO_ROOT / rel_path)
        lines.append(f"- {rel_path}: {actual} expected={expected_hash}")
    lines.extend(
        [
            f"- src/sprite_review_shadow.inc: {sha256(SHADOW_INCLUDE_PATH)}",
            f"- assets/sprite_review_shadow_summary.txt: {sha256(SHADOW_SUMMARY_PATH)}",
            "",
            "Slot assignments:",
        ]
    )
    for sprite in sprite_records:
        slot = int(sprite["slot"])
        sat_start = slot * 8
        color_start = slot * review.SPRITE_COLOR_STRIDE
        lines.append(
            f"- slot {slot}: {sprite['name']} state={sprite['state']} "
            f"arcade_tile=({sprite['tile_x']},{sprite['tile_y']}) "
            f"xy=({sprite['x']},{sprite['y']}) sprite_id={sprite['sprite_id']} "
            f"pattern={sprite['pattern']} palette={sprite['palette']} "
            f"sat={format_hex(sat[sat_start : sat_start + 8])} "
            f"colors={format_hex(colors[color_start : color_start + review.SPRITE_COLOR_STRIDE])}"
        )
    lines.append(f"- slot 5: reserved terminator sat={format_hex(sat[40:48])}")
    lines.extend(
        [
            "",
            "Determinism:",
            "- animation source: deterministic review state, frame counter initialized to 0",
            "- coordinate source: T015 transform from arcade 8.8 positions to fitted V8 pixels",
        ]
    )
    if frame_hash is not None and frame_dimensions is not None:
        lines.append(
            f"- frame dump: {frame_dimensions[0]}x{frame_dimensions[1]} sha256={frame_hash}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic T013 sprite render data.")
    parser.add_argument("--vectors-output", type=pathlib.Path, required=True)
    parser.add_argument("--frame-dump", type=pathlib.Path)
    args = parser.parse_args()

    failures: list[str] = []
    source_colors = review.load_source_colors(SPRITE_COLORS_PATH)
    coordmap = review.transform.load_coordmap(review.COORDMAP_PATH)
    sat, colors, sprite_records = review.build_review_shadow(source_colors, coordmap)

    require(SPRITES_PATH.stat().st_size == 2048, "assets/sprites.bin must be 2048 bytes", failures)
    require(
        SPRITE_COLORS_PATH.stat().st_size == 1024,
        "assets/sprite_colors.bin must be 1024 bytes",
        failures,
    )
    require(PALETTE_A_PATH.stat().st_size == 32, "assets/palette_a.bin must be 32 bytes", failures)
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        actual = sha256(REPO_ROOT / rel_path)
        require(actual == expected_hash, f"{rel_path} hash {actual} != {expected_hash}", failures)

    require(len(sat) == 48, "SAT shadow must contain 6 Mode 2 slots", failures)
    require(len(colors) == 96, "Color shadow must contain 6 row-color records", failures)
    require(sat[40] == 0xD0, "slot 5 must be the reserved terminator", failures)
    require(generated_include_matches(sat, colors), "generated shadow include is stale", failures)

    for sprite in sprite_records:
        slot = int(sprite["slot"])
        sat_start = slot * 8
        expected_pattern = int(sprite["sprite_id"]) * 4
        require(
            sat[sat_start + 2] == expected_pattern,
            f"slot {slot} pattern does not equal sprite_id * 4",
            failures,
        )
        row_start = slot * review.SPRITE_COLOR_STRIDE
        slot_rows = colors[row_start : row_start + review.SPRITE_COLOR_STRIDE]
        require(
            any(value != 0 for value in slot_rows),
            f"slot {slot} color rows must include visible rows",
            failures,
        )

    frame_hash: str | None = None
    frame_dimensions: tuple[int, int] | None = None
    if args.frame_dump is not None:
        width, height, frame_hash = parse_ppm(args.frame_dump)
        frame_dimensions = (width, height)
        require((width, height) == (256, 212), "frame dump must be 256x212", failures)

    write_vectors(args.vectors_output, sat, colors, sprite_records, frame_hash, frame_dimensions)

    if failures:
        print("sprite_render_tests: FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("sprite_render_tests: 8/8 passed")
    print(f"sprites.bin SHA-256: {sha256(SPRITES_PATH)}")
    print(f"sprite_colors.bin SHA-256: {sha256(SPRITE_COLORS_PATH)}")
    print(f"palette_a.bin SHA-256: {sha256(PALETTE_A_PATH)}")
    print(f"SAT shadow SHA-256: {hashlib.sha256(bytes(sat)).hexdigest()}")
    print(f"Color shadow SHA-256: {hashlib.sha256(bytes(colors)).hexdigest()}")
    if frame_hash is not None:
        print(f"Frame dump SHA-256: {frame_hash}")
    print(f"Vectors: {rel(args.vectors_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
