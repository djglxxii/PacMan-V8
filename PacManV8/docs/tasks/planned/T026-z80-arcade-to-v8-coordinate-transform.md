# T026 — Z80 Arcade-to-V8 Coordinate Transform

| Field | Value |
|---|---|
| ID | T026 |
| State | planned |
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

- [ ] T015 evidence inspected to confirm the Python transform reference
      values.
- [ ] Decision recorded in this file's Implementation notes whether to
      use a Z80 routine or a build-time lookup table.

## Implementation notes

- The existing Python transform handles vertical compression (arcade
  248 → V8 196) and horizontal centering (arcade 224 → V8 256 with side
  margin). See `tools/coordinate_transform.py`.
- A lookup-table approach is likely preferred — fixed cost, simple Z80
  code, ~512 bytes for 28×36 integer-tile entries, sub-tile interpolation
  done in assembly.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T026-z80-arcade-to-v8-coordinate-transform/transform_compare.txt`
  — headless harness comparing Z80 output to Python reference for a 28×36
  tile grid plus sub-tile offsets {0, 2, 4, 6}. Reviewer confirms zero
  mismatches.

**Reviewer checklist:**

- [ ] All compared positions match Python reference exactly.
- [ ] Routine completes within the V-blank budget for 5 sprites
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
