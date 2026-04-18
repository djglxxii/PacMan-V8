# T003 — Sprite Extraction from Sprite ROM

| Field | Value |
|---|---|
| ID | T003 |
| State | completed |
| Phase | Phase 1 — ROM Data Extraction |
| Depends on | T001 |
| Plan reference | `docs/PLAN.md` Phase 1, section 1.2 Sprite Extraction |

## Goal

Create a reproducible extraction tool that decodes the permitted Pac-Man sprite
ROM into Vanguard 8 Sprite Mode 2 pattern and color data. This supplies the
sprite assets needed later for Pac-Man, ghosts, fruit, and animation evidence.

## Scope

- In scope:
  - `tools/extract_sprites.py` reads `pacman/pacman.5f`.
  - Decode 64 16x16 2bpp sprites from the Pac-Man sprite ROM format.
  - Convert each decoded sprite to V9938 Sprite Mode 2 1bpp pattern data.
  - Generate per-row color-table data from the dominant non-transparent source
    color for each sprite row.
  - Write `assets/sprites.bin`, `assets/sprite_colors.bin`, and a manifest.
  - Produce evidence output under `tests/evidence/T003-sprite-extraction/`.

- Out of scope:
  - Palette PROM conversion.
  - Sprite animation sequencing.
  - Runtime sprite upload or rendering in the Vanguard 8 emulator.
  - Gameplay use of sprites.

## Scope changes

- 2026-04-18: Two defects in `tools/extract_sprites.py` surfaced when T013
  first rendered sprites on VDP-A. (1) `X_BIT_OFFSETS` and `Y_BIT_OFFSETS`
  had their contents assigned to the wrong variables — pacman.5f stores each
  16x16 sprite column-first (one byte = 4 vertical pixels of one column),
  so X must use the byte-level offsets and Y must use the bit-level offsets.
  (2) `read_bit` indexed bytes LSB-first, but the MAME-style offset tables
  are MSB-first. Both bugs combined to render sprites as transposed and
  locally-mirrored garbage; fixed inside the T013 active task. See the T013
  "Scope changes" section and progress log for the patch, the replacement
  `assets/sprites.bin` and `assets/sprite_colors.bin` hashes, and the
  regenerated render evidence. The original T003 evidence artifacts under
  `tests/evidence/T003-sprite-extraction/` are left intact as the historical
  record at acceptance time.

## Pre-flight

- [x] T001 is completed and accepted.
- [x] `pacman/pacman.5f` exists and is an allowed extraction source.
- [x] No other task is active.
- [x] Confirm the exact sprite ROM bit layout against the documented MAME
  Pac-Man `spritelayout` before writing the decoder. If `docs/PLAN.md` needs a
  correction similar to T002, update the plan first.

## Implementation notes

The plan describes 64 16x16 sprites, 2 bits per pixel. The corrected format is
the MAME Pac-Man `spritelayout`: each 64-byte sprite is assembled from four
4-pixel-wide packed-nibble groups per row, with bitplane 0 in bits 0-3 and
bitplane 1 in bits 4-7 of each source byte. Decode from `pacman/pacman.5f`
only; do not read or inspect the restricted program ROMs. Because V9938 Sprite
Mode 2 is 1bpp pattern plus per-row color, preserve source opacity in the
pattern data and record any color-loss assumptions in the manifest.

The V9938 16x16 sprite pattern bank is written in four 8x8 pattern blocks:
top-left, top-right, bottom-left, bottom-right. This matches the Vanguard 8
emulator's 16x16 sprite fetch path and is not row-interleaved.

The manifest should be sufficient for a reviewer to confirm the sprite count,
output sizes, hashes, per-sprite nonzero pixel counts, and any row-color
selection behavior.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T003-sprite-extraction/extract_sprites.log` — extraction
  stdout from `tools/extract_sprites.py`.
- `tests/evidence/T003-sprite-extraction/sprites_manifest.txt` — copy of the
  generated sprite manifest.
- `tests/evidence/T003-sprite-extraction/sprites_summary.txt` — compact summary
  of source/output sizes, hashes, and row-color selection counts.

**Reviewer checklist** (human ticks these):

- [ ] `python3 tools/extract_sprites.py` completes without errors.
- [ ] `assets/sprites.bin` is exactly `2048` bytes (`64 sprites * 32 bytes`).
- [ ] `assets/sprite_colors.bin` is exactly `1024` bytes
  (`64 sprites * 16 rows`).
- [ ] The manifest contains exactly `64` sprite rows after its header.
- [ ] The summary shows stable SHA-256 values for the sprite ROM and output
  assets.
- [ ] No restricted program or sound PROM files are read by the extractor.

**Observed values:**

- Source ROM bytes: `4096`
- Source ROM SHA-256:
  `49c8f656cb8ea1ae02fb64a2c09df98e7f06a034b43c6c8240032df417c6d36f`
- Output pattern bank bytes: `2048`
- Output pattern bank SHA-256:
  `0ffed3a88be1b88be0127f15a246cdf3b620aec58ebfef354dc39de7201b9fd4`
- Output color table bytes: `1024`
- Output color table SHA-256:
  `4ef70c04ae89f37007266562cbb09d909a327686dde82a9613c0be0c90834f14`
- Manifest sprite rows: `64`
- Total opaque pixels: `6431`
- Blank sprites: `5`
- Blank sprite rows: `260`
- Rows with multiple non-transparent colors: `215`
- Dominant row color counts: `0=260`, `1=303`, `2=58`, `3=403`
- Regression check: `python3 tools/build.py` completed, ROM size `16,384`
  bytes, symbol count `7`

**Rerun command:**

```bash
python3 tools/extract_sprites.py | tee tests/evidence/T003-sprite-extraction/extract_sprites.log
cp assets/sprites_manifest.txt tests/evidence/T003-sprite-extraction/sprites_manifest.txt
cp assets/sprites_summary.txt tests/evidence/T003-sprite-extraction/sprites_summary.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-15 | Created, state: planned. |
| 2026-04-15 | Activated after user approval to begin the planned task. |
| 2026-04-15 | Corrected the Phase 1 sprite-format plan note before implementing extraction. The ROM uses the MAME Pac-Man packed-nibble `spritelayout`, not simple upper/lower planar halves. |
| 2026-04-15 | Implemented `tools/extract_sprites.py`, generated `assets/sprites.bin`, `assets/sprite_colors.bin`, manifest, and summary evidence. Verified with `py_compile`, byte-for-byte evidence regeneration, restricted-source scan, and the existing build. Stopping for human review. |
| 2026-04-15 | Accepted by human reviewer and moved to completed. |
