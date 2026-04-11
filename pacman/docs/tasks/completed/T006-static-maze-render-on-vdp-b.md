# T006 — Static maze render on VDP-B

| Field | Value |
|---|---|
| ID | T006 |
| State | completed |
| Phase | 1 Visual |
| Depends on | T004, T005 |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §2, §3.2, §5 |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/02-video.md` §Graphic 4, §VDP Command Engine |

## Goal

Render the Pac-Man maze as a static rotated playfield on VDP-B at boot,
replacing the T004 palette swatch. This is the first ROM-visible integration
of the T005 tile bank and establishes the framebuffer coordinates that later
movement, dot eating, and sprite placement tasks will use.

## Scope

In scope:

- Add an authored maze layout source under `vanguard8_port/assets/src/`
  describing the 28×30 arcade tile map using T005 tile-bank names or indices.
- Extend `tools/conv_tiles.py` or add a small companion converter so
  `assets/tile_nametable.bin` is generated reproducibly from the authored
  layout and `assets/tiles_vdpb.index.txt`.
- At boot, upload `tiles_vdpb.bin` to VDP-B tile-bank VRAM beginning at
  `0x7D00`.
- Render the rotated maze into the Graphic 4 framebuffer on VDP-B, centered
  with the documented 8 px horizontal border and 6-line top/bottom clipping.
- Replace the T004 swatch runtime display with the static maze render.
- Capture a frame showing the maze in correct colors on VDP-B.

Out of scope:

- Pac-Man, ghosts, fruit, or any sprites (T009 and later).
- HUD overlay text on VDP-A (T007).
- Dot removal, score changes, or gameplay state mutation (T012).
- Perfect final maze tile selection if a small number of decorative junction
  pieces need adjustment; this task should document any mismatches for T006
  review rather than silently hiding them.

## Implementation notes

The port plan rotates the game world 90° counter-clockwise: the arcade
28×30 active maze becomes a 30×28 tile landscape playfield. The visible
framebuffer is 256×212. The 240 px wide rotated playfield is centered at
screen X=8. The original 224 px maze height is clipped to 212 visible lines,
removing 6 px from the top and 6 px from the bottom.

Use VDP-B Graphic 4. The active framebuffer starts at VRAM `0x0000`; the
tile-bank source region starts at `0x7D00` per the plan. Prefer VDP command
engine copies if the current emulator supports them reliably; otherwise a
deterministic CPU-side VRAM stream is acceptable for this static bring-up,
provided the task log names the reason.

The authored layout is clean-room data: it may be created from public maze
diagrams and visual inspection of the already-extracted graphics, but not
from arcade code or disassembly. If the layout source has symbolic tile names,
the converter should fail loudly when a name is missing from
`tiles_vdpb.index.txt`.

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/tests/evidence/T006-maze/maze.png` — captured frame showing
  the static rotated maze on VDP-B.
- `vanguard8_port/tests/evidence/T006-maze/frame_hash.txt` — frame-60 hash
  for regression detection:
  `855ca25d699a8b1fe984aff1dc6ca3d1f505ebe8b01ce95a7786b0fbc6d45c49`.
- `vanguard8_port/tests/evidence/T006-maze/layout_checklist.txt` — manual
  checklist noting any known tile/layout mismatches, or stating none found.
- `vanguard8_port/tests/evidence/T006-maze/rerun_log.txt` — clean build and
  headless capture log.

**Reviewer checklist**:

- [ ] `maze.png` shows the Pac-Man maze rotated into landscape orientation.
- [ ] Maze walls are blue, dots are visible, power pellets are visible, and
      the ghost-house gate is visible.
- [ ] The maze is centered with 8 px horizontal gutters and no unintended
      non-black background outside the playfield.
- [ ] The top/bottom clipping matches the port plan: only black tunnel-border
      pixels are clipped, not active maze corridors.
- [ ] No T004/T005 regressions: palette swatch and tile-bank converter still
      reproduce their accepted hashes/counts when rerun.

**Rerun command:**

```
cd /home/djglxxii/src/pacman/vanguard8_port && rm -rf build && python3 tools/pack_rom.py && \
  /home/djglxxii/src/Vanguard8/build/src/vanguard8_headless \
    --rom build/pacman.rom --frames 60 \
    --dump-frame tests/evidence/T006-maze/maze.ppm \
    --hash-frame 60
```

## Progress log

- 2026-04-10 — created, state: planned.
- 2026-04-10 — activated after user approval of the task spec. Reviewed the
  T006 scope, VDP-B Graphic 4 layout, and T005 tile-bank outputs before
  implementing static maze rendering.
- 2026-04-10 — added clean-room `assets/src/maze_layout.txt`, extended
  `tools/conv_tiles.py` to generate `assets/tile_nametable.bin`, and replaced
  the boot-time palette swatch with a VDP-B static maze render.
- 2026-04-10 — fixed CPU VRAM page handling by setting R#14 for high-address
  VDP writes and resetting VDP-B R#14 before streaming the framebuffer. Without
  this, the tile-bank upload left the CPU VRAM pointer on the wrong 16 KB page.
- 2026-04-10 — captured frame-60 evidence under
  `vanguard8_port/tests/evidence/T006-maze/`; frame hash is
  `c3610aee20811d023a9cba43604d9bbbae499cd255c095586d0cdc79ec8298d2`.
- 2026-04-10 — applied `ANALYSIS-maze-distortion.md` corrections after review
  rejection: fixed `rotate_ccw()` to perform a true 90° counter-clockwise
  rotation and replaced `#` wall inference with a 30-token-per-row explicit
  tile-source layout. New frame-60 hash is
  `6e04314d154c9fb0563b5a236e9f7b31ffc689d2cac4d906dd5297ed18ea49bc`.
- 2026-04-10 — applied `ANALYSIS-maze-distortion-round2.md` corrections after
  second review rejection: replaced the hand-authored landscape grid with a
  native 28×36 arcade playfield tile grid from the cited public `pacman.c`
  reference, mechanically rotate that grid CCW in the converter, and decode
  tile pixels in the displayed tile-code orientation used by that reference.
  Added `tools/check_maze_layout.py`; it reports 576 wall seams checked, 16
  known arcade seam exceptions, and 0 unexpected mismatches. New frame-60 hash
  is `855ca25d699a8b1fe984aff1dc6ca3d1f505ebe8b01ce95a7786b0fbc6d45c49`.
- 2026-04-11 — approved by human reviewer and moved to completed.
