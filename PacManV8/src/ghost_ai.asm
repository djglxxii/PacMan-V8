; Deterministic ghost targeting and mode control for T009/T010.
; The routines keep all positions in arcade tile coordinates. Higher-level
; collision, speed, and rendering are intentionally left to later tasks.

GHOST_ID_BLINKY         EQU 0
GHOST_ID_PINKY          EQU 1
GHOST_ID_INKY           EQU 2
GHOST_ID_CLYDE          EQU 3

GHOST_MODE_CHASE        EQU 0
GHOST_MODE_SCATTER      EQU 1
GHOST_MODE_FRIGHTENED   EQU 2

GHOST_FRAMES_PER_SECOND EQU LEVEL_FRAMES_PER_SECOND
GHOST_SCATTER_7_FRAMES  EQU LEVEL_SCATTER_7_FRAMES
GHOST_SCATTER_5_FRAMES  EQU LEVEL_SCATTER_5_FRAMES
GHOST_CHASE_20_FRAMES   EQU LEVEL_CHASE_20_FRAMES
GHOST_CHASE_1033_FRAMES EQU LEVEL_CHASE_1033_FRAMES
GHOST_CHASE_1037_FRAMES EQU LEVEL_CHASE_1037_FRAMES
GHOST_SCATTER_1_FRAME   EQU LEVEL_SCATTER_1_FRAME

GHOST_PHASE_S1          EQU 0
GHOST_PHASE_C1          EQU 1
GHOST_PHASE_S2          EQU 2
GHOST_PHASE_C2          EQU 3
GHOST_PHASE_S3          EQU 4
GHOST_PHASE_C3          EQU 5
GHOST_PHASE_S4          EQU 6
GHOST_PHASE_C_FOREVER   EQU 7

GHOST_SCHEDULE_LEVEL1   EQU LEVEL_SCHEDULE_LEVEL1
GHOST_SCHEDULE_LEVEL2_4 EQU LEVEL_SCHEDULE_LEVEL2_4
GHOST_SCHEDULE_LEVEL5P  EQU LEVEL_SCHEDULE_LEVEL5P

GHOST_REVERSAL_BLINKY   EQU 0x01
GHOST_REVERSAL_PINKY    EQU 0x02
GHOST_REVERSAL_INKY     EQU 0x04
GHOST_REVERSAL_CLYDE    EQU 0x08
GHOST_REVERSAL_ALL      EQU 0x0F

GHOST_SCATTER_BLINKY_X  EQU 25
GHOST_SCATTER_BLINKY_Y  EQU 0xFD        ; -3, signed arcade tile coordinate
GHOST_SCATTER_PINKY_X   EQU 2
GHOST_SCATTER_PINKY_Y   EQU 0xFD        ; -3, signed arcade tile coordinate
GHOST_SCATTER_INKY_X    EQU 27
GHOST_SCATTER_INKY_Y    EQU 35
GHOST_SCATTER_CLYDE_X   EQU 0
GHOST_SCATTER_CLYDE_Y   EQU 35

GHOST_STATE_BASE        EQU 0x8120
GHOST_RECORD_SIZE       EQU 8

GHOST_RECORD_X_TILE     EQU 0
GHOST_RECORD_Y_TILE     EQU 1
GHOST_RECORD_DIR        EQU 2
GHOST_RECORD_MODE       EQU 3
GHOST_RECORD_ID         EQU 4
GHOST_RECORD_TARGET_X   EQU 5
GHOST_RECORD_TARGET_Y   EQU 6
GHOST_RECORD_CHOSEN_DIR EQU 7

GHOST_BLINKY_BASE       EQU GHOST_STATE_BASE + (GHOST_ID_BLINKY * GHOST_RECORD_SIZE)
GHOST_PINKY_BASE        EQU GHOST_STATE_BASE + (GHOST_ID_PINKY * GHOST_RECORD_SIZE)
GHOST_INKY_BASE         EQU GHOST_STATE_BASE + (GHOST_ID_INKY * GHOST_RECORD_SIZE)
GHOST_CLYDE_BASE        EQU GHOST_STATE_BASE + (GHOST_ID_CLYDE * GHOST_RECORD_SIZE)

GHOST_BLINKY_X_TILE     EQU GHOST_BLINKY_BASE + GHOST_RECORD_X_TILE
GHOST_BLINKY_Y_TILE     EQU GHOST_BLINKY_BASE + GHOST_RECORD_Y_TILE
GHOST_BLINKY_DIR        EQU GHOST_BLINKY_BASE + GHOST_RECORD_DIR
GHOST_BLINKY_MODE       EQU GHOST_BLINKY_BASE + GHOST_RECORD_MODE
GHOST_BLINKY_ID         EQU GHOST_BLINKY_BASE + GHOST_RECORD_ID
GHOST_BLINKY_TARGET_X   EQU GHOST_BLINKY_BASE + GHOST_RECORD_TARGET_X
GHOST_BLINKY_TARGET_Y   EQU GHOST_BLINKY_BASE + GHOST_RECORD_TARGET_Y
GHOST_BLINKY_CHOSEN_DIR EQU GHOST_BLINKY_BASE + GHOST_RECORD_CHOSEN_DIR

GHOST_PINKY_X_TILE      EQU GHOST_PINKY_BASE + GHOST_RECORD_X_TILE
GHOST_PINKY_Y_TILE      EQU GHOST_PINKY_BASE + GHOST_RECORD_Y_TILE
GHOST_PINKY_DIR         EQU GHOST_PINKY_BASE + GHOST_RECORD_DIR
GHOST_PINKY_MODE        EQU GHOST_PINKY_BASE + GHOST_RECORD_MODE
GHOST_PINKY_ID          EQU GHOST_PINKY_BASE + GHOST_RECORD_ID
GHOST_PINKY_TARGET_X    EQU GHOST_PINKY_BASE + GHOST_RECORD_TARGET_X
GHOST_PINKY_TARGET_Y    EQU GHOST_PINKY_BASE + GHOST_RECORD_TARGET_Y
GHOST_PINKY_CHOSEN_DIR  EQU GHOST_PINKY_BASE + GHOST_RECORD_CHOSEN_DIR

GHOST_INKY_X_TILE       EQU GHOST_INKY_BASE + GHOST_RECORD_X_TILE
GHOST_INKY_Y_TILE       EQU GHOST_INKY_BASE + GHOST_RECORD_Y_TILE
GHOST_INKY_DIR          EQU GHOST_INKY_BASE + GHOST_RECORD_DIR
GHOST_INKY_MODE         EQU GHOST_INKY_BASE + GHOST_RECORD_MODE
GHOST_INKY_ID           EQU GHOST_INKY_BASE + GHOST_RECORD_ID
GHOST_INKY_TARGET_X     EQU GHOST_INKY_BASE + GHOST_RECORD_TARGET_X
GHOST_INKY_TARGET_Y     EQU GHOST_INKY_BASE + GHOST_RECORD_TARGET_Y
GHOST_INKY_CHOSEN_DIR   EQU GHOST_INKY_BASE + GHOST_RECORD_CHOSEN_DIR

GHOST_CLYDE_X_TILE      EQU GHOST_CLYDE_BASE + GHOST_RECORD_X_TILE
GHOST_CLYDE_Y_TILE      EQU GHOST_CLYDE_BASE + GHOST_RECORD_Y_TILE
GHOST_CLYDE_DIR         EQU GHOST_CLYDE_BASE + GHOST_RECORD_DIR
GHOST_CLYDE_MODE        EQU GHOST_CLYDE_BASE + GHOST_RECORD_MODE
GHOST_CLYDE_ID          EQU GHOST_CLYDE_BASE + GHOST_RECORD_ID
GHOST_CLYDE_TARGET_X    EQU GHOST_CLYDE_BASE + GHOST_RECORD_TARGET_X
GHOST_CLYDE_TARGET_Y    EQU GHOST_CLYDE_BASE + GHOST_RECORD_TARGET_Y
GHOST_CLYDE_CHOSEN_DIR  EQU GHOST_CLYDE_BASE + GHOST_RECORD_CHOSEN_DIR

GHOST_WORK_BASE         EQU 0x8160
GHOST_CHOICE_TILE_X     EQU GHOST_WORK_BASE + 0
GHOST_CHOICE_TILE_Y     EQU GHOST_WORK_BASE + 1
GHOST_CHOICE_CURRENT_DIR EQU GHOST_WORK_BASE + 2
GHOST_CHOICE_TARGET_X   EQU GHOST_WORK_BASE + 3
GHOST_CHOICE_TARGET_Y   EQU GHOST_WORK_BASE + 4
GHOST_CHOICE_ALLOW_REVERSAL EQU GHOST_WORK_BASE + 5
GHOST_CANDIDATE_X       EQU GHOST_WORK_BASE + 6
GHOST_CANDIDATE_Y       EQU GHOST_WORK_BASE + 7
GHOST_CANDIDATE_DIR     EQU GHOST_WORK_BASE + 8
GHOST_BEST_DIR          EQU GHOST_WORK_BASE + 9
GHOST_BEST_DISTANCE     EQU GHOST_WORK_BASE + 10
GHOST_FRIGHT_START_DIR  EQU GHOST_WORK_BASE + 12
GHOST_FRIGHT_TRIES      EQU GHOST_WORK_BASE + 13
GHOST_FRIGHT_CANDIDATE  EQU GHOST_WORK_BASE + 14

GHOST_MODE_STATE_BASE   EQU 0x8170
GHOST_GLOBAL_MODE       EQU GHOST_MODE_STATE_BASE + 0
GHOST_PRIOR_MODE        EQU GHOST_MODE_STATE_BASE + 1
GHOST_SCHEDULE_KIND     EQU GHOST_MODE_STATE_BASE + 2
GHOST_MODE_PHASE        EQU GHOST_MODE_STATE_BASE + 3
GHOST_PHASE_REMAIN      EQU GHOST_MODE_STATE_BASE + 4
GHOST_FRIGHT_REMAIN     EQU GHOST_MODE_STATE_BASE + 6
GHOST_REVERSAL_PENDING  EQU GHOST_MODE_STATE_BASE + 8
GHOST_FRIGHT_PRNG_STATE EQU GHOST_MODE_STATE_BASE + 9

ghost_init_state:
        ld a, 14
        ld (GHOST_BLINKY_X_TILE), a
        ld a, 14
        ld (GHOST_BLINKY_Y_TILE), a
        ld a, MOVEMENT_DIR_LEFT
        ld (GHOST_BLINKY_DIR), a
        ld a, GHOST_MODE_CHASE
        ld (GHOST_BLINKY_MODE), a
        ld a, GHOST_ID_BLINKY
        ld (GHOST_BLINKY_ID), a

        ld a, 14
        ld (GHOST_PINKY_X_TILE), a
        ld a, 17
        ld (GHOST_PINKY_Y_TILE), a
        ld a, MOVEMENT_DIR_DOWN
        ld (GHOST_PINKY_DIR), a
        ld a, GHOST_MODE_CHASE
        ld (GHOST_PINKY_MODE), a
        ld a, GHOST_ID_PINKY
        ld (GHOST_PINKY_ID), a

        ld a, 12
        ld (GHOST_INKY_X_TILE), a
        ld a, 17
        ld (GHOST_INKY_Y_TILE), a
        ld a, MOVEMENT_DIR_UP
        ld (GHOST_INKY_DIR), a
        ld a, GHOST_MODE_CHASE
        ld (GHOST_INKY_MODE), a
        ld a, GHOST_ID_INKY
        ld (GHOST_INKY_ID), a

        ld a, 16
        ld (GHOST_CLYDE_X_TILE), a
        ld a, 17
        ld (GHOST_CLYDE_Y_TILE), a
        ld a, MOVEMENT_DIR_UP
        ld (GHOST_CLYDE_DIR), a
        ld a, GHOST_MODE_CHASE
        ld (GHOST_CLYDE_MODE), a
        ld a, GHOST_ID_CLYDE
        ld (GHOST_CLYDE_ID), a
        call ghost_mode_init
        call ghost_house_init
        ret

ghost_mode_init:
        call level_progression_get_current_schedule_kind
        ld (GHOST_SCHEDULE_KIND), a
        ld a, GHOST_PHASE_S1
        ld (GHOST_MODE_PHASE), a
        ld a, GHOST_MODE_SCATTER
        ld (GHOST_GLOBAL_MODE), a
        ld (GHOST_PRIOR_MODE), a
        call ghost_mode_apply_to_records
        ld a, GHOST_PHASE_S1
        call ghost_mode_load_phase_duration
        ld hl, 0
        ld (GHOST_FRIGHT_REMAIN), hl
        xor a
        ld (GHOST_REVERSAL_PENDING), a
        ld a, 0x5A
        ld (GHOST_FRIGHT_PRNG_STATE), a
        ret

; Advances the global mode controller by one gameplay frame. Scatter/chase
; timing pauses while frightened mode is active, matching the timer contract
; later gameplay systems will depend on.
ghost_mode_tick:
        ld a, (GHOST_GLOBAL_MODE)
        cp GHOST_MODE_FRIGHTENED
        jr z, ghost_mode_tick_frightened

        ld a, (GHOST_MODE_PHASE)
        cp GHOST_PHASE_C_FOREVER
        ret z

        ld hl, (GHOST_PHASE_REMAIN)
        ld a, h
        or l
        ret z
        dec hl
        ld (GHOST_PHASE_REMAIN), hl
        ld a, h
        or l
        ret nz

        ld a, (GHOST_MODE_PHASE)
        inc a
        jp ghost_mode_transition_to_phase

ghost_mode_tick_frightened:
        ld hl, (GHOST_FRIGHT_REMAIN)
        ld a, h
        or l
        ret z
        dec hl
        ld (GHOST_FRIGHT_REMAIN), hl
        ld a, h
        or l
        ret nz

        ld a, (GHOST_PRIOR_MODE)
        ld (GHOST_GLOBAL_MODE), a
        call ghost_mode_apply_to_records
        ret

; Enters frightened mode using the current level table.
ghost_enter_frightened:
        ld a, (GHOST_MODE_PHASE)
        ld b, a
        ld a, (GHOST_PHASE_REMAIN)
        xor b
        ld (GHOST_FRIGHT_PRNG_STATE), a
        jr ghost_enter_frightened_common

; Input: A = deterministic frightened PRNG seed for test harnesses.
ghost_enter_frightened_seeded:
        ld (GHOST_FRIGHT_PRNG_STATE), a

ghost_enter_frightened_common:
        ld a, (GHOST_GLOBAL_MODE)
        cp GHOST_MODE_FRIGHTENED
        jr z, .already_frightened
        ld (GHOST_PRIOR_MODE), a
.already_frightened:
        call level_progression_get_current_frightened_frames
        ld (GHOST_FRIGHT_REMAIN), hl
        ld a, h
        or l
        jr z, .no_blue_time
        ld a, GHOST_MODE_FRIGHTENED
        ld (GHOST_GLOBAL_MODE), a
        call ghost_mode_apply_to_records
        jr .request_reversal
.no_blue_time:
        ld a, (GHOST_PRIOR_MODE)
        ld (GHOST_GLOBAL_MODE), a
        call ghost_mode_apply_to_records
.request_reversal:
        call ghost_request_all_reversals
        ret

ghost_mode_transition_to_phase:
        ld (GHOST_MODE_PHASE), a
        push af
        call ghost_mode_load_phase_duration
        pop af
        call ghost_mode_phase_to_global
        ld (GHOST_GLOBAL_MODE), a
        call ghost_mode_apply_to_records
        call ghost_request_all_reversals
        ret

; Input: A = schedule phase. Output: A = scatter/chase mode.
ghost_mode_phase_to_global:
        cp GHOST_PHASE_C_FOREVER
        jr nc, .chase
        and 0x01
        jr z, .scatter
.chase:
        ld a, GHOST_MODE_CHASE
        ret
.scatter:
        ld a, GHOST_MODE_SCATTER
        ret

; Input: A = schedule phase. Duration comes from the current level schedule
; family: level 1, levels 2-4, or level 5+.
ghost_mode_load_phase_duration:
        cp GHOST_PHASE_S1
        jr z, .scatter_first_pair
        cp GHOST_PHASE_C1
        jr z, .chase20
        cp GHOST_PHASE_S2
        jr z, .scatter_first_pair
        cp GHOST_PHASE_C2
        jr z, .chase20
        cp GHOST_PHASE_S3
        jr z, .scatter5
        cp GHOST_PHASE_C3
        jr z, .chase_third
        cp GHOST_PHASE_S4
        jr z, .scatter_fourth
        ld hl, 0
        jr .store
.scatter_first_pair:
        ld a, (GHOST_SCHEDULE_KIND)
        cp GHOST_SCHEDULE_LEVEL5P
        jr z, .scatter5
        ld hl, GHOST_SCATTER_7_FRAMES
        jr .store
.scatter5:
        ld hl, GHOST_SCATTER_5_FRAMES
        jr .store
.chase20:
        ld hl, GHOST_CHASE_20_FRAMES
        jr .store
.chase_third:
        ld a, (GHOST_SCHEDULE_KIND)
        cp GHOST_SCHEDULE_LEVEL1
        jr z, .chase20
        cp GHOST_SCHEDULE_LEVEL2_4
        jr z, .chase1033
        ld hl, GHOST_CHASE_1037_FRAMES
        jr .store
.chase1033:
        ld hl, GHOST_CHASE_1033_FRAMES
        jr .store
.scatter_fourth:
        ld a, (GHOST_SCHEDULE_KIND)
        cp GHOST_SCHEDULE_LEVEL1
        jr z, .scatter5
        ld hl, GHOST_SCATTER_1_FRAME
.store:
        ld (GHOST_PHASE_REMAIN), hl
        ret

; Input: A = mode to write into all ghost records.
ghost_mode_apply_to_records:
        ld (GHOST_BLINKY_MODE), a
        ld (GHOST_PINKY_MODE), a
        ld (GHOST_INKY_MODE), a
        ld (GHOST_CLYDE_MODE), a
        ret

ghost_request_all_reversals:
        ld a, (GHOST_REVERSAL_PENDING)
        or GHOST_REVERSAL_ALL
        ld (GHOST_REVERSAL_PENDING), a
        ret

ghost_clear_reversal_requests:
        xor a
        ld (GHOST_REVERSAL_PENDING), a
        ret

; Input: B = current tile x, C = current tile y, D = current direction,
;        A = nonzero to allow reversal.
; Output: A = deterministic pseudo-random legal direction, or NONE.
ghost_choose_frightened_direction:
        ld (GHOST_CHOICE_ALLOW_REVERSAL), a
        ld a, b
        ld (GHOST_CHOICE_TILE_X), a
        ld a, c
        ld (GHOST_CHOICE_TILE_Y), a
        ld a, d
        ld (GHOST_CHOICE_CURRENT_DIR), a
        call ghost_advance_frightened_prng
        and 0x03
        ld (GHOST_FRIGHT_START_DIR), a
        xor a
        ld (GHOST_FRIGHT_TRIES), a
.loop:
        ld a, (GHOST_FRIGHT_START_DIR)
        ld b, a
        ld a, (GHOST_FRIGHT_TRIES)
        add a, b
        and 0x03
        call ghost_frightened_index_to_dir
        call ghost_frightened_candidate_legal
        ret c
        ld a, (GHOST_FRIGHT_TRIES)
        inc a
        ld (GHOST_FRIGHT_TRIES), a
        cp 4
        jr c, .loop
        ld a, MOVEMENT_DIR_NONE
        ret

ghost_advance_frightened_prng:
        ld a, (GHOST_FRIGHT_PRNG_STATE)
        ld b, a
        add a, a
        add a, a
        add a, b
        inc a
        ld (GHOST_FRIGHT_PRNG_STATE), a
        ret

ghost_frightened_index_to_dir:
        cp 0
        jr z, .up
        cp 1
        jr z, .left
        cp 2
        jr z, .down
        ld a, MOVEMENT_DIR_RIGHT
        ret
.up:
        ld a, MOVEMENT_DIR_UP
        ret
.left:
        ld a, MOVEMENT_DIR_LEFT
        ret
.down:
        ld a, MOVEMENT_DIR_DOWN
        ret

; Input: A = candidate direction. Output: carry set if legal, A = direction.
ghost_frightened_candidate_legal:
        ld (GHOST_FRIGHT_CANDIDATE), a
        ld a, (GHOST_CHOICE_ALLOW_REVERSAL)
        or a
        jr nz, .compute
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_UP
        jr nz, .not_up
        ld a, (GHOST_FRIGHT_CANDIDATE)
        cp MOVEMENT_DIR_DOWN
        jp z, .blocked
.not_up:
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_DOWN
        jr nz, .not_down
        ld a, (GHOST_FRIGHT_CANDIDATE)
        cp MOVEMENT_DIR_UP
        jp z, .blocked
.not_down:
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_LEFT
        jr nz, .not_left
        ld a, (GHOST_FRIGHT_CANDIDATE)
        cp MOVEMENT_DIR_RIGHT
        jr z, .blocked
.not_left:
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_RIGHT
        jr nz, .compute
        ld a, (GHOST_FRIGHT_CANDIDATE)
        cp MOVEMENT_DIR_LEFT
        jr z, .blocked

.compute:
        ld a, (GHOST_CHOICE_TILE_X)
        ld (GHOST_CANDIDATE_X), a
        ld a, (GHOST_CHOICE_TILE_Y)
        ld (GHOST_CANDIDATE_Y), a
        ld a, (GHOST_FRIGHT_CANDIDATE)
        cp MOVEMENT_DIR_UP
        jr z, .up
        cp MOVEMENT_DIR_LEFT
        jr z, .left
        cp MOVEMENT_DIR_DOWN
        jr z, .down
        cp MOVEMENT_DIR_RIGHT
        jr z, .right
        jr .blocked
.up:
        ld a, (GHOST_CANDIDATE_Y)
        or a
        jr z, .blocked
        dec a
        ld (GHOST_CANDIDATE_Y), a
        jr .check_cell
.left:
        ld a, (GHOST_CANDIDATE_X)
        or a
        jr z, .left_wrap
        dec a
        jr .left_store
.left_wrap:
        ld a, MOVEMENT_MAZE_WIDTH - 1
.left_store:
        ld (GHOST_CANDIDATE_X), a
        jr .check_cell
.down:
        ld a, (GHOST_CANDIDATE_Y)
        cp MOVEMENT_MAZE_HEIGHT - 1
        jr z, .blocked
        inc a
        ld (GHOST_CANDIDATE_Y), a
        jr .check_cell
.right:
        ld a, (GHOST_CANDIDATE_X)
        cp MOVEMENT_MAZE_WIDTH - 1
        jr z, .right_wrap
        inc a
        jr .right_store
.right_wrap:
        xor a
.right_store:
        ld (GHOST_CANDIDATE_X), a

.check_cell:
        ld a, (GHOST_CANDIDATE_X)
        ld b, a
        ld a, (GHOST_CANDIDATE_Y)
        ld c, a
        call movement_cell_passable
        or a
        jr z, .blocked
        ld a, (GHOST_FRIGHT_CANDIDATE)
        scf
        ret
.blocked:
        or a
        ret

; Computes chase or scatter target tiles for all four ghosts from the current
; Pac-Man movement state and the existing ghost records.
ghost_update_all_targets:
        call ghost_pacman_tile_to_bc
        ld a, (GHOST_BLINKY_MODE)
        cp GHOST_MODE_SCATTER
        jr z, .blinky_scatter
        cp GHOST_MODE_FRIGHTENED
        jr z, .pinky
        ld a, b
        ld (GHOST_BLINKY_TARGET_X), a
        ld a, c
        ld (GHOST_BLINKY_TARGET_Y), a
        jr .pinky
.blinky_scatter:
        ld a, GHOST_SCATTER_BLINKY_X
        ld (GHOST_BLINKY_TARGET_X), a
        ld a, GHOST_SCATTER_BLINKY_Y
        ld (GHOST_BLINKY_TARGET_Y), a

.pinky:
        call ghost_pacman_tile_to_bc
        ld a, (GHOST_PINKY_MODE)
        cp GHOST_MODE_SCATTER
        jr z, .pinky_scatter
        cp GHOST_MODE_FRIGHTENED
        jr z, .inky
        ld a, (PACMAN_CURRENT_DIR)
        call ghost_apply_four_ahead
        ld a, b
        ld (GHOST_PINKY_TARGET_X), a
        ld a, c
        ld (GHOST_PINKY_TARGET_Y), a
        jr .inky
.pinky_scatter:
        ld a, GHOST_SCATTER_PINKY_X
        ld (GHOST_PINKY_TARGET_X), a
        ld a, GHOST_SCATTER_PINKY_Y
        ld (GHOST_PINKY_TARGET_Y), a

.inky:
        call ghost_pacman_tile_to_bc
        ld a, (GHOST_INKY_MODE)
        cp GHOST_MODE_SCATTER
        jr z, .inky_scatter
        cp GHOST_MODE_FRIGHTENED
        jr z, .clyde
        ld a, (PACMAN_CURRENT_DIR)
        call ghost_apply_two_ahead
        ld a, b
        add a, a
        ld d, a
        ld a, (GHOST_BLINKY_X_TILE)
        ld e, a
        ld a, d
        sub e
        ld (GHOST_INKY_TARGET_X), a
        ld a, c
        add a, a
        ld d, a
        ld a, (GHOST_BLINKY_Y_TILE)
        ld e, a
        ld a, d
        sub e
        ld (GHOST_INKY_TARGET_Y), a
        jr .clyde
.inky_scatter:
        ld a, GHOST_SCATTER_INKY_X
        ld (GHOST_INKY_TARGET_X), a
        ld a, GHOST_SCATTER_INKY_Y
        ld (GHOST_INKY_TARGET_Y), a

.clyde:
        call ghost_pacman_tile_to_bc
        ld a, (GHOST_CLYDE_MODE)
        cp GHOST_MODE_SCATTER
        jr z, .clyde_scatter
        cp GHOST_MODE_FRIGHTENED
        ret z
        call ghost_clyde_chases_pacman
        jr nc, .clyde_scatter
        call ghost_pacman_tile_to_bc
        ld a, b
        ld (GHOST_CLYDE_TARGET_X), a
        ld a, c
        ld (GHOST_CLYDE_TARGET_Y), a
        ret
.clyde_scatter:
        ld a, GHOST_SCATTER_CLYDE_X
        ld (GHOST_CLYDE_TARGET_X), a
        ld a, GHOST_SCATTER_CLYDE_Y
        ld (GHOST_CLYDE_TARGET_Y), a
        ret

; Output: B = Pac-Man tile x, C = Pac-Man tile y.
ghost_pacman_tile_to_bc:
        ld a, (PACMAN_X_FP + 1)
        srl a
        srl a
        srl a
        ld b, a
        ld a, (PACMAN_Y_FP + 1)
        srl a
        srl a
        srl a
        ld c, a
        ret

; Input: B/C = source tile, A = direction. Output: B/C = four-ahead target.
; The UP case keeps the original overflow behavior: four up and four left.
ghost_apply_four_ahead:
        cp MOVEMENT_DIR_UP
        jr z, .up
        cp MOVEMENT_DIR_LEFT
        jr z, .left
        cp MOVEMENT_DIR_DOWN
        jr z, .down
        cp MOVEMENT_DIR_RIGHT
        ret nz
        inc b
        inc b
        inc b
        inc b
        ret
.down:
        inc c
        inc c
        inc c
        inc c
        ret
.left:
        dec b
        dec b
        dec b
        dec b
        ret
.up:
        dec b
        dec b
        dec b
        dec b
        dec c
        dec c
        dec c
        dec c
        ret

; Input: B/C = source tile, A = direction. Output: B/C = two-ahead target.
; Inky uses the same up-direction offset family, scaled to two tiles.
ghost_apply_two_ahead:
        cp MOVEMENT_DIR_UP
        jr z, .up
        cp MOVEMENT_DIR_LEFT
        jr z, .left
        cp MOVEMENT_DIR_DOWN
        jr z, .down
        cp MOVEMENT_DIR_RIGHT
        ret nz
        inc b
        inc b
        ret
.down:
        inc c
        inc c
        ret
.left:
        dec b
        dec b
        ret
.up:
        dec b
        dec b
        dec c
        dec c
        ret

; Input: B/C = Pac-Man tile. Output: carry set when Clyde is farther than
; eight tiles and should chase Pac-Man; carry clear when he scatters.
ghost_clyde_chases_pacman:
        ld a, b
        ld d, a
        ld a, (GHOST_CLYDE_X_TILE)
        ld e, a
        ld a, d
        sub e
        call ghost_abs_a
        call ghost_square_a
        push hl
        ld a, c
        ld d, a
        ld a, (GHOST_CLYDE_Y_TILE)
        ld e, a
        ld a, d
        sub e
        call ghost_abs_a
        call ghost_square_a
        pop de
        add hl, de
        ld a, h
        or a
        jr nz, .chase
        ld a, l
        cp 65
        jr nc, .chase
        or a
        ret
.chase:
        scf
        ret

; Input: B = current tile x, C = current tile y, D = current direction,
;        E = signed target tile x, H = signed target tile y,
;        A = nonzero to allow reversal.
; Output: A = chosen direction using UP, LEFT, DOWN, RIGHT tie order.
ghost_choose_direction:
        ld (GHOST_CHOICE_ALLOW_REVERSAL), a
        ld a, b
        ld (GHOST_CHOICE_TILE_X), a
        ld a, c
        ld (GHOST_CHOICE_TILE_Y), a
        ld a, d
        ld (GHOST_CHOICE_CURRENT_DIR), a
        ld a, e
        ld (GHOST_CHOICE_TARGET_X), a
        ld a, h
        ld (GHOST_CHOICE_TARGET_Y), a
        ld a, MOVEMENT_DIR_NONE
        ld (GHOST_BEST_DIR), a
        ld hl, 0xFFFF
        ld (GHOST_BEST_DISTANCE), hl

        call ghost_eval_up
        call ghost_eval_left
        call ghost_eval_down
        call ghost_eval_right
        ld a, (GHOST_BEST_DIR)
        ret

ghost_eval_up:
        ld a, (GHOST_CHOICE_ALLOW_REVERSAL)
        or a
        jr nz, .candidate
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_DOWN
        ret z
.candidate:
        ld a, (GHOST_CHOICE_TILE_X)
        ld (GHOST_CANDIDATE_X), a
        ld a, (GHOST_CHOICE_TILE_Y)
        or a
        ret z
        dec a
        ld (GHOST_CANDIDATE_Y), a
        ld a, MOVEMENT_DIR_UP
        jp ghost_evaluate_candidate

ghost_eval_left:
        ld a, (GHOST_CHOICE_ALLOW_REVERSAL)
        or a
        jr nz, .candidate
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_RIGHT
        ret z
.candidate:
        ld a, (GHOST_CHOICE_TILE_X)
        or a
        jr z, .wrap
        dec a
        jr .store_x
.wrap:
        ld a, MOVEMENT_MAZE_WIDTH - 1
.store_x:
        ld (GHOST_CANDIDATE_X), a
        ld a, (GHOST_CHOICE_TILE_Y)
        ld (GHOST_CANDIDATE_Y), a
        ld a, MOVEMENT_DIR_LEFT
        jp ghost_evaluate_candidate

ghost_eval_down:
        ld a, (GHOST_CHOICE_ALLOW_REVERSAL)
        or a
        jr nz, .candidate
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_UP
        ret z
.candidate:
        ld a, (GHOST_CHOICE_TILE_X)
        ld (GHOST_CANDIDATE_X), a
        ld a, (GHOST_CHOICE_TILE_Y)
        cp MOVEMENT_MAZE_HEIGHT - 1
        ret z
        inc a
        ld (GHOST_CANDIDATE_Y), a
        ld a, MOVEMENT_DIR_DOWN
        jp ghost_evaluate_candidate

ghost_eval_right:
        ld a, (GHOST_CHOICE_ALLOW_REVERSAL)
        or a
        jr nz, .candidate
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        cp MOVEMENT_DIR_LEFT
        ret z
.candidate:
        ld a, (GHOST_CHOICE_TILE_X)
        cp MOVEMENT_MAZE_WIDTH - 1
        jr z, .wrap
        inc a
        jr .store_x
.wrap:
        xor a
.store_x:
        ld (GHOST_CANDIDATE_X), a
        ld a, (GHOST_CHOICE_TILE_Y)
        ld (GHOST_CANDIDATE_Y), a
        ld a, MOVEMENT_DIR_RIGHT
        jp ghost_evaluate_candidate

ghost_evaluate_candidate:
        ld (GHOST_CANDIDATE_DIR), a
        ld a, (GHOST_CANDIDATE_X)
        ld b, a
        ld a, (GHOST_CANDIDATE_Y)
        ld c, a
        call movement_cell_passable
        or a
        ret z

        call ghost_candidate_distance
        ld de, (GHOST_BEST_DISTANCE)
        ld a, h
        cp d
        jr c, .better
        ret nz
        ld a, l
        cp e
        jr c, .better
        ret
.better:
        ld (GHOST_BEST_DISTANCE), hl
        ld a, (GHOST_CANDIDATE_DIR)
        ld (GHOST_BEST_DIR), a
        ret

ghost_candidate_distance:
        ld a, (GHOST_CANDIDATE_X)
        ld b, a
        ld a, (GHOST_CHOICE_TARGET_X)
        ld c, a
        ld a, b
        sub c
        call ghost_abs_a
        call ghost_square_a
        push hl
        ld a, (GHOST_CANDIDATE_Y)
        ld b, a
        ld a, (GHOST_CHOICE_TARGET_Y)
        ld c, a
        ld a, b
        sub c
        call ghost_abs_a
        call ghost_square_a
        pop de
        add hl, de
        ret

; Input: A = signed 8-bit delta. Output: A = absolute value.
ghost_abs_a:
        bit 7, a
        ret z
        cpl
        inc a
        ret

; Input: A = 0..63. Output: HL = A*A.
ghost_square_a:
        ld b, a
        ld c, a
        ld hl, 0
        or a
        ret z
.loop:
        ld e, c
        ld d, 0
        add hl, de
        djnz .loop
        ret
