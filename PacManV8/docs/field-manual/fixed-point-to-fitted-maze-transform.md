# Fixed-Point To Fitted Maze Transform

**Context:** T015 needed Pac-Man and ghost sprites to line up with the
non-uniform 256x212 fitted maze while gameplay stayed in arcade 8.8
fixed-point coordinates.

**The insight:** Do not derive sprite Y from a single global scale factor after
T006's portrait fit. Use the generated coordinate-map record for the entity's
current arcade tile, then scale only the sub-tile 8.8 remainder by that
record's fitted cell height. This keeps tile centers identical to the maze
renderer's `rect.center` rule and avoids cumulative rounding drift across rows.

**Example:**

```python
tile_y = (arcade_y_fp >> 8) // 8
cell = record_at(coordmap, tile_x, tile_y)
within_y_fp = arcade_y_fp - ((tile_y * 8) << 8)
screen_center_y = cell.y + ((within_y_fp * cell.height) >> 11)
sprite_y = screen_center_y - 8
```

Horizontal mapping is still one arcade pixel to one V8 pixel inside the
centered 224-pixel maze, but using the coordinate-map record for both axes
keeps the transform tied to the same generated data as the framebuffer.
