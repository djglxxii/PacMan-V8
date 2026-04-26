# T023 — Boot-Time Game State Initialization

| Field | Value |
|---|---|
| ID | T023 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | none |
| Plan reference | `docs/PLAN.md` §9.1 Boot-Time Game State Initialization |

## Goal

Replace `sprite_init_debug_state`'s screenshot-time mix of ghost modes
(audit finding LOW-3) with a proper game-state init that runs at boot and on
game-over → new-game transitions. After this task the ROM boots into a
coherent level-1 starting state instead of a four-ghost screenshot palette.

## Scope

- In scope:
  - New `game_state_init` routine (likely a new `src/game_state.asm`)
    that calls `level_progression_init`, `ghost_init_state`,
    `ghost_house_init`, `collision_init`, then sets SCORE = 0, LIVES = 3,
    LEVEL = 1.
  - Replace the call to `sprite_init_debug_state` in `init_video` with a
    call to `game_state_init` (or have `game_state_init` invoke a
    trimmed-down sprite init that uploads patterns/colors but does not
    inject the debug ghost-mode mix).
  - Allocate SCORE/LIVES/LEVEL state bytes at a documented RAM base
    (avoid the `0x8270` overlap noted in the audit).
  - Ghosts initialized with arcade-correct house starting tiles and the
    level-1 ghost-mode schedule (Blinky/Pinky/Inky/Clyde set per the
    Pac-Man Dossier first phase).

- Out of scope:
  - Per-frame sprite SAT update (T027).
  - Live HUD score/lives display (T031).
  - Game-over → ATTRACT transition (T033).

## Pre-flight

- [ ] Audit report read: `docs/AUDIT-2026-04-25-runtime-integration-gaps.md`
- [ ] Confirm chosen RAM base does not overlap any existing block in
      `src/*.asm` (`MOVEMENT_STATE_BASE`, `GHOST_STATE_BASE`,
      `COLLISION_STATE_BASE`, etc.)

## Implementation notes

- Existing inits to compose: `level_progression_init`, `ghost_init_state`,
  `ghost_house_init` (called from `ghost_init_state` already),
  `collision_init`, `movement_init_pacman`. None of these take parameters.
- Ghost starting tiles are documented in `src/ghost_ai.asm:130`
  (`ghost_init_state`), already arcade-correct.
- Replace the debug mode mix at `src/sprites.asm:92`
  (`sprite_init_debug_state`) with a call site that does only the static
  pattern/color VRAM uploads (`sprite_upload_patterns`,
  `sprite_upload_color_shadow`). The SAT shadow stays empty until T027
  begins committing live game state.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T023-boot-time-game-state-init/boot_state.txt` —
  headless run of a Python harness that asserts: ghosts at level-1 start
  tiles, ghost-mode schedule starts in SCATTER (level-1 phase 0), pellet
  bitset has all 244 dots set, energizer count = 4, score = 0, lives = 3,
  level = 1.
- `tests/evidence/T023-boot-time-game-state-init/boot_frame.ppm` —
  PPM dump from `vanguard8_headless --frames 30` showing the maze with
  pellets and (if T027 not yet done) no sprites or the pre-T027 static
  pattern-bank screenshot.

**Reviewer checklist:**

- [ ] No debug ghost-mode mix is visible — at boot, all ghosts are in
      SCATTER (or the level-1 starting mode).
- [ ] State assertions pass.
- [ ] T021 pattern-replay evidence still passes after this change.

**Rerun command:**

```
python3 tools/build.py
python3 tools/game_state_init_tests.py > tests/evidence/T023-boot-time-game-state-init/boot_state.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless build/pacman.rom --frames 30 --frame-dump tests/evidence/T023-boot-time-game-state-init/boot_frame.ppm
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
