# T010 — Scatter/Chase Timer and Frightened Mode

| Field | Value |
|---|---|
| ID | T010 |
| State | planned |
| Phase | Phase 3 — Gameplay Core |
| Depends on | T009 |
| Plan reference | `docs/PLAN.md` Phase 3.3 Scatter/Chase Timer; Phase 3.5 Frightened Mode |

## Goal

Implement deterministic ghost mode sequencing on top of T009's target and
direction-choice slice: level-based scatter/chase timing, immediate reversal
requests on mode switches, and the first frightened-mode state machine needed
for later energizer, collision, and rendering tasks.

## Scope

- In scope:
  - Add runtime ghost mode/timer state for scatter, chase, and frightened.
  - Implement the level-1 scatter/chase schedule from `docs/PLAN.md`:
    `7s -> 20s -> 7s -> 20s -> 5s -> 20s -> 5s -> chase forever`.
  - Add data structure boundaries for later level 2-4 and level 5+ schedules,
    without fully tuning those tables unless needed by tests.
  - Integrate mode output with T009 target calculation so ghosts use scatter
    targets in scatter and chase targets in chase.
  - Track pending reversal requests when scatter/chase mode changes or
    frightened mode begins; the actual movement-step reversal can remain a
    clearly exposed flag for later ghost movement integration.
  - Implement frightened-mode duration, expiry back to the prior global mode,
    and a deterministic pseudo-random intersection choice hook for tests.
  - Add deterministic tests under `tools/` or an equivalent local harness that
    exercise timer phase boundaries, reversal flags, frightened entry/expiry,
    and representative frightened direction choices.
  - Produce checklist/test-output evidence under
    `tests/evidence/T010-scatter-chase-frightened/`.

- Out of scope:
  - Energizer pellet consumption or collision-triggered frightened entry from
    live gameplay.
  - Ghost house release logic, dot counters, or eyes returning to the house.
  - Sprite rendering, frightened flashing visuals, audio, scoring, lives,
    fruit, attract mode, or level progression UI.
  - Full ghost movement stepping or speed tables beyond constants needed to
    prove deterministic mode timing and frightened behavior.
  - Pattern replay or full arcade-fidelity validation beyond the included
    deterministic timing vectors.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T009 is completed and accepted.
- [ ] Review `docs/PLAN.md` Phase 3.3 and Phase 3.5 before implementation.
- [ ] Review `docs/tasks/completed/T009-ghost-ai-and-targeting.md` for the
  direction enum, tie order, ghost state layout, and evidence vectors.
- [ ] Confirm no other task is active before activation.

## Implementation notes

Keep mode timing in frame counts at the gameplay tick rate used by the runtime.
For the current deterministic harness, assume 60 frames per second unless the
Vanguard 8 timing contract or emulator documentation requires a different
value before implementation.

The mode state should remain separate from pellet/collision/game-flow systems:
tests may trigger frightened mode directly through a function call or harness
input. That keeps this task focused on mode sequencing and leaves energizer
consumption to T011.

T009's direction enum and deterministic tie order remain authoritative:
`UP=0`, `LEFT=1`, `DOWN=2`, `RIGHT=3`, `NONE=4`; tie order is `UP`, `LEFT`,
`DOWN`, `RIGHT`.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T010-scatter-chase-frightened/mode_timer_tests.txt` —
  stdout from the deterministic mode timer/frightened test harness.
- `tests/evidence/T010-scatter-chase-frightened/mode_timer_vectors.txt` —
  readable summary of frame boundaries, mode transitions, reversal flags,
  frightened entry/expiry, and representative frightened choices.

**Reviewer checklist** (human ticks these):

- [ ] Level-1 scatter/chase schedule changes modes at the documented frame
  boundaries and then remains in chase forever.
- [ ] Scatter/chase transitions set pending reversal requests for all ghosts.
- [ ] T009 target selection uses scatter targets during scatter and chase
  targets during chase.
- [ ] Frightened entry records/restores the prior global mode and sets pending
  reversal requests.
- [ ] Frightened expiry returns to the correct scatter/chase mode for the
  current timer position.
- [ ] Frightened intersection selection is deterministic for the same seed and
  legal topology inputs.
- [ ] Evidence output records deterministic pass/fail results and relevant
  constants/hashes.
- [ ] No energizer consumption, collision, ghost house release, rendering,
  audio, scoring, lives, fruit, or game-flow behavior is introduced.

**Rerun command:**

```bash
# To be finalized when T010 is implemented.
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-17 | Created after T009 acceptance; state: planned. |

## Blocker (only if state = blocked)

*(None.)*
