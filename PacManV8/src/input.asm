; Shared controller input module for T024.
; Maps the Vanguard 8 controller port to Pac-Man movement directions.
; Active-low D-pad bits: bit 7 up, bit 5 left, bit 6 down, bit 4 right.

; Reads controller port 0x00 and returns the corresponding MOVEMENT_DIR_*
; constant in A (MOVEMENT_DIR_NONE when no direction is pressed).
input_read_controller_0_to_dir:
        in a, (0x00)
        bit 7, a
        jr z, .up
        bit 5, a
        jr z, .left
        bit 6, a
        jr z, .down
        bit 4, a
        jr z, .right
        ld a, MOVEMENT_DIR_NONE
        ret
.up:
        ld a, MOVEMENT_DIR_UP
        ret
.left:
        ld a, MOVEMENT_DIR_LEFT
        ret
.down:
        ld a, MOVEMENT_DIR_DOWN
        ret
.right:
        ld a, MOVEMENT_DIR_RIGHT
        ret
