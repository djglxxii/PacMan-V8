# T011 — Collision, Pellets, and Dot-Stall

| Field | Value |
|---|---|
| ID | T011 |
| State | completed |
| Phase | Phase 3 — Gameplay Core |
| Depends on | T008, T010 |
| Plan reference | `docs/PLAN.md` Phase 3.6 Collision Detection; Phase 4.3 VDP-B Pellet Management |

## Goal

Implement the first deterministic collision and pellet-consumption slice:
Pac-Man consumes pellets and energizers at tile centers, dot-stall timing is
tracked for movement integration, energizers enter frightened mode through the
T010 mode controller, and Pac-Man/ghost same-tile collisions report the correct
gameplay outcome.

## Scope

- In scope:
  - Add runtime collision/pellet state separate from rendering and scoring.
  - Track remaining pellets/energizers from the generated semantic maze input.
  - Consume a pellet or energizer when Pac-Man's center crosses the matching
    tile center.
  - Expose a pellet-erase queue entry or equivalent deterministic state for
    later VDP-B rendering work; actual HMMM erase rendering remains out of
    scope.
  - Apply dot-stall counters: 1 frame for a normal pellet, 3 frames for an
    energizer.
  - Trigger T010 frightened entry when an energizer is consumed.
  - Detect Pac-Man vs. ghost same-tile collisions and report distinct outcomes:
    normal ghost kills Pac-Man, frightened ghost is eaten, no collision.
  - Add deterministic tests under `tools/` or an equivalent local harness that
    exercise pellet consumption, energizer consumption, dot-stall duration,
    duplicate-consumption prevention, erase-queue output, and representative
    ghost collision outcomes.
  - Produce test-output evidence under
    `tests/evidence/T011-collision-pellets-dot-stall/`.

- Out of scope:
  - Rendering pellet erases to VDP-B, energizer blink animation, sprites, HUD,
    score display, lives display, death animation, audio, or game-flow state
    transitions.
  - Fruit spawning or fruit collisions.
  - Ghost house release logic, eaten-ghost eyes movement, or return-to-house
    pathing.
  - Full level progression, speed tables, Elroy behavior, or pattern-replay
    validation.
  - Modifying Pac-Man movement speed directly beyond exposing a dot-stall
    counter/flag that later movement integration can consume.

## Scope changes

*(None.)*

## Pre-flight

- [x] T008 and T010 are completed and accepted.
- [x] Review `docs/PLAN.md` Phase 3.6 and Phase 4.3 before implementation.
- [x] Review `docs/tasks/completed/T008-movement-system-and-turn-buffering.md`
  for the 8.8 fixed-point center/tile contract.
- [x] Review `docs/tasks/completed/T010-scatter-chase-timer-and-frightened-mode.md`
  for frightened mode entry and ghost mode state.
- [x] Verify `assets/maze_semantic.bin`, `assets/maze_graph.bin`, and
  `assets/maze_v8_coordmap.bin` match their accepted hashes before using them
  in tests.
- [x] Confirm no other task is active before activation.

## Implementation notes

Gameplay collision stays in the original arcade tile coordinate system. Use
T008's 8.8 fixed-point position contract: a tile center is
`(tile * 8 + 4) << 8`, and consumption should occur only when Pac-Man reaches
the relevant tile center, not merely when his position maps to the tile.

The pellet state should be initialized from tracked/generated maze data, not
from the arcade program ROMs. A compact runtime bitset is appropriate for
pellet-present state; tests should record initial counts and specific tile
coordinates used by each vector.

Dot-stall should be represented as an explicit counter or flag that later
movement code can consume. This task does not need to freeze live movement in
the main loop if the gameplay loop is not wired yet, but the runtime state and
test harness should prove the exact 1-frame and 3-frame stall durations.

Energizer consumption should call or model the T010 frightened entry point and
record that the pending reversal mask is set. Frightened expiry, random
movement, and flashing remain owned by T010/T013+.

Ghost collision outcomes should be data-level results suitable for later
game-flow work:

- normal/scatter/chase ghost on Pac-Man's tile => Pac-Man death result
- frightened ghost on Pac-Man's tile => ghost-eaten result
- different tiles => no collision

Do not add scoring, lives decrement, ghost-house routing, death animation, or
sound effects in this task.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T011-collision-pellets-dot-stall/collision_tests.txt` —
  stdout from the deterministic collision/pellet/dot-stall test harness.
- `tests/evidence/T011-collision-pellets-dot-stall/collision_vectors.txt` —
  readable summary of pellet/energizer coordinates, fixed-point positions,
  consumed-state changes, dot-stall counters, erase-queue outputs, frightened
  entry effects, and ghost collision outcomes.

**Reviewer checklist** (human ticks these):

- [ ] Pellet consumption occurs only at the tile center and removes that pellet
  from the runtime pellet state.
- [ ] Consuming the same pellet twice does not decrement counts or enqueue a
  second erase.
- [ ] Normal pellets set a 1-frame dot-stall counter.
- [ ] Energizers set a 3-frame dot-stall counter and trigger T010 frightened
  entry/reversal state.
- [ ] The erase-queue state identifies the consumed tile for later VDP-B
  rendering.
- [ ] Same-tile Pac-Man/ghost collisions produce normal-death and
  frightened-eaten outcomes as appropriate.
- [ ] Evidence output records deterministic pass/fail results and relevant
  asset hashes/constants.
- [ ] No rendering, scoring, lives, audio, fruit, ghost-house routing, or
  game-flow transitions are introduced.

**Rerun command:**

```bash
python3 tools/collision_tests.py --vectors-output tests/evidence/T011-collision-pellets-dot-stall/collision_vectors.txt > tests/evidence/T011-collision-pellets-dot-stall/collision_tests.txt
```

**Observed evidence values:**

- `collision_tests.txt` SHA-256:
  `d78cdb589fcd12618c585936debf61b7cdfd78e9be6569259e29c176015f2a18`
- `collision_vectors.txt` SHA-256:
  `8d85cce48cfbc3ef85a5844a3e8af09e3d432f474b1cdbc9861e9e65b0f77090`
- Collision/pellet/dot-stall test result: `4/4 passed`
- Input asset hashes recorded by the test:
  - `assets/maze_semantic.bin`:
    `ca8c00e7b76da593a4fc2e9c8f064dde3ac0d062ee5cce1687500850325db111`
  - `assets/maze_graph.bin`:
    `4b355ccce9f28ad8acab093f7726287140dbcdf3429554a46473103caa1405a2`
  - `assets/maze_v8_coordmap.bin`:
    `551bfd06927f84482f59f3c215ba39bd70b1659c3b04ba600feb80095fc567f2`
- Test constants recorded by the evidence:
  - Runtime consumable bitset size: `126` bytes for 28x36 cells.
  - Initial consumable counts: `240` normal pellets and `4` energizers.
  - Dot-stall durations: `1` frame for pellets and `3` frames for energizers.
  - Frightened reversal mask on energizer consumption: `0x0F`.
- Build verification:
  `python3 -m py_compile tools/collision_tests.py tools/mode_timer_tests.py tools/ghost_ai_tests.py tools/movement_tests.py`
  and `python3 tools/build.py` both passed.
- Regression verification:
  `tools/movement_tests.py`, `tools/ghost_ai_tests.py`, and
  `tools/mode_timer_tests.py` all passed when rerun with their existing vector
  output paths.
- Runtime smoke verification:
  `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 60`
  completed 60 frames with event log digest `6563162820683566367`.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-17 | Created after T010 acceptance; state: planned. |
| 2026-04-18 | Activated T011 after confirming no other active task; beginning plan/prerequisite review. |
| 2026-04-18 | Implemented runtime collision/pellet state in `src/collision.asm`, included it in the ROM build, and added `tools/collision_tests.py` covering initial consumable counts, tile-center-only pellet consumption, duplicate prevention, erase queue state, pellet/energizer dot-stall counters, T010 frightened entry/reversal on energizer consumption, and same-tile ghost collision outcomes. Generated evidence under `tests/evidence/T011-collision-pellets-dot-stall/`, verified Python compilation, ROM assembly, T008/T009/T010 regressions, and a 60-frame headless smoke run. Added field manual entry `docs/field-manual/z80-row-major-bitset-scans.md`. Stopping for human review. |

## Blocker (only if state = blocked)

*(None.)*
