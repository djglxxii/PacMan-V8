; Level/timing table owner for T019.
; Values are encoded from the public Pac-Man Dossier level specifications.
; Speeds keep both source percentages and 8.8 pixels/frame values.

LEVEL_FRAMES_PER_SECOND        EQU 60
LEVEL_MAX_NUMBER               EQU 256
LEVEL_KILL_SCREEN_NUMBER       EQU 256

LEVEL_SPEED_100_PX_PER_SEC_MILLI EQU 75758
LEVEL_SPEED_FP_0               EQU 0x0000
LEVEL_SPEED_FP_40              EQU 0x0081
LEVEL_SPEED_FP_45              EQU 0x0091
LEVEL_SPEED_FP_50              EQU 0x00A2
LEVEL_SPEED_FP_55              EQU 0x00B2
LEVEL_SPEED_FP_60              EQU 0x00C2
LEVEL_SPEED_FP_75              EQU 0x00F2
LEVEL_SPEED_FP_80              EQU 0x0103
LEVEL_SPEED_FP_85              EQU 0x0113
LEVEL_SPEED_FP_90              EQU 0x0123
LEVEL_SPEED_FP_95              EQU 0x0133
LEVEL_SPEED_FP_100             EQU 0x0143
LEVEL_SPEED_FP_105             EQU 0x0153

LEVEL_SCHEDULE_LEVEL1          EQU 0
LEVEL_SCHEDULE_LEVEL2_4        EQU 1
LEVEL_SCHEDULE_LEVEL5P         EQU 2

LEVEL_SCATTER_7_FRAMES         EQU 420
LEVEL_SCATTER_5_FRAMES         EQU 300
LEVEL_CHASE_20_FRAMES          EQU 1200
LEVEL_CHASE_1033_FRAMES        EQU 61980
LEVEL_CHASE_1037_FRAMES        EQU 62220
LEVEL_SCATTER_1_FRAME          EQU 1

LEVEL_FRUIT_CHERRIES           EQU 0
LEVEL_FRUIT_STRAWBERRY         EQU 1
LEVEL_FRUIT_PEACH              EQU 2
LEVEL_FRUIT_APPLE              EQU 3
LEVEL_FRUIT_GRAPES             EQU 4
LEVEL_FRUIT_GALAXIAN           EQU 5
LEVEL_FRUIT_BELL               EQU 6
LEVEL_FRUIT_KEY                EQU 7

LEVEL_DECISION_INTERMISSION    EQU 0x01
LEVEL_DECISION_KILL_SCREEN     EQU 0x02
LEVEL_DECISION_WRAP            EQU 0x04

LEVEL_STATE_BASE               EQU 0x8260
LEVEL_CURRENT_NUMBER           EQU LEVEL_STATE_BASE + 0
LEVEL_COMPLETED_NUMBER         EQU LEVEL_STATE_BASE + 2
LEVEL_NEXT_NUMBER              EQU LEVEL_STATE_BASE + 4
LEVEL_CURRENT_TABLE_INDEX      EQU LEVEL_STATE_BASE + 6
LEVEL_CURRENT_SCHEDULE_KIND    EQU LEVEL_STATE_BASE + 7
LEVEL_LAST_DECISION_FLAGS      EQU LEVEL_STATE_BASE + 8

level_progression_init:
        ld hl, 1
        ld (LEVEL_CURRENT_NUMBER), hl
        ld (LEVEL_NEXT_NUMBER), hl
        ld hl, 0
        ld (LEVEL_COMPLETED_NUMBER), hl
        xor a
        ld (LEVEL_LAST_DECISION_FLAGS), a
        jp level_progression_update_current_cache

; T018's deterministic review script exercises the first intermission handoff.
; Normal level progression still starts at level 1 through level_progression_init.
level_progression_set_current_level_2_for_review:
        ld hl, 2
        ld (LEVEL_CURRENT_NUMBER), hl
        jp level_progression_update_current_cache

; Input: HL = level number, 1..256. Values outside that range are clamped into
; the table families so tests can probe boundary behavior without corrupting RAM.
level_progression_set_current_level:
        ld a, h
        or l
        jr nz, .not_zero
        ld hl, 1
.not_zero:
        ld (LEVEL_CURRENT_NUMBER), hl
        jp level_progression_update_current_cache

level_progression_complete_current_level:
        ld hl, (LEVEL_CURRENT_NUMBER)
        ld (LEVEL_COMPLETED_NUMBER), hl

        ld de, LEVEL_MAX_NUMBER
        or a
        sbc hl, de
        jr z, .wrap_to_one

        ld hl, (LEVEL_COMPLETED_NUMBER)
        inc hl
        jr .store_next
.wrap_to_one:
        ld hl, 1
.store_next:
        ld (LEVEL_NEXT_NUMBER), hl

        ld b, 0
        ld hl, (LEVEL_COMPLETED_NUMBER)
        ld a, h
        or a
        jr nz, .check_kill
        ld a, l
        cp 2
        jr z, .mark_intermission
        cp 5
        jr z, .mark_intermission
        cp 9
        jr z, .mark_intermission
        jr .check_kill
.mark_intermission:
        ld a, b
        or LEVEL_DECISION_INTERMISSION
        ld b, a

.check_kill:
        ld hl, (LEVEL_NEXT_NUMBER)
        ld a, h
        cp 0x01
        jr nz, .check_wrap
        ld a, l
        or a
        jr nz, .check_wrap
        ld a, b
        or LEVEL_DECISION_KILL_SCREEN
        ld b, a

.check_wrap:
        ld hl, (LEVEL_COMPLETED_NUMBER)
        ld a, h
        cp 0x01
        jr nz, .store_flags
        ld a, l
        or a
        jr nz, .store_flags
        ld a, b
        or LEVEL_DECISION_WRAP
        ld b, a

.store_flags:
        ld a, b
        ld (LEVEL_LAST_DECISION_FLAGS), a
        ld hl, (LEVEL_NEXT_NUMBER)
        ld (LEVEL_CURRENT_NUMBER), hl
        jp level_progression_update_current_cache

level_progression_completed_requests_intermission:
        ld a, (LEVEL_LAST_DECISION_FLAGS)
        and LEVEL_DECISION_INTERMISSION
        ret z
        ld a, 1
        ret

level_progression_update_current_cache:
        ld hl, (LEVEL_CURRENT_NUMBER)
        ld a, h
        or a
        jr nz, .index_twenty_one_plus
        ld a, l
        or a
        jr z, .store_index
        ld b, a
        xor a
.index_loop:
        dec b
        jr z, .store_index
        inc a
        cp 20
        jr z, .store_index
        jr .index_loop
.index_twenty_one_plus:
        ld a, 20
.store_index:
        ld (LEVEL_CURRENT_TABLE_INDEX), a

        ld hl, (LEVEL_CURRENT_NUMBER)
        ld a, h
        or a
        jr nz, .schedule_5p
        ld a, l
        or a
        jr z, .schedule_1
        cp 1
        jr z, .schedule_1
        cp 2
        jr z, .schedule_2_4
        cp 3
        jr z, .schedule_2_4
        cp 4
        jr z, .schedule_2_4
        cp 5
        jr z, .schedule_5p
.schedule_5p:
        ld a, LEVEL_SCHEDULE_LEVEL5P
        jr .store_schedule
.schedule_1:
        ld a, LEVEL_SCHEDULE_LEVEL1
        jr .store_schedule
.schedule_2_4:
        ld a, LEVEL_SCHEDULE_LEVEL2_4
.store_schedule:
        ld (LEVEL_CURRENT_SCHEDULE_KIND), a
        ret

level_progression_get_current_schedule_kind:
        ld a, (LEVEL_CURRENT_SCHEDULE_KIND)
        ret

level_progression_get_current_table_index:
        ld a, (LEVEL_CURRENT_TABLE_INDEX)
        ret

level_progression_get_pacman_normal_percent:
        ld hl, level_pacman_normal_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_pacman_normal_fp:
        ld hl, level_pacman_normal_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_pacman_tunnel_percent:
        ld hl, level_pacman_tunnel_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_pacman_tunnel_fp:
        ld hl, level_pacman_tunnel_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_pacman_fright_percent:
        ld hl, level_pacman_fright_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_pacman_fright_fp:
        ld hl, level_pacman_fright_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_ghost_normal_percent:
        ld hl, level_ghost_normal_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_ghost_normal_fp:
        ld hl, level_ghost_normal_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_ghost_tunnel_percent:
        ld hl, level_ghost_tunnel_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_ghost_tunnel_fp:
        ld hl, level_ghost_tunnel_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_ghost_fright_percent:
        ld hl, level_ghost_fright_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_ghost_fright_fp:
        ld hl, level_ghost_fright_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_elroy1_percent:
        ld hl, level_elroy1_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_elroy1_fp:
        ld hl, level_elroy1_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_elroy2_percent:
        ld hl, level_elroy2_pct_by_index
        jp level_progression_read_percent_by_index

level_progression_get_elroy2_fp:
        ld hl, level_elroy2_fp_by_index
        jp level_progression_read_word_by_index

level_progression_get_elroy1_dots:
        ld hl, level_elroy1_dots_by_index
        jp level_progression_read_percent_by_index

level_progression_get_elroy2_dots:
        ld hl, level_elroy2_dots_by_index
        jp level_progression_read_percent_by_index

level_progression_get_bonus_symbol:
        ld hl, level_bonus_symbol_by_index
        jp level_progression_read_percent_by_index

level_progression_get_bonus_points:
        ld hl, level_bonus_points_by_index
        jp level_progression_read_word_by_index

level_progression_get_current_frightened_frames:
        ld hl, level_fright_frames_by_index
        jp level_progression_read_word_by_index

level_progression_get_current_frightened_flashes:
        ld hl, level_fright_flashes_by_index
        jp level_progression_read_percent_by_index

level_progression_read_percent_by_index:
        ld a, (LEVEL_CURRENT_TABLE_INDEX)
        ld e, a
        ld d, 0
        add hl, de
        ld a, (hl)
        ret

level_progression_read_word_by_index:
        ld a, (LEVEL_CURRENT_TABLE_INDEX)
        add a, a
        ld e, a
        ld d, 0
        add hl, de
        ld e, (hl)
        inc hl
        ld d, (hl)
        ex de, hl
        ret

level_bonus_symbol_by_index:
        db LEVEL_FRUIT_CHERRIES, LEVEL_FRUIT_STRAWBERRY
        db LEVEL_FRUIT_PEACH, LEVEL_FRUIT_PEACH
        db LEVEL_FRUIT_APPLE, LEVEL_FRUIT_APPLE
        db LEVEL_FRUIT_GRAPES, LEVEL_FRUIT_GRAPES
        db LEVEL_FRUIT_GALAXIAN, LEVEL_FRUIT_GALAXIAN
        db LEVEL_FRUIT_BELL, LEVEL_FRUIT_BELL
        db LEVEL_FRUIT_KEY, LEVEL_FRUIT_KEY, LEVEL_FRUIT_KEY, LEVEL_FRUIT_KEY
        db LEVEL_FRUIT_KEY, LEVEL_FRUIT_KEY, LEVEL_FRUIT_KEY, LEVEL_FRUIT_KEY
        db LEVEL_FRUIT_KEY

level_bonus_points_by_index:
        dw 100, 300, 500, 500, 700, 700, 1000, 1000
        dw 2000, 2000, 3000, 3000
        dw 5000, 5000, 5000, 5000, 5000, 5000, 5000, 5000
        dw 5000

level_pacman_normal_pct_by_index:
        db 80, 90, 90, 90, 100, 100, 100, 100, 100, 100
        db 100, 100, 100, 100, 100, 100, 100, 100, 100, 100
        db 90

level_pacman_normal_fp_by_index:
        dw LEVEL_SPEED_FP_80
        dw LEVEL_SPEED_FP_90, LEVEL_SPEED_FP_90, LEVEL_SPEED_FP_90
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_90

; Pac-Man is not slowed by the side tunnels in the arcade behavior.
level_pacman_tunnel_pct_by_index:
        db 80, 90, 90, 90, 100, 100, 100, 100, 100, 100
        db 100, 100, 100, 100, 100, 100, 100, 100, 100, 100
        db 90

level_pacman_tunnel_fp_by_index:
        dw LEVEL_SPEED_FP_80
        dw LEVEL_SPEED_FP_90, LEVEL_SPEED_FP_90, LEVEL_SPEED_FP_90
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_90

level_pacman_fright_pct_by_index:
        db 90, 95, 95, 95, 100, 100, 100, 100, 100, 100
        db 100, 100, 100, 100, 100, 100, 0, 100, 0, 0
        db 0

level_pacman_fright_fp_by_index:
        dw LEVEL_SPEED_FP_90
        dw LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_0, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_0, LEVEL_SPEED_FP_0
        dw LEVEL_SPEED_FP_0

level_ghost_normal_pct_by_index:
        db 75, 85, 85, 85, 95, 95, 95, 95, 95, 95
        db 95, 95, 95, 95, 95, 95, 95, 95, 95, 95
        db 95

level_ghost_normal_fp_by_index:
        dw LEVEL_SPEED_FP_75
        dw LEVEL_SPEED_FP_85, LEVEL_SPEED_FP_85, LEVEL_SPEED_FP_85
        dw LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95
        dw LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95
        dw LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95
        dw LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95
        dw LEVEL_SPEED_FP_95

level_ghost_tunnel_pct_by_index:
        db 40, 45, 45, 45, 50, 50, 50, 50, 50, 50
        db 50, 50, 50, 50, 50, 50, 50, 50, 50, 50
        db 50

level_ghost_tunnel_fp_by_index:
        dw LEVEL_SPEED_FP_40
        dw LEVEL_SPEED_FP_45, LEVEL_SPEED_FP_45, LEVEL_SPEED_FP_45
        dw LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50
        dw LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50
        dw LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50
        dw LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50, LEVEL_SPEED_FP_50
        dw LEVEL_SPEED_FP_50

level_ghost_fright_pct_by_index:
        db 50, 55, 55, 55, 60, 60, 60, 60, 60, 60
        db 60, 60, 60, 60, 60, 60, 0, 60, 0, 0
        db 0

level_ghost_fright_fp_by_index:
        dw LEVEL_SPEED_FP_50
        dw LEVEL_SPEED_FP_55, LEVEL_SPEED_FP_55, LEVEL_SPEED_FP_55
        dw LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60
        dw LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60
        dw LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_60
        dw LEVEL_SPEED_FP_0, LEVEL_SPEED_FP_60, LEVEL_SPEED_FP_0, LEVEL_SPEED_FP_0
        dw LEVEL_SPEED_FP_0

level_elroy1_dots_by_index:
        db 20, 30, 40, 40, 40, 50, 50, 50, 60, 60
        db 60, 80, 80, 80, 100, 100, 100, 100, 120, 120
        db 120

level_elroy1_pct_by_index:
        db 80, 90, 90, 90, 100, 100, 100, 100, 100, 100
        db 100, 100, 100, 100, 100, 100, 100, 100, 100, 100
        db 100

level_elroy1_fp_by_index:
        dw LEVEL_SPEED_FP_80
        dw LEVEL_SPEED_FP_90, LEVEL_SPEED_FP_90, LEVEL_SPEED_FP_90
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100, LEVEL_SPEED_FP_100
        dw LEVEL_SPEED_FP_100

level_elroy2_dots_by_index:
        db 10, 15, 20, 20, 20, 25, 25, 25, 30, 30
        db 30, 40, 40, 40, 50, 50, 50, 50, 60, 60
        db 60

level_elroy2_pct_by_index:
        db 85, 95, 95, 95, 105, 105, 105, 105, 105, 105
        db 105, 105, 105, 105, 105, 105, 105, 105, 105, 105
        db 105

level_elroy2_fp_by_index:
        dw LEVEL_SPEED_FP_85
        dw LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95, LEVEL_SPEED_FP_95
        dw LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105
        dw LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105
        dw LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105
        dw LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105, LEVEL_SPEED_FP_105
        dw LEVEL_SPEED_FP_105

level_fright_seconds_by_index:
        db 6, 5, 4, 3, 2, 5, 2, 2, 1, 5
        db 2, 1, 1, 3, 1, 1, 0, 1, 0, 0
        db 0

level_fright_frames_by_index:
        dw 360, 300, 240, 180, 120, 300, 120, 120, 60, 300
        dw 120, 60, 60, 180, 60, 60, 0, 60, 0, 0
        dw 0

level_fright_flashes_by_index:
        db 5, 5, 5, 5, 5, 5, 5, 5, 3, 5
        db 5, 3, 3, 5, 3, 3, 0, 3, 0, 0
        db 0
