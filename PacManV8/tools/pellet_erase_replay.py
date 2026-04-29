#!/usr/bin/env python3
"""Generate T029 pellet erase framebuffer evidence."""

from __future__ import annotations

import hashlib
import pathlib
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
HEADLESS = pathlib.Path("/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless")
EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T029-pellet-erase-to-vdp-b-framebuffer"

COLLISION_PELLET_COUNT = 0x81FE
COLLISION_ERASE_PENDING = 0x8203
PACMAN_STATE = 0x8100
GAME_FLOW_STATE = 0x8250
PALETTE_B_PATH = REPO_ROOT / "assets" / "palette_b.bin"

BUTTON_BITS = {
    "right": 4,
    "left": 5,
    "down": 6,
    "up": 7,
}

PLAYING_FRAME_BASE = 377
BEFORE_FRAME = 18
AFTER_FRAME = 63
EXPECTED_PELLET_DELTA = 5
TARGET_TILES = ((17, 26), (18, 26), (19, 26), (20, 26), (21, 26))
CONTROL_TILE = (12, 26)


def rel(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_byte(buttons: tuple[str, ...]) -> int:
    value = 0xFF
    for button in buttons:
        value &= ~(1 << BUTTON_BITS[button])
    return value


def write_replay(path: pathlib.Path, rom_bytes: bytes, frame_count: int) -> None:
    data = bytearray(b"V8RR")
    data.extend(struct.pack("<B", 1))
    data.extend(hashlib.sha256(rom_bytes).digest())
    data.extend(struct.pack("<B", 0))
    data.extend(struct.pack("<I", frame_count))
    right = input_byte(("right",))
    for frame in range(frame_count):
        data.extend(struct.pack("<IBB", frame, right, 0xFF))
    path.write_bytes(data)


def parse_ppm(path: pathlib.Path) -> tuple[int, int, bytes]:
    with path.open("rb") as handle:
        magic = handle.readline().strip()
        dims = handle.readline().strip()
        max_value = handle.readline().strip()
        payload = handle.read()
    if magic != b"P6" or max_value != b"255":
        raise ValueError(f"{rel(path)} is not a binary PPM")
    width_text, height_text = dims.split()
    width = int(width_text)
    height = int(height_text)
    if len(payload) != width * height * 3:
        raise ValueError(f"{rel(path)} has an unexpected payload size")
    return width, height, payload


def write_ppm(path: pathlib.Path, width: int, height: int, payload: bytes) -> None:
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + payload)


def decode_palette() -> list[tuple[int, int, int]]:
    palette = PALETTE_B_PATH.read_bytes()
    colors = []
    for index in range(16):
        byte0 = palette[index * 2]
        byte1 = palette[index * 2 + 1]
        red = (byte0 >> 4) & 0x07
        green = byte0 & 0x07
        blue = byte1 & 0x07
        colors.append(tuple(int(channel * 255 / 7 + 0.5) for channel in (red, green, blue)))
    return colors


def write_vdpb_layer_ppm(vram_path: pathlib.Path, ppm_path: pathlib.Path) -> None:
    vram = vram_path.read_bytes()
    if len(vram) < 212 * 128:
        raise ValueError(f"{rel(vram_path)} is too small for a Graphic 4 framebuffer")
    colors = decode_palette()
    payload = bytearray()
    for byte in vram[: 212 * 128]:
        payload.extend(colors[(byte >> 4) & 0x0F])
        payload.extend(colors[byte & 0x0F])
    write_ppm(ppm_path, 256, 212, bytes(payload))


def combine_before_after(before_path: pathlib.Path, after_path: pathlib.Path, output_path: pathlib.Path) -> None:
    width, height, before = parse_ppm(before_path)
    after_width, after_height, after = parse_ppm(after_path)
    if (width, height) != (after_width, after_height):
        raise ValueError("before/after frame dimensions differ")
    rows = []
    row_bytes = width * 3
    for y in range(height):
        start = y * row_bytes
        rows.append(before[start : start + row_bytes] + after[start : start + row_bytes])
    write_ppm(output_path, width * 2, height, b"".join(rows))


def parse_peeks(text: str) -> dict[int, list[int]]:
    result: dict[int, list[int]] = {}
    current_base: int | None = None
    current_bytes: list[int] = []
    for line in text.splitlines():
        header = re.match(r"^logical 0x([0-9A-Fa-f]{4}) .* length ([0-9]+)$", line)
        if header is not None:
            if current_base is not None:
                result[current_base] = current_bytes
            current_base = int(header.group(1), 16)
            current_bytes = []
            continue
        match = re.match(r"^\s+0x([0-9A-Fa-f]{4}):((?: [0-9A-Fa-f]{2})+)$", line)
        if match is None:
            continue
        current_bytes.extend(int(item, 16) for item in match.group(2).split())
    if current_base is not None:
        result[current_base] = current_bytes
    return result


def u16le(data: list[int], offset: int = 0) -> int:
    return data[offset] | (data[offset + 1] << 8)


def run_frame(
    replay_path: pathlib.Path,
    frame: int,
    composite_path: pathlib.Path,
    vram_path: pathlib.Path,
) -> dict[int, list[int]]:
    argv = [
        str(HEADLESS),
        "--rom",
        str(ROM_PATH),
        "--replay",
        str(replay_path),
        "--frames",
        str(frame),
        "--dump-frame",
        str(composite_path),
        "--dump-vram-b",
        str(vram_path),
        "--peek-logical",
        f"0x{PACMAN_STATE:04X}:7",
        "--peek-logical",
        f"0x{COLLISION_PELLET_COUNT:04X}:2",
        "--peek-logical",
        f"0x{COLLISION_ERASE_PENDING:04X}:4",
        "--peek-logical",
        f"0x{GAME_FLOW_STATE:04X}:4",
    ]
    completed = subprocess.run(argv, cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    width, height, _ = parse_ppm(composite_path)
    if (width, height) != (256, 212):
        raise ValueError(f"{rel(composite_path)} is not 256x212")
    return parse_peeks(completed.stdout)


def pixel(payload: bytes, width: int, x: int, y: int) -> tuple[int, int, int]:
    offset = (y * width + x) * 3
    return payload[offset], payload[offset + 1], payload[offset + 2]


def pellet_pixels_in_tile(path: pathlib.Path, tile_x: int, tile_y: int) -> int:
    import coordinate_transform as transform

    width, _height, payload = parse_ppm(path)
    pellet_rgb = (219, 219, 255)
    coordmap = transform.load_coordmap()
    cell = transform.record_at(coordmap, tile_x, tile_y)
    count = 0
    for y in range(cell.y, cell.y + cell.height):
        for x in range(cell.x, cell.x + cell.width):
            if pixel(payload, width, x, y) == pellet_rgb:
                count += 1
    return count


def changed_pixels(before_path: pathlib.Path, after_path: pathlib.Path) -> int:
    width, height, before = parse_ppm(before_path)
    after_width, after_height, after = parse_ppm(after_path)
    if (width, height) != (after_width, after_height):
        raise ValueError("before/after dimensions differ")
    return sum(1 for offset in range(0, len(before), 3) if before[offset : offset + 3] != after[offset : offset + 3])


def main() -> int:
    if not ROM_PATH.is_file():
        raise FileNotFoundError("build/pacman.rom is missing; run python3 tools/build.py first")
    if not HEADLESS.is_file():
        raise FileNotFoundError(f"headless emulator not found: {HEADLESS}")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    rom_bytes = ROM_PATH.read_bytes()
    replay_path = EVIDENCE_DIR / "pellet_erase.v8r"
    write_replay(replay_path, rom_bytes, PLAYING_FRAME_BASE + AFTER_FRAME + 20)

    before_composite_path = EVIDENCE_DIR / "before_composite.ppm"
    after_composite_path = EVIDENCE_DIR / "after_composite.ppm"
    before_vram_path = EVIDENCE_DIR / "before_vdpb.vram"
    after_vram_path = EVIDENCE_DIR / "after_vdpb.vram"
    before_path = EVIDENCE_DIR / "before_vdpb.ppm"
    after_path = EVIDENCE_DIR / "after_vdpb.ppm"
    combined_path = EVIDENCE_DIR / "before_after.ppm"
    before_peeks = run_frame(
        replay_path,
        PLAYING_FRAME_BASE + BEFORE_FRAME,
        before_composite_path,
        before_vram_path,
    )
    after_peeks = run_frame(
        replay_path,
        PLAYING_FRAME_BASE + AFTER_FRAME,
        after_composite_path,
        after_vram_path,
    )
    write_vdpb_layer_ppm(before_vram_path, before_path)
    write_vdpb_layer_ppm(after_vram_path, after_path)
    combine_before_after(before_path, after_path, combined_path)

    before_pellets = u16le(before_peeks.get(COLLISION_PELLET_COUNT, [0, 0]))
    after_pellets = u16le(after_peeks.get(COLLISION_PELLET_COUNT, [0, 0]))
    before_target_pixels = [pellet_pixels_in_tile(before_path, x, y) for x, y in TARGET_TILES]
    after_target_pixels = [pellet_pixels_in_tile(after_path, x, y) for x, y in TARGET_TILES]
    before_control_pixels = pellet_pixels_in_tile(before_path, *CONTROL_TILE)
    after_control_pixels = pellet_pixels_in_tile(after_path, *CONTROL_TILE)
    delta = before_pellets - after_pellets
    changed = changed_pixels(before_path, after_path)

    lines = [
        "T029 pellet erase replay",
        f"ROM: {rel(ROM_PATH)} sha256={hashlib.sha256(rom_bytes).hexdigest()}",
        f"Replay: {rel(replay_path)} sha256={sha256(replay_path)}",
        "Route: hold RIGHT; before is after tiles 15-16 are eaten, after is after the visible 17-21 run is eaten.",
        f"Before frame: {PLAYING_FRAME_BASE + BEFORE_FRAME} vdpb_ppm={rel(before_path)} sha256={sha256(before_path)}",
        f"After frame: {PLAYING_FRAME_BASE + AFTER_FRAME} vdpb_ppm={rel(after_path)} sha256={sha256(after_path)}",
        f"Composite before: {rel(before_composite_path)} sha256={sha256(before_composite_path)}",
        f"Composite after: {rel(after_composite_path)} sha256={sha256(after_composite_path)}",
        f"Combined VDP-B frame: {rel(combined_path)} sha256={sha256(combined_path)}",
        f"Collision pellet count: {before_pellets} -> {after_pellets} delta={delta}",
        f"Target tiles: {TARGET_TILES}",
        f"Target pellet-color pixels before: {before_target_pixels}",
        f"Target pellet-color pixels after: {after_target_pixels}",
        f"Control tile {CONTROL_TILE} pellet-color pixels: {before_control_pixels} -> {after_control_pixels}",
        f"Changed RGB pixels between before/after: {changed}",
        f"Erase queue after frame: {after_peeks.get(COLLISION_ERASE_PENDING, [0, 0, 0, 0])}",
    ]

    if delta != EXPECTED_PELLET_DELTA:
        raise ValueError(f"expected pellet count delta {EXPECTED_PELLET_DELTA}, got {delta}")
    if any(count == 0 for count in before_target_pixels):
        raise ValueError(f"expected every target tile to contain pellet-color pixels before erase, got {before_target_pixels}")
    if any(count != 0 for count in after_target_pixels):
        raise ValueError(f"expected every target tile to contain no pellet-color pixels after erase, got {after_target_pixels}")
    if before_control_pixels == 0 or after_control_pixels == 0:
        raise ValueError("control pellet was not visible in both before and after frames")
    if after_peeks.get(COLLISION_ERASE_PENDING, [1])[0] != 0:
        raise ValueError("erase queue is still pending in the after frame")

    summary_path = EVIDENCE_DIR / "pellet_erase_summary.txt"
    summary_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, file=sys.stdout, end="")
        if error.stderr:
            print(error.stderr, file=sys.stderr, end="")
        raise SystemExit(error.returncode) from error
