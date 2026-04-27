#!/usr/bin/env python3
"""T023 boot-time game state initialization verification.

Runs the built ROM in headless mode, peeks the game-state RAM regions,
and asserts that every field matches the level-1 arcade starting state.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
SYM_PATH = REPO_ROOT / "build" / "pacman.sym"
HEADLESS = (
    REPO_ROOT.parent
    / "Vanguard8"
    / "cmake-build-debug"
    / "src"
    / "vanguard8_headless"
)

# Arcade-correct level-1 starting positions and values.
# Ghost positions and initial modes from the Pac-Man Dossier.
EXPECTED = {
    "blinky_x_tile": 14,
    "blinky_y_tile": 14,
    "blinky_dir": 1,          # LEFT
    "blinky_mode": 1,         # SCATTER
    "blinky_id": 0,           # GHOST_ID_BLINKY
    "pinky_x_tile": 14,
    "pinky_y_tile": 17,
    "pinky_dir": 2,           # DOWN
    "pinky_mode": 1,          # SCATTER
    "pinky_id": 1,            # GHOST_ID_PINKY
    "inky_x_tile": 12,
    "inky_y_tile": 17,
    "inky_dir": 0,            # UP
    "inky_mode": 1,           # SCATTER
    "inky_id": 2,             # GHOST_ID_INKY
    "clyde_x_tile": 16,
    "clyde_y_tile": 17,
    "clyde_dir": 0,           # UP
    "clyde_mode": 1,          # SCATTER
    "clyde_id": 3,            # GHOST_ID_CLYDE
    "global_mode": 1,         # SCATTER
    "prior_mode": 1,          # SCATTER
    "schedule_kind": 0,       # LEVEL_SCHEDULE_LEVEL1
    "mode_phase": 0,          # GHOST_PHASE_S1
    "phase_remain": 420,      # 7 * 60 frames
    "fright_remain": 0,
    "reversal_pending": 0,
    "pellet_count": 240,
    "energizer_count": 4,
    "erase_pending": 0,
    "blinky_house_state": 0,  # GHOST_HOUSE_OUTSIDE
    "pinky_house_state": 2,   # PENDING_RELEASE (qualifies at 0 dots eaten)
    "inky_house_state": 1,    # GHOST_HOUSE_WAITING
    "clyde_house_state": 1,   # GHOST_HOUSE_WAITING
    "score": 0,
    "lives": 3,
    "level_current": 1,
    "level_completed": 0,
    "level_next": 1,
    "level_table_index": 0,
}

PEEK_ADDRS = [
    (0x8120, 32),   # ghost records (4 x 8 bytes)
    (0x8170, 10),   # ghost mode state
    (0x81FE, 6),    # collision counts + erase pending
    (0x8220, 16),   # ghost house state
    (0x8230, 2),    # AUDIO_FRAME_COUNTER (sanity: must be > 0 after boot)
    (0x8241, 5),    # SCORE (4 bytes) + LIVES (1 byte)
    (0x8260, 9),    # level state
]


def build_rom() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "build.py")],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"BUILD FAILED:\n{result.stderr}")
        sys.exit(1)


def read_memory() -> dict[int, int]:
    """Return {logical_address: byte_value} from headless peek."""
    cmd = [
        str(HEADLESS),
        "--rom", str(ROM_PATH),
        "--frames", "60",
    ]
    for addr, length in PEEK_ADDRS:
        cmd.extend(["--peek-logical", f"0x{addr:04X}:{length}"])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"HEADLESS FAILED:\n{result.stderr}")
        sys.exit(1)

    memory: dict[int, int] = {}
    for line in result.stdout.splitlines():
        match = re.match(r"^\s*0x([0-9A-Fa-f]+):\s+((?:[0-9A-Fa-f]{2}\s?)+)", line)
        if match:
            base = int(match.group(1), 16)
            hex_bytes = match.group(2).split()
            for offset, hex_byte in enumerate(hex_bytes):
                memory[base + offset] = int(hex_byte, 16)
    return memory


def assert_eq(mem: dict[int, int], addr: int, expected: int, label: str) -> list[str]:
    actual = mem.get(addr)
    if actual == expected:
        return []
    return [f"FAIL {label}: 0x{addr:04X} expected {expected} (0x{expected:02X}), got {actual}"]


def run_assertions(mem: dict[int, int]) -> list[str]:
    errors: list[str] = []

    # Ghost records
    errors += assert_eq(mem, 0x8120, EXPECTED["blinky_x_tile"], "blinky_x_tile")
    errors += assert_eq(mem, 0x8121, EXPECTED["blinky_y_tile"], "blinky_y_tile")
    errors += assert_eq(mem, 0x8122, EXPECTED["blinky_dir"], "blinky_dir")
    errors += assert_eq(mem, 0x8123, EXPECTED["blinky_mode"], "blinky_mode")
    errors += assert_eq(mem, 0x8124, EXPECTED["blinky_id"], "blinky_id")

    errors += assert_eq(mem, 0x8128, EXPECTED["pinky_x_tile"], "pinky_x_tile")
    errors += assert_eq(mem, 0x8129, EXPECTED["pinky_y_tile"], "pinky_y_tile")
    errors += assert_eq(mem, 0x812A, EXPECTED["pinky_dir"], "pinky_dir")
    errors += assert_eq(mem, 0x812B, EXPECTED["pinky_mode"], "pinky_mode")
    errors += assert_eq(mem, 0x812C, EXPECTED["pinky_id"], "pinky_id")

    errors += assert_eq(mem, 0x8130, EXPECTED["inky_x_tile"], "inky_x_tile")
    errors += assert_eq(mem, 0x8131, EXPECTED["inky_y_tile"], "inky_y_tile")
    errors += assert_eq(mem, 0x8132, EXPECTED["inky_dir"], "inky_dir")
    errors += assert_eq(mem, 0x8133, EXPECTED["inky_mode"], "inky_mode")
    errors += assert_eq(mem, 0x8134, EXPECTED["inky_id"], "inky_id")

    errors += assert_eq(mem, 0x8138, EXPECTED["clyde_x_tile"], "clyde_x_tile")
    errors += assert_eq(mem, 0x8139, EXPECTED["clyde_y_tile"], "clyde_y_tile")
    errors += assert_eq(mem, 0x813A, EXPECTED["clyde_dir"], "clyde_dir")
    errors += assert_eq(mem, 0x813B, EXPECTED["clyde_mode"], "clyde_mode")
    errors += assert_eq(mem, 0x813C, EXPECTED["clyde_id"], "clyde_id")

    # Ghost mode state
    errors += assert_eq(mem, 0x8170, EXPECTED["global_mode"], "global_mode")
    errors += assert_eq(mem, 0x8171, EXPECTED["prior_mode"], "prior_mode")
    errors += assert_eq(mem, 0x8172, EXPECTED["schedule_kind"], "schedule_kind")
    errors += assert_eq(mem, 0x8173, EXPECTED["mode_phase"], "mode_phase")
    # phase_remain is little-endian 16-bit at 0x8174
    phase_lo = mem.get(0x8174, 0)
    phase_hi = mem.get(0x8175, 0)
    phase_remain = phase_lo | (phase_hi << 8)
    if phase_remain != EXPECTED["phase_remain"]:
        errors.append(
            f"FAIL phase_remain: expected {EXPECTED['phase_remain']} (0x{EXPECTED['phase_remain']:04X}), "
            f"got {phase_remain} (0x{phase_remain:04X})"
        )
    # fright_remain at 0x8176
    fr_lo = mem.get(0x8176, 0)
    fr_hi = mem.get(0x8177, 0)
    fright_remain = fr_lo | (fr_hi << 8)
    if fright_remain != EXPECTED["fright_remain"]:
        errors.append(f"FAIL fright_remain: expected 0, got {fright_remain}")
    errors += assert_eq(mem, 0x8178, EXPECTED["reversal_pending"], "reversal_pending")

    # Collision counts
    pellet_lo = mem.get(0x81FE, 0)
    pellet_hi = mem.get(0x81FF, 0)
    pellet_count = pellet_lo | (pellet_hi << 8)
    if pellet_count != EXPECTED["pellet_count"]:
        errors.append(
            f"FAIL pellet_count: expected {EXPECTED['pellet_count']}, got {pellet_count}"
        )
    ener_lo = mem.get(0x8200, 0)
    ener_hi = mem.get(0x8201, 0)
    energizer_count = ener_lo | (ener_hi << 8)
    if energizer_count != EXPECTED["energizer_count"]:
        errors.append(
            f"FAIL energizer_count: expected {EXPECTED['energizer_count']}, got {energizer_count}"
        )
    errors += assert_eq(mem, 0x8202, EXPECTED["erase_pending"], "erase_pending")

    # Ghost house
    errors += assert_eq(mem, 0x8220, EXPECTED["blinky_house_state"], "blinky_house_state")
    errors += assert_eq(mem, 0x8221, EXPECTED["pinky_house_state"], "pinky_house_state")
    errors += assert_eq(mem, 0x8222, EXPECTED["inky_house_state"], "inky_house_state")
    errors += assert_eq(mem, 0x8223, EXPECTED["clyde_house_state"], "clyde_house_state")

    # Audio frame counter at 0x8230 must be advancing.
    # This also proves GAME_STATE no longer overlaps AUDIO_STATE.
    audio_ctr_lo = mem.get(0x8230, 0)
    audio_ctr_hi = mem.get(0x8231, 0)
    audio_frame_counter = audio_ctr_lo | (audio_ctr_hi << 8)
    if audio_frame_counter == 0:
        errors.append(
            "FAIL audio_frame_counter: still zero after 60 frames — "
            "regions may still overlap"
        )
    else:
        print(f"  PASS audio_frame_counter = {audio_frame_counter} (advancing, regions independent)")

    # SCORE (4 bytes little-endian) at 0x8241
    s0 = mem.get(0x8241, 0)
    s1 = mem.get(0x8242, 0)
    s2 = mem.get(0x8243, 0)
    s3 = mem.get(0x8244, 0)
    score = s0 | (s1 << 8) | (s2 << 16) | (s3 << 24)
    if score != EXPECTED["score"]:
        errors.append(f"FAIL score: expected {EXPECTED['score']}, got {score}")

    # LIVES at 0x8245
    errors += assert_eq(mem, 0x8245, EXPECTED["lives"], "lives")

    # Level state
    lvl_lo = mem.get(0x8260, 0)
    lvl_hi = mem.get(0x8261, 0)
    level_current = lvl_lo | (lvl_hi << 8)
    if level_current != EXPECTED["level_current"]:
        errors.append(f"FAIL level_current: expected {EXPECTED['level_current']}, got {level_current}")

    completed_lo = mem.get(0x8262, 0)
    completed_hi = mem.get(0x8263, 0)
    level_completed = completed_lo | (completed_hi << 8)
    if level_completed != EXPECTED["level_completed"]:
        errors.append(f"FAIL level_completed: expected {EXPECTED['level_completed']}, got {level_completed}")

    next_lo = mem.get(0x8264, 0)
    next_hi = mem.get(0x8265, 0)
    level_next = next_lo | (next_hi << 8)
    if level_next != EXPECTED["level_next"]:
        errors.append(f"FAIL level_next: expected {EXPECTED['level_next']}, got {level_next}")

    errors += assert_eq(mem, 0x8266, EXPECTED["level_table_index"], "level_table_index")

    return errors


def main() -> int:
    build_rom()

    mem = read_memory()
    errors = run_assertions(mem)

    print("T023 Boot-Time Game State Initialization Test")
    print("==============================================")
    print(f"ROM: {ROM_PATH}")
    print(f"Peek regions: {len(PEEK_ADDRS)}")
    print()

    if errors:
        for err in errors:
            print(err)
        print()
        print(f"RESULT: {len(errors)} assertion(s) FAILED")
        return 1
    else:
        for key, value in EXPECTED.items():
            print(f"  PASS {key} = {value}")
        print()
        print("RESULT: all assertions passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
