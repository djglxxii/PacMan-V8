#!/usr/bin/env python3
"""T024 controller input verification.

Builds the ROM, creates a replay with directional inputs in PLAYING state,
and asserts PACMAN_REQUESTED_DIR updates correctly.
"""

from __future__ import annotations

import hashlib
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T024-controller-input-to-movement-request"
HEADLESS = (
    REPO_ROOT.parent / "Vanguard8" / "cmake-build-debug" / "src" / "vanguard8_headless"
)

DIR_UP = 0
DIR_LEFT = 1
DIR_DOWN = 2
DIR_RIGHT = 3
DIR_NONE = 4
DIR_NAMES = {DIR_UP: "UP", DIR_LEFT: "LEFT", DIR_DOWN: "DOWN", DIR_RIGHT: "RIGHT", DIR_NONE: "NONE"}

# Active-low controller bits.
# bit 7 = up, bit 6 = down, bit 5 = left, bit 4 = right, bit 0 = start
BUTTON_MASKS = {"up": 0x80, "down": 0x40, "left": 0x20, "right": 0x10}

# PACMAN_REQUESTED_DIR is at MOVEMENT_STATE_BASE + 5 = 0x8100 + 5 = 0x8105
PACMAN_REQUESTED_DIR_ADDR = 0x8105

# Game flow: ATTRACT(120) -> READY(240) -> PLAYING at frame ~383.
# init_video runs before the main loop, consuming ~23 frames of timer head start.
# Use 400 neutral frames to guarantee PLAYING state before testing directions.
WAIT_FRAMES = 400
DIR_HOLD_FRAMES = 10
NEUTRAL_GAP = 5


def build_rom() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "build.py")],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"BUILD FAILED:\n{result.stderr}")
        sys.exit(1)


def write_replay(path: Path, rom_hash: bytes, frames: list[int]) -> None:
    data = bytearray()
    data.extend(b"V8RR")
    data.extend(struct.pack("<B", 1))
    data.extend(rom_hash)
    data.extend(struct.pack("<B", 0))
    data.extend(struct.pack("<I", len(frames)))
    for frame, controller1 in enumerate(frames):
        data.extend(struct.pack("<IBB", frame, controller1, 0xFF))
    path.write_bytes(bytes(data))


def button_byte(buttons: list[str]) -> int:
    """Return active-low controller byte with given buttons pressed."""
    state = 0xFF
    for btn in buttons:
        if btn in BUTTON_MASKS:
            state &= ~BUTTON_MASKS[btn]
        elif btn == "start":
            state &= ~0x01
    return state


def peek_requested_dir(frame: int, replay_path: Path) -> int:
    """Run headless to the given frame and return PACMAN_REQUESTED_DIR value."""
    cmd = [
        str(HEADLESS),
        "--rom", str(ROM_PATH),
        "--replay", str(replay_path),
        "--frames", str(frame),
        "--peek-logical", f"0x{PACMAN_REQUESTED_DIR_ADDR:04X}:1",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"HEADLESS FAILED at frame {frame}:\n{result.stderr}")
        return -1
    for line in result.stdout.splitlines():
        match = re.match(r"^\s*0x([0-9A-Fa-f]+):\s+([0-9A-Fa-f]{2})", line)
        if match and int(match.group(1), 16) == PACMAN_REQUESTED_DIR_ADDR:
            return int(match.group(2), 16)
    return -1


def main() -> int:
    build_rom()
    rom_bytes = ROM_PATH.read_bytes()
    rom_hash = hashlib.sha256(rom_bytes).digest()

    # Build input sequence:
    # WAIT_FRAMES neutral -> then cycle through Up/Left/Down/Right with gaps.
    directions = [
        ("UP", "up"),
        ("LEFT", "left"),
        ("DOWN", "down"),
        ("RIGHT", "right"),
    ]

    controller_frames: list[int] = []
    controller_frames.extend([button_byte([])] * WAIT_FRAMES)
    for _dir_name, btn in directions:
        controller_frames.extend([button_byte([btn])] * DIR_HOLD_FRAMES)
        controller_frames.extend([button_byte([])] * NEUTRAL_GAP)

    with tempfile.TemporaryDirectory(prefix="pacmanv8-t024-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        replay_path = tmp_path / "input_test.v8r"
        write_replay(replay_path, rom_hash, controller_frames)

        evidence_dir = EVIDENCE_DIR
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Check each direction at a frame mid-hold, and NONE in the gap after.
        frame_idx = WAIT_FRAMES
        results: list[tuple[str, int, int, bool]] = []

        for dir_name, _btn in directions:
            # Check mid-hold
            check_frame = frame_idx + DIR_HOLD_FRAMES // 2
            dir_val = peek_requested_dir(check_frame, replay_path)
            expected_dir = {
                "UP": DIR_UP, "LEFT": DIR_LEFT, "DOWN": DIR_DOWN, "RIGHT": DIR_RIGHT
            }[dir_name]
            ok = dir_val == expected_dir
            results.append((f"hold {dir_name}", check_frame, dir_val, ok))

            frame_idx += DIR_HOLD_FRAMES

            # Check neutral gap
            check_frame = frame_idx + NEUTRAL_GAP // 2
            dir_val = peek_requested_dir(check_frame, replay_path)
            ok = dir_val == DIR_NONE
            results.append((f"neutral after {dir_name}", check_frame, dir_val, ok))

            frame_idx += NEUTRAL_GAP

    # Print results
    print("T024 Controller Input Test")
    print("==========================")
    print(f"ROM: {ROM_PATH}")
    print(f"WAIT_FRAMES (ATTRACT+READY): {WAIT_FRAMES}")
    print()

    all_pass = True
    for label, frame, observed, ok in results:
        status = "PASS" if ok else "FAIL"
        observed_name = DIR_NAMES.get(observed, f"UNKNOWN({observed})")
        print(f"[{status}] frame {frame:4d}  {label:25s}  observed={observed_name}")
        if not ok:
            all_pass = False
            expected_name = (
                DIR_NAMES[DIR_NONE] if "neutral" in label
                else DIR_NAMES[{"UP": DIR_UP, "LEFT": DIR_LEFT, "DOWN": DIR_DOWN, "RIGHT": DIR_RIGHT}[label.split()[1]]]
            )
            print(f"      expected {expected_name}")

    print()
    if all_pass:
        print("RESULT: All input direction tests PASSED")
        return 0
    else:
        print("RESULT: Some tests FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
