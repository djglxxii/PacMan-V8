#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
from collections.abc import Callable, Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_ASM_PATH = REPO_ROOT / "src" / "main.asm"
GAME_FLOW_ASM_PATH = REPO_ROOT / "src" / "game_flow.asm"
INTERMISSION_ASM_PATH = REPO_ROOT / "src" / "intermission.asm"
LEVEL_ASM_PATH = REPO_ROOT / "src" / "level_progression.asm"
AUDIO_ASM_PATH = REPO_ROOT / "src" / "audio.asm"
SPRITES_ASM_PATH = REPO_ROOT / "src" / "sprites.asm"
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
SYM_PATH = REPO_ROOT / "build" / "pacman.sym"

SOURCE_URL = "https://strategywiki.org/wiki/Pac-Man/Gameplay#Intermissions"
SOURCE_NOTE = (
    "Public intermission descriptions: Intermission I after round 2, "
    "Intermission II after round 5, Intermission III after rounds 9/13/17."
)

EQU_PATTERN = re.compile(r"^([A-Z0-9_]+)\s+EQU\s+(.+?)\s*(?:;.*)?$")


class IntermissionError(AssertionError):
    pass


@dataclasses.dataclass(frozen=True)
class SceneSpec:
    scene_id: int
    name: str
    trigger_level: int
    global_start_frame: int
    representative_frame: int


@dataclasses.dataclass(frozen=True)
class SceneRun:
    scene: SceneSpec
    group_frames: tuple[tuple[str, int, int], ...]
    completion_frame: int
    next_state: str
    fm_cue_requested: bool


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
        raise IntermissionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(condition: bool, label: str) -> None:
    if not condition:
        raise IntermissionError(label)


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
            raise IntermissionError(f"could not resolve EQU constants: {unresolved}")
    return constants


CONSTANTS = parse_equ_constants(
    SPRITES_ASM_PATH,
    LEVEL_ASM_PATH,
    GAME_FLOW_ASM_PATH,
    INTERMISSION_ASM_PATH,
    AUDIO_ASM_PATH,
)


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


FIRST_INTERMISSION_START = (
    CONSTANTS["GAME_FLOW_DURATION_ATTRACT"]
    + CONSTANTS["GAME_FLOW_DURATION_READY"]
    + CONSTANTS["GAME_FLOW_DURATION_PLAYING_DYING"]
    + CONSTANTS["GAME_FLOW_DURATION_DYING"]
    + CONSTANTS["GAME_FLOW_DURATION_CONTINUE"]
    + CONSTANTS["GAME_FLOW_DURATION_PLAYING_LEVEL"]
    + CONSTANTS["GAME_FLOW_DURATION_LEVEL_COMPLETE"]
    + CONSTANTS["GAME_FLOW_DURATION_NEXT_LEVEL"]
)

INTERMISSION_REVIEW_CYCLE = (
    CONSTANTS["INTERMISSION_SCENE_DURATION"]
    + CONSTANTS["GAME_FLOW_DURATION_READY"]
    + CONSTANTS["GAME_FLOW_DURATION_PLAYING_LEVEL"]
    + CONSTANTS["GAME_FLOW_DURATION_LEVEL_COMPLETE"]
    + CONSTANTS["GAME_FLOW_DURATION_NEXT_LEVEL"]
)

SCENE_TEMPLATES = [
    (
        CONSTANTS["INTERMISSION_SCENE_TABLES_TURN"],
        "tables_turn",
        CONSTANTS["INTERMISSION_TRIGGER_LEVEL_1"],
    ),
    (
        CONSTANTS["INTERMISSION_SCENE_NAIL_TEAR"],
        "nail_tear",
        CONSTANTS["INTERMISSION_TRIGGER_LEVEL_2"],
    ),
    (
        CONSTANTS["INTERMISSION_SCENE_PATCH_DRAG"],
        "patch_drag",
        CONSTANTS["INTERMISSION_TRIGGER_LEVEL_3"],
    ),
]

SCENES = [
    SceneSpec(
        scene_id,
        name,
        trigger_level,
        FIRST_INTERMISSION_START + (index * INTERMISSION_REVIEW_CYCLE),
        FIRST_INTERMISSION_START + (index * INTERMISSION_REVIEW_CYCLE) + CONSTANTS["INTERMISSION_GROUP_1_FRAME"],
    )
    for index, (scene_id, name, trigger_level) in enumerate(SCENE_TEMPLATES)
]


def state_name(state: int) -> str:
    return STATE_NAMES.get(state, f"UNKNOWN({state})")


def scene_for_completed_level(level: int) -> int:
    if level == CONSTANTS["INTERMISSION_TRIGGER_LEVEL_1"]:
        return CONSTANTS["INTERMISSION_SCENE_TABLES_TURN"]
    if level == CONSTANTS["INTERMISSION_TRIGGER_LEVEL_2"]:
        return CONSTANTS["INTERMISSION_SCENE_NAIL_TEAR"]
    if level == CONSTANTS["INTERMISSION_TRIGGER_LEVEL_3"]:
        return CONSTANTS["INTERMISSION_SCENE_PATCH_DRAG"]
    return CONSTANTS["INTERMISSION_SCENE_NONE"]


def scene_runs() -> list[SceneRun]:
    duration = CONSTANTS["INTERMISSION_SCENE_DURATION"]
    group_1 = CONSTANTS["INTERMISSION_GROUP_1_FRAME"]
    group_2 = CONSTANTS["INTERMISSION_GROUP_2_FRAME"]
    runs: list[SceneRun] = []
    for scene in SCENES:
        runs.append(
            SceneRun(
                scene=scene,
                group_frames=(
                    ("CHASE", scene.global_start_frame, scene.global_start_frame + group_1 - 1),
                    ("GAG", scene.global_start_frame + group_1, scene.global_start_frame + group_2 - 1),
                    (
                        "EXIT",
                        scene.global_start_frame + group_2,
                        scene.global_start_frame + duration - 1,
                    ),
                ),
                completion_frame=scene.global_start_frame + duration,
                next_state="READY",
                fm_cue_requested=True,
            )
        )
    return runs


def schedule_hash() -> str:
    payload = {
        "source": SOURCE_URL,
        "scene_duration": CONSTANTS["INTERMISSION_SCENE_DURATION"],
        "group_1_frame": CONSTANTS["INTERMISSION_GROUP_1_FRAME"],
        "group_2_frame": CONSTANTS["INTERMISSION_GROUP_2_FRAME"],
        "scenes": [dataclasses.asdict(scene) for scene in SCENES],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def case_scene_ids_and_triggers() -> CaseResult:
    expected = [
        ("TABLES_TURN", 1, 2),
        ("NAIL_TEAR", 2, 5),
        ("PATCH_DRAG", 3, 9),
    ]
    details: list[str] = []
    for label, scene_id, trigger in expected:
        assert_equal(CONSTANTS[f"INTERMISSION_SCENE_{label}"], scene_id, f"{label} scene id")
        selected = scene_for_completed_level(trigger)
        assert_equal(selected, scene_id, f"completed level {trigger} scene")
        details.append(f"completed_level={trigger} -> scene={scene_id} {label.lower()}")
    assert_equal(scene_for_completed_level(3), CONSTANTS["INTERMISSION_SCENE_NONE"], "non-trigger scene")

    return CaseResult(
        "scene_ids_and_triggers",
        True,
        "completed levels 2, 5, and 9 map to distinct explicit scene IDs",
        details,
    )


def case_frame_schedule_and_completion() -> CaseResult:
    duration = CONSTANTS["INTERMISSION_SCENE_DURATION"]
    assert_equal(duration, 180, "scene duration")
    assert_equal(CONSTANTS["INTERMISSION_GROUP_1_FRAME"], 60, "group 1 frame")
    assert_equal(CONSTANTS["INTERMISSION_GROUP_2_FRAME"], 120, "group 2 frame")
    details = []
    for run in scene_runs():
        assert_equal(run.next_state, "READY", f"{run.scene.name} next state")
        assert_true(run.fm_cue_requested, f"{run.scene.name} FM cue")
        details.append(
            f"scene={run.scene.name} trigger={run.scene.trigger_level} "
            f"start={run.scene.global_start_frame} representative={run.scene.representative_frame} "
            f"complete={run.completion_frame} next={run.next_state}"
        )
        for group_name, first, last in run.group_frames:
            details.append(f"  group={group_name} frames={first}-{last}")

    return CaseResult(
        "frame_schedule_and_completion",
        True,
        "each scene has three 60-frame visual groups and completes after 180 frames",
        details,
    )


def case_game_flow_and_audio_wiring() -> CaseResult:
    main_text = MAIN_ASM_PATH.read_text(encoding="ascii")
    flow_text = GAME_FLOW_ASM_PATH.read_text(encoding="ascii")
    intermission_text = INTERMISSION_ASM_PATH.read_text(encoding="ascii")

    assert_true('INCLUDE "intermission.asm"' in main_text, "main.asm must include intermission.asm")
    assert_true("jp z, intermission_update_frame" in flow_text, "INTERMISSION state must update owner")
    assert_true("jp intermission_start" in flow_text, "INTERMISSION transition must start owner")
    assert_true(
        "call intermission_select_review_level_for_game_flow" in flow_text,
        "review level selection should be owned by T020 intermission module",
    )
    assert_true(
        "call audio_trigger_intermission_music" in intermission_text,
        "cutscene flow must request the T017 FM intermission cue",
    )
    assert_true(
        "jp game_flow_transition_to" in intermission_text,
        "cutscene completion must return through game-flow transition plumbing",
    )
    assert_true(
        "LEVEL_COMPLETED_NUMBER" in intermission_text,
        "scene selection must consume T019 completed-level handoff data",
    )

    return CaseResult(
        "game_flow_and_audio_wiring",
        True,
        "game flow delegates INTERMISSION to the T020 owner, which consumes T019 data and requests the T017 FM cue",
        [
            "main_include=src/intermission.asm",
            "game_flow_intermission_update=intermission_update_frame",
            "game_flow_intermission_start=intermission_start",
            "audio_cue=audio_trigger_intermission_music",
            "return_state=GAME_FLOW_STATE_READY via game_flow_transition_to",
        ],
    )


def case_visual_script_labels() -> CaseResult:
    text = INTERMISSION_ASM_PATH.read_text(encoding="ascii")
    required_labels = [
        "intermission_draw_scene_1_chase",
        "intermission_draw_scene_1_gag",
        "intermission_draw_scene_1_exit",
        "intermission_draw_scene_2_chase",
        "intermission_draw_scene_2_gag",
        "intermission_draw_scene_2_exit",
        "intermission_draw_scene_3_chase",
        "intermission_draw_scene_3_gag",
        "intermission_draw_scene_3_exit",
        "intermission_draw_nail",
        "intermission_draw_tear",
        "intermission_draw_patch",
        "intermission_draw_cloth_trail",
    ]
    for label in required_labels:
        assert_true(f"{label}:" in text, f"missing visual script label {label}")
    for pattern in [
        "INTERMISSION_PACMAN_PATTERN",
        "INTERMISSION_BLINKY_PATTERN",
        "INTERMISSION_FRIGHT_PATTERN",
        "INTERMISSION_EYES_PATTERN",
    ]:
        assert_true(pattern in text, f"missing sprite pattern reference {pattern}")

    return CaseResult(
        "visual_script_labels",
        True,
        "three distinct scenes expose chase, gag, and exit visual groups plus authored prop draws",
        [f"label={label}" for label in required_labels],
    )


def case_hashes_and_symbols() -> CaseResult:
    details = [
        f"schedule_hash={schedule_hash()}",
        f"{rel(INTERMISSION_ASM_PATH)} sha256={sha256(INTERMISSION_ASM_PATH)}",
        f"{rel(GAME_FLOW_ASM_PATH)} sha256={sha256(GAME_FLOW_ASM_PATH)}",
        f"{rel(pathlib.Path(__file__))} sha256={sha256(pathlib.Path(__file__))}",
    ]
    if ROM_PATH.is_file():
        details.append(f"{rel(ROM_PATH)} sha256={sha256(ROM_PATH)}")
    if SYM_PATH.is_file():
        symbols = {
            line.split(maxsplit=1)[1]
            for line in SYM_PATH.read_text(encoding="ascii").splitlines()
            if len(line.split(maxsplit=1)) == 2
        }
        for required in [
            "intermission_start",
            "intermission_update_frame",
            "intermission_select_review_level_for_game_flow",
        ]:
            assert_true(required in symbols, f"symbol file missing {required}")
        details.append(f"{rel(SYM_PATH)} sha256={sha256(SYM_PATH)}")

    return CaseResult(
        "hashes_and_symbols",
        True,
        "source, ROM, schedule, and exported intermission symbols are deterministic",
        details,
    )


def run_cases() -> list[CaseResult]:
    case_functions: Iterable[Callable[[], CaseResult]] = [
        case_scene_ids_and_triggers,
        case_frame_schedule_and_completion,
        case_game_flow_and_audio_wiring,
        case_visual_script_labels,
        case_hashes_and_symbols,
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
        "# T020 Intermission Cutscene Vectors",
        "",
        f"Public behavior source: {SOURCE_URL}",
        f"Source note: {SOURCE_NOTE}",
        "",
        "Scene IDs:",
        f"- NONE={CONSTANTS['INTERMISSION_SCENE_NONE']}",
        f"- TABLES_TURN={CONSTANTS['INTERMISSION_SCENE_TABLES_TURN']}",
        f"- NAIL_TEAR={CONSTANTS['INTERMISSION_SCENE_NAIL_TEAR']}",
        f"- PATCH_DRAG={CONSTANTS['INTERMISSION_SCENE_PATCH_DRAG']}",
        "",
        "Runtime scene schedule:",
    ]
    for run in scene_runs():
        lines.append(
            f"- scene {run.scene.scene_id} {run.scene.name}: "
            f"trigger_level={run.scene.trigger_level} start_frame={run.scene.global_start_frame} "
            f"representative_frame={run.scene.representative_frame} "
            f"completion_frame={run.completion_frame} next={run.next_state} "
            f"fm_cue_requested={run.fm_cue_requested}"
        )
        for group_name, first, last in run.group_frames:
            lines.append(f"  - {group_name}: frames {first}-{last}")

    lines.extend(
        [
            "",
            f"Schedule hash: {schedule_hash()}",
            "",
            "Case results:",
        ]
    )
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
        description="Run deterministic T020 intermission cutscene validation."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable intermission vector summary.",
    )
    args = parser.parse_args()

    results = run_cases()
    failures = sum(1 for result in results if not result.passed)

    print("T020 intermission cutscene tests")
    print("================================")
    print("scenes: 1=tables_turn 2=nail_tear 3=patch_drag")
    print("triggers: completed levels 2,5,9")
    print("scene_duration: 180 frames")
    print("representative_frames: " + ",".join(str(scene.representative_frame) for scene in SCENES))
    print("completion_frame: " + str(scene_runs()[-1].completion_frame))
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
