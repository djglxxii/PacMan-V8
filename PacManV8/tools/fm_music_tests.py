#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIO_ASM_PATH = REPO_ROOT / "src" / "audio.asm"
MAIN_ASM_PATH = REPO_ROOT / "src" / "main.asm"

SIM_FRAMES = 300
YM_REST = 0xFF
YM_TL_MUTE = 0x7F
YM_KEY_ALL_OPERATORS = 0x78
YM_REG_KEY_ON = 0x08
YM_REG_KEY_CODE_BASE = 0x28
YM_REG_KEY_FRACTION_BASE = 0x30
YM_REG_OPERATOR_TL_BASE = 0x60

FM_TABLES = {
    "intro": "audio_fm_intro_rows",
    "intermission": "audio_fm_intermission_rows",
    "death": "audio_fm_death_rows",
}

REVIEW_SCHEDULE = [
    (144, "intro"),
    (196, "intermission"),
    (240, "death"),
]

NOTE_NAMES = {
    0x0: "C",
    0x1: "C#",
    0x2: "D",
    0x3: "D#",
    0x4: "E",
    0x5: "F",
    0x6: "F#",
    0x7: "G",
    0x8: "G#",
    0x9: "A",
    0xA: "A#",
    0xB: "B",
}

LABEL_PATTERN = re.compile(r"^([A-Za-z_.$][A-Za-z0-9_.$]*):")
EQU_PATTERN = re.compile(r"^([A-Z0-9_]+)\s+EQU\s+(.+?)\s*(?:;.*)?$")


class FmMusicError(AssertionError):
    pass


@dataclasses.dataclass(frozen=True)
class FmCell:
    key: int
    level: int

    @property
    def active(self) -> bool:
        return self.key != YM_REST

    @property
    def note_name(self) -> str:
        if not self.active:
            return "rest"
        octave = self.key >> 4
        note = NOTE_NAMES.get(self.key & 0x0F, f"n{self.key & 0x0F:X}")
        return f"{note}{octave}"


@dataclasses.dataclass(frozen=True)
class FmRow:
    duration: int
    channels: tuple[FmCell, FmCell, FmCell, FmCell]


@dataclasses.dataclass(frozen=True)
class Write:
    frame: int | None
    channel: str
    cue: str
    register: int
    value: int

    def line(self) -> str:
        frame = "init" if self.frame is None else f"{self.frame:03d}"
        return (
            f"{frame} {self.channel:<4} {self.cue:<14} "
            f"R0x{self.register:02X}=0x{self.value:02X}"
        )


@dataclasses.dataclass
class MusicState:
    cue: str | None = None
    rows: list[FmRow] | None = None
    index: int = 0
    remaining: int = 0


class Checks:
    def __init__(self) -> None:
        self.total = 0
        self.failures: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        self.total += 1
        if not condition:
            self.failures.append(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: pathlib.Path) -> pathlib.Path:
    return path.resolve().relative_to(REPO_ROOT)


def parse_equ_values(source: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for raw_line in source.splitlines():
        line = raw_line.strip()
        match = EQU_PATTERN.match(line)
        if match is None:
            continue
        name, expression = match.groups()
        expression = expression.split(";", 1)[0].strip()
        if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+", expression):
            values[name] = int(expression, 0)
    return values


def parse_db_value(token: str, equ_values: dict[str, int]) -> int:
    token = token.strip()
    if token in equ_values:
        return equ_values[token]
    return int(token, 0)


def parse_db_tables(source: str, labels: set[str], equ_values: dict[str, int]) -> dict[str, list[int]]:
    tables: dict[str, list[int]] = {label: [] for label in labels}
    current: str | None = None

    for raw_line in source.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue

        label_match = LABEL_PATTERN.match(line)
        if label_match is not None:
            label = label_match.group(1)
            current = label if label in labels else None
            continue

        if current is None or not line.lower().startswith("db "):
            continue

        for token in line[3:].split(","):
            if token.strip():
                tables[current].append(parse_db_value(token, equ_values))

    return tables


def decode_init_table(values: list[int]) -> list[tuple[int, int]]:
    if not values or values[-1] != YM_REST:
        raise FmMusicError("audio_fm_init_table must end with 0xFF")

    body = values[:-1]
    if len(body) % 2 != 0:
        raise FmMusicError("audio_fm_init_table must contain register/value pairs")

    pairs = [(body[index], body[index + 1]) for index in range(0, len(body), 2)]
    for register, value in pairs:
        if not 0 <= register <= 0xFE:
            raise FmMusicError(f"YM init register out of range: 0x{register:02X}")
        if not 0 <= value <= 0xFF:
            raise FmMusicError(f"YM init value out of range: 0x{value:02X}")
    return pairs


def decode_rows(label: str, values: list[int]) -> list[FmRow]:
    if not values:
        raise FmMusicError(f"{label} has no data")

    rows: list[FmRow] = []
    index = 0
    while index < len(values):
        duration = values[index]
        if duration == 0:
            if index != len(values) - 1:
                raise FmMusicError(f"{label} has data after terminator")
            return rows
        if index + 8 >= len(values):
            raise FmMusicError(f"{label} has incomplete row at byte {index}")

        cells = []
        for channel in range(4):
            key = values[index + 1 + channel * 2]
            level = values[index + 2 + channel * 2]
            if key != YM_REST and not 0 <= key <= 0x7F:
                raise FmMusicError(f"{label} has invalid key code 0x{key:02X}")
            if not 0 <= level <= 0x7F:
                raise FmMusicError(f"{label} has invalid total level 0x{level:02X}")
            if key == YM_REST and level != YM_TL_MUTE:
                raise FmMusicError(f"{label} rest on channel {channel} must use mute TL")
            cells.append(FmCell(key=key, level=level))

        if not 1 <= duration <= 24:
            raise FmMusicError(f"{label} duration out of review range: {duration}")
        rows.append(FmRow(duration=duration, channels=tuple(cells)))  # type: ignore[arg-type]
        index += 9

    raise FmMusicError(f"{label} is missing a zero terminator")


def cue_duration(rows: list[FmRow]) -> int:
    return sum(row.duration for row in rows)


def active_channels(row: FmRow) -> int:
    return sum(cell.active for cell in row.channels)


def channel_keys(rows: list[FmRow], channel: int) -> list[int]:
    return [row.channels[channel].key for row in rows if row.channels[channel].active]


def strictly_decreasing(values: list[int]) -> bool:
    return all(left > right for left, right in zip(values, values[1:]))


def simulate(init_pairs: list[tuple[int, int]], tables: dict[str, list[FmRow]]) -> list[Write]:
    writes = [Write(None, "init", "fm_init", register, value) for register, value in init_pairs]
    state = MusicState()

    def write_level(frame: int, channel: int, cue: str, level: int) -> None:
        for op in range(4):
            writes.append(
                Write(frame, f"ch{channel}", cue, YM_REG_OPERATOR_TL_BASE + channel + op * 8, level)
            )

    def mute_channel(frame: int, channel: int, cue: str) -> None:
        writes.append(Write(frame, f"ch{channel}", cue, YM_REG_KEY_ON, channel))
        write_level(frame, channel, cue, YM_TL_MUTE)

    def apply_cell(frame: int, channel: int, cue: str, cell: FmCell) -> None:
        if not cell.active:
            mute_channel(frame, channel, cue)
            return
        writes.append(Write(frame, f"ch{channel}", cue, YM_REG_KEY_ON, channel))
        writes.append(Write(frame, f"ch{channel}", cue, YM_REG_KEY_CODE_BASE + channel, cell.key))
        writes.append(Write(frame, f"ch{channel}", cue, YM_REG_KEY_FRACTION_BASE + channel, 0))
        write_level(frame, channel, cue, cell.level)
        writes.append(Write(frame, f"ch{channel}", cue, YM_REG_KEY_ON, YM_KEY_ALL_OPERATORS | channel))

    def trigger(cue: str) -> None:
        nonlocal state
        state = MusicState(cue=cue, rows=tables[cue])

    def update_music(frame: int) -> None:
        nonlocal state
        if state.cue is None or state.rows is None:
            return
        if state.remaining > 0:
            state.remaining -= 1
            return
        if state.index >= len(state.rows):
            cue = state.cue
            for channel in range(4):
                mute_channel(frame, channel, cue)
            state = MusicState()
            return

        row = state.rows[state.index]
        for channel, cell in enumerate(row.channels):
            apply_cell(frame, channel, state.cue, cell)
        state.index += 1
        state.remaining = row.duration - 1

    schedule_by_frame = {frame: cue for frame, cue in REVIEW_SCHEDULE}
    for frame in range(SIM_FRAMES):
        cue = schedule_by_frame.get(frame)
        if cue is not None:
            trigger(cue)
        update_music(frame)

    return writes


def trace_hash(writes: list[Write]) -> str:
    text = "\n".join(write.line() for write in writes) + "\n"
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def write_vectors(
    path: pathlib.Path,
    init_pairs: list[tuple[int, int]],
    tables: dict[str, list[FmRow]],
    writes: list[Write],
    checks: Checks,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "T017 YM2151 FM music vectors",
        "",
        "Hardware surface:",
        "- YM2151 address/status port: 0x40",
        "- YM2151 register data port: 0x41",
        "- Busy polling: status bit 7 before address and data writes",
        "- Sequencer cadence: VBlank frame update, no YM2151 timer IRQ dependency",
        "",
        "Initialization summary:",
        f"- register/value pairs: {len(init_pairs)}",
        "- timers disabled through R0x14=0x00",
        "- noise disabled through R0x0F=0x00",
        "- channels 0-7 receive key-off writes",
        "- every operator total-level register R0x60-R0x7F is initialized to 0x7F",
        "",
        "Review trigger schedule:",
    ]
    lines.extend(f"- frame {frame:03d}: {cue}" for frame, cue in REVIEW_SCHEDULE)

    lines.extend(["", "Cue definitions:"])
    for cue, rows in tables.items():
        lines.append(f"- {cue}: {len(rows)} rows, {cue_duration(rows)} frames")
        for index, row in enumerate(rows):
            cells = ", ".join(
                f"ch{channel}={cell.note_name}/TL0x{cell.level:02X}"
                for channel, cell in enumerate(row.channels)
            )
            lines.append(f"  row {index:02d}: duration={row.duration:02d}, {cells}")

    lines.extend(
        [
            "",
            "Deterministic register trace:",
            f"- writes: {len(writes)}",
            f"- trace SHA-256: {trace_hash(writes)}",
            f"- validation: {checks.total - len(checks.failures)}/{checks.total} passed",
        ]
    )
    lines.extend(write.line() for write in writes)
    lines.append("")
    path.write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic T017 YM2151 FM music.")
    parser.add_argument("--vectors-output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    checks = Checks()
    source = AUDIO_ASM_PATH.read_text(encoding="ascii")
    main_source = MAIN_ASM_PATH.read_text(encoding="ascii")
    equ_values = parse_equ_values(source)

    checks.require('INCLUDE "audio.asm"' in main_source, "main.asm must include audio.asm")
    checks.require("call audio_init" in main_source, "reset path must call audio_init")
    checks.require("call audio_update_frame" in main_source, "IM1 handler must call audio_update_frame")
    checks.require("YM_ADDR_PORT                EQU 0x40" in source, "YM address/status port must be 0x40")
    checks.require("YM_DATA_PORT                EQU 0x41" in source, "YM data port must be 0x41")
    checks.require("in a, (YM_ADDR_PORT)" in source, "YM writes must poll the status port")
    checks.require("and 0x80" in source, "YM writes must test busy bit 7")
    checks.require("jp audio_fm_init" in source, "audio_init must finish with FM init")
    checks.require("call audio_update_music" in source, "audio_update_frame must update FM music")
    checks.require("PSG_MIXER_TONE_AB           EQU 0x3C" in source, "T016 PSG mixer constant must remain 0x3C")

    raw_tables = parse_db_tables(
        source,
        {"audio_fm_init_table", *FM_TABLES.values()},
        equ_values,
    )

    init_pairs: list[tuple[int, int]] = []
    tables: dict[str, list[FmRow]] = {}
    try:
        init_pairs = decode_init_table(raw_tables["audio_fm_init_table"])
        for cue, label in FM_TABLES.items():
            tables[cue] = decode_rows(label, raw_tables[label])
    except FmMusicError as error:
        checks.require(False, str(error))

    if init_pairs and tables:
        init_map = {(register, value) for register, value in init_pairs}
        init_registers = {register for register, _ in init_pairs}
        checks.require((0x14, 0x00) in init_map, "YM timer control must be cleared")
        checks.require((0x0F, 0x00) in init_map, "YM noise must be disabled")
        checks.require(all((0x08, channel) in init_map for channel in range(8)), "FM init must key off channels 0-7")
        checks.require(
            all((register, YM_TL_MUTE) in init_map for register in range(0x60, 0x80)),
            "FM init must mute every operator total-level register",
        )
        checks.require(
            all((0x20 + channel, 0xC7) in init_map for channel in range(8)),
            "FM init must set every channel to both-speaker additive output",
        )
        checks.require(all(0x80 + channel in init_registers for channel in range(4)), "FM init must set attack rates")
        checks.require(REVIEW_SCHEDULE == [(144, "intro"), (196, "intermission"), (240, "death")], "FM schedule must match T017 review frames")
        checks.require(cue_duration(tables["intro"]) == 48, "intro cue must last 48 frames")
        checks.require(cue_duration(tables["intermission"]) == 40, "intermission cue must last 40 frames")
        checks.require(cue_duration(tables["death"]) == 32, "death cue must last 32 frames")
        checks.require(max(active_channels(row) for row in tables["intro"]) == 3, "intro must use 2-3 FM channels")
        checks.require(max(active_channels(row) for row in tables["intermission"]) == 4, "intermission must use 4 FM channels")
        checks.require(max(active_channels(row) for row in tables["death"]) == 3, "death must use 2-3 FM channels")
        checks.require(strictly_decreasing(channel_keys(tables["death"], 0)), "death lead must descend")
        checks.require(
            all(left.level <= right.level for left, right in zip([row.channels[0] for row in tables["death"]], [row.channels[0] for row in tables["death"]][1:])),
            "death lead must decay by increasing or equal TL values",
        )

    writes: list[Write] = []
    if init_pairs and tables:
        writes = simulate(init_pairs, tables)
        trace_registers = {(write.register, write.value) for write in writes}
        checks.require((0x08, 0x78) in trace_registers, "trace must key on FM channel 0")
        checks.require((0x08, 0x7B) in trace_registers, "trace must key on FM channel 3")
        checks.require(any(write.channel == "ch3" and write.value == YM_TL_MUTE for write in writes), "trace must mute/rest channel 3")
        checks.require(len(writes) > len(init_pairs), "trace must contain runtime music writes")
        write_vectors(args.vectors_output, init_pairs, tables, writes, checks)

    if checks.failures:
        print("fm_music_tests: FAILED")
        for failure in checks.failures:
            print(f"- {failure}")
        return 1

    print(f"fm_music_tests: {checks.total}/{checks.total} passed")
    print(f"src/audio.asm SHA-256: {sha256(AUDIO_ASM_PATH)}")
    print(f"Register trace SHA-256: {trace_hash(writes)}")
    print(f"Frames simulated: {SIM_FRAMES}")
    print(f"Register writes: {len(writes)}")
    print(f"Vectors: {rel(args.vectors_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
