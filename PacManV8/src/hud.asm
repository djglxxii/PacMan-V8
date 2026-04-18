; VDP-A bitmap HUD renderer for T014.
; The generated patch is transparent outside HUD glyph/icon pixels and covers
; only the top and bottom 8-pixel foreground bands.

HUD_PATCH_BAND_BYTES         EQU 1024
HUD_BOTTOM_PATCH_VRAM_PAGE   EQU 0x01
HUD_BOTTOM_PATCH_VRAM_OFFSET EQU 0x2600      ; Absolute VRAM 0x6600, y=204.

    MACRO HUD_PATCH_TILE tile_index, dst_x, dst_y
        ; Review-only metadata macro consumed by the generated include.
    ENDM

hud_renderer_init:
        call hud_upload_patch
        ret

hud_upload_patch:
        VDP_REG_A 14, 0x00
        ld bc, 0x0000
        call vdp_a_seek_write_bc
        ld hl, hud_patch_data
        ld de, HUD_PATCH_BAND_BYTES
        call copy_vdp_a_bytes

        VDP_REG_A 14, HUD_BOTTOM_PATCH_VRAM_PAGE
        ld bc, HUD_BOTTOM_PATCH_VRAM_OFFSET
        call vdp_a_seek_write_bc
        ld hl, hud_patch_data + HUD_PATCH_BAND_BYTES
        ld de, HUD_PATCH_BAND_BYTES
        call copy_vdp_a_bytes

        VDP_REG_A 14, 0x00
        ret

hud_draw_review_rows:
        INCLUDE "hud_review_draw.inc"
        ret

hud_patch_data:
        INCBIN "../assets/hud_patch.bin"
