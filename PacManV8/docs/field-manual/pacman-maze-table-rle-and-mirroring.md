# Pac-Man Maze Table RLE And Mirroring

**Context:** T005 needed to turn the level-1 maze data table into a
36-by-28 arcade-orientation nametable without disassembling program ROM code.

**The insight:** The maze drawing table at CPU ROM address `0x3435` is a
data-only RLE stream. The first byte is the destination video RAM offset
(`0x40`). Bytes `>= 0x80` are literal tile IDs, bytes `< 0x80` repeat the next
byte that many times, and `0x00` terminates the stream. It expands to `448`
bytes: one half of the 32-row center playfield. Place those bytes at video
RAM offsets `0x040-0x1FF`, map offsets through the Pac-Man column-major screen
layout, then fill the other half by horizontally mirroring the tile patterns
from `pacman.5e` and looking up the matching tile ID.

**Example:**

```python
destination = program_rom[0x3435]  # 0x40
position = 0x3436
expanded = []
while program_rom[position] != 0x00:
    value = program_rom[position]
    position += 1
    if value < 0x80:
        repeated = program_rom[position]
        position += 1
        expanded.extend([repeated] * value)
    else:
        expanded.append(value)

assert destination == 0x40
assert len(expanded) == 448
```
