; Ghost-house release state for T012.
; This slice tracks release eligibility and exit decisions only. Movement,
; door pathing, rendering, scoring, and eaten-eyes routing remain separate.

GHOST_HOUSE_OUTSIDE          EQU 0
GHOST_HOUSE_WAITING          EQU 1
GHOST_HOUSE_PENDING_RELEASE  EQU 2
GHOST_HOUSE_EXITING          EQU 3

GHOST_HOUSE_RELEASE_NONE     EQU 0xFF
GHOST_HOUSE_REASON_NONE      EQU 0
GHOST_HOUSE_REASON_DOT       EQU 1
GHOST_HOUSE_REASON_TIMER     EQU 2

GHOST_HOUSE_PINKY_DOTS       EQU 0
GHOST_HOUSE_INKY_DOTS        EQU 30
GHOST_HOUSE_CLYDE_DOTS       EQU 60
GHOST_HOUSE_FALLBACK_FRAMES  EQU 240

GHOST_HOUSE_STATE_BASE       EQU 0x8220
GHOST_HOUSE_BLINKY_STATE     EQU GHOST_HOUSE_STATE_BASE + 0
GHOST_HOUSE_PINKY_STATE      EQU GHOST_HOUSE_STATE_BASE + 1
GHOST_HOUSE_INKY_STATE       EQU GHOST_HOUSE_STATE_BASE + 2
GHOST_HOUSE_CLYDE_STATE      EQU GHOST_HOUSE_STATE_BASE + 3
GHOST_HOUSE_BLINKY_DOTS      EQU GHOST_HOUSE_STATE_BASE + 4
GHOST_HOUSE_PINKY_DOT_COUNT  EQU GHOST_HOUSE_STATE_BASE + 5
GHOST_HOUSE_INKY_DOT_COUNT   EQU GHOST_HOUSE_STATE_BASE + 6
GHOST_HOUSE_CLYDE_DOT_COUNT  EQU GHOST_HOUSE_STATE_BASE + 7
GHOST_HOUSE_NEXT_GHOST       EQU GHOST_HOUSE_STATE_BASE + 8
GHOST_HOUSE_TIMER            EQU GHOST_HOUSE_STATE_BASE + 9
GHOST_HOUSE_RELEASE_PENDING  EQU GHOST_HOUSE_STATE_BASE + 11
GHOST_HOUSE_EXIT_PENDING     EQU GHOST_HOUSE_STATE_BASE + 12
GHOST_HOUSE_LAST_RELEASE     EQU GHOST_HOUSE_STATE_BASE + 13
GHOST_HOUSE_LAST_REASON      EQU GHOST_HOUSE_STATE_BASE + 14

ghost_house_init:
        ld a, GHOST_HOUSE_OUTSIDE
        ld (GHOST_HOUSE_BLINKY_STATE), a
        ld a, GHOST_HOUSE_WAITING
        ld (GHOST_HOUSE_PINKY_STATE), a
        ld (GHOST_HOUSE_INKY_STATE), a
        ld (GHOST_HOUSE_CLYDE_STATE), a
        xor a
        ld (GHOST_HOUSE_BLINKY_DOTS), a
        ld (GHOST_HOUSE_PINKY_DOT_COUNT), a
        ld (GHOST_HOUSE_INKY_DOT_COUNT), a
        ld (GHOST_HOUSE_CLYDE_DOT_COUNT), a
        ld (GHOST_HOUSE_RELEASE_PENDING), a
        ld (GHOST_HOUSE_EXIT_PENDING), a
        ld (GHOST_HOUSE_LAST_REASON), a
        ld hl, 0
        ld (GHOST_HOUSE_TIMER), hl
        ld a, GHOST_ID_PINKY
        ld (GHOST_HOUSE_NEXT_GHOST), a
        ld a, GHOST_HOUSE_RELEASE_NONE
        ld (GHOST_HOUSE_LAST_RELEASE), a
        jp ghost_house_try_dot_release

ghost_house_reset_after_life_loss:
        jp ghost_house_init

; Call only after T011 reports a real pellet or energizer consumption. Duplicate
; pellet attempts and non-dot frames must not enter this routine.
ghost_house_on_dot_event:
        ld hl, 0
        ld (GHOST_HOUSE_TIMER), hl

        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_PINKY
        jr z, .pinky
        cp GHOST_ID_INKY
        jr z, .inky
        cp GHOST_ID_CLYDE
        jr z, .clyde
        ret

.pinky:
        ld a, (GHOST_HOUSE_PINKY_STATE)
        cp GHOST_HOUSE_WAITING
        ret nz
        ld a, (GHOST_HOUSE_PINKY_DOT_COUNT)
        cp 0xFF
        jr z, .try_release
        inc a
        ld (GHOST_HOUSE_PINKY_DOT_COUNT), a
        jr .try_release

.inky:
        ld a, (GHOST_HOUSE_INKY_STATE)
        cp GHOST_HOUSE_WAITING
        ret nz
        ld a, (GHOST_HOUSE_INKY_DOT_COUNT)
        cp 0xFF
        jr z, .try_release
        inc a
        ld (GHOST_HOUSE_INKY_DOT_COUNT), a
        jr .try_release

.clyde:
        ld a, (GHOST_HOUSE_CLYDE_STATE)
        cp GHOST_HOUSE_WAITING
        ret nz
        ld a, (GHOST_HOUSE_CLYDE_DOT_COUNT)
        cp 0xFF
        jr z, .try_release
        inc a
        ld (GHOST_HOUSE_CLYDE_DOT_COUNT), a

.try_release:
        jp ghost_house_try_dot_release

ghost_house_tick:
        call ghost_house_next_is_waiting
        ret nc

        ld hl, (GHOST_HOUSE_TIMER)
        inc hl
        ld (GHOST_HOUSE_TIMER), hl
        ld de, GHOST_HOUSE_FALLBACK_FRAMES
        or a
        sbc hl, de
        ret c
        jp ghost_house_release_next_by_timer

; Output: carry set when the current release-order ghost is still waiting.
ghost_house_next_is_waiting:
        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_PINKY
        jr z, .pinky
        cp GHOST_ID_INKY
        jr z, .inky
        cp GHOST_ID_CLYDE
        jr z, .clyde
        or a
        ret
.pinky:
        ld a, (GHOST_HOUSE_PINKY_STATE)
        cp GHOST_HOUSE_WAITING
        scf
        ret z
        or a
        ret
.inky:
        ld a, (GHOST_HOUSE_INKY_STATE)
        cp GHOST_HOUSE_WAITING
        scf
        ret z
        or a
        ret
.clyde:
        ld a, (GHOST_HOUSE_CLYDE_STATE)
        cp GHOST_HOUSE_WAITING
        scf
        ret z
        or a
        ret

ghost_house_try_dot_release:
        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_PINKY
        jr z, .pinky
        cp GHOST_ID_INKY
        jr z, .inky
        cp GHOST_ID_CLYDE
        jr z, .clyde
        ret
.pinky:
        ld a, (GHOST_HOUSE_PINKY_STATE)
        cp GHOST_HOUSE_WAITING
        ret nz
        ld a, (GHOST_HOUSE_PINKY_DOT_COUNT)
        cp GHOST_HOUSE_PINKY_DOTS
        ret c
        jp ghost_house_release_pinky_by_dot
.inky:
        ld a, (GHOST_HOUSE_INKY_STATE)
        cp GHOST_HOUSE_WAITING
        ret nz
        ld a, (GHOST_HOUSE_INKY_DOT_COUNT)
        cp GHOST_HOUSE_INKY_DOTS
        ret c
        jp ghost_house_release_inky_by_dot
.clyde:
        ld a, (GHOST_HOUSE_CLYDE_STATE)
        cp GHOST_HOUSE_WAITING
        ret nz
        ld a, (GHOST_HOUSE_CLYDE_DOT_COUNT)
        cp GHOST_HOUSE_CLYDE_DOTS
        ret c
        jp ghost_house_release_clyde_by_dot

ghost_house_release_next_by_timer:
        ld hl, 0
        ld (GHOST_HOUSE_TIMER), hl
        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_PINKY
        jr z, ghost_house_release_pinky_by_timer
        cp GHOST_ID_INKY
        jr z, ghost_house_release_inky_by_timer
        cp GHOST_ID_CLYDE
        jr z, ghost_house_release_clyde_by_timer
        ret

ghost_house_release_pinky_by_dot:
        ld a, GHOST_HOUSE_REASON_DOT
        jr ghost_house_release_pinky
ghost_house_release_pinky_by_timer:
        ld a, GHOST_HOUSE_REASON_TIMER
ghost_house_release_pinky:
        ld (GHOST_HOUSE_LAST_REASON), a
        ld a, GHOST_HOUSE_PENDING_RELEASE
        ld (GHOST_HOUSE_PINKY_STATE), a
        ld a, GHOST_ID_PINKY
        ld (GHOST_HOUSE_LAST_RELEASE), a
        ld a, (GHOST_HOUSE_RELEASE_PENDING)
        or GHOST_REVERSAL_PINKY
        ld (GHOST_HOUSE_RELEASE_PENDING), a
        ret

ghost_house_release_inky_by_dot:
        ld a, GHOST_HOUSE_REASON_DOT
        jr ghost_house_release_inky
ghost_house_release_inky_by_timer:
        ld a, GHOST_HOUSE_REASON_TIMER
ghost_house_release_inky:
        ld (GHOST_HOUSE_LAST_REASON), a
        ld a, GHOST_HOUSE_PENDING_RELEASE
        ld (GHOST_HOUSE_INKY_STATE), a
        ld a, GHOST_ID_INKY
        ld (GHOST_HOUSE_LAST_RELEASE), a
        ld a, (GHOST_HOUSE_RELEASE_PENDING)
        or GHOST_REVERSAL_INKY
        ld (GHOST_HOUSE_RELEASE_PENDING), a
        ret

ghost_house_release_clyde_by_dot:
        ld a, GHOST_HOUSE_REASON_DOT
        jr ghost_house_release_clyde
ghost_house_release_clyde_by_timer:
        ld a, GHOST_HOUSE_REASON_TIMER
ghost_house_release_clyde:
        ld (GHOST_HOUSE_LAST_REASON), a
        ld a, GHOST_HOUSE_PENDING_RELEASE
        ld (GHOST_HOUSE_CLYDE_STATE), a
        ld a, GHOST_ID_CLYDE
        ld (GHOST_HOUSE_LAST_RELEASE), a
        ld a, (GHOST_HOUSE_RELEASE_PENDING)
        or GHOST_REVERSAL_CLYDE
        ld (GHOST_HOUSE_RELEASE_PENDING), a
        ret

; Moves the current pending-release ghost into the data-level exiting state.
; Output: A = ghost id that began exiting, or GHOST_HOUSE_RELEASE_NONE.
ghost_house_begin_next_exit:
        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_PINKY
        jr z, .pinky
        cp GHOST_ID_INKY
        jr z, .inky
        cp GHOST_ID_CLYDE
        jr z, .clyde
        ld a, GHOST_HOUSE_RELEASE_NONE
        ret
.pinky:
        ld a, (GHOST_HOUSE_PINKY_STATE)
        cp GHOST_HOUSE_PENDING_RELEASE
        jr nz, .none
        ld a, GHOST_HOUSE_EXITING
        ld (GHOST_HOUSE_PINKY_STATE), a
        ld a, (GHOST_HOUSE_EXIT_PENDING)
        or GHOST_REVERSAL_PINKY
        ld (GHOST_HOUSE_EXIT_PENDING), a
        ld a, GHOST_ID_PINKY
        ret
.inky:
        ld a, (GHOST_HOUSE_INKY_STATE)
        cp GHOST_HOUSE_PENDING_RELEASE
        jr nz, .none
        ld a, GHOST_HOUSE_EXITING
        ld (GHOST_HOUSE_INKY_STATE), a
        ld a, (GHOST_HOUSE_EXIT_PENDING)
        or GHOST_REVERSAL_INKY
        ld (GHOST_HOUSE_EXIT_PENDING), a
        ld a, GHOST_ID_INKY
        ret
.clyde:
        ld a, (GHOST_HOUSE_CLYDE_STATE)
        cp GHOST_HOUSE_PENDING_RELEASE
        jr nz, .none
        ld a, GHOST_HOUSE_EXITING
        ld (GHOST_HOUSE_CLYDE_STATE), a
        ld a, (GHOST_HOUSE_EXIT_PENDING)
        or GHOST_REVERSAL_CLYDE
        ld (GHOST_HOUSE_EXIT_PENDING), a
        ld a, GHOST_ID_CLYDE
        ret
.none:
        ld a, GHOST_HOUSE_RELEASE_NONE
        ret

; Input: A = ghost id whose later movement slice has completed the exit path.
ghost_house_complete_exit:
        cp GHOST_ID_PINKY
        jr z, .pinky
        cp GHOST_ID_INKY
        jr z, .inky
        cp GHOST_ID_CLYDE
        jr z, .clyde
        ret
.pinky:
        ld a, GHOST_HOUSE_OUTSIDE
        ld (GHOST_HOUSE_PINKY_STATE), a
        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_PINKY
        ret nz
        ld a, GHOST_ID_INKY
        ld (GHOST_HOUSE_NEXT_GHOST), a
        ret
.inky:
        ld a, GHOST_HOUSE_OUTSIDE
        ld (GHOST_HOUSE_INKY_STATE), a
        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_INKY
        ret nz
        ld a, GHOST_ID_CLYDE
        ld (GHOST_HOUSE_NEXT_GHOST), a
        ret
.clyde:
        ld a, GHOST_HOUSE_OUTSIDE
        ld (GHOST_HOUSE_CLYDE_STATE), a
        ld a, (GHOST_HOUSE_NEXT_GHOST)
        cp GHOST_ID_CLYDE
        ret nz
        ld a, GHOST_ID_CLYDE + 1
        ld (GHOST_HOUSE_NEXT_GHOST), a
        ret

ghost_house_clear_release_flags:
        xor a
        ld (GHOST_HOUSE_RELEASE_PENDING), a
        ld (GHOST_HOUSE_EXIT_PENDING), a
        ld (GHOST_HOUSE_LAST_REASON), a
        ld a, GHOST_HOUSE_RELEASE_NONE
        ld (GHOST_HOUSE_LAST_RELEASE), a
        ret
