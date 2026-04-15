# Portrait Maze Vertical Fit

**Context:** T006 needed to fit Pac-Man's 28-by-31 arcade maze into the
Vanguard 8's 196-pixel maze-height budget while preserving the arcade
player-view portrait orientation.

**The insight:** Keep the horizontal axis at native 8-pixel cell width and
center the resulting 224-pixel maze at `x=16`. Only the vertical axis needs
compression. Cumulative integer boundaries divide 196 pixels across 31 rows,
yielding deterministic 6- or 7-pixel row heights that sum exactly to 196.
Because adjacent rows share exact integer edges, graph continuity can be
validated with rectangle edge-touch tests instead of tolerance-based geometry.

**Example:**

```python
def make_bounds(total: int, segments: int) -> list[int]:
    return [(index * total) // segments for index in range(segments + 1)]

y_bounds = make_bounds(196, 31)

v8_x0 = 16 + arcade_x * 8
v8_x1 = v8_x0 + 8
v8_y0 = 8 + y_bounds[arcade_y - 3]
v8_y1 = 8 + y_bounds[arcade_y - 3 + 1]
```
