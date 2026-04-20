# Frame Loop State Updates Preserve Audio Hashes

**Context:** T018 added the first game-flow state machine while T016/T017
already had accepted VBlank-driven PSG/YM2151 audio evidence.

**The insight:** Keep non-audio per-frame state work out of the IM1 handler
when preserving audio evidence. Even when audio register writes and event-log
digests remain stable, extra CPU work in or around the interrupt path can
change headless PCM hashes. For review-only frame counters, update after
`HALT` returns in the main loop and leave IM1 focused on clearing VBlank and
running `audio_update_frame`.

The timed emulator also reported `Unsupported timed Z180 opcode 0x2B` for
`DEC HL` in the new state timer path. For nonessential review timers, a
bytewise decrement using already-covered 8-bit operations avoided creating an
external emulator blocker.

**Example:**

```asm
im1_handler:
        in a, (VDP_A_CTRL)
        call audio_update_frame
        ; pop registers, EI, RETI

idle_loop:
        ei
        halt
        call game_flow_update_frame
        jp idle_loop

; Avoid DEC HL in timed-runtime-sensitive review code:
        ld hl, (GAME_FLOW_STATE_TIMER)
        ld a, l
        or a
        jr nz, .decrement_low
        dec h
        ld l, 0xFF
        jr .timer_decremented
.decrement_low:
        dec l
.timer_decremented:
        ld (GAME_FLOW_STATE_TIMER), hl
```
