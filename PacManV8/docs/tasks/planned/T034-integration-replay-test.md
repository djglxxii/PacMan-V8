# T034 — Integration Replay Test

| Field | Value |
|---|---|
| ID | T034 |
| State | planned |
| Phase | Phase 9 — Live Gameplay Integration |
| Depends on | T023, T024, T025, T026, T027, T028, T029, T030, T031, T032, T033 |
| Plan reference | `docs/PLAN.md` §9.12 Integration Replay Test |

## Goal

Lock in the integrated PLAYING loop with a recorded controller-input file
plus checkpoint vectors (frame hash, score, pellet count, Pac-Man tile,
ghost tiles), runnable via the headless emulator. Becomes the ongoing
regression check for every later task.

## Scope

- In scope:
  - One ~60-second recorded input replay covering: a few corners,
    eating an energizer, eating a frightened ghost, dying once, level
    advancement.
  - Checkpoint assertions at 10–15 frames spread across the replay.
  - Resolve the MEDIUM-4 RAM-base overlap between
    `PATTERN_REPLAY_STATE_BASE` and `INTERMISSION_STATE_BASE`
    (both `0x8270`) since both must coexist after integration.

- Out of scope:
  - Visual diffing — the frame hash assertion is sufficient.
  - Multi-level replays — one level + one death is enough coverage.

## Pre-flight

- [ ] All preceding Phase 9 tasks completed.

## Implementation notes

- Reuse the existing T021 replay infrastructure
  (`tools/pattern_replay_tests.py`) but operate against the live game
  loop instead of the test-harness path. Once the live loop is in
  place, the T021-style replay should naturally exercise it.
- Pick one base address for `PATTERN_REPLAY_*` and another for
  `INTERMISSION_*`. Document the chosen layout in
  `docs/field-manual/ram-base-layout.md`.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T034-integration-replay-test/replay.input` — recorded
  controller inputs.
- `tests/evidence/T034-integration-replay-test/checkpoints.txt` —
  expected (frame, hash, score, pellet count, Pac-Man tile, ghost tiles)
  vectors.
- `tests/evidence/T034-integration-replay-test/run_log.txt` — headless
  run with `--expect-frame-hash` at each checkpoint, exit 0.

**Reviewer checklist:**

- [ ] Headless run exits 0 with all checkpoints matching.
- [ ] Replay covers death and level advance.

**Rerun command:**

```
python3 tools/build.py
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless build/pacman.rom --replay tests/evidence/T034-integration-replay-test/replay.input --checkpoints tests/evidence/T034-integration-replay-test/checkpoints.txt > tests/evidence/T034-integration-replay-test/run_log.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-26 | Created, state: planned. |
