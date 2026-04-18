# T013 — Sprite Rendering and Animation

| Field | Value |
|---|---|
| ID | T013 |
| State | completed |
| Phase | Phase 4 — Rendering Layer |
| Depends on | T003, T008, T009, T010, T012 |
| Plan reference | `docs/PLAN.md` Phase 4.1 Frame Update Flow; Phase 4.2 Sprite Rendering |

## Goal

Implement the first VDP-A sprite-rendering slice: upload the extracted Sprite
Mode 2 assets, maintain a sprite attribute/color shadow, and render Pac-Man and
the four ghosts over the existing VDP-B maze with deterministic animation
states suitable for visual review.

## Scope

- In scope:
  - Add VDP-A sprite pattern/color upload from `assets/sprites.bin` and
    `assets/sprite_colors.bin` during boot or initialization.
  - Add a small runtime sprite attribute table shadow for Sprite Mode 2.
  - Render Pac-Man and the four ghost sprite slots on VDP-A over the existing
    transparent foreground layer.
  - Map the current T008/T009 arcade-grid positions to visible V8 sprite
    coordinates using a simple documented mapping or existing coordinate data
    sufficient for this slice.
  - Select normal Pac-Man mouth frames and ghost direction/animation frames
    from deterministic frame counters or test states.
  - Reflect T010/T012 data-level state boundaries where practical: normal
    ghost color, frightened color/frame selection, and hidden or held house
    states should be represented as deterministic sprite attributes rather
    than full movement/pathing.
  - Add a deterministic local harness or debug setup that places all five
    sprites in visible, non-overlapping review positions and records the
    selected sprite IDs, SAT bytes, and asset hashes.
  - Produce frame-capture evidence under
    `tests/evidence/T013-sprite-rendering-animation/`.

- Out of scope:
  - HUD text, score/lives/fruit rendering, point-value popups, or font tile
    blits.
  - VDP-B pellet erase updates or energizer palette blinking.
  - Full coordinate transform/rotation fidelity beyond the documented mapping
    needed to show sprites; T015 owns the final transform validation.
  - Full ghost movement stepping, in-house bouncing, door crossing, or eaten
    eyes return pathing.
  - Audio, scoring, lives decrement, game-state flow, level progression, or
    attract mode.

## Scope changes

- 2026-04-18: Fixed two bugs in `tools/extract_sprites.py` discovered during
  T013 visual review. The rendered sprites came out as clearly transposed
  (rotated 90° with eyes stacked vertically instead of side-by-side), which
  was traced to two problems working together:
  1. The `X_BIT_OFFSETS` and `Y_BIT_OFFSETS` tables had their contents assigned
     to the wrong variables. In pacman.5f, each byte encodes 4 vertical pixels
     of a single column, so advancing by one column moves one byte forward and
     advancing by one row moves one bit forward — the opposite of what the
     original code assumed. Swapping the two tables' contents fixes the
     transpose.
  2. `read_bit` indexed from the LSB of each byte, but the MAME-style bit
     offsets in the offset tables are counted from the MSB. Without this,
     even with the tables correctly assigned every 4-pixel column group
     within each byte is left-right mirrored and the two 2bpp planes are
     swapped. Changed `read_bit` to compute `bit_index = 7 - (bit_offset % 8)`.
  `assets/sprites.bin` and `assets/sprite_colors.bin` both change (the per-row
  dominant colors are derived from the decoded pixels). Updated the expected
  hash constants in `tools/sprite_render_tests.py`, regenerated the review
  shadow, rebuilt the ROM, and recaptured the T013 evidence with the
  emulator build referenced in the task's rerun command
  (`Vanguard8/build/src/vanguard8_headless`, not the older `cmake-build-debug`
  binary). Upstream T003 remains completed; a forward-pointer note was added
  to that task file.

## Pre-flight

- [x] T003, T008, T009, T010, and T012 are completed and accepted.
- [x] Review `docs/PLAN.md` Phase 4.1 and Phase 4.2 before implementation.
- [x] Review `docs/tasks/completed/T003-sprite-extraction-from-sprite-rom.md`
  for sprite pattern/color bank format and accepted hashes.
- [x] Review `docs/tasks/completed/T008-movement-system-and-turn-buffering.md`
  for the 8.8 fixed-point arcade-coordinate position contract.
- [x] Review `docs/tasks/completed/T009-ghost-ai-and-targeting.md` for ghost
  record layout, direction enum, and ghost IDs.
- [x] Review `docs/tasks/completed/T010-scatter-chase-timer-and-frightened-mode.md`
  for normal/frightened mode fields.
- [x] Review `docs/tasks/completed/T012-ghost-house-logic.md` for house state
  values and pending/exiting boundaries.
- [x] Consult the Vanguard 8 hardware spec for V9938 Sprite Mode 2 pattern,
  color, and attribute table addresses before writing VDP upload code.
- [x] Confirm no other task is active before activation.

## Implementation notes

Keep VDP-A color `0` transparent so the existing VDP-B maze remains visible
behind sprites. The current `src/main.asm` already configures Graphic 4 and
transparent VDP-A output; this task should extend that path with sprite asset
upload and SAT updates.

Use the T003 asset contract:

- `assets/sprites.bin`: `2048` bytes, 64 Sprite Mode 2 16x16 patterns.
- `assets/sprite_colors.bin`: `1024` bytes, 64 sprites by 16 row colors.
- Accepted hashes from T003 should be recorded in the T013 evidence output.

The sprite budget from the plan is six slots. This task should populate slots
`0..4` for Pac-Man, Blinky, Pinky, Inky, and Clyde. Slot `5` is reserved for
later fruit/score rendering and may remain hidden.

Avoid turning this into the final coordinate-transform task. If the first
slice uses a direct arcade-to-screen scale/offset or a small debug placement
table to make the sprites visually inspectable, document that mapping in the
evidence vectors and leave final rotation/fit validation for T015.

Because V9938 Sprite Mode 2 has one visible color per row, ghost body/eye
fidelity depends on row-color selection. If a runtime color override is needed
for Blinky/Pinky/Inky/Clyde/frightened display, implement it as a deterministic
table and record the chosen palette indices in the evidence.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T013-sprite-rendering-animation/sprite_frame.ppm` — PPM
  frame dump from the headless emulator showing Pac-Man and the four ghosts
  rendered over the maze on VDP-A.
- `tests/evidence/T013-sprite-rendering-animation/sprite_render_tests.txt` —
  stdout from the deterministic sprite render harness or evidence script.
- `tests/evidence/T013-sprite-rendering-animation/sprite_render_vectors.txt`
  — readable summary of sprite slot assignments, selected pattern/color
  indices, SAT bytes or fields, asset hashes, and frame-capture hash.

**Reviewer checklist** (human ticks these):

- [ ] Frame capture shows the VDP-B maze still visible with VDP-A transparent
  background.
- [ ] Pac-Man and all four ghosts are visible as 16x16 sprites in expected
  review positions.
- [ ] Sprite slot assignment matches the plan: Pac-Man `0`, ghosts `1..4`,
  fruit/score slot `5` hidden or reserved.
- [ ] Pac-Man animation frame selection is deterministic and recorded.
- [ ] Ghost normal/frightened/house-state sprite selection boundaries are
  deterministic and recorded, without adding movement/pathing scope.
- [ ] Evidence output records sprite asset hashes, SAT fields/bytes, frame
  hash, and deterministic pass/fail results.
- [ ] No HUD, scoring, lives, fruit behavior, audio, pellet erase rendering,
  coordinate-transform task work, or game-flow transitions are introduced.

**Rerun command:**

```bash
python3 tools/generate_sprite_review_shadow.py
python3 tools/build.py
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --dump-frame tests/evidence/T013-sprite-rendering-animation/sprite_frame.ppm --hash-frame 60
python3 tools/sprite_render_tests.py --vectors-output tests/evidence/T013-sprite-rendering-animation/sprite_render_vectors.txt --frame-dump tests/evidence/T013-sprite-rendering-animation/sprite_frame.ppm > tests/evidence/T013-sprite-rendering-animation/sprite_render_tests.txt
```

**Observed evidence values:**

- `sprite_frame.ppm` SHA-256:
  `fdeeaa7dcb59fd710ecbd1a84d3083259c7f8a0986eded2a33b1f1bd785eba16`
- `sprite_render_tests.txt` SHA-256:
  `0e3df4c4761486ad01fadd04a71c8692a942141d8ab559863685e0507dbf69db`
- `sprite_render_vectors.txt` SHA-256:
  `104362c72ff88e06c67276943418b0ff66d6b9692d5d0a87cf1ba498dbaadc41`
- Sprite render test result: `8/8 passed`
- Runtime frame capture:
  - Frame dump source: `runtime`
  - Frame size: `256x212`
  - Emulator `--hash-frame 60` SHA-256:
    `fdeeaa7dcb59fd710ecbd1a84d3083259c7f8a0986eded2a33b1f1bd785eba16`
  - Event log digest: `3984620313185289862`
- Input/generated asset hashes recorded by the evidence:
  - `assets/sprites.bin`:
    `28e586b9ff65658f94928b190aff143a514cace76a5c95409ad989666407304b`
  - `assets/sprite_colors.bin`:
    `8795faea939d4fffaef5cb60fbf94bfaade78540deafb919564b17eec9bb5308`
  - `assets/palette_a.bin`:
    `7e821cb405d1d30ae6ef29bf75fde5a87637c7e381566eaf750f895dc834b78f`
  - SAT shadow:
    `259b117ec038486ac171ba3465d978d0ea3cc3efcc2a8b8720c290339c1cfa53`
  - Color shadow:
    `5d86eb101f66c814c0fb238448a80c0ae6a26193e62eace05398001198b5e87a`
- Deterministic review slots:
  - Pac-Man slot `0`: sprite ID `1`, pattern `4`, palette `1`, `(56,96)`.
  - Blinky slot `1`: sprite ID `8`, pattern `32`, palette `2`, `(88,96)`.
  - Pinky slot `2`: frightened sprite ID `50`, pattern `200`, palette `8`,
    `(120,96)`.
  - Inky slot `3`: house-waiting sprite ID `32`, pattern `128`, palette `4`,
    `(152,96)`.
  - Clyde slot `4`: house-exiting sprite ID `9`, pattern `36`, palette `5`,
    `(184,96)`.
  - Reserved slot `5`: terminator SAT entry `D0 00 00 00 00 00 00 00`.
- Build verification:
  `python3 tools/build.py` passed; ROM size `49,152` bytes, symbol count `98`.
- Regression verification:
  `tools/movement_tests.py`, `tools/ghost_ai_tests.py`,
  `tools/mode_timer_tests.py`, `tools/collision_tests.py`, and
  `tools/ghost_house_tests.py` all passed using temporary vectors under
  `build/`.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-18 | Created after T012 acceptance; state: planned. |
| 2026-04-18 | Activated after user request; confirmed no other task active and synced `docs/tasks/INDEX.md`. |
| 2026-04-18 | Implemented VDP-A sprite palette/pattern/color/SAT upload, generated deterministic review shadow data from `assets/sprite_colors.bin`, added runtime SAT/color shadow upload in `src/sprites.asm`, corrected the V9938 sprite pattern base register to `R#6=0x0E` for VRAM `0x7000`, and added `tools/sprite_render_tests.py`. Generated frame/test/vector evidence under `tests/evidence/T013-sprite-rendering-animation/`, verified Python compilation, ROM assembly, T008-T012 regressions, and a 60-frame runtime headless capture. Stopping for human review. |
| 2026-04-18 | Human review flagged sprites rendering as transposed ghosts (rotated 90°, eyes stacked vertically). Initial hypothesis of a V9938 quadrant-packing bug was wrong; corrective patch against `pack_mode2_pattern` made the artifact worse. Reverted, read the emulator's `sprite_pattern_row_bytes` directly, and confirmed the V9938 stores 16x16 quadrants as TL, TR, BL, BR — the packer was already correct. Instead, root-caused to `extract_sprites.py` having two independent defects: the X_BIT_OFFSETS and Y_BIT_OFFSETS table contents were swapped (causing the transpose), and `read_bit` used LSB-first bit indexing while the MAME-style bit offsets are MSB-first (causing local 4-pixel column mirroring plus plane swap). Fixed both, regenerated `assets/sprites.bin` and `assets/sprite_colors.bin`, updated the expected hash constants in `tools/sprite_render_tests.py`, regenerated the review shadow, rebuilt the ROM, and recaptured the 60-frame headless dump with `Vanguard8/build/src/vanguard8_headless` (the binary referenced in the task's rerun command; I had been using the older `cmake-build-debug` binary, which was the reason earlier attempts appeared to render nothing). `sprite_render_tests.py` reports 8/8 pass. Visually verified the five review slots now render as a yellow Pac-Man, red Blinky with clean rounded-top/wavy-feet silhouette, frightened-blue Pinky, cyan Inky, and orange Clyde. Added a forward-pointer note in the completed T003 task file and a field-manual entry on the pacman.5f sprite ROM layout. Stopping for human review of the corrected frame. |
| 2026-04-18 | Accepted by human reviewer and moved to completed. |

## Blocker (only if state = blocked)

*(None.)*
