#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import sys
from collections.abc import Callable, Iterable

from mode_timer_tests import (
    LEVEL1_FRIGHTENED_FRAMES,
    MODE_CHASE,
    MODE_FRIGHTENED,
    MODE_NAMES,
    MODE_SCATTER,
    REVERSAL_ALL,
    ModeController,
)


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
BITSET_BYTES = (WIDTH_TILES * HEIGHT_TILES + 7) // 8

SEMANTIC_PELLET = 2
SEMANTIC_ENERGIZER = 3

CONSUME_NONE = 0
CONSUME_PELLET = 1
CONSUME_ENERGIZER = 2
CONSUME_NAMES = {
    CONSUME_NONE: "NONE",
    CONSUME_PELLET: "PELLET",
    CONSUME_ENERGIZER: "ENERGIZER",
}

GHOST_NONE = 0
GHOST_PACMAN_DIES = 1
GHOST_EATEN = 2
GHOST_RESULT_NAMES = {
    GHOST_NONE: "NO_COLLISION",
    GHOST_PACMAN_DIES: "PACMAN_DIES",
    GHOST_EATEN: "GHOST_EATEN",
}


class CollisionError(AssertionError):
    pass


@dataclasses.dataclass(frozen=True)
class EraseEntry:
    tile: tuple[int, int]
    kind: int


@dataclasses.dataclass
class CollisionSnapshot:
    pellets_remaining: int
    energizers_remaining: int
    dot_stall: int
    erase_entry: EraseEntry | None
    last_consume: int


@dataclasses.dataclass
class CaseResult:
    name: str
    passed: bool
    expected: str
    details: list[str]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def center_fp(tile: int) -> int:
    return (tile * TILE_PX + TILE_CENTER_PX) * FP_ONE


def tile_from_fp(x_fp: int, y_fp: int) -> tuple[int, int]:
    return (x_fp // FP_ONE) // TILE_PX, (y_fp // FP_ONE) // TILE_PX


def is_center(x_fp: int, y_fp: int) -> bool:
    return (
        x_fp % (TILE_PX * FP_ONE) == TILE_CENTER_PX * FP_ONE
        and y_fp % (TILE_PX * FP_ONE) == TILE_CENTER_PX * FP_ONE
    )


def find_tiles(semantic: bytes, semantic_class: int) -> list[tuple[int, int]]:
    return [
        (index % WIDTH_TILES, index // WIDTH_TILES)
        for index, value in enumerate(semantic)
        if value == semantic_class
    ]


class CollisionCore:
    def __init__(self, semantic: bytes) -> None:
        if len(semantic) != WIDTH_TILES * HEIGHT_TILES:
            raise CollisionError(
                f"semantic grid must be {WIDTH_TILES * HEIGHT_TILES} bytes"
            )
        self.semantic = semantic
        self.present_bits = bytearray(BITSET_BYTES)
        self.pellets_remaining = 0
        self.energizers_remaining = 0
        self.dot_stall = 0
        self.erase_entry: EraseEntry | None = None
        self.last_consume = CONSUME_NONE
        self.last_ghost_result = GHOST_NONE
        self._init_from_semantic()

    def _init_from_semantic(self) -> None:
        for index, value in enumerate(self.semantic):
            if value not in {SEMANTIC_PELLET, SEMANTIC_ENERGIZER}:
                continue
            self.present_bits[index >> 3] |= 1 << (index & 0x07)
            if value == SEMANTIC_PELLET:
                self.pellets_remaining += 1
            else:
                self.energizers_remaining += 1

    def snapshot(self) -> CollisionSnapshot:
        return CollisionSnapshot(
            pellets_remaining=self.pellets_remaining,
            energizers_remaining=self.energizers_remaining,
            dot_stall=self.dot_stall,
            erase_entry=self.erase_entry,
            last_consume=self.last_consume,
        )

    def has_consumable(self, tile: tuple[int, int]) -> bool:
        index = self._index(tile)
        return bool(self.present_bits[index >> 3] & (1 << (index & 0x07)))

    def clear_erase_queue(self) -> None:
        self.erase_entry = None

    def tick_dot_stall(self) -> int:
        if self.dot_stall > 0:
            self.dot_stall -= 1
        return self.dot_stall

    def consume_at_pacman(
        self,
        x_fp: int,
        y_fp: int,
        mode_controller: ModeController | None = None,
    ) -> int:
        self.last_consume = CONSUME_NONE
        if not is_center(x_fp, y_fp):
            return CONSUME_NONE
        return self.consume_tile(tile_from_fp(x_fp, y_fp), mode_controller)

    def consume_tile(
        self,
        tile: tuple[int, int],
        mode_controller: ModeController | None = None,
    ) -> int:
        self.last_consume = CONSUME_NONE
        x, y = tile
        if not (0 <= x < WIDTH_TILES and 0 <= y < HEIGHT_TILES):
            return CONSUME_NONE

        index = self._index(tile)
        semantic_class = self.semantic[index]
        if semantic_class not in {SEMANTIC_PELLET, SEMANTIC_ENERGIZER}:
            return CONSUME_NONE

        mask = 1 << (index & 0x07)
        byte_index = index >> 3
        if not self.present_bits[byte_index] & mask:
            return CONSUME_NONE

        self.present_bits[byte_index] &= 0xFF ^ mask
        if semantic_class == SEMANTIC_PELLET:
            self.pellets_remaining -= 1
            self.dot_stall = 1
            result = CONSUME_PELLET
        else:
            self.energizers_remaining -= 1
            self.dot_stall = 3
            result = CONSUME_ENERGIZER
            if mode_controller is not None:
                mode_controller.enter_frightened(seed=0x2A)

        self.erase_entry = EraseEntry(tile=tile, kind=result)
        self.last_consume = result
        return result

    def ghost_collision(
        self,
        pacman_tile: tuple[int, int],
        ghost_tile: tuple[int, int],
        ghost_mode: int,
    ) -> int:
        if pacman_tile != ghost_tile:
            self.last_ghost_result = GHOST_NONE
        elif ghost_mode == MODE_FRIGHTENED:
            self.last_ghost_result = GHOST_EATEN
        else:
            self.last_ghost_result = GHOST_PACMAN_DIES
        return self.last_ghost_result

    @staticmethod
    def _index(tile: tuple[int, int]) -> int:
        return tile[1] * WIDTH_TILES + tile[0]


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise CollisionError(f"{label}: expected {expected}, got {actual}")


def describe_snapshot(snapshot: CollisionSnapshot) -> str:
    erase = "none"
    if snapshot.erase_entry is not None:
        erase = (
            f"tile={snapshot.erase_entry.tile} "
            f"kind={CONSUME_NAMES[snapshot.erase_entry.kind]}"
        )
    return (
        f"pellets={snapshot.pellets_remaining} "
        f"energizers={snapshot.energizers_remaining} "
        f"dot_stall={snapshot.dot_stall} "
        f"erase={erase} "
        f"last_consume={CONSUME_NAMES[snapshot.last_consume]}"
    )


def case_initial_counts(semantic: bytes) -> CaseResult:
    pellet_tiles = find_tiles(semantic, SEMANTIC_PELLET)
    energizer_tiles = find_tiles(semantic, SEMANTIC_ENERGIZER)
    core = CollisionCore(semantic)
    assert_equal(core.pellets_remaining, 240, "initial pellet count")
    assert_equal(core.energizers_remaining, 4, "initial energizer count")
    assert_equal(len(pellet_tiles), core.pellets_remaining, "pellet scan count")
    assert_equal(len(energizer_tiles), core.energizers_remaining, "energizer scan count")
    return CaseResult(
        "initial_counts",
        True,
        "semantic maze initializes 240 normal pellets and 4 energizers in the runtime bitset",
        [
            f"bitset_bytes={BITSET_BYTES}",
            f"first_pellets={pellet_tiles[:8]}",
            f"energizers={energizer_tiles}",
            "snapshot: " + describe_snapshot(core.snapshot()),
        ],
    )


def case_pellet_consumption_and_duplicate(semantic: bytes) -> CaseResult:
    pellet_tile = find_tiles(semantic, SEMANTIC_PELLET)[0]
    core = CollisionCore(semantic)
    start = core.snapshot()

    off_center = core.consume_at_pacman(
        center_fp(pellet_tile[0]) + 0x80,
        center_fp(pellet_tile[1]),
    )
    assert_equal(off_center, CONSUME_NONE, "off-center pellet consume")
    assert_equal(core.pellets_remaining, start.pellets_remaining, "off-center count")
    assert_equal(core.has_consumable(pellet_tile), True, "off-center bit state")

    consumed = core.consume_at_pacman(center_fp(pellet_tile[0]), center_fp(pellet_tile[1]))
    assert_equal(consumed, CONSUME_PELLET, "center pellet consume")
    assert_equal(core.pellets_remaining, start.pellets_remaining - 1, "pellet count")
    assert_equal(core.has_consumable(pellet_tile), False, "pellet bit cleared")
    assert_equal(core.dot_stall, 1, "pellet dot-stall frames")
    assert_equal(core.erase_entry, EraseEntry(pellet_tile, CONSUME_PELLET), "erase entry")
    after_center = core.snapshot()

    core.clear_erase_queue()
    duplicate = core.consume_at_pacman(center_fp(pellet_tile[0]), center_fp(pellet_tile[1]))
    assert_equal(duplicate, CONSUME_NONE, "duplicate pellet consume")
    assert_equal(core.pellets_remaining, start.pellets_remaining - 1, "duplicate count")
    assert_equal(core.erase_entry, None, "duplicate erase queue")
    after_duplicate = core.snapshot()

    tick_after_pellet = core.tick_dot_stall()
    assert_equal(tick_after_pellet, 0, "pellet dot-stall expiry")

    return CaseResult(
        "pellet_consumption_and_duplicate",
        True,
        "normal pellet consumes only at exact tile center, queues one erase, stalls for 1 frame, and cannot be consumed twice",
        [
            f"tile={pellet_tile}",
            f"fixed_point_center=(0x{center_fp(pellet_tile[0]):04X},0x{center_fp(pellet_tile[1]):04X})",
            f"off_center_result={CONSUME_NAMES[off_center]}",
            "after_center: " + describe_snapshot(after_center),
            "after_duplicate: " + describe_snapshot(after_duplicate),
            f"dot_stall_after_one_tick={tick_after_pellet}",
        ],
    )


def case_energizer_frightened_and_stall(semantic: bytes) -> CaseResult:
    energizer_tile = find_tiles(semantic, SEMANTIC_ENERGIZER)[0]
    core = CollisionCore(semantic)
    controller = ModeController()
    start = core.snapshot()

    consumed = core.consume_at_pacman(
        center_fp(energizer_tile[0]),
        center_fp(energizer_tile[1]),
        controller,
    )
    assert_equal(consumed, CONSUME_ENERGIZER, "energizer consume")
    assert_equal(core.energizers_remaining, start.energizers_remaining - 1, "energizer count")
    assert_equal(core.has_consumable(energizer_tile), False, "energizer bit cleared")
    assert_equal(core.dot_stall, 3, "energizer dot-stall frames")
    assert_equal(core.erase_entry, EraseEntry(energizer_tile, CONSUME_ENERGIZER), "erase entry")
    assert_equal(controller.mode, MODE_FRIGHTENED, "frightened mode after energizer")
    assert_equal(
        controller.frightened_remaining,
        LEVEL1_FRIGHTENED_FRAMES,
        "frightened duration",
    )
    assert_equal(controller.consume_reversals(), REVERSAL_ALL, "frightened reversal mask")
    after_consume = core.snapshot()

    stall_sequence = [core.dot_stall]
    for _ in range(3):
        stall_sequence.append(core.tick_dot_stall())
    assert_equal(stall_sequence, [3, 2, 1, 0], "energizer dot-stall sequence")

    return CaseResult(
        "energizer_frightened_and_stall",
        True,
        "energizer consumes at center, queues erase, stalls for 3 frames, enters T010 frightened mode, and requests all reversals",
        [
            f"tile={energizer_tile}",
            f"fixed_point_center=(0x{center_fp(energizer_tile[0]):04X},0x{center_fp(energizer_tile[1]):04X})",
            "after_consume: " + describe_snapshot(after_consume),
            f"mode={MODE_NAMES[controller.mode]} frightened_remaining={controller.frightened_remaining}",
            f"reversal_mask=0x{REVERSAL_ALL:02X}",
            f"dot_stall_sequence={stall_sequence}",
        ],
    )


def case_ghost_collision_outcomes(semantic: bytes) -> CaseResult:
    core = CollisionCore(semantic)
    pacman_tile = (14, 26)

    chase = core.ghost_collision(pacman_tile, pacman_tile, MODE_CHASE)
    scatter = core.ghost_collision(pacman_tile, pacman_tile, MODE_SCATTER)
    frightened = core.ghost_collision(pacman_tile, pacman_tile, MODE_FRIGHTENED)
    separate = core.ghost_collision(pacman_tile, (14, 25), MODE_FRIGHTENED)

    assert_equal(chase, GHOST_PACMAN_DIES, "chase same-tile collision")
    assert_equal(scatter, GHOST_PACMAN_DIES, "scatter same-tile collision")
    assert_equal(frightened, GHOST_EATEN, "frightened same-tile collision")
    assert_equal(separate, GHOST_NONE, "different-tile collision")

    return CaseResult(
        "ghost_collision_outcomes",
        True,
        "same-tile normal ghosts kill Pac-Man, frightened ghosts are eaten, and different tiles do not collide",
        [
            f"pacman_tile={pacman_tile}",
            f"CHASE same tile -> {GHOST_RESULT_NAMES[chase]}",
            f"SCATTER same tile -> {GHOST_RESULT_NAMES[scatter]}",
            f"FRIGHTENED same tile -> {GHOST_RESULT_NAMES[frightened]}",
            f"FRIGHTENED at (14,25) -> {GHOST_RESULT_NAMES[separate]}",
        ],
    )


def run_cases(semantic: bytes) -> list[CaseResult]:
    case_functions: Iterable[Callable[[bytes], CaseResult]] = [
        case_initial_counts,
        case_pellet_consumption_and_duplicate,
        case_energizer_frightened_and_stall,
        case_ghost_collision_outcomes,
    ]
    results: list[CaseResult] = []
    for case_function in case_functions:
        try:
            results.append(case_function(semantic))
        except Exception as error:
            results.append(
                CaseResult(
                    case_function.__name__.removeprefix("case_"),
                    False,
                    f"ERROR: {error}",
                    [],
                )
            )
    return results


def format_vectors(results: list[CaseResult]) -> str:
    lines = [
        "# T011 Collision, Pellet, and Dot-Stall Vectors",
        "",
        "Position format: 8.8 fixed-point arcade pixels.",
        "Tile center formula: (tile * 8 + 4) << 8.",
        f"Semantic classes: pellet={SEMANTIC_PELLET}, energizer={SEMANTIC_ENERGIZER}.",
        f"Runtime consumable bitset bytes: {BITSET_BYTES}.",
        f"Dot-stall frames: pellet=1, energizer=3.",
        "Ghost collision modes: normal scatter/chase kills Pac-Man; frightened ghost is eaten.",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result.name}",
                f"status: {'PASS' if result.passed else 'FAIL'}",
                f"expected: {result.expected}",
                "details:",
            ]
        )
        if result.details:
            lines.extend(f"- {detail}" for detail in result.details)
        else:
            lines.append("- no details recorded")
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic T011 collision, pellet, and dot-stall tests."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable collision vector summary.",
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

    print("T011 collision, pellet, and dot-stall tests")
    print("============================================")
    print(f"semantic: {rel(SEMANTIC_PATH)} sha256={EXPECTED_HASHES[SEMANTIC_PATH]}")
    print(f"graph: {rel(GRAPH_PATH)} sha256={EXPECTED_HASHES[GRAPH_PATH]}")
    print(f"coordmap: {rel(COORDMAP_PATH)} sha256={EXPECTED_HASHES[COORDMAP_PATH]}")
    print(f"bitset_bytes: {BITSET_BYTES}")
    print("dot_stall_frames: pellet=1 energizer=3")
    print(f"frightened_reversal_mask: 0x{REVERSAL_ALL:02X}")
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
