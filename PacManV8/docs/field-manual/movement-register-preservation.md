# Movement Register Preservation

**Context:** T021 replay validation reached the runtime movement path and
showed Pac-Man stopping immediately even though the maze semantic asset marked
the next cell as passable.

**The insight:** Runtime helper routines may reuse caller registers even when
their high-level purpose sounds like a predicate. `movement_try_turn_at_center`
stored the requested direction in `B`, then called
`movement_direction_passable_from_current_tile`; that callee reused `B` for the
candidate tile X coordinate. The caller then wrote tile X as the current
direction, which was rejected on the next passability check. Preserve direction
registers across movement/collision predicates unless the callee contract
explicitly says they survive.

**Example:**

```asm
        ld a, (PACMAN_REQUESTED_DIR)
        ld b, a
        push bc
        call movement_direction_passable_from_current_tile
        pop bc
        or a
        ret z
        ld a, b
        ld (PACMAN_CURRENT_DIR), a
```
