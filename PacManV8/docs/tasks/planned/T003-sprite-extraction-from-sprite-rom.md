# T003 — Sprite Extraction from Sprite ROM

| Field | Value |
|---|---|
| ID | T003 |
| State | planned |
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

*(None.)*

## Pre-flight

- [ ] T001 is completed and accepted.
- [ ] `pacman/pacman.5f` exists and is an allowed extraction source.
- [ ] No other task is active.
- [ ] Confirm the exact sprite ROM bit layout against the documented MAME
  Pac-Man `spritelayout` before writing the decoder. If `docs/PLAN.md` needs a
  correction similar to T002, update the plan first.

## Implementation notes

The plan describes 64 16x16 sprites, 2 bits per pixel. The task should decode
from `pacman/pacman.5f` only; do not read or inspect the restricted program
ROMs. Because V9938 Sprite Mode 2 is 1bpp pattern plus per-row color, preserve
source opacity in the pattern data and record any color-loss assumptions in the
manifest.

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
- [ ] `assets/sprites.bin` has the expected V9938 Sprite Mode 2 pattern size.
- [ ] `assets/sprite_colors.bin` has the expected V9938 Sprite Mode 2 color
  table size.
- [ ] The manifest contains exactly `64` sprite rows after its header.
- [ ] The summary shows stable SHA-256 values for the sprite ROM and output
  assets.
- [ ] No restricted program or sound PROM files are read by the extractor.

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
