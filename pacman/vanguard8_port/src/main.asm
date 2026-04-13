        INCLUDE "vdp.inc"

FRAME_COUNTER_LO                EQU 0x8100
FRAME_COUNTER_HI                EQU 0x8101
HUD_GLYPH_SLICE_BYTES           EQU 168

        ORG 0x0000
        jp reset

        defs 0x0038 - $, 0x00

        jp int0_handler

        defs 0x0040 - $, 0x00

reset:
        di

        OUT0_A 0x3A, 0x48          ; CBAR: 0x0000-0x3FFF fixed, 0x8000-0xFFFF SRAM
        OUT0_A 0x38, 0xF0          ; CBR: SRAM physical base 0xF0000
        OUT0_A 0x39, 0x04          ; BBR: bank window physical base 0x04000

        ld sp, 0x8100

        xor a
        ld (FRAME_COUNTER_LO), a
        ld (FRAME_COUNTER_HI), a

        ; Configure both VDPs with display disabled first so setup is not visible.
        VDP_REG_B 0, 0x06          ; Graphic 4
        VDP_REG_B 1, 0x00
        VDP_REG_B 5, 0xF8          ; SAT base 0x7C00
        VDP_REG_B 6, 0x0E          ; sprite pattern base 0x7000
        VDP_REG_B 7, 0x00          ; backdrop color 0
        VDP_REG_B 8, 0x00          ; opaque background layer
        VDP_REG_B 9, 0x80          ; LN = 1
        VDP_REG_B 11, 0x00
        VDP_REG_B 23, 0x00         ; no vertical scroll

        VDP_REG_A 0, 0x04          ; Graphic 3
        VDP_REG_A 1, 0x00
        VDP_REG_A 2, 0x00          ; name table at 0x0000
        VDP_REG_A 5, 0x84          ; SAT base 0x4200
        VDP_REG_A 6, 0x06          ; sprite pattern base 0x3000
        VDP_REG_A 7, 0x00          ; backdrop color 0
        VDP_REG_A 8, 0x20          ; TP = 1 for compositing
        VDP_REG_A 9, 0x80          ; LN = 1
        VDP_REG_A 11, 0x00
        VDP_REG_A 23, 0x00         ; no vertical scroll

        ld hl, PALETTE_B_DATA
        call upload_vdp_b_palette
        ld hl, PALETTE_A_DATA
        call upload_vdp_a_palette

        ; The emulator resets VRAM to zero, so one SAT sentinel byte is enough to
        ; terminate each sprite list and keep both layers sprite-free for T002.
        call upload_vdp_a_hud_tables
        VDP_A_WRITE 0x4200, 0xD0
        VDP_B_WRITE 0x7C00, 0xD0

        call upload_vdp_b_tile_bank
        call render_static_maze

        VDP_REG_B 1, 0x40          ; display on
        VDP_REG_A 1, 0x40          ; display on with TP compositing from R#8

        im 1
        ei

main_loop:
        halt
        ld hl, (FRAME_COUNTER_LO)
        inc hl
        ld (FRAME_COUNTER_LO), hl
        jr main_loop

int0_handler:
        push af
        in a, (0x81)               ; Read S#0 to clear V-blank on VDP-A.
        pop af
        ei
        db 0xED, 0x4D

upload_vdp_a_palette:
        xor a
        out (0x82), a
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        inc hl
        ld a, (hl)
        out (0x82), a
        ret

upload_vdp_b_palette:
        xor a
        out (0x86), a
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        inc hl
        ld a, (hl)
        out (0x86), a
        ret

upload_vdp_a_hud_tables:
        ld hl, HUD_FONT_DATA

        VDP_A_WRITE_ADDRESS 0x0000
        REPT 6
        call upload_vdp_a_128_bytes
        ENDR

        VDP_A_WRITE_ADDRESS 0x0300
        call upload_vdp_a_hud_glyph_slice
        VDP_A_WRITE_ADDRESS 0x0B00
        call upload_vdp_a_hud_glyph_slice
        VDP_A_WRITE_ADDRESS 0x1300
        call upload_vdp_a_hud_glyph_slice

        VDP_A_WRITE_ADDRESS 0x1800
        call upload_vdp_a_hud_glyph_slice
        VDP_A_WRITE_ADDRESS 0x2000
        call upload_vdp_a_hud_glyph_slice
        VDP_A_WRITE_ADDRESS 0x2800
        call upload_vdp_a_hud_glyph_slice
        ret

upload_vdp_a_hud_glyph_slice:
        ld b, HUD_GLYPH_SLICE_BYTES
        call upload_vdp_a_b_bytes
        ret

upload_vdp_a_128_bytes:
        ld b, 128
        call upload_vdp_a_b_bytes
        ret

upload_vdp_a_b_bytes:
.byte:
        ld a, (hl)
        out (0x80), a
        inc hl
        dec b
        jr nz, .byte
        ret

upload_vdp_b_tile_bank:
        VDP_REG_B 14, 0x01
        ld a, 0x00
        out (0x85), a
        ld a, 0x7D
        out (0x85), a
        ld hl, TILES_VDPB_DATA
        REPT 10
        call upload_vdp_b_128_bytes
        ENDR
        ret

render_static_maze:
        VDP_REG_B 14, 0x00
        ld a, 0x00
        out (0x85), a
        ld a, 0x40
        out (0x85), a
        ld hl, TILE_NAMETABLE_DATA
        REPT 212
        call upload_vdp_b_128_bytes
        ENDR
        ret

upload_vdp_b_128_bytes:
        ld b, 128
        call upload_vdp_b_b_bytes
        ret

upload_vdp_b_b_bytes:
.byte:
        ld a, (hl)
        out (0x84), a
        inc hl
        dec b
        jr nz, .byte
        ret

wait_vdp_b_command_clear:
        VDP_REG_B 15, 0x02
.wait:
        in a, (0x85)
        and 0x01
        jr nz, .wait
        VDP_REG_B 15, 0x00
        ret

        INCLUDE "data.asm"
