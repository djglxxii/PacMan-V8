# T008 — Movement System and Turn Buffering

| Field | Value |
|---|---|
| ID | T008 |
| State | completed |
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

- [x] T007 is completed and accepted.
- [x] `assets/maze_semantic.bin`, `assets/maze_graph.bin`, and
  `assets/maze_v8_coordmap.bin` exist and match their manifest hashes.
- [x] Review `docs/PLAN.md` Phase 3.1 and 3.7 before implementation.
- [x] Confirm the intended fixed-point representation and direction enum in
  the active task notes before writing assembly.
- [x] Confirm no other task is active before activation.

## Implementation notes

Gameplay movement stays in the original arcade tile coordinate system, not the
fitted V8 render coordinate system. Use the fitted coordinate map only for
future rendering/debug display, not as the source of truth for collision.

T008 movement contract:

- Position representation: 8.8 fixed-point arcade pixels. A cell center is
  `(tile_index * 8 + 4) << 8` on each axis.
- Direction enum: `UP=0`, `LEFT=1`, `DOWN=2`, `RIGHT=3`, `NONE=4`.
- T008 configured movement speed: `0x0100` fixed-point pixels per frame. Full
  level-specific speed tables remain out of scope for this task.
- Turn-buffer window: `0x0400` fixed-point pixels, matching the documented
  approximate 4-pixel pre-turn window.
- Pac-Man passable semantic classes for this slice: `PATH`, `PELLET`,
  `ENERGIZER`, and `TUNNEL`.

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
python3 tools/movement_tests.py --vectors-output tests/evidence/T008-movement-turn-buffering/movement_vectors.txt > tests/evidence/T008-movement-turn-buffering/movement_tests.txt
```

**Observed evidence values:**

- `movement_tests.txt` SHA-256:
  `f1b31650125a0d1c9cd70428a5fd534c0a5874fcba72520c9272d21a3b7acc22`
- `movement_vectors.txt` SHA-256:
  `4e082b5a07c6f6eb3543ea494a48b42b0a2571ceff17ec986a805eafbbb53af4`
- Movement test result: `5/5 passed`
- Input asset hashes recorded by the test:
  - `assets/maze_semantic.bin`:
    `ca8c00e7b76da593a4fc2e9c8f064dde3ac0d062ee5cce1687500850325db111`
  - `assets/maze_graph.bin`:
    `4b355ccce9f28ad8acab093f7726287140dbcdf3429554a46473103caa1405a2`
  - `assets/maze_v8_coordmap.bin`:
    `551bfd06927f84482f59f3c215ba39bd70b1659c3b04ba600feb80095fc567f2`
- Build verification: `python3 -m py_compile tools/movement_tests.py` and
  `python3 tools/build.py` both passed.
- Runtime smoke verification:
  `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 60`
  completed 60 frames with event log digest `6563162820683566367`.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-17 | Created after T007 acceptance; state: planned. |
| 2026-04-17 | Activated after user request; beginning pre-flight checks, plan review, and movement-system implementation. |
| 2026-04-17 | Implemented runtime movement state/routines in `src/movement.asm`, included them in the ROM build, and added `tools/movement_tests.py` covering straight movement, wall stops, early turn acceptance/rejection, and horizontal tunnel wrap. Generated evidence under `tests/evidence/T008-movement-turn-buffering/`, verified Python compilation, ROM assembly, and a 60-frame headless smoke run. Stopping for human review. |

## Blocker (only if state = blocked)

*(None.)*
