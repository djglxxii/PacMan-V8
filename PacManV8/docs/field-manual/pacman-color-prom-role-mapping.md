# Pac-Man Color PROM Role Mapping

**Context:** T004 palette extraction needed to decode the two permitted Pac-Man
color PROMs into Vanguard 8 V9938 palette assets.

**The insight:** In the standard MAME Pac-Man ROM split, `82s123.7f` is the
32-byte RGB palette PROM, while `82s126.4a` is the 256-byte color lookup PROM.
It is easy to reverse these because the larger PROM looks like it might contain
RGB entries, but MAME's `pacman_palette()` treats the first 32 bytes as the
resistor-weighted RGB source and the following 256 bytes as 64 groups of four
low-nibble color indices.

**Example:** Decode `82s123.7f` with red bits 0-2, green bits 3-5, and blue
bits 6-7. Then decode `82s126.4a` as lookup rows:

```text
82s123.7f[09] = 0x3F -> RGB yellow -> V9938 packed 77 00
82s126.4a group 01 = 00 0F 0B 01 -> black, white, blue, red
```
