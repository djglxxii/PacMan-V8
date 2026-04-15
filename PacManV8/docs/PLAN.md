# Pac-Man for Vanguard 8 — Implementation Plan

## Goal

Port Pac-Man to the Vanguard 8 console with **arcade-faithful gameplay** and
a presentation layer purpose-built for the Vanguard 8 hardware. Pac-Man
patterns, ghost AI, timing, and feel must be indistinguishable from the
original. The visuals are re-authored to fit the V8's 256x212 display natively
— no bitmap scaling.

---

## Architecture

Two cleanly separated layers:

```
+---------------------------+
|   Gameplay Core           |   Arcade-accurate simulation
|   (platform-agnostic)     |   Deterministic, pattern-correct
+-------------+-------------+
              |
              v
+---------------------------+
|   Render / Presentation   |   Vanguard 8 specific
|   VDP-A + VDP-B + Audio   |   256x212, rotated coords, V9938
+---------------------------+
```

The gameplay core operates in the original arcade coordinate space (288x224,
portrait orientation). The render layer transforms game state into Vanguard 8
VDP output every frame.

---

## Project Structure

```
PacManV8/
├── pacman/                  ROM files (MAME split, do not commit)
├── tools/                   Python extraction and conversion scripts
│   ├── extract_tiles.py     Decode character ROM → indexed tile data
│   ├── extract_sprites.py   Decode sprite ROM → indexed sprite data
│   ├── extract_palette.py   Convert arcade palette → V8 9-bit RGB
│   ├── extract_maze.py      Build semantic maze from ROM tilemap
│   └── build_assets.py      Master script: run all, produce binary assets
├── assets/                  Converted binary assets for inclusion in ROM
│   ├── tiles_vdpb.bin       VDP-B tile patterns (4bpp Graphic 4 format)
│   ├── sprites.bin          VDP-A sprite patterns (Mode 2 format)
│   ├── palette_a.bin        VDP-A palette (16 entries, 2 bytes each)
│   ├── palette_b.bin        VDP-B palette (16 entries, 2 bytes each)
│   ├── maze_nametable.bin   Maze tile indices (for VDP-B background)
│   ├── maze_semantic.bin     Semantic maze data (wall/path/pellet/etc.)
│   └── maze_graph.bin       Movement graph (intersections + edges)
├── src/
│   ├── main.asm             Entry point, init, main loop
│   ├── game_core.asm        Gameplay simulation (movement, AI, timing)
│   ├── ghost_ai.asm         Ghost targeting, scatter/chase, frightened
│   ├── movement.asm         Pac-Man + ghost movement, turn buffering
│   ├── collision.asm        Pellet eat, ghost collision, energizer
│   ├── timing.asm           Speed tables, dot-stall, level progression
│   ├── render.asm           Coordinate transform + VDP update dispatch
│   ├── vdp_a.asm            VDP-A driver (sprites, HUD, foreground)
│   ├── vdp_b.asm            VDP-B driver (maze background, pellets)
│   ├── audio.asm            Sound engine (YM2151 + AY-3-8910)
│   ├── input.asm            Controller read + direction mapping
│   └── data.inc             Asset includes and lookup tables
├── build/                   Build output (ROM + symbols)
├── docs/                    Reference docs and notes
└── PLAN.md                  This file
```

---

## ROM File Inventory

The `pacman/` folder contains the standard MAME Pac-Man ROM split:

| File          | Size   | Content                                        |
|---------------|--------|------------------------------------------------|
| `pacman.6e`   | 4 KB   | Program ROM 1 (CPU 0x0000–0x0FFF)             |
| `pacman.6f`   | 4 KB   | Program ROM 2 (CPU 0x1000–0x1FFF)             |
| `pacman.6h`   | 4 KB   | Program ROM 3 (CPU 0x2000–0x2FFF)             |
| `pacman.6j`   | 4 KB   | Program ROM 4 (CPU 0x3000–0x3FFF)             |
| `pacman.5e`   | 4 KB   | Character/tile ROM (256 8x8 tiles, 2bpp)       |
| `pacman.5f`   | 4 KB   | Sprite ROM (64 16x16 sprites, 2bpp)            |
| `82s123.7f`   | 32 B   | Color PROM — 4-color palette groups (16 entries)|
| `82s126.4a`   | 256 B  | Color PROM — RGB values (32 entries)            |
| `82s126.1m`   | 256 B  | Sound PROM — waveform table                    |
| `82s126.3m`   | 256 B  | Sound PROM — waveform table (second half)       |

---

## Vanguard 8 Hardware Mapping

### Display

| Arcade                  | Vanguard 8                              |
|-------------------------|-----------------------------------------|
| 288x224 portrait        | 256x212 landscape (both VDPs)           |
| 60.61 Hz refresh        | 59.94 Hz NTSC                           |
| Single tilemap + sprites| VDP-B background + VDP-A sprites/HUD    |
| 4-color palettes        | 16-entry 9-bit RGB palettes (per VDP)   |

### VDP Configuration

Both VDPs run **Graphic 4** (Screen 5): 256x212, 4bpp bitmap, Sprite Mode 2.

**VDP-B (background — rear layer):**
- Maze walls rendered as pre-blitted tiles via HMMM commands
- Pellets rendered as small tile patterns (static until eaten)
- Energizer pellets blink via palette animation
- Palette: maze colors (blue walls, black background, pellet colors)

**VDP-A (foreground — front layer, composited via YS pin):**
- Color 0 = transparent (TP bit set in R#8) — VDP-B shows through
- Pac-Man sprite (16x16, Sprite Mode 2, per-row color for mouth animation)
- 4 ghost sprites (16x16, per-row color for body + eyes + skirt)
- Fruit sprite
- HUD text (score, lives, level) rendered via HMMM from font tile bank
- Eyes-only sprites during ghost retreat

**Compositing:** VDP-A's YS pin drives the 74LS257 mux. Wherever VDP-A
outputs color 0, VDP-B's pixel is selected. This gives us a clean
background (maze) + foreground (characters, HUD) split with zero CPU cost.

### VRAM Layout (per VDP, Graphic 4)

```
0x0000–0x69FF   Framebuffer (27,136 bytes, 212 lines x 128 bytes)
0x7000–0x77FF   Sprite pattern generator (2,048 bytes)
0x7A00–0x7BFF   Sprite color table (512 bytes, SAT base - 512)
0x7C00–0x7CFF   Sprite attribute table (256 bytes)
0x7D00–0xFFFF   Tile/asset pattern bank (~33 KB for HMMM source tiles)
```

### Sprite Budget

Pac-Man needs at most 6 sprites per VDP-A frame:
- 1 Pac-Man (16x16)
- 4 ghosts (16x16 each)
- 1 fruit (16x16)

Well within the 32-sprite / 8-per-scanline Mode 2 limit. Ghost eyes during
retreat can reuse the ghost sprite slot with a different pattern.

### Audio Mapping

| Arcade (Namco WSG)           | Vanguard 8                              |
|------------------------------|-----------------------------------------|
| 3-ch wavetable (8-bit, 96kHz)| AY-3-8910 PSG (3-ch square + noise)     |
| —                            | YM2151 FM (for richer siren/intermission)|
| —                            | MSM5205 ADPCM (optional: death, fruit)  |

The arcade's wavetable sounds are simple enough to approximate well with PSG
square waves for the primary effects (waka-waka, siren, ghost eat, death).
The YM2151 can enhance the siren with FM modulation and handle intermission
music. MSM5205 is optional for higher-fidelity death sequence or fruit pickup.

### Orientation

The arcade monitor is rotated 90° (portrait). The Vanguard 8 outputs standard
NTSC landscape. The gameplay core runs in the original 28-column x 36-row
tile coordinate system. The render layer performs the rotation:

```
Arcade (portrait):          V8 (landscape):
  28 tiles wide               36 tiles wide (x)
  36 tiles tall               28 tiles tall (y)

  arcade_x → v8_y (inverted)
  arcade_y → v8_x
```

The arcade playfield (224x288 pixels) maps to 224x288 logical pixels. After
rotation, this becomes 288x224. The V8 display is 256x212 — so the rotated
image must be **fitted** into the available space, not scaled. The maze will
be re-drawn at a resolution that fits within 256x212 while preserving the
exact tile topology and movement graph.

---

## Phase 0 — Project Setup

**Deliverables:**
- Repository structure (as above)
- Build script (`tools/build.py`) using SjASM assembler, matching the
  showcase build pattern from the Vanguard 8 repo
- Run script to launch in emulator (`run.sh`)
- Minimal ROM that boots and shows a solid background color on VDP-B

**Details:**
- Assembler: SjASM (same as Vanguard 8 showcase ROM)
- Emulator: `/home/djglxxii/src/Vanguard8/cmake-build-debug/superz80_app`
  (note: emulator binary is `superz80_app` for historical reasons)
- ROM padded to 16 KB page boundary per V8 cartridge spec
- HD64180 MMU configured: CBAR=0x48, CBR=0xF0, BBR=0x04
- VDP-A and VDP-B initialized to Graphic 4, 212-line mode, display off
- IM1 interrupt handler stub at 0x0038

---

## Phase 1 — ROM Data Extraction

**Objective:** Extract structured data from the MAME ROM files. All extraction
is done by Python tools that read the binary ROM files and produce V8-ready
binary assets.

### 1.1 Tile Extraction (`tools/extract_tiles.py`)

- Read `pacman.5e` (character ROM, 256 tiles, 2bpp planar)
- Decode the Pac-Man tile format: each tile is 8x8 pixels, 2 bits per pixel,
  stored as 16 bytes per tile. Each row uses two bytes: byte `row` supplies
  pixels 4-7 and byte `8 + row` supplies pixels 0-3. Within each byte, bits
  0-3 are bitplane 0 and bits 4-7 are bitplane 1 for those four pixels. This
  matches the MAME Pac-Man `tilelayout` definition, where the two bitplanes
  for four pixels are packed into one byte.
- Output each tile as 4bpp indexed data (V9938 Graphic 4 format: 2 pixels
  per byte, high nibble = left pixel)
- Classify tiles: wall, pellet, energizer, blank, text character, fruit icon
- Output: `assets/tiles_vdpb.bin` + manifest

### 1.2 Sprite Extraction (`tools/extract_sprites.py`)

- Read `pacman.5f` (sprite ROM, 64 sprites, 2bpp planar)
- Decode the Pac-Man sprite format from the MAME `spritelayout`: each 16x16
  sprite is 64 bytes, 2bpp, with bitplanes packed into nibbles. Each row is
  assembled from four 4-pixel groups, using source byte groups for x 0-3,
  x 4-7, x 8-11, and x 12-15 as defined by the layout's x offsets. Rows 0-7
  use bytes 0-31 and rows 8-15 use bytes 32-63.
- Convert to V9938 Sprite Mode 2 format: 1-bit pattern (opaque/transparent)
  with per-row color table entries
- Since arcade sprites are only 4 colors (2bpp), map to Mode 2's per-row
  color by selecting the dominant non-transparent color per row
- Output: `assets/sprites.bin` (patterns) + `assets/sprite_colors.bin`

### 1.3 Palette Extraction (`tools/extract_palette.py`)

- Read `82s126.4a` (32 RGB entries, arcade format) and `82s123.7f` (16
  palette group definitions, each selecting 4 colors from the 32)
- Arcade color format: each byte in `82s126.4a` encodes R(bit 0), G(bit 1-2),
  B(bit 3-4) with weighted resistor DAC values
- Convert to V9938 9-bit RGB: 3 bits R, 3 bits G, 3 bits B (512-color space)
- Assign palette entries to VDP-A and VDP-B independently:
  - VDP-B: maze wall color, pellet color, background (black), energizer
  - VDP-A: Pac-Man yellow, ghost colors (red/pink/cyan/orange), eyes white/blue,
    frightened blue/white, text colors
- Output: `assets/palette_a.bin`, `assets/palette_b.bin`

### 1.4 Sound Data Extraction (`tools/extract_sound.py`)

- Read `82s126.1m` and `82s126.3m` (waveform PROMs)
- Document the waveform shapes for reference when writing PSG/FM equivalents
- No direct binary conversion — V8 audio is re-authored using YM2151/AY-3-8910
- Output: `docs/arcade_waveforms.md` (reference only)

### 1.5 Maze Data Extraction (`tools/extract_maze.py`)

- Read the program ROMs (`pacman.6e`–`pacman.6j`, concatenated = 16 KB)
- Locate the tilemap data in the program ROM. The Pac-Man tilemap is stored
  at specific addresses in the program ROM and uses a non-linear mapping
  from memory address to screen position:
  - Video RAM at 0x4000–0x43FF (tile indices)
  - Color RAM at 0x4400–0x47FF (palette selections)
  - Screen mapping: the 36x28 grid is stored in a column-major order with
    the bottom two rows and top two rows stored separately (HUD regions)
- Extract the default maze layout (level 1 tilemap)
- Build a semantic maze grid (36 rows x 28 columns in arcade orientation):
  ```
  WALL, PATH, PELLET, ENERGIZER, GHOST_HOUSE, GHOST_DOOR, TUNNEL, BLANK
  ```
- Build the movement graph:
  - Nodes: every intersection and corner
  - Edges: valid movement paths between nodes
  - Annotate: tunnel slow zones, ghost house entry/exit point, warp tunnel
    endpoints, energizer positions
- Output: `assets/maze_semantic.bin`, `assets/maze_graph.bin`,
  `assets/maze_nametable.bin`

---

## Phase 2 — Maze Reconstruction for V8

**Objective:** Rebuild the maze visuals to fit 256x212 while preserving the
exact topology and movement graph.

### Screen Layout (after 90° rotation)

```
+------------------------------------------+  y=0
|  1UP    HIGH SCORE    2UP                |  HUD row (8px)
+------------------------------------------+  y=8
|                                          |
|              MAZE AREA                   |
|           (240 x 196 px)                 |
|                                          |
+------------------------------------------+  y=204
|  LIVES ●●    LEVEL FRUIT 🍒🍓           |  Status row (8px)
+------------------------------------------+  y=212
          256 px wide
```

The original maze is 28x31 tiles (excluding HUD rows) = 224x248 pixels in
arcade orientation. After rotation this becomes 248x224. To fit 256x212:
- Horizontal (248px rotated): fits in 256px with 8px margin
- Vertical (224px rotated): must compress slightly to fit 212px minus HUD space

**Strategy:** Re-draw the maze using 8x8 tiles at the topology level. Each
arcade tile position maps to a V8 tile position. Wall thickness and pellet
size are adjusted to fit the available pixel grid while keeping path widths
and intersections at exactly the right relative positions for the movement
graph to remain valid.

The maze is rendered once to VDP-B's framebuffer at scene init using HMMM
commands from the tile asset bank. Pellets are rendered as part of the initial
maze blit. When eaten, the pellet tile is overwritten with a blank tile via
HMMM.

**Deliverables:**
- Re-authored maze tile set in `assets/tiles_vdpb.bin`
- Coordinate mapping table: arcade tile (col,row) → V8 pixel (x,y)
- VDP-B framebuffer init routine in `src/vdp_b.asm`

---

## Phase 3 — Gameplay Core

**Objective:** Implement arcade-accurate Pac-Man game logic in Z80 assembly.
All gameplay runs in the original arcade coordinate system (sub-tile
precision using 8.8 or similar fixed-point within each tile).

### 3.1 Movement System

- Tile-based movement with sub-tile (pixel) precision
- Pac-Man moves continuously in current direction until hitting a wall
- **Turn buffering (cornering):** player can pre-input a turn up to ~4 pixels
  before reaching the intersection center. This is critical for pattern play.
- Speed tables per level (from the Pac-Man Dossier):
  - Pac-Man: normal speed, frightened speed, tunnel speed
  - Ghosts: normal, tunnel, frightened, elroy 1, elroy 2
- Speed is expressed as pixels-per-frame (fractional, using fixed-point)

### 3.2 Ghost AI

Each ghost has three components:
1. **Mode:** Scatter, Chase, or Frightened (with global timer-driven switching)
2. **Target tile:** Computed per ghost per mode
3. **Movement rule:** At each intersection, choose the direction that minimizes
   Euclidean distance to the target tile (never reversing except on mode switch)

Ghost targeting (chase mode):
- **Blinky (red):** targets Pac-Man's current tile
- **Pinky (pink):** targets 4 tiles ahead of Pac-Man (with the original
  up-direction overflow bug: when facing up, target is 4 up AND 4 left)
- **Inky (cyan):** complex — vector from Blinky to 2 tiles ahead of Pac-Man,
  doubled
- **Clyde (orange):** targets Pac-Man when > 8 tiles away, scatter corner
  when <= 8 tiles

Scatter targets (fixed corner tiles):
- Blinky: top-right
- Pinky: top-left
- Inky: bottom-right
- Clyde: bottom-left

### 3.3 Scatter/Chase Timer

Global mode timer switches all ghosts between scatter and chase:
```
Level 1:  Scatter 7s → Chase 20s → Scatter 7s → Chase 20s →
          Scatter 5s → Chase 20s → Scatter 5s → Chase forever
```
(Different tables for levels 2-4 and 5+)

### 3.4 Ghost House Logic

- Ghosts start inside the house and exit based on a dot counter or global
  timer
- Exit order: Blinky (already out) → Pinky → Inky → Clyde
- Dot counter per ghost resets on life loss (then uses global timer)

### 3.5 Frightened Mode

- Triggered by energizer consumption
- All ghosts reverse direction immediately
- Ghosts move at frightened speed (slower)
- Ghost direction at intersections becomes pseudo-random (PRNG seeded by
  timer/frame counter)
- Duration decreases per level (from speed/timing tables)
- Flashing phase in final 2 seconds (alternating blue/white)

### 3.6 Collision Detection

- Pac-Man vs. pellet: consume when Pac-Man's center crosses the pellet tile
  center. **Dot-stall:** Pac-Man freezes for 1 frame when eating a pellet,
  3 frames for an energizer. This is critical for pattern timing.
- Pac-Man vs. ghost: compare tile positions. If same tile, collision occurs.
  - Normal ghost: Pac-Man dies
  - Frightened ghost: ghost is eaten, eyes retreat to ghost house
- Pac-Man vs. fruit: same-tile check

### 3.7 Tunnel

- Wrap-around at the horizontal edges of the maze
- **Tunnel slow zone:** ghosts move at reduced speed in the tunnel region
  (approximately half speed, exact zones defined in the movement graph)

### 3.8 Level Progression

- 256 levels (with the famous level 256 kill screen)
- Speed tables, ghost behavior timers, frightened duration, and bonus fruit
  all vary per level according to the well-documented Pac-Man level tables
- Intermission cutscenes at levels 2, 5, and 9

---

## Phase 4 — Rendering Layer

**Objective:** Transform game state into VDP-A/VDP-B output each frame.

### 4.1 Frame Update Flow (V-blank ISR at 0x0038)

```
1. Read VDP-A S#0 (clears VB flag)
2. Read controller input (port 0x00)
3. Run gameplay core update (one tick)
4. Update VDP-B:
   - HMMM to erase eaten pellets (overwrite with blank tile)
   - Energizer blink (palette toggle via port 0x86)
5. Update VDP-A:
   - Update sprite attribute table in SRAM shadow
   - DMA shadow SAT to VDP-A VRAM
   - Update HUD text if score changed (HMMM font tiles)
6. Update audio state
7. Return from interrupt
```

### 4.2 Sprite Rendering

Each game entity maps to a VDP-A sprite:

| Entity      | Sprite # | Size  | Pattern Source              |
|-------------|----------|-------|-----------------------------|
| Pac-Man     | 0        | 16x16 | Animation frame from table  |
| Blinky      | 1        | 16x16 | Direction + animation frame |
| Pinky       | 2        | 16x16 | Direction + animation frame |
| Inky        | 3        | 16x16 | Direction + animation frame |
| Clyde       | 4        | 16x16 | Direction + animation frame |
| Fruit/Score | 5        | 16x16 | Current fruit or point value|

Sprite position = gameplay coordinate transformed through the rotation
mapping, offset by the maze area origin on screen.

Ghost sprite pattern changes based on state:
- Normal: body pattern (direction-dependent) + per-row color for body + eyes
- Frightened: blue body pattern + per-row color (blue/white flash)
- Eaten: eyes-only pattern (much smaller, centered in 16x16)

### 4.3 VDP-B Pellet Management

Pellets are part of the VDP-B framebuffer. When eaten:
1. Look up the pellet's V8 screen position from the coordinate map
2. Queue an HMMM command to blit a blank (black) 8x8 tile over that position
3. Limit to 1-2 HMMM commands per frame to stay within V-blank budget

Since Pac-Man eats at most 1 pellet per frame (due to dot-stall), this is
always sufficient.

---

## Phase 5 — Audio

**Objective:** Recreate recognizable Pac-Man audio using V8 sound hardware.

### Sound Effects (AY-3-8910 PSG)

| Effect          | PSG Channel | Technique                        |
|-----------------|-------------|----------------------------------|
| Waka-waka       | A           | Alternating square wave pitches  |
| Pellet eat      | A           | Short pitch sweep                |
| Ghost siren     | B           | Slow pitch modulation            |
| Ghost eaten     | A           | Fast descending sweep            |
| Extra life      | A + B       | Ascending arpeggio               |

### Music (YM2151 FM)

| Piece           | Channels | Notes                            |
|-----------------|----------|----------------------------------|
| Intro jingle    | 2-3      | FM recreation of the startup tune|
| Intermission    | 3-4      | FM arrangement                   |
| Death sequence  | 2-3      | Descending FM with decay         |

### Optional ADPCM (MSM5205)

- Pre-recorded death sound effect for higher fidelity
- Fruit pickup accent
- Stored as 4-bit ADPCM nibbles in cartridge ROM, fed via INT1 handler

---

## Phase 6 — Game Flow and State Machine

```
ATTRACT → READY → PLAYING → (DYING | LEVEL_COMPLETE)
                     ↑              |          |
                     |              v          v
                     +-------- CONTINUE    NEXT_LEVEL
                                               |
                                               v
                                          INTERMISSION (levels 2,5,9)
```

- **ATTRACT:** Demo mode (AI-controlled Pac-Man, cycling screens)
- **READY:** "READY!" text, 4-second countdown, ghosts in starting positions
- **PLAYING:** Active gameplay
- **DYING:** Death animation (Pac-Man deflation), life decremented
- **LEVEL_COMPLETE:** Maze flash animation (blue/white wall toggle)
- **INTERMISSION:** Cutscene sequences between certain levels

---

## Phase 7 — Validation

### Pattern Testing

Record input sequences for known Pac-Man patterns and verify:
- Pac-Man follows the expected path
- Ghost positions match at key checkpoints
- Score matches expected value after the sequence
- Timing (frame count to complete pattern) matches arcade

### Specific Behaviors to Validate

- [ ] Turn buffering / cornering allows pre-input at intersections
- [ ] Dot-stall pauses: 1 frame for pellets, 3 frames for energizers
- [ ] Ghost scatter/chase timer sequence matches per-level tables
- [ ] Ghost house exit order and dot counter behavior
- [ ] Frightened mode duration per level
- [ ] Tunnel slow zone positions and speed reduction
- [ ] Elroy mode triggers (Blinky speed-up when few dots remain)
- [ ] Pinky's targeting overflow bug when Pac-Man faces up
- [ ] Ghost reversal on mode switch
- [ ] Fruit spawn timing (appears after 70 and 170 dots eaten)
- [ ] Level 256 kill screen (half the maze corrupted)

---

## Phase 8 — Polish (Safe Enhancements Only)

**Allowed:**
- Richer colors using the full 9-bit RGB palette (512 colors per VDP)
- Smoother ghost siren using YM2151 FM modulation
- Clean HUD font rendering
- VDP-B palette cycling for energizer blink and maze flash
- Optional: subtle background pattern on VDP-B behind the maze

**Forbidden — these break gameplay fidelity:**
- Any change to maze topology or movement graph
- Any change to speed tables or timing
- Movement smoothing or interpolation
- AI modifications
- Resolution or aspect ratio changes to the gameplay coordinate space

---

## Build and Run

### Build

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
```

Produces `build/pacman.rom` and `build/pacman.sym`.

### Run (interactive)

```bash
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_frontend build/pacman.rom
```

### Run (headless / automated testing)

```bash
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless build/pacman.rom --frames 60
```

The headless binary runs the full emulator core without SDL/OpenGL/ImGui.
It supports frame-count execution (`--frames N`), framebuffer and audio
SHA-256 hash verification (`--expect-frame-hash`, `--expect-audio-hash`),
PPM frame dumps, input replay, and nonzero exit on mismatch — designed
for automated testing and CI. Coding agents should use `vanguard8_headless`
for build verification and regression testing.

### Dependencies

- **SjASM** assembler (Z80/HD64180)
- **Python 3** for extraction and build tools
- Vanguard 8 emulator (built from `/home/djglxxii/src/Vanguard8/`)

---

## Known Constraints and Risks

1. **Screen size reduction:** Arcade is 224x288 (rotated to 288x224). V8 is
   256x212. The 32px horizontal deficit and 12px vertical deficit mean the
   maze must be re-drawn at a slightly reduced scale. The movement graph
   must be preserved exactly — only wall art is adjusted.

2. **Frame rate difference:** Arcade runs at ~60.61 Hz, V8 at 59.94 Hz
   (NTSC). This is a ~1.1% speed difference. Gameplay timing must be
   adjusted to compensate — either run the game tick at a fixed rate
   independent of V-blank, or accept the minor speed difference (patterns
   may drift very slightly over long plays). Decision: accept the NTSC rate
   and adjust speed tables by the 1.1% factor.

3. **V-blank budget:** At 7.16 MHz with ~50 scanlines of V-blank (~22,750
   CPU cycles), we have a tight window for VDP updates. Sprite SAT update
   (48 bytes) and 1-2 HMMM tile blits should fit comfortably. HUD updates
   can be spread across frames.

4. **Sprite color limitation:** V9938 Sprite Mode 2 gives per-row color but
   only 1 color per row (plus transparent). Arcade sprites are 2bpp (4
   colors). Ghost sprites need careful design: the body color fills most
   rows, with eye color on the 2-3 eye rows. Pac-Man is single-color
   (yellow) so no issue there.

5. **Audio fidelity:** The arcade uses a custom wavetable synthesizer. PSG
   square waves will sound different but recognizable. The YM2151 FM can
   help bridge the gap for the siren and music, but exact waveform
   reproduction is not possible. This is an acceptable trade-off.
