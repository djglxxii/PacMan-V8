# T031 — Live HUD Update

| Field | Value |
|---|---|
| ID | T031 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T025 |
| Plan reference | `docs/PLAN.md` §9.9 Live HUD Update |

## Goal

Maintain SCORE / LIVES / LEVEL state and update the HUD VRAM rows
on each gameplay event so the score, life icons, and level fruit row
visibly track play.

## Scope

- In scope:
  - SCORE / HIGH_SCORE / LIVES / LEVEL bytes (allocated in T023).
  - Score update on pellet (10), energizer (50), ghost-eaten chain
    (200/400/800/1600), fruit (per level).
  - Lives decremented on death; high-score updated on score crossing.
  - HUD digit rendering: per-frame check whether SCORE has changed,
    redraw the SCORE row with a small 8×8 digit set already produced
    in `assets/hud_patch.bin`.
  - Life icons: redraw the lives row whenever LIVES changes.
  - Level fruit row: redraw on level transition with the next-N fruit
    icons per arcade rule (one per level up to 7).
  - Remove the dead `hud_draw_review_rows` label
    (`src/hud.asm:35`, audit LOW-2).

- Out of scope:
  - Score popups (T036).
  - GAME OVER overlay (T038).
  - HUD font polish (Phase 8 / T022).

## Pre-flight

- [ ] T025 driving real gameplay events.

## Implementation notes

- HUD VRAM regions are documented in `src/hud.asm`. Top band starts at
  VRAM 0x0000 page 0; bottom band at VRAM 0x6600 page 1. Digit positions
  for SCORE, HIGH SCORE are defined by the existing hud asset generator
  in `tools/generate_hud_assets.py`.
- Updates should be minimal-bandwidth: write only the digits that
  changed since last frame, not the entire row.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T031-live-hud-update/score_progression.ppm` set —
  three PPMs at frame 60, 240, 480 of an input replay that eats
  pellets, energizers, and (if T032 already in) a ghost. Reviewer
  confirms score visibly increases across the three frames.
- `tests/evidence/T031-live-hud-update/lives_decrement.ppm` — PPM
  after a forced death showing one fewer life icon.

**Reviewer checklist:**

- [ ] Score digits update.
- [ ] Lives icons decrement on death.
- [ ] Level fruit row matches the current level number.
- [ ] No flicker or partial-row corruption (writes V-blank-safe).

**Rerun command:**

```
python3 tools/build.py
python3 tools/hud_live_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
