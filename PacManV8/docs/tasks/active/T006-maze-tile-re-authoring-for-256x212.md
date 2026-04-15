# T006 — Portrait Maze Re-authoring for 256x212

| Field | Value |
|---|---|
| ID | T006 |
| State | active |
| Phase | Phase 2 — Maze Reconstruction |
| Depends on | T005 |
| Plan reference | `docs/PLAN.md` Phase 2 — Maze Reconstruction for V8 |

## Goal

Create a reproducible maze re-authoring step that maps the T005 arcade maze
topology into the revised Vanguard 8 portrait-on-landscape layout. The output
must preserve the arcade player-view orientation, keep the maze centered with
black side margins, and produce reviewable evidence for the fitted 256x212
presentation layout.

## Scope

- In scope:
  - Add or update a tool under `tools/` that reads `assets/maze_nametable.bin`,
    `assets/maze_semantic.bin`, `assets/maze_graph.bin`, and the existing
    palette/tile assets.
  - Define the no-rotation arcade tile to V8 pixel rectangle mapping:
    `arcade_x -> v8_x + horizontal offset`, `arcade_y -> v8_y + HUD
    clearance`.
  - Fit the 28x31 maze area into the available 196-pixel vertical span between
    the 8px HUD and 8px status bands, using non-uniform vertical cell heights
    while keeping the maze horizontally centered.
  - Re-author maze wall, pellet, energizer, ghost door, tunnel, ghost-house,
    path, and blank visual primitives for the fitted portrait maze without
    changing T005 topology or movement graph data.
  - Write deterministic generated assets needed by later render tasks, such as
    a coordinate mapping table and fitted maze visual data.
  - Produce a human-inspectable preview or frame artifact under
    `tests/evidence/T006-maze-tile-re-authoring/`.

- Out of scope:
  - Rotating the maze into landscape orientation. The revised plan explicitly
    preserves the arcade player-view portrait orientation.
  - Runtime VDP-B upload or framebuffer rendering code; T007 owns runtime maze
    rendering unless the plan is revised again before activation.
  - Gameplay movement, collision, pellet consumption, ghost AI, or timing.
  - Changing T005 maze semantics or movement graph topology.
  - Final visual polish beyond a faithful first fitted layout.

## Scope changes

*(None.)*

## Pre-flight

- [x] T005 is completed and accepted.
- [x] `assets/maze_nametable.bin`, `assets/maze_semantic.bin`, and
  `assets/maze_graph.bin` exist and match the T005 manifest hashes.
- [x] Review `docs/PLAN.md` Orientation and Phase 2 screen layout sections,
  confirming the no-rotation portrait-maze mapping.
- [x] Confirm no other task is active before activation.

## Implementation notes

The gameplay coordinate system remains the arcade 28x36 tile grid. This task
only creates the render-side fitted layout for Vanguard 8.

The revised plan says the displayed maze should remain in the arcade
player-view portrait orientation:

```text
arcade_x -> v8_x + horizontal offset (centering)
arcade_y -> v8_y + vertical offset (HUD clearance)
```

The maze proper is 28x31 tiles, excluding HUD rows, or 224x248 pixels at
native 8x8 scale. The V8 screen leaves 196 vertical pixels for the maze after
8px top HUD and 8px bottom status bands, so vertical fitting is the
constraining axis. Horizontal native width is 224 pixels, so the fitted maze
should remain centered within the 256-pixel screen with black side margins.

Keep generated mapping data explicit and deterministic so later assembly can
consume it without parsing text. Preserve graph-relative positions and path
continuity; do not silently modify T005 outputs. If fitting exposes a topology
issue in T005, stop and report it instead of changing completed extraction
data.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T006-maze-tile-re-authoring/maze_v8_preview.ppm` — visual
  preview showing the fitted portrait maze on the 256x212 landscape screen.
- `tests/evidence/T006-maze-tile-re-authoring/summary.txt` — generated
  summary of output sizes, hashes, mapping bounds, cell dimensions, and
  topology checks.
- `tests/evidence/T006-maze-tile-re-authoring/reauthor_maze_v8.log` — stdout
  from the generator rerun.

**Reviewer checklist** (human ticks these):

- [ ] The evidence preview is 256x212, keeps the maze in portrait orientation,
  and shows black side margins.
- [ ] The maze fits between the HUD band at `y=0-7` and the status band
  beginning at `y=204`.
- [ ] Maze walls, pellets, energizers, tunnels, ghost house, and ghost door are
  visually distinguishable.
- [ ] The mapping summary proves every T005 graph node maps inside the fitted
  maze area without overlap that breaks path continuity.
- [ ] Generated assets are deterministic and include stable SHA-256 values.
- [ ] No runtime gameplay or VDP upload code is introduced in this task.

**Rerun command:**

```bash
python3 tools/reauthor_maze_v8.py | tee tests/evidence/T006-maze-tile-re-authoring/reauthor_maze_v8.log
```

**Observed values:**

- Maze area: `224x196` at V8 pixel origin `(16,8)`; mapping bounds
  `x=16-239`, `y=8-203`.
- Side margins: `16` px left, `16` px right.
- Cell dimensions: all columns `8` px wide; arcade maze row heights range
  `6-7` px with sequence
  `6,6,6,7,6,6,7,6,6,7,6,6,7,6,6,7,6,6,7,6,6,7,6,6,7,6,6,7,6,6,7`.
- `assets/maze_v8_coordmap.bin` bytes: `8064`
- `assets/maze_v8_coordmap.bin` SHA-256:
  `551bfd06927f84482f59f3c215ba39bd70b1659c3b04ba600feb80095fc567f2`
- `assets/maze_v8_drawlist.bin` bytes: `6128`
- `assets/maze_v8_drawlist.bin` SHA-256:
  `ffc8a11f3cebefa7d925fae1417a8a70089ad64e1863ebfc33f97d5b0a7aeaa3`
- `assets/maze_v8_framebuffer.bin` bytes: `27136`
- `assets/maze_v8_framebuffer.bin` SHA-256:
  `78a7fedcb2f504a6f16ebb77aa196939a263a01c9a1d00a59ebff6a4656cb895`
- Graph nodes mapped: `132/132`
- Graph node center overlaps: `0`
- Walkable adjacencies contiguous: `410/410`
- Warp edges preserved as non-contiguous wrap links: `1`
- Regression check: `python3 -m py_compile tools/reauthor_maze_v8.py`
  completed, and `python3 tools/build.py` completed with ROM size `16,384`
  bytes and symbol count `7`.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created from the revised plan after discarding the prior rotated-layout T006 work; state: planned. |
| 2026-04-15 | Activated after confirming no other active task; beginning T005 asset hash verification and portrait-fit implementation. |
| 2026-04-15 | Implemented `tools/reauthor_maze_v8.py`, generated portrait V8 coordinate, drawlist, framebuffer, manifest, summary, and preview evidence. Verified deterministic rerun output, topology checks, `py_compile`, and existing ROM build. Stopping for human review. |

## Blocker (only if state = blocked)

*(None.)*
