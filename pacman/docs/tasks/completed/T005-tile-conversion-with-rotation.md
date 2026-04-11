# T005 — Tile conversion with 90° rotation

| Field | Value |
|---|---|
| ID | T005 |
| State | completed |
| Phase | 1 Visual |
| Depends on | T004 |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §2, §3.2 |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/02-video.md` §Graphic 4 |

## Goal

Convert the arcade 8×8 tile set (`pacman.5e`) into the Vanguard 8 Graphic 4
tile-bank format, applying the 90° counter-clockwise rotation required by
the chosen landscape presentation. Produce both a binary blob for
`INCBIN` *and* a sanity-check PNG the reviewer can inspect without running
the ROM.

## Scope

In scope:

- Replace the `conv_tiles.py` stub with real logic:
  - Re-use the tile-decoding path from `tools/extract_mame_assets.py`
    (same MAME gfx_layout decoder) to produce 256 × 8×8 × 2bpp tiles.
  - Apply the arcade color-lookup table `82s126.4a` to each tile, but
    only for the CLUT entries the **maze** uses (identified in a short
    authored list at the top of the script — reviewers can audit it).
  - Rotate each tile 90° CCW (so the arcade's vertical maze becomes
    Vanguard 8's landscape maze).
  - Pack each rotated tile into Graphic 4 4bpp format (4 bytes per row,
    32 bytes per tile), mapping arcade CLUT colors to the palette slots
    defined by T004's `slot_map.txt`.
  - Emit `assets/tiles_vdpb.bin` with only the distinct maze tile
    shapes (typically ~50 unique patterns), in a stable order, plus a
    companion `assets/tiles_vdpb.index.txt` mapping each entry to a
    short name (wall_h, wall_v, corner_nw, dot, power, tunnel, etc.).
- Emit a **sanity-check PNG** `tests/evidence/T005-tiles/tile_bank.png`
  showing every converted tile rendered at 4× zoom in the Vanguard 8
  palette, alongside its index label.
- Do **not** yet upload tiles to VRAM or change the runtime render — the
  boot screen stays the T004 palette swatch. Runtime use lands in T006.

Out of scope:

- `tile_nametable.bin` — authored in T006 alongside the maze layout.
- HUD font conversion (T007 uses `conv_hud_font.py`).
- Sprite conversion (T008).

## Implementation notes

Rotation: for a source tile `src[y][x]` (y, x ∈ 0..7), the rotated tile is
`dst[7 - x][y]` (CCW). Do the rotation in the 2bpp planar form and then
repack to 4bpp so the palette mapping happens exactly once per pixel.

De-duplication: hash each rotated, recolored tile's 32 bytes and keep
only the first occurrence. Record the count (expected in the 40–60 range
for maze tiles).

The palette mapping step reads the slot assignment from
`vanguard8_port/assets/src/palette_map.md` (T004 output). If a tile uses
a CLUT color that has no palette slot assignment, fail loudly with a
clear message so T004's slot map can be extended.

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/tests/evidence/T005-tiles/tile_bank.png` — a labeled
  grid of every converted maze tile.
- `vanguard8_port/tests/evidence/T005-tiles/tiles_vdpb.index.txt` —
  copy of the index file produced by the converter.
- `vanguard8_port/tests/evidence/T005-tiles/conversion_log.txt` — stdout
  of `conv_tiles.py` listing: total source tiles, unique maze tiles
  kept, bytes written, any palette-mapping warnings. Current unique tile
  count: `40`; current byte size: `1280`.
- `vanguard8_port/tests/evidence/T005-tiles/build_log.txt` — clean
  `pack_rom.py` regression build log.
- `vanguard8_port/tests/evidence/T005-tiles/t004_regression_log.txt` —
  T004 swatch regression capture. Current frame-60 SHA-256:
  `680738b26715e28175a12855123559974c36e55085cf19bffaf40fcfd22153c9`.

**Reviewer checklist:**

- [ ] `tile_bank.png` contains visually recognizable maze pieces:
      horizontal wall, vertical wall, all four corners, T-junctions,
      dot, power pellet, ghost-house gate, blank corridor
- [ ] Each tile is visibly rotated 90° (a horizontal arcade wall should
      now appear vertical in the PNG — this is correct)
- [ ] Colors in `tile_bank.png` use the T004 palette (blue walls, white
      dots, peach power pellets)
- [ ] `tiles_vdpb.index.txt` has a human-readable name for every tile
- [ ] Tile count in `conversion_log.txt` is between 40 and 60 (sanity
      bound; if outside, investigate before acceptance)
- [ ] No T001–T004 regressions (rerun their commands)

**Rerun command:**

```
cd /home/djglxxii/src/pacman/vanguard8_port && python3 tools/conv_tiles.py
```

## Progress log

- 2026-04-10 — created, state: planned.
- 2026-04-10 — activated after T004 approval. Reviewed the T005 spec,
  `docs/VANGUARD8_PORT_PLAN.md` §3.2, and the existing MAME tile decoder
  before implementing real tile conversion.
- 2026-04-10 — replaced `tools/conv_tiles.py` stub with real conversion:
  MAME 2bpp tile decode, audited maze tile source list, CLUT-to-T004 palette
  mapping, 90° CCW rotation, Graphic 4 4bpp packing, stable dedupe, index
  output, and labeled PNG evidence rendering.
- 2026-04-10 — captured acceptance evidence under
  `vanguard8_port/tests/evidence/T005-tiles/`. Conversion keeps 41 unique
  maze tiles (`1312` bytes), writes `assets/tiles_vdpb.bin` and
  `assets/tiles_vdpb.index.txt`, and renders `tile_bank.png` with blue maze
  walls, white dot, peach power pellet, and gate/blank primitives. Clean
  `pack_rom.py` and T004 swatch regression both pass; T004 frame hash remains
  `680738b26715e28175a12855123559974c36e55085cf19bffaf40fcfd22153c9`.
- 2026-04-10 — approved by human reviewer and ready to move to
  `docs/tasks/completed/`.
- 2026-04-10 — corrected during T006 review after
  `vanguard8_port/tests/evidence/T006-maze/ANALYSIS-maze-distortion.md`
  identified the accepted formula as clockwise. The converter now uses
  `dst[7 - x][y]`, regenerating `tiles_vdpb.bin`, `tiles_vdpb.index.txt`,
  and `tile_bank.png` while preserving the 41-tile / 1312-byte count.
- 2026-04-10 — corrected again during T006 round-two review after
  `vanguard8_port/tests/evidence/T006-maze/ANALYSIS-maze-distortion-round2.md`
  showed that the previous MAME-style tile decode orientation did not match
  the public playfield tile-code grid. `conv_tiles.py` now decodes tiles in
  displayed tile-code orientation before applying the planned CCW rotation.
  The deduped tile bank is now 40 tiles / 1280 bytes, still inside the
  accepted sanity bound.
