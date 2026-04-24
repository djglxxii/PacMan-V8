#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
from collections.abc import Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "tests" / "replays" / "pattern_sources"
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
SEMANTIC_PATH = REPO_ROOT / "assets" / "maze_semantic.bin"
MAIN_ASM_PATH = REPO_ROOT / "src" / "main.asm"
PATTERN_ASM_PATH = REPO_ROOT / "src" / "pattern_replay.asm"
MOVEMENT_ASM_PATH = REPO_ROOT / "src" / "movement.asm"
COLLISION_ASM_PATH = REPO_ROOT / "src" / "collision.asm"
GHOST_ASM_PATH = REPO_ROOT / "src" / "ghost_ai.asm"
LEVEL_ASM_PATH = REPO_ROOT / "src" / "level_progression.asm"
HEADLESS = pathlib.Path("/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless")

WIDTH_TILES = 28
HEIGHT_TILES = 36
TILE_SIZE = 8
TILE_CENTER = 4
PASSABLE_CLASSES = {1, 2, 3, 6}
PELLET = 2
ENERGIZER = 3

DIR_UP = 0
DIR_LEFT = 1
DIR_DOWN = 2
DIR_RIGHT = 3
DIR_NONE = 4
DIR_NAMES = {
    DIR_UP: "UP",
    DIR_LEFT: "LEFT",
    DIR_DOWN: "DOWN",
    DIR_RIGHT: "RIGHT",
    DIR_NONE: "NONE",
}
DIR_DELTAS = {
    DIR_UP: (0, -1),
    DIR_LEFT: (-1, 0),
    DIR_DOWN: (0, 1),
    DIR_RIGHT: (1, 0),
}
OPPOSITE = {
    DIR_UP: DIR_DOWN,
    DIR_LEFT: DIR_RIGHT,
    DIR_DOWN: DIR_UP,
    DIR_RIGHT: DIR_LEFT,
}

BUTTON_BITS = {
    "start": 0,
    "select": 1,
    "b": 2,
    "a": 3,
    "right": 4,
    "left": 5,
    "down": 6,
    "up": 7,
}
BUTTON_TO_DIR = {
    "up": DIR_UP,
    "left": DIR_LEFT,
    "down": DIR_DOWN,
    "right": DIR_RIGHT,
}

EQU_PATTERN = re.compile(r"^([A-Z0-9_]+)\s+EQU\s+(.+?)\s*(?:;.*)?$")
PEEK_HEADER_PATTERN = re.compile(r"^logical 0x([0-9a-f]{4}) .* length ([0-9]+)$")
BYTE_ROW_PATTERN = re.compile(r"^\s+0x([0-9a-f]{4}):((?: [0-9a-f]{2})+)$")
FRAME_HASH_PATTERN = re.compile(r"Frame ([0-9]+) SHA-256: ([0-9a-f]{64})")


class PatternReplayError(AssertionError):
    pass


@dataclasses.dataclass(frozen=True)
class Segment:
    frames: int
    buttons: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CheckpointSpec:
    name: str
    frame: int


@dataclasses.dataclass(frozen=True)
class PatternCase:
    case_id: str
    title: str
    public_sources: tuple[dict[str, str], ...]
    intent: str
    segments: tuple[Segment, ...]
    checkpoints: tuple[CheckpointSpec, ...]
    source_path: pathlib.Path


@dataclasses.dataclass
class RuntimeSnapshot:
    active: int
    input_byte: int
    replay_frame: int
    score: int
    dots: int
    pac_tile: tuple[int, int]
    last_consume: int
    last_collision: int
    last_dir: int
    pac_px: tuple[int, int]
    ghosts: dict[str, tuple[int, int]]
    ghost_mode: int
    mode_phase: int
    phase_remain: int
    frightened_remain: int
    current_level: int


@dataclasses.dataclass
class CaseResult:
    case_id: str
    passed: bool
    replay_path: pathlib.Path
    replay_sha: str
    frame_hashes: dict[int, str]
    details: list[str]
    failures: list[str]


def rel(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_equ_constants(*paths: pathlib.Path) -> dict[str, int]:
    raw: dict[str, str] = {}
    for path in paths:
        for line in path.read_text(encoding="ascii").splitlines():
            match = EQU_PATTERN.match(line.strip())
            if match is not None:
                raw[match.group(1)] = match.group(2).strip()

    constants: dict[str, int] = {}
    pending = dict(raw)
    while pending:
        made_progress = False
        for name, expression in list(pending.items()):
            substituted = expression
            for key, value in sorted(constants.items(), key=lambda item: len(item[0]), reverse=True):
                substituted = re.sub(rf"\b{re.escape(key)}\b", str(value), substituted)
            if re.search(r"\b[A-Z][A-Z0-9_]*\b", substituted):
                continue
            try:
                constants[name] = int(eval(substituted, {"__builtins__": {}}, {}))
            except Exception:
                continue
            del pending[name]
            made_progress = True
        if not made_progress:
            unresolved = ", ".join(sorted(pending))
            raise PatternReplayError(f"could not resolve EQU constants: {unresolved}")
    return constants


CONSTANTS = parse_equ_constants(
    PATTERN_ASM_PATH,
    MOVEMENT_ASM_PATH,
    COLLISION_ASM_PATH,
    GHOST_ASM_PATH,
    LEVEL_ASM_PATH,
)


def load_cases() -> list[PatternCase]:
    cases: list[PatternCase] = []
    for path in sorted(SOURCE_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="ascii"))
        cases.append(
            PatternCase(
                case_id=payload["id"],
                title=payload["title"],
                public_sources=tuple(payload["public_sources"]),
                intent=payload["intent"],
                segments=tuple(
                    Segment(frames=int(segment["frames"]), buttons=tuple(segment["buttons"]))
                    for segment in payload["segments"]
                ),
                checkpoints=tuple(
                    CheckpointSpec(name=item["name"], frame=int(item["frame"]))
                    for item in payload["checkpoints"]
                ),
                source_path=path,
            )
        )
    if not cases:
        raise PatternReplayError(f"no pattern sources found under {rel(SOURCE_DIR)}")
    return cases


def expand_inputs(case: PatternCase) -> list[int]:
    frames: list[int] = []
    for segment in case.segments:
        if segment.frames <= 0:
            raise PatternReplayError(f"{case.case_id}: segment frame counts must be positive")
        state = 0xFF
        for button in segment.buttons:
            if button not in BUTTON_BITS:
                raise PatternReplayError(f"{case.case_id}: unknown button {button!r}")
            state &= ~(1 << BUTTON_BITS[button])
        frames.extend([state] * segment.frames)
    max_checkpoint = max(checkpoint.frame for checkpoint in case.checkpoints)
    if len(frames) < max_checkpoint:
        frames.extend([0xFF] * (max_checkpoint - len(frames)))
    return frames


def write_replay(path: pathlib.Path, rom_bytes: bytes, controller1_frames: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = bytearray()
    data.extend(b"V8RR")
    data.extend(struct.pack("<B", 1))
    data.extend(hashlib.sha256(rom_bytes).digest())
    data.extend(struct.pack("<B", 0))
    data.extend(struct.pack("<I", len(controller1_frames)))
    for frame, controller1 in enumerate(controller1_frames):
        data.extend(struct.pack("<IBB", frame, controller1, 0xFF))
    path.write_bytes(bytes(data))


class ReplayModel:
    def __init__(self, semantic: bytes) -> None:
        if len(semantic) != WIDTH_TILES * HEIGHT_TILES:
            raise PatternReplayError("semantic maze asset has unexpected size")
        self.semantic = semantic
        self.active = False
        self.last_input = 0xFF
        self.replay_frame = 0
        self.score = 0
        self.dots = 0
        self.x_px = 14 * TILE_SIZE + TILE_CENTER
        self.y_px = 26 * TILE_SIZE + TILE_CENTER
        self.current_dir = DIR_LEFT
        self.requested_dir = DIR_LEFT
        self.dot_stall = 0
        self.last_consume = 0
        self.last_collision = 0
        self.last_dir = DIR_NONE
        self.pellets: set[tuple[int, int]] = set()
        self.energizers: set[tuple[int, int]] = set()
        self.ghosts = {
            "blinky": (14, 14),
            "pinky": (14, 17),
            "inky": (12, 17),
            "clyde": (16, 17),
        }
        self.ghost_mode = 1
        self.mode_phase = 0
        self.phase_remain = 420
        self.frightened_remain = 0
        self.current_level = 1

    def start(self) -> None:
        self.__init__(self.semantic)
        self.active = True
        for y in range(HEIGHT_TILES):
            for x in range(WIDTH_TILES):
                semantic = self.semantic[y * WIDTH_TILES + x]
                if semantic == PELLET:
                    self.pellets.add((x, y))
                elif semantic == ENERGIZER:
                    self.energizers.add((x, y))

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            active=1 if self.active else 0,
            input_byte=self.last_input,
            replay_frame=self.replay_frame,
            score=self.score,
            dots=self.dots,
            pac_tile=(self.x_px // TILE_SIZE, self.y_px // TILE_SIZE),
            last_consume=self.last_consume,
            last_collision=self.last_collision,
            last_dir=self.last_dir,
            pac_px=(self.x_px, self.y_px),
            ghosts=dict(self.ghosts),
            ghost_mode=self.ghost_mode,
            mode_phase=self.mode_phase,
            phase_remain=self.phase_remain,
            frightened_remain=self.frightened_remain,
            current_level=self.current_level,
        )

    def tick(self, input_byte: int) -> None:
        self.last_input = input_byte
        if not self.active:
            if (input_byte & (1 << BUTTON_BITS["start"])) == 0:
                self.start()
            return

        self.replay_frame = (self.replay_frame + 1) & 0xFFFF
        direction = self.input_to_dir(input_byte)
        self.last_dir = direction
        if direction != DIR_NONE:
            self.request_direction(direction)

        if self.dot_stall:
            self.dot_stall -= 1
        else:
            self.update_movement()
            self.consume_at_pacman()
        self.tick_ghost_mode()

    def input_to_dir(self, input_byte: int) -> int:
        for button in ("up", "left", "down", "right"):
            if (input_byte & (1 << BUTTON_BITS[button])) == 0:
                return BUTTON_TO_DIR[button]
        return DIR_NONE

    def request_direction(self, direction: int) -> None:
        if direction == DIR_NONE:
            self.requested_dir = DIR_NONE
            return
        if self.current_dir == DIR_NONE or OPPOSITE.get(self.current_dir) == direction:
            self.requested_dir = direction
            return
        if self.distance_to_next_center_px() < 5:
            self.requested_dir = direction

    def update_movement(self) -> None:
        if self.requested_dir != DIR_NONE and self.is_center() and self.direction_passable(self.requested_dir):
            self.current_dir = self.requested_dir
        if not self.direction_passable(self.current_dir):
            self.current_dir = DIR_NONE
            return
        if self.current_dir == DIR_LEFT:
            self.x_px = (self.x_px - 1) & 0xFF
        elif self.current_dir == DIR_RIGHT:
            self.x_px = (self.x_px + 1) & 0xFF
        elif self.current_dir == DIR_UP:
            self.y_px = (self.y_px - 1) & 0xFF
        elif self.current_dir == DIR_DOWN:
            self.y_px = (self.y_px + 1) & 0xFF
        if self.x_px >= 240:
            self.x_px = (self.x_px + WIDTH_TILES * TILE_SIZE) & 0xFF
        elif self.x_px >= WIDTH_TILES * TILE_SIZE:
            self.x_px -= WIDTH_TILES * TILE_SIZE

    def is_center(self) -> bool:
        return (self.x_px & 0x07) == TILE_CENTER and (self.y_px & 0x07) == TILE_CENTER

    def tile(self) -> tuple[int, int]:
        return self.x_px // TILE_SIZE, self.y_px // TILE_SIZE

    def direction_passable(self, direction: int) -> bool:
        if direction not in DIR_DELTAS:
            return False
        x, y = self.tile()
        dx, dy = DIR_DELTAS[direction]
        return self.cell_passable((x + dx) % WIDTH_TILES, y + dy)

    def cell_passable(self, x: int, y: int) -> bool:
        if y < 0 or y >= HEIGHT_TILES:
            return False
        if x < 0 or x >= WIDTH_TILES:
            return False
        return self.semantic[y * WIDTH_TILES + x] in PASSABLE_CLASSES

    def distance_to_next_center_px(self) -> int:
        if self.current_dir in {DIR_RIGHT, DIR_DOWN}:
            axis = self.x_px if self.current_dir == DIR_RIGHT else self.y_px
            low = axis & 0x07
            if low < TILE_CENTER + 1:
                return TILE_CENTER - low
            return 12 - low
        if self.current_dir in {DIR_LEFT, DIR_UP}:
            axis = self.x_px if self.current_dir == DIR_LEFT else self.y_px
            low = axis & 0x07
            if low >= TILE_CENTER:
                return low - TILE_CENTER
            return low + TILE_CENTER
        return 0

    def consume_at_pacman(self) -> None:
        self.last_consume = 0
        if not self.is_center():
            return
        tile = self.tile()
        if tile in self.pellets:
            self.pellets.remove(tile)
            self.score += 10
            self.dots += 1
            self.dot_stall = 1
            self.last_consume = 1
        elif tile in self.energizers:
            self.energizers.remove(tile)
            self.score += 50
            self.dots += 1
            self.dot_stall = 3
            self.last_consume = 2
            self.ghost_mode = 2
            self.frightened_remain = 360

    def tick_ghost_mode(self) -> None:
        if self.ghost_mode == 2:
            if self.frightened_remain:
                self.frightened_remain -= 1
                if self.frightened_remain == 0:
                    self.ghost_mode = 1 if self.mode_phase % 2 == 0 else 0
            return
        if self.mode_phase >= 7:
            return
        if self.phase_remain:
            self.phase_remain -= 1
            if self.phase_remain:
                return
        self.mode_phase += 1
        self.ghost_mode = 1 if self.mode_phase % 2 == 0 and self.mode_phase < 7 else 0
        durations = [420, 1200, 420, 1200, 300, 1200, 300, 0]
        self.phase_remain = durations[self.mode_phase]


def expected_at_frame(inputs: list[int], semantic: bytes, frame: int, activation_frame: int) -> RuntimeSnapshot:
    if activation_frame > frame:
        raise PatternReplayError(f"activation frame {activation_frame} is after checkpoint frame {frame}")
    model = ReplayModel(semantic)
    model.start()
    for completed_frame in range(activation_frame + 1, frame + 1):
        input_index = completed_frame - 1
        input_byte = inputs[input_index] if input_index < len(inputs) else 0xFF
        model.tick(input_byte)
    return model.snapshot()


def parse_peek_bytes(report: str, address: int, length: int) -> bytes:
    in_target = False
    collected: list[int] = []
    for line in report.splitlines():
        header = PEEK_HEADER_PATTERN.match(line)
        if header is not None:
            in_target = int(header.group(1), 16) == address
            continue
        if not in_target:
            continue
        row = BYTE_ROW_PATTERN.match(line)
        if row is not None:
            collected.extend(int(token, 16) for token in row.group(2).split())
            if len(collected) >= length:
                return bytes(collected[:length])
    raise PatternReplayError(f"inspection report did not contain logical 0x{address:04x}:{length}")


def u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def observed_from_report(report: str) -> RuntimeSnapshot:
    base = CONSTANTS["PATTERN_REPLAY_STATE_BASE"]
    pattern = parse_peek_bytes(report, base, 13)
    movement = parse_peek_bytes(report, CONSTANTS["PACMAN_X_FP"], 6)
    ghosts_raw = parse_peek_bytes(report, CONSTANTS["GHOST_STATE_BASE"], 32)
    mode_raw = parse_peek_bytes(report, CONSTANTS["GHOST_MODE_STATE_BASE"], 10)
    level_raw = parse_peek_bytes(report, CONSTANTS["LEVEL_STATE_BASE"], 9)

    ghosts = {
        "blinky": (ghosts_raw[0], ghosts_raw[1]),
        "pinky": (ghosts_raw[8], ghosts_raw[9]),
        "inky": (ghosts_raw[16], ghosts_raw[17]),
        "clyde": (ghosts_raw[24], ghosts_raw[25]),
    }
    return RuntimeSnapshot(
        active=pattern[0],
        input_byte=pattern[1],
        replay_frame=u16le(pattern, 2),
        score=u16le(pattern, 4),
        dots=u16le(pattern, 6),
        pac_tile=(pattern[8], pattern[9]),
        last_consume=pattern[10],
        last_collision=pattern[11],
        last_dir=pattern[12],
        pac_px=(u16le(movement, 0) >> 8, u16le(movement, 2) >> 8),
        ghosts=ghosts,
        ghost_mode=mode_raw[0],
        mode_phase=mode_raw[3],
        phase_remain=u16le(mode_raw, 4),
        frightened_remain=u16le(mode_raw, 6),
        current_level=u16le(level_raw, 0),
    )


def compare_snapshots(label: str, observed: RuntimeSnapshot, expected: RuntimeSnapshot) -> list[str]:
    failures: list[str] = []
    fields = [
        ("active", observed.active, expected.active),
        ("replay_frame", observed.replay_frame, expected.replay_frame),
        ("score", observed.score, expected.score),
        ("dots", observed.dots, expected.dots),
        ("pac_tile", observed.pac_tile, expected.pac_tile),
        ("pac_px", observed.pac_px, expected.pac_px),
        ("last_consume", observed.last_consume, expected.last_consume),
        ("last_dir", observed.last_dir, expected.last_dir),
        ("ghost_mode", observed.ghost_mode, expected.ghost_mode),
        ("mode_phase", observed.mode_phase, expected.mode_phase),
        ("phase_remain", observed.phase_remain, expected.phase_remain),
        ("frightened_remain", observed.frightened_remain, expected.frightened_remain),
        ("current_level", observed.current_level, expected.current_level),
    ]
    for name, actual, wanted in fields:
        if actual != wanted:
            failures.append(f"{label}: {name} expected {wanted!r}, observed {actual!r}")
    for ghost, wanted_pos in expected.ghosts.items():
        actual_pos = observed.ghosts[ghost]
        if actual_pos != wanted_pos:
            failures.append(f"{label}: {ghost} expected {wanted_pos}, observed {actual_pos}")
    return failures


def format_snapshot(snapshot: RuntimeSnapshot) -> str:
    ghost_text = " ".join(f"{name}=({x},{y})" for name, (x, y) in snapshot.ghosts.items())
    return (
        f"active={snapshot.active} replay_frame={snapshot.replay_frame} "
        f"pac_tile={snapshot.pac_tile} pac_px={snapshot.pac_px} "
        f"dir={DIR_NAMES.get(snapshot.last_dir, snapshot.last_dir)} "
        f"score={snapshot.score} dots={snapshot.dots} consume={snapshot.last_consume} "
        f"mode={snapshot.ghost_mode} phase={snapshot.mode_phase} phase_remain={snapshot.phase_remain} "
        f"level={snapshot.current_level} {ghost_text}"
    )


def run_headless(
    replay_path: pathlib.Path,
    frame: int,
    inspect_path: pathlib.Path,
    dump_frame_path: pathlib.Path | None,
) -> tuple[str, str]:
    argv = [
        str(HEADLESS),
        "--rom",
        str(ROM_PATH),
        "--replay",
        str(replay_path),
        "--frames",
        str(frame),
        "--inspect-frame",
        str(frame),
        "--inspect",
        str(inspect_path),
        "--peek-logical",
        f"{CONSTANTS['PATTERN_REPLAY_STATE_BASE']:04X}:13",
        "--peek-logical",
        f"{CONSTANTS['PACMAN_X_FP']:04X}:6",
        "--peek-logical",
        f"{CONSTANTS['GHOST_STATE_BASE']:04X}:32",
        "--peek-logical",
        f"{CONSTANTS['GHOST_MODE_STATE_BASE']:04X}:10",
        "--peek-logical",
        f"{CONSTANTS['LEVEL_STATE_BASE']:04X}:9",
        "--hash-frame",
        str(frame),
    ]
    if dump_frame_path is not None:
        argv.extend(["--dump-frame", str(dump_frame_path)])
    completed = subprocess.run(argv, cwd=REPO_ROOT, check=True, text=True, capture_output=True)
    return completed.stdout, inspect_path.read_text(encoding="ascii")


def measured_arcade_drift(snapshot: RuntimeSnapshot) -> str:
    # T019 records Dossier-derived level-1 Pac-Man normal speed as 80%, or
    # 0x0103 8.8 px/frame. T008's current live movement step remains exactly
    # 1 px/frame, so this harness records the known delta instead of hiding it.
    arcade_fp = 0x0103
    current_fp = 0x0100
    drift_px = (arcade_fp - current_fp) * snapshot.replay_frame / 256.0
    return f"current_step=0x{current_fp:04X} dossier_level1_step=0x{arcade_fp:04X} drift={drift_px:.3f}px"


def run_case(case: PatternCase, evidence_dir: pathlib.Path, rom_bytes: bytes, semantic: bytes) -> CaseResult:
    replay_dir = evidence_dir / "replays"
    replay_path = replay_dir / f"{case.case_id}.v8r"
    inputs = expand_inputs(case)
    write_replay(replay_path, rom_bytes, inputs)
    replay_sha = sha256(replay_path)
    frame_hashes: dict[int, str] = {}
    details: list[str] = []
    failures: list[str] = []
    activation_frame: int | None = None

    with tempfile.TemporaryDirectory(prefix="pacmanv8-t021-") as tmp_dir_name:
        tmp_dir = pathlib.Path(tmp_dir_name)
        for checkpoint in case.checkpoints:
            inspect_path = tmp_dir / f"{case.case_id}-{checkpoint.frame}.txt"
            dump_path = None
            if checkpoint == case.checkpoints[-1] or checkpoint == case.checkpoints[1]:
                dump_path = evidence_dir / f"{case.case_id}_frame_{checkpoint.frame:04d}.ppm"
            stdout, report = run_headless(replay_path, checkpoint.frame, inspect_path, dump_path)
            observed = observed_from_report(report)
            match = FRAME_HASH_PATTERN.search(stdout)
            if match is not None:
                frame_hashes[int(match.group(1))] = match.group(2)
            label = f"{case.case_id}/{checkpoint.name}@{checkpoint.frame}"
            if observed.active != 1:
                failures.append(f"{label}: replay validation mode was not active")
                continue
            observed_activation = checkpoint.frame - observed.replay_frame
            if activation_frame is None:
                activation_frame = observed_activation
            elif activation_frame != observed_activation:
                failures.append(
                    f"{label}: activation frame drifted from {activation_frame} to {observed_activation}"
                )
            expected = expected_at_frame(inputs, semantic, checkpoint.frame, observed_activation)
            failures.extend(compare_snapshots(label, observed, expected))
            details.append(
                f"{label}: activation_frame={observed_activation} "
                f"expected {format_snapshot(expected)} | "
                f"observed {format_snapshot(observed)} | {measured_arcade_drift(observed)}"
            )
            if dump_path is not None:
                details.append(f"{label}: ppm={rel(dump_path)} sha256={sha256(dump_path)}")

    return CaseResult(
        case_id=case.case_id,
        passed=not failures,
        replay_path=replay_path,
        replay_sha=replay_sha,
        frame_hashes=frame_hashes,
        details=details,
        failures=failures,
    )


def write_vectors(
    path: pathlib.Path,
    cases: Iterable[PatternCase],
    results: Iterable[CaseResult],
    rom_hash: str,
) -> None:
    lines: list[str] = [
        "T021 pattern replay vectors",
        f"ROM: {rel(ROM_PATH)}",
        f"ROM SHA-256: {rom_hash}",
        f"Replay format: V8RR version 1, power-on anchor, active-low controller bytes",
        f"Pattern replay SRAM base: 0x{CONSTANTS['PATTERN_REPLAY_STATE_BASE']:04X}",
        "",
    ]
    results_by_id = {result.case_id: result for result in results}
    for case in cases:
        result = results_by_id[case.case_id]
        lines.extend(
            [
                f"Case: {case.case_id}",
                f"Title: {case.title}",
                f"Source file: {rel(case.source_path)}",
                f"Intent: {case.intent}",
                "Public behavior sources:",
            ]
        )
        for source in case.public_sources:
            lines.append(f"- {source['name']}: {source['url']} ({source['notes']})")
        lines.extend(
            [
                f"Replay: {rel(result.replay_path)}",
                f"Replay SHA-256: {result.replay_sha}",
                "Segments:",
            ]
        )
        for segment in case.segments:
            buttons = "+".join(segment.buttons) if segment.buttons else "neutral"
            lines.append(f"- {segment.frames} frames: {buttons}")
        lines.append("Frame hashes:")
        for frame, digest in sorted(result.frame_hashes.items()):
            lines.append(f"- frame {frame}: {digest}")
        lines.append("Checkpoints:")
        lines.extend(f"- {detail}" for detail in result.details)
        lines.append(f"Result: {'PASS' if result.passed else 'FAIL'}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic T021 pattern replay tests.")
    parser.add_argument(
        "--evidence-dir",
        type=pathlib.Path,
        default=REPO_ROOT / "tests" / "evidence" / "T021-pattern-replay-and-fidelity-testing",
    )
    args = parser.parse_args()

    if not ROM_PATH.is_file():
        raise PatternReplayError("build/pacman.rom is missing; run python3 tools/build.py first")
    if not HEADLESS.is_file():
        raise PatternReplayError(f"headless emulator not found: {HEADLESS}")

    evidence_dir = args.evidence_dir
    evidence_dir.mkdir(parents=True, exist_ok=True)
    rom_bytes = ROM_PATH.read_bytes()
    rom_hash = sha256_bytes(rom_bytes)
    semantic = SEMANTIC_PATH.read_bytes()
    cases = load_cases()
    results = [run_case(case, evidence_dir, rom_bytes, semantic) for case in cases]
    write_vectors(evidence_dir / "pattern_replay_vectors.txt", cases, results, rom_hash)

    print("T021 pattern replay and fidelity tests")
    print(f"ROM SHA-256: {rom_hash}")
    print(f"pattern sources: {rel(SOURCE_DIR)}")
    print(f"evidence dir: {rel(evidence_dir)}")
    passed = sum(1 for result in results if result.passed)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id}")
        print(f"  replay: {rel(result.replay_path)} sha256={result.replay_sha}")
        for frame, digest in sorted(result.frame_hashes.items()):
            print(f"  frame {frame} sha256={digest}")
        for failure in result.failures:
            print(f"  failure: {failure}")
    print(f"result: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, file=sys.stdout, end="")
        if error.stderr:
            print(error.stderr, file=sys.stderr, end="")
        raise SystemExit(error.returncode) from error
    except Exception as error:
        print(f"pattern_replay_tests.py error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
