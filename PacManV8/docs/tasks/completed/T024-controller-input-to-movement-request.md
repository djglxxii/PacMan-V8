# T024 — Controller Input → Movement Request

| Field | Value |
|---|---|
| ID | T024 |
| State | completed |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T023 |
| Plan reference | `docs/PLAN.md` §9.2 Controller Input |

## Goal

Read controller port `0x00` once per frame and feed
`movement_request_direction`, so the live game can be steered by the
player. Refactor the existing `pattern_replay_input_to_dir` into a shared
input module so the test harness and live game read input the same way.

## Scope

- In scope:
  - New `src/input.asm` with `input_read_controller_0_to_dir` returning
    `MOVEMENT_DIR_*` in A.
  - Refactor `pattern_replay_input_to_dir` (`src/pattern_replay.asm:107`)
    to call the shared routine.
  - Per-frame call sequence (input read → `movement_request_direction`)
    integrated into the live PLAYING tick stub (full tick lands in T025).

- Out of scope:
  - START/SELECT button handling (kept in pattern replay for now).
  - Two-player input (this project is single-player).
  - Coin/credit handling.

## Pre-flight

- [x] T023 completed and merged.

## Implementation notes

- Active-low D-pad bit layout already in pattern_replay (bit 7 up,
  bit 5 left, bit 6 down, bit 4 right, bit 0 start).
- Shared input routine returns `MOVEMENT_DIR_NONE` when no direction is
  pressed; consumer decides whether to call
  `movement_request_direction` with NONE (current behavior accepts).

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T024-controller-input-to-movement-request/input_replay.txt` —
  headless run with a recorded input file that presses each of
  Up/Left/Down/Right; harness asserts `PACMAN_REQUESTED_DIR` updates
  after each frame.

**Reviewer checklist:**

- [x] All four directions accepted.
- [x] No direction held → no spurious request.
- [x] T021 pattern-replay regression still green.

**Rerun command:**

```
python3 tools/build.py
python3 tools/input_tests.py > tests/evidence/T024-controller-input-to-movement-request/input_replay.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
| 2026-04-26 | Activated. Created src/input.asm, refactored pattern_replay_input_to_dir, wired input into game_flow_update_frame PLAYING state. All eight direction/neutral test cases pass, T021 regression green (2/2). |
