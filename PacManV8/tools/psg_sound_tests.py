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

PSG_CLOCK_HZ = 1_789_772.5
SIM_FRAMES = 180

INIT_WRITES = [
    (0, 0x01),
    (1, 0x00),
    (2, 0x01),
    (3, 0x00),
    (4, 0x01),
    (5, 0x00),
    (6, 0x1F),
    (7, 0x3C),
    (8, 0x00),
    (9, 0x00),
    (10, 0x00),
    (11, 0x00),
    (12, 0x00),
    (13, 0x00),
]

EFFECT_TABLES = {
    "waka": ("A", "audio_waka_steps"),
    "pellet": ("A", "audio_pellet_steps"),
    "siren": ("B", "audio_siren_steps"),
    "ghost_eaten": ("A", "audio_ghost_eaten_steps"),
    "extra_life_a": ("A", "audio_extra_life_a_steps"),
    "extra_life_b": ("B", "audio_extra_life_b_steps"),
}

REVIEW_SCHEDULE = [
    (0, "siren"),
    (12, "pellet"),
    (36, "waka"),
    (72, "ghost_eaten"),
    (112, "extra_life"),
]

LABEL_PATTERN = re.compile(r"^([A-Za-z_.$][A-Za-z0-9_.$]*):")


class PsgSoundError(AssertionError):
    pass


@dataclasses.dataclass(frozen=True)
class Step:
    duration: int
    fine: int
    coarse: int
    volume: int

    @property
    def period(self) -> int:
        return (self.coarse << 8) | self.fine

    @property
    def frequency(self) -> float:
        return PSG_CLOCK_HZ / (16 * self.period)


@dataclasses.dataclass(frozen=True)
class Write:
    frame: int | None
    channel: str
    effect: str
    register: int
    value: int

    def line(self) -> str:
        frame = "init" if self.frame is None else f"{self.frame:03d}"
        return (
            f"{frame} {self.channel:<4} {self.effect:<12} "
            f"R{self.register:02d}=0x{self.value:02X}"
        )


@dataclasses.dataclass
class ChannelState:
    effect: str | None = None
    steps: list[Step] | None = None
    index: int = 0
    remaining: int = 0


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: pathlib.Path) -> pathlib.Path:
    return path.resolve().relative_to(REPO_ROOT)


def parse_db_value(token: str) -> int:
    token = token.strip()
    if token.lower().startswith("0x"):
        return int(token, 16)
    return int(token, 10)


def parse_effect_tables(source: str) -> dict[str, list[int]]:
    wanted = {label for _, label in EFFECT_TABLES.values()}
    tables: dict[str, list[int]] = {label: [] for label in wanted}
    current: str | None = None

    for raw_line in source.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue

        label_match = LABEL_PATTERN.match(line)
        if label_match is not None:
            label = label_match.group(1)
            current = label if label in wanted else None
            continue

        if current is None or not line.lower().startswith("db "):
            continue

        for token in line[3:].split(","):
            if token.strip():
                tables[current].append(parse_db_value(token))

    return tables


def decode_steps(label: str, values: list[int]) -> list[Step]:
    if not values:
        raise PsgSoundError(f"{label} has no data")

    steps: list[Step] = []
    index = 0
    while index < len(values):
        duration = values[index]
        if duration == 0:
            if index != len(values) - 1:
                raise PsgSoundError(f"{label} has data after terminator")
            return steps
        if index + 3 >= len(values):
            raise PsgSoundError(f"{label} has incomplete step at byte {index}")

        fine = values[index + 1]
        coarse = values[index + 2]
        volume = values[index + 3]
        step = Step(duration=duration, fine=fine, coarse=coarse, volume=volume)

        if not 1 <= step.period <= 4095:
            raise PsgSoundError(f"{label} period out of AY range: {step.period}")
        if not 1 <= duration <= 60:
            raise PsgSoundError(f"{label} duration out of review range: {duration}")
        if not 0 <= volume <= 15:
            raise PsgSoundError(f"{label} volume out of AY range: {volume}")
        if fine > 0xFF or coarse > 0x0F:
            raise PsgSoundError(f"{label} tone bytes exceed AY 12-bit layout")

        steps.append(step)
        index += 4

    raise PsgSoundError(f"{label} is missing a zero terminator")


def periods(steps: list[Step]) -> list[int]:
    return [step.period for step in steps]


def duration(steps: list[Step]) -> int:
    return sum(step.duration for step in steps)


def strictly_decreasing(values: list[int]) -> bool:
    return all(left > right for left, right in zip(values, values[1:]))


def strictly_increasing(values: list[int]) -> bool:
    return all(left < right for left, right in zip(values, values[1:]))


def simulate(tables: dict[str, list[Step]]) -> list[Write]:
    writes = [Write(None, "init", "psg_init", register, value) for register, value in INIT_WRITES]
    state = {"A": ChannelState(), "B": ChannelState()}

    def trigger(effect_name: str) -> None:
        if effect_name == "extra_life":
            state["A"] = ChannelState(effect_name, tables["extra_life_a"])
            state["B"] = ChannelState(effect_name, tables["extra_life_b"])
            return
        channel = EFFECT_TABLES[effect_name][0]
        state[channel] = ChannelState(effect_name, tables[effect_name])

    def update_channel(frame: int, channel: str) -> None:
        channel_state = state[channel]
        if channel_state.effect is None or channel_state.steps is None:
            return
        if channel_state.remaining > 0:
            channel_state.remaining -= 1
            return
        if channel_state.index >= len(channel_state.steps):
            volume_register = 8 if channel == "A" else 9
            writes.append(Write(frame, channel, channel_state.effect, volume_register, 0))
            state[channel] = ChannelState()
            return

        step = channel_state.steps[channel_state.index]
        fine_register, coarse_register, volume_register = (0, 1, 8)
        if channel == "B":
            fine_register, coarse_register, volume_register = (2, 3, 9)
        writes.append(Write(frame, channel, channel_state.effect, fine_register, step.fine))
        writes.append(Write(frame, channel, channel_state.effect, coarse_register, step.coarse))
        writes.append(Write(frame, channel, channel_state.effect, volume_register, step.volume))
        channel_state.index += 1
        channel_state.remaining = step.duration - 1

    schedule_by_frame = {frame: effect for frame, effect in REVIEW_SCHEDULE}
    for frame in range(SIM_FRAMES):
        effect = schedule_by_frame.get(frame)
        if effect is not None:
            trigger(effect)
        update_channel(frame, "A")
        update_channel(frame, "B")

    return writes


def trace_hash(writes: list[Write]) -> str:
    text = "\n".join(write.line() for write in writes) + "\n"
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def write_vectors(path: pathlib.Path, tables: dict[str, list[Step]], writes: list[Write]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "T016 PSG sound-effect vectors",
        "",
        "Hardware surface:",
        "- AY-3-8910 address latch: port 0x50",
        "- AY-3-8910 register data: port 0x51",
        "- AY clock: 1,789,772.5 Hz",
        "- Mixer value: 0x3C (tone A+B enabled; tone C and all noise disabled)",
        "",
        "Initialization writes:",
    ]
    lines.extend(f"- R{register:02d}=0x{value:02X}" for register, value in INIT_WRITES)
    lines.extend(["", "Review trigger schedule:"])
    lines.extend(f"- frame {frame:03d}: {effect}" for frame, effect in REVIEW_SCHEDULE)

    lines.extend(["", "Effect definitions:"])
    for effect_name, (channel, label) in EFFECT_TABLES.items():
        effect_steps = tables[effect_name]
        lines.append(
            f"- {effect_name}: channel {channel}, label {label}, "
            f"{len(effect_steps)} steps, {duration(effect_steps)} frames"
        )
        for index, step in enumerate(effect_steps):
            lines.append(
                f"  step {index:02d}: duration={step.duration:02d} "
                f"period=0x{step.period:03X} "
                f"frequency={step.frequency:.1f}Hz volume=0x{step.volume:X}"
            )

    lines.extend(
        [
            "",
            "Deterministic register trace:",
            f"- writes: {len(writes)}",
            f"- trace SHA-256: {trace_hash(writes)}",
        ]
    )
    lines.extend(write.line() for write in writes)
    lines.append("")
    path.write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic T016 PSG sound effects.")
    parser.add_argument("--vectors-output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    failures: list[str] = []
    source = AUDIO_ASM_PATH.read_text(encoding="ascii")
    main_source = MAIN_ASM_PATH.read_text(encoding="ascii")

    require('INCLUDE "audio.asm"' in main_source, "main.asm must include audio.asm", failures)
    require("call audio_init" in main_source, "reset path must call audio_init", failures)
    require("call audio_update_frame" in main_source, "IM1 handler must call audio_update_frame", failures)
    require("PSG_MIXER_TONE_AB           EQU 0x3C" in source, "PSG mixer constant must be 0x3C", failures)

    raw_tables = parse_effect_tables(source)
    tables: dict[str, list[Step]] = {}
    try:
        for effect_name, (_, label) in EFFECT_TABLES.items():
            tables[effect_name] = decode_steps(label, raw_tables[label])
    except PsgSoundError as error:
        failures.append(str(error))

    if not failures:
        require(periods(tables["waka"]) == [0x0F0, 0x0B4, 0x0F0, 0x0B4], "waka must alternate two pitches", failures)
        require(strictly_decreasing(periods(tables["pellet"])), "pellet effect must sweep upward in pitch", failures)
        require(len(set(periods(tables["siren"]))) >= 4, "siren must modulate across at least four periods", failures)
        require(duration(tables["siren"]) >= 90, "siren must last long enough for review hashing", failures)
        require(strictly_increasing(periods(tables["ghost_eaten"])), "ghost-eaten effect must descend in pitch", failures)
        require(strictly_decreasing(periods(tables["extra_life_a"])), "extra-life channel A must ascend", failures)
        require(strictly_decreasing(periods(tables["extra_life_b"])), "extra-life channel B must ascend", failures)
        require(duration(tables["extra_life_a"]) == duration(tables["extra_life_b"]), "extra-life channels must align", failures)

    writes: list[Write] = []
    if not failures:
        writes = simulate(tables)
        write_vectors(args.vectors_output, tables, writes)
        written_registers = {(write.channel, write.register) for write in writes}
        require(("init", 10) in written_registers, "PSG init must write muted channel C volume", failures)
        require(("A", 8) in written_registers, "trace must include channel A volume writes", failures)
        require(("B", 9) in written_registers, "trace must include channel B volume writes", failures)
        schedule_effects = {effect for _, effect in REVIEW_SCHEDULE}
        require({"siren", "pellet", "waka", "ghost_eaten", "extra_life"} <= schedule_effects, "schedule must cover every T016 effect", failures)

    if failures:
        print("psg_sound_tests: FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("psg_sound_tests: 16/16 passed")
    print(f"src/audio.asm SHA-256: {sha256(AUDIO_ASM_PATH)}")
    print(f"Register trace SHA-256: {trace_hash(writes)}")
    print(f"Frames simulated: {SIM_FRAMES}")
    print(f"Register writes: {len(writes)}")
    print(f"Vectors: {rel(args.vectors_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
