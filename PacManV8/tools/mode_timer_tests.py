#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import sys
from collections.abc import Callable, Iterable

from ghost_ai_tests import (
    DIR_NAMES,
    DIR_NONE,
    DIR_ORDER,
    EXPECTED_HASHES,
    GRAPH_PATH,
    GHOST_BLINKY,
    GHOST_CLYDE,
    GHOST_INKY,
    GHOST_PINKY,
    GHOSTS,
    GhostContext,
    MazeTopology,
    SCATTER_TARGETS,
    SEMANTIC_PATH,
    chase_target,
    parse_graph_header,
    rel,
    sha256,
)


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

MODE_CHASE = 0
MODE_SCATTER = 1
MODE_FRIGHTENED = 2
MODE_NAMES = {
    MODE_CHASE: "CHASE",
    MODE_SCATTER: "SCATTER",
    MODE_FRIGHTENED: "FRIGHTENED",
}

FRAMES_PER_SECOND = 60
LEVEL1_SCHEDULE = [
    (MODE_SCATTER, 7 * FRAMES_PER_SECOND),
    (MODE_CHASE, 20 * FRAMES_PER_SECOND),
    (MODE_SCATTER, 7 * FRAMES_PER_SECOND),
    (MODE_CHASE, 20 * FRAMES_PER_SECOND),
    (MODE_SCATTER, 5 * FRAMES_PER_SECOND),
    (MODE_CHASE, 20 * FRAMES_PER_SECOND),
    (MODE_SCATTER, 5 * FRAMES_PER_SECOND),
    (MODE_CHASE, None),
]
LEVEL1_BOUNDARIES = [420, 1620, 2040, 3240, 3540, 4740, 5040]
LEVEL1_FRIGHTENED_FRAMES = 6 * FRAMES_PER_SECOND
FRIGHTENED_FLASH_FRAMES = 2 * FRAMES_PER_SECOND
REVERSAL_ALL = 0x0F


class ModeTimerError(AssertionError):
    pass


@dataclasses.dataclass
class ModeSnapshot:
    frame: int
    phase: int
    mode: int
    phase_remaining: int | None
    frightened_remaining: int
    reversal_mask: int


@dataclasses.dataclass
class FrightenedChoice:
    seed_in: int
    seed_out: int
    start_index: int
    legal_choices: list[int]
    chosen_dir: int


@dataclasses.dataclass
class CaseResult:
    name: str
    passed: bool
    expected: str
    details: list[str]


class ModeController:
    def __init__(self) -> None:
        self.frame = 0
        self.phase = 0
        self.mode = MODE_SCATTER
        self.prior_mode = MODE_SCATTER
        self.phase_remaining = LEVEL1_SCHEDULE[0][1]
        self.frightened_remaining = 0
        self.reversal_mask = 0
        self.ghost_modes = {ghost: self.mode for ghost in GHOSTS}
        self.prng_state = 0x5A

    def snapshot(self) -> ModeSnapshot:
        return ModeSnapshot(
            frame=self.frame,
            phase=self.phase,
            mode=self.mode,
            phase_remaining=self.phase_remaining,
            frightened_remaining=self.frightened_remaining,
            reversal_mask=self.reversal_mask,
        )

    def consume_reversals(self) -> int:
        mask = self.reversal_mask
        self.reversal_mask = 0
        return mask

    def request_all_reversals(self) -> None:
        self.reversal_mask |= REVERSAL_ALL

    def apply_mode(self, mode: int) -> None:
        self.mode = mode
        for ghost in GHOSTS:
            self.ghost_modes[ghost] = mode

    def tick(self) -> None:
        self.frame += 1
        if self.mode == MODE_FRIGHTENED:
            if self.frightened_remaining > 0:
                self.frightened_remaining -= 1
                if self.frightened_remaining == 0:
                    self.apply_mode(self.prior_mode)
            return

        if self.phase_remaining is None:
            return

        self.phase_remaining -= 1
        if self.phase_remaining != 0:
            return

        self.phase += 1
        next_mode, next_duration = LEVEL1_SCHEDULE[self.phase]
        self.phase_remaining = next_duration
        self.apply_mode(next_mode)
        self.request_all_reversals()

    def run_to(self, frame: int) -> None:
        while self.frame < frame:
            self.tick()

    def enter_frightened(self, seed: int) -> None:
        if self.mode != MODE_FRIGHTENED:
            self.prior_mode = self.mode
        self.prng_state = seed & 0xFF
        self.apply_mode(MODE_FRIGHTENED)
        self.frightened_remaining = LEVEL1_FRIGHTENED_FRAMES
        self.request_all_reversals()

    def target_for_ghost(self, ghost: str, context: GhostContext) -> tuple[int, int] | None:
        mode = self.ghost_modes[ghost]
        if mode == MODE_SCATTER:
            return SCATTER_TARGETS[ghost]
        if mode == MODE_CHASE:
            return chase_target(ghost, context)
        return None

    def next_prng(self) -> int:
        self.prng_state = ((self.prng_state * 5) + 1) & 0xFF
        return self.prng_state

    def frightened_choice(
        self,
        topology: MazeTopology,
        tile: tuple[int, int],
        current_dir: int,
        *,
        allow_reverse: bool = False,
    ) -> FrightenedChoice:
        seed_in = self.prng_state
        seed_out = self.next_prng()
        start_index = seed_out & 0x03

        legal_choices: list[int] = []
        chosen_dir = DIR_NONE
        for offset in range(4):
            direction = DIR_ORDER[(start_index + offset) & 0x03]
            neighbor = topology.neighbor(tile, direction)
            if neighbor is None:
                continue
            if not allow_reverse and is_reverse(current_dir, direction):
                continue
            legal_choices.append(direction)
            if chosen_dir == DIR_NONE:
                chosen_dir = direction

        return FrightenedChoice(
            seed_in=seed_in,
            seed_out=seed_out,
            start_index=start_index,
            legal_choices=legal_choices,
            chosen_dir=chosen_dir,
        )


def is_reverse(current_dir: int, candidate_dir: int) -> bool:
    return {
        0: 2,
        1: 3,
        2: 0,
        3: 1,
    }.get(current_dir) == candidate_dir


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ModeTimerError(f"{label}: expected {expected}, got {actual}")


def describe_snapshot(snapshot: ModeSnapshot) -> str:
    remaining = "forever" if snapshot.phase_remaining is None else str(snapshot.phase_remaining)
    return (
        f"frame={snapshot.frame} phase={snapshot.phase} mode={MODE_NAMES[snapshot.mode]} "
        f"phase_remaining={remaining} frightened_remaining={snapshot.frightened_remaining} "
        f"reversal_mask=0x{snapshot.reversal_mask:02X}"
    )


def describe_choice(choice: FrightenedChoice) -> list[str]:
    legal = ", ".join(DIR_NAMES[direction] for direction in choice.legal_choices)
    return [
        (
            f"seed_in=0x{choice.seed_in:02X} seed_out=0x{choice.seed_out:02X} "
            f"start_index={choice.start_index}"
        ),
        f"legal_choices_in_probe_order={legal}",
        f"chosen={DIR_NAMES[choice.chosen_dir]}",
    ]


def case_level1_boundaries(topology: MazeTopology) -> CaseResult:
    del topology
    controller = ModeController()
    expected = [
        (0, MODE_SCATTER, 0),
        (419, MODE_SCATTER, 0),
        (420, MODE_CHASE, REVERSAL_ALL),
        (1619, MODE_CHASE, 0),
        (1620, MODE_SCATTER, REVERSAL_ALL),
        (2040, MODE_CHASE, REVERSAL_ALL),
        (3240, MODE_SCATTER, REVERSAL_ALL),
        (3540, MODE_CHASE, REVERSAL_ALL),
        (4740, MODE_SCATTER, REVERSAL_ALL),
        (5040, MODE_CHASE, REVERSAL_ALL),
        (9000, MODE_CHASE, 0),
    ]
    details = []
    for frame, mode, reversal_mask in expected:
        controller.run_to(frame)
        snapshot = controller.snapshot()
        assert_equal(snapshot.mode, mode, f"mode at frame {frame}")
        assert_equal(controller.consume_reversals(), reversal_mask, f"reversal at frame {frame}")
        details.append(describe_snapshot(snapshot))

    return CaseResult(
        "level1_boundaries",
        True,
        "level-1 scatter/chase changes at 420, 1620, 2040, 3240, 3540, 4740, and 5040 frames",
        details,
    )


def case_target_mode_handoff(topology: MazeTopology) -> CaseResult:
    del topology
    controller = ModeController()
    context = GhostContext((14, 26), 0, (12, 26), (20, 20))

    scatter_targets = {ghost: controller.target_for_ghost(ghost, context) for ghost in GHOSTS}
    for ghost in GHOSTS:
        assert_equal(scatter_targets[ghost], SCATTER_TARGETS[ghost], f"{ghost} scatter target")

    controller.run_to(420)
    chase_targets = {ghost: controller.target_for_ghost(ghost, context) for ghost in GHOSTS}
    assert_equal(chase_targets[GHOST_BLINKY], (14, 26), "Blinky chase handoff")
    assert_equal(chase_targets[GHOST_PINKY], (10, 22), "Pinky chase handoff")
    assert_equal(chase_targets[GHOST_INKY], (12, 22), "Inky chase handoff")
    assert_equal(chase_targets[GHOST_CLYDE], (14, 26), "Clyde chase handoff")

    return CaseResult(
        "target_mode_handoff",
        True,
        "mode controller drives T009 target selection to scatter targets in scatter and chase targets in chase",
        [
            f"initial scatter targets={scatter_targets}",
            f"frame 420 chase targets={chase_targets}",
        ],
    )


def case_frightened_entry_expiry_from_scatter(topology: MazeTopology) -> CaseResult:
    del topology
    controller = ModeController()
    controller.run_to(100)
    before = controller.snapshot()
    controller.enter_frightened(seed=0x2A)
    entry = controller.snapshot()
    assert_equal(entry.mode, MODE_FRIGHTENED, "frightened entry mode")
    assert_equal(entry.frightened_remaining, LEVEL1_FRIGHTENED_FRAMES, "frightened duration")
    assert_equal(controller.consume_reversals(), REVERSAL_ALL, "frightened entry reversal")

    controller.run_to(459)
    almost_done = controller.snapshot()
    assert_equal(almost_done.mode, MODE_FRIGHTENED, "frightened frame before expiry")
    assert_equal(almost_done.phase_remaining, before.phase_remaining, "scatter/chase timer paused")

    controller.run_to(460)
    expired = controller.snapshot()
    assert_equal(expired.mode, MODE_SCATTER, "frightened expiry restores scatter")
    assert_equal(expired.phase_remaining, before.phase_remaining, "timer position after expiry")
    assert_equal(controller.consume_reversals(), 0, "no reversal on frightened expiry")

    controller.run_to(780)
    chase = controller.snapshot()
    assert_equal(chase.mode, MODE_CHASE, "scatter resumes after frightened expiry")
    assert_equal(controller.consume_reversals(), REVERSAL_ALL, "resumed scatter/chase reversal")

    return CaseResult(
        "frightened_entry_expiry_from_scatter",
        True,
        "frightened pauses the global timer, restores scatter on expiry, then resumes the pending scatter phase",
        [
            "before: " + describe_snapshot(before),
            "entry: " + describe_snapshot(entry),
            "almost_done: " + describe_snapshot(almost_done),
            "expired: " + describe_snapshot(expired),
            "resumed_boundary: " + describe_snapshot(chase),
        ],
    )


def case_frightened_entry_expiry_from_chase(topology: MazeTopology) -> CaseResult:
    del topology
    controller = ModeController()
    controller.run_to(500)
    before = controller.snapshot()
    assert_equal(before.mode, MODE_CHASE, "precondition chase mode")
    controller.consume_reversals()
    controller.enter_frightened(seed=0x91)
    assert_equal(controller.consume_reversals(), REVERSAL_ALL, "frightened entry reversal")
    controller.run_to(860)
    expired = controller.snapshot()
    assert_equal(expired.mode, MODE_CHASE, "frightened expiry restores chase")
    assert_equal(expired.phase_remaining, before.phase_remaining, "chase timer position after expiry")

    return CaseResult(
        "frightened_entry_expiry_from_chase",
        True,
        "frightened records and restores chase mode without advancing the chase timer",
        [
            "before: " + describe_snapshot(before),
            "expired: " + describe_snapshot(expired),
        ],
    )


def case_frightened_choices(topology: MazeTopology) -> CaseResult:
    first = ModeController()
    first.enter_frightened(seed=0x33)
    choice_a = first.frightened_choice(topology, (6, 8), 3)

    repeat = ModeController()
    repeat.enter_frightened(seed=0x33)
    choice_b = repeat.frightened_choice(topology, (6, 8), 3)

    assert_equal(dataclasses.astuple(choice_a), dataclasses.astuple(choice_b), "same seed choice")
    if not choice_a.legal_choices:
        raise ModeTimerError("expected legal frightened choices at tile (6,8)")
    if choice_a.chosen_dir not in choice_a.legal_choices:
        raise ModeTimerError("chosen frightened direction was not legal")
    if is_reverse(3, choice_a.chosen_dir):
        raise ModeTimerError("frightened choice reversed without allow_reverse")

    reverse_allowed = ModeController()
    reverse_allowed.enter_frightened(seed=0x32)
    choice_c = reverse_allowed.frightened_choice(topology, (6, 8), 3, allow_reverse=True)
    if 1 not in choice_c.legal_choices:
        raise ModeTimerError("allow_reverse did not include LEFT as a legal choice")

    return CaseResult(
        "frightened_choices",
        True,
        "frightened intersection choices are deterministic for a seed and constrained to legal topology moves",
        [
            "same-seed first run:",
            *describe_choice(choice_a),
            "allow_reverse probe:",
            *describe_choice(choice_c),
        ],
    )


def run_cases(topology: MazeTopology) -> list[CaseResult]:
    case_functions: Iterable[Callable[[MazeTopology], CaseResult]] = [
        case_level1_boundaries,
        case_target_mode_handoff,
        case_frightened_entry_expiry_from_scatter,
        case_frightened_entry_expiry_from_chase,
        case_frightened_choices,
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
        "# T010 Scatter/Chase and Frightened Mode Vectors",
        "",
        f"Frame rate: {FRAMES_PER_SECOND} frames/second.",
        "Level 1 schedule: 7s scatter, 20s chase, 7s scatter, 20s chase, 5s scatter, 20s chase, 5s scatter, chase forever.",
        f"Frame boundaries: {', '.join(str(frame) for frame in LEVEL1_BOUNDARIES)}.",
        f"Level 1 frightened duration: {LEVEL1_FRIGHTENED_FRAMES} frames.",
        f"Frightened flash reservation: {FRIGHTENED_FLASH_FRAMES} frames.",
        f"Reversal mask: all ghosts = 0x{REVERSAL_ALL:02X}.",
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
        description="Run deterministic T010 scatter/chase and frightened mode tests."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable mode timer vector summary.",
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

    print("T010 mode timer and frightened tests")
    print("====================================")
    print(f"semantic: {rel(SEMANTIC_PATH)} sha256={EXPECTED_HASHES[SEMANTIC_PATH]}")
    print(f"graph: {rel(GRAPH_PATH)} sha256={EXPECTED_HASHES[GRAPH_PATH]}")
    print(f"graph_header: nodes={node_count} edges={edge_count}")
    print(f"frames_per_second: {FRAMES_PER_SECOND}")
    print(f"level1_boundaries: {','.join(str(frame) for frame in LEVEL1_BOUNDARIES)}")
    print(f"frightened_duration_frames: {LEVEL1_FRIGHTENED_FRAMES}")
    print(f"frightened_flash_frames: {FRIGHTENED_FLASH_FRAMES}")
    print(f"reversal_all_mask: 0x{REVERSAL_ALL:02X}")
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
