# T019 — Level Progression and Speed Tables

| Field | Value |
|---|---|
| ID | T019 |
| State | active |
| Phase | Phase 6 — Game Flow |
| Depends on | T018 |
| Plan reference | `docs/PLAN.md` Phase 3.1 Movement System, Phase 3.3 Scatter/Chase Timer, Phase 3.5 Frightened Mode, Phase 3.7 Tunnel, Phase 3.8 Level Progression, Phase 6 — Game Flow and State Machine |

## Goal

Add the first level-progression and timing-table owner so the game-flow state
machine can advance levels deterministically and gameplay systems can query
per-level speed, frightened, scatter/chase, tunnel, Elroy, fruit, and
intermission trigger data from one source of truth.

## Scope

- In scope:
  - Review the Phase 3 and Phase 6 plan sections before implementation.
  - Review T018's state-machine owner and evidence so level advancement plugs
    into `NEXT_LEVEL` and `INTERMISSION` handoffs without changing T018's
    accepted deterministic review path unexpectedly.
  - Add a compact level/timing table representation for levels `1..256`,
    including at minimum:
    - Pac-Man normal, frightened, and tunnel speed table entries.
    - Ghost normal, tunnel, frightened, Elroy 1, and Elroy 2 speed table
      entries.
    - Scatter/chase schedule family selection for level 1, levels 2-4, and
      level 5+.
    - Frightened duration and flash timing per level family.
    - Bonus fruit symbol/value schedule by level family.
    - Intermission trigger levels `2`, `5`, and `9`.
  - Add level counter and progression plumbing around the T018 flow states,
    including deterministic review vectors for level completion, next-level
    advance, intermission handoff, and level wrap/kill-screen boundary data.
  - Add a Python validation harness that records table values, boundary
    levels, hashes, and pass/fail results.
  - Keep existing movement, ghost AI, collision, ghost-house, rendering, HUD,
    PSG, and FM behavior compatible with the new table queries.
  - Produce human-verifiable evidence under
    `tests/evidence/T019-level-progression-and-speed-tables/`.

- Out of scope:
  - Implementing full intermission cutscene content; T020 owns cutscenes.
  - Pattern replay/fidelity validation; T021 owns full pattern validation.
  - Rendering a level-select UI, attract-title art, or game-over/continue
    presentation beyond what is strictly needed for deterministic review.
  - Reworking maze topology, coordinate transform, sprite art, HUD art, PSG
    effects, or FM music cues.
  - Changing Pac-Man movement physics, ghost targeting rules, collision rules,
    pellet/dot-stall behavior, or ghost-house release rules except to read
    table values through the new owner.
  - Reading or reverse-engineering restricted Pac-Man program ROMs.

## Scope changes

*(None.)*

## Pre-flight

- [x] T018 is completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Phase 3.1, 3.3, 3.5, 3.7, 3.8, and Phase 6.
- [x] Review `docs/tasks/completed/T008-movement-system-and-turn-buffering.md`
  for current fixed-point speed assumptions and turn-buffer contracts.
- [x] Review `docs/tasks/completed/T010-scatter-chase-timer-and-frightened-mode.md`
  for the accepted level-1 scatter/chase and frightened-mode timing surface.
- [x] Review `docs/tasks/completed/T011-collision-pellets-and-dot-stall.md`
  for pellet-count/level-clear inputs.
- [x] Review `docs/tasks/completed/T018-game-state-machine-and-attract-mode.md`
  for accepted state IDs, transition frames, review flags, and frame-loop
  wiring.
- [x] Identify the public documentation source used for arcade level/speed
  values before encoding tables. Do not use restricted program ROMs.

## Implementation notes

The table owner should be small, explicit, and queryable by later gameplay
systems. Prefer an assembly module such as `src/timing.asm` or
`src/level_progression.asm` plus a Python harness such as
`tools/level_progression_tests.py`, following the source-level validation
pattern used by T010, T012, and T018.

The table design should avoid scattering level constants across movement,
ghost mode, collision, and game-flow code. Later tasks should be able to ask
for "current level frightened duration" or "current level ghost tunnel speed"
without duplicating table family logic.

T019 should establish data and progression plumbing, not prove full pattern
fidelity. If exact arcade values need fractional speeds, record the fixed-point
scale and rounding behavior in the vectors so T021 can validate pattern timing
against the same contract.

Intermission levels should be recorded as handoff decisions only:

- Completing level `2` requests `INTERMISSION`.
- Completing level `5` requests `INTERMISSION`.
- Completing level `9` requests `INTERMISSION`.
- T020 owns the actual cutscene scenes and frame content.

For level `256`, this task should expose the boundary in table/progression
data and record the intended kill-screen handoff/flag state. Do not implement
the corrupted level-256 visual presentation unless the plan is updated first.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T019-level-progression-and-speed-tables/level_progression_tests.txt`
  — stdout from a deterministic level/timing-table validation harness.
- `tests/evidence/T019-level-progression-and-speed-tables/level_progression_vectors.txt`
  — readable table values, fixed-point scales, boundary levels, intermission
  trigger decisions, hashes, and pass/fail results.
- `tests/evidence/T019-level-progression-and-speed-tables/level_progression_checklist.txt`
  — manual review checklist for frontend/headless behavior, including any
  frame/audio hash or table hash used during review.

**Reviewer checklist** (human ticks these):

- [ ] Level `1`, `2`, `5`, `9`, `21`, and `256` table lookups return the
  documented speed/timing/fruit/intermission families.
- [ ] Scatter/chase schedule selection covers level 1, levels 2-4, and level
  5+ without regressing T010's accepted level-1 schedule.
- [ ] Frightened duration and flash timing vary by level family and are exposed
  through one owner.
- [ ] `NEXT_LEVEL` progression increments levels deterministically and records
  intermission handoff decisions for levels `2`, `5`, and `9`.
- [ ] Evidence records fixed-point scale, table hashes, boundary decisions,
  and deterministic pass/fail results.
- [ ] T020 intermission cutscene content, T021 pattern validation, visual
  kill-screen corruption, and unrelated gameplay/rendering/audio changes are
  not introduced.

**Rerun command:**

```bash
python3 tools/build.py
python3 tools/level_progression_tests.py --vectors-output tests/evidence/T019-level-progression-and-speed-tables/level_progression_vectors.txt > tests/evidence/T019-level-progression-and-speed-tables/level_progression_tests.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 960 --hash-frame 960
```

**Observed evidence values:**

- Public documentation source:
  Jamey Pittman's Pac-Man Dossier, `https://pacman.holenet.info/`, Table A.1
  plus the scatter/chase timing summary.
- `level_progression_tests.py`: `6/6 passed`
- Deterministic table hash:
  `4196b73a68bb8a0ce30e3c66bb4455e8cbb5352b18787296f400746d65c02202`
- Fixed-point speed scale:
  `100% = 75.75757625 pixels/sec`, `60` frames/sec, `8.8` pixels/frame;
  `100%` encodes as `0x0143`.
- `level_progression_tests.txt` SHA-256:
  `d6434320f4b89977beea269e4c929784c7e4b79d0a2996e6d7dd6d4df0be6703`
- `level_progression_vectors.txt` SHA-256:
  `ed6afdfbcbb3e45dccf957f1a9d1b62afc67de0ff5bdb673d16e8d285ffe4bb6`
- `level_progression_checklist.txt` SHA-256:
  `0bcdefef8da740c940290b6d3063fb8a7746269f3156c71535dbb0294fef791d`
- `src/level_progression.asm` SHA-256:
  `2fa2c065a1a0900f991717f24f204576b1d5b12ba4847eb8059f1bd91bc53596`
- `tools/level_progression_tests.py` SHA-256:
  `ae2213013cd04dec76f6abca1fb92a60e16b57519b94431681e9f5d2547eb58f`
- ROM SHA-256:
  `3dcebfbcb8b55ea6f909b0d476ffb1206bf6d0033d06500b5723eb8d56d65973`
- Headless 960-frame hash:
  `4a63cec305375edd4b20e85ba9830d83888e2eaf4327a29c229cfc7ce7a79693`
- Headless 960-frame event log digest:
  `12325614728164139587`
- Regression checks:
  `game_flow_tests.py` passed `5/5`; `mode_timer_tests.py` passed `5/5`;
  `ghost_ai_tests.py` passed `5/5`; `ghost_house_tests.py` passed `5/5`;
  `movement_tests.py` and `collision_tests.py` were rerun successfully.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-20 | Created, state: planned. |
| 2026-04-20 | Activated task; starting plan and prior-task review before implementation. |
| 2026-04-20 | Implemented `src/level_progression.asm` as the level/timing table owner with Dossier-derived speed, frightened, scatter/chase, Elroy, fruit, intermission, kill-screen, and wrap data for levels 1..256. Wired `game_flow.asm` to initialize and complete levels through the new owner, and wired `ghost_ai.asm` to query schedule and frightened-duration data without changing the accepted T018 review path. Added `tools/level_progression_tests.py`, generated evidence under `tests/evidence/T019-level-progression-and-speed-tables/`, verified build, a 960-frame headless run, and targeted gameplay regressions. Added field manual entry `docs/field-manual/headless-timed-core-jr-c-gap.md`. Stopping for human review. |

## Blocker (only if state = blocked)

*(None.)*
