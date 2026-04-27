; Boot-time and game-over → new-game state initialization for T023.
; Composes level, ghost, ghost-house, collision, and movement inits,
; then sets SCORE/LIVES. Removes the LOW-3 debug ghost-mode mix from the
; boot path.
;
; RAM claimed by this module:
;   0x8241–0x8244  GAME_STATE_SCORE  (4 bytes, little-endian)
;   0x8245         GAME_STATE_LIVES  (1 byte)
;   0x8246–0x824F  reserved (future expansion)
;
; Placed immediately after AUDIO_STATE_BASE (0x8230, extends to 0x8240)
; and before GAME_FLOW_STATE_BASE (0x8250).  LEVEL is stored at
; LEVEL_CURRENT_NUMBER (0x8260) by level_progression_init — no separate
; LEVEL byte is allocated here.

GAME_STATE_BASE     EQU 0x8241
GAME_STATE_SCORE    EQU GAME_STATE_BASE + 0    ; 4 bytes, little-endian
GAME_STATE_LIVES    EQU GAME_STATE_BASE + 4    ; 1 byte

game_state_init:
        call level_progression_init     ; sets LEVEL_CURRENT_NUMBER = 1
        call movement_init_pacman
        call ghost_init_state           ; calls ghost_mode_init + ghost_house_init
        call collision_init

        xor a
        ld (GAME_STATE_SCORE), a
        ld (GAME_STATE_SCORE + 1), a
        ld (GAME_STATE_SCORE + 2), a
        ld (GAME_STATE_SCORE + 3), a

        ld a, 3
        ld (GAME_STATE_LIVES), a
        ret
