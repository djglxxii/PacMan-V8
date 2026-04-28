# T025 Review Findings

**Reviewer:** human + Claude (review pass)
**Date:** 2026-04-26
**Verdict:** Not accepted. Do not mark complete. Address items below before
re-submitting.

The issues are listed in the order they should be addressed. Item 1 is a
process issue that must be resolved before any of the code work below is
re-done — otherwise the workarounds get rebuilt on top of the same broken
foundation.

---

## 1. Operating-contract violation: emulator opcode workarounds

**Status:** Must be reverted.

The progress log and `docs/field-manual/emulator-unsupported-opcodes.md`
document that the headless emulator rejected two opcodes during the new
PLAYING tick:

- `EX AF, AF'` (0x08)
- `LD DE, (nn)` (ED 5B)

Instead of stopping and reporting, the agent worked around both:

- `src/game_state.asm:25` — added `GHOST_MOVE_MODE_TEMP` as a memory scratch
  to replace `EX AF, AF'`.
- `src/ghost_ai.asm:856-862` — replaced `ld de, (GHOST_BEST_DISTANCE)` with
  `push hl / ld hl,(nn) / ex de,hl / pop hl`.

`CLAUDE.md` §5 (Operating rules) is explicit:

> If the Vanguard 8 emulator reports an unsupported opcode, stop and report
> the exact opcode, PC, command, and minimal repro. Do not rewrite the ROM
> to avoid the opcode unless the opcode is clearly accidental or
> unimportant. Let the user patch the emulator when the missing opcode is
> important to the implementation.

Neither `EX AF, AF'` nor `LD DE, (nn)` is accidental or unimportant — both
are core Z80 instructions used routinely. The correct path was:

1. Move T025 to `docs/tasks/blocked/`.
2. Add a **Blocker** section listing the confirmed-missing opcodes (with
   PC and context) plus a probe for additional likely-missing opcodes —
   per CLAUDE.md, "look ahead for additional missing opcodes before
   reporting."
3. Stop.

### Required corrective action

- Revert both workarounds (`game_state.asm` `GHOST_MOVE_MODE_TEMP` use and
  `ghost_ai.asm:856-862`) so the natural Z80 instructions are restored.
- Move `docs/tasks/active/T025-per-frame-playing-tick.md` to
  `docs/tasks/blocked/`.
- Update `docs/tasks/INDEX.md` to reflect the state change.
- In the task file's **Blocker** section, list:
  - **Confirmed missing:** `EX AF, AF'` (0x08), `LD DE, (nn)` (ED 5B), with
    the PC and the source line that emitted each.
  - **Suspected missing:** scan the new tick code paths (the new
    `game_state_tick_playing`, `movement_update_ghosts`,
    `movement_ghost_step`, and any ghost-AI code paths now reachable from
    the live tick) for other instructions plausibly unimplemented by the
    emulator's "timed" path: ED-prefixed block ops (`LDIR`, `LDDR`, `CPI`,
    `CPIR`, `INI`, `OUTI`, etc.), DD/FD `(IX+d)`/`(IY+d)` variants,
    CB-prefixed bit ops, and any other unusual instruction the new code
    emits. Mark each as confirmed or suspected.
- Stop and wait for the user to patch the emulator.

The field-manual entry `docs/field-manual/emulator-unsupported-opcodes.md`
should also be removed or rewritten — it currently documents the
workaround pattern, which directly contradicts CLAUDE.md §5. If anything
about emulator opcode handling deserves a field-manual entry, it is the
*process* (probe, batch, block, wait), not the workaround code.

---

## 2. Code bug: `ghost_id_to_reversal_bit` is broken

**Location:** `src/game_state.asm:271-279`

```asm
ghost_id_to_reversal_bit:
        ld b, a
        ld a, 1
        or b          ; pollutes A with ID bits before the shift
        ret z
.loop:
        add a, a
        djnz .loop
        ret
```

The intent is `A = 1 << ID`. Actual behavior:

| ID | `A` after `or b` | shifts | result | expected |
|----|------------------|--------|--------|----------|
| 0  | 1                | 256 (djnz wraps when B=0) | 0  | 1 |
| 1  | 1                | 1      | 2      | 2 ✓ (accidental — `1|1 == 1`) |
| 2  | 3                | 2      | 12     | 4 |
| 3  | 3                | 3      | 24     | 8 |

Blinky (ID=0) is the only ghost actually outside the house in the trace,
and his reversal mask is `0` — meaning `and b` against
`GHOST_REVERSAL_PENDING` is always zero and reversals never fire for him.
Pinky/Inky/Clyde will misbehave when they leave the house.

### Required corrective action

- Don't introduce a new helper if `ghost_ai.asm` already has an
  ID→mask conversion. Audit and reuse if so.
- If a new helper is genuinely needed, write it correctly. A clean form:

  ```asm
  ; Input: A = ghost ID (0..3). Output: A = 1 << ID.
  ghost_id_to_reversal_bit:
          or a
          ld a, 1
          ret z
          ld b, a
  .loop:  add a, a
          djnz .loop
          ret
  ```

- After the fix, add coverage that exercises at least one ghost other than
  Blinky leaving the house and reversing on a mode change, so this can't
  regress silently again.

---

## 3. Acceptance evidence does not satisfy the reviewer checklist

**Artifact:** `tests/evidence/T025-per-frame-playing-tick/tick_trace.txt`

The task's reviewer checklist requires:

- [ ] Pac-Man tile changes over time.
- [ ] At least one ghost's tile changes over time.
- [ ] Pellet count decreases as Pac-Man moves over pellet tiles.
- [ ] Dot-stall produces the expected 1-frame freeze on pellet, 3-frame on
      energizer.
- [ ] No regression in earlier task evidence.

What the trace actually shows:

### 3a. Dot-stall criterion is not demonstrated

The `stall` column is `0` at every checkpoint. The sampling interval
(5–20 frames between samples) is far too coarse to observe a 1-frame
pellet freeze, and no energizer is exercised, so the 3-frame stall is
never visible.

**Fix:** add dense sampling (every frame for ~10 frames around each
pellet pickup), and route Pac-Man over an energizer at least once.
Capture both the pellet stall and the energizer stall as distinct
windows in the trace, with explicit before/during/after rows.

### 3b. Pac-Man stops at a wall and never recovers

```
460 PLAY (21,26)  NONE     ( 5,14) RIGHT   234     0  Pac-Man stopped at wall
...
600 PLAY (21,26)  NONE     (12,14) RIGHT   234     0  Pac-Man stopped at wall
```

The replay script (`tools/playing_tick_tests.py:135-141`) continues to
push UP, LEFT, DOWN, then RIGHT after the initial RIGHT segment. Pac-Man
should turn at the next legal intersection, not sit indefinitely. Either
the replay-input plumbing isn't being honored once the live tick is
driving, or `movement_request_direction` isn't picking up the new held
direction after Pac-Man's velocity goes to zero.

**Fix:** investigate (don't paper over with an annotation). Confirm the
held direction is reaching `MOVEMENT_DIR_REQUESTED`, and that the turn
attempt fires when Pac-Man is at a tile center with `DIR_NONE`. Once
fixed, the trace should show Pac-Man making at least one turn at an
intersection.

### 3c. Suspicious ghost movement

Blinky's path:

```
(14,14) → (15,14) → (17,14) → (18,14) → (20,14) → (23,14) → (25,14) → (0,14) → (5,14) → ... → (25,14) → (2,14) → ...
```

Two problems:

1. Row 14 is inside the ghost-house lane. Blinky should hit walls and
   turn off this row almost immediately, not traverse the full maze
   width along it.
2. The transition (25,14) → (0,14) is the tunnel-wrap branch in
   `.right` (`game_state.asm:249-257`) firing on a non-tunnel row.
   Tunnels are at row 17, not 14. The wrap should be gated on
   "is this tile on the tunnel row" or, more correctly, on the wall
   table — `ghost_choose_direction` should never have selected RIGHT if
   the tile to the right is a wall.

This points to ghost AI selecting/applying directions without
consulting walls — possibly tied to item 2 above (broken reversal mask),
possibly a deeper issue in `ghost_choose_direction` integration. The
task promised a side-by-side against `tools/ghost_ai_tests.py`; that
comparison was not actually run.

**Fix:** identify whether `ghost_choose_direction` is consulting the
wall map for the tick's tile, and whether `movement_ghost_step` should
be deferring the wall check at all (it currently moves blindly in the
chosen direction). Run the existing `tools/ghost_ai_tests.py` reference
against the new tick path and include the diff (or a clean pass) in the
evidence.

---

## 4. Smaller items

### 4a. Misleading implementation-note assumption

The task file's implementation notes say "preserve the audio-IRQ path
while replacing the PLAYING-state body." Reading the original
`game_flow_update_frame`, the `.timer` block contains only the
state-timer countdown — no audio IRQ. The new `ret` after
`game_state_tick_playing` correctly bypasses the timer (since PLAYING
is now unbounded), so this is fine in practice, but the progress log
should be updated to note the original assumption was inaccurate so
future readers don't hunt for a missing audio side-effect.

### 4b. INDEX.md state

`docs/tasks/INDEX.md` is staged-modified. When T025 moves to `blocked/`,
re-check that its row reflects the new state, dependencies, and a link
to the blocker description.

---

## Summary of required corrective actions

1. **Revert** both opcode workarounds and the field-manual entry that
   documents them.
2. **Move** T025 from `active/` to `blocked/`; add a precise **Blocker**
   section listing confirmed and suspected missing opcodes (probed, not
   guessed); update `INDEX.md`. **Stop.**
3. After the emulator is patched and the task is unblocked:
   - Re-implement the tick using the natural opcodes.
   - Fix or remove `ghost_id_to_reversal_bit` (prefer reusing existing
     ghost_ai helpers).
   - Investigate why Pac-Man halts permanently after the first wall and
     why Blinky traverses row 14 / wraps at the maze edge — these are
     real defects, not trace artifacts.
   - Re-record evidence with:
     - dense sampling around at least one pellet pickup and one
       energizer pickup, demonstrating the 1-frame and 3-frame stalls;
     - at least one Pac-Man turn at an intersection;
     - a `tools/ghost_ai_tests.py` reference comparison showing ghost
       behavior matches expectations;
     - the frame-300 PPM (already produced) regenerated against the
       fixed build.
4. Only then re-submit T025 for review.
