; Boot-time and game-over → new-game state initialization for T023.
; Composes level, ghost, ghost-house, collision, and movement inits,
; then sets SCORE/LIVES. Removes the LOW-3 debug ghost-mode mix from the
; boot path.
;
; Also owns the per-frame PLAYING tick (T025) and ghost tile-based movement.
;
; RAM claimed by this module:
;   0x8140–0x8143  GHOST_MOVE_COUNTER  (4 bytes, one per ghost)
;   0x8241–0x8244  GAME_STATE_SCORE    (4 bytes, little-endian)
;   0x8245         GAME_STATE_LIVES    (1 byte)
;   0x8246–0x824F  reserved (future expansion)
;
; Placed immediately after AUDIO_STATE_BASE (0x8230, extends to 0x8240)
; and before GAME_FLOW_STATE_BASE (0x8250).  LEVEL is stored at
; LEVEL_CURRENT_NUMBER (0x8260) by level_progression_init — no separate
; LEVEL byte is allocated here.

GAME_STATE_BASE     EQU 0x8241
GAME_STATE_SCORE    EQU GAME_STATE_BASE + 0    ; 4 bytes, little-endian
GAME_STATE_LIVES    EQU GAME_STATE_BASE + 4    ; 1 byte

GHOST_MOVE_COUNTER  EQU 0x8140  ; 4 bytes, one per ghost
GHOST_MOVE_THRESHOLD EQU 4      ; frames per tile at normal speed

game_state_init:
        call level_progression_init     ; sets LEVEL_CURRENT_NUMBER = 1
        call movement_init_pacman
        call ghost_init_state           ; calls ghost_mode_init + ghost_house_init
        call collision_init
        call ghost_init_move_counters

        xor a
        ld (GAME_STATE_SCORE), a
        ld (GAME_STATE_SCORE + 1), a
        ld (GAME_STATE_SCORE + 2), a
        ld (GAME_STATE_SCORE + 3), a

        ld a, 3
        ld (GAME_STATE_LIVES), a
        ret

ghost_init_move_counters:
        xor a
        ld (GHOST_MOVE_COUNTER + 0), a
        ld a, 2
        ld (GHOST_MOVE_COUNTER + 1), a
        ld a, 1
        ld (GHOST_MOVE_COUNTER + 2), a
        ld a, 3
        ld (GHOST_MOVE_COUNTER + 3), a
        ret

; Per-frame PLAYING tick. Composes movement, pellet, ghost, and collision
; updates in arcade order. Called from game_flow_update_frame when
; GAME_FLOW_STATE_PLAYING is active and pattern_replay is not driving.
game_state_tick_playing:
        call input_read_controller_0_to_dir
        call movement_request_direction

        ld a, (COLLISION_DOT_STALL)
        or a
        jr z, .move
        call collision_tick_dot_stall
        jr .after_stall

.move:
        call movement_update_pacman
        call collision_update_pellet_at_pacman

.after_move:
        call ghost_mode_tick
        call ghost_update_all_targets
        call movement_update_ghosts
        call ghost_house_tick
        call collision_check_all_ghosts
        ld a, (COLLISION_DOT_STALL)
        or a
        call z, sprite_animation_tick
        jp sprite_commit_from_game_state

.after_stall:
        call ghost_mode_tick
        call ghost_update_all_targets
        call movement_update_ghosts
        call ghost_house_tick
        call collision_check_all_ghosts
        jp sprite_commit_from_game_state

; Update ghost tile positions. Ghosts outside the house move one tile
; every GHOST_MOVE_THRESHOLD frames.
movement_update_ghosts:
        ld a, (GHOST_HOUSE_BLINKY_STATE)
        cp GHOST_HOUSE_OUTSIDE
        jr nz, .chk_pinky
        ld a, (GHOST_MOVE_COUNTER + 0)
        inc a
        ld (GHOST_MOVE_COUNTER + 0), a
        cp GHOST_MOVE_THRESHOLD
        jr c, .chk_pinky
        xor a
        ld (GHOST_MOVE_COUNTER + 0), a
        ld hl, GHOST_BLINKY_BASE
        call movement_ghost_step

.chk_pinky:
        ld a, (GHOST_HOUSE_PINKY_STATE)
        cp GHOST_HOUSE_OUTSIDE
        jr nz, .chk_inky
        ld a, (GHOST_MOVE_COUNTER + 1)
        inc a
        ld (GHOST_MOVE_COUNTER + 1), a
        cp GHOST_MOVE_THRESHOLD
        jr c, .chk_inky
        xor a
        ld (GHOST_MOVE_COUNTER + 1), a
        ld hl, GHOST_PINKY_BASE
        call movement_ghost_step

.chk_inky:
        ld a, (GHOST_HOUSE_INKY_STATE)
        cp GHOST_HOUSE_OUTSIDE
        jr nz, .chk_clyde
        ld a, (GHOST_MOVE_COUNTER + 2)
        inc a
        ld (GHOST_MOVE_COUNTER + 2), a
        cp GHOST_MOVE_THRESHOLD
        jr c, .chk_clyde
        xor a
        ld (GHOST_MOVE_COUNTER + 2), a
        ld hl, GHOST_INKY_BASE
        call movement_ghost_step

.chk_clyde:
        ld a, (GHOST_HOUSE_CLYDE_STATE)
        cp GHOST_HOUSE_OUTSIDE
        ret nz
        ld a, (GHOST_MOVE_COUNTER + 3)
        inc a
        ld (GHOST_MOVE_COUNTER + 3), a
        cp GHOST_MOVE_THRESHOLD
        ret c
        xor a
        ld (GHOST_MOVE_COUNTER + 3), a
        ld hl, GHOST_CLYDE_BASE
        call movement_ghost_step
        ret

; Input: HL = ghost record base. Chooses direction at current tile and
; moves one tile in the chosen direction. Checks reversal flags.
movement_ghost_step:
        ; Load state from record into ghost_ai work variables.
        ld a, (hl)                          ; X_TILE
        ld (GHOST_CHOICE_TILE_X), a
        inc hl
        ld a, (hl)                          ; Y_TILE
        ld (GHOST_CHOICE_TILE_Y), a
        inc hl
        ld a, (hl)                          ; DIR
        ld (GHOST_CHOICE_CURRENT_DIR), a
        inc hl
        ld a, (hl)                          ; MODE
        ex af, af'                          ; save MODE
        inc hl                              ; skip ID
        inc hl
        ld a, (hl)                          ; TARGET_X
        ld (GHOST_CHOICE_TARGET_X), a
        inc hl
        ld a, (hl)                          ; TARGET_Y
        ld (GHOST_CHOICE_TARGET_Y), a

        ; Rewind to record base, then fetch ID for reversal check.
        ld a, l
        sub 6
        ld l, a
        push hl                             ; save record base
        inc hl
        inc hl
        inc hl
        inc hl                              ; &ID
        ld a, (hl)
        call ghost_id_to_reversal_bit
        ld b, a
        ld a, (GHOST_REVERSAL_PENDING)
        and b
        jr z, .no_rev
        ld a, b
        cpl
        ld b, a
        ld a, (GHOST_REVERSAL_PENDING)
        and b
        ld (GHOST_REVERSAL_PENDING), a
        ld a, 1                             ; allow reversal
        jr .choose
.no_rev:
        xor a                               ; deny reversal
.choose:
        ld (GHOST_CHOICE_ALLOW_REVERSAL), a

        ex af, af'                          ; A = MODE
        cp GHOST_MODE_FRIGHTENED
        jr z, .frightened

        call ghost_choose_direction
        jr .apply
.frightened:
        ld a, (GHOST_CHOICE_TILE_X)
        ld b, a
        ld a, (GHOST_CHOICE_TILE_Y)
        ld c, a
        ld a, (GHOST_CHOICE_CURRENT_DIR)
        ld d, a
        ld a, (GHOST_CHOICE_ALLOW_REVERSAL)
        call ghost_choose_frightened_direction

.apply:
        cp MOVEMENT_DIR_NONE
        jr z, .done_pop

        ; Store DIR and CHOSEN_DIR into record.
        pop hl                              ; HL = record base
        push hl
        inc hl
        inc hl                              ; &DIR
        ld (hl), a
        inc hl
        inc hl
        inc hl
        inc hl
        inc hl                              ; &CHOSEN_DIR
        ld (hl), a
        ld d, a                             ; D = new direction

        ; Move one tile.
        pop hl                              ; HL = record base
        push hl                             ; &X_TILE

        cp MOVEMENT_DIR_LEFT
        jr z, .left
        cp MOVEMENT_DIR_RIGHT
        jr z, .right
        cp MOVEMENT_DIR_UP
        jr z, .up
        cp MOVEMENT_DIR_DOWN
        jr z, .down
        jr .done_pop

.left:
        ld a, (hl)
        or a
        jr nz, .left_dec
        inc hl
        ld a, (hl)
        cp 17
        dec hl
        jr nz, .done_pop
        ld a, MOVEMENT_MAZE_WIDTH - 1
        ld (hl), a
        jr .done_pop
.left_dec:
        dec (hl)
        jr .done_pop
.right:
        ld a, (hl)
        inc a
        cp MOVEMENT_MAZE_WIDTH
        jr c, .right_ok
        inc hl
        ld a, (hl)
        cp 17
        dec hl
        jr nz, .done_pop
        xor a
.right_ok:
        ld (hl), a
        jr .done_pop
.up:
        inc hl                              ; &Y_TILE
        ld a, (hl)
        or a                                ; Y == 0, at top edge
        jr z, .done_pop
        dec (hl)
        jr .done_pop
.down:
        inc hl                              ; &Y_TILE
        ld a, (hl)
        cp MOVEMENT_MAZE_HEIGHT - 1         ; Y >= 35, at bottom edge
        jr nc, .done_pop
        inc (hl)

.done_pop:
        pop hl
        ret

; Input: A = ghost ID (0-3). Output: A = 1 << ID (reversal bit mask).
ghost_id_to_reversal_bit:
        or a
        jr z, .id0
        ld b, a
        ld a, 1
.loop:
        add a, a
        djnz .loop
        ret
.id0:
        ld a, 1
        ret
