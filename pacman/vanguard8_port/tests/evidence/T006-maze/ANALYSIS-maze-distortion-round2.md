# T006 Maze Distortion — Round 2 Analysis

Round 1 fixed the rotation direction and switched from mask-based picking
to an explicit tile grid. Both fixes landed correctly. The maze is still
wrong, but for a different reason than before.

## What the fixes confirmed

- `conv_tiles.py:132` now performs a true 90° CCW rotation (`rotated[7-x][y] = tile[y][x]`).
- `assets/src/maze_layout.txt` is now a 30×28 grid of explicit tile IDs, so
  `choose_wall_tile`/`edge_mask` is no longer in the selection path.
- The new `tile_bank.png` shows rotated tiles with consistent edge-mask
  labels.

## What's still wrong

The authored layout picks tile IDs **by reading the edge-mask labels in
`tiles_vdpb.index.txt`**, assuming those labels describe the *shape* of
the tile. They do not — they only describe which 1-pixel edges have any
pixels at all. When I dumped the actual pixel content, the supposed
"corner" and "border" tiles turn out to be filled triangular wedges that
were never designed to form a thin outline wall.

### Concrete proof — the top border

Layout row 0 reads:

```
e3 ce ce ce ce ce … ce ce dc dc ce ce … ce ce e2
```

The layout author read `e3` as "nw → top-left corner" and `ce` as
"ew → horizontal wall piece". Let's look at the actual CCW-rotated pixels:

**`ce` (labelled `ew`) — does form a clean horizontal line:**

```
........
########
########
........
........
........
........
........
```

Rows 1–2 are a full-width horizontal stripe. Two adjacent `ce` tiles
produce a continuous horizontal rail at y=1..2. Good.

**`e3` (labelled `nw`) — is a triangular wedge, NOT a corner piece:**

```
#######.
#######.
######..
####....
........
........
........
........
```

It's a solid fill packed into the top-left of the tile, tapering out
toward the middle. Its right edge (col 7) is **empty on every row**.

Put `e3` immediately left of `ce` and the rails do not meet:

```
e3 right edge      ce left edge
col 6 | col 7    col 0 | col 1
row 0:  #  |  .     .  |  .    <- e3 has wall here, ce doesn't
row 1:  #  |  .     #  |  #    <- GAP: e3 col 7 empty, ce col 0 filled
row 2:  #  |  .     #  |  #    <- GAP
row 3:  .  |  .     .  |  .
```

There is a 1-pixel dead column between the corner wedge and the first
horizontal-rail tile. That gap is what's producing the broken,
fragmented look across the maze — it appears at **every** place a "corner"
meets a "straight" in the current layout, because the arcade corner
tiles were never designed to hand off a 2-pixel-thick rail at rows 1–2
to `ce`.

### Why mix-and-match is fundamentally broken here

The same experiment on `e1`, `e2`, `e0`, `d2`, `d3`, `da`, `dc`:

- `e0`/`e1`/`e2`/`e3` are all triangular wedge fills, one per corner of
  the 8×8 cell. They are **inside-corner fills**, meant to live at the
  concave inner corner of an arcade double-wall — not on a border rail.
- `d2` (CCW) is a left-half rectangular fill (cols 0–3), not a "top wall".
- `d3` (CCW) is a right-half rectangular fill (cols 4–7).
- `ce` (CCW) is the rails-at-rows-1-2 piece — only this one is a
  continuous line segment in this direction.

Arcade Pac-Man walls are *double* walls: a thin outer rail and a thin
inner rail with a gap between. Each curve, elbow, T, and cap is a
specific tile drawn so it connects to **specific neighbors in specific
positions**. The asymmetry is baked into the pixel art — the tiles
assume they'll be placed in the arcade's exact layout. They are not
general-purpose "line primitives" you can freely recombine.

The edge-mask label (e.g. `nw`) only tells you *any* pixel touches the
north and west edges. It doesn't tell you *which row*, *how thick*, or
*whether the shape actually connects through the tile*. That's why
hand-picking by label produces a maze where every junction misses.

## Suggested fixes, in priority order

### Fix D (recommended) — copy the arcade's own tile placement

The arcade's tiles *do* form a clean maze — when placed in exactly the
positions the arcade uses. The fastest way to get a traversable maze is
to reproduce the arcade's tile-ID grid and rotate it 90° CCW into the
port's coordinate system. The tile art is already paid for; use it as
designed.

Clean-room-legal ways to obtain the arcade tile grid (these are data
observations, not code):

1. **MAME tilemap viewer.** Boot `pacman` in MAME, pause on the
   attract-mode maze (or the start of a life), open the tilemap viewer
   (`F4`), and transcribe the 28×36 grid of tile IDs. MAME's viewer
   lets you click a tile to see its hex index. This reads VRAM state,
   not ROM code.
2. **Screenshot + tile-bank lookup.** Take a lossless PNG capture of the
   attract-mode maze. Slice it into 8×8 blocks. For each block, match
   its pixels against the decoded tile bank to recover the tile ID.
   This is a purely mechanical image-comparison over the generated
   `tile_bank.png` — write it as a tool under `vanguard8_port/tools/`
   so it's reproducible. No arcade code is read.
3. **Published maze diagrams.** The tile-ID-per-cell map is documented
   in public fan references (maze disassemblies/atlases). Cite the
   reference in `maze_layout.txt` and transcribe.

Once you have the 28×36 arcade tile-ID grid, rotate it 90° CCW in the
converter (or author it pre-rotated as a 36×28 grid) and drop it in as
`maze_layout.txt`. Because every tile sits in a position identical to
the arcade (modulo rotation), the pixel rails will line up by
construction. No hand-matching required.

Note on grid size: the arcade playfield is 28×36 including the score/HUD
rows. The current 30×28 layout truncates; after Fix D the layout should
be the full 36×28 (CCW of 28×36), and the existing 256×212 framebuffer
clip already accounts for this — the plan file says so.

### Fix E (alternative) — author a fresh wall tileset

If the goal is a clean-room landscape maze rather than a rotation of the
arcade, the arcade wall tiles cannot be reused for walls. Author a small
set of landscape-native wall primitives (straight, corner, T, cross)
under `assets/src/` and convert them through `conv_tiles.py` alongside
the existing maze assets. Keep using the arcade dots, pellets, and
ghost-house gate since those are rotationally symmetric enough. This is
strictly more work than Fix D and also diverges from the port plan's
"preserve the arcade maze" intent, so prefer Fix D unless the team
explicitly wants an original design.

### Fix F (not recommended) — keep hand-picking but verify by adjacency

You could keep the current "pick per cell by eye" approach but
additionally check every pair of neighbors for pixel continuity. This
is tractable as a linter (`for each horizontal pair, assert
left_tile[:, 7] == right_tile[:, 0]` — similar for vertical pairs), but
no hand-picked assignment of the arcade tiles to a non-arcade layout
will actually satisfy that lint, because the arcade tile set doesn't
contain the general-purpose connectors you'd need. Use this lint only
as a regression check *after* Fix D lands.

## Verification plan once a fix is applied

1. Rerun `python3 tools/conv_tiles.py` and the headless capture.
2. Write a small Python check that walks the generated `tile_nametable.bin`
   and asserts, for every pair of adjacent tiles, that the right-edge
   column of the left tile equals the left-edge column of the right
   tile (and symmetrically for vertical neighbors). Store the check
   under `vanguard8_port/tools/` and run it as part of the T006 build.
   This converts "does the maze look traversable" from a human judgment
   into a deterministic test.
3. Re-capture `maze.png` and visually confirm: every corridor forms a
   continuous path, corners curve smoothly, and the ghost-house gate is
   intact.
