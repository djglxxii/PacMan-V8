# T008 — Movement System and Turn Buffering

| Field | Value |
|---|---|
| ID | T008 |
| State | planned |
| Phase | Phase 3 — Gameplay Core |
| Depends on | T007 |
| Plan reference | `docs/PLAN.md` Phase 3.1 Movement System; Phase 3.7 Tunnel |

## Goal

Implement the first gameplay-core movement slice: deterministic tile-based
Pac-Man movement with sub-tile precision, wall stops, tunnel wrap handling, and
early turn buffering suitable for arcade pattern play.

## Scope

- In scope:
  - Add runtime movement state for Pac-Man's arcade-grid position, current
    direction, requested direction, and sub-tile progress.
  - Implement fixed-point per-frame movement using the existing maze semantic
    grid or movement graph assets.
  - Keep Pac-Man aligned to legal path centerlines and stop at walls.
  - Implement turn buffering so a queued turn can be accepted shortly before
    reaching an intersection center, targeting the documented ~4-pixel
    pre-turn window.
  - Implement basic horizontal tunnel wrap in arcade-grid coordinates.
  - Add deterministic movement tests under `tools/` or an equivalent local
    test harness that exercises straight movement, blocked movement, early
    turn acceptance/rejection, and tunnel wrapping.
  - Produce test-output evidence under
    `tests/evidence/T008-movement-turn-buffering/`.

- Out of scope:
  - Ghost movement, ghost targeting, scatter/chase/frightened behavior, or
    ghost-house release logic.
  - Pellet consumption, dot-stall, energizer effects, score, lives, or fruit.
  - Rendering Pac-Man, ghosts, movement debug overlays, HUD, or animation.
  - Full per-level speed table implementation beyond whatever constants are
    needed to prove the movement stepper.
  - Audio or input replay integration beyond deterministic test inputs.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T007 is completed and accepted.
- [ ] `assets/maze_semantic.bin`, `assets/maze_graph.bin`, and
  `assets/maze_v8_coordmap.bin` exist and match their manifest hashes.
- [ ] Review `docs/PLAN.md` Phase 3.1 and 3.7 before implementation.
- [ ] Confirm the intended fixed-point representation and direction enum in
  the active task notes before writing assembly.
- [ ] Confirm no other task is active before activation.

## Implementation notes

Gameplay movement stays in the original arcade tile coordinate system, not the
fitted V8 render coordinate system. Use the fitted coordinate map only for
future rendering/debug display, not as the source of truth for collision.

T005 generated the movement inputs:

- `assets/maze_semantic.bin`: 36 rows by 28 columns, one cell class per tile.
- `assets/maze_graph.bin`: header plus fixed-width node and edge records.
- Graph flags include tunnel endpoints (`0x0004`), warp edges (`0x0040`), and
  tunnel edges (`0x0080`).

T006 generated the render mapping:

- `assets/maze_v8_coordmap.bin`: 36 by 28 row-major records mapping arcade
  cells to V8 pixel rectangles.

Keep this task focused on deterministic movement math. If the assembly runtime
is not yet convenient to unit-test directly, a Python reference harness is
acceptable as evidence only if the task also adds the same movement rules to
the runtime source and the test vectors are simple enough to audit against the
assembly constants/tables.

Do not read or derive movement behavior from the restricted Pac-Man program
ROMs. Use public Pac-Man behavior documentation and the already-generated maze
semantic/graph assets.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T008-movement-turn-buffering/movement_tests.txt` — stdout
  from the deterministic movement test harness.
- `tests/evidence/T008-movement-turn-buffering/movement_vectors.txt` — readable
  summary of start state, input sequence, and expected/final state for each
  covered movement case.

**Reviewer checklist** (human ticks these):

- [ ] Straight movement advances in the current direction by the configured
  fixed-point speed without drifting off the path centerline.
- [ ] Movement stops before entering wall cells.
- [ ] A requested turn inside the early-turn window is accepted at the next
  legal intersection center.
- [ ] A requested turn outside the early-turn window is rejected until the next
  valid opportunity.
- [ ] Horizontal tunnel movement wraps across the maze edge in arcade-grid
  coordinates.
- [ ] The evidence output records deterministic pass/fail results and the
  hashes of movement input assets used by the tests.
- [ ] No ghost AI, pellet consumption, rendering, audio, scoring, or gameplay
  state-machine behavior is introduced.

**Rerun command:**

```bash
# To be finalized when T008 is implemented.
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-17 | Created after T007 acceptance; state: planned. |

## Blocker (only if state = blocked)

*(None.)*
