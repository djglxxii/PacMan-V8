# T007 — HUD overlay text on VDP-A

| Field | Value |
|---|---|
| ID | T007 |
| State | completed |
| Phase | 1 Visual |
| Depends on | T004, T006 |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §2, §3.4, §4.5, §5.3 |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/02-video.md` §Mixed-Mode Operation, §Graphic 3, §Graphic 3 Layout, §Palette |

## Goal

Render the first upright HUD overlay on VDP-A, composited transparently over
the accepted T006 VDP-B maze. This establishes the foreground layer that later
score, lives, fruit, READY, and GAME OVER updates will mutate during gameplay.

## Scope

In scope:

- Replace the `tools/conv_hud_font.py` stub with a real scripted converter
  that generates `assets/hud_font.bin` from the extracted arcade font tiles
  in `pacman.5e`.
- Include the HUD glyphs needed for the initial overlay: digits `0`-`9`,
  uppercase score text, blank/transparent tile, a small life icon, and one
  fruit placeholder icon if available from the tile set.
- Emit VDP-A Graphic 3 pattern data and color data reproducibly from the
  converter. The font should be upright, not rotated.
- Add a static HUD Pattern Name Table source or generated layout for:
  - left gutter lives/fruit stack in column 0,
  - top-center high-score strip,
  - bottom-center current-score strip on Graphic 3 row 23.
- Upload VDP-A Pattern Name Table, Pattern Generator Table, and Color Table at
  boot using the documented Graphic 3 layout.
- Enable VDP-A display with TP transparency preserved so color index 0 shows
  the VDP-B maze underneath.
- Capture a frame showing the VDP-A HUD composited over the T006 maze.
- Add a small reviewer-readable clearance note measuring or explaining that
  the chosen strips cover only decorative wall/gutter regions from the port
  plan.

Out of scope:

- Dynamic scoring, BCD score math, or score increments. The displayed numbers
  may be fixed boot-time placeholders.
- READY, GAME OVER, credits, or attract-mode text.
- Runtime lives/fruit updates after game-state changes.
- Pac-Man, ghost, fruit gameplay sprites, or sprite SAT uploads.
- Input handling, movement, dot eating, or audio.
- Any changes to the accepted T006 maze layout except what is necessary to
  keep the HUD clearances documented.

## Implementation notes

The current boot path in `vanguard8_port/src/main.asm` already configures
VDP-B as Graphic 4 and VDP-A as Graphic 3 with `R#8` TP set. T006 leaves VDP-A
display disabled; this task should populate VDP-A VRAM first, then turn on
VDP-A display without disturbing the accepted VDP-B maze render.

Use the fixed Graphic 3 layout from the Vanguard 8 video spec:

- `0x0000-0x02FF`: Pattern Name Table, 32x24 tile indices.
- `0x0300-0x17FF`: Pattern Generator Table, three 2 KB banks.
- `0x1800-0x2FFF`: Color Table, three 2 KB banks.
- `0x4200`: Sprite Attribute Table sentinel remains present so VDP-A sprites
  stay disabled for this task.

Because Graphic 3 fetches a 32x24 tile map for visible lines `0-191` and
outputs backdrop color for lines `192-211`, the bottom score strip belongs on
row 23, not in the final 20 physical scanlines. Do not add vertical scrolling
or line-timing tricks in this task.

For Graphic 3, duplicate the HUD glyph patterns and colors into all three
pattern/color banks unless the implementation proves the exact bank addressing
for each HUD row and writes only the required bank slices. Color index 0 must
remain transparent on VDP-A; glyph foreground should use the HUD white palette
slot from T004. Keep the left gutter within column 0 so it remains outside the
240 px VDP-B maze render.

The converter should fail loudly if required source files are missing or if a
requested glyph cannot be resolved. If a full arcade font tile mapping is not
yet practical, keep the initial mapping deliberately small and document the
tile IDs used inside `conv_hud_font.py` or an authored source file under
`assets/src/`.

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/tests/evidence/T007-hud/hud.png` — captured frame showing
  the static VDP-A HUD overlay composited over the T006 maze.
- `vanguard8_port/tests/evidence/T007-hud/frame_hash.txt` — frame-60 hash for
  regression detection:
  `e6b639078704ea947698db8581975923507519d6aef89d3dbb652cdc8cd65069`.
- `vanguard8_port/tests/evidence/T007-hud/hud_clearance.txt` — reviewer note
  identifying the exact HUD tile cells used and why they do not cover active
  dots, pellets, ghost-house tiles, or corridors.
- `vanguard8_port/tests/evidence/T007-hud/rerun_log.txt` — clean build and
  headless capture log.
- `vanguard8_port/tests/evidence/T007-hud/font_manifest.txt` — generated or
  copied manifest listing the HUD glyphs, tile indices, and output byte sizes.

**Reviewer checklist:**

- [ ] `hud.png` shows the T006 maze unchanged on VDP-B with upright HUD text
      visible above it from VDP-A.
- [ ] VDP-A transparency works: the maze shows through all unused HUD tiles,
      with no opaque black rectangle covering the playfield.
- [ ] HIGH SCORE and current SCORE text are readable and horizontally centered
      in their planned strips.
- [ ] Lives/fruit placeholders appear in the left gutter and do not intrude
      into the maze bitmap.
- [ ] `hud_clearance.txt` lists the occupied tile cells and confirms the
      overlay covers only decorative wall/gutter regions.
- [ ] T006 maze data has not regressed: `check_maze_layout.py` still passes
      and the T006 converter still reports 40 unique maze tiles plus a 27,136
      byte static maze framebuffer. The final full-frame hash is expected to
      differ from T006 because VDP-A is now visible.

**Rerun command:**

```
cd /home/djglxxii/src/pacman/vanguard8_port && rm -rf build && python3 tools/pack_rom.py && \
  /home/djglxxii/src/Vanguard8/build/src/vanguard8_headless \
    --rom build/pacman.rom --frames 60 \
    --dump-frame tests/evidence/T007-hud/hud.ppm \
    --hash-frame 60
```

## Progress log

- 2026-04-13 — created, state: planned.
- 2026-04-13 — activated after user approval. Reviewed T007 scope,
  `docs/VANGUARD8_PORT_PLAN.md` HUD sections, current T006 boot path, and
  Vanguard 8 Graphic 3 compositing constraints before implementation.
- 2026-04-13 — implemented `tools/conv_hud_font.py` as a compact scripted
  HUD converter from `pacman.5e`, generating `hud_font.bin` and
  `hud_font_manifest.txt`; added VDP-A Graphic 3 name/pattern/color uploads
  and enabled the transparent overlay at boot.
- 2026-04-13 — fixed a VDP helper macro bug where parenthesized R#14 address
  expressions assembled as memory loads instead of immediates. This made
  targeted VDP-A table uploads land on the intended VRAM pages.
- 2026-04-13 — captured T007 evidence under
  `vanguard8_port/tests/evidence/T007-hud/`; frame-60 hash is
  `e6b639078704ea947698db8581975923507519d6aef89d3dbb652cdc8cd65069`.
  `python3 tools/check_maze_layout.py` still reports 576 wall seams checked,
  16 known arcade seam exceptions, and 0 unexpected mismatches.
- 2026-04-13 — approved by human reviewer and moved to completed.

## Blocker (only if state = blocked)

- **Blocking system:** n/a
- **Symptom:** n/a
- **Minimal repro:** n/a
- **Resolution needed:** n/a
