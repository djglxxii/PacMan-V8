# Wrapped 8.8 Y Coordinate Transform

**Context:** T026 ported the Python arcade-to-V8 fitted-maze coordinate
transform into a runtime Z80 routine that accepts 16-bit 8.8 entity
coordinates.

**The insight:** A 36-row arcade grid is 288 pixels tall, so rows 32-33
produce Y pixel values 256-271 and do not fit directly in a 16-bit 8.8 value.
Those rows are still mapped maze rows, while top rows 0-2 and bottom rows
34-35 are unmapped. A runtime table can safely treat high-byte values
0x00-0x0F as wrapped pixels 256-271 for rows 32-33, while values 0x18-0xFF
map normally. Values 0x10-0x17 remain unmapped/hidden.

**Example:** `tools/generate_coord_lut.py` generates the Y tables with the
same fitted-maze row rectangles as `tools/coordinate_transform.py`:

```python
wrapped_mapped_pixels = (MAZE_TOP + MAZE_ROWS) * ARCADE_TILE_SIZE - 256
if y_px_byte < wrapped_mapped_pixels:
    arcade_y_px = y_px_byte + 256
else:
    arcade_y_px = y_px_byte
```

This preserves lower-maze sprite placement without adding a third coordinate
byte to the Z80 routine's `HL = Y 8.8, DE = X 8.8` calling convention.
