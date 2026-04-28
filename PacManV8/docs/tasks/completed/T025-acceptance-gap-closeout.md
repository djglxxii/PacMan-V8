# T025 — Acceptance Gap Closeout

Two reviewer-checklist items in `T025-per-frame-playing-tick.md` are unchecked.
Resolve both before reporting back.

## 1. Demonstrate the 3-frame energizer stall

Extend the replay route in `tools/playing_tick_tests.py` to drive Pac-Man over
an energizer. Energizers sit at the four maze corners — confirm exact tile
coordinates from `assets/maze_semantic.bin` (`SEMANTIC_ENERGIZER = 3`). The
closest energizer is reachable from start (14,26) with a short route.

Capture a dense per-frame trace across the energizer pickup and append it to
`tests/evidence/T025-per-frame-playing-tick/tick_trace.txt` showing:

- `stall = 3, 3, 3, 0` across 4 consecutive frames
- Pellet count decreasing by the energizer delta on the pickup frame

Check the box in the task file.

## 2. Verify the "T021 was already broken pre-T025" claim

Do not take the prior agent's word for this. Run:

```bash
git stash
git checkout f3959bb -- src/   # last commit before T025 work
python3 tools/build.py
python3 tools/pattern_replay.py   # or T021's rerun command
git checkout HEAD -- src/
git stash pop
```

**If T021 fails on `f3959bb`:** document the failure mode in the task's
progress log with the exact error and command output. The regression check
is satisfied. Check the box.

**If T021 passes on `f3959bb`:** T025 introduced a regression. Do not accept.
Investigate which T025 change broke it — likely candidates are the B-clobber
fix in `movement.asm:90-99` or the ghost edge-wrap gating in `ghost_ai.asm`
and `game_state.asm`. Report findings and stop.

## Reporting

Stop and report when both boxes are checked. Do not move the task to
`completed/` — that is the human reviewer's call.
