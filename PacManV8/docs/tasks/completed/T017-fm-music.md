# T017 — FM Music

| Field | Value |
|---|---|
| ID | T017 |
| State | active |
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

- [x] T016 is completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Phase 5 audio sections and the audio-fidelity risk
  note before implementation.
- [x] Consult `/home/djglxxii/src/Vanguard8/docs/spec/03-audio.md` for
  YM2151 port, register, busy/status, and timer behavior.
- [x] Consult `/home/djglxxii/src/Vanguard8/docs/spec/04-io.md` for INT0
  source sharing between VDP-A and YM2151.
- [x] Consult `/home/djglxxii/src/Vanguard8/docs/emulator/05-audio.md` and
  `/home/djglxxii/src/Vanguard8/docs/emulator/02-emulation-loop.md` for
  headless audio hashes and YM2151 IRQ/status handling.
- [x] Review `docs/tasks/completed/T016-psg-sound-effects.md` so the FM music
  path preserves accepted PSG initialization, register trace determinism, and
  audio-hash evidence expectations.
- [x] Review `docs/field-manual/vanguard8-build-directory-skew-and-timed-opcodes.md`
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
- `tests/evidence/T017-fm-music/psg_compatibility_tests.txt` and
  `tests/evidence/T017-fm-music/psg_compatibility_vectors.txt` — T016 PSG
  compatibility rerun against the FM-enabled audio module.

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
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 300 --hash-audio --expect-audio-hash 0d634fb059d15b12c4a8faf2412fbe08b85d187a31b1f22278ce3662f3b44390
python3 tools/fm_music_tests.py --vectors-output tests/evidence/T017-fm-music/fm_music_vectors.txt > tests/evidence/T017-fm-music/fm_music_tests.txt
python3 tools/psg_sound_tests.py --vectors-output tests/evidence/T017-fm-music/psg_compatibility_vectors.txt > tests/evidence/T017-fm-music/psg_compatibility_tests.txt
```

**Observed evidence values:**

- `fm_music_tests.txt` SHA-256:
  `c297e2fe5d794b1a05e14c380feaf9feffcb0b46480cc53bf4754819c3cb9dec`
- `fm_music_vectors.txt` SHA-256:
  `6af702940d5e603c8a703fd9d256d1b834ea8c02b01b0fdc6e274b11eff8c7d8`
- `fm_audio_summary.txt` SHA-256:
  `203af4e324b2c37931e309f3d9dab8cc1d44f06ab1885a791aef36fb61911c55`
- `psg_compatibility_tests.txt` SHA-256:
  `28e5bf6642101c8d3d4521dcca4799c744b4e0828a7024859d2081201576e82c`
- `psg_compatibility_vectors.txt` SHA-256:
  `3f02e1e682c9682fc6a8cbb40de16bca9c2f69228a4473a56dad9c14ad4f32fb`
- `src/audio.asm` SHA-256:
  `55587dfa152087001240bb394f02a54c9a6ccd426ca2ad0ba5a3bde297acaee6`
- `tools/fm_music_tests.py` SHA-256:
  `f060b1d6c445721e68873a36b37ca19239a89a82f756cc1745a852fbcffbf2cc`
- FM register/music validation result: `29/29 passed`
- FM deterministic register trace SHA-256:
  `1c00bb874e1db7356288b22048409153a43338e52c01e53405bf11f21ec9a51f`
- PSG compatibility validation result: `16/16 passed`
- PSG deterministic register trace SHA-256 remains:
  `5b42f187966ed3e89d0ac19c1d06fb9bc28c732aea7cc62b71db6214bf26fbaf`
- Review trigger schedule:
  PSG frames `0`, `12`, `36`, `72`, `112`; FM intro frame `144`,
  FM intermission frame `196`, FM death frame `240`.
- Headless audio verification:
  `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 300 --hash-audio --expect-audio-hash 0d634fb059d15b12c4a8faf2412fbe08b85d187a31b1f22278ce3662f3b44390`
  passed with audio hash
  `0d634fb059d15b12c4a8faf2412fbe08b85d187a31b1f22278ce3662f3b44390`
  and event log digest `793085328687964239`.
- Build verification:
  `python3 -m py_compile tools/fm_music_tests.py tools/psg_sound_tests.py`
  and `python3 tools/build.py` both passed.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-19 | Created, state: planned. |
| 2026-04-19 | Activated task after confirming no other task was active; starting pre-flight review for YM2151 hardware behavior, emulator audio support, and T016 PSG compatibility. |
| 2026-04-19 | Implemented a YM2151 path in `src/audio.asm`: busy-polled register writes on ports `0x40/0x41`, table-driven FM initialization, VBlank-driven music row playback, deterministic review triggers for intro/intermission/death cues, and explicit mute/key-off handling for unused FM channels. Added `tools/fm_music_tests.py`, generated evidence under `tests/evidence/T017-fm-music/`, reran the T016 PSG harness for compatibility, verified ROM assembly, and verified a 300-frame headless audio hash. Stopping for human review. |
| 2026-04-19 | Added `docs/field-manual/vblank-driven-ym2151-review-sequencer.md` to capture the reusable INT0/YM2151 timer-avoidance and register-trace validation pattern from this task. |

## Blocker (only if state = blocked)

*(None.)*
