; Pac-Man for Vanguard 8 -- minimal boot ROM for T001.
; Boots the HD64180, initializes both V9938 chips to Graphic 4 / 212-line
; mode, and shows the fitted Pac-Man maze framebuffer on VDP-B through
; transparent VDP-A pixels.

        ORG 0x0000

VDP_A_DATA      EQU 0x80
VDP_A_CTRL      EQU 0x81
VDP_A_PALETTE   EQU 0x82
VDP_B_DATA      EQU 0x84
VDP_B_CTRL      EQU 0x85
VDP_B_PALETTE   EQU 0x86
ROM_BANK_0      EQU 0x04
ROM_BANK_1      EQU 0x08
MAZE_FB_BANK0_SIZE EQU 0x4000
MAZE_FB_BANK1_SIZE EQU 0x2A00

    MACRO OUT0_A port, value
        ld a, value
        db 0xED, 0x39, port
    ENDM

    MACRO VDP_REG_A reg, value
        ld a, value
        out (VDP_A_CTRL), a
        ld a, 0x80 | reg
        out (VDP_A_CTRL), a
    ENDM

    MACRO VDP_REG_B reg, value
        ld a, value
        out (VDP_B_CTRL), a
        ld a, 0x80 | reg
        out (VDP_B_CTRL), a
    ENDM

    MACRO VDP_PALETTE_A index, rg, blue
        ld a, index
        out (VDP_A_PALETTE), a
        ld a, rg
        out (VDP_A_PALETTE), a
        ld a, blue
        out (VDP_A_PALETTE), a
    ENDM

    MACRO VDP_PALETTE_B index, rg, blue
        ld a, index
        out (VDP_B_PALETTE), a
        ld a, rg
        out (VDP_B_PALETTE), a
        ld a, blue
        out (VDP_B_PALETTE), a
    ENDM

    MACRO VDP_CMD_A_HMMV x, y, width_bytes, height, value
        VDP_REG_A 36, ((x) & 0xFF)
        VDP_REG_A 37, (((x) >> 8) & 0x03)
        VDP_REG_A 38, ((y) & 0xFF)
        VDP_REG_A 39, (((y) >> 8) & 0x03)
        VDP_REG_A 40, ((width_bytes) & 0xFF)
        VDP_REG_A 41, (((width_bytes) >> 8) & 0x03)
        VDP_REG_A 42, ((height) & 0xFF)
        VDP_REG_A 43, (((height) >> 8) & 0x03)
        VDP_REG_A 44, value
        VDP_REG_A 45, 0x00
        VDP_REG_A 46, 0xC0
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

entry_point:
        jp reset_entry

        defs 0x0038 - $, 0x00

im1_handler:
        push af
        push bc
        push de
        push hl
        in a, (VDP_A_CTRL)          ; Read S#0 to clear VDP-A V-blank.
        call audio_update_frame
        pop hl
        pop de
        pop bc
        pop af
        ei
        db 0xED, 0x4D              ; RETI

reset_entry:
        di
        ld sp, 0xFF00

        ; HD64180 MMU setup from the Vanguard 8 hardware contract.
        OUT0_A 0x3A, 0x48          ; CBAR: CA0 0x0000-0x3FFF, CA1 0x8000+
        OUT0_A 0x38, 0xF0          ; CBR: CA1 maps to SRAM at 0xF0000
        OUT0_A 0x39, 0x04          ; BBR: bank window maps cartridge bank 0

        im 1

        call audio_init
        call init_video

idle_loop:
        ei
        halt
        jp idle_loop

init_video:
        ; Configure both VDPs as Graphic 4 / Screen 5 with display disabled
        ; while the framebuffers are cleared.
        VDP_REG_A 0, 0x06
        VDP_REG_A 1, 0x00
        VDP_REG_A 5, 0xF8
        VDP_REG_A 6, 0x0E
        VDP_REG_A 7, 0x00
        VDP_REG_A 8, 0x20          ; TP: color 0 is transparent on VDP-A.
        VDP_REG_A 9, 0x80          ; LN: 212-line display.
        VDP_REG_A 11, 0x00
        VDP_REG_A 23, 0x00
        VDP_REG_A 15, 0x00

        VDP_REG_B 0, 0x06
        VDP_REG_B 1, 0x00
        VDP_REG_B 5, 0xF8
        VDP_REG_B 6, 0x0E
        VDP_REG_B 7, 0x00
        VDP_REG_B 8, 0x00
        VDP_REG_B 9, 0x80
        VDP_REG_B 11, 0x00
        VDP_REG_B 23, 0x00
        VDP_REG_B 15, 0x00

        ; Palette entry format: RRR0GGG then 00000BBB.
        call upload_vdp_a_palette
        call upload_vdp_b_palette

        call clear_vdp_a_framebuffer
        call load_vdp_b_maze_framebuffer
        call sprite_renderer_init
        call hud_renderer_init

        ; Enable display. VDP-A also enables V-blank IRQs to exercise the
        ; IM1 handler; VDP-B IRQ is not connected on Vanguard 8.
        VDP_REG_A 1, 0x62          ; Display + VBlank IRQ + 16x16 sprites.
        VDP_REG_B 1, 0x40
        ret

clear_vdp_a_framebuffer:
        VDP_REG_A 14, 0x00
        ld bc, 0x0000
        call vdp_a_seek_write_bc
        ld de, MAZE_FB_BANK0_SIZE
        call fill_vdp_a_zeroes

        VDP_REG_A 14, 0x01
        ld bc, 0x0000
        call vdp_a_seek_write_bc
        ld de, MAZE_FB_BANK1_SIZE
        call fill_vdp_a_zeroes

        VDP_REG_A 14, 0x00
        ret

clear_vdp_b_framebuffer:
        VDP_CMD_B_HMMV 0, 0, 128, 212, 0x00
        ret

upload_vdp_b_palette:
        ld a, 0x00
        out (VDP_B_PALETTE), a
        ld hl, vdp_b_palette_data
        ld b, 32
.loop:
        ld a, (hl)
        out (VDP_B_PALETTE), a
        inc hl
        dec b
        jr nz, .loop
        ret

upload_vdp_a_palette:
        ld a, 0x00
        out (VDP_A_PALETTE), a
        ld hl, vdp_a_palette_data
        ld b, 32
.loop:
        ld a, (hl)
        out (VDP_A_PALETTE), a
        inc hl
        dec b
        jr nz, .loop
        ret

load_vdp_b_maze_framebuffer:
        ; The 27,136-byte Graphic 4 framebuffer spans two cartridge banks.
        ; Execute this routine from common ROM and read each bank at 0x4000.
        VDP_REG_B 14, 0x00
        ld bc, 0x0000
        call vdp_b_seek_write_bc
        OUT0_A 0x39, ROM_BANK_0
        ld hl, 0x4000
        ld de, MAZE_FB_BANK0_SIZE
        call copy_vdp_b_bytes

        VDP_REG_B 14, 0x01
        ld bc, 0x0000
        call vdp_b_seek_write_bc
        OUT0_A 0x39, ROM_BANK_1
        ld hl, 0x4000
        ld de, MAZE_FB_BANK1_SIZE
        call copy_vdp_b_bytes

        OUT0_A 0x39, ROM_BANK_0
        VDP_REG_B 14, 0x00
        ret

vdp_b_seek_write_bc:
        ld a, c
        out (VDP_B_CTRL), a
        ld a, b
        and 0x3F
        or 0x40
        out (VDP_B_CTRL), a
        ret

copy_vdp_b_bytes:
        ld a, d
        or e
        ret z
.loop:
        ld a, (hl)
        out (VDP_B_DATA), a
        inc hl
        dec de
        ld a, d
        or e
        jr nz, .loop
        ret

fill_vdp_a_zeroes:
        ld a, d
        or e
        ret z
.loop:
        xor a
        out (VDP_A_DATA), a
        dec de
        ld a, d
        or e
        jr nz, .loop
        ret

        INCLUDE "movement.asm"
        INCLUDE "ghost_ai.asm"
        INCLUDE "collision.asm"
        INCLUDE "ghost_house.asm"
        INCLUDE "sprites.asm"
        INCLUDE "hud.asm"
        INCLUDE "audio.asm"

vdp_a_palette_data:
        INCBIN "../assets/palette_a.bin"
vdp_b_palette_data:
        INCBIN "../assets/palette_b.bin"

        defs 0x4000 - $, 0xFF

; Bank 0 page, mapped at logical 0x4000 when BBR=0x04.
        ORG 0x4000
maze_framebuffer_bank0:
        INCBIN "../assets/maze_v8_framebuffer.bin", 0, MAZE_FB_BANK0_SIZE

        defs 0x8000 - $, 0x00

; Bank 1 page, mapped at logical 0x4000 when BBR=0x08.
        ORG 0x8000
maze_framebuffer_bank1:
        INCBIN "../assets/maze_v8_framebuffer.bin", MAZE_FB_BANK0_SIZE, MAZE_FB_BANK1_SIZE
