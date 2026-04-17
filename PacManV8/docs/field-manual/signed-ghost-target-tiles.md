# Signed Ghost Target Tiles

**Context:** T009 ghost AI targeting needed scatter targets above the maze and
Pinky/Inky chase targets that can move left or above Pac-Man's current tile.

**The insight:** Keep ghost targets as signed arcade tile coordinates, even
when candidate movement cells stay in the normal 0..27 by 0..35 maze bounds.
On Z80, the signed difference can stay in one byte as long as the coordinate
range is small: subtract the target byte from the candidate byte, then take a
two's-complement absolute value before squaring. This handles top scatter
targets like `y=-3` stored as `0xFD` without clamping or special cases.

**Example:** A candidate at `(25,4)` compared with Blinky's scatter target
`(25,-3)` stores the target y as `0xFD`. The byte subtraction `4 - 0xFD`
wraps to `7`, so the normal absolute-value and square path produces `49`.
