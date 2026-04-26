# T028 — Sprite Frame Animation

| Field | Value |
|---|---|
| ID | T028 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T027 |
| Plan reference | `docs/PLAN.md` §9.6 Sprite Frame Animation |

## Goal

Animate Pac-Man's mouth (open/close cycle) and the ghost wobble (alternate
body frames) so on-screen sprites visually animate while the game plays.

## Scope

- In scope:
  - Per-frame counter advancing at ~10 Hz (every 6 frames at 60 Hz).
  - Pac-Man pattern selection: closed when stopped, alternating
    open/half/closed/half while moving (matches arcade 4-frame cycle).
  - Ghost wobble: alternate two body patterns every 8 frames.
  - Animation paused during dot-stall and during DYING.

- Out of scope:
  - Pac-Man death animation (T033 owns the DYING state visuals).
  - Frightened-mode flashing (T030).

## Pre-flight

- [ ] T027 completed.

## Implementation notes

- Pattern indices for the four mouth states are sequential in
  `sprites.bin`. Identify the base via `tools/extract_sprites.py` output
  in `assets/sprites_summary.txt`.
- Stopped Pac-Man = mouth closed = first frame.
- Animation tick should be advanced inside `sprite_commit_from_game_state`
  (T027) or in a separate `sprite_animation_tick` called immediately
  before commit.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T028-sprite-frame-animation/anim_seq_0006.ppm`,
  `anim_seq_0012.ppm`, `anim_seq_0018.ppm`, `anim_seq_0024.ppm` — four
  PPMs spaced 6 frames apart while Pac-Man is moving, demonstrating the
  full mouth cycle.

**Reviewer checklist:**

- [ ] Pac-Man mouth visibly cycles open → half → closed → half.
- [ ] Ghost body wobble visible across two PPMs spaced 8 frames apart.
- [ ] Pac-Man mouth stays closed in a frame where he is stopped at a
      wall.

**Rerun command:**

```
python3 tools/build.py
python3 tools/sprite_animation_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
