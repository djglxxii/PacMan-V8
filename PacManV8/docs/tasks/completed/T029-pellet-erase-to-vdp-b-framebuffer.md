# T029 — Pellet/Energizer Erase to VDP-B Framebuffer

| Field | Value |
|---|---|
| ID | T029 |
| State | active |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T025 |
| Plan reference | `docs/PLAN.md` §9.7 Pellet Erase to VDP-B Framebuffer |

## Goal

Consume `COLLISION_ERASE_PENDING` and write 8×8 transparent pixels to the
VDP-B maze framebuffer at the eaten tile's pixel coordinates, so eaten
dots actually disappear from the maze.

## Scope

- In scope:
  - New `pellet_erase_commit` that runs after the gameplay tick and
    before the next V-blank closes. Reads `COLLISION_ERASE_TILE_X/Y`
    and `COLLISION_ERASE_KIND`, computes the maze framebuffer pixel
    coordinates, issues a VDP-B HMMV with width 8 pixels, fitted row
    height, value 0.
  - Resolves the `COLLISION_ERASE_PENDING` flag via
    `collision_clear_erase_queue` after the DMA.
  - Tile-to-framebuffer-pixel mapping uses the same fitted maze geometry
    as the maze framebuffer asset (`assets/maze_v8_framebuffer.bin`)
    and the maze re-author script (`tools/reauthor_maze_v8.py`).

- Out of scope:
  - Energizer blink (T022 / Phase 8 polish).
  - Maze flash on level clear (T022).
  - Multiple-pellet erase per frame — at one pellet per Pac-Man-move
    frame this is sufficient; if the queue ever grows, expand later.

## Pre-flight

- [x] T025 completed (live tick driving the erase queue).

## Implementation notes

- VDP-B HMMV macros already exist as `VDP_CMD_B_HMMV` in `src/main.asm`.
- Tile (col, row) → framebuffer (x, y) mapping must match the geometry
  used to build `assets/maze_v8_framebuffer.bin`. Reuse the offsets from
  `tools/reauthor_maze_v8.py` and emit a small `assets/tile_to_pixel.bin`
  lookup if needed.
- 27 KB framebuffer spans two banks; the erase target sits in whichever
  bank covers the eaten tile's row.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T029-pellet-erase-to-vdp-b-framebuffer/before_after.ppm`
  — side-by-side VDP-B layer PPM before/after Pac-Man eats a 5-pellet
  horizontal run, with all 5 pellets gone in the after half.
- `tests/evidence/T029-pellet-erase-to-vdp-b-framebuffer/pellet_erase_summary.txt`
  — replay hashes, frame numbers, target tile pixel checks, and
  `COLLISION_PELLET_COUNT` delta.

**Reviewer checklist:**

- [x] Eaten pellets are invisible in the after PPM: target tiles
      `(17,26)` through `(21,26)` have pellet-color pixels
      `[4,2,2,2,2] -> [0,0,0,0,0]`.
- [x] Walls and unrelated pellets are unchanged: control tile `(12,26)`
      remains `6 -> 6` pellet-color pixels.
- [x] Pellet count in `COLLISION_PELLET_COUNT` matches the visible erased
      run: `238 -> 233`, delta `5`.

**Rerun command:**

```
python3 tools/build.py
python3 tools/pellet_erase_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
| 2026-04-29 | Activated as the next Phase 9 integration task. |
| 2026-04-29 | Implemented `pellet_erase_commit`, added replay evidence tooling, and generated VDP-B before/after artifacts. |
