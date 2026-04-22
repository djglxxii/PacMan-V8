; T020 intermission cutscene owner.
; Scene beats are re-authored for the 256x212 Vanguard 8 presentation from
; public Pac-Man intermission descriptions, not from arcade program ROM code.

INTERMISSION_SCENE_NONE        EQU 0
INTERMISSION_SCENE_TABLES_TURN EQU 1
INTERMISSION_SCENE_NAIL_TEAR   EQU 2
INTERMISSION_SCENE_PATCH_DRAG  EQU 3

INTERMISSION_GROUP_CHASE       EQU 0
INTERMISSION_GROUP_GAG         EQU 1
INTERMISSION_GROUP_EXIT        EQU 2
INTERMISSION_GROUP_UNDRAWN     EQU 0xFF

INTERMISSION_TRIGGER_LEVEL_1   EQU 2
INTERMISSION_TRIGGER_LEVEL_2   EQU 5
INTERMISSION_TRIGGER_LEVEL_3   EQU 9

INTERMISSION_SCENE_DURATION    EQU 180
INTERMISSION_GROUP_1_FRAME     EQU 60
INTERMISSION_GROUP_2_FRAME     EQU 120
INTERMISSION_REVIEW_LAST_INDEX EQU 2

INTERMISSION_PANEL_FILL_SCENE_1 EQU 0x22
INTERMISSION_PANEL_FILL_SCENE_2 EQU 0x44
INTERMISSION_PANEL_FILL_SCENE_3 EQU 0x66
INTERMISSION_CLEAR_FILL        EQU 0x00
INTERMISSION_NAIL_FILL         EQU 0x66
INTERMISSION_TEAR_FILL         EQU 0x11
INTERMISSION_CLOTH_FILL        EQU 0x22

INTERMISSION_STATE_BASE        EQU 0x8270
INTERMISSION_CURRENT_SCENE     EQU INTERMISSION_STATE_BASE + 0
INTERMISSION_FRAME_COUNTER     EQU INTERMISSION_STATE_BASE + 1
INTERMISSION_COMPLETE_FLAG     EQU INTERMISSION_STATE_BASE + 3
INTERMISSION_CURRENT_GROUP     EQU INTERMISSION_STATE_BASE + 4
INTERMISSION_CUE_REQUESTED     EQU INTERMISSION_STATE_BASE + 5
INTERMISSION_NEXT_STATE        EQU INTERMISSION_STATE_BASE + 6
INTERMISSION_REVIEW_INDEX      EQU INTERMISSION_STATE_BASE + 7

INTERMISSION_PACMAN_PATTERN    EQU SPRITE_PACMAN_ID * 4
INTERMISSION_BLINKY_PATTERN    EQU SPRITE_BLINKY_ID * 4
INTERMISSION_FRIGHT_PATTERN    EQU SPRITE_PINKY_FRIGHT_ID * 4
INTERMISSION_EYES_PATTERN      EQU 49 * 4

    MACRO INTERMISSION_SPRITE slot, y, x, pattern, palette
        ld a, y
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 0), a
        ld a, x
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 1), a
        ld a, pattern
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 2), a
        ld a, palette
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 3), a
        xor a
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 4), a
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 5), a
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 6), a
        ld (SPRITE_SAT_SHADOW + (slot * SPRITE_SAT_STRIDE) + 7), a
    ENDM

intermission_select_review_level_for_game_flow:
        ld a, (INTERMISSION_REVIEW_INDEX)
        cp 1
        jr z, .level_5
        cp 2
        jr z, .level_9
        ld hl, INTERMISSION_TRIGGER_LEVEL_1
        jp level_progression_set_current_level
.level_5:
        ld hl, INTERMISSION_TRIGGER_LEVEL_2
        jp level_progression_set_current_level
.level_9:
        ld hl, INTERMISSION_TRIGGER_LEVEL_3
        jp level_progression_set_current_level

intermission_start:
        xor a
        ld (INTERMISSION_FRAME_COUNTER), a
        ld (INTERMISSION_FRAME_COUNTER + 1), a
        ld (INTERMISSION_COMPLETE_FLAG), a
        ld a, INTERMISSION_GROUP_UNDRAWN
        ld (INTERMISSION_CURRENT_GROUP), a
        ld a, GAME_FLOW_STATE_READY
        ld (INTERMISSION_NEXT_STATE), a

        call intermission_select_scene_from_completed_level
        ld (INTERMISSION_CURRENT_SCENE), a

        ld a, 1
        ld (INTERMISSION_CUE_REQUESTED), a
        call audio_trigger_intermission_music

        xor a
        ld (INTERMISSION_CURRENT_GROUP), a
        jp intermission_draw_current_group

intermission_select_scene_from_completed_level:
        ld hl, (LEVEL_COMPLETED_NUMBER)
        ld a, h
        or a
        jr nz, .none
        ld a, l
        cp INTERMISSION_TRIGGER_LEVEL_1
        jr z, .scene_1
        cp INTERMISSION_TRIGGER_LEVEL_2
        jr z, .scene_2
        cp INTERMISSION_TRIGGER_LEVEL_3
        jr z, .scene_3
.none:
        ld a, INTERMISSION_SCENE_NONE
        ret
.scene_1:
        ld a, INTERMISSION_SCENE_TABLES_TURN
        ret
.scene_2:
        ld a, INTERMISSION_SCENE_NAIL_TEAR
        ret
.scene_3:
        ld a, INTERMISSION_SCENE_PATCH_DRAG
        ret

intermission_update_frame:
        ld a, (INTERMISSION_COMPLETE_FLAG)
        or a
        ret nz

        ld hl, (INTERMISSION_FRAME_COUNTER)
        inc hl
        ld (INTERMISSION_FRAME_COUNTER), hl
        ld a, h
        or a
        jr nz, .complete
        ld a, l
        cp INTERMISSION_SCENE_DURATION
        jr nc, .complete
        cp INTERMISSION_GROUP_1_FRAME
        jr c, .group_0
        cp INTERMISSION_GROUP_2_FRAME
        jr c, .group_1
        ld b, INTERMISSION_GROUP_EXIT
        jr .maybe_draw
.group_0:
        ld b, INTERMISSION_GROUP_CHASE
        jr .maybe_draw
.group_1:
        ld b, INTERMISSION_GROUP_GAG
.maybe_draw:
        ld a, (INTERMISSION_CURRENT_GROUP)
        cp b
        ret z
        ld a, b
        ld (INTERMISSION_CURRENT_GROUP), a
        jp intermission_draw_current_group

.complete:
        ld a, 1
        ld (INTERMISSION_COMPLETE_FLAG), a
        call intermission_advance_review_index
        call intermission_restore_playfield_overlay
        ld a, (INTERMISSION_NEXT_STATE)
        jp game_flow_transition_to

intermission_advance_review_index:
        ld a, (INTERMISSION_REVIEW_INDEX)
        cp INTERMISSION_REVIEW_LAST_INDEX
        ret nc
        inc a
        ld (INTERMISSION_REVIEW_INDEX), a
        ret

intermission_draw_current_group:
        call intermission_fill_panel
        ld a, (INTERMISSION_CURRENT_SCENE)
        cp INTERMISSION_SCENE_TABLES_TURN
        jp z, intermission_draw_scene_1
        cp INTERMISSION_SCENE_NAIL_TEAR
        jp z, intermission_draw_scene_2
        cp INTERMISSION_SCENE_PATCH_DRAG
        jp z, intermission_draw_scene_3
        ret

intermission_draw_scene_1:
        ld a, (INTERMISSION_CURRENT_GROUP)
        cp INTERMISSION_GROUP_GAG
        jr z, intermission_draw_scene_1_gag
        cp INTERMISSION_GROUP_EXIT
        jp z, intermission_draw_scene_1_exit
intermission_draw_scene_1_chase:
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 102, 170, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 102, 204, INTERMISSION_BLINKY_PATTERN, SPRITE_PALETTE_BLINKY
        jp intermission_upload_scene_sprites
intermission_draw_scene_1_gag:
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 102, 22, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 102, 40, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 2, 102, 76, INTERMISSION_FRIGHT_PATTERN, SPRITE_PALETTE_FRIGHTENED
        jp intermission_upload_scene_sprites
intermission_draw_scene_1_exit:
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 102, 100, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 102, 118, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 2, 102, 154, INTERMISSION_FRIGHT_PATTERN, SPRITE_PALETTE_FRIGHTENED
        jp intermission_upload_scene_sprites

intermission_draw_scene_2:
        ld a, (INTERMISSION_CURRENT_GROUP)
        cp INTERMISSION_GROUP_GAG
        jr z, intermission_draw_scene_2_gag
        cp INTERMISSION_GROUP_EXIT
        jp z, intermission_draw_scene_2_exit
intermission_draw_scene_2_chase:
        call intermission_draw_nail
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 102, 160, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 102, 194, INTERMISSION_BLINKY_PATTERN, SPRITE_PALETTE_BLINKY
        jp intermission_upload_scene_sprites
intermission_draw_scene_2_gag:
        call intermission_draw_nail
        call intermission_draw_tear
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 102, 36, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 102, 128, INTERMISSION_BLINKY_PATTERN, SPRITE_PALETTE_BLINKY
        jp intermission_upload_scene_sprites
intermission_draw_scene_2_exit:
        call intermission_draw_nail
        call intermission_draw_tear
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 102, 128, INTERMISSION_BLINKY_PATTERN, SPRITE_PALETTE_BLINKY
        INTERMISSION_SPRITE 1, 104, 148, INTERMISSION_EYES_PATTERN, SPRITE_PALETTE_PACMAN
        jp intermission_upload_scene_sprites

intermission_draw_scene_3:
        ld a, (INTERMISSION_CURRENT_GROUP)
        cp INTERMISSION_GROUP_GAG
        jr z, intermission_draw_scene_3_gag
        cp INTERMISSION_GROUP_EXIT
        jp z, intermission_draw_scene_3_exit
intermission_draw_scene_3_chase:
        call intermission_draw_patch
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 102, 160, INTERMISSION_PACMAN_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 102, 194, INTERMISSION_BLINKY_PATTERN, SPRITE_PALETTE_BLINKY
        jp intermission_upload_scene_sprites
intermission_draw_scene_3_gag:
        call intermission_draw_cloth_trail
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 106, 58, INTERMISSION_EYES_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 118, 86, INTERMISSION_BLINKY_PATTERN, SPRITE_PALETTE_BLINKY
        jp intermission_upload_scene_sprites
intermission_draw_scene_3_exit:
        call intermission_draw_cloth_trail
        call intermission_clear_sprite_shadows
        INTERMISSION_SPRITE 0, 106, 124, INTERMISSION_EYES_PATTERN, SPRITE_PALETTE_PACMAN
        INTERMISSION_SPRITE 1, 126, 82, INTERMISSION_BLINKY_PATTERN, SPRITE_PALETTE_BLINKY
        jp intermission_upload_scene_sprites

intermission_upload_scene_sprites:
        ld a, (SPRITE_SAT_SHADOW + 3)
        ld c, 0
        call intermission_fill_color_slot
        ld a, (SPRITE_SAT_SHADOW + SPRITE_SAT_STRIDE + 3)
        ld c, 1
        call intermission_fill_color_slot
        ld a, (SPRITE_SAT_SHADOW + (SPRITE_SAT_STRIDE * 2) + 3)
        ld c, 2
        call intermission_fill_color_slot
        ld a, (SPRITE_SAT_SHADOW + (SPRITE_SAT_STRIDE * 3) + 3)
        ld c, 3
        call intermission_fill_color_slot
        ld a, (SPRITE_SAT_SHADOW + (SPRITE_SAT_STRIDE * 4) + 3)
        ld c, 4
        call intermission_fill_color_slot
        call sprite_upload_color_shadow
        jp sprite_upload_sat_shadow

intermission_clear_sprite_shadows:
        ld hl, SPRITE_SAT_SHADOW
        ld b, SPRITE_SAT_SHADOW_BYTES
        xor a
.sat_loop:
        ld (hl), a
        inc hl
        djnz .sat_loop
        ld a, SPRITE_TERMINATOR_Y
        ld (SPRITE_SAT_SHADOW + (SPRITE_SAT_STRIDE * 5)), a

        ld hl, SPRITE_COLOR_SHADOW
        ld b, SPRITE_COLOR_SHADOW_BYTES
        xor a
.color_loop:
        ld (hl), a
        inc hl
        djnz .color_loop
        ret

; Input: C = slot, A = palette index for all rows in that slot.
intermission_fill_color_slot:
        push af
        ld a, c
        add a, a
        add a, a
        add a, a
        add a, a
        ld e, a
        ld d, 0
        ld hl, SPRITE_COLOR_SHADOW
        add hl, de
        pop af
        ld b, SPRITE_COLOR_STRIDE
.loop:
        ld (hl), a
        inc hl
        djnz .loop
        ret

intermission_fill_panel:
        call clear_vdp_a_framebuffer
        ld a, (INTERMISSION_CURRENT_SCENE)
        cp INTERMISSION_SCENE_TABLES_TURN
        jp z, .scene_1
        cp INTERMISSION_SCENE_NAIL_TEAR
        jp z, .scene_2
        ld bc, 0x2418
        ld d, 68
        ld e, 80
        ld a, INTERMISSION_PANEL_FILL_SCENE_3
        call intermission_fill_vdp_b_rect
        ld bc, 0x2E1E
        ld d, 4
        ld e, 18
        ld a, INTERMISSION_CLEAR_FILL
        call intermission_fill_vdp_b_rect
        ld bc, 0x3A3C
        ld d, 4
        ld e, 18
        ld a, INTERMISSION_CLEAR_FILL
        call intermission_fill_vdp_b_rect
        ret
.scene_1:
        ld bc, 0x2418
        ld d, 68
        ld e, 80
        ld a, INTERMISSION_PANEL_FILL_SCENE_1
        call intermission_fill_vdp_b_rect
        ld bc, 0x321C
        ld d, 4
        ld e, 16
        ld a, INTERMISSION_CLEAR_FILL
        call intermission_fill_vdp_b_rect
        ld bc, 0x3234
        ld d, 4
        ld e, 16
        ld a, INTERMISSION_CLEAR_FILL
        call intermission_fill_vdp_b_rect
        ret
.scene_2:
        ld bc, 0x2418
        ld d, 68
        ld e, 80
        ld a, INTERMISSION_PANEL_FILL_SCENE_2
        call intermission_fill_vdp_b_rect
        ld bc, 0x2C22
        ld d, 6
        ld e, 14
        ld a, INTERMISSION_CLEAR_FILL
        call intermission_fill_vdp_b_rect
        ret

; Input: BC = VRAM offset on VDP-B page 0, D = height in rows, E = width in
; bytes, A = fill value.
intermission_fill_vdp_b_rect:
        ld a, d
        or a
        ret z
.row:
        push bc
        push de
        push af
        call vdp_b_seek_write_bc
        ld b, e
        pop af
.byte:
        out (VDP_B_DATA), a
        djnz .byte
        pop de
        pop bc
        ld hl, 0x0080
        add hl, bc
        ld b, h
        ld c, l
        dec d
        jr nz, .row
        ret

intermission_restore_playfield_overlay:
        call clear_vdp_a_framebuffer
        call load_vdp_b_maze_framebuffer
        call sprite_renderer_init
        jp hud_renderer_init

intermission_draw_nail:
        ld bc, 0x2636
        ld d, 52
        ld e, 2
        ld a, INTERMISSION_NAIL_FILL
        call intermission_fill_vdp_b_rect
        ret

intermission_draw_tear:
        ld bc, 0x2E3A
        ld d, 10
        ld e, 8
        ld a, INTERMISSION_TEAR_FILL
        call intermission_fill_vdp_b_rect
        ret

intermission_draw_patch:
        ld bc, 0x2B30
        ld d, 12
        ld e, 10
        ld a, INTERMISSION_TEAR_FILL
        call intermission_fill_vdp_b_rect
        ret

intermission_draw_cloth_trail:
        ld bc, 0x3928
        ld d, 6
        ld e, 28
        ld a, INTERMISSION_CLOTH_FILL
        call intermission_fill_vdp_b_rect
        ret
