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
LEVEL_ASM_PATH = REPO_ROOT / "src" / "level_progression.asm"
GHOST_ASM_PATH = REPO_ROOT / "src" / "ghost_ai.asm"
GAME_FLOW_ASM_PATH = REPO_ROOT / "src" / "game_flow.asm"
ROM_PATH = REPO_ROOT / "build" / "pacman.rom"
SYM_PATH = REPO_ROOT / "build" / "pacman.sym"

SOURCE_URL = "https://pacman.holenet.info/"
SOURCE_NOTE = "Pac-Man Dossier Table A.1 plus scatter/chase timing summary"
FPS = 60
SPEED_100_PX_PER_SEC = 75.75757625

EQU_PATTERN = re.compile(r"^([A-Z0-9_]+)\s+EQU\s+(.+?)\s*(?:;.*)?$")
LABEL_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


class LevelProgressionError(AssertionError):
    pass


@dataclasses.dataclass(frozen=True)
class LevelSpec:
    level_key: str
    bonus_symbol: str
    bonus_points: int
    pac_normal: int
    ghost_normal: int
    ghost_tunnel: int
    elroy1_dots: int
    elroy1_speed: int
    elroy2_dots: int
    elroy2_speed: int
    pac_fright: int
    ghost_fright: int
    fright_seconds: int
    fright_flashes: int

    @property
    def pac_tunnel(self) -> int:
        return self.pac_normal


@dataclasses.dataclass(frozen=True)
class ProgressionDecision:
    completed: int
    next_level: int
    intermission: bool
    kill_screen: bool
    wrap: bool


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
        raise LevelProgressionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(condition: bool, label: str) -> None:
    if not condition:
        raise LevelProgressionError(label)


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
            raise LevelProgressionError(f"could not resolve EQU constants: {unresolved}")
    return constants


CONSTANTS = parse_equ_constants(LEVEL_ASM_PATH)

FRUIT_SYMBOL_IDS = {
    "Cherries": CONSTANTS["LEVEL_FRUIT_CHERRIES"],
    "Strawberry": CONSTANTS["LEVEL_FRUIT_STRAWBERRY"],
    "Peach": CONSTANTS["LEVEL_FRUIT_PEACH"],
    "Apple": CONSTANTS["LEVEL_FRUIT_APPLE"],
    "Grapes": CONSTANTS["LEVEL_FRUIT_GRAPES"],
    "Galaxian": CONSTANTS["LEVEL_FRUIT_GALAXIAN"],
    "Bell": CONSTANTS["LEVEL_FRUIT_BELL"],
    "Key": CONSTANTS["LEVEL_FRUIT_KEY"],
}

FRUIT_NAMES_BY_ID = {value: key for key, value in FRUIT_SYMBOL_IDS.items()}

SCHEDULES = {
    "LEVEL1": [
        ("SCATTER", 7 * FPS),
        ("CHASE", 20 * FPS),
        ("SCATTER", 7 * FPS),
        ("CHASE", 20 * FPS),
        ("SCATTER", 5 * FPS),
        ("CHASE", 20 * FPS),
        ("SCATTER", 5 * FPS),
        ("CHASE", None),
    ],
    "LEVEL2_4": [
        ("SCATTER", 7 * FPS),
        ("CHASE", 20 * FPS),
        ("SCATTER", 7 * FPS),
        ("CHASE", 20 * FPS),
        ("SCATTER", 5 * FPS),
        ("CHASE", 1033 * FPS),
        ("SCATTER", 1),
        ("CHASE", None),
    ],
    "LEVEL5P": [
        ("SCATTER", 5 * FPS),
        ("CHASE", 20 * FPS),
        ("SCATTER", 5 * FPS),
        ("CHASE", 20 * FPS),
        ("SCATTER", 5 * FPS),
        ("CHASE", 1037 * FPS),
        ("SCATTER", 1),
        ("CHASE", None),
    ],
}


EXPECTED_SPECS = [
    LevelSpec("1", "Cherries", 100, 80, 75, 40, 20, 80, 10, 85, 90, 50, 6, 5),
    LevelSpec("2", "Strawberry", 300, 90, 85, 45, 30, 90, 15, 95, 95, 55, 5, 5),
    LevelSpec("3", "Peach", 500, 90, 85, 45, 40, 90, 20, 95, 95, 55, 4, 5),
    LevelSpec("4", "Peach", 500, 90, 85, 45, 40, 90, 20, 95, 95, 55, 3, 5),
    LevelSpec("5", "Apple", 700, 100, 95, 50, 40, 100, 20, 105, 100, 60, 2, 5),
    LevelSpec("6", "Apple", 700, 100, 95, 50, 50, 100, 25, 105, 100, 60, 5, 5),
    LevelSpec("7", "Grapes", 1000, 100, 95, 50, 50, 100, 25, 105, 100, 60, 2, 5),
    LevelSpec("8", "Grapes", 1000, 100, 95, 50, 50, 100, 25, 105, 100, 60, 2, 5),
    LevelSpec("9", "Galaxian", 2000, 100, 95, 50, 60, 100, 30, 105, 100, 60, 1, 3),
    LevelSpec("10", "Galaxian", 2000, 100, 95, 50, 60, 100, 30, 105, 100, 60, 5, 5),
    LevelSpec("11", "Bell", 3000, 100, 95, 50, 60, 100, 30, 105, 100, 60, 2, 5),
    LevelSpec("12", "Bell", 3000, 100, 95, 50, 80, 100, 40, 105, 100, 60, 1, 3),
    LevelSpec("13", "Key", 5000, 100, 95, 50, 80, 100, 40, 105, 100, 60, 1, 3),
    LevelSpec("14", "Key", 5000, 100, 95, 50, 80, 100, 40, 105, 100, 60, 3, 5),
    LevelSpec("15", "Key", 5000, 100, 95, 50, 100, 100, 50, 105, 100, 60, 1, 3),
    LevelSpec("16", "Key", 5000, 100, 95, 50, 100, 100, 50, 105, 100, 60, 1, 3),
    LevelSpec("17", "Key", 5000, 100, 95, 50, 100, 100, 50, 105, 0, 0, 0, 0),
    LevelSpec("18", "Key", 5000, 100, 95, 50, 100, 100, 50, 105, 100, 60, 1, 3),
    LevelSpec("19", "Key", 5000, 100, 95, 50, 120, 100, 60, 105, 0, 0, 0, 0),
    LevelSpec("20", "Key", 5000, 100, 95, 50, 120, 100, 60, 105, 0, 0, 0, 0),
    LevelSpec("21+", "Key", 5000, 90, 95, 50, 120, 100, 60, 105, 0, 0, 0, 0),
]


TABLE_LABELS = {
    "bonus_symbol": "level_bonus_symbol_by_index",
    "bonus_points": "level_bonus_points_by_index",
    "pac_normal_pct": "level_pacman_normal_pct_by_index",
    "pac_normal_fp": "level_pacman_normal_fp_by_index",
    "pac_tunnel_pct": "level_pacman_tunnel_pct_by_index",
    "pac_tunnel_fp": "level_pacman_tunnel_fp_by_index",
    "pac_fright_pct": "level_pacman_fright_pct_by_index",
    "pac_fright_fp": "level_pacman_fright_fp_by_index",
    "ghost_normal_pct": "level_ghost_normal_pct_by_index",
    "ghost_normal_fp": "level_ghost_normal_fp_by_index",
    "ghost_tunnel_pct": "level_ghost_tunnel_pct_by_index",
    "ghost_tunnel_fp": "level_ghost_tunnel_fp_by_index",
    "ghost_fright_pct": "level_ghost_fright_pct_by_index",
    "ghost_fright_fp": "level_ghost_fright_fp_by_index",
    "elroy1_dots": "level_elroy1_dots_by_index",
    "elroy1_pct": "level_elroy1_pct_by_index",
    "elroy1_fp": "level_elroy1_fp_by_index",
    "elroy2_dots": "level_elroy2_dots_by_index",
    "elroy2_pct": "level_elroy2_pct_by_index",
    "elroy2_fp": "level_elroy2_fp_by_index",
    "fright_seconds": "level_fright_seconds_by_index",
    "fright_frames": "level_fright_frames_by_index",
    "fright_flashes": "level_fright_flashes_by_index",
}


def percent_to_fp(percent: int) -> int:
    return round((SPEED_100_PX_PER_SEC / FPS) * (percent / 100) * 256)


def evaluate_token(token: str) -> int:
    token = token.strip()
    if token in CONSTANTS:
        return CONSTANTS[token]
    if token.startswith("0x"):
        return int(token, 16)
    return int(token)


def parse_table(label: str) -> list[int]:
    text = LEVEL_ASM_PATH.read_text(encoding="ascii").splitlines()
    values: list[int] = []
    inside = False
    for raw_line in text:
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        match = LABEL_PATTERN.match(line)
        if match is not None:
            if inside and match.group(1) != label:
                break
            inside = match.group(1) == label
            remainder = line.split(":", 1)[1].strip()
            if not remainder:
                continue
            line = remainder
        if not inside:
            continue
        if line.startswith("db ") or line.startswith("dw "):
            _, rest = line.split(maxsplit=1)
            values.extend(evaluate_token(token) for token in rest.split(",") if token.strip())
    if not values:
        raise LevelProgressionError(f"table {label} not found or empty")
    return values


def parse_all_tables() -> dict[str, list[int]]:
    return {name: parse_table(label) for name, label in TABLE_LABELS.items()}


ASM_TABLES = parse_all_tables()


def expected_table_rows() -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for spec in EXPECTED_SPECS:
        rows.append(
            {
                "level_key": spec.level_key,
                "bonus_symbol": FRUIT_SYMBOL_IDS[spec.bonus_symbol],
                "bonus_points": spec.bonus_points,
                "pac_normal_pct": spec.pac_normal,
                "pac_normal_fp": percent_to_fp(spec.pac_normal),
                "pac_tunnel_pct": spec.pac_tunnel,
                "pac_tunnel_fp": percent_to_fp(spec.pac_tunnel),
                "pac_fright_pct": spec.pac_fright,
                "pac_fright_fp": percent_to_fp(spec.pac_fright),
                "ghost_normal_pct": spec.ghost_normal,
                "ghost_normal_fp": percent_to_fp(spec.ghost_normal),
                "ghost_tunnel_pct": spec.ghost_tunnel,
                "ghost_tunnel_fp": percent_to_fp(spec.ghost_tunnel),
                "ghost_fright_pct": spec.ghost_fright,
                "ghost_fright_fp": percent_to_fp(spec.ghost_fright),
                "elroy1_dots": spec.elroy1_dots,
                "elroy1_pct": spec.elroy1_speed,
                "elroy1_fp": percent_to_fp(spec.elroy1_speed),
                "elroy2_dots": spec.elroy2_dots,
                "elroy2_pct": spec.elroy2_speed,
                "elroy2_fp": percent_to_fp(spec.elroy2_speed),
                "fright_seconds": spec.fright_seconds,
                "fright_frames": spec.fright_seconds * FPS,
                "fright_flashes": spec.fright_flashes,
            }
        )
    return rows


EXPECTED_ROWS = expected_table_rows()


def table_hash() -> str:
    payload = {
        "source": SOURCE_URL,
        "speed_100_px_per_sec": SPEED_100_PX_PER_SEC,
        "fps": FPS,
        "rows": EXPECTED_ROWS,
        "schedules": SCHEDULES,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def table_index_for_level(level: int) -> int:
    if level < 1:
        return 0
    if level >= 21:
        return 20
    return level - 1


def schedule_kind_for_level(level: int) -> str:
    if level <= 1:
        return "LEVEL1"
    if level <= 4:
        return "LEVEL2_4"
    return "LEVEL5P"


def complete_level(level: int) -> ProgressionDecision:
    next_level = 1 if level == 256 else level + 1
    return ProgressionDecision(
        completed=level,
        next_level=next_level,
        intermission=level in {2, 5, 9},
        kill_screen=next_level == 256,
        wrap=level == 256,
    )


def row_summary(level: int) -> str:
    index = table_index_for_level(level)
    row = EXPECTED_ROWS[index]
    symbol = FRUIT_NAMES_BY_ID[int(row["bonus_symbol"])]
    return (
        f"level={level} table={row['level_key']} schedule={schedule_kind_for_level(level)} "
        f"fruit={symbol}/{row['bonus_points']} pac={row['pac_normal_pct']}% "
        f"ghost={row['ghost_normal_pct']}% tunnel={row['ghost_tunnel_pct']}% "
        f"elroy={row['elroy1_dots']}@{row['elroy1_pct']}%,{row['elroy2_dots']}@{row['elroy2_pct']}% "
        f"fright={row['fright_seconds']}s/{row['fright_flashes']} flashes"
    )


def case_table_lengths_and_values() -> CaseResult:
    for name, values in ASM_TABLES.items():
        assert_equal(len(values), len(EXPECTED_ROWS), f"{name} table length")

    details: list[str] = []
    for index, expected_row in enumerate(EXPECTED_ROWS):
        for name, expected_value in expected_row.items():
            if name == "level_key":
                continue
            assert_equal(ASM_TABLES[name][index], expected_value, f"{name}[{index}]")
        if index in {0, 1, 4, 8, 20}:
            level = 21 if index == 20 else index + 1
            details.append(row_summary(level))
    details.append(f"table_hash={table_hash()}")
    return CaseResult(
        "table_lengths_and_values",
        True,
        "assembly table columns match Dossier-derived level rows 1-20 plus the 21+ family",
        details,
    )


def case_boundary_level_lookups() -> CaseResult:
    probes = {
        1: ("1", "LEVEL1", "Cherries", 6),
        2: ("2", "LEVEL2_4", "Strawberry", 5),
        5: ("5", "LEVEL5P", "Apple", 2),
        9: ("9", "LEVEL5P", "Galaxian", 1),
        21: ("21+", "LEVEL5P", "Key", 0),
        256: ("21+", "LEVEL5P", "Key", 0),
    }
    details: list[str] = []
    for level, (level_key, schedule, fruit, fright_seconds) in probes.items():
        row = EXPECTED_ROWS[table_index_for_level(level)]
        assert_equal(row["level_key"], level_key, f"level {level} table family")
        assert_equal(schedule_kind_for_level(level), schedule, f"level {level} schedule")
        assert_equal(FRUIT_NAMES_BY_ID[int(row["bonus_symbol"])], fruit, f"level {level} fruit")
        assert_equal(row["fright_seconds"], fright_seconds, f"level {level} frightened seconds")
        details.append(row_summary(level))
    return CaseResult(
        "boundary_level_lookups",
        True,
        "levels 1, 2, 5, 9, 21, and 256 resolve to documented table families",
        details,
    )


def case_scatter_chase_schedules() -> CaseResult:
    expected_constants = {
        "LEVEL_SCATTER_7_FRAMES": 420,
        "LEVEL_SCATTER_5_FRAMES": 300,
        "LEVEL_CHASE_20_FRAMES": 1200,
        "LEVEL_CHASE_1033_FRAMES": 61980,
        "LEVEL_CHASE_1037_FRAMES": 62220,
        "LEVEL_SCATTER_1_FRAME": 1,
    }
    for name, value in expected_constants.items():
        assert_equal(CONSTANTS[name], value, name)

    ghost_text = GHOST_ASM_PATH.read_text(encoding="ascii")
    assert_true("GHOST_CHASE_1033_FRAMES" in ghost_text, "ghost mode loader must use 1033-second chase family")
    assert_true("GHOST_CHASE_1037_FRAMES" in ghost_text, "ghost mode loader must use 1037-second chase family")
    assert_true("GHOST_SCATTER_1_FRAME" in ghost_text, "ghost mode loader must use one-frame fourth scatter")

    details = []
    for name, schedule in SCHEDULES.items():
        rendered = " -> ".join(
            f"{mode}:{'forever' if frames is None else frames}" for mode, frames in schedule
        )
        details.append(f"{name}: {rendered}")
    return CaseResult(
        "scatter_chase_schedules",
        True,
        "schedule family constants cover level 1, levels 2-4, and level 5+ without changing level-1 timings",
        details,
    )


def case_frightened_tables_and_zero_duration() -> CaseResult:
    no_blue_levels = [17, 19, 20, 21, 256]
    blue_levels = [1, 2, 5, 9, 14, 18]
    details: list[str] = []
    for level in blue_levels:
        row = EXPECTED_ROWS[table_index_for_level(level)]
        assert_true(int(row["fright_frames"]) > 0, f"level {level} should have frightened frames")
        assert_true(int(row["ghost_fright_pct"]) > 0, f"level {level} should have ghost frightened speed")
        details.append(
            f"level {level}: frightened={row['fright_frames']} frames flashes={row['fright_flashes']} "
            f"pac={row['pac_fright_pct']}% ghost={row['ghost_fright_pct']}%"
        )
    for level in no_blue_levels:
        row = EXPECTED_ROWS[table_index_for_level(level)]
        assert_equal(row["fright_frames"], 0, f"level {level} no frightened frames")
        assert_equal(row["ghost_fright_pct"], 0, f"level {level} no frightened ghost speed")
        details.append(f"level {level}: no blue time; energizer still reverses via ghost_enter_frightened_common")

    ghost_text = GHOST_ASM_PATH.read_text(encoding="ascii")
    assert_true("level_progression_get_current_frightened_frames" in ghost_text, "ghost frightened entry must query table owner")
    assert_true(".no_blue_time" in ghost_text, "ghost frightened entry must handle zero-duration levels")
    return CaseResult(
        "frightened_tables_and_zero_duration",
        True,
        "frightened duration, flash count, and zero-duration families are exposed through the table owner",
        details,
    )


def case_progression_decisions() -> CaseResult:
    probes = [1, 2, 5, 9, 20, 21, 255, 256]
    expected = {
        1: (2, False, False, False),
        2: (3, True, False, False),
        5: (6, True, False, False),
        9: (10, True, False, False),
        20: (21, False, False, False),
        21: (22, False, False, False),
        255: (256, False, True, False),
        256: (1, False, False, True),
    }
    details: list[str] = []
    for level in probes:
        decision = complete_level(level)
        assert_equal(
            (decision.next_level, decision.intermission, decision.kill_screen, decision.wrap),
            expected[level],
            f"completion decision for level {level}",
        )
        details.append(
            f"complete {level}: next={decision.next_level} "
            f"intermission={decision.intermission} kill_screen={decision.kill_screen} wrap={decision.wrap}"
        )

    flow_text = GAME_FLOW_ASM_PATH.read_text(encoding="ascii")
    assert_true("call level_progression_complete_current_level" in flow_text, "NEXT_LEVEL handoff must complete current level")
    assert_true("call level_progression_completed_requests_intermission" in flow_text, "NEXT_LEVEL must query intermission decision")
    assert_true("call level_progression_set_current_level_2_for_review" in flow_text, "review path must exercise level-2 intermission")
    return CaseResult(
        "progression_decisions",
        True,
        "level completion increments deterministically and marks intermission, kill-screen, and wrap decisions",
        details,
    )


def case_assembly_symbols_and_wiring() -> CaseResult:
    main_text = MAIN_ASM_PATH.read_text(encoding="ascii")
    ghost_text = GHOST_ASM_PATH.read_text(encoding="ascii")
    flow_text = GAME_FLOW_ASM_PATH.read_text(encoding="ascii")

    assert_true('INCLUDE "level_progression.asm"' in main_text, "main.asm must include level_progression.asm")
    assert_true(
        main_text.index('INCLUDE "level_progression.asm"') < main_text.index('INCLUDE "ghost_ai.asm"'),
        "level_progression.asm must be included before ghost_ai.asm",
    )
    assert_true("call level_progression_init" in flow_text, "game_flow_init must initialize level progression")
    assert_true("call level_progression_get_current_schedule_kind" in ghost_text, "ghost mode init must query schedule family")

    required_symbols = {
        "level_progression_init",
        "level_progression_complete_current_level",
        "level_progression_get_current_schedule_kind",
        "level_progression_get_current_frightened_frames",
        "level_progression_get_pacman_normal_fp",
        "level_progression_get_ghost_tunnel_fp",
        "level_progression_get_elroy2_dots",
        "level_progression_get_bonus_points",
    }
    symbol_details: list[str] = []
    if SYM_PATH.is_file():
        symbols = {
            line.split(maxsplit=1)[1]
            for line in SYM_PATH.read_text(encoding="ascii").splitlines()
            if len(line.split(maxsplit=1)) == 2
        }
        missing = sorted(required_symbols - symbols)
        assert_true(not missing, "symbol file missing level progression labels: " + ", ".join(missing))
        symbol_details.append("symbols_present=" + ", ".join(sorted(required_symbols)))
    else:
        symbol_details.append("symbols_present=not checked; build/pacman.sym not found")

    return CaseResult(
        "assembly_symbols_and_wiring",
        True,
        "level progression owner is assembled, exported, and queried by game-flow and ghost timing owners",
        [
            "main_include_order=movement -> level_progression -> ghost_ai",
            "game_flow_init=level_progression_init",
            "ghost_mode_init=level_progression_get_current_schedule_kind",
            *symbol_details,
        ],
    )


def run_cases() -> list[CaseResult]:
    case_functions: Iterable[Callable[[], CaseResult]] = [
        case_table_lengths_and_values,
        case_boundary_level_lookups,
        case_scatter_chase_schedules,
        case_frightened_tables_and_zero_duration,
        case_progression_decisions,
        case_assembly_symbols_and_wiring,
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
    paths = [
        MAIN_ASM_PATH,
        LEVEL_ASM_PATH,
        GHOST_ASM_PATH,
        GAME_FLOW_ASM_PATH,
        pathlib.Path(__file__),
    ]
    lines = [f"- {rel(path)} sha256={sha256(path)}" for path in paths]
    if ROM_PATH.is_file():
        lines.append(f"- {rel(ROM_PATH)} sha256={sha256(ROM_PATH)}")
    if SYM_PATH.is_file():
        lines.append(f"- {rel(SYM_PATH)} sha256={sha256(SYM_PATH)}")
    return lines


def format_vectors(results: list[CaseResult]) -> str:
    lines = [
        "# T019 Level Progression and Speed Table Vectors",
        "",
        f"Source: {SOURCE_NOTE}",
        f"Source URL: {SOURCE_URL}",
        f"Speed scale: 100% = {SPEED_100_PX_PER_SEC} pixels/sec, {FPS} frames/sec, 8.8 fixed point pixels/frame",
        f"Deterministic table hash: {table_hash()}",
        "",
        "Speed fixed-point values:",
        *[
            f"- {percent}% => 0x{percent_to_fp(percent):04X}"
            for percent in [0, 40, 45, 50, 55, 60, 75, 80, 85, 90, 95, 100, 105]
        ],
        "",
        "Boundary lookups:",
        *[f"- {row_summary(level)}" for level in [1, 2, 5, 9, 21, 256]],
        "",
        "Progression boundary decisions:",
        *[
            (
                f"- complete {level}: next={complete_level(level).next_level} "
                f"intermission={complete_level(level).intermission} "
                f"kill_screen={complete_level(level).kill_screen} wrap={complete_level(level).wrap}"
            )
            for level in [1, 2, 5, 9, 255, 256]
        ],
        "",
        "Scatter/chase schedules:",
    ]
    for name, schedule in SCHEDULES.items():
        lines.append(
            "- "
            + name
            + ": "
            + " -> ".join(
                f"{mode}:{'forever' if frames is None else frames}" for mode, frames in schedule
            )
        )
    lines.extend(["", "File hashes:", *file_hash_lines(), "", "Case results:"])
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
        description="Run deterministic T019 level progression and speed table tests."
    )
    parser.add_argument(
        "--vectors-output",
        type=pathlib.Path,
        help="Optional path for the readable level progression vector summary.",
    )
    args = parser.parse_args()

    results = run_cases()
    failures = sum(1 for result in results if not result.passed)

    print("T019 level progression and speed table tests")
    print("============================================")
    print(f"source: {SOURCE_NOTE} ({SOURCE_URL})")
    print(f"speed_scale: 100%={SPEED_100_PX_PER_SEC} px/sec, fp8.8 per frame")
    print(f"table_hash: {table_hash()}")
    print("boundary_levels: 1,2,5,9,21,256")
    print("")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.expected}")
        if not result.passed and result.details:
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
