# T012 — Ghost House Logic

| Field | Value |
|---|---|
| ID | T012 |
| State | completed |
| Phase | Phase 3 — Gameplay Core |
| Depends on | T009, T010, T011 |
| Plan reference | `docs/PLAN.md` Phase 3.4 Ghost House Logic |

## Goal

Implement the first deterministic ghost-house state slice: initial in-house
state, exit ordering, dot-counter release rules, and fallback global-timer
release state suitable for later ghost movement and game-flow integration.

## Scope

- In scope:
  - Add runtime ghost-house state separate from rendering, scoring, and lives.
  - Represent whether each ghost is outside, waiting in the house, exiting, or
    pending release.
  - Model the level-start release order: Blinky starts outside, then Pinky,
    Inky, and Clyde become eligible in order.
  - Track per-ghost dot counters or release thresholds using T011 pellet
    consumption events as deterministic inputs.
  - Add a global release timer fallback for cases where no dots are eaten.
  - Expose release/exit decisions as data-level flags or state transitions that
    later movement and pathing work can consume.
  - Add deterministic tests under `tools/` or an equivalent local harness that
    exercise initial state, dot-count release order, duplicate/non-dot event
    handling, timer fallback release, reset-on-life-loss behavior, and
    interaction boundaries with frightened/scatter/chase mode state.
  - Produce checklist/test-output evidence under
    `tests/evidence/T012-ghost-house-logic/`.

- Out of scope:
  - Full in-house bouncing movement, door crossing animation, or exact
    tile-by-tile exit pathing.
  - Eaten-ghost eyes returning to the house after a frightened collision.
  - Score, lives, death/game-over flow, attract mode, HUD, sprites, audio,
    fruit, Elroy, or level progression.
  - Tuning full per-level release tables beyond constants needed to prove the
    first deterministic slice.
  - Pattern replay or full arcade-fidelity validation beyond the included
    deterministic release vectors.

## Scope changes

*(None.)*

## Pre-flight

- [x] T009, T010, and T011 are completed and accepted.
- [x] Review `docs/PLAN.md` Phase 3.4 before implementation.
- [x] Review `docs/tasks/completed/T009-ghost-ai-and-targeting.md` for ghost
  IDs, record layout, direction enum, and target-selection boundaries.
- [x] Review `docs/tasks/completed/T010-scatter-chase-timer-and-frightened-mode.md`
  for global/per-ghost mode fields and reversal-state ownership.
- [x] Review `docs/tasks/completed/T011-collision-pellets-and-dot-stall.md`
  for pellet-consumption event state and dot-stall boundaries.
- [x] Confirm no other task is active before activation.

## Implementation notes

Keep ghost-house logic data-level for this slice. Later movement work can turn
release flags into actual door/path motion; this task should only establish
the deterministic state machine and counters.

Use the ghost IDs and record layout already introduced by T009/T010:
Blinky is ghost `0`, Pinky `1`, Inky `2`, and Clyde `3`. Blinky should begin
outside. Pinky, Inky, and Clyde should be represented as in-house/pending until
their release condition fires.

Use T011 pellet or energizer consumption as the dot-event input. Duplicate
consumption or non-dot frames must not advance release counters. The first test
slice may use named constants for release thresholds if full level-specific
tables are not yet in scope, but those constants must be recorded in the
evidence vectors.

Mode control remains owned by T010. Frightened/scatter/chase state may coexist
with house state, but this task should not add frightened movement, eaten-eyes
return routing, or sprite rendering.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T012-ghost-house-logic/ghost_house_tests.txt` — stdout from
  the deterministic ghost-house release test harness.
- `tests/evidence/T012-ghost-house-logic/ghost_house_vectors.txt` — readable
  summary of initial house state, dot-event sequence, release counters,
  fallback timer values, reset behavior, and final per-ghost states.

**Reviewer checklist** (human ticks these):

- [ ] Blinky starts outside while Pinky, Inky, and Clyde start in the house or
  pending release.
- [ ] Dot-event release proceeds in the documented order: Pinky, then Inky,
  then Clyde.
- [ ] Duplicate pellet consumption or no-consume frames do not advance release
  counters.
- [ ] Global timer fallback can release a waiting ghost when dots are not eaten.
- [ ] Life-loss reset returns house counters/state to the documented starting
  condition for the next life slice.
- [ ] Evidence output records deterministic pass/fail results and relevant
  constants/hashes.
- [ ] No rendering, scoring, lives decrement, audio, fruit, eaten-eyes return
  pathing, or game-flow transitions are introduced.

**Rerun command:**

```bash
python3 tools/ghost_house_tests.py --vectors-output tests/evidence/T012-ghost-house-logic/ghost_house_vectors.txt > tests/evidence/T012-ghost-house-logic/ghost_house_tests.txt
```

**Observed evidence values:**

- `ghost_house_tests.txt` SHA-256:
  `2c013e0bfc51f16e921f02741900eb5f6c644ab3cd418c719d57cc269749a732`
- `ghost_house_vectors.txt` SHA-256:
  `1c131dcab07bfe26f3e56448975811d7871f6b9fb402fbff1c46aaaa8b255735`
- Ghost-house test result: `5/5 passed`
- Release constants recorded by the evidence:
  - State values: `OUTSIDE=0`, `WAITING=1`, `PENDING_RELEASE=2`, `EXITING=3`.
  - Dot thresholds: Pinky `0`, Inky `30`, Clyde `60`.
  - Global fallback release timer: `240` frames.
  - Release order: Blinky starts outside, then Pinky, Inky, Clyde.
- Build verification:
  `python3 -m py_compile tools/ghost_house_tests.py tools/collision_tests.py tools/mode_timer_tests.py tools/ghost_ai_tests.py tools/movement_tests.py`
  and `python3 tools/build.py` both passed.
- Regression verification:
  `tools/movement_tests.py`, `tools/ghost_ai_tests.py`,
  `tools/mode_timer_tests.py`, `tools/collision_tests.py`, and
  `tools/ghost_house_tests.py` all passed.
- Runtime smoke verification:
  `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 60`
  completed 60 frames with event log digest `6563162820683566367`.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-18 | Created after T011 acceptance; state: planned. |
| 2026-04-18 | Activated per user request; beginning pre-flight review and implementation. |
| 2026-04-18 | Implemented data-level ghost-house release state in `src/ghost_house.asm`, initialized it from ghost runtime setup, and connected successful T011 pellet/energizer consumption to the house dot-event counter. Added `tools/ghost_house_tests.py`, generated evidence under `tests/evidence/T012-ghost-house-logic/`, verified Python compilation, ROM assembly, T008-T011 regressions plus T012, and a 60-frame headless smoke run. Added field manual entry `docs/field-manual/ghost-house-release-pending-state.md`. Stopping for human review. |
| 2026-04-18 | Human approved deliverable; moved task to completed. |

## Blocker (only if state = blocked)

*(None.)*
