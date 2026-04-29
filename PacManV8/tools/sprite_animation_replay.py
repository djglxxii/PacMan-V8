#!/usr/bin/env python3
"""Generate T028 live sprite frame animation evidence."""

from __future__ import annotations

import hashlib
import pathlib
import re
import struct
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
HEADLESS = pathlib.Path("/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless")
EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T028-sprite-frame-animation"

PACMAN_STATE = 0x8100
COLLISION_DOT_STALL = 0x8202
GAME_FLOW_STATE = 0x8250
SPRITE_SAT_SHADOW = 0x8300
SPRITE_ANIM_STATE = 0x8390

BUTTON_BITS = {
    "right": 4,
    "left": 5,
    "down": 6,
    "up": 7,
}

PLAYING_FRAME_BASE = 377
MOUTH_CHECKPOINTS = (6, 12, 18, 24)
GHOST_WOBBLE_CHECKPOINTS = (7, 15)
STOPPED_WALL_CHECKPOINT = 108


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
    neutral = input_byte(())
    for frame in range(frame_count):
        data.extend(struct.pack("<IBB", frame, neutral, 0xFF))
    path.write_bytes(data)


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


def u16le(data: list[int], offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def ppm_dimensions(path: pathlib.Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        magic = handle.readline().strip()
        dims = handle.readline().strip()
        max_value = handle.readline().strip()
    if magic != b"P6" or max_value != b"255":
        raise ValueError(f"{path} is not a binary PPM frame dump")
    width_text, height_text = dims.split()
    return int(width_text), int(height_text)


def run_checkpoint(replay_path: pathlib.Path, output_name: str, absolute_frame: int) -> tuple[str, dict[int, list[int]]]:
    ppm_path = EVIDENCE_DIR / output_name
    argv = [
        str(HEADLESS),
        "--rom",
        str(ROM_PATH),
        "--replay",
        str(replay_path),
        "--frames",
        str(absolute_frame),
        "--dump-frame",
        str(ppm_path),
        "--peek-logical",
        f"0x{PACMAN_STATE:04X}:7",
        "--peek-logical",
        f"0x{COLLISION_DOT_STALL:04X}:1",
        "--peek-logical",
        f"0x{GAME_FLOW_STATE:04X}:13",
        "--peek-logical",
        f"0x{SPRITE_SAT_SHADOW:04X}:48",
        "--peek-logical",
        f"0x{SPRITE_ANIM_STATE:04X}:6",
    ]
    completed = subprocess.run(argv, cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    if ppm_dimensions(ppm_path) != (256, 212):
        raise ValueError(f"{rel(ppm_path)} is not 256x212")
    return sha256(ppm_path), parse_peeks(completed.stdout)


def sat_slot(sat: list[int], slot: int) -> tuple[int, int, int, int]:
    offset = slot * 8
    y, x, pattern, palette = sat[offset : offset + 4]
    return x, y, pattern, palette


def format_sat_slots(sat: list[int]) -> str:
    chunks: list[str] = []
    for slot in range(5):
        x, y, pattern, palette = sat_slot(sat, slot)
        chunks.append(f"s{slot}=xy({x:3d},{y:3d}) pat={pattern:02X} pal={palette:02X}")
    return "; ".join(chunks)


def append_checkpoint(lines: list[str], label: str, absolute_frame: int, ppm_hash: str, peeks: dict[int, list[int]]) -> None:
    pac = peeks.get(PACMAN_STATE, [0] * 7)
    stall = peeks.get(COLLISION_DOT_STALL, [0])
    flow = peeks.get(GAME_FLOW_STATE, [0] * 13)
    sat = peeks.get(SPRITE_SAT_SHADOW, [0] * 48)
    anim = peeks.get(SPRITE_ANIM_STATE, [0] * 6)
    ppm_path = EVIDENCE_DIR / f"{label}.ppm"
    lines.append(
        f"{label}: absolute_frame={absolute_frame} ppm={rel(ppm_path)} sha256={ppm_hash}"
    )
    lines.append(
        f"  flow_state={flow[0]} flow_frame={u16le(flow, 2)} dot_stall={stall[0]} "
        f"pacman_fp=(0x{u16le(pac, 0):04X},0x{u16le(pac, 2):04X}) "
        f"dir={pac[4]} requested={pac[5]}"
    )
    lines.append(
        f"  anim: pac_counter={anim[0]} pac_phase={anim[1]} "
        f"ghost_counter={anim[2]} ghost_phase={anim[3]}"
    )
    lines.append(f"  sat: {format_sat_slots(sat)}")


def main() -> int:
    if not ROM_PATH.is_file():
        raise FileNotFoundError("build/pacman.rom is missing; run python3 tools/build.py first")
    if not HEADLESS.is_file():
        raise FileNotFoundError(f"headless emulator not found: {HEADLESS}")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    rom_bytes = ROM_PATH.read_bytes()
    replay_path = EVIDENCE_DIR / "anim_seq.v8r"
    max_checkpoint = max((*MOUTH_CHECKPOINTS, *GHOST_WOBBLE_CHECKPOINTS, STOPPED_WALL_CHECKPOINT))
    write_replay(replay_path, rom_bytes, PLAYING_FRAME_BASE + max_checkpoint + 30)

    lines = [
        "T028 sprite frame animation replay",
        f"ROM: {rel(ROM_PATH)} sha256={hashlib.sha256(rom_bytes).hexdigest()}",
        f"Replay: {rel(replay_path)} sha256={sha256(replay_path)}",
        "Route: neutral controller; Pac-Man keeps his initialized leftward direction until he reaches a wall.",
        "Labels are gameplay-sequence checkpoints; absolute frames include ATTRACT+READY warmup.",
        "Pac-Man phases: 0=open, 1=half, 2=closed, 3=half.",
        "",
    ]

    for label in MOUTH_CHECKPOINTS:
        output_name = f"anim_seq_{label:04d}.ppm"
        absolute_frame = PLAYING_FRAME_BASE + label
        ppm_hash, peeks = run_checkpoint(replay_path, output_name, absolute_frame)
        append_checkpoint(lines, f"anim_seq_{label:04d}", absolute_frame, ppm_hash, peeks)

    for label in GHOST_WOBBLE_CHECKPOINTS:
        output_name = f"ghost_wobble_{label:04d}.ppm"
        absolute_frame = PLAYING_FRAME_BASE + label
        ppm_hash, peeks = run_checkpoint(replay_path, output_name, absolute_frame)
        append_checkpoint(lines, f"ghost_wobble_{label:04d}", absolute_frame, ppm_hash, peeks)

    stopped_output = f"stopped_wall_{STOPPED_WALL_CHECKPOINT:04d}.ppm"
    stopped_absolute = PLAYING_FRAME_BASE + STOPPED_WALL_CHECKPOINT
    ppm_hash, peeks = run_checkpoint(replay_path, stopped_output, stopped_absolute)
    append_checkpoint(lines, f"stopped_wall_{STOPPED_WALL_CHECKPOINT:04d}", stopped_absolute, ppm_hash, peeks)

    summary_path = EVIDENCE_DIR / "sprite_animation_summary.txt"
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
