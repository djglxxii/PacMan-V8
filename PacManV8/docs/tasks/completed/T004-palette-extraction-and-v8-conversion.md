# T004 — Palette Extraction and V8 Conversion

| Field | Value |
|---|---|
| ID | T004 |
| State | completed |
| Phase | Phase 1 — ROM Data Extraction |
| Depends on | T001 |
| Plan reference | `docs/PLAN.md` Phase 1, section 1.3 Palette Extraction |

## Goal

Create a reproducible extraction tool that converts the permitted Pac-Man color
PROMs into Vanguard 8 16-entry palette assets. This provides the color data
needed for maze reconstruction, sprite rendering, and later visual evidence.

## Scope

- In scope:
  - `tools/extract_palette.py` reads `pacman/82s123.7f` and
    `pacman/82s126.4a`.
  - Decode the 32 arcade RGB entries from the color PROM.
  - Decode the 64 arcade palette groups from the lookup PROM.
  - Convert arcade colors to V9938 9-bit RGB values.
  - Assign separate VDP-A and VDP-B 16-entry palettes for the planned render
    split.
  - Write `assets/palette_a.bin`, `assets/palette_b.bin`, and a manifest.
  - Produce evidence output under `tests/evidence/T004-palette-extraction/`.

- Out of scope:
  - Tile, sprite, maze, or sound extraction.
  - Runtime palette upload code.
  - Emulator frame-capture rendering.
  - Visual polish or final color tuning beyond the first reproducible mapping.

## Scope changes

- Corrected the documented PROM roles after checking MAME's Pac-Man video
  driver: `82s123.7f` is the 32x8 RGB palette PROM, and `82s126.4a` is the
  256x4 color lookup PROM arranged as 64 groups of 4 pens.

## Pre-flight

- [x] T001 is completed and accepted.
- [x] `pacman/82s126.4a` exists and is an allowed color PROM source.
- [x] `pacman/82s123.7f` exists and is an allowed color PROM source.
- [x] No other task is active.
- [x] Confirm the arcade PROM resistor-weight conversion against public
  Pac-Man/MAME documentation before writing the decoder.

## Implementation notes

The Vanguard 8 V9938 palette format is two bytes per entry:
`RRR0GGG` then `00000BBB`. Each VDP has its own 16-entry palette.

The source PROM roles are:

- `82s123.7f`: 32-byte RGB palette PROM. Bits 0-2 drive red through
  1000/470/220 ohm resistors, bits 3-5 drive green through the same resistor
  weights, and bits 6-7 drive blue through 470/220 ohm resistors.
- `82s126.4a`: 256-byte color lookup PROM. It contains 64 groups of 4
  low-nibble color indices selecting entries from `82s123.7f`.

The plan calls for VDP-B to contain background/maze colors and VDP-A to contain
transparent color 0, Pac-Man yellow, ghost body colors, eyes, frightened colors,
text, and fruit/HUD colors. The first pass should be deterministic and
manifested; final aesthetic tuning belongs to later visual polish tasks.

The extractor may read the allowed color PROMs only. It must not read the
restricted program ROMs or sound PROMs.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T004-palette-extraction/extract_palette.log` — extraction
  stdout from `tools/extract_palette.py`.
- `tests/evidence/T004-palette-extraction/palette_manifest.txt` — copy of the
  generated palette manifest.
- `tests/evidence/T004-palette-extraction/palette_summary.txt` — compact
  summary of source/output sizes, hashes, and assigned palette entries.

**Reviewer checklist** (human ticks these):

- [ ] `python3 tools/extract_palette.py` completes without errors.
- [ ] `assets/palette_a.bin` is exactly `32` bytes (`16 entries * 2 bytes`).
- [ ] `assets/palette_b.bin` is exactly `32` bytes (`16 entries * 2 bytes`).
- [ ] The manifest records all 32 decoded arcade RGB entries and both V8
  palette assignments.
- [ ] The summary shows stable SHA-256 values for both PROM inputs and both
  output palettes.
- [ ] No restricted program or sound PROM files are read by the extractor.

**Observed values:**

- RGB palette PROM bytes: `32`
- RGB palette PROM SHA-256:
  `48fe0b01d68e3d702019ca715f7266c8e3261c769509b281720f53ca0a1cc8fb`
- Color lookup PROM bytes: `256`
- Color lookup PROM SHA-256:
  `ef8f7a3b0c10f787d9cc1cbc5cc266fcc1afadb24c3b4d610fe252b9c3df1d76`
- Decoded RGB entries: `32`
- Decoded lookup groups: `64`
- Output VDP-A palette bytes: `32`
- Output VDP-A palette SHA-256:
  `7e821cb405d1d30ae6ef29bf75fde5a87637c7e381566eaf750f895dc834b78f`
- Output VDP-B palette bytes: `32`
- Output VDP-B palette SHA-256:
  `99213a904be24a870047e41d1f2df48981fa9440c4e56959c7f74dd6fcd2a70e`
- PROMs read: `pacman/82s123.7f`, `pacman/82s126.4a`
- Restricted PROMs read: `none`
- Regression check: `python3 tools/build.py` completed, ROM size `16,384`
  bytes, symbol count `7`

**Rerun command:**

```bash
python3 tools/extract_palette.py | tee tests/evidence/T004-palette-extraction/extract_palette.log
cp assets/palette_manifest.txt tests/evidence/T004-palette-extraction/palette_manifest.txt
cp assets/palette_summary.txt tests/evidence/T004-palette-extraction/palette_summary.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created, state: planned. |
| 2026-04-15 | Activated task; starting PROM palette decoder and V8 conversion assets. |
| 2026-04-15 | Corrected the Phase 1 palette plan after checking MAME's Pac-Man video driver: `82s123.7f` is the 32x8 RGB palette PROM, and `82s126.4a` is the 256x4 color lookup PROM. |
| 2026-04-15 | Implemented `tools/extract_palette.py`, generated `assets/palette_a.bin`, `assets/palette_b.bin`, manifest, summary, and evidence. Verified with `py_compile`, byte-for-byte evidence regeneration, scoped restricted-source review, and the existing build. Stopping for human review. |
| 2026-04-15 | Accepted by human reviewer and moved to completed. |
