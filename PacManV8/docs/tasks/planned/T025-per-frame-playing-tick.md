# T025 — Per-Frame PLAYING Tick

| Field | Value |
|---|---|
| ID | T025 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T023, T024 |
| Plan reference | `docs/PLAN.md` §9.3 Per-Frame PLAYING Tick |

## Goal

Replace `game_flow_update_frame`'s timer-only PLAYING state with a real
per-frame gameplay tick that composes movement, ghost mode, ghost AI,
ghost-house release, collision, and dot-stall in arcade order. After this
task, Pac-Man and the ghosts move under their own logic — no rendering is
required yet, but the in-RAM state evolves correctly.

## Scope

- In scope:
  - New `game_state_tick_playing` calling, in order: input read →
    `movement_try_turn_at_center` → `movement_update_pacman` (which
    invokes `movement_apply_tunnel_wrap`) → dot-stall branch
    (`collision_tick_dot_stall` if `COLLISION_DOT_STALL > 0`, else
    `collision_update_pellet_at_pacman`) → `ghost_mode_tick` →
    `ghost_update_all_targets` → `ghost_house_tick` →
    `collision_check_all_ghosts`.
  - Wire `game_flow_update_frame`'s PLAYING branch to call the new tick.
  - Remove the fixed `GAME_FLOW_DURATION_PLAYING_LEVEL` exit; PLAYING
    exits only on collision (DYING) or pellet count = 0 (LEVEL_COMPLETE).
    Predicate transitions land in T033, but the timer-based exit is
    removed in this task.

- Out of scope:
  - Sprite/HUD rendering — internal state only (T027, T031).
  - Audio bindings (T032).
  - DYING / LEVEL_COMPLETE / CONTINUE predicate wiring (T033). For now
    PLAYING is unbounded — DYING and LEVEL_COMPLETE remain test-driven.

## Pre-flight

- [ ] T023 + T024 completed.

## Implementation notes

- Order matters: dot-stall must be checked before pellet collision so
  that Pac-Man freezes for the correct number of frames after a pellet.
- `ghost_house_tick` requires the dot-event fan-in (already in
  `collision.asm:186`) — it should not be double-counted by the new
  tick.
- The current `game_flow.asm:67` PLAYING branch falls through to the
  generic timer; preserve the audio-IRQ path while replacing the
  PLAYING-state body.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T025-per-frame-playing-tick/tick_trace.txt` — headless
  run with input file that records (frame, Pac-Man tile, Blinky tile,
  pellet count) for 600 frames; reviewer checks values progress
  monotonically and ghost behavior matches the existing
  `tools/ghost_ai_tests.py` reference.
- `tests/evidence/T025-per-frame-playing-tick/tick_frame_0300.ppm` —
  even though sprite rendering is not yet wired, dump the frame to
  confirm the maze framebuffer is unchanged.

**Reviewer checklist:**

- [ ] Pac-Man tile changes over time.
- [ ] At least one ghost's tile changes over time.
- [ ] Pellet count decreases as Pac-Man moves over pellet tiles.
- [ ] Dot-stall produces the expected 1-frame freeze on pellet, 3-frame
      on energizer.
- [ ] No regression in earlier task evidence.

**Rerun command:**

```
python3 tools/build.py
python3 tools/playing_tick_tests.py > tests/evidence/T025-per-frame-playing-tick/tick_trace.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
