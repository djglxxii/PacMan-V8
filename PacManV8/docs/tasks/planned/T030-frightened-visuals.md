# T030 — Frightened Visuals + Final-2s Flash

| Field | Value |
|---|---|
| ID | T030 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T027 |
| Plan reference | `docs/PLAN.md` §9.8 Frightened Visuals |

## Goal

When a ghost enters frightened mode, swap its slot palette to
`SPRITE_PALETTE_FRIGHTENED` and pattern to the frightened body. In the
final 2 seconds of frightened, alternate blue/white palette at the arcade
cadence. Restore prior visuals on frightened exit and swap to the eyes
pattern when the ghost is eaten and retreats.

## Scope

- In scope:
  - Per-ghost prior palette/pattern saved on frightened entry, restored
    on frightened exit.
  - Final-2s flashing: alternate frightened-blue (palette index 8) and
    frightened-white (a new palette entry 9, configured during boot).
  - Eaten-ghost retreat visual: swap to eyes pattern
    (`SPRITE_EYES_ID = 49` in arcade pattern numbering).
  - Frightened palette/pattern selection integrated into
    `sprite_commit_from_game_state` (T027).

- Out of scope:
  - Eaten-ghost AI (eyes-back-to-house pathing) — the AI module already
    handles mode transitions via `ghost_enter_frightened`. Eaten-eyes
    pathing belongs in a future AI task; for now treat eaten as a
    visual + score event and let the existing collision + house code
    handle the rest.

## Pre-flight

- [ ] T027 committing live SAT shadow.
- [ ] Confirm `SPRITE_PALETTE_FRIGHTENED` (index 8) is configured in
      `assets/palette_a.bin`. Add a `SPRITE_PALETTE_FRIGHTENED_FLASH`
      (index 9) entry with a near-white color if missing.

## Implementation notes

- Frightened duration per level lives in `level_progression.asm`.
- The "last 2 seconds" boundary should drive a flash flag at 4-Hz
  alternation (every 15 frames at 60 Hz) per arcade convention.
- `GHOST_FRIGHT_REMAIN` already counts down — wire the flash threshold
  off that.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T030-frightened-visuals/fright_active.ppm` — PPM during
  active frightened (all four ghosts blue).
- `tests/evidence/T030-frightened-visuals/fright_flash_blue.ppm` — PPM
  during the flashing window, on the blue half-cycle.
- `tests/evidence/T030-frightened-visuals/fright_flash_white.ppm` — PPM
  during the flashing window, on the white half-cycle.
- `tests/evidence/T030-frightened-visuals/fright_eaten_eyes.ppm` — PPM
  showing one ghost as eyes after being eaten.

**Reviewer checklist:**

- [ ] All four ghosts blue immediately after energizer eaten.
- [ ] Two PPMs in the flash window show the alternating blue/white.
- [ ] Eaten ghost shows the eyes pattern.
- [ ] After frightened expires, ghosts return to their normal palettes
      and patterns.

**Rerun command:**

```
python3 tools/build.py
python3 tools/frightened_visuals_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
