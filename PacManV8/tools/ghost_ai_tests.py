#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import struct
import sys
from collections.abc import Callable, Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SEMANTIC_PATH = REPO_ROOT / "assets" / "maze_semantic.bin"
GRAPH_PATH = REPO_ROOT / "assets" / "maze_graph.bin"

EXPECTED_HASHES = {
    SEMANTIC_PATH: "ca8c00e7b76da593a4fc2e9c8f064dde3ac0d062ee5cce1687500850325db111",
    GRAPH_PATH: "4b355ccce9f28ad8acab093f7726287140dbcdf3429554a46473103caa1405a2",
}

WIDTH_TILES = 28
HEIGHT_TILES = 36
PASSABLE_CLASSES = {1, 2, 3, 6}

DIR_UP = 0
DIR_LEFT = 1
DIR_DOWN = 2
DIR_RIGHT = 3
DIR_NONE = 4
DIR_ORDER = [DIR_UP, DIR_LEFT, DIR_DOWN, DIR_RIGHT]

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

GHOST_BLINKY = "blinky"
GHOST_PINKY = "pinky"
GHOST_INKY = "inky"
GHOST_CLYDE = "clyde"
GHOSTS = [GHOST_BLINKY, GHOST_PINKY, GHOST_INKY, GHOST_CLYDE]

SCATTER_TARGETS = {
    GHOST_BLINKY: (25, -3),
    GHOST_PINKY: (2, -3),
    GHOST_INKY: (27, 35),
    GHOST_CLYDE: (0, 35),
}


class GhostAIError(AssertionError):
    pass


@dataclasses.dataclass(frozen=True)
class GhostContext:
    pacman_tile: tuple[int, int]
    pacman_dir: int
    blinky_tile: tuple[int, int]
    ghost_tile: tuple[int, int]


@dataclasses.dataclass
class DirectionChoice:
    tile: tuple[int, int]
    current_dir: int
    target: tuple[int, int]
    allow_reverse: bool
    legal_choices: list[tuple[int, tuple[int, int], int]]
    chosen_dir: int


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


def parse_graph_header(graph: bytes) -> tuple[int, int]:
    if len(graph) < 16:
        raise GhostAIError("maze_graph.bin is too small for its header")
    magic, version, node_count, edge_count, reserved = struct.unpack_from("<8sHHHH", graph, 0)
    if magic != b"PMVGRAF1":
        raise GhostAIError(f"graph magic expected PMVGRAF1, got {magic!r}")
    if version != 1:
        raise GhostAIError(f"graph version expected 1, got {version}")
    if reserved != 0:
        raise GhostAIError(f"graph reserved field expected 0, got {reserved}")
    expected_size = 16 + node_count * 8 + edge_count * 8
    if len(graph) != expected_size:
        raise GhostAIError(
            f"graph size expected {expected_size} from header, got {len(graph)}"
        )
    return node_count, edge_count


def ahead_tile(tile: tuple[int, int], direction: int, distance: int) -> tuple[int, int]:
    x, y = tile
    if direction == DIR_UP:
        return x - distance, y - distance
    if direction == DIR_LEFT:
        return x - distance, y
    if direction == DIR_DOWN:
        return x, y + distance
    if direction == DIR_RIGHT:
        return x + distance, y
    return x, y


def squared_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def chase_target(ghost: str, context: GhostContext) -> tuple[int, int]:
    if ghost == GHOST_BLINKY:
        return context.pacman_tile

    if ghost == GHOST_PINKY:
        return ahead_tile(context.pacman_tile, context.pacman_dir, 4)

    if ghost == GHOST_INKY:
        pivot = ahead_tile(context.pacman_tile, context.pacman_dir, 2)
        return (
            pivot[0] + (pivot[0] - context.blinky_tile[0]),
            pivot[1] + (pivot[1] - context.blinky_tile[1]),
        )

    if ghost == GHOST_CLYDE:
        if squared_distance(context.ghost_tile, context.pacman_tile) > 64:
            return context.pacman_tile
        return SCATTER_TARGETS[GHOST_CLYDE]

    raise ValueError(f"unknown ghost: {ghost}")


class MazeTopology:
    def __init__(self, semantic: bytes) -> None:
        if len(semantic) != WIDTH_TILES * HEIGHT_TILES:
            raise GhostAIError(f"semantic grid must be {WIDTH_TILES * HEIGHT_TILES} bytes")
        self.semantic = semantic

    def passable_cell(self, x: int, y: int) -> bool:
        if y < 0 or y >= HEIGHT_TILES:
            return False
        if x < 0 or x >= WIDTH_TILES:
            return False
        return self.semantic[y * WIDTH_TILES + x] in PASSABLE_CLASSES

    def neighbor(self, tile: tuple[int, int], direction: int) -> tuple[int, int] | None:
        dx, dy = DIR_DELTAS[direction]
        x = tile[0] + dx
        y = tile[1] + dy
        if direction == DIR_LEFT and tile[0] == 0:
            x = WIDTH_TILES - 1
        elif direction == DIR_RIGHT and tile[0] == WIDTH_TILES - 1:
            x = 0
        if not self.passable_cell(x, y):
            return None
        return x, y

    def choose_direction(
        self,
        tile: tuple[int, int],
        current_dir: int,
        target: tuple[int, int],
        *,
        allow_reverse: bool = False,
    ) -> DirectionChoice:
        choices: list[tuple[int, tuple[int, int], int]] = []
        chosen_dir = DIR_NONE
        best_distance: int | None = None

        for direction in DIR_ORDER:
            if not allow_reverse and OPPOSITE_DIR.get(current_dir) == direction:
                continue
            neighbor = self.neighbor(tile, direction)
            if neighbor is None:
                continue
            distance = squared_distance(neighbor, target)
            choices.append((direction, neighbor, distance))
            if best_distance is None or distance < best_distance:
                best_distance = distance
                chosen_dir = direction

        return DirectionChoice(
            tile=tile,
            current_dir=current_dir,
            target=target,
            allow_reverse=allow_reverse,
            legal_choices=choices,
            chosen_dir=chosen_dir,
        )


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise GhostAIError(f"{label}: expected {expected}, got {actual}")


def case_chase_targets(topology: MazeTopology) -> CaseResult:
    del topology
    details: list[str] = []

    blinky_context = GhostContext((14, 26), DIR_LEFT, (10, 10), (10, 10))
    target = chase_target(GHOST_BLINKY, blinky_context)
    assert_equal(target, (14, 26), "Blinky chase target")
    details.append("Blinky chase: Pac-Man at (14,26), target=(14,26)")

    pinky_context = GhostContext((14, 26), DIR_UP, (10, 10), (10, 10))
    target = chase_target(GHOST_PINKY, pinky_context)
    assert_equal(target, (10, 22), "Pinky UP overflow target")
    details.append("Pinky chase UP: Pac-Man at (14,26), target=(10,22)")

    inky_context = GhostContext((14, 26), DIR_RIGHT, (12, 26), (20, 20))
    target = chase_target(GHOST_INKY, inky_context)
    assert_equal(target, (20, 26), "Inky doubled-vector target")
    details.append(
        "Inky chase RIGHT: two-ahead pivot=(16,26), Blinky=(12,26), target=(20,26)"
    )

    clyde_far_context = GhostContext((14, 26), DIR_LEFT, (10, 10), (1, 8))
    target = chase_target(GHOST_CLYDE, clyde_far_context)
    assert_equal(target, (14, 26), "Clyde far target")
    details.append("Clyde far: ghost=(1,8), distance squared >64, target=(14,26)")

    clyde_near_context = GhostContext((14, 26), DIR_LEFT, (10, 10), (10, 26))
    target = chase_target(GHOST_CLYDE, clyde_near_context)
    assert_equal(target, SCATTER_TARGETS[GHOST_CLYDE], "Clyde near target")
    details.append("Clyde near: ghost=(10,26), distance squared <=64, target=(0,35)")

    return CaseResult(
        "chase_targets",
        True,
        "Blinky, Pinky, Inky, and Clyde chase targets match documented rules",
        details,
    )


def case_scatter_targets(topology: MazeTopology) -> CaseResult:
    del topology
    expected = {
        GHOST_BLINKY: (25, -3),
        GHOST_PINKY: (2, -3),
        GHOST_INKY: (27, 35),
        GHOST_CLYDE: (0, 35),
    }
    details = []
    for ghost in GHOSTS:
        target = SCATTER_TARGETS[ghost]
        assert_equal(target, expected[ghost], f"{ghost} scatter target")
        details.append(f"{ghost}: scatter target={target}")
    return CaseResult(
        "scatter_targets",
        True,
        "all four scatter targets are stable and distinct",
        details,
    )


def describe_choice(choice: DirectionChoice) -> list[str]:
    lines = [
        (
            f"tile={choice.tile} current={DIR_NAMES[choice.current_dir]} "
            f"target={choice.target} allow_reverse={choice.allow_reverse}"
        ),
        "legal choices in tie order:",
    ]
    for direction, neighbor, distance in choice.legal_choices:
        lines.append(
            f"  {DIR_NAMES[direction]} -> {neighbor}, squared_distance={distance}"
        )
    lines.append(f"chosen={DIR_NAMES[choice.chosen_dir]}")
    return lines


def case_direction_min_distance(topology: MazeTopology) -> CaseResult:
    choice = topology.choose_direction(
        (6, 8),
        DIR_LEFT,
        (6, 20),
        allow_reverse=False,
    )
    assert_equal(choice.chosen_dir, DIR_DOWN, "minimum-distance direction")
    return CaseResult(
        "direction_min_distance",
        True,
        "legal non-reversal direction with the smallest squared distance is chosen",
        describe_choice(choice),
    )


def case_direction_excludes_reversal_and_ties(topology: MazeTopology) -> CaseResult:
    choice = topology.choose_direction(
        (6, 8),
        DIR_RIGHT,
        (1, 8),
        allow_reverse=False,
    )
    assert_equal(choice.chosen_dir, DIR_UP, "non-reversal tie direction")
    details = describe_choice(choice)
    details.append("LEFT would be closest but is excluded as the reversal of RIGHT")
    details.append("UP and DOWN tie at squared_distance=26; UP wins by enum order")
    return CaseResult(
        "direction_excludes_reversal_and_ties",
        True,
        "reversal is excluded and equal distances keep the first enum-order direction",
        details,
    )


def case_direction_allows_reversal(topology: MazeTopology) -> CaseResult:
    choice = topology.choose_direction(
        (6, 8),
        DIR_RIGHT,
        (1, 8),
        allow_reverse=True,
    )
    assert_equal(choice.chosen_dir, DIR_LEFT, "allowed reversal direction")
    return CaseResult(
        "direction_allows_reversal",
        True,
        "when reversal is explicitly allowed, the reverse direction can win",
        describe_choice(choice),
    )


def run_cases(topology: MazeTopology) -> list[CaseResult]:
    case_functions: Iterable[Callable[[MazeTopology], CaseResult]] = [
        case_chase_targets,
        case_scatter_targets,
        case_direction_min_distance,
        case_direction_excludes_reversal_and_ties,
        case_direction_allows_reversal,
    ]
    results: list[CaseResult] = []
    for case_function in case_functions:
        try:
            results.append(case_function(topology))
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


def format_vectors(results: list[CaseResult], node_count: int, edge_count: int) -> str:
    lines = [
        "# T009 Ghost AI Test Vectors",
        "",
        f"Direction enum and tie order: UP={DIR_UP}, LEFT={DIR_LEFT}, DOWN={DIR_DOWN}, RIGHT={DIR_RIGHT}, NONE={DIR_NONE}.",
        "Position format: signed arcade tile coordinates for targets; maze cells remain 0..27 by 0..35.",
        f"Topology inputs: semantic={rel(SEMANTIC_PATH)}, graph={rel(GRAPH_PATH)}.",
        f"Graph header: nodes={node_count}, edges={edge_count}.",
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
        description="Run deterministic T009 Pac-Man ghost AI targeting tests."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable ghost AI vector summary.",
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
    graph = GRAPH_PATH.read_bytes()
    node_count, edge_count = parse_graph_header(graph)
    topology = MazeTopology(semantic)
    results = run_cases(topology)

    print("T009 ghost AI tests")
    print("===================")
    print(f"semantic: {rel(SEMANTIC_PATH)} sha256={EXPECTED_HASHES[SEMANTIC_PATH]}")
    print(f"graph: {rel(GRAPH_PATH)} sha256={EXPECTED_HASHES[GRAPH_PATH]}")
    print(f"graph_header: nodes={node_count} edges={edge_count}")
    print(
        "direction_enum: "
        f"UP={DIR_UP} LEFT={DIR_LEFT} DOWN={DIR_DOWN} RIGHT={DIR_RIGHT} NONE={DIR_NONE}"
    )
    print("tie_order: UP, LEFT, DOWN, RIGHT")
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
        output_path.write_text(
            format_vectors(results, node_count, edge_count) + "\n",
            encoding="utf-8",
        )
        print(f"wrote vectors: {output_path.relative_to(REPO_ROOT)}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
