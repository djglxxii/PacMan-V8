# T025 Review Findings — Round 2

**Reviewer:** Claude (review pass)
**Date:** 2026-04-27
**Verdict:** Not accepted. Do not mark complete. Address items below before
re-submitting.

The previous review (`T025-review-findings.md`, dated 2026-04-26) listed four
required corrective actions. Two of those (opcode workarounds reverted; broken
`ghost_id_to_reversal_bit` fixed) are confirmed done. The remaining items —
mostly around evidence quality and the re-block decision — were not satisfied.
A new defect (emulator replay does not deliver controller state) was
discovered mid-task and should have re-blocked T025 instead of being papered
over with neutral-input evidence.

The issues below are listed in the order they should be addressed.

---

## 1. Newly-discovered emulator defect should re-block the task

**Status:** Task should be moved to `docs/tasks/blocked/`.

The progress log (entry 2026-04-27) records:

> Discovered emulator replay mechanism does not feed controller state to
> `in a, (0x00)` — CPU reads 0xFF regardless of replay file. Acceptance
> evidence collected without replay (neutral input). Replay-based
> turn/energizer testing blocked on emulator fix.

This is exactly the situation `CLAUDE.md` §5 describes:

> If any external-tool or emulator error prevents the active task from
> continuing, move the task file to `docs/tasks/blocked/`, add a precise
> **Blocker** section to the task file, update `docs/tasks/INDEX.md`, report
> the blocker, and stop.

The previous review (item 3) listed two evidence requirements that depend on
working replay input — Pac-Man turning at an intersection, and Pac-Man eating
an energizer to demonstrate the 3-frame stall. Both are unsatisfiable until
the emulator delivers replay controller state to `IN A,(0x00)`. The task
cannot be completed without those pieces, so it should not have stayed in
`active/` once the defect was identified.

### Required corrective action

- Move `docs/tasks/active/T025-per-frame-playing-tick.md` back to
  `docs/tasks/blocked/`.
- Add a precise **Blocker** section describing:
  - The exact symptom: replay file frames specify controller mask, the
    emulator's inspection report displays the masked state, but the CPU's
    `IN A,(0x00)` reads `0xFF` (idle) regardless.
  - A minimal repro: replay file with one non-neutral mask + a 1-instruction
    test ROM that loops `IN A,(0x00)` and writes the value to RAM, peeked
    via `--peek-logical`.
  - The plumbing path the user/agent should look at on the emulator side
    (replay-driven controller state vs. the I/O port `0x00` read handler).
- Update `docs/tasks/INDEX.md` to reflect the state change.
- Stop and wait for the user.

---

## 2. Acceptance evidence is not reproducible from the rerun command

**Status:** Build-reproducibility violation (`CLAUDE.md` §6).

The task file's rerun command is:

```
python3 tools/build.py
python3 tools/playing_tick_tests.py > tests/evidence/T025-per-frame-playing-tick/tick_trace.txt
```

I executed `python3 tools/playing_tick_tests.py` against the current `master`.
Three independent problems:

### 2a. The script writes the trace file itself, so the `>` redirect is dead code

`tools/playing_tick_tests.py:213-214`:

```python
trace = EVIDENCE / "tick_trace.txt"
trace.write_text("\n".join(lines) + "\n")
```

The `> tick_trace.txt` in the rerun command does not produce the file. The
script overwrites it directly. Either remove the redirect from the rerun
command, or remove the `write_text` call from the script — pick one source
of truth.

### 2b. Format does not match the committed trace

Committed `tests/evidence/T025-per-frame-playing-tick/tick_trace.txt` header:

```
# frame    st        pac   dir   req     blinky  bdir pellets stall
```

The script's actual header (line 105):

```python
header = f"{'frame':>5s} {'state':>5s} {'pac':>10s} {'p_dir':>5s} {'blinky':>10s} {'b_dir':>5s} {'pellets':>7s} {'stall':>5s}"
```

Resolves to: `frame state pac p_dir blinky b_dir pellets stall`.

The committed file has an extra `req` column (requested direction); the
script does not emit one. Whatever produced the committed file is not the
script committed in `tools/`. This is the §6 violation.

### 2c. The fresh run from the script fails the task's own acceptance criteria

Running `python3 tools/playing_tick_tests.py` against the current build
produces:

```
# Pac-Man visited 1 unique tiles across 21 checkpoints
# FAIL: Pac-Man moved across >= 3 tiles
# Stall events detected: 0
# Pellet stall detected: NO
# Energizer stall detected: NO
```

Pac-Man reads as `(0,0)` at every checkpoint; Blinky moves correctly,
suggesting the address layout for ghost peeks is right but the Pac-Man peek
(`0x8100:8` at offsets 0/2/3) is either pointed at uninitialized memory or
the live tick is not advancing Pac-Man under the script's replay. Either
way: the rerun command does not reproduce the committed evidence.

### Required corrective action

- Pick one source of truth for `tick_trace.txt` (script-authored, not redirected).
- Make sure the committed trace is byte-for-byte what the rerun command
  produces against the committed code.
- Investigate why the fresh run reads Pac-Man at `(0,0)`. Likely candidates:
  - Script's peek address/offsets for Pac-Man are stale relative to the asm
    (verify against `PACMAN_*` symbols).
  - Replay-driven boot path doesn't reach PLAYING with Pac-Man initialized
    in the same frame window the script samples (the previous trace was
    "no replay"; the script always uses replay).
  - Real regression in `game_state_init` or the new tick under live input.

Do not paper this over by editing the trace file by hand.

---

## 3. Reviewer-required evidence items are still missing

The previous review (`T025-review-findings.md` §3) demanded the re-recorded
evidence include:

- [ ] Dense sampling around at least one pellet pickup, demonstrating the
      1-frame pellet stall.
- [ ] An energizer pickup demonstrating the 3-frame stall.
- [ ] At least one Pac-Man turn at an intersection.
- [ ] `tools/ghost_ai_tests.py` reference comparison showing ghost behavior
      matches expectations.
- [x] Frame-300 PPM regenerated against the fixed build.

Only the frame dump is satisfied. The committed `tick_trace.txt` even
acknowledges the gap:

```
# [~] Dot-stall: not captured at this sampling rate (1-frame stalls need every-frame scan)
```

The task's own reviewer checklist requires "Dot-stall produces the expected
1-frame freeze on pellet, 3-frame on energizer." That is a hard-coded
acceptance criterion, not an aspirational one — partial credit is not
acceptable.

The "not practical with current per-frame headless invocation overhead"
justification in the trace file is also unconvincing: the script is already
running ~30 headless invocations sequentially; running ~10 more across a
known pellet-eating window is the same order of magnitude. The real issue
is the replay defect (item 1), which prevents routing Pac-Man over a known
pellet/energizer at all.

### Required corrective action

After the emulator replay defect is fixed (item 1):

- Add dense (every-frame) sampling around at least one pellet pickup; the
  trace should show three rows: pre-stall, `stall=1`, post-stall.
- Route Pac-Man over an energizer; the trace should show pre-stall,
  `stall=3` (or the row decrementing 3→2→1), post-stall.
- Have Pac-Man execute at least one turn at an intersection so the trace
  contains a non-trivial direction change driven by replay input.
- Run `tools/ghost_ai_tests.py` against the live tick (or a clearly
  documented adapter), and include either a clean pass or a side-by-side
  diff in the evidence directory.

---

## 4. Smaller items

### 4a. Stale `blocked/T025-review-findings.md`

The first review-findings file is still in `docs/tasks/blocked/`. Once
T025 is re-blocked (item 1), keep that file alongside the new findings —
the historical record is useful. If T025 is instead re-completed without
re-blocking, the prior findings file should move alongside the task to
`completed/` (or be referenced from the task body) so the history stays
discoverable.

### 4b. Field-manual entry on opcode workarounds

The previous review (§1) suggested removing or rewriting
`docs/field-manual/emulator-unsupported-opcodes.md`. I did not see an entry
by that name in the current `docs/field-manual/` listing, so this appears
to have been resolved already — but worth confirming the prior workaround
guidance is gone and not preserved under a different name.

### 4c. INDEX.md state must reflect the re-block

When T025 moves back to `blocked/`, update its row in
`docs/tasks/INDEX.md` (currently `active`) and the "Current focus" section
at the top.

---

## Summary of required corrective actions

1. **Move T025 to `blocked/`** with a precise Blocker section describing
   the emulator replay defect (controller state not delivered to
   `IN A,(0x00)` during replay). Update `INDEX.md`. Stop.
2. After the emulator is patched:
   - Reconcile `tools/playing_tick_tests.py` with the committed trace
     format. The rerun command must produce the committed file byte-for-byte.
     Fix the script-vs-redirect contradiction.
   - Diagnose the Pac-Man `(0,0)` reading — either fix the peek address
     layout in the script, or fix the genuine state-init regression.
   - Re-record evidence with: dense sampling + visible 1-frame pellet stall;
     visible 3-frame energizer stall; at least one Pac-Man turn at an
     intersection; `ghost_ai_tests.py` reference comparison.
   - Regenerate the frame dumps against the final build.
3. Only then re-submit T025 for review.

---

## What is confirmed correct (no action needed)

- `ghost_id_to_reversal_bit` is now correctly `1 << ID` for IDs 0-3
  (`src/game_state.asm:278-289`).
- `movement_try_turn_at_center` allows immediate turn when
  `CURRENT_DIR == MOVEMENT_DIR_NONE` (`src/movement.asm:116-136`).
- Opcode workarounds are gone from `src/game_state.asm` and
  `src/ghost_ai.asm` — natural Z80 instructions are restored.
- The fixed-frame-300 PPM artifact is regenerated and present in
  `tests/evidence/T025-per-frame-playing-tick/`.
