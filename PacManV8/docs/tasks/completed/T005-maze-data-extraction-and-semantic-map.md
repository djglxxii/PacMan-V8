# T005 — Maze Data Extraction and Semantic Map

| Field | Value |
|---|---|
| ID | T005 |
| State | completed |
| Phase | Phase 1 — ROM Data Extraction |
| Depends on | T002, T004 |
| Plan reference | `docs/PLAN.md` Phase 1, section 1.5 Maze Data Extraction |

## Goal

Create a reproducible extraction tool that derives the level-1 Pac-Man maze
tilemap, color selections, semantic occupancy grid, and movement graph needed
by later rendering and gameplay tasks.

## Scope

- In scope:
  - `tools/extract_maze.py` reads only the inputs required for maze data:
    `pacman/pacman.6e` through `pacman/pacman.6j` for documented data tables,
    plus the already-generated tile and palette assets needed for summaries.
  - Locate and extract the level-1 default maze tilemap and color data tables.
  - Convert arcade video/color RAM layout into a 36-row by 28-column arcade
    orientation nametable.
  - Build a semantic grid using stable numeric cell classes:
    `WALL`, `PATH`, `PELLET`, `ENERGIZER`, `GHOST_HOUSE`, `GHOST_DOOR`,
    `TUNNEL`, and `BLANK`.
  - Build a compact movement graph with intersections, corners, tunnel
    endpoints, energizer positions, ghost-house entry/exit points, and edge
    lengths.
  - Write `assets/maze_nametable.bin`, `assets/maze_semantic.bin`,
    `assets/maze_graph.bin`, and manifest/summary files.
  - Produce evidence output under `tests/evidence/T005-maze-data-extraction/`.

- Out of scope:
  - Disassembling or reverse-engineering Pac-Man program logic from the program
    ROMs.
  - Re-authoring the maze art for the Vanguard 8 screen.
  - Runtime rendering, VDP upload code, or gameplay movement code.
  - Any changes to tile or palette extraction outputs.

## Scope changes

*(None.)*

## Pre-flight

- [x] T002 is completed and accepted.
- [x] T004 is completed and accepted.
- [x] `pacman/pacman.6e` through `pacman/pacman.6j` exist.
- [x] Confirm the source and address range of the maze tilemap/color tables
  from public Pac-Man documentation before writing the extractor.
- [x] Confirm the extractor reads program ROM bytes only as data tables and
  does not disassemble, emulate, or replicate program logic.
- [x] No other task is active.

## Implementation notes

The repo operating contract permits extraction tools to read
`pacman/pacman.6e` through `pacman/pacman.6j` only to locate data tables such
as tilemap layout and color assignments. This task must stay inside that
boundary: no opcode decoding, no control-flow analysis, and no gameplay logic
derived from program ROM instructions.

The plan calls for arcade-orientation data first. Keep coordinate transforms
to Vanguard 8 screen space out of this task; T006 owns re-authoring and fit.
The manifest should make the tilemap source offsets, output dimensions, cell
class counts, graph node count, graph edge count, and all hashes easy to
review.

Use deterministic binary formats and document them in the manifest. Prefer
simple fixed-width records so later assembly code can consume the assets
without parsing text.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T005-maze-data-extraction/extract_maze.log` — extraction
  stdout from `tools/extract_maze.py`.
- `tests/evidence/T005-maze-data-extraction/maze_manifest.txt` — copy of the
  generated maze manifest.
- `tests/evidence/T005-maze-data-extraction/maze_summary.txt` — compact
  summary of source/output sizes, hashes, semantic counts, and graph counts.

**Reviewer checklist** (human ticks these):

- [ ] `python3 tools/extract_maze.py` completes without errors.
- [ ] `assets/maze_nametable.bin` has the documented dimensions and byte size.
- [ ] `assets/maze_semantic.bin` has the documented dimensions and byte size.
- [ ] `assets/maze_graph.bin` contains deterministic node and edge records.
- [ ] The manifest identifies the data-table source offsets used from the
  program ROMs.
- [ ] The summary shows stable SHA-256 values for all program ROM inputs and
  maze output assets.
- [ ] The extractor does not disassemble or derive behavior from program ROM
  instructions.

**Rerun command:**

```bash
python3 tools/extract_maze.py | tee tests/evidence/T005-maze-data-extraction/extract_maze.log
cp assets/maze_manifest.txt tests/evidence/T005-maze-data-extraction/maze_manifest.txt
cp assets/maze_summary.txt tests/evidence/T005-maze-data-extraction/maze_summary.txt
```

**Observed values:**

- Program ROM bytes: `16,384`
- Concatenated program ROM SHA-256:
  `e9d4817d70bf1931c25e39a3d626e05dd0d5902d9400097316248a52ff627b77`
- Maze tile table source: `0x3435-0x35B1`
- Maze tile table encoded bytes: `381`
- Maze tile table expanded bytes: `448`
- Maze color table source: `0x35B5-0x36A4`
- Maze color table raw bytes: `240`
- Maze color table raw SHA-256:
  `cf6abcb9654a97baee39d1fe6e4b4e565eb3f9ea7ecca84ee083bb0819b1427c`
- `assets/maze_nametable.bin` bytes: `1008`
- `assets/maze_nametable.bin` SHA-256:
  `3c2cd199a6c5e50ccc961d4a3960097df8fe4adf2b91ca24ba058f89d4bb029a`
- `assets/maze_semantic.bin` bytes: `1008`
- `assets/maze_semantic.bin` SHA-256:
  `ca8c00e7b76da593a4fc2e9c8f064dde3ac0d062ee5cce1687500850325db111`
- `assets/maze_graph.bin` bytes: `2520`
- `assets/maze_graph.bin` SHA-256:
  `4b355ccce9f28ad8acab093f7726287140dbcdf3429554a46473103caa1405a2`
- Semantic counts: `WALL=488`, `PATH=104`, `PELLET=240`,
  `ENERGIZER=4`, `GHOST_HOUSE=18`, `GHOST_DOOR=2`, `TUNNEL=12`,
  `BLANK=140`
- Movement graph: `132` nodes, `181` edges
- Graph header validation: magic `PMVGRAF1`, version `1`, expected size
  `2520` bytes
- Regression check: `python3 tools/build.py` completed, ROM size `16,384`
  bytes, symbol count `7`

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created, state: planned. |
| 2026-04-15 | Activated after user authorization; beginning pre-flight and plan review. |
| 2026-04-15 | Implemented `tools/extract_maze.py`, generated maze nametable, semantic grid, movement graph, manifest, summary, and evidence. Verified with `py_compile`, evidence copy comparison, graph header/size validation, scoped restricted-source review, and the existing build. Stopping for human review. |
| 2026-04-15 | Accepted by human reviewer and moved to completed. |

## Blocker (only if state = blocked)

*(None.)*
