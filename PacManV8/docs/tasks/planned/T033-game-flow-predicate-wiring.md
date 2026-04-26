# T033 — Game-Flow Predicate Wiring

| Field | Value |
|---|---|
| ID | T033 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T025, T031 |
| Plan reference | `docs/PLAN.md` §9.11 Game-Flow Predicate Wiring |

## Goal

Replace the timer-based PLAYING / DYING / LEVEL_COMPLETE / CONTINUE
transitions in `game_flow_update_frame` with real predicates so the game
progresses through states based on what actually happens in play.

## Scope

- In scope:
  - PLAYING → DYING on `COLLISION_LAST_GHOST_RESULT ==
    COLLISION_GHOST_PACMAN_DIES`.
  - PLAYING → LEVEL_COMPLETE on
    `COLLISION_PELLET_COUNT == 0 && COLLISION_ENERGIZER_COUNT == 0`.
  - DYING → CONTINUE after death-animation duration (existing timer is
    fine here).
  - CONTINUE → PLAYING if `LIVES > 0`, else CONTINUE → ATTRACT
    (game-over) and reset score / restart attract.
  - Remove `level_progression_set_current_level_2_for_review` from the
    live game path (audit LOW-7).
  - Ensure `intermission_select_review_level_for_game_flow`
    (audit LOW-6) is replaced by a normal completed-level read on the
    LEVEL_COMPLETE → NEXT_LEVEL transition.

- Out of scope:
  - Death animation visuals (folded into a small T028 follow-up if
    needed; for now reuse the existing intermission-style sprite).
  - High-score persistence between games (single-session only).

## Pre-flight

- [ ] T025 + T031 in.

## Implementation notes

- `GAME_FLOW_STATE_TIMER` continues to drive READY / NEXT_LEVEL /
  intermission entry timers (they are fixed-duration by design). Only
  the gameplay-driven states change.
- `game_flow.asm:138` `.from_playing` is the relevant decision branch
  to replace.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T033-game-flow-predicate-wiring/state_transitions.txt`
  — replay log capturing (frame, state) on three replays:
  1. Pac-Man dies → CONTINUE → PLAYING with LIVES decremented.
  2. Pac-Man eats all dots → LEVEL_COMPLETE → NEXT_LEVEL → READY.
  3. Pac-Man dies 3 times → CONTINUE → ATTRACT with SCORE reset.

**Reviewer checklist:**

- [ ] Each replay produces the expected state sequence.
- [ ] Game-over correctly returns to ATTRACT.
- [ ] No silent timer-based PLAYING exit when the player isn't dying or
      finishing a level.

**Rerun command:**

```
python3 tools/build.py
python3 tools/game_flow_predicate_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
