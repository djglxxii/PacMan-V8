# T017 — FM Music

| Field | Value |
|---|---|
| ID | T017 |
| State | planned |
| Phase | Phase 5 — Audio |
| Depends on | T016 |
| Plan reference | `docs/PLAN.md` Phase 5 — Audio; Music (YM2151 FM) |

## Goal

Add the first YM2151 FM music slice: deterministic, recognizable Pac-Man
intro, intermission, and death music cues that coexist with the T016 PSG sound
effects without changing gameplay or game-flow rules.

## Scope

- In scope:
  - Consult the Vanguard 8 hardware spec for YM2151 ports, busy/status
    behavior, timer IRQ wiring, stereo/pan registers, and register timing.
  - Consult the Vanguard 8 emulator docs for headless audio hash behavior and
    any YM2151 status/busy limitations.
  - Extend the audio module under `src/` with a small YM2151 initialization and
    frame-driven music sequencer path.
  - Re-author short FM approximations for the Phase 5 music pieces:
    intro jingle, intermission phrase, and death sequence.
  - Keep T016 PSG sound-effect behavior deterministic and compatible with the
    new FM path.
  - Provide deterministic review/test triggers that exercise each FM cue
    without changing gameplay scoring, collision, movement, AI, rendering,
    level progression, attract mode, or game-flow rules.
  - Produce human-verifiable evidence under
    `tests/evidence/T017-fm-music/`.

- Out of scope:
  - MSM5205 ADPCM samples or cartridge-fed sample playback.
  - Replacing T016 PSG sound effects or changing their accepted review
    schedule unless the task file records an approved scope change.
  - New gameplay scoring, extra-life thresholds, fruit award timing, level
    progression, attract mode, title/menu flow, or intermission cutscene flow.
  - Changing movement, ghost AI, frightened timing, collision, pellet
    consumption, ghost-house rules, sprite rendering, HUD rendering, or
    coordinate transform behavior.
  - Exact arcade Namco WSG waveform reproduction or use of restricted program
    ROM logic. Any reference listening should come from public documentation or
    authored approximation, not disassembly.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T016 is completed and accepted.
- [ ] Confirm no other task is active before activation.
- [ ] Review `docs/PLAN.md` Phase 5 audio sections and the audio-fidelity risk
  note before implementation.
- [ ] Consult `/home/djglxxii/src/Vanguard8/docs/spec/03-audio.md` for
  YM2151 port, register, busy/status, and timer behavior.
- [ ] Consult `/home/djglxxii/src/Vanguard8/docs/spec/04-io.md` for INT0
  source sharing between VDP-A and YM2151.
- [ ] Consult `/home/djglxxii/src/Vanguard8/docs/emulator/05-audio.md` and
  `/home/djglxxii/src/Vanguard8/docs/emulator/02-emulation-loop.md` for
  headless audio hashes and YM2151 IRQ/status handling.
- [ ] Review `docs/tasks/completed/T016-psg-sound-effects.md` so the FM music
  path preserves accepted PSG initialization, register trace determinism, and
  audio-hash evidence expectations.
- [ ] Review `docs/field-manual/vanguard8-build-directory-skew-and-timed-opcodes.md`
  and choose the working/canonical headless emulator binary before generating
  audio evidence.

## Implementation notes

The plan maps Phase 5 music to the YM2151:

- Intro jingle: 2-3 FM channels.
- Intermission: 3-4 FM channels.
- Death sequence: 2-3 FM channels with descending contour and decay.

Keep this slice deterministic. A review routine may trigger a scripted
sequence of FM cues after boot or through a small harness, as long as the
evidence records the exact frame schedule, YM2151 register writes, expected
busy/status handling, and a stable audio hash or register-trace fallback.

The YM2151 shares INT0 with VDP-A. This task should avoid depending on YM2151
timer IRQs unless the handler source-identification path is deliberately
implemented and tested. A VBlank-driven sequencer is acceptable for this first
music slice if it produces stable headless audio hashes.

Preserve the T016 PSG path unless an explicit scope change is approved. The
music sequencer should initialize or silence only the YM2151 state it owns and
should leave AY channel mute/effect behavior in the accepted T016 state.

Do not read or reverse-engineer restricted Pac-Man program ROMs. Do not extract
or replicate arcade sound PROM waveform data directly; the V8 audio is
re-authored.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T017-fm-music/fm_music_tests.txt` — stdout from a
  deterministic YM2151 register/music validation harness.
- `tests/evidence/T017-fm-music/fm_music_vectors.txt` — readable summary of FM
  instrument parameters, cue definitions, frame schedule, YM2151 register
  writes, hashes, and pass/fail results.
- `tests/evidence/T017-fm-music/fm_audio_summary.txt` — headless emulator
  audio hash summary, or a documented register-trace fallback if audio hashes
  are unavailable.

**Reviewer checklist** (human ticks these):

- [ ] Intro jingle, intermission phrase, and death sequence each have
  deterministic YM2151 register sequences.
- [ ] The review trigger schedule exercises every FM cue without changing
  gameplay scoring, collision, movement, AI, rendering, or game-flow rules.
- [ ] YM2151 initialization leaves unused FM channels in a known muted state.
- [ ] T016 PSG sound-effect initialization and deterministic behavior remain
  compatible with the FM path.
- [ ] Evidence records music parameters, frame schedule, hashes or register
  traces, and deterministic pass/fail results.
- [ ] MSM5205 ADPCM, level progression, attract mode, title/menu flow, and
  intermission cutscene behavior are not introduced.

**Rerun command:**

```bash
python3 tools/build.py
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames <filled-after-implementation> --hash-audio --expect-audio-hash <filled-after-implementation>
python3 tools/fm_music_tests.py --vectors-output tests/evidence/T017-fm-music/fm_music_vectors.txt > tests/evidence/T017-fm-music/fm_music_tests.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-19 | Created, state: planned. |

## Blocker (only if state = blocked)

*(None.)*
