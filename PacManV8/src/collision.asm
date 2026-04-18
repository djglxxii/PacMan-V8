; Pellet, energizer, dot-stall, and same-tile ghost collision state for T011.
; This slice stays in arcade tile coordinates and exposes data for later
; rendering/game-flow code without performing score, lives, or VDP updates.

COLLISION_MAZE_CELLS        EQU MOVEMENT_MAZE_WIDTH * MOVEMENT_MAZE_HEIGHT
COLLISION_BITSET_BYTES      EQU 126

COLLISION_CONSUME_NONE      EQU 0
COLLISION_CONSUME_PELLET    EQU 1
COLLISION_CONSUME_ENERGIZER EQU 2

COLLISION_GHOST_NONE        EQU 0
COLLISION_GHOST_PACMAN_DIES EQU 1
COLLISION_GHOST_EATEN       EQU 2

COLLISION_STATE_BASE        EQU 0x8180
COLLISION_PELLET_BITS       EQU COLLISION_STATE_BASE
COLLISION_PELLET_COUNT      EQU COLLISION_PELLET_BITS + COLLISION_BITSET_BYTES
COLLISION_ENERGIZER_COUNT   EQU COLLISION_PELLET_COUNT + 2
COLLISION_DOT_STALL         EQU COLLISION_ENERGIZER_COUNT + 2
COLLISION_ERASE_PENDING     EQU COLLISION_DOT_STALL + 1
COLLISION_ERASE_TILE_X      EQU COLLISION_ERASE_PENDING + 1
COLLISION_ERASE_TILE_Y      EQU COLLISION_ERASE_TILE_X + 1
COLLISION_ERASE_KIND        EQU COLLISION_ERASE_TILE_Y + 1
COLLISION_LAST_CONSUME      EQU COLLISION_ERASE_KIND + 1
COLLISION_LAST_GHOST_RESULT EQU COLLISION_LAST_CONSUME + 1

COLLISION_WORK_BASE         EQU 0x8210
COLLISION_WORK_INDEX        EQU COLLISION_WORK_BASE
COLLISION_WORK_MASK         EQU COLLISION_WORK_INDEX + 2
COLLISION_WORK_SEMANTIC     EQU COLLISION_WORK_MASK + 1
COLLISION_WORK_TILE_X       EQU COLLISION_WORK_SEMANTIC + 1
COLLISION_WORK_TILE_Y       EQU COLLISION_WORK_TILE_X + 1

collision_init:
        ld hl, COLLISION_PELLET_BITS
        ld b, COLLISION_BITSET_BYTES
        xor a
.clear_bits:
        ld (hl), a
        inc hl
        djnz .clear_bits

        ld hl, 0
        ld (COLLISION_PELLET_COUNT), hl
        ld (COLLISION_ENERGIZER_COUNT), hl
        xor a
        ld (COLLISION_DOT_STALL), a
        ld (COLLISION_ERASE_PENDING), a
        ld (COLLISION_ERASE_TILE_X), a
        ld (COLLISION_ERASE_TILE_Y), a
        ld (COLLISION_ERASE_KIND), a
        ld (COLLISION_LAST_CONSUME), a
        ld (COLLISION_LAST_GHOST_RESULT), a

        ld hl, movement_maze_semantic
        ld de, COLLISION_PELLET_BITS
        ld bc, COLLISION_MAZE_CELLS
        ld a, 0x01
        ld (COLLISION_WORK_MASK), a

.scan_cell:
        ld a, (hl)
        cp SEMANTIC_PELLET
        jr z, .set_pellet
        cp SEMANTIC_ENERGIZER
        jr z, .set_energizer
        jr .advance_cell

.set_pellet:
        ex de, hl
        ld a, (COLLISION_WORK_MASK)
        or (hl)
        ld (hl), a
        ex de, hl
        push hl
        ld hl, (COLLISION_PELLET_COUNT)
        inc hl
        ld (COLLISION_PELLET_COUNT), hl
        pop hl
        jr .advance_cell

.set_energizer:
        ex de, hl
        ld a, (COLLISION_WORK_MASK)
        or (hl)
        ld (hl), a
        ex de, hl
        push hl
        ld hl, (COLLISION_ENERGIZER_COUNT)
        inc hl
        ld (COLLISION_ENERGIZER_COUNT), hl
        pop hl

.advance_cell:
        inc hl
        ld a, (COLLISION_WORK_MASK)
        add a, a
        jr nz, .store_mask
        ld a, 0x01
        inc de
.store_mask:
        ld (COLLISION_WORK_MASK), a
        dec bc
        ld a, b
        or c
        jr nz, .scan_cell
        ret

; Consume the pellet/energizer under Pac-Man only when his position is exactly
; on a tile center. Output A = COLLISION_CONSUME_* result.
collision_update_pellet_at_pacman:
        xor a
        ld (COLLISION_LAST_CONSUME), a
        call movement_is_at_center
        or a
        jr z, .none
        ld a, (PACMAN_X_FP + 1)
        srl a
        srl a
        srl a
        ld b, a
        ld a, (PACMAN_Y_FP + 1)
        srl a
        srl a
        srl a
        ld c, a
        call collision_consume_tile
        ret
.none:
        xor a
        ret

; Input: B = tile x, C = tile y.
; Output: A = COLLISION_CONSUME_* result.
collision_consume_tile:
        ld a, b
        ld (COLLISION_WORK_TILE_X), a
        ld a, c
        ld (COLLISION_WORK_TILE_Y), a
        xor a
        ld (COLLISION_LAST_CONSUME), a

        call collision_prepare_tile
        jr nc, .none
        cp SEMANTIC_PELLET
        jr z, .pellet_candidate
        cp SEMANTIC_ENERGIZER
        jr z, .energizer_candidate
.none:
        xor a
        ret

.pellet_candidate:
        ld d, COLLISION_CONSUME_PELLET
        jr .check_present
.energizer_candidate:
        ld d, COLLISION_CONSUME_ENERGIZER

.check_present:
        ld a, (COLLISION_WORK_MASK)
        ld e, a
        ld a, (hl)
        and e
        jr z, .none

        ld a, e
        cpl
        and (hl)
        ld (hl), a

        ld a, d
        cp COLLISION_CONSUME_ENERGIZER
        jr z, .apply_energizer

.apply_pellet:
        push hl
        ld hl, (COLLISION_PELLET_COUNT)
        dec hl
        ld (COLLISION_PELLET_COUNT), hl
        pop hl
        ld a, 1
        ld (COLLISION_DOT_STALL), a
        ld a, COLLISION_CONSUME_PELLET
        call collision_record_erase
        ld a, COLLISION_CONSUME_PELLET
        ld (COLLISION_LAST_CONSUME), a
        ret

.apply_energizer:
        push hl
        ld hl, (COLLISION_ENERGIZER_COUNT)
        dec hl
        ld (COLLISION_ENERGIZER_COUNT), hl
        pop hl
        ld a, 3
        ld (COLLISION_DOT_STALL), a
        ld a, COLLISION_CONSUME_ENERGIZER
        call collision_record_erase
        call ghost_enter_frightened
        ld a, COLLISION_CONSUME_ENERGIZER
        ld (COLLISION_LAST_CONSUME), a
        ret

; Input: A = COLLISION_CONSUME_PELLET or COLLISION_CONSUME_ENERGIZER.
collision_record_erase:
        ld (COLLISION_ERASE_KIND), a
        ld a, 1
        ld (COLLISION_ERASE_PENDING), a
        ld a, (COLLISION_WORK_TILE_X)
        ld (COLLISION_ERASE_TILE_X), a
        ld a, (COLLISION_WORK_TILE_Y)
        ld (COLLISION_ERASE_TILE_Y), a
        ret

collision_clear_erase_queue:
        xor a
        ld (COLLISION_ERASE_PENDING), a
        ld (COLLISION_ERASE_KIND), a
        ret

collision_tick_dot_stall:
        ld a, (COLLISION_DOT_STALL)
        or a
        ret z
        dec a
        ld (COLLISION_DOT_STALL), a
        ret

; Input: B = tile x, C = tile y.
; Output: carry set if the tile was in bounds; A = semantic class; HL = bit byte.
collision_prepare_tile:
        ld a, c
        cp MOVEMENT_MAZE_HEIGHT
        jr nc, .invalid
        ld a, b
        cp MOVEMENT_MAZE_WIDTH
        jr nc, .invalid

        push bc
        ld h, 0
        ld l, c
        add hl, hl
        ld de, movement_row_offsets
        add hl, de
        ld e, (hl)
        inc hl
        ld d, (hl)
        ex de, hl
        pop bc
        ld e, b
        ld d, 0
        add hl, de
        ld (COLLISION_WORK_INDEX), hl

        ld a, l
        and 0x07
        ld b, a
        ld a, 0x01
        jr z, .mask_ready
.mask_loop:
        add a, a
        djnz .mask_loop
.mask_ready:
        ld (COLLISION_WORK_MASK), a

        ld hl, (COLLISION_WORK_INDEX)
        ld de, movement_maze_semantic
        add hl, de
        ld a, (hl)
        ld (COLLISION_WORK_SEMANTIC), a

        ld hl, (COLLISION_WORK_INDEX)
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        ld de, COLLISION_PELLET_BITS
        add hl, de
        ld a, (COLLISION_WORK_SEMANTIC)
        scf
        ret
.invalid:
        or a
        ret

collision_check_all_ghosts:
        ld hl, GHOST_BLINKY_BASE
        call collision_check_ghost_at_hl
        or a
        ret nz
        ld hl, GHOST_PINKY_BASE
        call collision_check_ghost_at_hl
        or a
        ret nz
        ld hl, GHOST_INKY_BASE
        call collision_check_ghost_at_hl
        or a
        ret nz
        ld hl, GHOST_CLYDE_BASE
        call collision_check_ghost_at_hl
        ret

; Input: HL = ghost record base.
; Output: A = COLLISION_GHOST_* result.
collision_check_ghost_at_hl:
        push hl
        call ghost_pacman_tile_to_bc
        pop hl
        ld a, (hl)
        cp b
        jr nz, .none
        inc hl
        ld a, (hl)
        cp c
        jr nz, .none
        inc hl
        inc hl
        ld a, (hl)
        cp GHOST_MODE_FRIGHTENED
        jr z, .eaten
        ld a, COLLISION_GHOST_PACMAN_DIES
        ld (COLLISION_LAST_GHOST_RESULT), a
        ret
.eaten:
        ld a, COLLISION_GHOST_EATEN
        ld (COLLISION_LAST_GHOST_RESULT), a
        ret
.none:
        xor a
        ld (COLLISION_LAST_GHOST_RESULT), a
        ret
