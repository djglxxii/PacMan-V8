# T006 — Maze Tile Re-authoring for 256x212

| Field | Value |
|---|---|
| ID | T006 |
| State | planned |
| Phase | Phase 2 — Maze Reconstruction |
| Depends on | T005 |
| Plan reference | `docs/PLAN.md` Phase 2 — Maze Reconstruction for V8 |

## Goal

Create a reproducible maze re-authoring step that maps the arcade maze
topology from T005 into a Vanguard 8 256x212 layout, preserving the movement
graph while producing reviewable visual output for the fitted maze.

## Scope

- In scope:
  - Add a tool under `tools/` that reads `assets/maze_nametable.bin`,
    `assets/maze_semantic.bin`, `assets/maze_graph.bin`, and the existing
    palette/tile assets.
  - Define the arcade tile to V8 pixel coordinate mapping for the fitted
    256x212 screen layout.
  - Re-author maze wall, pellet, energizer, ghost door, tunnel, and blank
    visual tiles for the V8 background layer without changing the T005
    topology.
  - Write deterministic generated assets needed by later render tasks, such
    as a coordinate mapping table and fitted maze/tile assets.
  - Produce a human-inspectable preview or frame artifact under
    `tests/evidence/T006-maze-tile-re-authoring/`.

- Out of scope:
  - Runtime VDP-B upload or framebuffer rendering code; T007 owns that.
  - Gameplay movement, collision, pellet consumption, or ghost AI.
  - Changing T005 maze semantics or movement graph topology.
  - Final visual polish beyond a faithful first fitted layout.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T005 is completed and accepted.
- [ ] `assets/maze_nametable.bin`, `assets/maze_semantic.bin`, and
  `assets/maze_graph.bin` exist and match the T005 manifest hashes.
- [ ] Review `docs/PLAN.md` Phase 2 screen layout and fit constraints.
- [ ] Confirm no other task is active before activation.

## Implementation notes

The gameplay coordinate system remains the arcade 28x36 tile grid. This task
only creates the render-side fitted layout for Vanguard 8. Keep generated
mapping data explicit and deterministic so later assembly code can use it
without interpreting text.

The plan reserves 8px HUD/status bands with a 240x196 maze area target. The
rotated arcade maze does not fit as a raw 8x8 tile grid, so this task should
preserve graph-relative positions and path continuity rather than scaling the
arcade framebuffer.

Do not overwrite T005 outputs except by rerunning `tools/extract_maze.py` for
verification. If the re-authoring exposes a topology issue in T005, stop and
report it instead of silently modifying the completed extraction.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T006-maze-tile-re-authoring/<preview>.ppm` — visual preview
  or emulator frame showing the fitted 256x212 maze layout.
- `tests/evidence/T006-maze-tile-re-authoring/<summary>.txt` — generated
  summary of output sizes, hashes, mapping bounds, and topology checks.

**Reviewer checklist** (human ticks these):

- [ ] The evidence preview fits within 256x212 with HUD/status clearance.
- [ ] Maze walls, pellets, energizers, tunnels, and ghost door are visually
  distinguishable.
- [ ] The mapping summary proves every T005 graph node maps inside the maze
  area without overlap that breaks path continuity.
- [ ] Generated assets are deterministic and include stable SHA-256 values.
- [ ] No runtime gameplay or VDP upload code is introduced in this task.

**Rerun command:**

```bash
# To be finalized when the T006 tool is implemented.
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created, state: planned. |

## Blocker (only if state = blocked)

*(None.)*
