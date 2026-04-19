# VBlank-Driven YM2151 Review Sequencer

**Context:** T017 added the first YM2151 FM music cues while the IM1 handler was
already driven by VDP-A VBlank for deterministic PSG effects.

**The insight:** For short review music cues, a VBlank-driven YM2151 sequencer
is simpler and safer than enabling YM2151 timer IRQs. The YM2151 shares INT0
with VDP-A, so timer-driven sequencing requires full source arbitration in the
interrupt handler. A frame sequencer can still produce deterministic audio
hashes and register traces as long as every YM write polls status bit 7 before
writing the address and data ports.

**Example:**

```asm
audio_ym_write_bc:
.wait_address:
        in a, (YM_ADDR_PORT)
        and 0x80
        jr nz, .wait_address
        ld a, b
        out (YM_ADDR_PORT), a
.wait_data:
        in a, (YM_ADDR_PORT)
        and 0x80
        jr nz, .wait_data
        ld a, c
        out (YM_DATA_PORT), a
        ret
```

Pair this with a source-level Python harness that simulates the exact row
schedule and emits a register-trace hash. The trace catches accidental cue
changes even when the whole-ROM audio hash also includes PSG effects.
