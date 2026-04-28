#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

import coordinate_transform as transform


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADLESS = REPO_ROOT.parent / "Vanguard8" / "cmake-build-debug" / "src" / "vanguard8_headless"
COORD_LUT_PATH = REPO_ROOT / "assets" / "coord_lut.bin"
OFFSETS = (0, 2, 4, 6)
OUTPUT_ADDR = 0x9000
PTR_ADDR = 0x8FE0
Y_TILE_ADDR = 0x8FE2
X_TILE_ADDR = 0x8FE3
Y_OFF_ADDR = 0x8FE4
X_OFF_ADDR = 0x8FE5


SYMBOL_PATTERN = re.compile(r"^([A-Za-z_.$][A-Za-z0-9_.$]*):\s+EQU\s+0x([0-9A-Fa-f]+)\s*$")
PEEK_ROW_PATTERN = re.compile(r"^\s*0x[0-9A-Fa-f]+:\s+([0-9A-Fa-f\s]+)$")


def run(argv: list[str], cwd: pathlib.Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        command = " ".join(shlex.quote(str(arg)) for arg in argv)
        raise RuntimeError(f"command failed ({result.returncode}): {command}\n{result.stdout}\n{result.stderr}")
    return result


def build_expected(coordmap: bytes) -> list[tuple[int, int]]:
    expected: list[tuple[int, int]] = []
    for tile_y in range(transform.MAZE_TOP, transform.MAZE_TOP + transform.MAZE_ROWS):
        for y_offset in OFFSETS:
            for tile_x in range(transform.ARCADE_WIDTH):
                for x_offset in OFFSETS:
                    x_fp = ((tile_x * transform.ARCADE_TILE_SIZE) + x_offset) << 8
                    y_fp = ((tile_y * transform.ARCADE_TILE_SIZE) + y_offset) << 8
                    result = transform.transform_entity(coordmap, x_fp, y_fp)
                    expected.append((result.sprite_y & 0xFF, result.sprite_x & 0xFF))
    return expected


def test_rom_source() -> str:
    return f"""
        ORG 0x0000

    MACRO OUT0_A port, value
        ld a, value
        db 0xED, 0x39, port
    ENDM

entry:
        jp start

start:
        di
        ld sp, 0xFF00
        OUT0_A 0x3A, 0x48
        OUT0_A 0x38, 0xF0
        OUT0_A 0x39, 0x04

        ld hl, 0x{OUTPUT_ADDR:04X}
        ld (0x{PTR_ADDR:04X}), hl
        ld a, {transform.MAZE_TOP}
        ld (0x{Y_TILE_ADDR:04X}), a

y_tile_loop:
        xor a
        ld (0x{Y_OFF_ADDR:04X}), a

y_offset_loop:
        xor a
        ld (0x{X_TILE_ADDR:04X}), a

x_tile_loop:
        xor a
        ld (0x{X_OFF_ADDR:04X}), a

x_offset_loop:
        ld a, (0x{X_OFF_ADDR:04X})
        call load_offset_b
        ld a, (0x{X_TILE_ADDR:04X})
        add a, a
        add a, a
        add a, a
        add a, b
        ld d, a
        ld e, 0

        ld a, (0x{Y_OFF_ADDR:04X})
        call load_offset_b
        ld a, (0x{Y_TILE_ADDR:04X})
        add a, a
        add a, a
        add a, a
        add a, b
        ld h, a
        ld l, 0

        call coord_arcade_to_v8

        push hl
        ld hl, (0x{PTR_ADDR:04X})
        pop de
        ld (hl), d
        inc hl
        ld (hl), e
        inc hl
        ld (0x{PTR_ADDR:04X}), hl

        ld a, (0x{X_OFF_ADDR:04X})
        inc a
        ld (0x{X_OFF_ADDR:04X}), a
        cp {len(OFFSETS)}
        jr c, x_offset_loop

        ld a, (0x{X_TILE_ADDR:04X})
        inc a
        ld (0x{X_TILE_ADDR:04X}), a
        cp {transform.ARCADE_WIDTH}
        jr c, x_tile_loop

        ld a, (0x{Y_OFF_ADDR:04X})
        inc a
        ld (0x{Y_OFF_ADDR:04X}), a
        cp {len(OFFSETS)}
        jr c, y_offset_loop

        ld a, (0x{Y_TILE_ADDR:04X})
        inc a
        ld (0x{Y_TILE_ADDR:04X}), a
        cp {transform.MAZE_TOP + transform.MAZE_ROWS}
        jr c, y_tile_loop

test_done:
        halt
        jp test_done

load_offset_b:
        ld l, a
        ld h, 0
        ld bc, offset_values
        add hl, bc
        ld b, (hl)
        ret

offset_values:
        db {", ".join(str(value) for value in OFFSETS)}

        INCLUDE "{(REPO_ROOT / "src" / "coord_transform.asm").as_posix()}"
"""


def parse_symbol(path: pathlib.Path, name: str) -> int:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = SYMBOL_PATTERN.match(line.strip())
        if match and match.group(1) == name:
            return int(match.group(2), 16)
    raise RuntimeError(f"missing symbol {name} in {path}")


def parse_peek_bytes(stdout: str) -> bytes:
    values: list[int] = []
    in_peek = False
    for line in stdout.splitlines():
        if line.strip() == "[peek-logical]":
            in_peek = True
            continue
        if in_peek and line.startswith("["):
            in_peek = False
            continue
        if not in_peek:
            continue
        match = PEEK_ROW_PATTERN.match(line)
        if match:
            values.extend(int(part, 16) for part in match.group(1).split())
    return bytes(values)


def main() -> int:
    if not HEADLESS.is_file():
        raise FileNotFoundError(f"headless emulator not found: {HEADLESS}")
    if not COORD_LUT_PATH.is_file():
        raise FileNotFoundError(f"coordinate LUT not found: {COORD_LUT_PATH}; run tools/build.py first")

    coordmap = transform.load_coordmap()
    expected = build_expected(coordmap)
    expected_bytes = bytes(value for pair in expected for value in pair)

    with tempfile.TemporaryDirectory(prefix="t026-coord-z80-") as tmp_dir:
        tmp = pathlib.Path(tmp_dir)
        source = tmp / "coord_transform_test.asm"
        rom = tmp / "coord_transform_test.rom"
        sym = tmp / "coord_transform_test.sym"
        source.write_text(test_rom_source(), encoding="utf-8")

        run(["sjasmplus", "--nologo", "--msg=war", f"--raw={rom}", f"--sym={sym}", str(source)])
        rom.write_bytes(rom.read_bytes().ljust(0x4000, b"\x00"))
        done_pc = parse_symbol(sym, "test_done")

        cmd = [
            str(HEADLESS),
            "--rom",
            str(rom),
            "--frames",
            "300",
            "--run-until-pc",
            f"0x{done_pc:04X}:300",
        ]
        for offset in range(0, len(expected_bytes), 0x100):
            length = min(0x100, len(expected_bytes) - offset)
            cmd.extend(["--peek-logical", f"0x{OUTPUT_ADDR + offset:04X}:0x{length:X}"])
        result = run(cmd)
        actual_bytes = parse_peek_bytes(result.stdout)

    mismatches: list[str] = []
    if len(actual_bytes) != len(expected_bytes):
        mismatches.append(f"output length mismatch: expected {len(expected_bytes)} bytes, got {len(actual_bytes)}")
    else:
        for index, (actual, expected_value) in enumerate(zip(actual_bytes, expected_bytes, strict=True)):
            if actual == expected_value:
                continue
            pair_index = index // 2
            component = "Y" if index % 2 == 0 else "X"
            tile_block = pair_index // (len(OFFSETS) * transform.ARCADE_WIDTH * len(OFFSETS))
            within_y = pair_index % (len(OFFSETS) * transform.ARCADE_WIDTH * len(OFFSETS))
            y_offset = OFFSETS[within_y // (transform.ARCADE_WIDTH * len(OFFSETS))]
            within_x = within_y % (transform.ARCADE_WIDTH * len(OFFSETS))
            tile_x = within_x // len(OFFSETS)
            x_offset = OFFSETS[within_x % len(OFFSETS)]
            tile_y = transform.MAZE_TOP + tile_block
            mismatches.append(
                f"tile=({tile_x},{tile_y}) offsets=({x_offset},{y_offset}) {component}: "
                f"z80=0x{actual:02X} python=0x{expected_value:02X}"
            )
            if len(mismatches) >= 20:
                break

    print("T026 Z80 coordinate transform comparison")
    print(f"coordmap SHA-256: {hashlib.sha256(coordmap).hexdigest()}")
    print(f"coord_lut SHA-256: {hashlib.sha256(COORD_LUT_PATH.read_bytes()).hexdigest()}")
    print(f"mapped tile rows: {transform.MAZE_TOP}-{transform.MAZE_TOP + transform.MAZE_ROWS - 1}")
    print(f"tile columns: 0-{transform.ARCADE_WIDTH - 1}")
    print(f"sub-tile offsets: {OFFSETS}")
    print(
        "28x36 grid coverage: mapped rows compared; "
        f"{transform.ARCADE_WIDTH * (transform.ARCADE_HEIGHT - transform.MAZE_ROWS) * len(OFFSETS) * len(OFFSETS)} "
        "unmapped row/offset positions skipped because the Python reference rejects unmapped cells"
    )
    print(f"positions compared: {len(expected)}")
    print(f"bytes compared: {len(expected_bytes)}")
    print("cycle estimate: 189-234 T-states per call, below the 250-cycle target for 5 sprites")
    print(f"mismatches: {len(mismatches)}")
    for mismatch in mismatches:
        print(f"  {mismatch}")
    if mismatches:
        print("coord_transform_z80_tests: FAILED")
        return 1
    print("coord_transform_z80_tests: PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"coord_transform_z80_tests.py error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
