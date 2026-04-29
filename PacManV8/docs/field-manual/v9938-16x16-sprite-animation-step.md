# V9938 16x16 Sprite Animation Step

**Context:** T028 added live Pac-Man mouth animation and ghost body wobble by
changing Sprite Mode 2 SAT pattern bytes each frame.
**The insight:** In 16x16 sprite mode, the V9938 ignores the lower two bits of
the SAT pattern byte and fetches a four-pattern group. Animation between
different 16x16 source sprites therefore has to advance the SAT pattern by
four, not by one. Direction groups that contain two wobble frames should be
addressed as `base + direction * 8 + wobble * 4`.
**Example:**

```asm
        ; Direction enum is 0-3, wobble phase is 0-1.
        add a, a
        add a, a
        add a, a
        add a, SPRITE_GHOST_NORMAL_BASE_PATTERN
        ld b, a
        ld a, (SPRITE_GHOST_WOBBLE_PHASE)
        and 0x01
        add a, a
        add a, a
        add a, b
```
