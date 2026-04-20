#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import re
import sys
from collections.abc import Callable, Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_ASM_PATH = REPO_ROOT / "src" / "main.asm"
GAME_FLOW_ASM_PATH = REPO_ROOT / "src" / "game_flow.asm"
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
SYM_PATH = REPO_ROOT / "build" / "pacman.sym"

EQU_PATTERN = re.compile(r"^([A-Z0-9_]+)\s+EQU\s+(.+?)\s*(?:;.*)?$")
REQUIRED_SYMBOLS = {
    "game_flow_init",
    "game_flow_update_frame",
    "game_flow_transition_to",
    "game_flow_load_state_timer",
}


class GameFlowError(AssertionError):
    pass


@dataclasses.dataclass
class Transition:
    frame: int
    previous: int
    current: int
    timer: int
    script_step: int
    flags: int


@dataclasses.dataclass
class Snapshot:
    frame: int
    state: int
    previous: int
    timer: int
    entry_frame: int
    last_transition_frame: int
    transition_count: int
    flags: int
    script_step: int


@dataclasses.dataclass
class CaseResult:
    name: str
    passed: bool
    expected: str
    details: list[str]


def rel(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise GameFlowError(f"{label}: expected {expected}, got {actual}")


def assert_true(condition: bool, label: str) -> None:
    if not condition:
        raise GameFlowError(label)


def parse_equ_constants(path: pathlib.Path) -> dict[str, int]:
    raw: dict[str, str] = {}
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
            raise GameFlowError(f"could not resolve EQU constants: {unresolved}")
    return constants


CONSTANTS = parse_equ_constants(GAME_FLOW_ASM_PATH)

STATE_NAMES = {
    CONSTANTS["GAME_FLOW_STATE_ATTRACT"]: "ATTRACT",
    CONSTANTS["GAME_FLOW_STATE_READY"]: "READY",
    CONSTANTS["GAME_FLOW_STATE_PLAYING"]: "PLAYING",
    CONSTANTS["GAME_FLOW_STATE_DYING"]: "DYING",
    CONSTANTS["GAME_FLOW_STATE_LEVEL_COMPLETE"]: "LEVEL_COMPLETE",
    CONSTANTS["GAME_FLOW_STATE_CONTINUE"]: "CONTINUE",
    CONSTANTS["GAME_FLOW_STATE_NEXT_LEVEL"]: "NEXT_LEVEL",
    CONSTANTS["GAME_FLOW_STATE_INTERMISSION"]: "INTERMISSION",
}

SCRIPT_NAMES = {
    CONSTANTS["GAME_FLOW_SCRIPT_DEATH"]: "DEATH_REVIEW",
    CONSTANTS["GAME_FLOW_SCRIPT_LEVEL_COMPLETE"]: "LEVEL_COMPLETE_REVIEW",
    CONSTANTS["GAME_FLOW_SCRIPT_HANDOFF"]: "INTERMISSION_HANDOFF",
}


def state_name(state: int) -> str:
    return STATE_NAMES.get(state, f"UNKNOWN({state})")


def script_name(step: int) -> str:
    return SCRIPT_NAMES.get(step, f"UNKNOWN({step})")


class GameFlowModel:
    def __init__(self) -> None:
        self.frame = 0
        self.current = CONSTANTS["GAME_FLOW_STATE_ATTRACT"]
        self.previous = CONSTANTS["GAME_FLOW_STATE_ATTRACT"]
        self.timer = CONSTANTS["GAME_FLOW_DURATION_ATTRACT"]
        self.entry_frame = 0
        self.last_transition_frame = 0xFFFF
        self.transition_count = 0
        self.flags = CONSTANTS["GAME_FLOW_FLAG_ATTRACT"]
        self.script_step = CONSTANTS["GAME_FLOW_SCRIPT_DEATH"]
        self.transitions: list[Transition] = []

    def snapshot(self) -> Snapshot:
        return Snapshot(
            frame=self.frame,
            state=self.current,
            previous=self.previous,
            timer=self.timer,
            entry_frame=self.entry_frame,
            last_transition_frame=self.last_transition_frame,
            transition_count=self.transition_count,
            flags=self.flags,
            script_step=self.script_step,
        )

    def run_to(self, frame: int) -> None:
        while self.frame < frame:
            self.tick()

    def tick(self) -> None:
        self.frame += 1
        if self.current == CONSTANTS["GAME_FLOW_STATE_INTERMISSION"]:
            return
        if self.timer == 0:
            return
        self.timer -= 1
        if self.timer == 0:
            self.transition_elapsed()

    def transition_elapsed(self) -> None:
        if self.current == CONSTANTS["GAME_FLOW_STATE_ATTRACT"]:
            self.transition_to(CONSTANTS["GAME_FLOW_STATE_READY"])
        elif self.current == CONSTANTS["GAME_FLOW_STATE_READY"]:
            self.transition_to(CONSTANTS["GAME_FLOW_STATE_PLAYING"])
        elif self.current == CONSTANTS["GAME_FLOW_STATE_PLAYING"]:
            if self.script_step == CONSTANTS["GAME_FLOW_SCRIPT_DEATH"]:
                self.script_step = CONSTANTS["GAME_FLOW_SCRIPT_LEVEL_COMPLETE"]
                self.transition_to(CONSTANTS["GAME_FLOW_STATE_DYING"])
            else:
                self.script_step = CONSTANTS["GAME_FLOW_SCRIPT_HANDOFF"]
                self.transition_to(CONSTANTS["GAME_FLOW_STATE_LEVEL_COMPLETE"])
        elif self.current == CONSTANTS["GAME_FLOW_STATE_DYING"]:
            self.transition_to(CONSTANTS["GAME_FLOW_STATE_CONTINUE"])
        elif self.current == CONSTANTS["GAME_FLOW_STATE_CONTINUE"]:
            self.transition_to(CONSTANTS["GAME_FLOW_STATE_PLAYING"])
        elif self.current == CONSTANTS["GAME_FLOW_STATE_LEVEL_COMPLETE"]:
            self.transition_to(CONSTANTS["GAME_FLOW_STATE_NEXT_LEVEL"])
        elif self.current == CONSTANTS["GAME_FLOW_STATE_NEXT_LEVEL"]:
            self.script_step = CONSTANTS["GAME_FLOW_SCRIPT_HANDOFF"]
            self.transition_to(CONSTANTS["GAME_FLOW_STATE_INTERMISSION"])

    def transition_to(self, state: int) -> None:
        self.previous = self.current
        self.current = state
        self.last_transition_frame = self.frame
        self.entry_frame = self.frame
        self.transition_count += 1
        self.mark_seen(state)
        self.timer = self.load_timer(state)
        self.transitions.append(
            Transition(
                frame=self.frame,
                previous=self.previous,
                current=self.current,
                timer=self.timer,
                script_step=self.script_step,
                flags=self.flags,
            )
        )

    def mark_seen(self, state: int) -> None:
        flags_by_state = {
            CONSTANTS["GAME_FLOW_STATE_ATTRACT"]: CONSTANTS["GAME_FLOW_FLAG_ATTRACT"],
            CONSTANTS["GAME_FLOW_STATE_READY"]: CONSTANTS["GAME_FLOW_FLAG_READY"],
            CONSTANTS["GAME_FLOW_STATE_PLAYING"]: CONSTANTS["GAME_FLOW_FLAG_PLAYING"],
            CONSTANTS["GAME_FLOW_STATE_DYING"]: CONSTANTS["GAME_FLOW_FLAG_DYING"],
            CONSTANTS["GAME_FLOW_STATE_LEVEL_COMPLETE"]: CONSTANTS["GAME_FLOW_FLAG_LEVEL_COMPLETE"],
            CONSTANTS["GAME_FLOW_STATE_CONTINUE"]: CONSTANTS["GAME_FLOW_FLAG_CONTINUE"],
            CONSTANTS["GAME_FLOW_STATE_NEXT_LEVEL"]: CONSTANTS["GAME_FLOW_FLAG_NEXT_LEVEL"],
            CONSTANTS["GAME_FLOW_STATE_INTERMISSION"]: CONSTANTS["GAME_FLOW_FLAG_INTERMISSION"],
        }
        self.flags |= flags_by_state[state]

    def load_timer(self, state: int) -> int:
        if state == CONSTANTS["GAME_FLOW_STATE_ATTRACT"]:
            return CONSTANTS["GAME_FLOW_DURATION_ATTRACT"]
        if state == CONSTANTS["GAME_FLOW_STATE_READY"]:
            return CONSTANTS["GAME_FLOW_DURATION_READY"]
        if state == CONSTANTS["GAME_FLOW_STATE_PLAYING"]:
            if self.script_step == CONSTANTS["GAME_FLOW_SCRIPT_LEVEL_COMPLETE"]:
                return CONSTANTS["GAME_FLOW_DURATION_PLAYING_LEVEL"]
            return CONSTANTS["GAME_FLOW_DURATION_PLAYING_DYING"]
        if state == CONSTANTS["GAME_FLOW_STATE_DYING"]:
            return CONSTANTS["GAME_FLOW_DURATION_DYING"]
        if state == CONSTANTS["GAME_FLOW_STATE_CONTINUE"]:
            return CONSTANTS["GAME_FLOW_DURATION_CONTINUE"]
        if state == CONSTANTS["GAME_FLOW_STATE_LEVEL_COMPLETE"]:
            return CONSTANTS["GAME_FLOW_DURATION_LEVEL_COMPLETE"]
        if state == CONSTANTS["GAME_FLOW_STATE_NEXT_LEVEL"]:
            return CONSTANTS["GAME_FLOW_DURATION_NEXT_LEVEL"]
        return 0


def transition_summary(model: GameFlowModel) -> list[str]:
    return [
        (
            f"frame {transition.frame:04d}: "
            f"{state_name(transition.previous)} -> {state_name(transition.current)} "
            f"timer={transition.timer} script={script_name(transition.script_step)} "
            f"flags=0x{transition.flags:02X}"
        )
        for transition in model.transitions
    ]


def case_declared_states_and_flags() -> CaseResult:
    expected_states = {
        "ATTRACT": 0,
        "READY": 1,
        "PLAYING": 2,
        "DYING": 3,
        "LEVEL_COMPLETE": 4,
        "CONTINUE": 5,
        "NEXT_LEVEL": 6,
        "INTERMISSION": 7,
    }
    for name, value in expected_states.items():
        assert_equal(CONSTANTS[f"GAME_FLOW_STATE_{name}"], value, f"{name} state id")

    expected_flags = {
        "ATTRACT": 0x01,
        "READY": 0x02,
        "PLAYING": 0x04,
        "DYING": 0x08,
        "LEVEL_COMPLETE": 0x10,
        "CONTINUE": 0x20,
        "NEXT_LEVEL": 0x40,
        "INTERMISSION": 0x80,
    }
    for name, value in expected_flags.items():
        assert_equal(CONSTANTS[f"GAME_FLOW_FLAG_{name}"], value, f"{name} review flag")

    return CaseResult(
        "declared_states_and_flags",
        True,
        "state IDs are contiguous and review flags map one bit per Phase 6 state",
        [
            "states=" + ", ".join(f"{name}:{value}" for name, value in expected_states.items()),
            "flags=" + ", ".join(f"{name}:0x{value:02X}" for name, value in expected_flags.items()),
        ],
    )


def case_transition_schedule() -> CaseResult:
    model = GameFlowModel()
    expected = [
        (120, "ATTRACT", "READY", CONSTANTS["GAME_FLOW_DURATION_READY"]),
        (360, "READY", "PLAYING", CONSTANTS["GAME_FLOW_DURATION_PLAYING_DYING"]),
        (480, "PLAYING", "DYING", CONSTANTS["GAME_FLOW_DURATION_DYING"]),
        (570, "DYING", "CONTINUE", CONSTANTS["GAME_FLOW_DURATION_CONTINUE"]),
        (630, "CONTINUE", "PLAYING", CONSTANTS["GAME_FLOW_DURATION_PLAYING_LEVEL"]),
        (810, "PLAYING", "LEVEL_COMPLETE", CONSTANTS["GAME_FLOW_DURATION_LEVEL_COMPLETE"]),
        (900, "LEVEL_COMPLETE", "NEXT_LEVEL", CONSTANTS["GAME_FLOW_DURATION_NEXT_LEVEL"]),
        (960, "NEXT_LEVEL", "INTERMISSION", 0),
    ]
    model.run_to(1080)
    assert_equal(len(model.transitions), len(expected), "transition count")

    for transition, (frame, previous, current, timer) in zip(model.transitions, expected, strict=True):
        assert_equal(transition.frame, frame, f"{previous}->{current} frame")
        assert_equal(state_name(transition.previous), previous, f"{previous}->{current} previous")
        assert_equal(state_name(transition.current), current, f"{previous}->{current} current")
        assert_equal(transition.timer, timer, f"{previous}->{current} timer")

    final = model.snapshot()
    assert_equal(state_name(final.state), "INTERMISSION", "final handoff state")
    assert_equal(final.timer, 0, "intermission timer")
    assert_equal(final.transition_count, 8, "final transition count")

    return CaseResult(
        "transition_schedule",
        True,
        "boot review path reaches ATTRACT, READY, PLAYING, DYING, CONTINUE, LEVEL_COMPLETE, NEXT_LEVEL, and INTERMISSION at fixed frames",
        transition_summary(model),
    )


def case_boundary_snapshots() -> CaseResult:
    checkpoints = [
        (0, "ATTRACT", 120),
        (119, "ATTRACT", 1),
        (120, "READY", 240),
        (359, "READY", 1),
        (360, "PLAYING", 120),
        (480, "DYING", 90),
        (630, "PLAYING", 180),
        (810, "LEVEL_COMPLETE", 90),
        (960, "INTERMISSION", 0),
        (1080, "INTERMISSION", 0),
    ]
    model = GameFlowModel()
    details: list[str] = []
    for frame, expected_state, expected_timer in checkpoints:
        model.run_to(frame)
        snapshot = model.snapshot()
        assert_equal(state_name(snapshot.state), expected_state, f"state at frame {frame}")
        assert_equal(snapshot.timer, expected_timer, f"timer at frame {frame}")
        details.append(
            f"frame {frame:04d}: state={state_name(snapshot.state)} "
            f"timer={snapshot.timer} entry={snapshot.entry_frame} "
            f"last_transition={snapshot.last_transition_frame} count={snapshot.transition_count}"
        )

    return CaseResult(
        "boundary_snapshots",
        True,
        "state timer boundaries match the documented review schedule",
        details,
    )


def case_review_flags_cover_all_states() -> CaseResult:
    model = GameFlowModel()
    model.run_to(960)
    expected_flags = (
        CONSTANTS["GAME_FLOW_FLAG_ATTRACT"]
        | CONSTANTS["GAME_FLOW_FLAG_READY"]
        | CONSTANTS["GAME_FLOW_FLAG_PLAYING"]
        | CONSTANTS["GAME_FLOW_FLAG_DYING"]
        | CONSTANTS["GAME_FLOW_FLAG_LEVEL_COMPLETE"]
        | CONSTANTS["GAME_FLOW_FLAG_CONTINUE"]
        | CONSTANTS["GAME_FLOW_FLAG_NEXT_LEVEL"]
        | CONSTANTS["GAME_FLOW_FLAG_INTERMISSION"]
    )
    assert_equal(model.flags, expected_flags, "review flags")
    assert_equal(model.script_step, CONSTANTS["GAME_FLOW_SCRIPT_HANDOFF"], "final script step")

    return CaseResult(
        "review_flags_cover_all_states",
        True,
        "the textual review flag byte records that every Phase 6 state was visited exactly by the scripted path",
        [
            f"flags=0x{model.flags:02X}",
            f"script_step={script_name(model.script_step)}",
            f"visited={', '.join(STATE_NAMES[state] for state in sorted(STATE_NAMES))}",
        ],
    )


def case_assembly_wiring() -> CaseResult:
    main_text = MAIN_ASM_PATH.read_text(encoding="ascii")
    flow_text = GAME_FLOW_ASM_PATH.read_text(encoding="ascii")

    assert_true('INCLUDE "game_flow.asm"' in main_text, "main.asm must include game_flow.asm")
    assert_true("call game_flow_init" in main_text, "reset path must initialize game flow")
    assert_true("call game_flow_update_frame" in main_text, "frame loop must update game flow")

    handler = main_text.split("im1_handler:", 1)[1].split("reset_entry:", 1)[0]
    assert_true("call audio_update_frame" in handler, "VBlank handler must keep audio update")
    assert_true(
        "call game_flow_update_frame" not in handler,
        "game-flow update should stay outside IM1 to preserve accepted audio timing",
    )

    idle_loop = main_text.split("idle_loop:", 1)[1].split("init_video:", 1)[0]
    halt_index = idle_loop.index("halt")
    flow_index = idle_loop.index("call game_flow_update_frame")
    assert_true(halt_index < flow_index, "game-flow update should run after HALT returns")

    forbidden_runtime_hooks = [
        "audio_trigger_intro_music",
        "audio_trigger_intermission_music",
        "audio_trigger_death_music",
        "collision_consume_tile",
        "movement_update_pacman",
    ]
    for hook in forbidden_runtime_hooks:
        assert_true(hook not in flow_text, f"game_flow.asm should not call {hook}")

    symbol_details: list[str] = []
    if SYM_PATH.is_file():
        symbols = {
            line.split(maxsplit=1)[1]
            for line in SYM_PATH.read_text(encoding="ascii").splitlines()
            if len(line.split(maxsplit=1)) == 2
        }
        missing = sorted(REQUIRED_SYMBOLS - symbols)
        assert_true(not missing, "symbol file missing game-flow labels: " + ", ".join(missing))
        symbol_details.append(
            "symbols_present=" + ", ".join(sorted(REQUIRED_SYMBOLS))
        )
    else:
        symbol_details.append("symbols_present=not checked; build/pacman.sym not found")

    return CaseResult(
        "assembly_wiring",
        True,
        "game-flow init/update are wired from the frame loop, while accepted audio timing and gameplay/rendering slices remain untouched by the review script",
        [
            "main_include=src/game_flow.asm",
            "reset_call=game_flow_init",
            "vblank_audio_path=audio_update_frame only",
            "frame_loop=HALT then game_flow_update_frame",
            "no direct movement/collision/audio cue hooks in game_flow.asm",
            *symbol_details,
        ],
    )


def run_cases() -> list[CaseResult]:
    case_functions: Iterable[Callable[[], CaseResult]] = [
        case_declared_states_and_flags,
        case_transition_schedule,
        case_boundary_snapshots,
        case_review_flags_cover_all_states,
        case_assembly_wiring,
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


def file_hash_lines() -> list[str]:
    lines = [
        f"- {rel(MAIN_ASM_PATH)} sha256={sha256(MAIN_ASM_PATH)}",
        f"- {rel(GAME_FLOW_ASM_PATH)} sha256={sha256(GAME_FLOW_ASM_PATH)}",
        f"- {rel(pathlib.Path(__file__))} sha256={sha256(pathlib.Path(__file__))}",
    ]
    if ROM_PATH.is_file():
        lines.append(f"- {rel(ROM_PATH)} sha256={sha256(ROM_PATH)}")
    if SYM_PATH.is_file():
        lines.append(f"- {rel(SYM_PATH)} sha256={sha256(SYM_PATH)}")
    return lines


def format_vectors(results: list[CaseResult]) -> str:
    lines = [
        "# T018 Game Flow State Machine Vectors",
        "",
        "State IDs:",
        *[
            f"- {name}={CONSTANTS[f'GAME_FLOW_STATE_{name}']}"
            for name in [
                "ATTRACT",
                "READY",
                "PLAYING",
                "DYING",
                "LEVEL_COMPLETE",
                "CONTINUE",
                "NEXT_LEVEL",
                "INTERMISSION",
            ]
        ],
        "",
        "Review durations:",
        f"- ATTRACT={CONSTANTS['GAME_FLOW_DURATION_ATTRACT']} frames",
        f"- READY={CONSTANTS['GAME_FLOW_DURATION_READY']} frames",
        f"- PLAYING before DYING={CONSTANTS['GAME_FLOW_DURATION_PLAYING_DYING']} frames",
        f"- DYING={CONSTANTS['GAME_FLOW_DURATION_DYING']} frames",
        f"- CONTINUE={CONSTANTS['GAME_FLOW_DURATION_CONTINUE']} frames",
        f"- PLAYING before LEVEL_COMPLETE={CONSTANTS['GAME_FLOW_DURATION_PLAYING_LEVEL']} frames",
        f"- LEVEL_COMPLETE={CONSTANTS['GAME_FLOW_DURATION_LEVEL_COMPLETE']} frames",
        f"- NEXT_LEVEL={CONSTANTS['GAME_FLOW_DURATION_NEXT_LEVEL']} frames",
        "- INTERMISSION=handoff state with no T020 cutscene content",
        "",
        "File hashes:",
        *file_hash_lines(),
        "",
        "Case results:",
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
        description="Run deterministic T018 game-flow state-machine tests."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable game-flow vector summary.",
    )
    args = parser.parse_args()

    results = run_cases()
    failures = sum(1 for result in results if not result.passed)

    print("T018 game flow state machine tests")
    print("==================================")
    print("states: ATTRACT=0 READY=1 PLAYING=2 DYING=3 LEVEL_COMPLETE=4 CONTINUE=5 NEXT_LEVEL=6 INTERMISSION=7")
    print("review_schedule: 120,360,480,570,630,810,900,960")
    print("intermission: handoff only; no T019 speed tables or T020 cutscene content")
    print("")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.expected}")
        if not result.passed:
            print("  " + "; ".join(result.details))
    print("")
    print(f"result: {len(results) - failures}/{len(results)} passed")

    if args.vectors_output is not None:
        output_path = args.vectors_output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(format_vectors(results) + "\n", encoding="utf-8")
        print(f"wrote vectors: {rel(output_path)}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
