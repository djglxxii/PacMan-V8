# T016 — PSG Sound Effects

| Field | Value |
|---|---|
| ID | T016 |
| State | completed |
| Phase | Phase 5 — Audio |
| Depends on | T011 |
| Plan reference | `docs/PLAN.md` Phase 5 — Audio; Sound Effects (AY-3-8910 PSG) |

## Goal

Add the first runtime audio slice: a deterministic AY-3-8910 PSG sound-effects
engine and recognizable Pac-Man effect cues for pellet eating, waka-waka,
ghost siren, ghost eaten, and extra life.

## Scope

- In scope:
  - Consult the Vanguard 8 hardware spec for AY-3-8910 register ports,
    mixer/noise/tone behavior, interrupt timing, and any emulator audio hash
    support before implementation.
  - Add an audio module under `src/` that initializes the PSG and owns a small
    per-frame sound-effect update path.
  - Re-author PSG approximations for the Phase 5 sound effects: waka-waka,
    pellet eat, ghost siren, ghost eaten, and extra life.
  - Provide deterministic review/test triggers that exercise each effect
    without changing gameplay scoring, collision, or game-flow rules.
  - Keep the audio path compatible with the existing VBlank frame-update model
    and leave YM2151 music and MSM5205 ADPCM work to later tasks.
  - Produce human-verifiable evidence under
    `tests/evidence/T016-psg-sound-effects/`.

- Out of scope:
  - YM2151 intro/intermission/death music; T017 owns FM music.
  - MSM5205 ADPCM samples or cartridge-fed sample playback.
  - New gameplay scoring, extra-life thresholds, fruit award timing, or level
    progression behavior.
  - Changing movement, ghost AI, frightened timing, collision, pellet
    consumption rules, sprite rendering, HUD rendering, or coordinate
    transform behavior.
  - Exact arcade Namco WSG waveform reproduction or use of restricted sound
    PROM data beyond documented waveform context allowed by `AGENTS.md`.

## Scope changes

*(None.)*

## Pre-flight

- [x] T011 is completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Phase 5 audio sections and the audio-fidelity risk
  note before implementation.
- [x] Consult `/home/djglxxii/src/Vanguard8/docs/spec/` for AY-3-8910 ports,
  register layout, mixer semantics, and interrupt wiring.
- [x] Consult `/home/djglxxii/src/Vanguard8/docs/emulator/` for headless audio
  hash or audio dump support.
- [x] Review `docs/tasks/completed/T011-collision-pellets-and-dot-stall.md`
  so pellet/dot-stall hooks can later drive sound without changing those
  gameplay rules in this task.
- [x] Review current `src/main.asm` frame loop and interrupt handler before
  adding audio update calls.

## Implementation notes

The plan maps arcade sound effects to AY-3-8910 PSG channels:

- Waka-waka: channel A, alternating square-wave pitches.
- Pellet eat: channel A, short pitch sweep.
- Ghost siren: channel B, slow pitch modulation.
- Ghost eaten: channel A, fast descending sweep.
- Extra life: channels A+B, ascending arpeggio.

Keep this slice deterministic. A review routine may trigger a scripted sequence
of effects after boot or via a small harness, as long as the evidence records
the exact frame schedule, PSG register writes, and audio hash or comparable
emulator output. If the headless emulator cannot produce reliable audio hashes
or dumps from documented options, use a text-register trace as the acceptance
artifact and document the limitation in the task file.

Do not read or reverse-engineer the restricted Pac-Man program ROMs. If any
sound PROM inspection is needed, keep it documentation-only and do not convert
or replicate waveform data directly.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T016-psg-sound-effects/psg_sound_tests.txt` — stdout from a
  deterministic audio register/effect validation harness.
- `tests/evidence/T016-psg-sound-effects/psg_sound_vectors.txt` — readable
  summary of effect definitions, frame schedule, PSG register writes, hashes,
  and pass/fail results.
- `tests/evidence/T016-psg-sound-effects/psg_audio_summary.txt` — headless
  emulator audio hash/dump summary, or a documented register-trace fallback if
  audio hashes are unavailable.

**Reviewer checklist** (human ticks these):

- [ ] Waka-waka, pellet eat, ghost siren, ghost eaten, and extra-life effects
  each have deterministic PSG register sequences.
- [ ] The review trigger schedule exercises every effect without changing
  gameplay scoring, collision, movement, AI, rendering, or game-flow rules.
- [ ] PSG initialization leaves unused channels in a known muted state.
- [ ] Evidence records effect parameters, frame schedule, hashes or register
  traces, and deterministic pass/fail results.
- [ ] YM2151 music, MSM5205 ADPCM, level progression, attract mode, and
  intermission behavior are not introduced.

**Rerun command:**

```bash
python3 tools/build.py
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 180 --hash-audio --expect-audio-hash a8d5a5c921628a88b12a4b95e1294af3ddd79620bd940b0702300098af341483
python3 tools/psg_sound_tests.py --vectors-output tests/evidence/T016-psg-sound-effects/psg_sound_vectors.txt > tests/evidence/T016-psg-sound-effects/psg_sound_tests.txt
```

**Observed evidence values:**

- `psg_sound_tests.txt` SHA-256:
  `333331eb4087dbde29336dd736e308a4b683757ebe49c4fdbf2e5a5f4e7da7e0`
- `psg_sound_vectors.txt` SHA-256:
  `3f02e1e682c9682fc6a8cbb40de16bca9c2f69228a4473a56dad9c14ad4f32fb`
- `psg_audio_summary.txt` SHA-256:
  `70aa217e8e46f4a9ad659e07a16bb8bedd5ae80402b2696296e7bee7d8a40a21`
- PSG register/effect validation result: `16/16 passed`
- `src/audio.asm` SHA-256:
  `7f923ecea8ff6fc756b228e6d4aad8a5b3e5b8109288fef7954856cc1cd4a55b`
- Deterministic register trace SHA-256:
  `5b42f187966ed3e89d0ac19c1d06fb9bc28c732aea7cc62b71db6214bf26fbaf`
- Review trigger schedule:
  frame `0` ghost siren, frame `12` pellet eat, frame `36` waka-waka,
  frame `72` ghost eaten, frame `112` extra life.
- Headless audio verification:
  `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 180 --hash-audio --expect-audio-hash a8d5a5c921628a88b12a4b95e1294af3ddd79620bd940b0702300098af341483`
  passed with audio hash
  `a8d5a5c921628a88b12a4b95e1294af3ddd79620bd940b0702300098af341483`
  and event log digest `6306466758261423191`.
- Build verification:
  `python3 -m py_compile tools/psg_sound_tests.py` and
  `python3 tools/build.py` both passed.
- Emulator version note:
  `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` aborted on
  `Unsupported timed Z180 opcode 0xC5 at PC 0x39` in the widened VBlank
  handler, so evidence uses the repo-documented `cmake-build-debug` binary.
  Related stack opcodes in the same active handler that may need the same
  timed-path coverage are `0xD5` at `PC 0x003A`, `0xE5` at `PC 0x003B`,
  `0xE1` at `PC 0x0040`, `0xD1` at `PC 0x0041`, and `0xC1` at `PC 0x0042`.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-19 | Created, state: planned. |
| 2026-04-19 | Activated task after confirming no other task was active; starting pre-flight review. |
| 2026-04-19 | Implemented `src/audio.asm` with PSG initialization, channel A/B effect trigger routines, a VBlank-driven update path, and deterministic review triggers for siren, pellet, waka-waka, ghost-eaten, and extra-life cues. Wired `audio_init` and `audio_update_frame` into `src/main.asm`, added `tools/psg_sound_tests.py`, generated evidence under `tests/evidence/T016-psg-sound-effects/`, verified Python compilation, ROM assembly, deterministic register vectors, and a 180-frame headless audio hash. Updated `docs/field-manual/headless-runtime-dump-version-skew.md` with the current `build` binary opcode gap. Stopping for human review. |
| 2026-04-19 | Added `docs/field-manual/vanguard8-build-directory-skew-and-timed-opcodes.md` as a focused handoff for the separate Vanguard8 emulator session: explains the two CMake build directories, the confirmed `0xC5` timed opcode failure, likely adjacent stack opcodes, and the recommended emulator-side fix/verification path. |
| 2026-04-19 | Human accepted T016; moved task to completed and updated the task index. |

## Blocker (only if state = blocked)

*(None.)*
