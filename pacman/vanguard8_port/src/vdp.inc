; Shared Vanguard 8 VDP helper macros.
; Register and palette macros are adapted from the Vanguard 8 showcase ROM:
; /home/djglxxii/src/Vanguard8/showcase/src/showcase.asm

    MACRO OUT0_A port, value
        ld a, value
        db 0xED, 0x39, port
    ENDM

    MACRO VDP_REG_A reg, value
        ld a, value
        out (0x81), a
        ld a, 0x80 | reg
        out (0x81), a
    ENDM

    MACRO VDP_REG_B reg, value
        ld a, value
        out (0x85), a
        ld a, 0x80 | reg
        out (0x85), a
    ENDM

    MACRO VDP_PALETTE_A index, rg, blue
        ld a, index
        out (0x82), a
        ld a, rg
        out (0x82), a
        ld a, blue
        out (0x82), a
    ENDM

    MACRO VDP_PALETTE_B index, rg, blue
        ld a, index
        out (0x86), a
        ld a, rg
        out (0x86), a
        ld a, blue
        out (0x86), a
    ENDM

    MACRO VDP_A_WRITE address, value
        VDP_REG_A 14, 0 + (((address) >> 14) & 0x03)
        ld a, (address) & 0xFF
        out (0x81), a
        ld a, 0x40 | (((address) >> 8) & 0x3F)
        out (0x81), a
        ld a, value
        out (0x80), a
    ENDM

    MACRO VDP_A_WRITE_ADDRESS address
        VDP_REG_A 14, 0 + (((address) >> 14) & 0x03)
        ld a, (address) & 0xFF
        out (0x81), a
        ld a, 0x40 | (((address) >> 8) & 0x3F)
        out (0x81), a
    ENDM

    MACRO VDP_B_WRITE address, value
        VDP_REG_B 14, 0 + (((address) >> 14) & 0x03)
        ld a, (address) & 0xFF
        out (0x85), a
        ld a, 0x40 | (((address) >> 8) & 0x3F)
        out (0x85), a
        ld a, value
        out (0x84), a
    ENDM

    MACRO VDP_CMD_B_HMMV x, y, width_bytes, height, value
        VDP_REG_B 36, ((x) & 0xFF)
        VDP_REG_B 37, (((x) >> 8) & 0x03)
        VDP_REG_B 38, ((y) & 0xFF)
        VDP_REG_B 39, (((y) >> 8) & 0x03)
        VDP_REG_B 40, ((width_bytes) & 0xFF)
        VDP_REG_B 41, (((width_bytes) >> 8) & 0x03)
        VDP_REG_B 42, ((height) & 0xFF)
        VDP_REG_B 43, (((height) >> 8) & 0x03)
        VDP_REG_B 44, value
        VDP_REG_B 45, 0x00
        VDP_REG_B 46, 0xC0
    ENDM
