# T038 — READY! / GAME OVER Overlays

| Field | Value |
|---|---|
| ID | T038 |
| State | planned |
| Phase | Phase 10 — Final Presentation |
| Depends on | T031, T033 |
| Plan reference | `docs/PLAN.md` §10.4 READY! / GAME OVER Overlays |

## Goal

`GAME_FLOW_STATE_READY` draws "READY!" centered on the maze; the post
game-over path through the state machine draws "GAME OVER" before
transitioning back to ATTRACT.

## Scope

- In scope:
  - "READY!" text overlay drawn during READY state at the standard
    arcade position (centered on the row above the ghost house).
  - "GAME OVER" overlay drawn during the dedicated GAME_OVER hold
    (~3 seconds) before ATTRACT.
  - New `GAME_FLOW_STATE_GAME_OVER` (or reuse existing CONTINUE state
    when LIVES == 0) — decision recorded in this file.
  - Intro flash on level start (a brief palette flash at READY entry).

- Out of scope:
  - "READY!" yellow color cycling — Phase 8 polish if desired.

## Pre-flight

- [ ] T031 / T033 in.

## Implementation notes

- Text glyphs from the HUD font; same overlay rendering path as T037
  attract content.
- Position: arcade "READY!" sits at tile row 20, centered horizontally.
  Apply the V8 fitted-maze coordinate transform.
- "GAME OVER" position: same row as READY, but render with a different
  glyph string.
- If introducing a new state, update the
  `GAME_FLOW_FLAG_*` and the schedule in `game_flow_load_state_timer`.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T038-ready-and-game-over-overlays/ready_overlay.ppm` —
  PPM during READY state.
- `tests/evidence/T038-ready-and-game-over-overlays/game_over_overlay.ppm`
  — PPM during GAME_OVER state.
- `tests/evidence/T038-ready-and-game-over-overlays/intro_flash.ppm` set
  — two PPMs during the level-start flash showing the alternating
  palette.

**Reviewer checklist:**

- [ ] READY! visible during the READY state.
- [ ] GAME OVER visible after losing all lives.
- [ ] Intro flash plays exactly once at level start.

**Rerun command:**

```
python3 tools/build.py
python3 tools/overlay_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
