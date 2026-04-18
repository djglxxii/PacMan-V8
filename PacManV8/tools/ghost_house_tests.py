#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import sys
from collections.abc import Callable, Iterable

from collision_tests import (
    CONSUME_ENERGIZER,
    CONSUME_NAMES,
    CONSUME_NONE,
    CONSUME_PELLET,
)
from mode_timer_tests import MODE_CHASE, MODE_FRIGHTENED, MODE_NAMES, ModeController


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

GHOST_BLINKY = 0
GHOST_PINKY = 1
GHOST_INKY = 2
GHOST_CLYDE = 3
GHOST_ORDER = [GHOST_BLINKY, GHOST_PINKY, GHOST_INKY, GHOST_CLYDE]
RELEASABLE_ORDER = [GHOST_PINKY, GHOST_INKY, GHOST_CLYDE]

GHOST_NAMES = {
    GHOST_BLINKY: "BLINKY",
    GHOST_PINKY: "PINKY",
    GHOST_INKY: "INKY",
    GHOST_CLYDE: "CLYDE",
}

STATE_OUTSIDE = 0
STATE_WAITING = 1
STATE_PENDING_RELEASE = 2
STATE_EXITING = 3
STATE_NAMES = {
    STATE_OUTSIDE: "OUTSIDE",
    STATE_WAITING: "WAITING",
    STATE_PENDING_RELEASE: "PENDING_RELEASE",
    STATE_EXITING: "EXITING",
}

REASON_NONE = 0
REASON_DOT = 1
REASON_TIMER = 2
REASON_NAMES = {
    REASON_NONE: "NONE",
    REASON_DOT: "DOT",
    REASON_TIMER: "TIMER",
}

RELEASE_THRESHOLDS = {
    GHOST_PINKY: 0,
    GHOST_INKY: 30,
    GHOST_CLYDE: 60,
}
FALLBACK_RELEASE_FRAMES = 4 * 60

GHOST_MASKS = {
    GHOST_BLINKY: 0x01,
    GHOST_PINKY: 0x02,
    GHOST_INKY: 0x04,
    GHOST_CLYDE: 0x08,
}


class GhostHouseError(AssertionError):
    pass


@dataclasses.dataclass
class HouseSnapshot:
    states: dict[int, int]
    dot_counts: dict[int, int]
    next_ghost: int | None
    timer: int
    release_mask: int
    exit_mask: int
    last_release: int | None
    last_reason: int


@dataclasses.dataclass
class CaseResult:
    name: str
    passed: bool
    expected: str
    details: list[str]


class GhostHouse:
    def __init__(self) -> None:
        self.states = {
            GHOST_BLINKY: STATE_OUTSIDE,
            GHOST_PINKY: STATE_WAITING,
            GHOST_INKY: STATE_WAITING,
            GHOST_CLYDE: STATE_WAITING,
        }
        self.dot_counts = {ghost: 0 for ghost in GHOST_ORDER}
        self.next_ghost: int | None = GHOST_PINKY
        self.timer = 0
        self.release_mask = 0
        self.exit_mask = 0
        self.last_release: int | None = None
        self.last_reason = REASON_NONE
        self.release_log: list[tuple[int, int]] = []
        self._try_dot_release()

    def snapshot(self) -> HouseSnapshot:
        return HouseSnapshot(
            states=dict(self.states),
            dot_counts=dict(self.dot_counts),
            next_ghost=self.next_ghost,
            timer=self.timer,
            release_mask=self.release_mask,
            exit_mask=self.exit_mask,
            last_release=self.last_release,
            last_reason=self.last_reason,
        )

    def consume_release_flags(self) -> int:
        value = self.release_mask
        self.release_mask = 0
        return value

    def consume_exit_flags(self) -> int:
        value = self.exit_mask
        self.exit_mask = 0
        return value

    def on_consume_result(self, consume_result: int) -> None:
        if consume_result not in {CONSUME_PELLET, CONSUME_ENERGIZER}:
            return
        self.timer = 0
        ghost = self.next_ghost
        if ghost is None or self.states[ghost] != STATE_WAITING:
            return
        self.dot_counts[ghost] = min(self.dot_counts[ghost] + 1, 0xFF)
        self._try_dot_release()

    def tick(self) -> None:
        ghost = self.next_ghost
        if ghost is None or self.states[ghost] != STATE_WAITING:
            return
        self.timer += 1
        if self.timer >= FALLBACK_RELEASE_FRAMES:
            self._release(ghost, REASON_TIMER)
            self.timer = 0

    def begin_next_exit(self) -> int | None:
        ghost = self.next_ghost
        if ghost is None or self.states[ghost] != STATE_PENDING_RELEASE:
            return None
        self.states[ghost] = STATE_EXITING
        self.exit_mask |= GHOST_MASKS[ghost]
        return ghost

    def complete_exit(self, ghost: int) -> None:
        if ghost not in RELEASABLE_ORDER:
            raise GhostHouseError(f"cannot complete exit for {ghost}")
        self.states[ghost] = STATE_OUTSIDE
        if self.next_ghost == ghost:
            next_index = RELEASABLE_ORDER.index(ghost) + 1
            self.next_ghost = (
                RELEASABLE_ORDER[next_index]
                if next_index < len(RELEASABLE_ORDER)
                else None
            )
            self.timer = 0

    def reset_after_life_loss(self) -> None:
        self.__init__()

    def _try_dot_release(self) -> None:
        ghost = self.next_ghost
        if ghost is None or self.states[ghost] != STATE_WAITING:
            return
        if self.dot_counts[ghost] >= RELEASE_THRESHOLDS[ghost]:
            self._release(ghost, REASON_DOT)

    def _release(self, ghost: int, reason: int) -> None:
        if self.states[ghost] != STATE_WAITING:
            return
        self.states[ghost] = STATE_PENDING_RELEASE
        self.release_mask |= GHOST_MASKS[ghost]
        self.last_release = ghost
        self.last_reason = reason
        self.release_log.append((ghost, reason))


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise GhostHouseError(f"{label}: expected {expected}, got {actual}")


def describe_snapshot(snapshot: HouseSnapshot) -> str:
    states = ", ".join(
        f"{GHOST_NAMES[ghost]}={STATE_NAMES[snapshot.states[ghost]]}"
        for ghost in GHOST_ORDER
    )
    dots = ", ".join(
        f"{GHOST_NAMES[ghost]}={snapshot.dot_counts[ghost]}"
        for ghost in RELEASABLE_ORDER
    )
    next_ghost = "NONE"
    if snapshot.next_ghost is not None:
        next_ghost = GHOST_NAMES[snapshot.next_ghost]
    last = "NONE"
    if snapshot.last_release is not None:
        last = GHOST_NAMES[snapshot.last_release]
    return (
        f"states[{states}] dots[{dots}] next={next_ghost} timer={snapshot.timer} "
        f"release_mask=0x{snapshot.release_mask:02X} exit_mask=0x{snapshot.exit_mask:02X} "
        f"last={last}/{REASON_NAMES[snapshot.last_reason]}"
    )


def release_log_names(log: list[tuple[int, int]]) -> list[str]:
    return [f"{GHOST_NAMES[ghost]}:{REASON_NAMES[reason]}" for ghost, reason in log]


def begin_and_complete(house: GhostHouse, ghost: int) -> None:
    exiting = house.begin_next_exit()
    assert_equal(exiting, ghost, f"{GHOST_NAMES[ghost]} begins exit")
    house.complete_exit(ghost)


def feed_events(house: GhostHouse, count: int, event: int = CONSUME_PELLET) -> None:
    for _ in range(count):
        house.on_consume_result(event)


def case_initial_state() -> CaseResult:
    house = GhostHouse()
    snapshot = house.snapshot()
    assert_equal(snapshot.states[GHOST_BLINKY], STATE_OUTSIDE, "Blinky state")
    assert_equal(snapshot.states[GHOST_PINKY], STATE_PENDING_RELEASE, "Pinky state")
    assert_equal(snapshot.states[GHOST_INKY], STATE_WAITING, "Inky state")
    assert_equal(snapshot.states[GHOST_CLYDE], STATE_WAITING, "Clyde state")
    assert_equal(snapshot.next_ghost, GHOST_PINKY, "first releasable ghost")
    assert_equal(snapshot.release_mask, GHOST_MASKS[GHOST_PINKY], "initial release flag")
    assert_equal(snapshot.last_reason, REASON_DOT, "initial Pinky zero-dot reason")

    return CaseResult(
        "initial_state",
        True,
        "Blinky starts outside; Pinky is immediately pending release; Inky and Clyde wait in the house",
        [
            f"thresholds={{{', '.join(f'{GHOST_NAMES[g]}:{RELEASE_THRESHOLDS[g]}' for g in RELEASABLE_ORDER)}}}",
            f"fallback_frames={FALLBACK_RELEASE_FRAMES}",
            describe_snapshot(snapshot),
        ],
    )


def case_dot_release_order_and_duplicates() -> CaseResult:
    house = GhostHouse()
    initial = house.snapshot()
    assert_equal(house.consume_release_flags(), GHOST_MASKS[GHOST_PINKY], "initial Pinky release")
    begin_and_complete(house, GHOST_PINKY)
    after_pinky = house.snapshot()

    for event in [CONSUME_NONE, CONSUME_NONE]:
        house.on_consume_result(event)
    assert_equal(house.dot_counts[GHOST_INKY], 0, "non-dot events do not count")

    feed_events(house, RELEASE_THRESHOLDS[GHOST_INKY] - 1)
    before_inky = house.snapshot()
    assert_equal(before_inky.states[GHOST_INKY], STATE_WAITING, "Inky before threshold")
    assert_equal(before_inky.dot_counts[GHOST_INKY], 29, "Inky pre-threshold count")

    house.on_consume_result(CONSUME_NONE)
    assert_equal(house.dot_counts[GHOST_INKY], 29, "duplicate/non-dot after 29")
    house.on_consume_result(CONSUME_PELLET)
    assert_equal(house.states[GHOST_INKY], STATE_PENDING_RELEASE, "Inky release")
    inky_pending = house.snapshot()
    begin_and_complete(house, GHOST_INKY)

    feed_events(house, RELEASE_THRESHOLDS[GHOST_CLYDE] - 1, CONSUME_ENERGIZER)
    before_clyde = house.snapshot()
    assert_equal(before_clyde.states[GHOST_CLYDE], STATE_WAITING, "Clyde before threshold")
    house.on_consume_result(CONSUME_NONE)
    house.on_consume_result(CONSUME_PELLET)
    assert_equal(house.states[GHOST_CLYDE], STATE_PENDING_RELEASE, "Clyde release")
    clyde_pending = house.snapshot()

    expected_log = [
        (GHOST_PINKY, REASON_DOT),
        (GHOST_INKY, REASON_DOT),
        (GHOST_CLYDE, REASON_DOT),
    ]
    assert_equal(house.release_log, expected_log, "release order")

    return CaseResult(
        "dot_release_order_and_duplicates",
        True,
        "real pellet/energizer events release Pinky, Inky, then Clyde; NONE events do not advance counters",
        [
            "initial: " + describe_snapshot(initial),
            "after_pinky_exit: " + describe_snapshot(after_pinky),
            "before_inky_threshold: " + describe_snapshot(before_inky),
            "inky_pending: " + describe_snapshot(inky_pending),
            "before_clyde_threshold: " + describe_snapshot(before_clyde),
            "clyde_pending: " + describe_snapshot(clyde_pending),
            f"release_log={release_log_names(house.release_log)}",
            f"event_types: pellet={CONSUME_NAMES[CONSUME_PELLET]}, energizer={CONSUME_NAMES[CONSUME_ENERGIZER]}, ignored={CONSUME_NAMES[CONSUME_NONE]}",
        ],
    )


def case_global_timer_fallback() -> CaseResult:
    house = GhostHouse()
    house.consume_release_flags()
    begin_and_complete(house, GHOST_PINKY)

    for _ in range(FALLBACK_RELEASE_FRAMES - 1):
        house.tick()
    before_timer = house.snapshot()
    assert_equal(before_timer.states[GHOST_INKY], STATE_WAITING, "Inky before timer threshold")
    assert_equal(before_timer.timer, FALLBACK_RELEASE_FRAMES - 1, "timer before threshold")

    house.tick()
    inky_timer = house.snapshot()
    assert_equal(inky_timer.states[GHOST_INKY], STATE_PENDING_RELEASE, "Inky timer release")
    assert_equal(inky_timer.last_reason, REASON_TIMER, "Inky timer reason")
    begin_and_complete(house, GHOST_INKY)

    house.on_consume_result(CONSUME_PELLET)
    one_dot = house.snapshot()
    for _ in range(FALLBACK_RELEASE_FRAMES - 1):
        house.tick()
    no_release_after_reset = house.snapshot()
    assert_equal(
        no_release_after_reset.states[GHOST_CLYDE],
        STATE_WAITING,
        "Clyde waits because dot reset timer",
    )
    house.tick()
    clyde_timer = house.snapshot()
    assert_equal(clyde_timer.states[GHOST_CLYDE], STATE_PENDING_RELEASE, "Clyde timer release")
    assert_equal(clyde_timer.last_reason, REASON_TIMER, "Clyde timer reason")

    return CaseResult(
        "global_timer_fallback",
        True,
        "when no qualifying dots arrive for 240 frames, the current waiting ghost becomes pending release",
        [
            "before_timer_threshold: " + describe_snapshot(before_timer),
            "inky_timer_release: " + describe_snapshot(inky_timer),
            "after_one_dot_resets_timer: " + describe_snapshot(one_dot),
            "before_clyde_timer_release: " + describe_snapshot(no_release_after_reset),
            "clyde_timer_release: " + describe_snapshot(clyde_timer),
        ],
    )


def case_life_loss_reset() -> CaseResult:
    house = GhostHouse()
    begin_and_complete(house, GHOST_PINKY)
    feed_events(house, 12)
    for _ in range(37):
        house.tick()
    before_reset = house.snapshot()
    house.reset_after_life_loss()
    after_reset = house.snapshot()

    assert_equal(after_reset.states[GHOST_BLINKY], STATE_OUTSIDE, "Blinky reset state")
    assert_equal(after_reset.states[GHOST_PINKY], STATE_PENDING_RELEASE, "Pinky reset state")
    assert_equal(after_reset.states[GHOST_INKY], STATE_WAITING, "Inky reset state")
    assert_equal(after_reset.states[GHOST_CLYDE], STATE_WAITING, "Clyde reset state")
    assert_equal(after_reset.dot_counts[GHOST_INKY], 0, "Inky counter reset")
    assert_equal(after_reset.dot_counts[GHOST_CLYDE], 0, "Clyde counter reset")
    assert_equal(after_reset.timer, 0, "global timer reset")

    return CaseResult(
        "life_loss_reset",
        True,
        "life-loss reset restores the deterministic starting house state and clears counters/timer",
        [
            "before_reset: " + describe_snapshot(before_reset),
            "after_reset: " + describe_snapshot(after_reset),
        ],
    )


def case_mode_interaction_boundaries() -> CaseResult:
    house = GhostHouse()
    controller = ModeController()
    controller.run_to(420)
    assert_equal(controller.mode, MODE_CHASE, "mode precondition")
    begin_and_complete(house, GHOST_PINKY)
    feed_events(house, RELEASE_THRESHOLDS[GHOST_INKY])
    after_house_release = house.snapshot()
    assert_equal(controller.mode, MODE_CHASE, "house release does not alter chase mode")

    controller.enter_frightened(seed=0x44)
    frightened_mode = controller.mode
    before_house_tick = house.snapshot()
    for _ in range(10):
        house.tick()
        controller.tick()
    after_house_tick = house.snapshot()
    assert_equal(frightened_mode, MODE_FRIGHTENED, "frightened precondition")
    assert_equal(after_house_tick.states, before_house_tick.states, "house state during frightened")
    assert_equal(after_house_tick.timer, before_house_tick.timer, "pending release pauses house timer")

    return CaseResult(
        "mode_interaction_boundaries",
        True,
        "house release state coexists with scatter/chase/frightened mode state without owning mode changes",
        [
            f"controller_mode_after_420={MODE_NAMES[MODE_CHASE]}",
            "after_house_release: " + describe_snapshot(after_house_release),
            f"controller_mode_after_frightened_entry={MODE_NAMES[controller.mode]}",
            "before_house_tick: " + describe_snapshot(before_house_tick),
            "after_house_tick: " + describe_snapshot(after_house_tick),
        ],
    )


def run_cases() -> list[CaseResult]:
    case_functions: Iterable[Callable[[], CaseResult]] = [
        case_initial_state,
        case_dot_release_order_and_duplicates,
        case_global_timer_fallback,
        case_life_loss_reset,
        case_mode_interaction_boundaries,
    ]
    results: list[CaseResult] = []
    for case_function in case_functions:
        try:
            results.append(case_function())
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
        "# T012 Ghost House Logic Vectors",
        "",
        "State values: OUTSIDE=0, WAITING=1, PENDING_RELEASE=2, EXITING=3.",
        "Release order: Blinky is already outside; Pinky, Inky, then Clyde are releasable.",
        f"Dot thresholds: Pinky={RELEASE_THRESHOLDS[GHOST_PINKY]}, Inky={RELEASE_THRESHOLDS[GHOST_INKY]}, Clyde={RELEASE_THRESHOLDS[GHOST_CLYDE]}.",
        f"Global fallback timer: {FALLBACK_RELEASE_FRAMES} frames.",
        "Pellet and energizer consume events both count as dots; duplicate/no-consume frames use CONSUME_NONE and do not count.",
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
        description="Run deterministic T012 ghost-house release tests."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable ghost-house vector summary.",
    )
    args = parser.parse_args()

    results = run_cases()

    print("T012 ghost house logic tests")
    print("============================")
    print("release_order: BLINKY already outside -> PINKY -> INKY -> CLYDE")
    print(
        "dot_thresholds: "
        f"pinky={RELEASE_THRESHOLDS[GHOST_PINKY]} "
        f"inky={RELEASE_THRESHOLDS[GHOST_INKY]} "
        f"clyde={RELEASE_THRESHOLDS[GHOST_CLYDE]}"
    )
    print(f"global_fallback_frames: {FALLBACK_RELEASE_FRAMES}")
    print("states: outside=0 waiting=1 pending_release=2 exiting=3")
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
