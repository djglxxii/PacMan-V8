#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import sys
from collections.abc import Callable, Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SEMANTIC_PATH = REPO_ROOT / "assets" / "maze_semantic.bin"
GRAPH_PATH = REPO_ROOT / "assets" / "maze_graph.bin"
COORDMAP_PATH = REPO_ROOT / "assets" / "maze_v8_coordmap.bin"

EXPECTED_HASHES = {
    SEMANTIC_PATH: "ca8c00e7b76da593a4fc2e9c8f064dde3ac0d062ee5cce1687500850325db111",
    GRAPH_PATH: "4b355ccce9f28ad8acab093f7726287140dbcdf3429554a46473103caa1405a2",
    COORDMAP_PATH: "551bfd06927f84482f59f3c215ba39bd70b1659c3b04ba600feb80095fc567f2",
}

WIDTH_TILES = 28
HEIGHT_TILES = 36
TILE_PX = 8
TILE_CENTER_PX = 4
FP_ONE = 0x100
MAZE_WIDTH_FP = WIDTH_TILES * TILE_PX * FP_ONE

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
OPPOSITE_DIR = {
    DIR_UP: DIR_DOWN,
    DIR_LEFT: DIR_RIGHT,
    DIR_DOWN: DIR_UP,
    DIR_RIGHT: DIR_LEFT,
}

PACMAN_SPEED_FP = 0x0100
TURN_WINDOW_FP = 0x0400
PASSABLE_CLASSES = {1, 2, 3, 6}


class MovementError(AssertionError):
    pass


@dataclasses.dataclass
class MovementState:
    x_fp: int
    y_fp: int
    direction: int
    requested: int = DIR_NONE


@dataclasses.dataclass
class CaseResult:
    name: str
    passed: bool
    start: MovementState
    final: MovementState
    expected: str
    events: list[str]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def center_fp(tile: int) -> int:
    return (tile * TILE_PX + TILE_CENTER_PX) * FP_ONE


def state_summary(state: MovementState) -> str:
    return (
        f"x={state.x_fp / FP_ONE:.2f}px "
        f"y={state.y_fp / FP_ONE:.2f}px "
        f"dir={DIR_NAMES[state.direction]} "
        f"requested={DIR_NAMES[state.requested]}"
    )


class MovementCore:
    def __init__(self, semantic: bytes, state: MovementState) -> None:
        if len(semantic) != WIDTH_TILES * HEIGHT_TILES:
            raise ValueError(f"semantic grid must be {WIDTH_TILES * HEIGHT_TILES} bytes")
        self.semantic = semantic
        self.state = dataclasses.replace(state)

    def clone_state(self) -> MovementState:
        return dataclasses.replace(self.state)

    def current_tile(self) -> tuple[int, int]:
        x_px = (self.state.x_fp % MAZE_WIDTH_FP) // FP_ONE
        y_px = self.state.y_fp // FP_ONE
        return x_px // TILE_PX, y_px // TILE_PX

    def is_center(self) -> bool:
        return (
            self.state.x_fp % (TILE_PX * FP_ONE) == TILE_CENTER_PX * FP_ONE
            and self.state.y_fp % (TILE_PX * FP_ONE) == TILE_CENTER_PX * FP_ONE
        )

    def passable_cell(self, tile_x: int, tile_y: int) -> bool:
        if tile_y < 0 or tile_y >= HEIGHT_TILES:
            return False
        tile_x %= WIDTH_TILES
        return self.semantic[tile_y * WIDTH_TILES + tile_x] in PASSABLE_CLASSES

    def legal_direction(self, tile_x: int, tile_y: int, direction: int) -> bool:
        if direction not in DIR_DELTAS:
            return False
        dx, dy = DIR_DELTAS[direction]
        return self.passable_cell(tile_x + dx, tile_y + dy)

    def target_center_ahead(self) -> tuple[int, int, int]:
        direction = self.state.direction
        if direction == DIR_NONE:
            tile_x, tile_y = self.current_tile()
            return tile_x, tile_y, 0

        horizontal = direction in {DIR_LEFT, DIR_RIGHT}
        axis_fp = self.state.x_fp if horizontal else self.state.y_fp
        axis_px = axis_fp // FP_ONE
        tile = axis_px // TILE_PX
        center = center_fp(tile)

        if direction in {DIR_RIGHT, DIR_DOWN}:
            target_tile = tile if axis_fp < center else tile + 1
        else:
            target_tile = tile if axis_fp > center else tile - 1

        target_center = center_fp(target_tile)
        distance = abs(target_center - axis_fp)

        tile_x, tile_y = self.current_tile()
        if horizontal:
            tile_x = target_tile % WIDTH_TILES
        else:
            tile_y = target_tile
        return tile_x, tile_y, distance

    def request_direction(self, direction: int) -> bool:
        if direction == DIR_NONE:
            self.state.requested = DIR_NONE
            return True

        if self.state.direction == DIR_NONE:
            tile_x, tile_y = self.current_tile()
            if self.is_center() and self.legal_direction(tile_x, tile_y, direction):
                self.state.requested = direction
                return True
            return False

        if OPPOSITE_DIR.get(self.state.direction) == direction:
            self.state.requested = direction
            return True

        tile_x, tile_y, distance = self.target_center_ahead()
        if distance <= TURN_WINDOW_FP and self.legal_direction(tile_x, tile_y, direction):
            self.state.requested = direction
            return True
        return False

    def step(self, frames: int = 1) -> None:
        for _ in range(frames):
            self._step_one()

    def _step_one(self) -> None:
        remaining = PACMAN_SPEED_FP
        while remaining > 0:
            if self.is_center():
                tile_x, tile_y = self.current_tile()
                if self.legal_direction(tile_x, tile_y, self.state.requested):
                    self.state.direction = self.state.requested
                if not self.legal_direction(tile_x, tile_y, self.state.direction):
                    self.state.direction = DIR_NONE
                    return

            if self.state.direction == DIR_NONE:
                return

            turn_tile_x, turn_tile_y, distance = self.target_center_ahead()
            if (
                self.state.requested != DIR_NONE
                and distance <= remaining
                and self.legal_direction(turn_tile_x, turn_tile_y, self.state.requested)
            ):
                self._move(distance)
                remaining -= distance
                self.state.direction = self.state.requested
                continue

            move_distance = min(remaining, distance) if distance else remaining
            self._move(move_distance)
            remaining -= move_distance

            if distance and move_distance == distance:
                tile_x, tile_y = self.current_tile()
                if self.legal_direction(tile_x, tile_y, self.state.requested):
                    self.state.direction = self.state.requested
                if not self.legal_direction(tile_x, tile_y, self.state.direction):
                    self.state.direction = DIR_NONE
                    return

    def _move(self, distance: int) -> None:
        if distance <= 0:
            return
        if self.state.direction == DIR_LEFT:
            self.state.x_fp -= distance
        elif self.state.direction == DIR_RIGHT:
            self.state.x_fp += distance
        elif self.state.direction == DIR_UP:
            self.state.y_fp -= distance
        elif self.state.direction == DIR_DOWN:
            self.state.y_fp += distance
        self.state.x_fp %= MAZE_WIDTH_FP


def assert_state(
    core: MovementCore,
    *,
    x_fp: int | None = None,
    y_fp: int | None = None,
    direction: int | None = None,
) -> None:
    state = core.state
    if x_fp is not None and state.x_fp != x_fp:
        raise MovementError(f"x_fp expected {x_fp}, got {state.x_fp}")
    if y_fp is not None and state.y_fp != y_fp:
        raise MovementError(f"y_fp expected {y_fp}, got {state.y_fp}")
    if direction is not None and state.direction != direction:
        raise MovementError(
            f"direction expected {DIR_NAMES[direction]}, got {DIR_NAMES[state.direction]}"
        )


def case_straight_movement(semantic: bytes) -> CaseResult:
    start = MovementState(center_fp(1), center_fp(8), DIR_RIGHT)
    core = MovementCore(semantic, start)
    events = ["frame 0: start on row-8 horizontal corridor moving RIGHT"]
    core.step(4)
    events.append("frames 1-4: advance four fixed-point pixels")
    expected_x = center_fp(1) + 4 * FP_ONE
    assert_state(core, x_fp=expected_x, y_fp=center_fp(8), direction=DIR_RIGHT)
    return CaseResult(
        "straight_movement",
        True,
        start,
        core.clone_state(),
        f"x advances to {expected_x / FP_ONE:.2f}px; y remains centered",
        events,
    )


def case_wall_stop(semantic: bytes) -> CaseResult:
    start = MovementState(center_fp(1), center_fp(5), DIR_RIGHT)
    core = MovementCore(semantic, start)
    events = ["frame 0: start at tile (1,5), whose RIGHT neighbor is a wall"]
    core.step(3)
    events.append("frames 1-3: movement is blocked before entering tile (2,5)")
    assert_state(core, x_fp=center_fp(1), y_fp=center_fp(5), direction=DIR_NONE)
    return CaseResult(
        "wall_stop",
        True,
        start,
        core.clone_state(),
        "position remains at tile (1,5) center and direction becomes NONE",
        events,
    )


def case_early_turn_accept(semantic: bytes) -> CaseResult:
    start = MovementState((6 * TILE_PX) * FP_ONE, center_fp(8), DIR_RIGHT)
    core = MovementCore(semantic, start)
    events = [
        "frame 0: start four pixels before tile (6,8) center while moving RIGHT",
    ]
    accepted = core.request_direction(DIR_DOWN)
    events.append(f"frame 0: request DOWN accepted={accepted}")
    if not accepted:
        raise MovementError("DOWN request inside the 4-pixel window was rejected")
    core.step(5)
    events.append("frames 1-4: reach tile center and turn DOWN")
    events.append("frame 5: move one pixel down with x still on the centerline")
    assert_state(
        core,
        x_fp=center_fp(6),
        y_fp=center_fp(8) + FP_ONE,
        direction=DIR_DOWN,
    )
    return CaseResult(
        "early_turn_accept",
        True,
        start,
        core.clone_state(),
        "DOWN is buffered inside the window, turns at tile (6,8), then advances down",
        events,
    )


def case_early_turn_reject(semantic: bytes) -> CaseResult:
    start = MovementState((6 * TILE_PX - 1) * FP_ONE, center_fp(8), DIR_RIGHT)
    core = MovementCore(semantic, start)
    events = [
        "frame 0: start five pixels before tile (6,8) center while moving RIGHT",
    ]
    accepted = core.request_direction(DIR_DOWN)
    events.append(f"frame 0: one-frame DOWN tap accepted={accepted}")
    if accepted:
        raise MovementError("DOWN request outside the 4-pixel window was accepted")
    core.step(6)
    events.append("frames 1-6: pass the intersection with no queued turn")
    assert_state(
        core,
        x_fp=(6 * TILE_PX - 1) * FP_ONE + 6 * FP_ONE,
        y_fp=center_fp(8),
        direction=DIR_RIGHT,
    )
    return CaseResult(
        "early_turn_reject",
        True,
        start,
        core.clone_state(),
        "one-frame request at distance 5 is rejected; Pac-Man continues RIGHT",
        events,
    )


def case_tunnel_wrap(semantic: bytes) -> CaseResult:
    start = MovementState(center_fp(0), center_fp(17), DIR_LEFT)
    core = MovementCore(semantic, start)
    events = ["frame 0: start at left tunnel endpoint moving LEFT"]
    core.step(5)
    events.append("frames 1-5: cross x=0 and wrap to the right edge")
    expected_x = ((TILE_CENTER_PX - 5) % (WIDTH_TILES * TILE_PX)) * FP_ONE
    assert_state(core, x_fp=expected_x, y_fp=center_fp(17), direction=DIR_LEFT)
    return CaseResult(
        "tunnel_wrap",
        True,
        start,
        core.clone_state(),
        f"x wraps to {expected_x / FP_ONE:.2f}px on tunnel row 17",
        events,
    )


def run_cases(semantic: bytes) -> list[CaseResult]:
    case_functions: Iterable[Callable[[bytes], CaseResult]] = [
        case_straight_movement,
        case_wall_stop,
        case_early_turn_accept,
        case_early_turn_reject,
        case_tunnel_wrap,
    ]
    results: list[CaseResult] = []
    for case_function in case_functions:
        try:
            results.append(case_function(semantic))
        except Exception as error:
            start = MovementState(0, 0, DIR_NONE)
            results.append(
                CaseResult(
                    case_function.__name__.removeprefix("case_"),
                    False,
                    start,
                    start,
                    f"ERROR: {error}",
                    [],
                )
            )
    return results


def format_vectors(results: list[CaseResult]) -> str:
    lines = [
        "# T008 Movement Test Vectors",
        "",
        f"Position format: 8.8 fixed-point arcade pixels; tile center = tile*8+4.",
        f"Direction enum: UP={DIR_UP}, LEFT={DIR_LEFT}, DOWN={DIR_DOWN}, RIGHT={DIR_RIGHT}, NONE={DIR_NONE}.",
        f"Movement speed: 0x{PACMAN_SPEED_FP:04X} fixed-point pixels/frame.",
        f"Turn window: 0x{TURN_WINDOW_FP:04X} fixed-point pixels.",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result.name}",
                f"status: {'PASS' if result.passed else 'FAIL'}",
                f"start: {state_summary(result.start)}",
                f"expected: {result.expected}",
                f"final: {state_summary(result.final)}",
                "events:",
            ]
        )
        if result.events:
            lines.extend(f"- {event}" for event in result.events)
        else:
            lines.append("- no events recorded")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic T008 Pac-Man movement tests."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable movement vector summary.",
    )
    args = parser.parse_args()

    for path, expected_hash in EXPECTED_HASHES.items():
        if not path.is_file():
            print(f"missing input: {rel(path)}", file=sys.stderr)
            return 1
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            print(
                f"hash mismatch: {rel(path)} expected {expected_hash} got {actual_hash}",
                file=sys.stderr,
            )
            return 1

    semantic = SEMANTIC_PATH.read_bytes()
    results = run_cases(semantic)

    print("T008 movement tests")
    print("===================")
    print(f"semantic: {rel(SEMANTIC_PATH)} sha256={EXPECTED_HASHES[SEMANTIC_PATH]}")
    print(f"graph: {rel(GRAPH_PATH)} sha256={EXPECTED_HASHES[GRAPH_PATH]}")
    print(f"coordmap: {rel(COORDMAP_PATH)} sha256={EXPECTED_HASHES[COORDMAP_PATH]}")
    print(f"speed_fp=0x{PACMAN_SPEED_FP:04X}")
    print(f"turn_window_fp=0x{TURN_WINDOW_FP:04X}")
    print("")

    failures = 0
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.expected}")
        if not result.passed:
            failures += 1
    print("")
    print(f"result: {len(results) - failures}/{len(results)} passed")

    if args.vectors_output is not None:
        output_path = args.vectors_output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(format_vectors(results) + "\n", encoding="utf-8")
        print(f"wrote vectors: {output_path.relative_to(REPO_ROOT)}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
