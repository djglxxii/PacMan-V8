#!/usr/bin/env python3
"""Generate T027 live sprite SAT commit frame evidence."""

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
EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T027-sprite-sat-commit-from-game-state"

PACMAN_STATE = 0x8100
GHOST_STATE = 0x8120
SPRITE_SAT_SHADOW = 0x8300

BUTTON_BITS = {
    "right": 4,
    "left": 5,
    "down": 6,
    "up": 7,
}

CHECKPOINTS = (
    (30, 390),
    (90, 450),
    (180, 540),
)


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


def build_inputs(length: int) -> list[int]:
    frames = [input_byte(()) for _ in range(length)]
    for index in range(420, min(520, length)):
        frames[index] = input_byte(("right",))
    for index in range(520, length):
        frames[index] = input_byte(("up",))
    return frames


def write_replay(path: pathlib.Path, rom_bytes: bytes, frames: list[int]) -> None:
    data = bytearray(b"V8RR")
    data.extend(struct.pack("<B", 1))
    data.extend(hashlib.sha256(rom_bytes).digest())
    data.extend(struct.pack("<B", 0))
    data.extend(struct.pack("<I", len(frames)))
    for frame, controller1 in enumerate(frames):
        data.extend(struct.pack("<IBB", frame, controller1, 0xFF))
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


def run_checkpoint(replay_path: pathlib.Path, label: int, frame: int) -> tuple[str, dict[int, list[int]]]:
    ppm_path = EVIDENCE_DIR / f"move_seq_{label:04d}.ppm"
    argv = [
        str(HEADLESS),
        "--rom",
        str(ROM_PATH),
        "--replay",
        str(replay_path),
        "--frames",
        str(frame),
        "--dump-frame",
        str(ppm_path),
        "--peek-logical",
        f"0x{PACMAN_STATE:04X}:7",
        "--peek-logical",
        f"0x{GHOST_STATE:04X}:32",
        "--peek-logical",
        f"0x{SPRITE_SAT_SHADOW:04X}:48",
    ]
    completed = subprocess.run(argv, cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return sha256(ppm_path), parse_peeks(completed.stdout)


def format_sat_slots(sat: list[int]) -> str:
    slots: list[str] = []
    for slot in range(5):
        start = slot * 8
        y, x, pattern, palette = sat[start : start + 4]
        slots.append(f"s{slot}=xy({x:3d},{y:3d}) pat={pattern:02X} pal={palette:02X}")
    return "; ".join(slots)


def format_ghost_tiles(ghosts: list[int]) -> str:
    names = ("blinky", "pinky", "inky", "clyde")
    chunks: list[str] = []
    for index, name in enumerate(names):
        start = index * 8
        x, y, direction, mode = ghosts[start : start + 4]
        chunks.append(f"{name}=tile({x:2d},{y:2d}) dir={direction} mode={mode}")
    return "; ".join(chunks)


def main() -> int:
    if not ROM_PATH.is_file():
        raise FileNotFoundError("build/pacman.rom is missing; run python3 tools/build.py first")
    if not HEADLESS.is_file():
        raise FileNotFoundError(f"headless emulator not found: {HEADLESS}")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    rom_bytes = ROM_PATH.read_bytes()
    replay_path = EVIDENCE_DIR / "move_seq.v8r"
    write_replay(replay_path, rom_bytes, build_inputs(600))

    lines = [
        "T027 sprite SAT commit replay",
        f"ROM: {rel(ROM_PATH)} sha256={hashlib.sha256(rom_bytes).hexdigest()}",
        f"Replay: {rel(replay_path)} sha256={sha256(replay_path)}",
        "Route: neutral through PLAYING+60, right for 100 frames, then up.",
        "Labels are gameplay-sequence checkpoints; absolute frames include ATTRACT+READY warmup.",
        "",
    ]

    for label, absolute_frame in CHECKPOINTS:
        ppm_hash, peeks = run_checkpoint(replay_path, label, absolute_frame)
        pac = peeks.get(PACMAN_STATE, [0] * 7)
        ghosts = peeks.get(GHOST_STATE, [0] * 32)
        sat = peeks.get(SPRITE_SAT_SHADOW, [0] * 48)
        lines.append(
            f"move_seq_{label:04d}: absolute_frame={absolute_frame} "
            f"ppm={rel(EVIDENCE_DIR / f'move_seq_{label:04d}.ppm')} sha256={ppm_hash}"
        )
        lines.append(
            f"  pacman_fp=(0x{u16le(pac, 0):04X},0x{u16le(pac, 2):04X}) "
            f"dir={pac[4]} requested={pac[5]}"
        )
        lines.append(f"  ghosts: {format_ghost_tiles(ghosts)}")
        lines.append(f"  sat: {format_sat_slots(sat)}")

    summary_path = EVIDENCE_DIR / "sprite_commit_summary.txt"
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
