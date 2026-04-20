# T018 — Game State Machine and Attract Mode

| Field | Value |
|---|---|
| ID | T018 |
| State | completed |
| Phase | Phase 6 — Game Flow |
| Depends on | T014, T015, T016 |
| Plan reference | `docs/PLAN.md` Phase 6 — Game Flow and State Machine |

## Goal

Introduce the first explicit game-flow state machine for boot, attract, ready,
playing, dying, level-complete, continue, and intermission handoff states, with
a deterministic attract-mode review path that does not alter the accepted
movement, AI, collision, rendering, HUD, or audio behavior.

## Scope

- In scope:
  - Review the Phase 6 plan and current boot/frame-loop structure before
    implementation.
  - Add state identifiers, timers, and transition plumbing for the planned
    Phase 6 states:
    `ATTRACT`, `READY`, `PLAYING`, `DYING`, `LEVEL_COMPLETE`, `CONTINUE`,
    `NEXT_LEVEL`, and `INTERMISSION`.
  - Add a deterministic initial flow suitable for review: boot to attract,
    transition through ready into playing, and expose scripted state changes
    that can exercise dying and level-complete handoffs without changing
    gameplay rules.
  - Add visible or textual review evidence for the active state and key
    transition frame numbers.
  - Keep existing renderer, HUD, movement, ghost AI, collision, ghost-house,
    sprite, PSG, and FM music accepted behavior compatible with the new flow.
  - Produce human-verifiable evidence under
    `tests/evidence/T018-game-state-machine-and-attract-mode/`.

- Out of scope:
  - Level speed tables, level progression details, Elroy timing, and score
    threshold changes; T019 owns these.
  - Full intermission cutscene content; T020 owns cutscene implementation.
  - Pattern replay/fidelity validation; T021 owns that validation phase.
  - New fruit spawn/award logic, extra-life thresholds, or score model
    changes unless they are strictly necessary to display existing HUD state.
  - Changing maze topology, coordinate transform, movement physics, ghost AI
    targeting, frightened timing, collision rules, pellet/dot-stall behavior,
    ghost-house release rules, sprite art, HUD art, PSG sound effects, or FM
    music cues.
  - Reading or reverse-engineering restricted Pac-Man program ROMs.

## Scope changes

*(None.)*

## Pre-flight

- [x] T014, T015, and T016 are completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Phase 6 game-flow section before implementation.
- [x] Review current `src/main.asm` frame loop, IM1 handler, and initialization
  order.
- [x] Review completed T014/T015 task evidence so state overlays or transition
  displays do not regress accepted HUD/sprite/coordinate-transform behavior.
- [x] Review completed T016/T017 audio task evidence so flow triggers do not
  disturb accepted deterministic audio review paths.
- [x] Consult Vanguard 8 emulator docs for input replay/headless options if
  using scripted input or frame-based review triggers.

## Implementation notes

The architectural state graph is:

```text
ATTRACT -> READY -> PLAYING -> (DYING | LEVEL_COMPLETE)
                     ^              |          |
                     |              v          v
                     +-------- CONTINUE    NEXT_LEVEL
                                               |
                                               v
                                          INTERMISSION
```

This task should establish the state-machine owner and deterministic review
surface, not complete all later game-flow content. Prefer a small assembly
module under `src/` plus a source-level Python harness, following the existing
task pattern for movement, collision, rendering, and audio validation.

Any visible review overlay should be deliberately scoped and should not become
a permanent art-direction change. If a frame capture is produced, it should
make the current state and transition evidence obvious to a human reviewer.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T018-game-state-machine-and-attract-mode/game_flow_tests.txt`
  — stdout from a deterministic state-transition validation harness.
- `tests/evidence/T018-game-state-machine-and-attract-mode/game_flow_vectors.txt`
  — readable state IDs, timer values, review trigger schedule, transition
  frames, hashes, and pass/fail results.
- `tests/evidence/T018-game-state-machine-and-attract-mode/game_flow_checklist.txt`
  — manual review checklist for frontend/headless behavior, including any
  captured frame path or audio/frame hash used during review.
- `tests/evidence/T018-game-state-machine-and-attract-mode/game_flow_frame_960.ppm`
  — optional runtime frame dump at the documented `INTERMISSION` handoff frame.
- `tests/evidence/T018-game-state-machine-and-attract-mode/psg_compatibility_tests.txt`
  and `psg_compatibility_vectors.txt` — T016 PSG compatibility rerun.
- `tests/evidence/T018-game-state-machine-and-attract-mode/fm_compatibility_tests.txt`
  and `fm_compatibility_vectors.txt` — T017 FM compatibility rerun.

**Reviewer checklist** (human ticks these):

- [ ] The ROM has one explicit current game-flow state at a time.
- [ ] Boot reaches `ATTRACT`, then `READY`, then `PLAYING` on the documented
  deterministic review schedule.
- [ ] Scripted review transitions exercise `DYING`, `CONTINUE`,
  `LEVEL_COMPLETE`, `NEXT_LEVEL`, and `INTERMISSION` handoff states without
  adding T019/T020 behavior.
- [ ] Movement, ghost AI, collision, rendering, HUD, PSG effects, and FM music
  remain compatible with the new state-machine calls.
- [ ] Evidence records state IDs, transition frame numbers, hashes or visible
  artifacts, and deterministic pass/fail results.
- [ ] Level progression, speed tables, intermission cutscenes, attract-title
  art, pattern replay validation, and new scoring behavior are not introduced.

**Rerun command:**

```bash
python3 tools/build.py
python3 tools/game_flow_tests.py --vectors-output tests/evidence/T018-game-state-machine-and-attract-mode/game_flow_vectors.txt > tests/evidence/T018-game-state-machine-and-attract-mode/game_flow_tests.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 960 --dump-frame tests/evidence/T018-game-state-machine-and-attract-mode/game_flow_frame_960.ppm --hash-frame 960
python3 tools/psg_sound_tests.py --vectors-output tests/evidence/T018-game-state-machine-and-attract-mode/psg_compatibility_vectors.txt > tests/evidence/T018-game-state-machine-and-attract-mode/psg_compatibility_tests.txt
python3 tools/fm_music_tests.py --vectors-output tests/evidence/T018-game-state-machine-and-attract-mode/fm_compatibility_vectors.txt > tests/evidence/T018-game-state-machine-and-attract-mode/fm_compatibility_tests.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 300 --hash-audio
```

**Observed evidence values:**

- `game_flow_tests.py`: `5/5 passed`
- `game_flow_tests.txt` SHA-256:
  `787339cba4ffec0bed7102ce1e35a6c412105c87b6f08953409cac5713ea9dd0`
- `game_flow_vectors.txt` SHA-256:
  `549b063aa38f19b48120c3c767663a6efaada762421da5d68d25f46beee64d94`
- `game_flow_checklist.txt` SHA-256:
  `cee6946ee04d90f939bea9b18d4bdfb36eaa3174d18fb772d4a7c43f9a4d8f49`
- ROM SHA-256:
  `16d1dc626a6c93cf581f5607269e88c118d437266e3fa818a9717d06afefd9ac`
- `src/main.asm` SHA-256:
  `324b42ffdd00ea04385a8e4710d6697c170e8cb9fc46c5c945208397ed115827`
- `src/game_flow.asm` SHA-256:
  `dcf5e2adf0b74c2ca428e6e87812f258a29e66aa56ca40e1b92cd2d14f2b6006`
- `tools/game_flow_tests.py` SHA-256:
  `d5eef172e0bec79d0380ea8d50acbe45299ec44be4b8f1ea5c97760e51814979`
- Deterministic transition frames:
  `120`, `360`, `480`, `570`, `630`, `810`, `900`, `960`
- Final review flags:
  `0xFF`
- Headless frame hash at frame `960`:
  `4a63cec305375edd4b20e85ba9830d83888e2eaf4327a29c229cfc7ce7a79693`
- `game_flow_frame_960.ppm` SHA-256:
  `c0a29b0596a4b01ab1fb061291d74664bb3eed6b3e27342f156450eca5989281`
- Headless `960`-frame event log digest:
  `12325614728164139587`
- PSG compatibility validation:
  `16/16 passed`; register trace SHA-256
  `5b42f187966ed3e89d0ac19c1d06fb9bc28c732aea7cc62b71db6214bf26fbaf`
- FM compatibility validation:
  `29/29 passed`; register trace SHA-256
  `1c00bb874e1db7356288b22048409153a43338e52c01e53405bf11f21ec9a51f`
- T018 `300`-frame PCM audio SHA-256:
  `d99a8a94607436a8024330893ea4c8fca66de6029f2353c0feb9736e3689578e`
- T018 `300`-frame audio event log digest:
  `793085328687964239`
- Audio compatibility note:
  the T017 bit-exact PCM hash changes because T018 adds boot/frame-loop CPU
  work, but the PSG/FM register-trace schedules remain unchanged and the audio
  event digest still matches the T017 evidence value.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-19 | Created, state: planned. |
| 2026-04-20 | Activated task, state: active. Beginning pre-flight review of Phase 6 plan, current frame loop, and accepted rendering/audio evidence before implementation. |
| 2026-04-20 | Implemented `src/game_flow.asm` with explicit Phase 6 state IDs, timers, transition records, review flags, and a deterministic boot/ready/playing/death/continue/level-complete/intermission handoff script. Wired `game_flow_init` into reset and `game_flow_update_frame` into the post-`HALT` frame loop so the IM1 audio handler remains scoped to audio. Added `tools/game_flow_tests.py`, generated text/vector/checklist/frame evidence under `tests/evidence/T018-game-state-machine-and-attract-mode/`, verified build, headless frame run, and PSG/FM compatibility harnesses. Added `docs/field-manual/frame-loop-state-updates-preserve-audio-hash.md`. Stopping for human review. |
| 2026-04-20 | Accepted by human reviewer; moving task to completed and preparing T019 as the next planned task. |

## Blocker (only if state = blocked)

*(None.)*
