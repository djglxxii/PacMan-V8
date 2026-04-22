# Preserve State Across Flag Helper Calls

**Context:** T020 resumed after the emulator HALT-resume fix and exposed a
runtime game-flow stall. The state machine entered `DYING`, but the state timer
was loaded as zero and the flow never advanced to `CONTINUE`.

**The insight:** Do not keep semantic state in `B` across helper calls that also
use `B` as a scratch flag register. `game_flow_transition_to` passed the target
state in `B`, then called `game_flow_mark_state_seen`; that helper overwrote
`B` with the review-flag bit. The timer loader then received a flag byte such
as `0x08` instead of state `0x03`, fell through to the unknown-state case, and
stored a zero timer.

**Example:**

```asm
        ld a, b
        push af
        call game_flow_mark_state_seen
        pop af
        cp GAME_FLOW_STATE_INTERMISSION
        jr z, .start_intermission
        jp game_flow_load_state_timer
```

Preserve the value explicitly on the stack or reload it from authoritative SRAM
after the helper returns; do not rely on scratch registers retaining meaning
across subroutine boundaries.
