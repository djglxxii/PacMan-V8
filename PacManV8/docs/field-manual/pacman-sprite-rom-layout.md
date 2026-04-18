# pacman.5f sprite ROM layout and MAME gfx_layout bit conventions

**Context:** T013 first rendered VDP-A sprites from `assets/sprites.bin` and
the ghosts came out transposed (rotated 90°, with each ghost's two eyes
stacked vertically in a single column instead of sitting side-by-side on the
same row). Root cause was in the asset pipeline, not the Vanguard 8 side.

**The insight:** The Pac-Man sprite ROM (pacman.5f, 4096 bytes, 64 × 16x16
2bpp sprites) stores each sprite **column-first**, not row-first. Each byte
encodes 4 pixels of a single column across 4 vertical rows; advancing by one
**column** moves one full byte forward, while advancing by one **row** moves
just one bit within the current byte. Two concrete implications when writing
an extractor from the MAME `spritelayout`:

1. The `STEP8(…, 8)` offset table (the one with byte-aligned steps) is the
   **X** table — it walks across columns. The `STEP4(…, 1)` offset tables
   (the one-bit steps) form the **Y** table — they walk down rows inside one
   byte. A naïve reader looking at a `gfx_layout` and assuming "adjacent
   pixels share a byte ⇒ that's the X axis" gets this backwards for
   Pac-Man's Namco-format sprite ROM.
2. MAME `gfx_layout` bit offsets are MSB-first: bit offset `N` within a byte
   means "bit `7 − (N mod 8)` of that byte", not "bit `N mod 8`". A stock
   LSB-first `(byte >> (offset % 8)) & 1` extractor reverses the bit order
   inside every byte, which flips each 4-pixel column group left-right **and**
   swaps the two 2bpp planes (because the plane offsets `{0, 4}` live inside
   the same byte). The rendered output is usually unrecognizable noise.

Either defect alone will mangle the sprite; together they mask each other's
signature (the transpose from (1) and the intra-byte mirroring from (2) can
conspire to produce shapes that look vaguely ghost-like but wrong in ways
that aren't obvious until a reviewer sees them on screen).

**Diagnostic signature:** If a ghost renders as 90°-rotated with eyes in a
vertical column instead of a horizontal pair, suspect the X/Y table
assignment. If the shape is not just rotated but also speckled with
apparently-random gaps at 4-pixel intervals across every row, suspect the
MSB-vs-LSB bit-order bug on top of that.

**Example:** Corrected block from `tools/extract_sprites.py`:

```python
# X walks across columns: one byte per column-group of four columns.
X_BIT_OFFSETS = (
    0*8, 1*8, 2*8, 3*8, 4*8, 5*8, 6*8, 7*8,
    32*8, 33*8, 34*8, 35*8, 36*8, 37*8, 38*8, 39*8,
)
# Y walks down rows: one bit per row within each column's byte.
Y_BIT_OFFSETS = (
    8*8+0,  8*8+1,  8*8+2,  8*8+3,
    16*8+0, 16*8+1, 16*8+2, 16*8+3,
    24*8+0, 24*8+1, 24*8+2, 24*8+3,
    0, 1, 2, 3,
)

def read_bit(data, bit_offset):
    # MAME gfx_layout bit offsets count from the MSB of each byte.
    byte_index = bit_offset // 8
    bit_index = 7 - (bit_offset % 8)
    return (data[byte_index] >> bit_index) & 0x01
```

**Verification trick used:** When diagnosing an arcade-sprite extractor, dump
one expected ghost frame (e.g. sprite 8, Blinky chase) as a 2bpp ASCII grid
and check whether the two pupil pixels sit **on the same row** (correct) or
**in the same column** (transposed). That single check catches the X/Y swap
immediately without needing to render the ROM end-to-end.
