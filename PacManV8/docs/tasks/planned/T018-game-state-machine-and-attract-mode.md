# T018 — Game State Machine and Attract Mode

| Field | Value |
|---|---|
| ID | T018 |
| State | planned |
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

- [ ] T014, T015, and T016 are completed and accepted.
- [ ] Confirm no other task is active before activation.
- [ ] Review `docs/PLAN.md` Phase 6 game-flow section before implementation.
- [ ] Review current `src/main.asm` frame loop, IM1 handler, and initialization
  order.
- [ ] Review completed T014/T015 task evidence so state overlays or transition
  displays do not regress accepted HUD/sprite/coordinate-transform behavior.
- [ ] Review completed T016/T017 audio task evidence so flow triggers do not
  disturb accepted deterministic audio review paths.
- [ ] Consult Vanguard 8 emulator docs for input replay/headless options if
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
# Additional headless/frontend checklist command(s) filled after implementation.
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-19 | Created, state: planned. |

## Blocker (only if state = blocked)

*(None.)*
