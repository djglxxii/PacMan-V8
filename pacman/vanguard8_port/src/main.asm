        INCLUDE "vdp.inc"

FRAME_COUNTER_LO                EQU 0x8100
FRAME_COUNTER_HI                EQU 0x8101

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
        VDP_REG_B 8, 0x20          ; TP = 1
        VDP_REG_B 9, 0x80          ; LN = 1
        VDP_REG_B 11, 0x00

        VDP_REG_A 0, 0x04          ; Graphic 3
        VDP_REG_A 1, 0x00
        VDP_REG_A 2, 0x00          ; name table at 0x0000
        VDP_REG_A 5, 0x84          ; SAT base 0x4200
        VDP_REG_A 6, 0x06          ; sprite pattern base 0x3000
        VDP_REG_A 7, 0x00          ; backdrop color 0
        VDP_REG_A 8, 0x20          ; TP = 1 for compositing
        VDP_REG_A 9, 0x80          ; LN = 1
        VDP_REG_A 11, 0x00

        ; Palette writes use one initial index byte and then stream entry data.
        ld a, 0x00
        out (0x86), a
        ld a, 0x00
        out (0x86), a
        ld a, 0x03
        out (0x86), a
        ld a, 0x01
        out (0x86), a
        ld a, 0x00
        out (0x86), a
        ld a, 0x02
        out (0x86), a
        ld a, 0x01
        out (0x86), a
        ld a, 0x03
        out (0x86), a
        ld a, 0x02
        out (0x86), a
        ld a, 0x04
        out (0x86), a
        ld a, 0x03
        out (0x86), a
        ld a, 0x05
        out (0x86), a
        ld a, 0x04
        out (0x86), a
        ld a, 0x06
        out (0x86), a
        ld a, 0x05
        out (0x86), a
        ld a, 0x07
        out (0x86), a
        ld a, 0x06
        out (0x86), a
        ld a, 0x10
        out (0x86), a
        ld a, 0x07
        out (0x86), a
        ld a, 0x21
        out (0x86), a
        ld a, 0x06
        out (0x86), a
        ld a, 0x32
        out (0x86), a
        ld a, 0x05
        out (0x86), a
        ld a, 0x43
        out (0x86), a
        ld a, 0x04
        out (0x86), a
        ld a, 0x54
        out (0x86), a
        ld a, 0x03
        out (0x86), a
        ld a, 0x65
        out (0x86), a
        ld a, 0x02
        out (0x86), a
        ld a, 0x76
        out (0x86), a
        ld a, 0x01
        out (0x86), a
        ld a, 0x77
        out (0x86), a
        ld a, 0x07
        out (0x86), a

        ld a, 0x00
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x70
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x07
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x07
        out (0x82), a
        ld a, 0x77
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x70
        out (0x82), a
        ld a, 0x07
        out (0x82), a
        ld a, 0x07
        out (0x82), a
        ld a, 0x07
        out (0x82), a
        ld a, 0x33
        out (0x82), a
        ld a, 0x03
        out (0x82), a
        ld a, 0x55
        out (0x82), a
        ld a, 0x05
        out (0x82), a
        ld a, 0x27
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x72
        out (0x82), a
        ld a, 0x00
        out (0x82), a
        ld a, 0x22
        out (0x82), a
        ld a, 0x07
        out (0x82), a
        ld a, 0x44
        out (0x82), a
        ld a, 0x01
        out (0x82), a
        ld a, 0x14
        out (0x82), a
        ld a, 0x05
        out (0x82), a
        ld a, 0x63
        out (0x82), a
        ld a, 0x01
        out (0x82), a
        ld a, 0x36
        out (0x82), a
        ld a, 0x06
        out (0x82), a

        ; The emulator resets VRAM to zero, so one SAT sentinel byte is enough to
        ; terminate each sprite list and keep both layers sprite-free for T002.
        VDP_A_WRITE 0x0000, 0x00
        VDP_A_WRITE 0x0300, 0x00
        VDP_A_WRITE 0x1800, 0x00
        VDP_A_WRITE 0x4200, 0xD0
        VDP_B_WRITE 0x7C00, 0xD0

        call wait_vdp_b_command_clear
        VDP_CMD_B_HMMV 0, 0, 128, 212, 0x00
        call wait_vdp_b_command_clear

        VDP_REG_B 1, 0x40          ; display on
        VDP_REG_A 1, 0x60          ; display on + V-blank IRQ

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

wait_vdp_b_command_clear:
        VDP_REG_B 15, 0x02
.wait:
        in a, (0x85)
        and 0x01
        jr nz, .wait
        VDP_REG_B 15, 0x00
        ret

        INCLUDE "data.asm"
