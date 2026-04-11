# Pac-Man Palette Slot Map

Generated from `source_rom/82s123.7f` by `tools/conv_palette.py`.

| Slot | PROM index | Arcade RGB | V9938 RGB | Role |
|---|---:|---|---|---|
| 0 | 0 | `#000000` | `0,0,0` | maze backdrop / VDP-A transparent color |
| 1 | 11 | `#2121FF` | `1,1,7` | maze wall blue |
| 2 | 9 | `#FFFF00` | `7,7,0` | Pac-Man yellow |
| 3 | 1 | `#FF0000` | `7,0,0` | Blinky red |
| 4 | 3 | `#FFB8FF` | `7,5,7` | Pinky pink |
| 5 | 5 | `#00FFFF` | `0,7,7` | Inky cyan |
| 6 | 7 | `#FFB851` | `7,5,2` | Clyde orange |
| 7 | 6 | `#47B8FF` | `2,5,7` | frightened blue |
| 8 | 15 | `#DEDEFF` | `6,6,7` | frightened white |
| 9 | 2 | `#DE9751` | `6,4,2` | dot / pellet peach |
| 10 | 1 | `#FF0000` | `7,0,0` | fruit red alias |
| 11 | 12 | `#00FF00` | `0,7,0` | fruit stem green |
| 12 | 15 | `#DEDEFF` | `6,6,7` | HUD white alias |
| 13 | 14 | `#FFB8AE` | `7,5,5` | reserved warm peach |
| 14 | 13 | `#47B8AE` | `2,5,5` | reserved teal |
| 15 | 0 | `#000000` | `0,0,0` | reserved black alias |

Notes:

- Slot 0 is black on both VDPs. VDP-A transparency comes from TP=1 in R#8.
- Slots 10, 12, and 15 intentionally keep arcade role aliases even though
  they share source RGB values with slots 3, 8, and 0.
- Slots 13 and 14 preserve the remaining distinct non-black colors present
  in PROM entries 0-15 so the swatch exercises every unique converted hue.
