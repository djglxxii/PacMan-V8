# T009 — Ghost AI and Targeting

| Field | Value |
|---|---|
| ID | T009 |
| State | planned |
| Phase | Phase 3 — Gameplay Core |
| Depends on | T008 |
| Plan reference | `docs/PLAN.md` Phase 3.2 Ghost AI |

## Goal

Implement the first deterministic ghost AI slice: target-tile calculation for
the four ghosts and intersection direction choice using the movement graph,
suitable for later scatter/chase timer integration.

## Scope

- In scope:
  - Add runtime ghost state for arcade-grid position, direction, mode input,
    and per-ghost identity data needed by targeting.
  - Implement chase target tile calculation for Blinky, Pinky, Inky, and
    Clyde, including Pinky's original up-direction overflow behavior.
  - Implement scatter target tiles for all four ghosts.
  - Implement intersection direction selection by choosing the legal
    non-reversal direction that minimizes squared distance to the target tile.
  - Use T008's arcade-coordinate movement contract and existing maze semantic
    or graph assets as the topology source of truth.
  - Add deterministic tests under `tools/` or an equivalent local harness that
    exercise each ghost's target calculation and representative intersection
    choices.
  - Produce test-output evidence under
    `tests/evidence/T009-ghost-ai-targeting/`.

- Out of scope:
  - Scatter/chase global timer sequencing or mode-switch reversal timing.
  - Frightened mode random movement, flashing, ghost-eaten behavior, or eyes
    returning to the house.
  - Ghost house release logic and dot counters.
  - Collision handling, pellet consumption, scoring, lives, fruit, audio, or
    rendering.
  - Full speed table implementation beyond constants needed by deterministic
    AI tests.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T008 is completed and accepted.
- [ ] Review `docs/PLAN.md` Phase 3.2 before implementation.
- [ ] Review the T008 movement contract in
  `docs/tasks/completed/T008-movement-system-and-turn-buffering.md`.
- [ ] Confirm `assets/maze_semantic.bin` and `assets/maze_graph.bin` match
  their manifest hashes.
- [ ] Confirm no other task is active before activation.

## Implementation notes

Keep ghost AI in the original arcade tile coordinate system. T009 should
consume Pac-Man and ghost positions as arcade tiles or 8.8 fixed-point arcade
pixels, then produce target tiles and selected directions. The render mapping
from T006 remains out of scope.

Direction order matters for deterministic tie-breaking. Before implementation,
record the selected direction enum and tie-order in this task file, keeping it
compatible with T008's `UP=0`, `LEFT=1`, `DOWN=2`, `RIGHT=3`, `NONE=4`
contract unless there is a plan-level reason to change it.

Tests should be simple enough for a reviewer to audit without reading arcade
program ROMs. Use publicly documented Pac-Man behavior and the generated maze
topology assets only.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T009-ghost-ai-targeting/ghost_ai_tests.txt` — stdout from
  the deterministic ghost AI test harness.
- `tests/evidence/T009-ghost-ai-targeting/ghost_ai_vectors.txt` — readable
  summary of inputs, target tiles, legal choices, tie cases, and final chosen
  directions for each covered AI case.

**Reviewer checklist** (human ticks these):

- [ ] Blinky targets Pac-Man's current tile in chase mode.
- [ ] Pinky targets four tiles ahead of Pac-Man, including the documented
  up-direction overflow offset.
- [ ] Inky's target uses Blinky and Pac-Man positions to compute the doubled
  vector from the two-ahead tile.
- [ ] Clyde targets Pac-Man when farther than eight tiles and his scatter
  corner when within eight tiles.
- [ ] Scatter target tiles are stable and distinct for all four ghosts.
- [ ] Intersection choice excludes reversal unless explicitly allowed by the
  test setup and chooses the legal direction with minimum squared distance.
- [ ] Evidence output records deterministic pass/fail results and hashes of
  the movement input assets used by the tests.
- [ ] No scatter/chase timer, frightened mode, ghost house release, collision,
  pellet, rendering, audio, scoring, or game-flow behavior is introduced.

**Rerun command:**

```bash
# To be finalized when T009 is implemented.
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-17 | Created after T008 acceptance; state: planned. |

## Blocker (only if state = blocked)

*(None.)*
