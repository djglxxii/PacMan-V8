; Phase 6 game-flow state machine.
; This owner records a deterministic review path through the planned flow
; states without changing movement, collision, rendering, HUD, or audio rules.

GAME_FLOW_STATE_ATTRACT         EQU 0
GAME_FLOW_STATE_READY           EQU 1
GAME_FLOW_STATE_PLAYING         EQU 2
GAME_FLOW_STATE_DYING           EQU 3
GAME_FLOW_STATE_LEVEL_COMPLETE  EQU 4
GAME_FLOW_STATE_CONTINUE        EQU 5
GAME_FLOW_STATE_NEXT_LEVEL      EQU 6
GAME_FLOW_STATE_INTERMISSION    EQU 7

GAME_FLOW_FLAG_ATTRACT          EQU 0x01
GAME_FLOW_FLAG_READY            EQU 0x02
GAME_FLOW_FLAG_PLAYING          EQU 0x04
GAME_FLOW_FLAG_DYING            EQU 0x08
GAME_FLOW_FLAG_LEVEL_COMPLETE   EQU 0x10
GAME_FLOW_FLAG_CONTINUE         EQU 0x20
GAME_FLOW_FLAG_NEXT_LEVEL       EQU 0x40
GAME_FLOW_FLAG_INTERMISSION     EQU 0x80

GAME_FLOW_DURATION_ATTRACT      EQU 120
GAME_FLOW_DURATION_READY        EQU 240
GAME_FLOW_DURATION_PLAYING_DYING EQU 120
GAME_FLOW_DURATION_DYING        EQU 90
GAME_FLOW_DURATION_CONTINUE     EQU 60
GAME_FLOW_DURATION_PLAYING_LEVEL EQU 180
GAME_FLOW_DURATION_LEVEL_COMPLETE EQU 90
GAME_FLOW_DURATION_NEXT_LEVEL   EQU 60

GAME_FLOW_SCRIPT_DEATH          EQU 0
GAME_FLOW_SCRIPT_LEVEL_COMPLETE EQU 1
GAME_FLOW_SCRIPT_HANDOFF        EQU 2

GAME_FLOW_STATE_BASE            EQU 0x8250
GAME_FLOW_CURRENT_STATE         EQU GAME_FLOW_STATE_BASE + 0
GAME_FLOW_PREVIOUS_STATE        EQU GAME_FLOW_STATE_BASE + 1
GAME_FLOW_FRAME_COUNTER         EQU GAME_FLOW_STATE_BASE + 2
GAME_FLOW_STATE_TIMER           EQU GAME_FLOW_STATE_BASE + 4
GAME_FLOW_ENTRY_FRAME           EQU GAME_FLOW_STATE_BASE + 6
GAME_FLOW_LAST_TRANSITION_FRAME EQU GAME_FLOW_STATE_BASE + 8
GAME_FLOW_TRANSITION_COUNT      EQU GAME_FLOW_STATE_BASE + 10
GAME_FLOW_REVIEW_FLAGS          EQU GAME_FLOW_STATE_BASE + 11
GAME_FLOW_SCRIPT_STEP           EQU GAME_FLOW_STATE_BASE + 12

game_flow_init:
        xor a
        ld (GAME_FLOW_FRAME_COUNTER), a
        ld (GAME_FLOW_FRAME_COUNTER + 1), a
        ld (GAME_FLOW_PREVIOUS_STATE), a
        ld (GAME_FLOW_TRANSITION_COUNT), a
        ld (GAME_FLOW_SCRIPT_STEP), a
        ld hl, 0
        ld (GAME_FLOW_ENTRY_FRAME), hl
        ld hl, 0xFFFF
        ld (GAME_FLOW_LAST_TRANSITION_FRAME), hl
        ld a, GAME_FLOW_STATE_ATTRACT
        ld (GAME_FLOW_CURRENT_STATE), a
        ld a, GAME_FLOW_FLAG_ATTRACT
        ld (GAME_FLOW_REVIEW_FLAGS), a
        ld hl, GAME_FLOW_DURATION_ATTRACT
        ld (GAME_FLOW_STATE_TIMER), hl
        ret

game_flow_update_frame:
        ld hl, (GAME_FLOW_FRAME_COUNTER)
        inc hl
        ld (GAME_FLOW_FRAME_COUNTER), hl

        ld a, (GAME_FLOW_CURRENT_STATE)
        cp GAME_FLOW_STATE_INTERMISSION
        ret z

        ld hl, (GAME_FLOW_STATE_TIMER)
        ld a, h
        or l
        ret z
        ld a, l
        or a
        jr nz, .decrement_low
        dec h
        ld l, 0xFF
        jr .timer_decremented
.decrement_low:
        dec l
.timer_decremented:
        ld (GAME_FLOW_STATE_TIMER), hl
        ld a, h
        or l
        ret nz
        jp game_flow_elapsed_transition

game_flow_elapsed_transition:
        ld a, (GAME_FLOW_CURRENT_STATE)
        cp GAME_FLOW_STATE_ATTRACT
        jr z, .to_ready
        cp GAME_FLOW_STATE_READY
        jr z, .to_playing
        cp GAME_FLOW_STATE_PLAYING
        jr z, .from_playing
        cp GAME_FLOW_STATE_DYING
        jr z, .to_continue
        cp GAME_FLOW_STATE_CONTINUE
        jr z, .to_playing
        cp GAME_FLOW_STATE_LEVEL_COMPLETE
        jr z, .to_next_level
        cp GAME_FLOW_STATE_NEXT_LEVEL
        jr z, .to_intermission
        ret

.to_ready:
        ld a, GAME_FLOW_STATE_READY
        jp game_flow_transition_to
.to_playing:
        ld a, GAME_FLOW_STATE_PLAYING
        jp game_flow_transition_to
.to_continue:
        ld a, GAME_FLOW_STATE_CONTINUE
        jp game_flow_transition_to
.to_next_level:
        ld a, GAME_FLOW_STATE_NEXT_LEVEL
        jp game_flow_transition_to
.to_intermission:
        ld a, GAME_FLOW_SCRIPT_HANDOFF
        ld (GAME_FLOW_SCRIPT_STEP), a
        ld a, GAME_FLOW_STATE_INTERMISSION
        jp game_flow_transition_to

.from_playing:
        ld a, (GAME_FLOW_SCRIPT_STEP)
        cp GAME_FLOW_SCRIPT_DEATH
        jr nz, .playing_to_level_complete
        ld a, GAME_FLOW_SCRIPT_LEVEL_COMPLETE
        ld (GAME_FLOW_SCRIPT_STEP), a
        ld a, GAME_FLOW_STATE_DYING
        jp game_flow_transition_to
.playing_to_level_complete:
        ld a, GAME_FLOW_SCRIPT_HANDOFF
        ld (GAME_FLOW_SCRIPT_STEP), a
        ld a, GAME_FLOW_STATE_LEVEL_COMPLETE
        jp game_flow_transition_to

; Input: A = next game-flow state.
game_flow_transition_to:
        ld b, a
        ld a, (GAME_FLOW_CURRENT_STATE)
        ld (GAME_FLOW_PREVIOUS_STATE), a
        ld a, b
        ld (GAME_FLOW_CURRENT_STATE), a
        ld hl, (GAME_FLOW_FRAME_COUNTER)
        ld (GAME_FLOW_LAST_TRANSITION_FRAME), hl
        ld (GAME_FLOW_ENTRY_FRAME), hl
        ld a, (GAME_FLOW_TRANSITION_COUNT)
        inc a
        ld (GAME_FLOW_TRANSITION_COUNT), a
        ld a, b
        call game_flow_mark_state_seen
        ld a, b
        jp game_flow_load_state_timer

; Input: A = current state.
game_flow_load_state_timer:
        cp GAME_FLOW_STATE_ATTRACT
        jr z, .attract
        cp GAME_FLOW_STATE_READY
        jr z, .ready
        cp GAME_FLOW_STATE_PLAYING
        jr z, .playing
        cp GAME_FLOW_STATE_DYING
        jr z, .dying
        cp GAME_FLOW_STATE_CONTINUE
        jr z, .continue
        cp GAME_FLOW_STATE_LEVEL_COMPLETE
        jr z, .level_complete
        cp GAME_FLOW_STATE_NEXT_LEVEL
        jr z, .next_level
        ld hl, 0
        jr .store
.attract:
        ld hl, GAME_FLOW_DURATION_ATTRACT
        jr .store
.ready:
        ld hl, GAME_FLOW_DURATION_READY
        jr .store
.playing:
        ld a, (GAME_FLOW_SCRIPT_STEP)
        cp GAME_FLOW_SCRIPT_LEVEL_COMPLETE
        jr z, .playing_level
        ld hl, GAME_FLOW_DURATION_PLAYING_DYING
        jr .store
.playing_level:
        ld hl, GAME_FLOW_DURATION_PLAYING_LEVEL
        jr .store
.dying:
        ld hl, GAME_FLOW_DURATION_DYING
        jr .store
.continue:
        ld hl, GAME_FLOW_DURATION_CONTINUE
        jr .store
.level_complete:
        ld hl, GAME_FLOW_DURATION_LEVEL_COMPLETE
        jr .store
.next_level:
        ld hl, GAME_FLOW_DURATION_NEXT_LEVEL
.store:
        ld (GAME_FLOW_STATE_TIMER), hl
        ret

; Input: A = state to mark in GAME_FLOW_REVIEW_FLAGS.
game_flow_mark_state_seen:
        cp GAME_FLOW_STATE_ATTRACT
        jr z, .attract
        cp GAME_FLOW_STATE_READY
        jr z, .ready
        cp GAME_FLOW_STATE_PLAYING
        jr z, .playing
        cp GAME_FLOW_STATE_DYING
        jr z, .dying
        cp GAME_FLOW_STATE_LEVEL_COMPLETE
        jr z, .level_complete
        cp GAME_FLOW_STATE_CONTINUE
        jr z, .continue
        cp GAME_FLOW_STATE_NEXT_LEVEL
        jr z, .next_level
        cp GAME_FLOW_STATE_INTERMISSION
        jr z, .intermission
        ret
.attract:
        ld b, GAME_FLOW_FLAG_ATTRACT
        jr .or_flag
.ready:
        ld b, GAME_FLOW_FLAG_READY
        jr .or_flag
.playing:
        ld b, GAME_FLOW_FLAG_PLAYING
        jr .or_flag
.dying:
        ld b, GAME_FLOW_FLAG_DYING
        jr .or_flag
.level_complete:
        ld b, GAME_FLOW_FLAG_LEVEL_COMPLETE
        jr .or_flag
.continue:
        ld b, GAME_FLOW_FLAG_CONTINUE
        jr .or_flag
.next_level:
        ld b, GAME_FLOW_FLAG_NEXT_LEVEL
        jr .or_flag
.intermission:
        ld b, GAME_FLOW_FLAG_INTERMISSION
.or_flag:
        ld a, (GAME_FLOW_REVIEW_FLAGS)
        or b
        ld (GAME_FLOW_REVIEW_FLAGS), a
        ret
