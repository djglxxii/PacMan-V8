# VDP-A HUD Command Engine Fallback

**Context:** T014 HUD rendering needed deterministic top and bottom HUD rows
on the transparent VDP-A foreground plane.

**The insight:** In the current Vanguard 8 emulator, the VDP-A command engine
path was not reliable enough for HUD acceptance evidence. Polling S#2.CE before
the first HUD HMMM could remain stuck, and issuing HMMM commands without polling
did not produce visible HUD pixels in the captured frame. A generated CPU VRAM
patch for the top and bottom 8-pixel bands is a reliable review fallback: it
keeps color 0 transparent, preserves per-glyph placement metadata, and can be
replaced later by narrower HMMM updates without changing the HUD content. Use
the same CPU VRAM write path for the VDP-A framebuffer clear when validating
this fallback, so stale command-engine state cannot block the first HUD upload.

**Example:**

```asm
HUD_PATCH_BAND_BYTES         EQU 1024
HUD_BOTTOM_PATCH_VRAM_PAGE   EQU 0x01
HUD_BOTTOM_PATCH_VRAM_OFFSET EQU 0x2600      ; Absolute VRAM 0x6600, y=204.

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
```
