# T004 — Palette Extraction and V8 Conversion

| Field | Value |
|---|---|
| ID | T004 |
| State | planned |
| Phase | Phase 1 — ROM Data Extraction |
| Depends on | T001 |
| Plan reference | `docs/PLAN.md` Phase 1, section 1.3 Palette Extraction |

## Goal

Create a reproducible extraction tool that converts the permitted Pac-Man color
PROMs into Vanguard 8 16-entry palette assets. This provides the color data
needed for maze reconstruction, sprite rendering, and later visual evidence.

## Scope

- In scope:
  - `tools/extract_palette.py` reads `pacman/82s126.4a` and
    `pacman/82s123.7f`.
  - Decode the 32 arcade RGB entries from the color PROM.
  - Decode the 16 arcade palette groups from the palette PROM.
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

*(None.)*

## Pre-flight

- [ ] T001 is completed and accepted.
- [ ] `pacman/82s126.4a` exists and is an allowed color PROM source.
- [ ] `pacman/82s123.7f` exists and is an allowed color PROM source.
- [ ] No other task is active.
- [ ] Confirm the arcade PROM resistor-weight conversion against public
  Pac-Man/MAME documentation before writing the decoder.

## Implementation notes

The Vanguard 8 V9938 palette format is two bytes per entry:
`RRR0GGG` then `00000BBB`. Each VDP has its own 16-entry palette.

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
