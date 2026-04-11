# T006 Maze Distortion — Root-Cause Analysis

Inspection target: `vanguard8_port/tests/evidence/T006-maze/maze.png`

## Observed symptom

The maze renders with the correct overall silhouette (outer border,
ghost-house box in the middle with its gate, power pellets in the corners,
dots in expected rows), but the interior walls look fragmented and the
corridors do not connect cleanly. As the reviewer noted, the tile **art
itself is not corrupt** — individual wall pieces draw correctly — but the
maze is not traversable because wall pieces meet at the wrong orientations.

The issue is in how `vanguard8_port/tools/conv_tiles.py` rotates and picks
tiles, not in how the framebuffer is streamed to VDP-B.

---

## Finding 1 — `rotate_ccw` actually rotates 90° **clockwise**

File: `vanguard8_port/tools/conv_tiles.py:132`

```python
def rotate_ccw(tile: list[list[int]]) -> list[list[int]]:
    rotated = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
    for y in range(TILE_HEIGHT):
        for x in range(TILE_WIDTH):
            rotated[x][7 - y] = tile[y][x]
    return rotated
```

The mapping `rotated[x][7 - y] = tile[y][x]` is the formula for a 90°
**clockwise** rotation. Verified empirically: a single pixel at source
`(y=0, x=0)` (top-left) lands at `(y=0, x=7)` (top-right) — which is where
CW rotation sends it. A true CCW rotation would send it to `(y=7, x=0)`
(bottom-left). The correct CCW formula is:

```python
rotated[7 - x][y] = tile[y][x]
```

### Why this matters for T006

The T006 task file is explicit: *"The port plan rotates the game world 90°
counter-clockwise: the arcade 28×30 active maze becomes a 30×28 tile
landscape playfield."* (`docs/tasks/active/T006-static-maze-render-on-vdp-b.md:46-48`)

So the plan specifies CCW, but the tile converter applies CW. Every maze
tile ends up mirrored through a 180° rotation relative to what the port
plan assumed. In isolation, a single 90° rotation direction is arbitrary —
what matters is that the **tile orientation and the authored layout
orientation agree**. They do not here:

- `assets/src/maze_layout.txt` was clearly authored as "the arcade maze
  rotated CCW into landscape" (e.g. the ghost-house door sits on the top
  of the ghost box, with 30 columns × 28 rows — what CCW rotation of the
  arcade 28×30 playfield would produce).
- The tile pixels are rotated CW, so each tile's interior geometry is
  flipped end-for-end relative to that layout.

The net effect is that wall pieces technically carry the correct
**edge-mask label** (because `edge_mask()` is recomputed *after* rotation)
but their **interior pixel paths point the wrong way**, so corridors and
junctions don't line up with neighboring tiles when placed in the layout.

---

## Finding 2 — `edge_mask` is too coarse a signature to pick junction tiles

File: `vanguard8_port/tools/conv_tiles.py:170-176`, `299-317`

`edge_mask()` returns a 4-bit N/E/S/W signature based solely on whether
*any* pixel exists on each edge of the rotated tile. `choose_wall_tile()`
then picks the **first** tile whose name ends in that mask:

```python
for name, index in name_to_index.items():
    if name.endswith(f"_{mask}"):
        return index
```

This has three independent failure modes even once Finding 1 is fixed:

1. **Multiple distinct tiles share the same mask.** The index shows 11
   different source tiles all labelled `nesw` (`d0, d1, d4, d5, d6, d7,
   d8, d9, f2, f3, f4, f5, fa, fb`). These are a cross, a T, a filled
   block, rounded-corner variants, etc. — visually very different, but
   indistinguishable to `edge_mask`. The first one inserted wins, and
   because insertion order follows `MAZE_GEOMETRY_TILE_IDS` (`0xC0..0xFF`),
   every four-way cell picks `maze_wall_d0_nesw`, which is the **solid
   block** piece. That is why every four-wall junction in `maze.png`
   renders as a fat solid square instead of a maze corner.

2. **Mask says "an edge has pixels", not "the wall connects to that
   edge".** Arcade Pac-Man tiles encode the wall as a thin double-pipe
   that runs inside the tile with decorative end-caps. A tile can have
   pixels touching its east edge because a decorative cap extends there,
   while the interior pipe actually curves away. `edge_mask` treats these
   identically, so mask-driven matching routinely picks tiles whose
   interior geometry does not connect to the neighbor it was placed
   against.

3. **Mask ignores diagonals.** Pac-Man walls are double-wall tiles; the
   correct tile at a cell depends not only on its four orthogonal
   neighbors but also on its four diagonal neighbors (e.g. an outside
   corner vs an inside corner share the same N/E/S/W mask but differ at
   the NE/NW/SE/SW diagonal). The picker cannot distinguish them.

The checklist already hedges on this (*"Wall-junction tile choices are
approximate"*), but the combination of Finding 1 and Finding 2 is what
pushes the result from "approximate junctions" to "does not look
traversable".

---

## Finding 3 — Layout authoring style doesn't carry enough information

File: `vanguard8_port/assets/src/maze_layout.txt`

The layout uses a single `#` glyph for all walls and leans on
`choose_wall_tile()` to disambiguate. Given Finding 2, that disambiguation
is not solvable from orthogonal adjacency alone for Pac-Man's double-wall
style. The layout needs to carry more information — either:

- a per-cell tile index (skip tile picking entirely), or
- a richer glyph set that distinguishes outer corners, inner corners,
  straight runs, T-junctions in each orientation, and the ghost-house
  walls (which are a separate art set from the outer maze walls).

---

## Suggested fixes, in priority order

### Fix A (required) — correct the rotation direction

In `conv_tiles.py:132`, replace:

```python
rotated[x][7 - y] = tile[y][x]
```

with:

```python
rotated[7 - x][y] = tile[y][x]
```

Or, equivalently, use `list(zip(*tile))[::-1]` (rows of the CCW-rotated
tile). After this change, `edge_mask` still produces consistent labels
because it reads the rotated tile, so the tile-index file will change
(masks will differ) but `choose_wall_tile` will stay internally
consistent. The layout file requires no change.

Re-run `python3 tools/conv_tiles.py` and compare `tile_bank.png` against
the arcade maze tile sheet to confirm the orientation matches the
authored layout.

### Fix B (required) — pick tiles by identity, not by edge mask

Replace the mask-based picker with an explicit per-cell tile selection.
Two practical options:

**B1. Author the nametable directly.** Change `maze_layout.txt` from a
glyph grid into a grid of tile-bank indices (or symbolic names like
`e0`, `f2`, …). `conv_tiles.py` then just looks each cell up in
`name_to_index` and writes it into the framebuffer. This is the most
reliable option and eliminates tile-picking logic entirely. It is more
verbose to edit but the task is a one-shot authoring exercise.

**B2. Keep the glyph grid but expand the glyph set and hand-map each
glyph to a specific tile.** E.g. use `┌┐└┘─│├┤┬┴┼` (or ASCII equivalents
like `r, 7, L, J, -, |, …`) and maintain a small `GLYPH_TO_TILE` table
in `conv_tiles.py`. Easier to tweak visually than B1, still deterministic.

Either option should drop `choose_wall_tile` and `edge_mask` entirely
for layout selection. `edge_mask` can stay as a debug label on the tile
index, but it should not drive rendering.

### Fix C (optional, defer) — separate ghost-house wall set

The ghost-house box in arcade Pac-Man uses a different art set from the
outer maze walls (lighter color, different corner radius). Once Fixes A
and B are in, a follow-up can add those sources to the T005 tile bank
and reference them explicitly in the layout.

---

## Suggested verification after fix

1. Rerun `python3 tools/conv_tiles.py`; inspect the new `tile_bank.png`
   and confirm horizontal walls look horizontal, vertical walls look
   vertical, and corners point the way the authored layout expects.
2. Rebuild and capture a new `maze.png` via the T006 rerun command.
3. Walk the maze visually: every corridor should form a continuous
   traversable path with no solid blocks in the middle of a corridor
   and no wall fragments leaving gaps at junctions.
4. Keep the current `frame_hash.txt` as a "before" reference and record
   the new hash alongside it; the T006 task file's accepted hash will
   need to be updated once the reviewer signs off on the fix.
