# Pac-Man → Vanguard 8 Port Plan

A plan for building a Pac-Man cartridge for the Vanguard 8 fantasy console,
reusing graphics and audio waveforms already extracted from the MAME ROM set
in `extracted/`. The port preserves arcade **gameplay** exactly (ghost AI,
frame rules, audio character); the **visual presentation deviates** from the
arcade because the Vanguard 8's landscape framebuffer cannot host the arcade's
portrait playfield pixel-for-pixel. See §2 for the chosen display compromise.

Target hardware reference: `/home/djglxxii/src/Vanguard8/docs/spec/`
(00-overview, 01-cpu, 02-video, 03-audio, 04-io).

This document is the architectural source of truth. Execution is driven by
the task queue in `docs/tasks/` — see `docs/tasks/README.md` for workflow
and `docs/tasks/INDEX.md` for the master task list. Every task references
a section of this plan; if a task discovers a plan deviation is needed,
update this document first.

Agent operating rules live in `CLAUDE.md` at the repo root.

---

## 1. Scope and Philosophy

**Goal.** Ship a cartridge whose **gameplay** is authentic Pac-Man: Pac-Man
movement and cornering, dot/energizer placement in a maze that matches the
arcade's topology, ghost personalities (Blinky, Pinky, Inky, Clyde),
scatter/chase timing, Cruise Elroy escalation, fruit spawns, bonus life at
10 000, intermission cutscenes, and the "wakka-wakka" chomp / siren / death
jingle. A player who knows arcade Pac-Man strategy should find every
strategy still works.

**Non-goal.** Pixel-perfect visual parity with the arcade. The arcade
playfield is 224×288 portrait; the Vanguard 8 is 256×212 landscape. No
rotation and no sub-pixel scaling makes that fit. We explicitly accept the
following visual deviations — their rationale is in §2:

- The maze is rendered rotated 90° CCW while sprites and HUD stay upright in
  landscape screen-space (so the player sees Pac-Man and the ghosts in their
  familiar orientation on a rotated maze).
- The outermost ~18 px of the arcade maze's tunnel border is clipped at the
  top and bottom of the landscape framebuffer (decorative wall only, no
  dots/pellets lost).
- Lives and fruit are stacked vertically in a left-side gutter rather than
  displayed horizontally along the bottom.
- Score and HIGH SCORE text are overlaid across the center-top and
  center-bottom of the maze, in regions that the rotation leaves free of
  dots, pellets, and the ghost house.
- The current maze layout is a 30×28 clean-room **approximation** of the
  rotated arcade tilemap, not a 1:1 rotation. It is visually very close to
  the arcade and preserves the traversal graph; exact-tile fidelity may be
  revisited in a later polish task if it is ever needed, but it is not
  required for gameplay authenticity.

**What we reuse.** Only the *data* that is already decoded and sitting in
`extracted/`:

- `tiles_raw.png` — 256 × 8×8 tiles (maze pieces, digits, letters, "HIGH SCORE")
- `sprites_raw.png` — 64 × 16×16 sprites (Pac-Man frames, 4 ghost frames × 4
  directions, frightened / eyes ghost, fruit, death animation)
- `palette.png` + `82s123.7f` decode — the 16 used colors from the 32-entry master
- `82s126.4a` → 64-entry color-lookup table assigning 4 palette indices to each
  tile/sprite
- `waveform_0..7.wav` + `82s126.1m` → the 8 × 32-sample × 4-bit WSG wavetables
  (sine, two harmonic variants, pulse stacks, triangle, square)

**What we do NOT reuse.** The Z80 game code in `pacman.6[efhj]`. It is written
against a custom TTL video system with memory-mapped tile/sprite RAM, IM2
interrupts vectored from the sound board, and a custom WSG chip — none of which
exist on the Vanguard 8. Beyond the technical mismatch, the copyrighted game
code is replaced with a **clean-room reimplementation** driven entirely from
published Pac-Man behavior documentation (ghost targeting tables, frame rules,
scatter/chase durations, dot-counter release, Elroy thresholds, etc. — the
*Pac-Man Dossier* style of spec). The extracted art and wavetables are raw data
assets that we convert to Vanguard 8 native formats, not executable code.

---

## 2. Display Mapping — the Resolution Problem

Arcade Pac-Man is a vertical (tate) game: 224 × 288 pixels = 28 × 36 tiles.
The arcade playfield is organized as:

```
rows  0–1      top score strip (1UP / HIGH SCORE / 2UP)
rows  2        blank
rows  3–32     active maze (28 × 30 tiles = 224 × 240)
rows  33       blank
rows  34–35    bottom strip (lives + fruit carousel)
```

Vanguard 8 Graphic 4 is **256 × 212 landscape**. No orientation fits the
full arcade display pixel-for-pixel:

| Strategy | Fits? | Verdict |
|---|---|---|
| Upright, native 224×288 | 288 > 212 vertical | no |
| Rotated 90° landscape, full arcade tilemap 288×224 | 288 > 256, 224 > 212 | no |
| Uniform downscale (×0.74) | yes | destroys 8×8 tile crispness |
| **Rotated maze with upright sprites/HUD, clipped outer border, HUD overlay** | **yes** | **chosen** |

### Chosen approach: rotated maze, upright sprites and HUD, overlaid HUD

We rotate the **maze geometry** 90° counter-clockwise while keeping the
**sprites (Pac-Man, ghosts, fruit) and HUD text upright** in the landscape
screen's coordinate system. The player sees familiar upright sprites
navigating a rotated maze. Directional input from the controller maps
directly to on-screen motion; the game logic translates between landscape
screen-space and the rotated maze's internal coordinates.

**Playfield bitmap (VDP-B, Graphic 4, 256×212, 4bpp):**

- The active maze is authored as a **30×28 clean-room landscape grid**
  (`assets/src/maze_layout.txt`), rotated CCW from the arcade 28×30
  playfield. That grid packs to 240×224 px; it is centered horizontally
  with an 8 px gutter on the right and an 8 px gutter on the left (the
  left gutter hosts HUD — see below).
- The top/bottom 6 px of the 224-tall rotated maze are clipped to fit
  212 vertical lines. These clipped rows are the arcade's outer
  left-right border (after rotation), which is pure decorative wall
  with no dots, pellets, ghost-house tiles, or gameplay logic. The
  tunnel wrap still works because it is gameplay-coordinate logic, not
  pixel rendering.
- The current layout is a clean-room approximation, not a literal
  rotation of the arcade tilemap. See §4.1 for the authoring rationale.

**Sprites (both VDPs, Sprite Mode 2):**

- Pac-Man, ghosts, fruit, and the death-animation frames are drawn
  upright in landscape screen-space, exactly as the player would
  intuitively expect. No per-frame rotation of sprite art.
- Sprite world-position is stored in rotated maze coordinates; a single
  transform converts to landscape screen pixels at SAT commit time.
- Controller input is read as landscape directions (up/down/left/right
  relative to the display) and transformed into maze-local directions
  before the movement routine consults the maze walkability bitmap.

**HUD layout:**

The HUD is split into three thin overlays whose placement was chosen so
that each overlay covers only arcade wall pixels after rotation — no
dots, no power pellets, no ghost-house tiles are occluded:

1. **Left gutter — lives and fruit, stacked vertically.** An 8 px-wide
   column along the left edge of the framebuffer. Remaining Pac-Man
   lives are stacked top-to-bottom as 8×8 life icons; the current-level
   fruit icon is drawn below the lives. This gutter is outside the
   240 px maze render, so it occludes nothing.
2. **Top-center strip — HIGH SCORE text.** A short horizontal text
   strip centered along the very top row of the maze, at the
   midpoint above the ghost-house column. After CCW rotation, this
   region maps to the arcade's right-side outer border at mid-height —
   pure decorative wall, no dots or pellets, no ghost-house tiles.
3. **Bottom-center strip — current SCORE text.** Same treatment as the
   high-score strip but centered along the very bottom row of the
   maze. After rotation, this maps to the arcade's left-side outer
   border at mid-height — again pure decorative wall.

HUD overlay is handled by **VDP-A in Graphic 3** with transparent
background (palette slot 0, TP=1), composited over VDP-B. Score and
high-score digits are written as Pattern Name Table entries during
VBlank; lives/fruit are updated only when they change. The exact pixel
clearance for each strip is measured and pinned in the T007 HUD task.

### Why not single-VDP?

We could put everything on VDP-A in Graphic 4 and software-composite the HUD.
That works but:

1. We lose the HUD-over-game priority stacking that VDP-A → VDP-B gives for
   free.
2. Writing score digits means rewriting playfield bitmap bytes every frame,
   fighting the blitter instead of letting the hardware do it.
3. Using VDP-A for tile-mode HUD and VDP-B for bitmap playfield exercises the
   documented mixed-mode compositing path (`docs/spec/02-video.md`
   §Mixed-Mode Operation), which is a covered feature.

### Why rotated maze with upright sprites?

The alternative — rotating the entire display including sprites — makes
Pac-Man and the ghosts move "sideways" on screen and forces the player to
mentally rotate the game, which is a significant UX regression. Rotating
only the maze keeps sprite orientation, HUD reading direction, and
controller mapping all in landscape screen-space, which is how the player
naturally interprets a landscape display. The price is a small transform
between screen-space and maze-space in the movement code, which is cheap.

---

## 3. Asset Pipeline

All conversion is scripted; the extracted artifacts in `extracted/` are inputs,
and the outputs land in a new `vanguard8_port/assets/` tree ready to be
`INCBIN`-ed from assembly.

### 3.1 Palette

- Decode `82s123.7f` → 32 RGB triplets (already done by `extract.py`).
- Only 16 colors are non-black. Pack the 16 used colors into **VDP-B palette
  slots 0–15** (slot 0 = transparent/black maze background, 1 = maze blue,
  2 = Pac-Man yellow, 3 = Blinky red, 4 = Pinky pink, 5 = Inky cyan,
  6 = Clyde orange, 7 = frightened blue, 8 = frightened white, 9 = dot peach,
  10 = cherry red, 11 = fruit stem green, 12 = HUD white, 13/14/15 reserved).
- VDP-A palette mirrors VDP-B for consistency but slot 0 must be transparent
  (color 0, TP=1) so compositing works.
- Palette is written at boot via port 0x82 (VDP-A) / 0x86 (VDP-B). Convert each
  RGB triplet into the V9938 9-bit RGB form (`R:3 G:3 B:3`) with nearest-color
  quantization; the arcade's resistor-weighted palette maps cleanly into the
  512-color space with negligible error.

### 3.2 Tile set (VDP-B, Graphic 4 blitter source)

- Input: 256 × 8×8 tiles from `pacman.5e`.
- For each arcade CLUT entry used by maze tiles, pre-render that tile with
  that palette into the Vanguard 8's 4bpp packed format (4 bytes per row,
  32 bytes per 8×8 tile).
- Maze tiles actually used: ~50 unique silhouettes (walls, dots, energizers,
  tunnel, letters, digits). Store these in a **tile-bank region of VDP-B
  VRAM** at `0x7D00–0xFFFF` (~33 KB available per the Graphic 4 recommended
  layout), as HMMM blitter source rectangles.
- Blit to the active framebuffer at boot and whenever a dot is eaten (single
  tile overwrite with the "empty corridor" tile).
- Rotation: the 90° rotation is baked into the source data by rotating each
  tile bitmap during conversion, so the playfield renderer can stamp tiles
  in their natural landscape orientation without per-pixel rotation at runtime.

### 3.3 Sprites (VDP-B, Sprite Mode 2)

Sprites are **not rotated**. Per §2, Pac-Man, the ghosts, and the fruit are
drawn upright in landscape screen-space while only the maze geometry is
rotated. The sprite converter therefore emits arcade sprite frames in their
original orientation; only the maze-to-screen coordinate transform (applied
at SAT commit time) is rotation-aware.

- Input: 64 × 16×16 sprites from `pacman.5f`.
- Sprite Mode 2 stores a 1-bit pattern and a 16-entry row-color table per
  sprite. Convert each 2bpp arcade sprite into 16 bytes of pattern (one row
  per byte, using "opaque = any non-zero plane value") plus a 16-byte row
  color table derived from the dominant non-zero plane value per row. For
  sprites that need the full 4 colors per row (e.g. ghost eyes over body),
  split into **two overlaid sprites**: an outline/body sprite and a detail
  sprite (eyes/pupils). Pac-Man sprites already come in multi-layer form in
  the arcade hardware's CLUT, so this mapping is natural.
- Sprites used per frame (maximum 7): Pac-Man, Blinky, Pinky, Inky, Clyde,
  fruit, + one extra ghost detail sprite. All 7 fit within the 8-per-scanline
  budget of a single VDP-B Sprite Mode 2. The second-layer ghost eye sprites
  bring us to 11 — above the 8/line limit on a single chip, so **ghost eye
  sprites are rendered on VDP-A instead**, exploiting the 8 + 8 = 16
  sprites-per-scanline total (`docs/spec/02-video.md` §Per-Chip Sprite Limits).
- Sprite pattern table: VDP-B `0x7000–0x77FF`. Sprite color table (Mode 2):
  auto-placed at `0x7A00`. SAT at `0x7C00`.
- The death animation (11 frames) and frightened ghost blink (2 frames) are
  just additional pattern entries; we have room for all 64 patterns + room
  to spare.

### 3.4 HUD tile set (VDP-A, Graphic 3)

- Font comes from the same `pacman.5e` ROM: digits 0–9, letters A–Z,
  "UP", "HIGH SCORE", "CREDIT", "READY!", "GAME OVER". These are the
  actual arcade font tiles, in their original 8×8 form (no rotation —
  HUD text is drawn upright, see §2).
- Stored in VDP-A's Pattern Generator Table at `0x0300`.
- HUD Pattern Name Table at `0x0000` defines a 32×24 layout. Populated
  cells (per §2):
  - Leftmost column (col 0): vertically-stacked life icons and fruit
    icon.
  - Top-center cells (row 0, cols ~11–21): HIGH SCORE text and digits.
  - Bottom-center cells (row 23, cols ~11–21): current SCORE digits.
  - All other cells are pattern 0 (transparent) so VDP-B shows through.
- Lives and fruit are stored as additional font-style tile entries in
  the same pattern generator table; they are scaled/shaped to fit the
  8×8 grid rather than using 16×16 sprites, so the HUD is a single
  tile-mode layer with no sprite contention against gameplay sprites.

### 3.5 Audio — waveforms and sequences

The Namco WSG is a 3-voice wavetable synthesizer with 4-bit samples and a
20-bit phase accumulator. We reproduce it on the Vanguard 8's audio chips:

- **Wavetable voices 1 + 2** (Pac-Man melody lines: intro jingle, death
  jingle, extra-life chime): YM2151 channels 0–1 in a **custom-waveform
  algorithm**. Strategy A (preferred): use YM2151 algorithm 7 (all operators
  parallel) with detunes chosen to approximate each arcade waveform's
  harmonic content — this gives us the characteristic "chiptune" sound
  without literally streaming samples. Strategy B (fallback): stream each
  32-sample wavetable as ADPCM through MSM5205 in a loop, retriggered per
  note, with pitch controlled by changing the ADPCM sample-rate select.
- **WSG voice 3** (the siren, pellet chomp, ghost-eaten warble): AY-3-8910
  channel A with envelope + tone. The chomp is a short pitch sweep that the
  AY's envelope generator handles cleanly.
- **Frightened-mode siren**: AY-3-8910 noise + tone, same role as arcade
  voice 3 in frightened mode.
- **Ghost-eaten / bonus-score SFX**: single-shot ADPCM through MSM5205,
  re-encoding the arcade voice 3 output as 4 kHz ADPCM.

Sequencing uses YM2151 Timer A as the tempo clock (`docs/spec/03-audio.md`),
firing INT0 on YM2151 /IRQ; the wire-ORed INT0 handler dispatches on the
YM2151 status byte to the music tick routine. This is the documented
Vanguard 8 pattern for audio sequencers.

Conversion tool: `vanguard8_port/tools/conv_audio.py` — reads `82s126.1m`,
computes harmonic profiles of each 32-sample wavetable, and emits YM2151
operator parameter tables + per-note frequency tables. Produces
`assets/audio/wsg_instruments.bin` and `assets/audio/music_data.bin`.

### 3.6 Conversion tool layout

```
vanguard8_port/
  tools/
    conv_palette.py       # 82s123.7f → v9938 palette init blob
    conv_tiles.py         # 5e + CLUT + rotation → tile bank + name table
    conv_sprites.py       # 5f + CLUT → pattern + color tables
    conv_hud_font.py      # 5e subset → Graphic 3 pattern generator
    conv_audio.py         # 82s126.1m → YM2151/AY/ADPCM instrument banks
    pack_rom.py           # assemble + pad to 16 KB page boundary
  assets/
    palette_a.bin
    palette_b.bin
    tiles_vdpb.bin
    tile_nametable.bin
    sprites_patterns.bin
    sprites_colors.bin
    hud_font.bin
    wsg_instruments.bin
    music_data.bin
    maze_layout.bin       # authored, see §4.1
  src/
    main.asm              # entry, MMU/VDP/audio init, main loop
    vdp.inc               # VDP-A/VDP-B helper macros (copied from showcase)
    maze.asm              # maze state, dot counters, fruit scheduler
    pacman.asm            # player input + movement
    ghost.asm             # ghost AI (§5)
    ghost_targets.asm     # per-personality targeting tables
    collision.asm         # tile & sprite vs sprite
    hud.asm               # score, lives, HIGH SCORE
    audio.asm             # music + SFX driver
    interrupts.asm        # INT0 / VBlank / YM2151 timer dispatch
    data.asm              # INCBIN glue for assets/
```

---

## 4. Game Systems

### 4.1 Maze representation

The maze is a fixed **30×28 landscape tile grid** authored as a clean-room
rotation of the arcade 28×30 active playfield. The authored source is
`vanguard8_port/assets/src/maze_layout.txt`, a token grid of explicit
tile-bank source IDs (see T006). `conv_tiles.py` resolves each token
against the generated tile index and emits `assets/tile_nametable.bin` as
a packed byte array ready to blit to the VDP-B Graphic 4 framebuffer.

Authoring rationale: the arcade wall tiles are asymmetric and designed to
connect only to their arcade neighbors. We tried two naive approaches
before settling on the current one:

1. **Edge-mask auto-picking** — pick a wall tile per cell based on which
   of its orthogonal neighbors are walls. Failed because the edge-mask
   signature (`n`/`e`/`s`/`w` per edge) does not capture a tile's
   interior pixel connectivity, and arcade tiles with the same mask
   have wildly different shapes.
2. **Full-fidelity rotation of the arcade tilemap** — reproduce the
   arcade's own tile-ID grid, rotated. This would match the arcade's
   own adjacency assumptions but requires either a MAME tilemap-viewer
   transcription or a published reference, and the full rotated grid
   (36×28) overflows the V8 horizontally.

The current approach (explicit 30×28 grid authored against the T005 tile
bank, iteratively verified visually) hits the sweet spot: traversable,
close to the arcade, and fits the framebuffer without further clipping.

The dot/pellet layout matches the arcade's effective dot topology
(240 regular + 4 power pellets) so ghost-house dot counters, fruit spawn
thresholds (70 and 170 dots), and level-complete detection all use the
arcade's published values without adjustment.

A separate 30×28 **dynamic dot bitmap** in SRAM tracks which dots remain;
rendering a "dot eaten" is an 8×8 HMMV fill to the "empty corridor" tile.
Global "dots eaten" counter drives fruit spawn thresholds and
level-complete.

### 4.2 Pac-Man movement

- Grid-aligned 8-pixel cells; sub-pixel position in 1/16 tile units.
- Desired direction buffered from last D-pad input; actual direction changes
  only when the next cell in the desired direction is walkable (standard
  arcade behavior — the "cornering" trick where diagonal taps round corners
  early falls out of this automatically).
- Speed tables per level, per mode (normal / energizer / tunnel):
  arcade speeds are stored as "how many pixels to move per frame" lookup
  tables, and we store the same tables verbatim (`speed_tables.inc`), since
  the documented values are the behavior spec, not copyrighted code.
- **Coordinate system.** Movement and walkability checks run in
  maze-local coordinates (the 30×28 rotated grid). Controller input is
  read as landscape screen-space directions and passed through a fixed
  transform to maze-local directions before consulting the walkability
  bitmap. Sprite render positions go through the inverse transform at
  SAT-commit time. The transform is a single rotation constant — no
  trig, no per-frame cost.

### 4.3 Ghost AI

Implemented in `ghost.asm` + `ghost_targets.asm`. Each ghost has the same
four-state FSM (Scatter → Chase → Frightened → Eyes → Scatter …) driven by
the global mode timer. Targeting functions produce a **target tile** each
frame; ghosts then pick, at each intersection, the neighbor cell that
minimizes straight-line distance to that target (ties broken in
Up > Left > Down > Right order, as arcade does; never reverse unless the
state timer just flipped).

Targeting rules (the "personalities"):

| Ghost | Scatter target | Chase target |
|---|---|---|
| Blinky (red) | top-right maze corner | Pac-Man's current tile |
| Pinky (pink) | top-left maze corner | Pac-Man's tile + 4 tiles ahead (with the arcade's documented "up" overflow bug reproduced) |
| Inky (cyan) | bottom-right corner | vector from Blinky through (Pac-Man + 2 ahead), doubled |
| Clyde (orange) | bottom-left corner | Pac-Man's tile if > 8 tiles away, else scatter target |

Mode timing table (level 1): 7 s scatter → 20 s chase → 7 s scatter → 20 s
chase → 5 s scatter → 20 s chase → 5 s scatter → infinite chase. Later
levels shorten scatter phases per the arcade's published table. Stored as
a 4-level × 8-phase frame-count table.

Other ghost behaviors to replicate exactly:

- **House release**: per-ghost dot counter (Pinky 0, Inky 30, Clyde 60 on
  level 1), with global counter taking over after a life lost.
- **Cruise Elroy**: Blinky speeds up and enters permanent chase when dots
  remaining drops below level-dependent thresholds (20 / 10 on level 1).
- **Tunnel slowdown**: ghosts move slower than Pac-Man in the side tunnels.
- **Reverse direction on mode flip**: all non-frightened ghosts reverse
  when scatter ↔ chase transition fires, exactly once per transition.
- **Frightened targeting**: pseudo-random choice at intersections using the
  arcade's documented LFSR sequence (not true random), so player strategies
  that rely on frightened-ghost predictability still work.

### 4.4 Collisions

- Pac-Man vs dot: check maze dot bitmap at Pac-Man's current tile every
  frame; if set, clear, HMMV-fill the empty-corridor tile, increment score,
  advance global dot counter.
- Pac-Man vs ghost: 8-pixel bounding box (or same-tile test) each frame.
  If ghost is frightened → eat ghost (200/400/800/1600 points chain),
  ghost → eyes state, return to house. If ghost is in Chase/Scatter →
  life lost, death animation, reset positions.

### 4.5 Scoring and HUD

- Dots 10, power pellets 50, ghosts 200/400/800/1600, fruits by level
  (cherry 100, strawberry 300, orange 500, apple 700, melon 1000,
  Galaxian 2000, bell 3000, key 5000). Tables baked into `data.asm`.
- Score BCD in SRAM, rendered to VDP-A HUD tiles by pushing digit tile
  indices into the Graphic 3 Pattern Name Table during VBlank.
- **HUD placement** (per §2): current score along a centered top-of-maze
  strip, high score along a centered bottom-of-maze strip, lives and
  fruit stacked vertically in the 8 px left gutter. All three overlays
  are drawn on VDP-A with transparent-background tiles so VDP-B shows
  through everywhere else.
- High score persists in SRAM at `0xFF80–0xFF8F` (not battery-backed in
  this cartridge — resets on power cycle, matching arcade).
- 10 000 point extra life: one-time check, plays the extra-life jingle
  via the audio driver.

### 4.6 Intermissions

Three arcade intermissions (after level 2, 5, 9) — Pac-Man chased by Blinky,
Blinky's torn sheet, etc. Each is a scripted sprite sequence driven by a
frame-indexed action table; implemented as a small cutscene interpreter in
`intermission.asm`. The sprite art already exists in the extracted set.

---

## 5. ROM Layout and Memory Map

### 5.1 Cartridge layout (up to 960 KB; we need ~128 KB)

```
Bank (fixed) 0x00000–0x03FFF   16 KB   Boot, MMU init, main loop, IRQ handlers,
                                       hot game logic (Pac-Man + ghost AI)
Bank 0       0x04000–0x07FFF   16 KB   Maze data, font, small tables
Bank 1       0x08000–0x0BFFF   16 KB   Tile bank (VDP-B blitter source, 4bpp)
Bank 2       0x0C000–0x0FFFF   16 KB   Sprite patterns + color tables
Bank 3       0x10000–0x13FFF   16 KB   Intermission scripts + extra sprites
Bank 4       0x14000–0x17FFF   16 KB   YM2151 instrument bank + music data
Bank 5       0x18000–0x1BFFF   16 KB   ADPCM sample bank (SFX)
Bank 6       0x1C000–0x1FFFF   16 KB   HUD font + reserve
```

Bank switching via `OUT0 (0x39), BBR_value` as documented in
`docs/spec/00-overview.md`. The main loop and IRQ handlers live entirely in
fixed bank 0 so they're always resident regardless of which asset bank is
paged in.

### 5.2 SRAM layout (32 KB at 0xF0000, logical 0x8000–0xFFFF)

```
0x8000–0x80DF   Z80 stack (grows down from 0x8100)
0x80E0–0x80FF   INT1/INT2/PRT vector table (required by HD64180 vectored IRQs)
0x8100–0x81FF   VBlank/INT0 state (frame counter, dirty flags)
0x8200–0x83FF   Audio driver state (channel tracks, tempo, envelopes)
0x8400–0x85FF   Pac-Man state (pos, dir, sub-tile, anim, speed index)
0x8600–0x87FF   Ghost state ×4 (pos, dir, mode, target, house counter, ...)
0x8800–0x8BFF   Dynamic dot bitmap (28×31 bits + scoring state)
0x8C00–0x8FFF   SAT shadows (VDP-A + VDP-B), DMA queues
0x9000–0x9FFF   HUD shadow (Graphic 3 name table staging)
0xA000–0xFF7F   Free (future: replay buffer, debug)
0xFF80–0xFFFF   High score table
```

### 5.3 VRAM layouts

**VDP-B (playfield)**: recommended Graphic 4 layout from
`docs/spec/02-video.md`:

```
0x0000–0x69FF   Active framebuffer (27 136 bytes)
0x7000–0x77FF   Sprite pattern generator (64 × 16×16 patterns)
0x7A00–0x7BFF   Sprite color table (Sprite Mode 2)
0x7C00–0x7CFF   Sprite attribute table
0x7D00–0xFFFF   Tile bank for HMMM blitter (rotated maze tiles)
```

**VDP-A (HUD)**: recommended Graphic 3 layout:

```
0x0000–0x02FF   Pattern name table (32×24 HUD layout)
0x0300–0x17FF   Pattern generator (HUD font — digits, letters, UI strings)
0x1800–0x2FFF   Color table
0x3000–0x37FF   Sprite pattern generator (ghost-eye overlay sprites)
0x4000–0x41FF   Sprite color table
0x4200–0x42FF   Sprite attribute table
0x4300–0xFFFF   Free
```

---

## 6. Main Loop and Timing

```
reset:
    MMU setup        (CBAR/CBR/BBR as in docs/spec/00-overview.md)
    VDP-B init       (Graphic 4, LN=1, palette, TP=1)
    VDP-A init       (Graphic 3, LN=1, palette, TP=1, sprites enabled)
    Audio init       (YM2151 Timer A at 60 Hz, AY reset, MSM5205 idle)
    Load bank 1      (tile bank) → blit initial maze via HMMM
    Load bank 2      (sprites) → upload pattern + color tables
    Enable INT0 (VBlank), EI
    jp  main_loop

main_loop:
    halt                      ; wait for VBlank INT
    ; returns here after INT0 handler runs
    call read_inputs          ; port 0x00
    call tick_pacman
    call tick_ghosts
    call tick_collisions
    call tick_fruit
    call tick_audio_driver
    call commit_shadows       ; SAT shadows → VDP SATs, HUD dirty tiles → VDP-A
    jr   main_loop

INT0 (at 0x0038):
    ; dispatch on VDP-A S#0 (VBlank) / S#1 (scanline) / YM2151 status
    ; - VBlank: set vblank_flag, advance global mode timer
    ; - YM2151 timer: audio sequencer tick
    ei / reti
```

CPU budget: ~119 300 cycles per frame (`docs/spec/04-io.md`). Rough
allocations — Pac-Man tick 3 k, 4 ghost ticks 12 k, collisions 2 k, audio
5 k, HUD commit + SAT commit 10 k = ~32 k cycles, leaving ample headroom
for the blitter-driven dot erasure and intermission scripting.

---

## 7. Build and Verification

### 7.1 Build driver

Fork `showcase/tools/package/build_showcase.py` into
`vanguard8_port/tools/pack_rom.py`:

1. Run each `conv_*.py` tool → regenerate `assets/*.bin`.
2. Invoke `sjasmplus src/main.asm` → `pacman.rom` + `pacman.sym`.
3. Pad ROM up to the next 16 KB page boundary (Vanguard 8 cartridges are
   paged by the HD64180 MMU in 16 KB units).
4. Emit a reproducible symbol file for headless checkpoints.

Run it from `vanguard8_port/` with no arguments. The MAME ROM inputs stay
in `/home/djglxxii/src/pacman/pacman/`; the build pulls assets from
`/home/djglxxii/src/pacman/extracted/` and the conversion scripts.

### 7.2 Run

```
$ ~/src/Vanguard8/build/vanguard8_frontend --rom vanguard8_port/build/pacman.rom
```

### 7.3 Verification checkpoints

Headless runs (`run_showcase_headless.py` pattern) generate frame hashes and
audio hashes at deterministic checkpoints:

| Checkpoint | Verifies |
|---|---|
| Boot frame 1 | MMU + VDP init, palette upload, empty framebuffer |
| Boot frame 60 | Maze fully blitted via HMMM, all dots present |
| Attract-mode frame 300 | Intro jingle (YM2151) + ghost intro text correct |
| Gameplay tick 500 | Pac-Man + 4 ghosts in known positions, score 0 |
| After eating power pellet | All ghosts frightened, color table updated |
| Ghost-eaten chain | Score increments 200→400→800→1600 |
| Level 2 start | Cruise Elroy threshold table reloaded |
| Intermission 1 | Cutscene sprite script completes within frame budget |

Each checkpoint's expected frame hash + audio hash is captured once from a
reference run and stored in `vanguard8_port/tests/checkpoints.json`. CI re-
runs and compares; divergence fails the build.

Ghost-AI correctness is verified by a **deterministic replay test**: from a
fixed PRNG seed + pre-recorded input log, the ghosts must occupy specific
tiles at specific frames. The frame numbers and expected tiles come from
manual validation against arcade footage.

---

## 8. Risks and Open Questions

1. **WSG approximation quality.** YM2151 operator sums are close to but not
   identical to a 4-bit wavetable. If strategy A sounds wrong, fall back to
   strategy B (ADPCM streaming). Keep both paths in `conv_audio.py`
   selectable via a build flag.
2. **Sprite budget on fast attract screen.** Attract mode shows ghost name
   + personality text scrolling, which uses font tiles, not sprites, so we
   stay within limits; worth confirming once implemented.
3. **Per-frame HMMM budget for dot erasure.** Worst case is eating one dot
   per frame (one 8×8 HMMM); measured at ~160 master clocks, well inside
   VBlank. No risk.
4. **HUD overlay clearance.** The top-center and bottom-center HUD
   strips overlay the maze in regions that current analysis (§2) says
   are decorative wall only. T007 must empirically verify the exact
   pixel clearance above/below the outermost dot lane before committing
   to a strip height, and must handle the READY! / GAME OVER center
   text that uses the same screen region without collision.
5. **Maze-space ↔ screen-space transform correctness.** The rotation
   transform between maze coordinates and landscape screen coordinates
   must be consistent across movement, collision detection, SAT commit,
   and debug overlays. A single buggy axis mapping will make sprites
   appear in the wrong place or cause "wall detected" at the wrong
   cell. Mitigation: unit-test the transform in `tools/` as a
   standalone Python function and commit expected-value fixtures.
6. **Clean-room discipline.** Contributors must not read the arcade Z80
   disassembly while writing game logic. Use only public behavioral
   documentation (ghost targeting rules, speed tables, frame counts) as
   specification input. This is both a correctness and a licensing
   boundary.

---

## 9. Milestones

| # | Milestone | Exit criterion |
|---|---|---|
| 1 | Build scaffold | `pack_rom.py` produces an empty but valid ROM that boots to a blue screen on `vanguard8_frontend` |
| 2 | Palette + tile conversion | Static maze renders on VDP-B at boot, visually matches arcade layout |
| 3 | HUD overlay | VDP-A Graphic 3 shows HIGH SCORE + 1UP text composited over VDP-B |
| 4 | Sprite conversion | Pac-Man + 4 ghosts visible in known static positions, colors correct |
| 5 | Pac-Man movement | Input-driven Pac-Man movement, dot eating + score increment |
| 6 | Ghost AI | All 4 ghosts cycle Scatter/Chase with correct targeting + mode timing |
| 7 | Frightened + death | Power pellets, ghost-eaten chains, life loss, respawn |
| 8 | Audio | Intro jingle, siren, chomp, death jingle, ghost-eaten, extra-life |
| 9 | Fruit + levels | Fruit spawns at correct dot counts, level table drives speed/Elroy |
| 10 | Intermissions | Three cutscenes play at correct levels |
| 11 | Polish + checkpoints | Frame/audio hash checkpoints + replay test all green |

Each milestone ends with a committed checkpoint capture and a short note
in `vanguard8_port/docs/milestone-N.md` following the showcase's own
milestone discipline.
