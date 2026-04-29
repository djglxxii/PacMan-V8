# T028 — Sprite Frame Animation

| Field | Value |
|---|---|
| ID | T028 |
| State | completed |
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

- [x] T027 completed.

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
- `tests/evidence/T028-sprite-frame-animation/ghost_wobble_0007.ppm` and
  `ghost_wobble_0015.ppm` — PPMs spaced 8 gameplay frames apart showing
  the ghost body-frame alternation.
- `tests/evidence/T028-sprite-frame-animation/stopped_wall_0108.ppm` —
  PPM showing Pac-Man stopped against a wall with the closed-mouth frame.
- `tests/evidence/T028-sprite-frame-animation/sprite_animation_summary.txt`
  — replay route, absolute frame numbers, SHA-256 values, animation
  counters/phases, and SAT pattern bytes.
- `tests/evidence/T028-sprite-frame-animation/t021_regression.txt` —
  pattern replay regression stdout.

**Reviewer checklist:**

- [x] Pac-Man mouth visibly cycles open → half → closed → half:
      `anim_seq_0006`/`0012`/`0018`/`0024` use phases
      `0`/`1`/`2`/`3` and slot-0 patterns `0x44`/`0x54`/`0x64`/`0x54`.
- [x] Ghost body wobble visible across two PPMs spaced 8 frames apart:
      `ghost_wobble_0007` has ghost phase `0`; `ghost_wobble_0015`
      has ghost phase `1`, with ghost slot patterns toggling by `+0x04`.
- [x] Pac-Man mouth stays closed in a frame where he is stopped at a
      wall: `stopped_wall_0108` has `dir=4` and slot-0 pattern `0x64`.

**Rerun command:**

```
python3 tools/build.py
python3 tools/sprite_animation_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
| 2026-04-29 | Activated at user request; ready to begin pre-flight review. |
| 2026-04-29 | Implemented live sprite animation counters, Pac-Man open/half/closed/half pattern selection, ghost body-frame wobble, dot-stall/DYING pause behavior, and `tools/sprite_animation_replay.py`. Generated PPM evidence and `sprite_animation_summary.txt` under `tests/evidence/T028-sprite-frame-animation/`. |
| 2026-04-29 | Ran T021 pattern replay regression into `tests/evidence/T028-sprite-frame-animation/t021_regression.txt`; result: 2/2 passed. |
| 2026-04-29 | Human approved the deliverable; moved to completed. |
