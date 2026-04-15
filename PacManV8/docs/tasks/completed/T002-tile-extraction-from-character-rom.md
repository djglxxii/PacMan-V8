# T002 — Tile Extraction from Character ROM

| Field | Value |
|---|---|
| ID | T002 |
| State | completed |
| Phase | Phase 1 — ROM Data Extraction |
| Depends on | T001 |
| Plan reference | `docs/PLAN.md` Phase 1, section 1.1 Tile Extraction |

## Goal

Create a reproducible extraction tool that decodes the permitted Pac-Man
character ROM into Vanguard 8 Graphic 4 tile data. This establishes the first
asset conversion path used by later palette, maze, and render tasks.

## Scope

- In scope:
  - `tools/extract_tiles.py` reads `pacman/pacman.5e`.
  - Decode 256 8x8 2bpp tiles from the planar character ROM format.
  - Convert decoded pixels to V9938 Graphic 4 4bpp packed bytes.
  - Write `assets/tiles_vdpb.bin`.
  - Write a manifest with per-tile metadata and coarse visual classification.
  - Produce evidence output under `tests/evidence/T002-tile-extraction/`.

- Out of scope:
  - Palette conversion from PROMs.
  - Sprite extraction from `pacman.5f`.
  - Maze tilemap extraction from program ROMs.
  - Rendering the extracted tiles in the Vanguard 8 emulator.

## Scope changes

*(None.)*

## Pre-flight

- [x] T001 is completed and accepted.
- [x] `pacman/pacman.5e` exists and is an allowed extraction source.
- [x] No active task existed before T002 activation.

## Implementation notes

The plan defines each character tile as 16 bytes. The corrected format is the
MAME Pac-Man `tilelayout`: each row uses one byte for pixels 4-7 and one byte
for pixels 0-3, with bitplane 0 in bits 0-3 and bitplane 1 in bits 4-7 of
each byte. The V9938 Graphic 4 output stores two pixels per byte, high nibble
first.

The manifest classification is intentionally coarse at this stage because
palette groups and maze semantics are handled by later tasks. T002 records
shape-derived categories that can be refined when palette and maze context
exists.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T002-tile-extraction/extract_tiles.log` — extraction stdout
  from `tools/extract_tiles.py`.
- `tests/evidence/T002-tile-extraction/tiles_manifest.txt` — copy of the
  generated tile manifest.
- `tests/evidence/T002-tile-extraction/tiles_summary.txt` — compact summary of
  output sizes, hashes, and classification counts.

**Reviewer checklist** (human ticks these):

- [ ] `python3 tools/extract_tiles.py` completes without errors.
- [ ] `assets/tiles_vdpb.bin` is exactly `8192` bytes (`256 tiles * 32 bytes`).
- [ ] The manifest contains exactly `256` tile rows after its header.
- [ ] The summary shows stable SHA-256 values for the character ROM and output
  tile bank.
- [ ] No restricted program or sound PROM files are read by the extractor.

**Observed values:**

- Source ROM bytes: `4096`
- Source ROM SHA-256:
  `8d9a86c97fe94b1fd010b139672c330e3b257ba59b0d8df7a821592e30a77b4b`
- Output tile bank bytes: `8192`
- Output tile bank SHA-256:
  `ac43ac81d51248325ad510c2ef7b37b7fc56d77cd3efba016f3c055863b3e7c6`
- Manifest tile rows: `256`
- Classification counts: `blank=61`, `pellet=14`, `energizer=2`,
  `wall=168`, `text_character=11`, `fruit_icon=0`
- Regression check: `python3 tools/build.py` completed, ROM size `16,384`
  bytes, symbol count `7`

**Rerun command:**

```bash
python3 tools/extract_tiles.py | tee tests/evidence/T002-tile-extraction/extract_tiles.log
cp assets/tiles_manifest.txt tests/evidence/T002-tile-extraction/tiles_manifest.txt
cp assets/tiles_summary.txt tests/evidence/T002-tile-extraction/tiles_summary.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created and activated from the task index because the planned task file was missing and the user authorized proceeding to the next available task. |
| 2026-04-15 | Corrected the Phase 1 tile-format plan note before implementing extraction. The ROM uses the MAME Pac-Man packed-nibble tile layout, not separate 8-byte planes. |
| 2026-04-15 | Implemented `tools/extract_tiles.py`, generated `assets/tiles_vdpb.bin`, manifest, and summary evidence. Verified the extractor with `py_compile`, confirmed no restricted ROM references, and reran the existing build successfully. Stopping for human review. |
| 2026-04-15 | Accepted by human reviewer and moved to completed. |
