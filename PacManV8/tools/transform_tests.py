#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib
from dataclasses import dataclass

import coordinate_transform as transform
import generate_sprite_review_shadow as sprite_shadow


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SEMANTIC_PATH = REPO_ROOT / "assets" / "maze_semantic.bin"
COORDMAP_PATH = REPO_ROOT / "assets" / "maze_v8_coordmap.bin"
SPRITE_COLORS_PATH = REPO_ROOT / "assets" / "sprite_colors.bin"
PALETTE_A_PATH = REPO_ROOT / "assets" / "palette_a.bin"
PALETTE_B_PATH = REPO_ROOT / "assets" / "palette_b.bin"
SHADOW_INCLUDE_PATH = REPO_ROOT / "src" / "sprite_review_shadow.inc"
SHADOW_SUMMARY_PATH = REPO_ROOT / "assets" / "sprite_review_shadow_summary.txt"

EXPECTED_HASHES = {
    "assets/maze_semantic.bin": "ca8c00e7b76da593a4fc2e9c8f064dde3ac0d062ee5cce1687500850325db111",
    "assets/maze_v8_coordmap.bin": "551bfd06927f84482f59f3c215ba39bd70b1659c3b04ba600feb80095fc567f2",
    "assets/sprite_colors.bin": "8795faea939d4fffaef5cb60fbf94bfaade78540deafb919564b17eec9bb5308",
    "assets/palette_a.bin": "7e821cb405d1d30ae6ef29bf75fde5a87637c7e381566eaf750f895dc834b78f",
    "assets/palette_b.bin": "99213a904be24a870047e41d1f2df48981fa9440c4e56959c7f74dd6fcd2a70e",
}


@dataclass(frozen=True)
class AnchorSample:
    name: str
    tile_x: int
    tile_y: int
    expected_class: str


ANCHOR_SAMPLES = [
    AnchorSample("left_tunnel_exit", 0, 17, "TUNNEL"),
    AnchorSample("right_tunnel_exit", 27, 17, "TUNNEL"),
    AnchorSample("ghost_house_door_left", 13, 15, "GHOST_DOOR"),
    AnchorSample("ghost_house_door_right", 14, 15, "GHOST_DOOR"),
    AnchorSample("upper_left_pellet_corner", 1, 4, "PELLET"),
    AnchorSample("upper_right_pellet_corner", 26, 4, "PELLET"),
    AnchorSample("lower_left_pellet_corner", 1, 32, "PELLET"),
    AnchorSample("lower_right_pellet_corner", 26, 32, "PELLET"),
    AnchorSample("upper_left_energizer", 1, 6, "ENERGIZER"),
    AnchorSample("upper_right_energizer", 26, 6, "ENERGIZER"),
    AnchorSample("lower_left_energizer", 1, 26, "ENERGIZER"),
    AnchorSample("lower_right_energizer", 26, 26, "ENERGIZER"),
]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: pathlib.Path) -> pathlib.Path:
    return path.resolve().relative_to(REPO_ROOT)


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


def boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def generated_include_matches(sat: list[int], colors: list[int]) -> bool:
    expected = "\n".join(sprite_shadow.include_lines(sat, colors))
    return SHADOW_INCLUDE_PATH.read_text(encoding="ascii") == expected


def semantic_class_name(semantic: bytes, tile_x: int, tile_y: int) -> str:
    value = semantic[tile_y * transform.ARCADE_WIDTH + tile_x]
    if 0 <= value < len(transform.CLASS_NAMES):
        return transform.CLASS_NAMES[value]
    return f"UNKNOWN_{value}"


def write_vectors(
    path: pathlib.Path,
    coordmap: bytes,
    semantic: bytes,
    sat: list[int],
    colors: list[int],
    sprite_records: list[dict[str, int | str]],
    frame_hash: str | None,
    frame_dimensions: tuple[int, int] | None,
) -> None:
    lines = [
        "T015 coordinate transform vectors",
        "",
        "Transform constants:",
        f"- screen: {transform.SCREEN_WIDTH}x{transform.SCREEN_HEIGHT}",
        f"- arcade grid: {transform.ARCADE_WIDTH}x{transform.ARCADE_HEIGHT} tiles, 8.8 fixed-point pixels",
        f"- mapped maze rows: {transform.MAZE_TOP}-{transform.MAZE_TOP + transform.MAZE_ROWS - 1}",
        f"- maze area: x={transform.MAZE_X}-{transform.MAZE_X + transform.MAZE_WIDTH - 1}, "
        f"y={transform.MAZE_Y}-{transform.MAZE_Y + transform.MAZE_HEIGHT - 1}",
        f"- HUD bands: top y=0-{transform.HUD_HEIGHT - 1}, bottom y={transform.STATUS_Y}-{transform.SCREEN_HEIGHT - 1}",
        "- orientation: no rotation; arcade x maps to V8 x and arcade y maps to fitted V8 y",
        "- sprite anchor: transformed entity center minus 8 pixels on each axis",
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
            f"- SAT shadow: {hashlib.sha256(bytes(sat)).hexdigest()}",
            f"- color shadow: {hashlib.sha256(bytes(colors)).hexdigest()}",
            "",
            "Sprite slots:",
        ]
    )
    for sprite in sprite_records:
        slot = int(sprite["slot"])
        sat_start = slot * 8
        color_start = slot * sprite_shadow.SPRITE_COLOR_STRIDE
        lines.append(
            f"- slot {slot}: {sprite['name']} state={sprite['state']} "
            f"arcade_tile=({sprite['tile_x']},{sprite['tile_y']}) "
            f"fixed=0x{int(sprite['arcade_x_fp']):04X},0x{int(sprite['arcade_y_fp']):04X} "
            f"cell={sprite['cell_class']} center=({sprite['screen_center_x']},{sprite['screen_center_y']}) "
            f"sprite_xy=({sprite['x']},{sprite['y']}) sat={format_hex(sat[sat_start : sat_start + 8])} "
            f"colors={format_hex(colors[color_start : color_start + sprite_shadow.SPRITE_COLOR_STRIDE])}"
        )
    lines.append(f"- slot 5: reserved terminator sat={format_hex(sat[40:48])}")
    lines.extend(["", "Anchor samples:"])
    for sample in ANCHOR_SAMPLES:
        result = transform.transform_tile_center(coordmap, sample.tile_x, sample.tile_y)
        actual_class = semantic_class_name(semantic, sample.tile_x, sample.tile_y)
        lines.append(
            f"- {sample.name}: tile=({sample.tile_x},{sample.tile_y}) class={actual_class} "
            f"expected_class={sample.expected_class} center=({result.screen_center_x},{result.screen_center_y}) "
            f"rect=({result.cell.x},{result.cell.y},{result.cell.width},{result.cell.height}) "
            f"flags=0x{result.cell.flags:02X}"
        )
    lines.extend(["", "8.8 sub-tile samples:"])
    subtile_samples = [
        ("pacman_start_center", transform.fixed_tile_center(14), transform.fixed_tile_center(26)),
        ("one_pixel_right", transform.fixed_tile_center(14) + 0x0100, transform.fixed_tile_center(26)),
        ("two_pixels_down", transform.fixed_tile_center(14), transform.fixed_tile_center(26) + 0x0200),
        ("left_tunnel_wrap_input", transform.ARCADE_MAZE_WIDTH_PX << 8, transform.fixed_tile_center(17)),
    ]
    for name, x_fp, y_fp in subtile_samples:
        result = transform.transform_entity(coordmap, x_fp, y_fp)
        lines.append(
            f"- {name}: fixed=0x{x_fp:04X},0x{y_fp:04X} tile=({result.tile_x},{result.tile_y}) "
            f"center=({result.screen_center_x},{result.screen_center_y}) sprite_xy=({result.sprite_x},{result.sprite_y})"
        )
    if frame_hash is not None and frame_dimensions is not None:
        lines.extend(
            [
                "",
                f"Frame dump: {frame_dimensions[0]}x{frame_dimensions[1]} sha256={frame_hash}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate T015 gameplay-to-screen coordinate transform.")
    parser.add_argument("--vectors-output", type=pathlib.Path, required=True)
    parser.add_argument("--frame-dump", type=pathlib.Path)
    args = parser.parse_args()

    failures: list[str] = []
    checks = 0

    def require(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(message)

    coordmap = transform.load_coordmap(COORDMAP_PATH)
    semantic = SEMANTIC_PATH.read_bytes()
    source_colors = sprite_shadow.load_source_colors(SPRITE_COLORS_PATH)
    sat, colors, sprite_records = sprite_shadow.build_review_shadow(source_colors, coordmap)

    require(len(semantic) == transform.ARCADE_WIDTH * transform.ARCADE_HEIGHT, "semantic grid must be 28x36 bytes")
    require(len(coordmap) == transform.COORDMAP_BYTES, "coordmap must be 28x36 records")
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        actual = sha256(REPO_ROOT / rel_path)
        require(actual == expected_hash, f"{rel_path} hash {actual} != {expected_hash}")

    top_left = transform.record_at(coordmap, 0, transform.MAZE_TOP)
    bottom_right = transform.record_at(coordmap, 27, transform.MAZE_TOP + transform.MAZE_ROWS - 1)
    require(top_left.x == 16 and top_left.y == 8, "mapped maze must begin at V8 pixel (16,8)")
    require(
        bottom_right.x + bottom_right.width == 240 and bottom_right.y + bottom_right.height == 204,
        "mapped maze must end before the status band at x=240,y=204",
    )
    require(generated_include_matches(sat, colors), "generated sprite shadow include is stale")
    require(SHADOW_SUMMARY_PATH.is_file(), "sprite transform summary must exist")
    require(len(sat) == 48 and sat[40] == 0xD0, "SAT shadow must have five sprites plus slot-5 terminator")
    require(len(colors) == 96, "color shadow must have six 16-row records")

    fixed_t013_positions = [(56, 96), (88, 96), (120, 96), (152, 96), (184, 96)]
    actual_positions = [(int(sprite["x"]), int(sprite["y"])) for sprite in sprite_records]
    require(actual_positions != fixed_t013_positions, "sprite positions must not be the fixed T013 review row")

    boxes: list[tuple[int, int, int, int]] = []
    for sprite in sprite_records:
        result = transform.transform_tile_center(coordmap, int(sprite["tile_x"]), int(sprite["tile_y"]))
        require(
            (result.sprite_x, result.sprite_y) == (int(sprite["x"]), int(sprite["y"])),
            f"slot {sprite['slot']} SAT position must match transform output",
        )
        require(transform.sprite_box_clear_of_hud(result), f"slot {sprite['slot']} sprite box must not enter HUD/status bands")
        require(0 <= result.sprite_x <= transform.SCREEN_WIDTH - transform.SPRITE_SIZE, f"slot {sprite['slot']} x must fit on screen")
        box = (
            result.sprite_x,
            result.sprite_y,
            result.sprite_x + transform.SPRITE_SIZE,
            result.sprite_y + transform.SPRITE_SIZE,
        )
        require(not any(boxes_overlap(box, existing) for existing in boxes), f"slot {sprite['slot']} sprite box must not overlap earlier slots")
        boxes.append(box)

    for sample in ANCHOR_SAMPLES:
        result = transform.transform_tile_center(coordmap, sample.tile_x, sample.tile_y)
        actual_class = semantic_class_name(semantic, sample.tile_x, sample.tile_y)
        require(actual_class == sample.expected_class, f"{sample.name} semantic class must be {sample.expected_class}")
        require(result.cell.mapped, f"{sample.name} coordmap record must be mapped")
        require(
            transform.MAZE_X <= result.screen_center_x < transform.MAZE_X + transform.MAZE_WIDTH
            and transform.MAZE_Y <= result.screen_center_y < transform.MAZE_Y + transform.MAZE_HEIGHT,
            f"{sample.name} center must be inside mapped maze area",
        )

    center = transform.transform_tile_center(coordmap, 14, 26)
    one_right = transform.transform_entity(coordmap, center.arcade_x_fp + 0x0100, center.arcade_y_fp)
    two_down = transform.transform_entity(coordmap, center.arcade_x_fp, center.arcade_y_fp + 0x0200)
    wrapped = transform.transform_entity(coordmap, transform.ARCADE_MAZE_WIDTH_PX << 8, transform.fixed_tile_center(17))
    require(one_right.screen_center_x == center.screen_center_x + 1, "one arcade pixel right must move one V8 pixel right")
    require(two_down.screen_center_y > center.screen_center_y, "vertical 8.8 movement must advance inside compressed row")
    require(wrapped.tile_x == 0 and wrapped.screen_center_x == transform.MAZE_X, "x input at maze width must wrap to left edge")

    frame_hash: str | None = None
    frame_dimensions: tuple[int, int] | None = None
    if args.frame_dump is not None:
        width, height, frame_hash = parse_ppm(args.frame_dump)
        frame_dimensions = (width, height)
        require((width, height) == (transform.SCREEN_WIDTH, transform.SCREEN_HEIGHT), "frame dump must be 256x212")

    write_vectors(args.vectors_output, coordmap, semantic, sat, colors, sprite_records, frame_hash, frame_dimensions)

    if failures:
        print("transform_tests: FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"transform_tests: {checks}/{checks} passed")
    for rel_path in EXPECTED_HASHES:
        print(f"{rel_path}: {sha256(REPO_ROOT / rel_path)}")
    print(f"SAT shadow SHA-256: {hashlib.sha256(bytes(sat)).hexdigest()}")
    print(f"Color shadow SHA-256: {hashlib.sha256(bytes(colors)).hexdigest()}")
    if frame_hash is not None:
        print(f"Frame dump SHA-256: {frame_hash}")
    print(f"Vectors: {rel(args.vectors_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
