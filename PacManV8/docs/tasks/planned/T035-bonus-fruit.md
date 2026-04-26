# T035 — Bonus Fruit

| Field | Value |
|---|---|
| ID | T035 |
| State | planned |
| Phase | Phase 10 — Final Presentation |
| Depends on | T025, T027, T031 |
| Plan reference | `docs/PLAN.md` §10.1 Bonus Fruit |

## Goal

Spawn the level-appropriate fruit at the standard arcade fruit tile after
70 dots and 170 dots eaten, despawn after ~10 seconds, and award the
level-appropriate score on Pac-Man collision.

## Scope

- In scope:
  - Sprite slot 5 (currently `SPRITE_RESERVED_SLOT`) used for the fruit.
  - Spawn on `COLLISION_PELLET_COUNT` crossing (244-70) and (244-170).
  - Despawn timer ~10 s after spawn.
  - Pac-Man-fruit collision via `collision_consume_tile` extension or
    a dedicated check at the fruit tile.
  - Score award uses `level_progression_get_fruit_score` (add if
    missing — values are fixed per fruit kind).

- Out of scope:
  - Fruit walk animation (arcade fruits are stationary on Pac-Man).
  - Score popup at fruit-eat — that's T036.

## Pre-flight

- [ ] Phase 9 fully landed (live loop, sprites, HUD).

## Implementation notes

- Fruit table is in `level_progression.asm`; expose
  `level_progression_get_fruit` if not already public.
- Fruit sprite patterns are in the sprite ROM — confirm via
  `tools/extract_sprites.py` output and pick the correct base offset.
- Standard arcade fruit tile is (14, 20) in arcade coordinates (just
  below the ghost house exit).

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T035-bonus-fruit/fruit_spawn.ppm` — PPM at the frame
  after 70 dots eaten showing the fruit visible.
- `tests/evidence/T035-bonus-fruit/fruit_eaten.ppm` — PPM after Pac-Man
  walks over the fruit; fruit gone, score increased by the fruit value.
- `tests/evidence/T035-bonus-fruit/fruit_despawn.ppm` — PPM ~10 s after
  spawn (without eating), fruit gone.

**Reviewer checklist:**

- [ ] Fruit appears at the correct dot count.
- [ ] Eating the fruit increases SCORE by the level's fruit value.
- [ ] Fruit despawns on timer if not eaten.

**Rerun command:**

```
python3 tools/build.py
python3 tools/fruit_replay.py
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
