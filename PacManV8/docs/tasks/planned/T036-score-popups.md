# T036 — Score Popups

| Field | Value |
|---|---|
| ID | T036 |
| State | planned |
| Phase | Phase 10 — Final Presentation |
| Depends on | T031 |
| Plan reference | `docs/PLAN.md` §10.2 Score Popups |

## Goal

Display "200" / "400" / "800" / "1600" sprites at the ghost-eaten location
for ~1 second, and the fruit-bonus value at the fruit-eaten location.
Pause ghost movement during the ghost-eaten popup per arcade behavior.

## Scope

- In scope:
  - Numeric popup sprites (200/400/800/1600 + fruit values).
  - Spawn at the ghost-eaten location, freeze for ~60 frames.
  - During ghost-eaten popup: ghost AI / Pac-Man movement frozen except
    the eaten ghost's eyes which retreat.
  - Fruit popup spawn at the fruit-eaten location (no movement freeze
    for fruit).

- Out of scope:
  - High-score table popup (single-session score only).
  - Animated number reveal — static text.

## Pre-flight

- [ ] T035 landed (so fruit-eaten event exists).

## Implementation notes

- Numeric popup glyphs: pull from `assets/hud_patch.bin` digit set or
  add 4-digit popup tiles to a sprite slot.
- Movement freeze: gate the per-frame PLAYING tick on a
  `POPUP_FREEZE_TIMER` byte; tick down at 60 Hz.
- Sprite slot reuse: piggyback on slot 5 for popups, since fruit only
  spawns at known dot-count moments and ghost-eaten popups happen
  during frightened mode (no fruit collision possible mid-popup).

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T036-score-popups/ghost_chain_200_400.ppm` — PPMs
  during a chain of two frightened-ghost eats showing the 200 popup
  then the 400 popup.
- `tests/evidence/T036-score-popups/fruit_popup.ppm` — PPM during the
  fruit-eaten popup.

**Reviewer checklist:**

- [ ] Correct numeric value shown for each ghost in a chain.
- [ ] Movement freeze is exactly the popup duration.
- [ ] Fruit popup shows level-appropriate value.

**Rerun command:**

```
python3 tools/build.py
python3 tools/score_popup_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
