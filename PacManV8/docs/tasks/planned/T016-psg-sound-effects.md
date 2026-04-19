# T016 — PSG Sound Effects

| Field | Value |
|---|---|
| ID | T016 |
| State | planned |
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

- [ ] T011 is completed and accepted.
- [ ] Confirm no other task is active before activation.
- [ ] Review `docs/PLAN.md` Phase 5 audio sections and the audio-fidelity risk
  note before implementation.
- [ ] Consult `/home/djglxxii/src/Vanguard8/docs/spec/` for AY-3-8910 ports,
  register layout, mixer semantics, and interrupt wiring.
- [ ] Consult `/home/djglxxii/src/Vanguard8/docs/emulator/` for headless audio
  hash or audio dump support.
- [ ] Review `docs/tasks/completed/T011-collision-pellets-and-dot-stall.md`
  so pellet/dot-stall hooks can later drive sound without changing those
  gameplay rules in this task.
- [ ] Review current `src/main.asm` frame loop and interrupt handler before
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
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 180 --expect-audio-hash <filled-after-implementation>
python3 tools/psg_sound_tests.py --vectors-output tests/evidence/T016-psg-sound-effects/psg_sound_vectors.txt > tests/evidence/T016-psg-sound-effects/psg_sound_tests.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-19 | Created, state: planned. |

## Blocker (only if state = blocked)

*(None.)*
