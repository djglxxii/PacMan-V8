; T021 deterministic replay validation surface.
; Normal boot/review behavior is unchanged until replay input presses Start.
; Once active, this owner drives the accepted gameplay slices from controller
; port 0 and mirrors checkpoint state into SRAM for headless inspection.

PATTERN_REPLAY_STATE_BASE      EQU 0x8270
PATTERN_REPLAY_ACTIVE          EQU PATTERN_REPLAY_STATE_BASE + 0
PATTERN_REPLAY_LAST_INPUT      EQU PATTERN_REPLAY_STATE_BASE + 1
PATTERN_REPLAY_FRAME_COUNTER   EQU PATTERN_REPLAY_STATE_BASE + 2
PATTERN_REPLAY_SCORE           EQU PATTERN_REPLAY_STATE_BASE + 4
PATTERN_REPLAY_DOTS_EATEN      EQU PATTERN_REPLAY_STATE_BASE + 6
PATTERN_REPLAY_PAC_TILE_X      EQU PATTERN_REPLAY_STATE_BASE + 8
PATTERN_REPLAY_PAC_TILE_Y      EQU PATTERN_REPLAY_STATE_BASE + 9
PATTERN_REPLAY_LAST_CONSUME    EQU PATTERN_REPLAY_STATE_BASE + 10
PATTERN_REPLAY_LAST_COLLISION  EQU PATTERN_REPLAY_STATE_BASE + 11
PATTERN_REPLAY_LAST_DIR        EQU PATTERN_REPLAY_STATE_BASE + 12
PATTERN_REPLAY_RESERVED        EQU PATTERN_REPLAY_STATE_BASE + 13

PATTERN_REPLAY_BUTTON_START    EQU 0x01
PATTERN_REPLAY_BUTTON_RIGHT    EQU 0x10
PATTERN_REPLAY_BUTTON_LEFT     EQU 0x20
PATTERN_REPLAY_BUTTON_DOWN     EQU 0x40
PATTERN_REPLAY_BUTTON_UP       EQU 0x80

pattern_replay_update_frame:
        in a, (0x00)
        ld (PATTERN_REPLAY_LAST_INPUT), a

        ld b, a
        ld a, (PATTERN_REPLAY_ACTIVE)
        or a
        jr nz, .active

        ld a, b
        and PATTERN_REPLAY_BUTTON_START
        ret nz
        jp pattern_replay_start

.active:
        ld hl, (PATTERN_REPLAY_FRAME_COUNTER)
        inc hl
        ld (PATTERN_REPLAY_FRAME_COUNTER), hl

        ld a, b
        call pattern_replay_input_to_dir
        ld (PATTERN_REPLAY_LAST_DIR), a
        cp MOVEMENT_DIR_NONE
        jr z, .after_request
        call movement_request_direction

.after_request:
        ld a, (COLLISION_DOT_STALL)
        or a
        jr z, .move
        call collision_tick_dot_stall
        jr .after_pellet

.move:
        call movement_update_pacman
        call collision_update_pellet_at_pacman
        call pattern_replay_apply_consume_result

.after_pellet:
        call ghost_mode_tick
        call ghost_update_all_targets
        call collision_check_all_ghosts
        ld (PATTERN_REPLAY_LAST_COLLISION), a
        jp pattern_replay_capture_snapshot

pattern_replay_start:
        ld a, 1
        ld (PATTERN_REPLAY_ACTIVE), a
        xor a
        ld (PATTERN_REPLAY_FRAME_COUNTER), a
        ld (PATTERN_REPLAY_FRAME_COUNTER + 1), a
        ld (PATTERN_REPLAY_SCORE), a
        ld (PATTERN_REPLAY_SCORE + 1), a
        ld (PATTERN_REPLAY_DOTS_EATEN), a
        ld (PATTERN_REPLAY_DOTS_EATEN + 1), a
        ld (PATTERN_REPLAY_LAST_CONSUME), a
        ld (PATTERN_REPLAY_LAST_COLLISION), a
        ld (PATTERN_REPLAY_LAST_DIR), a
        ld (PATTERN_REPLAY_RESERVED), a

        call level_progression_init
        call movement_init_pacman
        call ghost_init_state
        call collision_init
        call ghost_update_all_targets

        ld a, (GAME_FLOW_CURRENT_STATE)
        ld (GAME_FLOW_PREVIOUS_STATE), a
        ld a, GAME_FLOW_STATE_PLAYING
        ld (GAME_FLOW_CURRENT_STATE), a
        ld hl, 0
        ld (GAME_FLOW_STATE_TIMER), hl
        ld hl, (GAME_FLOW_FRAME_COUNTER)
        ld (GAME_FLOW_ENTRY_FRAME), hl
        ld (GAME_FLOW_LAST_TRANSITION_FRAME), hl
        ld a, (GAME_FLOW_REVIEW_FLAGS)
        or GAME_FLOW_FLAG_PLAYING
        ld (GAME_FLOW_REVIEW_FLAGS), a

        jp pattern_replay_capture_snapshot

; Input: A = active-low controller port byte (unused; port is re-read).
; Output: A = MOVEMENT_DIR_*.
pattern_replay_input_to_dir:
        jp input_read_controller_0_to_dir

pattern_replay_apply_consume_result:
        ld (PATTERN_REPLAY_LAST_CONSUME), a
        cp COLLISION_CONSUME_PELLET
        jr z, .pellet
        cp COLLISION_CONSUME_ENERGIZER
        ret nz
        ld de, 50
        jr .add_score
.pellet:
        ld de, 10
.add_score:
        ld hl, (PATTERN_REPLAY_SCORE)
        add hl, de
        ld (PATTERN_REPLAY_SCORE), hl
        ld hl, (PATTERN_REPLAY_DOTS_EATEN)
        inc hl
        ld (PATTERN_REPLAY_DOTS_EATEN), hl
        ret

pattern_replay_capture_snapshot:
        ld a, (PACMAN_X_FP + 1)
        srl a
        srl a
        srl a
        ld (PATTERN_REPLAY_PAC_TILE_X), a
        ld a, (PACMAN_Y_FP + 1)
        srl a
        srl a
        srl a
        ld (PATTERN_REPLAY_PAC_TILE_Y), a
        ret
