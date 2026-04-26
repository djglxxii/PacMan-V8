# T037 — Attract Mode Demo Content

| Field | Value |
|---|---|
| ID | T037 |
| State | planned |
| Phase | Phase 10 — Final Presentation |
| Depends on | T027 |
| Plan reference | `docs/PLAN.md` §10.3 Attract-Mode Demo Content |

## Goal

`GAME_FLOW_STATE_ATTRACT` draws actual content: the "CHARACTER /
NICKNAME" table with the four ghost names and a blinking "PUSH START"
prompt. Optional brief ghost-chases-Pac-Man demo loop.

## Scope

- In scope:
  - Static "CHARACTER / NICKNAME" rows for Blinky/Pinky/Inky/Clyde
    drawn on VDP-A overlay (text glyphs).
  - "1UP" / "HIGH SCORE" / "2UP" header strip.
  - Blinking "PUSH START BUTTON" prompt at the bottom.
  - Press Start during ATTRACT → transition to READY (game start).

- Out of scope:
  - The full arcade "ghost-eats-Pac-Man" attract demo (a future polish
    task; not arcade-faithful is acceptable for v1).
  - Demo gameplay playback.

## Pre-flight

- [ ] Phase 9 closed.

## Implementation notes

- Text glyphs already exist in the HUD font produced by
  `tools/generate_hud_assets.py`. Reuse the same glyph set for the
  CHARACTER/NICKNAME row.
- ATTRACT-state input check needs the same controller read as PLAYING
  but listening for Start (bit 0).
- Replace the empty 120-frame ATTRACT timer with an unbounded
  ATTRACT state that exits only on Start press.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T037-attract-mode-demo/attract_static.ppm` — PPM at
  frame 60 after boot showing the attract content drawn.
- `tests/evidence/T037-attract-mode-demo/attract_prompt_blink_off.ppm`
  / `..._on.ppm` — PPMs at two frames spaced by the blink period
  showing the prompt visible / hidden.
- `tests/evidence/T037-attract-mode-demo/attract_to_ready.txt` — replay
  log: Start press in ATTRACT → transition to READY.

**Reviewer checklist:**

- [ ] Attract screen shows the four ghost names.
- [ ] PUSH START prompt blinks.
- [ ] Pressing Start transitions to READY.

**Rerun command:**

```
python3 tools/build.py
python3 tools/attract_mode_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
