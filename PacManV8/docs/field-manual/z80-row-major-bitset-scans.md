# Z80 Row-Major Bitset Scans

**Context:** T011 needed a compact runtime bitset for 28x36 pellet and
energizer presence, initialized from the generated semantic maze.

**The insight:** When scanning row-major data into a bitset on Z80, keep a
semantic pointer, a bitset pointer, and a rolling bit mask instead of computing
`index / 8` and `index % 8` for every cell. ALU operations cannot target
`(DE)`, so swap the bitset pointer into `HL` for memory updates, then swap back
before advancing the semantic stream.

**Example:**

```asm
        ld hl, movement_maze_semantic
        ld de, COLLISION_PELLET_BITS
        ld a, 0x01
        ld (COLLISION_WORK_MASK), a

.set_pellet:
        ex de, hl
        ld a, (COLLISION_WORK_MASK)
        or (hl)
        ld (hl), a
        ex de, hl

.advance_cell:
        inc hl
        ld a, (COLLISION_WORK_MASK)
        add a, a
        jr nz, .store_mask
        ld a, 0x01
        inc de
.store_mask:
        ld (COLLISION_WORK_MASK), a
```
