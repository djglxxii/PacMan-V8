; VDP-A sprite upload and deterministic T015 transform validation placement.
; The generated shadow include maps 8.8 arcade gameplay positions through the
; fitted V8 coordinate table before emitting Sprite Mode 2 SAT fields.

SPRITE_PATTERN_VRAM_PAGE     EQU 0x01
SPRITE_PATTERN_VRAM_OFFSET   EQU 0x3000      ; Absolute VRAM 0x7000.
SPRITE_COLOR_VRAM_PAGE       EQU 0x01
SPRITE_COLOR_VRAM_OFFSET     EQU 0x3A00      ; Absolute VRAM 0x7A00.
SPRITE_SAT_VRAM_PAGE         EQU 0x01
SPRITE_SAT_VRAM_OFFSET       EQU 0x3C00      ; Absolute VRAM 0x7C00.

SPRITE_PATTERN_BANK_BYTES    EQU 2048
SPRITE_SOURCE_COLOR_BYTES    EQU 1024
SPRITE_SLOT_COUNT            EQU 6
SPRITE_SAT_STRIDE            EQU 8
SPRITE_COLOR_STRIDE          EQU 16
SPRITE_SAT_SHADOW_BYTES      EQU SPRITE_SLOT_COUNT * SPRITE_SAT_STRIDE
SPRITE_COLOR_SHADOW_BYTES    EQU SPRITE_SLOT_COUNT * SPRITE_COLOR_STRIDE

SPRITE_PACMAN_SLOT           EQU 0
SPRITE_BLINKY_SLOT           EQU 1
SPRITE_PINKY_SLOT            EQU 2
SPRITE_INKY_SLOT             EQU 3
SPRITE_CLYDE_SLOT            EQU 4
SPRITE_RESERVED_SLOT         EQU 5

SPRITE_PACMAN_ID             EQU 1
SPRITE_BLINKY_ID             EQU 8
SPRITE_PINKY_FRIGHT_ID       EQU 50
SPRITE_INKY_HOUSE_ID         EQU 32
SPRITE_CLYDE_EXIT_ID         EQU 9

SPRITE_PACMAN_PATTERN        EQU SPRITE_PACMAN_ID * 4
SPRITE_BLINKY_PATTERN        EQU SPRITE_BLINKY_ID * 4
SPRITE_PINKY_PATTERN         EQU SPRITE_PINKY_FRIGHT_ID * 4
SPRITE_INKY_PATTERN          EQU SPRITE_INKY_HOUSE_ID * 4
SPRITE_CLYDE_PATTERN         EQU SPRITE_CLYDE_EXIT_ID * 4

SPRITE_PALETTE_TRANSPARENT   EQU 0
SPRITE_PALETTE_PACMAN        EQU 1
SPRITE_PALETTE_BLINKY        EQU 2
SPRITE_PALETTE_PINKY         EQU 3
SPRITE_PALETTE_INKY          EQU 4
SPRITE_PALETTE_CLYDE         EQU 5
SPRITE_PALETTE_FRIGHTENED    EQU 8

SPRITE_TERMINATOR_Y          EQU 0xD0

SPRITE_STATE_BASE            EQU 0x8300
SPRITE_SAT_SHADOW            EQU SPRITE_STATE_BASE
SPRITE_COLOR_SHADOW          EQU SPRITE_SAT_SHADOW + SPRITE_SAT_SHADOW_BYTES
SPRITE_FRAME_COUNTER         EQU SPRITE_COLOR_SHADOW + SPRITE_COLOR_SHADOW_BYTES

sprite_renderer_init:
        call sprite_upload_patterns
        call sprite_init_color_shadow
        call sprite_upload_color_shadow
        ret

sprite_upload_patterns:
        VDP_REG_A 14, SPRITE_PATTERN_VRAM_PAGE
        ld bc, SPRITE_PATTERN_VRAM_OFFSET
        call vdp_a_seek_write_bc
        ld hl, sprite_pattern_data
        ld de, SPRITE_PATTERN_BANK_BYTES
        call copy_vdp_a_bytes
        VDP_REG_A 14, 0x00
        ret

sprite_upload_color_shadow:
        VDP_REG_A 14, SPRITE_COLOR_VRAM_PAGE
        ld bc, SPRITE_COLOR_VRAM_OFFSET
        call vdp_a_seek_write_bc
        ld hl, SPRITE_COLOR_SHADOW
        ld de, SPRITE_COLOR_SHADOW_BYTES
        call copy_vdp_a_bytes
        VDP_REG_A 14, 0x00
        ret

sprite_upload_sat_shadow:
        VDP_REG_A 14, SPRITE_SAT_VRAM_PAGE
        ld bc, SPRITE_SAT_VRAM_OFFSET
        call vdp_a_seek_write_bc
        ld hl, SPRITE_SAT_SHADOW
        ld de, SPRITE_SAT_SHADOW_BYTES
        call copy_vdp_a_bytes
        VDP_REG_A 14, 0x00
        ret

sprite_init_color_shadow:
        ld hl, SPRITE_COLOR_SHADOW

        ld b, 16
        ld a, SPRITE_PALETTE_PACMAN
        call .fill_slot

        ld b, 16
        ld a, SPRITE_PALETTE_BLINKY
        call .fill_slot

        ld b, 16
        ld a, SPRITE_PALETTE_PINKY
        call .fill_slot

        ld b, 16
        ld a, SPRITE_PALETTE_INKY
        call .fill_slot

        ld b, 16
        ld a, SPRITE_PALETTE_CLYDE
        call .fill_slot

        xor a
        ld b, 16
        call .fill_slot

        xor a
        ld (SPRITE_FRAME_COUNTER), a
        ret

.fill_slot:
        ld (hl), a
        inc hl
        djnz .fill_slot
        ret

sprite_build_shadow:
        INCLUDE "sprite_review_shadow.inc"
        ret

vdp_a_seek_write_bc:
        ld a, c
        out (VDP_A_CTRL), a
        ld a, b
        and 0x3F
        or 0x40
        out (VDP_A_CTRL), a
        ret

copy_vdp_a_bytes:
        ld a, d
        or e
        ret z
.loop:
        ld a, (hl)
        out (VDP_A_DATA), a
        inc hl
        dec de
        ld a, d
        or e
        jr nz, .loop
        ret

sprite_pattern_data:
        INCBIN "../assets/sprites.bin"
sprite_color_data:
        INCBIN "../assets/sprite_colors.bin"
