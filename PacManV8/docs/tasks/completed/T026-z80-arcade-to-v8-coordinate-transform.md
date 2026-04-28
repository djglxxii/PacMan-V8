# T026 — Z80 Arcade-to-V8 Coordinate Transform

| Field | Value |
|---|---|
| ID | T026 |
| State | active |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T023 |
| Plan reference | `docs/PLAN.md` §9.4 Z80 Coordinate Transform |

## Goal

Port the arcade → V8 coordinate transform from `tools/coordinate_transform.py`
to a Z80 routine (or precomputed lookup table) callable per sprite per frame.
T015 baked transform results into `sprite_review_shadow.inc` at build time;
the live loop needs the same transform at runtime.

## Scope

- In scope:
  - New `src/coord_transform.asm` with `coord_arcade_to_v8`: input
    HL = arcade Y (8.8), DE = arcade X (8.8); output H = SAT Y byte,
    L = SAT X byte. Or, equivalently, a precomputed lookup table indexed
    by integer arcade tile coordinates with sub-tile fixup.
  - Asset-pipeline addition (if lookup-table approach): a Python tool
    that emits the table to `assets/coord_lut.bin` from the same
    fitted-maze data the Python transform uses.
  - Headless test harness comparing Z80 output to the Python reference
    on a grid of input positions.

- Out of scope:
  - Calling the routine from the per-frame loop — that's T027.
  - Vertical compression refinements (out-of-scope for the port; match
    the existing transform exactly).

## Pre-flight

- [x] T015 evidence inspected to confirm the Python transform reference
      values.
- [x] Decision recorded in this file's Implementation notes whether to
      use a Z80 routine or a build-time lookup table.

## Implementation notes

- The existing Python transform handles vertical compression (arcade
  248 → V8 196) and horizontal centering (arcade 224 → V8 256 with side
  margin). See `tools/coordinate_transform.py`.
- Implemented a hybrid build-time lookup table plus Z80 fixup:
  `tools/generate_coord_lut.py` emits `assets/coord_lut.bin` from
  `assets/maze_v8_coordmap.bin`; `src/coord_transform.asm` indexes the X
  table after 224-pixel wrap and indexes Y base/fraction-threshold tables
  for the fitted vertical compression.
- The LUT is 736 bytes: 224 bytes for SAT X, 256 bytes for SAT Y base, and
  256 bytes for the fractional Y carry threshold. The routine's static
  timing estimate is 189-234 T-states per call, under the ~250-cycle target.
- Mapped maze rows are 3-33. The Python reference rejects unmapped rows
  0-2 and 34-35, so the Z80 evidence compares every column and offset in
  mapped rows and reports the skipped unmapped row/offset count explicitly.
  Wrapped Y high-byte values 0x00-0x0F are reserved for mapped rows 32-33,
  which are beyond 16-bit 8.8's direct 0xFFFF range.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T026-z80-arcade-to-v8-coordinate-transform/transform_compare.txt`
  — headless harness comparing Z80 output to Python reference for the
  mapped portion of the 28×36 tile grid plus sub-tile offsets {0, 2, 4, 6}.
  Reviewer confirms zero mismatches and notes the reported unmapped-row
  skips.

**Reviewer checklist:**

- [x] All compared positions match Python reference exactly:
      13,888 positions / 27,776 bytes, zero mismatches.
- [x] Routine completes within the V-blank budget for 5 sprites
      (~250 cycles per call target).

**Rerun command:**

```
python3 tools/build.py
python3 tools/coord_transform_z80_tests.py > tests/evidence/T026-z80-arcade-to-v8-coordinate-transform/transform_compare.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
| 2026-04-28 | Activated at user request; ready to begin pre-flight review. |
| 2026-04-28 | Inspected T015 transform evidence, implemented generated `assets/coord_lut.bin`, added `src/coord_transform.asm`, wired LUT generation into `tools/build.py`, and added `tools/coord_transform_z80_tests.py`. Evidence `transform_compare.txt` reports 13,888 mapped positions compared, 2,240 unmapped row/offset positions skipped because Python rejects unmapped cells, zero mismatches, and a 189-234 T-state routine estimate. Build, 60-frame headless run, legacy transform tests, and Python compilation passed. Stopping for human review. |
