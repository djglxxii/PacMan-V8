# T022 — Visual Polish and Palette Refinement

| Field | Value |
|---|---|
| ID | T022 |
| State | planned |
| Phase | Phase 8 — Polish |
| Depends on | T038 |
| Plan reference | `docs/PLAN.md` Phase 8 — Polish (Safe Enhancements Only) |

## Goal

Apply the safe visual enhancements allowed by Phase 8 of the plan — richer
9-bit-RGB palette choices, energizer blink, and maze flash — without touching
gameplay state, timing, AI, or maze topology. Deliver before/after frame
captures that prove the polish is purely cosmetic.

## Scope

- In scope:
  - Re-author maze, pellet, ghost, and Pac-Man palettes using the V9938's
    full 9-bit RGB palette where the current build uses near-arcade
    approximations. Each color change must be justified against the arcade
    reference or the V9938 palette spec; no creative redesigns.
  - Implement energizer blink as a VDP-B palette cycle rather than per-tile
    pattern toggling, leaving gameplay state untouched.
  - Implement the maze flash on level-clear as a VDP-B palette cycle (white
    over blue, alternating at the documented arcade cadence) without
    modifying maze tiles or topology.
  - Optional and only if it does not regress sprite priority, frame budget,
    or DMA timing: a subtle, static background pattern on VDP-B behind the
    maze (e.g., dark dotted backdrop that respects the maze border).
  - Update palette extraction / asset pipeline scripts under `tools/` so the
    refined palettes are produced by tracked inputs — no hand-edited binaries.
  - Produce frame captures at clearly named checkpoints (attract, level
    start, energizer-active, level-clear flash mid-cycle) and a side-by-side
    "before" set captured from the current `master` build prior to changes.
  - Confirm pattern replay evidence from T021 still passes with the same
    checkpoint vectors (positions, score, frame counts) after polish.

- Out of scope:
  - Any change to maze topology, movement graph, dot/pellet placement, ghost
    house geometry, or coordinate transforms. Polish is cosmetic only.
  - Any change to scatter/chase tables, frightened duration, dot-stall
    constants, speed tables, Elroy thresholds, or fruit timing.
  - Movement smoothing, sub-pixel interpolation, or resolution changes.
  - Ghost AI changes of any kind — including "minor" targeting tweaks.
  - Audio polish (smoother siren / FM refinement). That is allowed by Phase
    8 in principle but belongs in a separate audio-polish task to keep
    visual evidence reviewable in isolation.
  - HUD font replacement beyond the existing clean-font work delivered in
    T014; only palette adjustments to the HUD are in scope here.
  - Level-256 kill-screen visual refinements; the corrupted half-maze must
    remain bug-faithful and is out of scope for this task.
  - Reading, disassembling, or reverse-engineering restricted Pac-Man
    program ROMs. Color choices come from public arcade documentation, the
    permitted color PROMs, and the V9938 palette spec.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T021 is completed and accepted.
- [ ] Confirm no other task is active before activation.
- [ ] Re-read `docs/PLAN.md` Phase 8 allowed/forbidden lists.
- [ ] Re-read the V9938 palette section of the Vanguard 8 hardware spec at
  `/home/djglxxii/src/Vanguard8/docs/spec/`.
- [ ] Capture a "before" frame set from the current `master` build before
  modifying any palette or rendering source so the diff is reviewable.
- [ ] Re-run `tools/pattern_replay_tests.py` from T021 against the unchanged
  build and record the baseline pass output, so post-change regression
  checks are anchored.

## Implementation notes

The arcade source palette comes through the permitted color PROMs
(`82s123.7f`, `82s126.4a`); the V9938 supports 9-bit RGB (3 bits per
channel, 512 colors per VDP). Most existing colors in the build are near-
arcade. The polish here is to pick V9938 entries that are visibly closer
to arcade reference where the current quantization drifts (notably maze
blue, pellet/energizer cream, and ghost body colors). Changes are made in
the palette source under `tools/` and re-emitted; no hand-tuning of binary
assets.

Energizer blink and maze flash should be implemented as VDP-B palette
cycles. The blink/flash cadence must match documented arcade timing —
this is a presentation-layer effect; do not introduce gameplay-visible
timing that game logic could observe. If any existing logic toggles
energizer pattern indices for blink, replace it with palette cycling and
keep the game-state side completely inert.

If a "subtle background" is added on VDP-B, it must:
- not affect sprite priority over the maze,
- not introduce additional VBlank DMA beyond the existing ≤2 DMA budget,
- be a single static pattern table update at scene init, not per-frame
  uploads.

Any change that risks frame-budget or DMA regressions is preferred to be
dropped rather than worked around. A regression in pattern replay vectors
is an automatic stop — fix the polish, not the gameplay.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T022-visual-polish-and-palette-refinement/before/*.ppm`
  — frame captures from the pre-polish build at named checkpoints
  (attract, level1_start, energizer_active, level_clear_flash_mid).
- `tests/evidence/T022-visual-polish-and-palette-refinement/after/*.ppm`
  — frame captures from the post-polish build at the same named
  checkpoints, captured by the same headless command.
- `tests/evidence/T022-visual-polish-and-palette-refinement/palette_diff.txt`
  — readable diff of palette source values (arcade reference, V9938 entry,
  before/after RGB, justification per changed color).
- `tests/evidence/T022-visual-polish-and-palette-refinement/replay_regression.txt`
  — re-run of T021's `tools/pattern_replay_tests.py` against the polished
  build, showing identical checkpoint vectors and pass results.
- `tests/evidence/T022-visual-polish-and-palette-refinement/frame_budget_notes.txt`
  — short note confirming DMA-per-VBlank remains within the documented
  budget after polish, with the measurement method.

**Reviewer checklist** (human ticks these):

- [ ] `before/*.ppm` and `after/*.ppm` are taken from the same headless
  command and same checkpoint frames; only colors / palette-cycle phase
  differ.
- [ ] Each changed color in `palette_diff.txt` has an explicit arcade or
  V9938 spec justification; no creative redesigns.
- [ ] Energizer blink and maze flash run via palette cycling, with no
  changes to maze tile data or gameplay state machines.
- [ ] T021 pattern replay still passes with identical Pac-Man positions,
  ghost positions, score, and frame counts at every checkpoint.
- [ ] No edits in `src/` to gameplay files (movement, ghost AI, collision,
  ghost house, level progression, scatter/chase, frightened timing) other
  than what's strictly required for palette plumbing.
- [ ] Frame-budget notes confirm ≤2 DMA per VBlank is preserved.
- [ ] No restricted Pac-Man program ROMs were read or used as a reference.

**Rerun command:**

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
# Capture "after" frames at the named checkpoints (one command per
# checkpoint, exact frames to be filled in by the implementing agent
# based on the captured "before" set).
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless \
  --rom build/pacman.rom \
  --frames <N> \
  --dump-frame <N>:tests/evidence/T022-visual-polish-and-palette-refinement/after/<name>.ppm

# Regression check against T021.
python3 tools/pattern_replay_tests.py \
  --evidence-dir tests/evidence/T021-pattern-replay-and-fidelity-testing \
  > tests/evidence/T022-visual-polish-and-palette-refinement/replay_regression.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-25 | Created, state: planned. Awaiting user approval before activation. |
| 2026-04-25 | Activated. |
| 2026-04-25 | Aborted and returned to planned. Audit `docs/AUDIT-2026-04-25-runtime-integration-gaps.md` showed the live runtime is missing the integration that connects the Phase 1–7 modules into a playable loop, so polish on a non-playable ROM is premature. Phases 9 and 10 added; T022's `Depends on` updated from T021 to T038 so it runs after the integration and presentation phases close. |
