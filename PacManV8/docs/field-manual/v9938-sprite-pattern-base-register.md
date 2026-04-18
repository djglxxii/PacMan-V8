# V9938 Sprite Pattern Base Register

**Context:** T013 uploaded Sprite Mode 2 patterns to the planned Graphic 4
VRAM sprite pattern area at `0x7000`, but the first runtime frame still showed
no sprites.

**The insight:** The V9938 sprite pattern generator base uses `R#6 << 11`.
For the recommended `0x7000` pattern base, `R#6` must be `0x0E`, not `0x07`.
If the SAT and color table are valid but sprites are invisible, confirm the
pattern base register before debugging sprite pattern bytes.

**Example:**

```asm
        VDP_REG_A 5, 0xF8          ; SAT base 0x7C00
        VDP_REG_A 6, 0x0E          ; Pattern base 0x7000
        VDP_REG_A 11, 0x00
```
