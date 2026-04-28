; Arcade-coordinate Pac-Man movement slice for T008.
; Coordinates are 8.8 fixed-point arcade pixels; tile centers are
; (tile * 8 + 4) << 8. This file is assembled into the ROM now, while later
; tasks will wire it into input, rendering, pellet, and ghost systems.

MOVEMENT_DIR_UP         EQU 0
MOVEMENT_DIR_LEFT       EQU 1
MOVEMENT_DIR_DOWN       EQU 2
MOVEMENT_DIR_RIGHT      EQU 3
MOVEMENT_DIR_NONE       EQU 4

MOVEMENT_TILE_SIZE      EQU 8
MOVEMENT_TILE_CENTER    EQU 4
MOVEMENT_MAZE_WIDTH     EQU 28
MOVEMENT_MAZE_HEIGHT    EQU 36
MOVEMENT_MAZE_WIDTH_PX  EQU 224
MOVEMENT_SPEED_FP       EQU 0x0100
MOVEMENT_TURN_WINDOW_PX EQU 4

SEMANTIC_PATH           EQU 1
SEMANTIC_PELLET         EQU 2
SEMANTIC_ENERGIZER      EQU 3
SEMANTIC_TUNNEL         EQU 6

MOVEMENT_STATE_BASE     EQU 0x8100
PACMAN_X_FP             EQU MOVEMENT_STATE_BASE + 0
PACMAN_Y_FP             EQU MOVEMENT_STATE_BASE + 2
PACMAN_CURRENT_DIR      EQU MOVEMENT_STATE_BASE + 4
PACMAN_REQUESTED_DIR    EQU MOVEMENT_STATE_BASE + 5
PACMAN_MOVE_FLAGS       EQU MOVEMENT_STATE_BASE + 6

PACMAN_START_X_FP       EQU 0x7400      ; tile 14 center: (14*8+4)<<8
PACMAN_START_Y_FP       EQU 0xD400      ; tile 26 center: (26*8+4)<<8

movement_init_pacman:
        ld hl, PACMAN_START_X_FP
        ld (PACMAN_X_FP), hl
        ld hl, PACMAN_START_Y_FP
        ld (PACMAN_Y_FP), hl
        ld a, MOVEMENT_DIR_LEFT
        ld (PACMAN_CURRENT_DIR), a
        ld (PACMAN_REQUESTED_DIR), a
        xor a
        ld (PACMAN_MOVE_FLAGS), a
        ret

; Input: A = requested direction enum.
; Output: carry set when the request was accepted into the turn buffer.
movement_request_direction:
        cp MOVEMENT_DIR_NONE
        jr nz, .non_none
        ld (PACMAN_REQUESTED_DIR), a
        scf
        ret

.non_none:
        ld b, a
        ld a, (PACMAN_CURRENT_DIR)
        cp MOVEMENT_DIR_NONE
        jr z, .accept

        ; Reversals are always bufferable for Pac-Man.
        cp MOVEMENT_DIR_UP
        jr nz, .not_up
        ld a, b
        cp MOVEMENT_DIR_DOWN
        jr z, .accept
.not_up:
        ld a, (PACMAN_CURRENT_DIR)
        cp MOVEMENT_DIR_DOWN
        jr nz, .not_down
        ld a, b
        cp MOVEMENT_DIR_UP
        jr z, .accept
.not_down:
        ld a, (PACMAN_CURRENT_DIR)
        cp MOVEMENT_DIR_LEFT
        jr nz, .not_left
        ld a, b
        cp MOVEMENT_DIR_RIGHT
        jr z, .accept
.not_left:
        ld a, (PACMAN_CURRENT_DIR)
        cp MOVEMENT_DIR_RIGHT
        jr nz, .window_check
        ld a, b
        cp MOVEMENT_DIR_LEFT
        jr z, .accept

.window_check:
        push bc                         ; preserve direction in B
        call movement_distance_to_next_center_px
        pop bc                          ; restore direction in B; A still holds distance
        cp MOVEMENT_TURN_WINDOW_PX + 1
        jr c, .accept
        or a
        ret

.accept:
        ld a, b
        ld (PACMAN_REQUESTED_DIR), a
        scf
        ret

movement_update_pacman:
        call movement_try_turn_at_center
        call movement_current_direction_passable
        or a
        jr nz, .move
        call movement_snap_to_center_on_current_axis
        ld a, MOVEMENT_DIR_NONE
        ld (PACMAN_CURRENT_DIR), a
        ret
.move:
        call movement_move_one_pixel
        call movement_apply_tunnel_wrap
        ret

movement_snap_to_center_on_current_axis:
        ld a, (PACMAN_CURRENT_DIR)
        cp MOVEMENT_DIR_LEFT
        jr z, .snap_x
        cp MOVEMENT_DIR_RIGHT
        jr z, .snap_x
        cp MOVEMENT_DIR_UP
        jr z, .snap_y
        cp MOVEMENT_DIR_DOWN
        jr z, .snap_y
        ret
.snap_x:
        xor a
        ld (PACMAN_X_FP), a
        ld a, (PACMAN_X_FP + 1)
        and 0xF8
        or 4
        ld (PACMAN_X_FP + 1), a
        ret
.snap_y:
        xor a
        ld (PACMAN_Y_FP), a
        ld a, (PACMAN_Y_FP + 1)
        and 0xF8
        or 4
        ld (PACMAN_Y_FP + 1), a
        ret

movement_try_turn_at_center:
        ld a, (PACMAN_REQUESTED_DIR)
        cp MOVEMENT_DIR_NONE
        ret z
        call movement_is_at_center
        or a
        ret z
        ld a, (PACMAN_REQUESTED_DIR)
        ld b, a
        push bc
        call movement_direction_passable_from_current_tile
        pop bc
        or a
        ret z
        ld a, b
        ld (PACMAN_CURRENT_DIR), a
        ret

movement_current_direction_passable:
        ld a, (PACMAN_CURRENT_DIR)
        ld b, a
        call movement_direction_passable_from_current_tile
        ret

; Input: B = direction enum.
; Output: A = 1 if the neighbor cell from Pac-Man's current tile is passable,
;         A = 0 otherwise.
movement_direction_passable_from_current_tile:
        ld a, b
        cp MOVEMENT_DIR_NONE
        jr z, .blocked

        ld a, (PACMAN_X_FP + 1)
        srl a
        srl a
        srl a
        ld d, a                         ; D = tile x
        ld a, (PACMAN_Y_FP + 1)
        srl a
        srl a
        srl a
        ld e, a                         ; E = tile y

        ld a, b
        cp MOVEMENT_DIR_LEFT
        jr nz, .not_left
        ld a, d
        or a
        jr nz, .left_no_wrap
        ld d, MOVEMENT_MAZE_WIDTH - 1
        jr .check_cell
.left_no_wrap:
        dec d
        jr .check_cell

.not_left:
        cp MOVEMENT_DIR_RIGHT
        jr nz, .not_right
        ld a, d
        cp MOVEMENT_MAZE_WIDTH - 1
        jr nz, .right_no_wrap
        ld d, 0
        jr .check_cell
.right_no_wrap:
        inc d
        jr .check_cell

.not_right:
        cp MOVEMENT_DIR_UP
        jr nz, .not_up
        ld a, e
        or a
        jr z, .blocked
        dec e
        jr .check_cell

.not_up:
        cp MOVEMENT_DIR_DOWN
        jr nz, .blocked
        ld a, e
        cp MOVEMENT_MAZE_HEIGHT - 1
        jr z, .blocked
        inc e

.check_cell:
        ld b, d
        ld c, e
        call movement_cell_passable
        ret

.blocked:
        xor a
        ret

; Input: B = tile x, C = tile y.
; Output: A = 1 for Pac-Man-passable semantic classes, A = 0 otherwise.
movement_cell_passable:
        ld a, c
        cp MOVEMENT_MAZE_HEIGHT
        jr nc, .blocked
        ld a, b
        cp MOVEMENT_MAZE_WIDTH
        jr nc, .blocked

        ld h, 0
        ld l, c
        add hl, hl
        ld de, movement_row_offsets
        add hl, de
        ld e, (hl)
        inc hl
        ld d, (hl)
        ex de, hl
        ld e, b
        ld d, 0
        add hl, de
        ld de, movement_maze_semantic
        add hl, de
        ld a, (hl)

        cp SEMANTIC_PATH
        jr z, .passable
        cp SEMANTIC_PELLET
        jr z, .passable
        cp SEMANTIC_ENERGIZER
        jr z, .passable
        cp SEMANTIC_TUNNEL
        jr z, .passable
.blocked:
        xor a
        ret
.passable:
        ld a, 1
        ret

movement_is_at_center:
        ld a, (PACMAN_X_FP)
        or a
        ret nz
        ld a, (PACMAN_X_FP + 1)
        and 0x07
        cp MOVEMENT_TILE_CENTER
        jr nz, .not_center
        ld a, (PACMAN_Y_FP)
        or a
        ret nz
        ld a, (PACMAN_Y_FP + 1)
        and 0x07
        cp MOVEMENT_TILE_CENTER
        jr nz, .not_center
        ld a, 1
        ret
.not_center:
        xor a
        ret

; Output: A = integer pixel distance to the next tile center on the current
; movement axis. Used by movement_request_direction for the 4-pixel window.
movement_distance_to_next_center_px:
        ld a, (PACMAN_CURRENT_DIR)
        cp MOVEMENT_DIR_LEFT
        jr z, .horizontal_left
        cp MOVEMENT_DIR_RIGHT
        jr z, .horizontal_right
        cp MOVEMENT_DIR_UP
        jr z, .vertical_up
        cp MOVEMENT_DIR_DOWN
        jr z, .vertical_down
        xor a
        ret

.horizontal_right:
        ld a, (PACMAN_X_FP + 1)
        and 0x07
        cp MOVEMENT_TILE_CENTER + 1
        jr c, .positive_before_center
        ld b, a
        ld a, 12
        sub b
        ret
.vertical_down:
        ld a, (PACMAN_Y_FP + 1)
        and 0x07
        cp MOVEMENT_TILE_CENTER + 1
        jr c, .positive_before_center
        ld b, a
        ld a, 12
        sub b
        ret
.positive_before_center:
        ld b, a
        ld a, MOVEMENT_TILE_CENTER
        sub b
        ret

.horizontal_left:
        ld a, (PACMAN_X_FP + 1)
        and 0x07
        cp MOVEMENT_TILE_CENTER
        jr nc, .negative_after_center
        add a, MOVEMENT_TILE_CENTER
        ret
.vertical_up:
        ld a, (PACMAN_Y_FP + 1)
        and 0x07
        cp MOVEMENT_TILE_CENTER
        jr nc, .negative_after_center
        add a, MOVEMENT_TILE_CENTER
        ret
.negative_after_center:
        sub MOVEMENT_TILE_CENTER
        ret

movement_move_one_pixel:
        ld a, (PACMAN_CURRENT_DIR)
        cp MOVEMENT_DIR_LEFT
        jr z, .left
        cp MOVEMENT_DIR_RIGHT
        jr z, .right
        cp MOVEMENT_DIR_UP
        jr z, .up
        cp MOVEMENT_DIR_DOWN
        jr z, .down
        ret
.left:
        ld hl, PACMAN_X_FP + 1
        dec (hl)
        ret
.right:
        ld hl, PACMAN_X_FP + 1
        inc (hl)
        ret
.up:
        ld hl, PACMAN_Y_FP + 1
        dec (hl)
        ret
.down:
        ld hl, PACMAN_Y_FP + 1
        inc (hl)
        ret

movement_apply_tunnel_wrap:
        ld a, (PACMAN_X_FP + 1)
        cp 240
        jr nc, .underflow
        cp MOVEMENT_MAZE_WIDTH_PX
        ret c
        sub MOVEMENT_MAZE_WIDTH_PX
        ld (PACMAN_X_FP + 1), a
        ret
.underflow:
        add a, MOVEMENT_MAZE_WIDTH_PX
        ld (PACMAN_X_FP + 1), a
        ret

movement_row_offsets:
        dw 0, 28, 56, 84, 112, 140, 168, 196
        dw 224, 252, 280, 308, 336, 364, 392, 420
        dw 448, 476, 504, 532, 560, 588, 616, 644
        dw 672, 700, 728, 756, 784, 812, 840, 868
        dw 896, 924, 952, 980

movement_maze_semantic:
        INCBIN "../assets/maze_semantic.bin"
