# T032 — Audio Cue Bindings

| Field | Value |
|---|---|
| ID | T032 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T025 |
| Plan reference | `docs/PLAN.md` §9.10 Audio Cue Bindings |

## Goal

Wire gameplay events to the existing `audio_trigger_*` routines so that
sound only plays in response to what the player is doing, and remove the
boot-time "audio sampler" that fires on every reset.

## Scope

- In scope:
  - `collision_update_pellet_at_pacman` pellet branch → waka cycle
    (alternate two waka pitches per dot, per arcade behavior).
  - Energizer branch → frightened cue (siren pitch shift or dedicated
    frightened-mode sequencer).
  - `collision_check_all_ghosts` eaten branch → `audio_trigger_ghost_eaten`.
  - `GAME_FLOW_STATE_DYING` entry → `audio_trigger_death_music`.
  - SCORE crossing 10000 (or configured threshold) →
    `audio_trigger_extra_life`.
  - `GAME_FLOW_STATE_READY` entry on level start → `audio_trigger_intro_music`.
  - Remove or gate `audio_review_script` behind a debug build flag
    (audit LOW-5).

- Out of scope:
  - Re-authoring waveforms or new musical content.
  - Siren chase/scatter switching (folded into Phase 8 audio polish if
    desired).

## Pre-flight

- [ ] T025 raising real gameplay events.
- [ ] T031 maintaining SCORE.

## Implementation notes

- Each `audio_trigger_*` is one call, side-effect-free besides starting
  the corresponding sequencer (`src/audio.asm:152`+).
- Waka alternation: keep a 1-bit `AUDIO_WAKA_PHASE` toggled per pellet,
  call the two waka variants alternately. (Arcade plays a slightly
  different up vs. down pitch each dot.)
- `audio_review_script` (`src/audio.asm:128`) currently auto-fires; gate
  with `IFDEF AUDIO_REVIEW_DEMO` so the live build skips it.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T032-audio-cue-bindings/audio_replay.txt` — headless
  run with recorded inputs that eats a row of pellets, an energizer,
  and dies; harness asserts `--expect-audio-hash` matches a recorded
  reference hash.
- `tests/evidence/T032-audio-cue-bindings/audio_silence_at_boot.txt` —
  headless run for 240 frames with no input, asserts audio hash equals
  the silent-output hash (no boot demo).

**Reviewer checklist:**

- [ ] Boot is silent.
- [ ] Eating a pellet produces waka.
- [ ] Eating an energizer kicks off the frightened cue.
- [ ] Dying plays the death jingle.

**Rerun command:**

```
python3 tools/build.py
python3 tools/audio_event_replay.py > tests/evidence/T032-audio-cue-bindings/audio_replay.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
