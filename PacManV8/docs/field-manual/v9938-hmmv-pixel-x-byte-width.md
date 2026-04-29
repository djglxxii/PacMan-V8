# V9938 HMMV Pixel X With Byte Width

**Context:** T029 needed live pellet erases in the VDP-B Graphic 4 maze
framebuffer using HMMV.

**The insight:** In the Vanguard 8 emulator's V9938 HMMV path for Graphic 4,
`DX` is a pixel coordinate, while `NX` is a byte count. For an 8-pixel-wide
erase, set `DX` to the left pixel (`16 + tile_x * 8`) and `NX` to `4`.
Using a byte-coordinate `DX` lands the erase at half the intended X position.
The fitted maze also uses 6/7-pixel row heights, so erasing the fitted cell
height avoids clearing into the next row.

**Example:**

```asm
        ; Tile x -> pixel DX, not byte DX. NX remains 4 bytes for 8 pixels.
        ld a, (COLLISION_ERASE_TILE_X)
        add a, a
        add a, a
        add a, a
        add a, 16
        ld b, a

        ld a, b
        ld c, 36        ; R#36 DX low
        call vdp_b_write_reg_c
        ld a, 4
        ld c, 40        ; R#40 NX low
        call vdp_b_write_reg_c
```
