# T007 — VDP-B Maze Render and Pellet Display

| Field | Value |
|---|---|
| ID | T007 |
| State | planned |
| Phase | Phase 2 — Maze Reconstruction |
| Depends on | T006 |
| Plan reference | `docs/PLAN.md` Phase 2 — Maze Reconstruction for V8; Phase 4.1 Frame Update Flow |

## Goal

Render the fitted portrait maze from T006 on VDP-B in the Vanguard 8 ROM so a
human can inspect the actual emulator output. This is the first runtime use of
the generated maze presentation assets.

## Scope

- In scope:
  - Add VDP-B maze initialization/render code under `src/`, using the existing
    project style or introducing `src/vdp_b.asm`/data include files if that is
    the cleanest local structure.
  - Include the generated T006 maze assets needed for the initial VDP-B
    framebuffer contents.
  - Initialize the VDP-B palette from `assets/palette_b.bin` or an equivalent
    deterministic assembler include generated from that asset.
  - Show the fitted portrait maze on VDP-B with pellets, energizers, tunnels,
    ghost house, and ghost door visible.
  - Keep VDP-A transparent enough that the VDP-B maze is visible through the
    compositor.
  - Produce headless emulator frame evidence under
    `tests/evidence/T007-vdp-b-maze-render/`.

- Out of scope:
  - Pellet consumption, pellet erase queues, energizer blinking, or gameplay
    state updates.
  - Pac-Man, ghost, fruit, score, lives, or HUD rendering beyond whatever
    minimal transparent foreground setup is needed to see VDP-B.
  - Movement, collision, input handling, AI, or audio.
  - Re-authoring T006 layout data or changing maze topology.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T006 is completed and accepted.
- [ ] `assets/maze_v8_coordmap.bin`, `assets/maze_v8_drawlist.bin`,
  `assets/maze_v8_framebuffer.bin`, and `assets/maze_v8_manifest.txt` exist
  and match T006 observed hashes.
- [ ] Review the Vanguard 8 V9938/VDP documentation for Graphic 4 framebuffer
  writes, palette upload, and any emulator-supported headless frame dump
  options needed for evidence.
- [ ] Confirm no other task is active before activation.

## Implementation notes

T006 produced a full packed Graphic 4 framebuffer:
`assets/maze_v8_framebuffer.bin` is 27,136 bytes, matching 212 rows by 128
bytes per row. The simplest acceptable implementation is to place that data in
ROM and copy it into VDP-B framebuffer VRAM during scene initialization, as
long as the copy path is deterministic and documented.

The T006 manifest records the fitted bounds as `x=16-239`, `y=8-203`, with
16px black side margins. The runtime image should visually match
`tests/evidence/T006-maze-tile-re-authoring/maze_v8_preview.ppm`.

If the emulator or documented VDP command surface cannot upload the framebuffer
or dump a frame as needed, move this task to `blocked/` with the exact command,
error, and minimal repro.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T007-vdp-b-maze-render/<frame>.ppm` — headless emulator frame
  showing the VDP-B-rendered fitted maze.
- `tests/evidence/T007-vdp-b-maze-render/<summary>.txt` — build/run output,
  frame hash, and any asset hashes needed to confirm deterministic rendering.

**Reviewer checklist** (human ticks these):

- [ ] The emulator frame is 256x212 and shows the portrait maze centered with
  black side margins.
- [ ] Walls, pellets, energizers, tunnels, ghost house, and ghost door are
  visible and match the T006 preview geometry.
- [ ] VDP-A transparency does not obscure the VDP-B maze.
- [ ] The summary records stable hashes for the ROM, frame evidence, and maze
  assets used by the render.
- [ ] No gameplay, movement, AI, audio, or pellet-consumption behavior is
  introduced in this task.

**Rerun command:**

```bash
# To be finalized when T007 is implemented.
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created after T006 acceptance; state: planned. |

## Blocker (only if state = blocked)

*(None.)*
