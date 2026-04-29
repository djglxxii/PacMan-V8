# T027 — Sprite SAT Commit From Game State

| Field | Value |
|---|---|
| ID | T027 |
| State | completed |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T026 |
| Plan reference | `docs/PLAN.md` §9.5 Sprite SAT Commit From Game State |

## Goal

New per-frame `sprite_commit_from_game_state` that walks Pac-Man's 8.8
position and the four ghost records, applies T026's transform, writes the
SAT shadow, and DMAs it to VRAM. After this task, sprites move on screen
in response to the gameplay tick.

## Scope

- In scope:
  - New `sprite_commit_from_game_state` in `src/sprites.asm` (or a new
    `src/sprite_commit.asm`).
  - Per-slot SAT shadow assembly: Pac-Man slot from
    `(PACMAN_X_FP, PACMAN_Y_FP)`; ghost slots from each ghost record's
    tile coordinates (re-expanded to 8.8 sub-tile if ghost positions
    move sub-pixel; otherwise tile-only is acceptable for now).
  - Ghost slot pattern selected by current ghost mode + direction
    (chase/scatter use the body sprite for the ghost's facing direction;
    frightened uses the frightened body — full frightened visual swap
    is T030).
  - Call from the live PLAYING tick after `collision_check_all_ghosts`.
  - V-blank-aware DMA — commit happens immediately after `halt`, before
    the gameplay tick, OR inside the IM1 handler (decision recorded in
    Implementation notes).

- Out of scope:
  - Sprite frame animation (T028).
  - Frightened mode visual swap (T030).
  - Score-popup sprite slots (T036).
  - Fruit sprite (T035).

## Pre-flight

- [x] T026 completed.
- [x] Decide foreground-after-halt vs. IM1 commit.

## Implementation notes

- 5 sprite slots (Pac-Man + 4 ghosts), 8 bytes per slot SAT entry =
  40 bytes per frame DMA. Comfortably within V-blank budget.
- The static `sprite_review_shadow.inc` becomes obsolete once this is
  in place — leave the include tied to a debug build flag, or remove it
  and the build-time generator script. Decision noted in this file's
  scope changes once landed.
- Ghost direction → pattern mapping: existing patterns in `sprites.bin`
  are organized as 4 directions × 4 ghosts × 2 wobble frames. Select
  pattern = `ghost_id_pattern_base + dir * 2 + wobble_frame`.
- Decision: commit in the foreground frame loop after `halt`, via the live
  PLAYING tick's post-`collision_check_all_ghosts` path. The IM1 handler
  stays limited to clearing VBlank and audio so the SAT builder can safely
  call gameplay transform helpers without interrupt-time state coupling.
- `sprite_renderer_init` now uploads a hidden SAT terminator at boot, then
  `sprite_commit_from_game_state` replaces it whenever live PLAYING runs.
  The generated `sprite_review_shadow.inc` is left in place for older
  deterministic review/test surfaces; it is no longer boot-time gameplay
  sprite state.
- T027 uses ghost tile centers for SAT placement because ghost movement is
  still tile-stepped. T028 will own animation frame cycling; T030 will own
  full frightened color-table swaps.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T027-sprite-sat-commit-from-game-state/move_seq_0030.ppm`
- `tests/evidence/T027-sprite-sat-commit-from-game-state/move_seq_0090.ppm`
- `tests/evidence/T027-sprite-sat-commit-from-game-state/move_seq_0180.ppm`
  — three PPMs from a recorded input replay showing Pac-Man at three
  different on-screen positions.
- `tests/evidence/T027-sprite-sat-commit-from-game-state/sprite_commit_summary.txt`
  — replay route, absolute frame numbers, PPM SHA-256 values, gameplay
  positions, and SAT slot coordinates.
- `tests/evidence/T027-sprite-sat-commit-from-game-state/t021_regression.txt`
  — T021 pattern replay regression output.

**Reviewer checklist:**

- [x] Pac-Man visibly at different positions in each PPM:
      SAT slot 0 moves from `(111,148)` to `(113,148)` to `(180,134)`.
- [x] At least one ghost visibly at different positions across the PPMs:
      Blinky SAT slot 1 moves from `(148,72)` to `(228,72)` to `(228,91)`.
- [x] No sprite tearing or duplicate copies (V-blank commit is correct):
      each PPM shows one Pac-Man and one copy of each visible ghost slot.
- [x] T021 pattern-replay regression still green:
      `t021_regression.txt` reports `result: 2/2 passed`.

**Rerun command:**

```
python3 tools/build.py
python3 tools/sprite_commit_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
| 2026-04-28 | Activated at user request; ready to begin pre-flight review. |
| 2026-04-28 | Implemented `sprite_commit_from_game_state`, boot-time hidden SAT upload, live PLAYING post-collision SAT commit, and `tools/sprite_commit_replay.py`. Evidence PPMs and SAT summary were generated under `tests/evidence/T027-sprite-sat-commit-from-game-state/`; T021 regression passed 2/2 in the same evidence directory. Stopping for human review. |
| 2026-04-29 | Human accepted the deliverable; moved to completed. |
