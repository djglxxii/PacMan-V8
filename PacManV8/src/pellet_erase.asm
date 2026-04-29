; VDP-B framebuffer erase for consumed pellets/energizers (T029).
; Consumes the one-entry collision erase queue and fills the fitted maze cell
; with color 0 using the Graphic 4 byte-mode HMMV command.

PELLET_ERASE_MAZE_TOP        EQU 3
PELLET_ERASE_X_ORIGIN        EQU 16
PELLET_ERASE_WIDTH_BYTES     EQU 4       ; 8 pixels in Graphic 4.

pellet_erase_commit:
        ld a, (COLLISION_ERASE_PENDING)
        or a
        ret z

        ld a, (COLLISION_ERASE_TILE_Y)
        cp PELLET_ERASE_MAZE_TOP
        jr c, .clear_queue
        sub PELLET_ERASE_MAZE_TOP
        cp PELLET_ERASE_ROW_COUNT
        jr nc, .clear_queue

        ld l, a
        ld h, 0
        ld de, pellet_erase_row_y
        add hl, de
        ld b, (hl)                       ; B = destination Y.

        ld l, a
        ld h, 0
        ld de, pellet_erase_row_height
        add hl, de
        ld e, (hl)                       ; E = fitted cell height.
        ld d, b                          ; D = destination Y.

        ld a, (COLLISION_ERASE_TILE_X)
        cp MOVEMENT_MAZE_WIDTH
        jr nc, .clear_queue
        add a, a
        add a, a
        add a, a
        add a, PELLET_ERASE_X_ORIGIN
        ld b, a                          ; B = destination pixel X.

        ld a, b
        ld c, 36
        call vdp_b_write_reg_c
        xor a
        ld c, 37
        call vdp_b_write_reg_c

        ld a, d
        ld c, 38
        call vdp_b_write_reg_c
        xor a
        ld c, 39
        call vdp_b_write_reg_c

        ld a, PELLET_ERASE_WIDTH_BYTES
        ld c, 40
        call vdp_b_write_reg_c
        xor a
        ld c, 41
        call vdp_b_write_reg_c

        ld a, e
        ld c, 42
        call vdp_b_write_reg_c
        xor a
        ld c, 43
        call vdp_b_write_reg_c

        xor a
        ld c, 44
        call vdp_b_write_reg_c
        xor a
        ld c, 45
        call vdp_b_write_reg_c
        ld a, 0xC0
        ld c, 46
        call vdp_b_write_reg_c

.clear_queue:
        jp collision_clear_erase_queue

; Input: A = value, C = VDP register index.
vdp_b_write_reg_c:
        out (VDP_B_CTRL), a
        ld a, c
        or 0x80
        out (VDP_B_CTRL), a
        ret

pellet_erase_row_y:
        db 8,14,20,26,33,39,45,52,58,64,71,77,83,90,96,102
        db 109,115,121,128,134,140,147,153,159,166,172,178,185,191,197
PELLET_ERASE_ROW_COUNT EQU $ - pellet_erase_row_y

pellet_erase_row_height:
        db 6,6,6,7,6,6,7,6,6,7,6,6,7,6,6,7
        db 6,6,7,6,6,7,6,6,7,6,6,7,6,6,7
