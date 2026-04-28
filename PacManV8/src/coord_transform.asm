; Runtime arcade 8.8 pixel coordinate to V8 Sprite Mode 2 SAT coordinate.
; Input:  HL = arcade Y 8.8, DE = arcade X 8.8.
; Output: H = SAT Y byte, L = SAT X byte.
; Clobbers: AF, BC, DE.

COORD_LUT_X_BYTES              EQU 224
COORD_LUT_Y_BASE_OFFSET        EQU COORD_LUT_X_BYTES
COORD_LUT_Y_THRESHOLD_OFFSET   EQU COORD_LUT_Y_BASE_OFFSET + 256
COORD_LUT_BYTES                EQU COORD_LUT_Y_THRESHOLD_OFFSET + 256
COORD_X_WRAP_HIGH              EQU 0xE0

coord_arcade_to_v8:
        push hl

        ld a, d
        cp COORD_X_WRAP_HIGH
        jr c, .x_index_ready
        sub COORD_X_WRAP_HIGH
.x_index_ready:
        ld l, a
        ld h, 0
        ld bc, coord_lut_x
        add hl, bc
        ld b, (hl)                 ; B = SAT X.

        pop de                     ; D = Y integer byte, E = Y fraction byte.
        push bc                    ; Preserve SAT X while BC addresses Y tables.

        ld l, d
        ld h, 0
        ld bc, coord_lut_y_base
        add hl, bc
        ld a, (hl)                 ; A = SAT Y base for fraction 0.

        ld l, d
        ld d, a                    ; D = SAT Y base; E remains Y fraction.
        ld h, 0
        ld bc, coord_lut_y_threshold
        add hl, bc
        ld a, (hl)
        or a
        jr z, .y_ready
        ld h, a
        ld a, e
        cp h
        jr c, .y_ready
        inc d

.y_ready:
        pop bc
        ld h, d
        ld l, b
        ret

coord_lut_x:
        INCBIN "../assets/coord_lut.bin", 0, COORD_LUT_X_BYTES
coord_lut_y_base:
        INCBIN "../assets/coord_lut.bin", COORD_LUT_Y_BASE_OFFSET, 256
coord_lut_y_threshold:
        INCBIN "../assets/coord_lut.bin", COORD_LUT_Y_THRESHOLD_OFFSET, 256
