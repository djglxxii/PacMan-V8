# T007 — VDP-B Maze Render and Pellet Display

| Field | Value |
|---|---|
| ID | T007 |
| State | completed |
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

- [x] T006 is completed and accepted.
- [x] `assets/maze_v8_coordmap.bin`, `assets/maze_v8_drawlist.bin`,
  `assets/maze_v8_framebuffer.bin`, and `assets/maze_v8_manifest.txt` exist
  and match T006 observed hashes.
- [x] Review the Vanguard 8 V9938/VDP documentation for Graphic 4 framebuffer
  writes, palette upload, and any emulator-supported headless frame dump
  options needed for evidence.
- [x] Confirm no other task is active before activation.

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
- `tests/evidence/T007-vdp-b-maze-render/<frame>.png` — PNG conversion of the
  same frame for convenient visual inspection.

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
python3 tools/build.py
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --dump-frame tests/evidence/T007-vdp-b-maze-render/frame_060.ppm --hash-frame 60
```

**Observed values:**

- Runtime frame evidence:
  `tests/evidence/T007-vdp-b-maze-render/frame_060.ppm`
- Visual convenience copy:
  `tests/evidence/T007-vdp-b-maze-render/frame_060.png`
- Summary:
  `tests/evidence/T007-vdp-b-maze-render/summary.txt`
- Runtime frame size: `256x212`
- Runtime headless output: `Frame dump source: runtime`
- Emulator frame hash: `e4da302bef57d0d47f14c8790b0f57dde5660ccb67357035f8c29c160e590c97`
- Runtime PPM SHA-256:
  `ed2b2ca31ea62799d149fe50971f6142e68ab736d0468b256f7ccbd58b42acc6`
- Runtime PPM comparison against accepted T006 preview:
  byte-identical to
  `tests/evidence/T006-maze-tile-re-authoring/maze_v8_preview.ppm`
- ROM SHA-256:
  `03b97221eb793db6c28ffcaf61db39265324e6d6178b30b68a4a3279e01737db`
- `assets/maze_v8_framebuffer.bin` SHA-256:
  `78a7fedcb2f504a6f16ebb77aa196939a263a01c9a1d00a59ebff6a4656cb895`
- `assets/palette_b.bin` SHA-256:
  `99213a904be24a870047e41d1f2df48981fa9440c4e56959c7f74dd6fcd2a70e`

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created after T006 acceptance; state: planned. |
| 2026-04-16 | Activated with user authorization; beginning pre-flight and implementation survey. |
| 2026-04-16 | Added WIP VDP-B initialization: uploads `assets/palette_b.bin`, copies the T006 packed Graphic 4 framebuffer from two cartridge banks into VDP-B VRAM, keeps VDP-A color 0 transparent, and sets vertical scroll registers to zero. Build succeeds and ROM size is 49,152 bytes. |
| 2026-04-16 | Blocked on runtime frame evidence: the currently documented `cmake-build-debug` headless binary dumps a fixed fixture frame, while the newer runtime-dump binary aborts on an unsupported timed Z180 opcode before producing a PPM. Minimal repro and output are in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt`. |
| 2026-04-16 | User reported the emulator is patched; reactivated task to retry runtime frame capture and evidence generation. |
| 2026-04-16 | Retried the patched-looking `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` runtime dump. It now gets past the previous `0x01` blocker but aborts on unsupported timed Z180 opcode `0x79` at `PC=0x023B` in the VDP-B VRAM seek helper. The older `cmake-build-debug` binary still emits a fixed fixture-like dump, so T007 remains blocked on runtime frame evidence. |
| 2026-04-16 | User reported the emulator is patched again; reactivated task to retry runtime frame capture and evidence generation. |
| 2026-04-16 | Retried `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` after the second patch report. It still aborts on unsupported timed Z180 opcode `0x79` at `PC=0x023B`; refreshed blocker output in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt` includes available binary timestamps and Vanguard8 git status. |
| 2026-04-16 | User clarified the previous emulator work was only planned and reported it is now implemented; reactivated task to retry runtime frame capture. |
| 2026-04-16 | Retried `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` after the implemented patch report. It gets past `0x79` but now aborts on unsupported timed Z180 opcode `0x78` at `PC=0x023E`, still in the VDP-B VRAM seek helper. Refreshed blocker output in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt`. |
| 2026-04-16 | User reported opcode `0x78` is now implemented; reactivated task to retry runtime frame capture. |
| 2026-04-16 | Retried `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` after the `0x78` patch report. It gets past `0x78` but now aborts on unsupported timed Z180 opcode `0xF6` at `PC=0x0241`, still in the VDP-B VRAM seek helper. Refreshed blocker output in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt`. |
| 2026-04-16 | User asked to retry again; reactivated task to test the newly rebuilt runtime-dump emulator. |
| 2026-04-16 | Retried `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` after the `0xF6` patch. It now aborts on unsupported timed Z180 opcode `0x11` at `PC=0x020B` (`LD DE,nn`) in the framebuffer-load setup. Refreshed blocker output in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt`. |
| 2026-04-16 | User reported the emulator has been patched for `0x11`; reactivated task to retry runtime frame capture. |
| 2026-04-16 | Retried `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` after the `0x11` patch. It now aborts on unsupported timed Z180 opcode `0x7A` at `PC=0x0246` (`LD A,D`) in the framebuffer copy loop. Refreshed blocker output in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt`. |
| 2026-04-16 | User reported the emulator has been patched for `0x7A`; reactivated task to retry runtime frame capture. |
| 2026-04-16 | Retried `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` after the `0x7A` patch. It now aborts on unsupported timed Z180 opcode `0xB3` at `PC=0x0247` (`OR E`) in the framebuffer copy loop. Refreshed blocker output in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt`. |
| 2026-04-16 | User reported the emulator has been patched for `0xB3`; reactivated task to retry runtime frame capture. |
| 2026-04-16 | Retried `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` after the `0xB3` patch. It now aborts on unsupported timed Z180 opcode `0xC8` at `PC=0x0248` (`RET Z`) in the framebuffer copy loop. Refreshed blocker output in `tests/evidence/T007-vdp-b-maze-render/runtime_dump_blocker.txt`. |
| 2026-04-16 | Static audit of the current T007 ROM against the Vanguard8 emulator's execution and timing opcode tables predicts one additional blocker after `0xC8`: opcode `0x1B` at `PC=0x024D` (`DEC DE`). Recommendation: implement both remaining missing opcodes, `0xC8` (`RET Z`) and `0x1B` (`DEC DE`), so this task can complete; defer a full general opcode audit tool to a later task. |
| 2026-04-17 | User reported the emulator has been patched for the remaining missing opcodes; reactivated task to retry runtime frame capture and complete evidence generation. |
| 2026-04-17 | Runtime frame capture now succeeds with `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless`. Produced `frame_060.ppm`, `frame_060.png`, and `summary.txt`; the runtime PPM is 256x212, reports `Frame dump source: runtime`, and is byte-identical to the accepted T006 preview. Stopping for human review. |
| 2026-04-17 | Accepted by human reviewer and moved to completed. |

## Resolved blocker history

External system: Vanguard 8 headless emulator runtime frame dump.

Exact symptom after opcode `0xB3` retry: `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless`
aborts while running the ROM for a runtime PPM dump:

```text
Unsupported timed Z180 opcode 0xC8 at PC 0x248
```

Minimal repro:

```bash
python3 tools/build.py
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --dump-frame tests/evidence/T007-vdp-b-maze-render/frame_060.ppm --hash-frame 60
```

Additional context: `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless`
can run `--hash-frame`, but its `--dump-frame` output is fixture-like and
does not respond to ROM changes, so it cannot produce the human-verifiable
runtime frame capture required by this task. The patched-looking
`/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` binary is newer
and advertises separate `--dump-frame` and `--dump-fixture` options, but its
timed CPU path still lacks opcode `0xC8` (`RET Z`) for this ROM after getting
past the previous `0x79` (`LD A,C`), `0x78` (`LD A,B`), `0xF6` (`OR n`),
`0x11` (`LD DE,nn`), `0x7A` (`LD A,D`), and `0xB3` (`OR E`) blockers. The
repro artifact also records the current Vanguard8 git status and available
headless binary timestamps.

Static audit recommendation: for the current T007 ROM, the remaining known
missing opcodes are:

- `0xC8` at `PC=0x0248` — `RET Z`
- `0x1B` at `PC=0x024D` — `DEC DE`

Resolution needed: update/rebuild the Vanguard 8 emulator so both opcodes are
implemented in the extracted Z180 execution core and timed in
`Z180Adapter::current_instruction_tstates()`. That should allow the documented
headless runtime dump command to execute this ROM and emit the composed runtime
PPM. A full general opcode audit can be handled later after T007 is unblocked.
