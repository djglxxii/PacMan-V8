; AY-3-8910 PSG sound-effect engine for T016.
; Effects are re-authored square-wave approximations.  The deterministic
; review script starts after boot and exercises each cue through VBlank ticks.

PSG_ADDR_PORT               EQU 0x50
PSG_DATA_PORT               EQU 0x51

PSG_REG_A_FINE              EQU 0
PSG_REG_A_COARSE            EQU 1
PSG_REG_B_FINE              EQU 2
PSG_REG_B_COARSE            EQU 3
PSG_REG_C_FINE              EQU 4
PSG_REG_C_COARSE            EQU 5
PSG_REG_NOISE               EQU 6
PSG_REG_MIXER               EQU 7
PSG_REG_A_VOLUME            EQU 8
PSG_REG_B_VOLUME            EQU 9
PSG_REG_C_VOLUME            EQU 10
PSG_REG_ENV_FINE            EQU 11
PSG_REG_ENV_COARSE          EQU 12
PSG_REG_ENV_SHAPE           EQU 13

PSG_MIXER_TONE_AB           EQU 0x3C    ; Tone A+B enabled, C/noise disabled.

AUDIO_EFFECT_NONE           EQU 0
AUDIO_EFFECT_WAKA           EQU 1
AUDIO_EFFECT_PELLET         EQU 2
AUDIO_EFFECT_SIREN          EQU 3
AUDIO_EFFECT_GHOST_EATEN    EQU 4
AUDIO_EFFECT_EXTRA_LIFE     EQU 5

AUDIO_STATE_BASE            EQU 0x8230
AUDIO_FRAME_COUNTER         EQU AUDIO_STATE_BASE + 0
AUDIO_CH_A_EFFECT           EQU AUDIO_STATE_BASE + 2
AUDIO_CH_A_TIMER            EQU AUDIO_STATE_BASE + 3
AUDIO_CH_A_PTR              EQU AUDIO_STATE_BASE + 4
AUDIO_CH_B_EFFECT           EQU AUDIO_STATE_BASE + 6
AUDIO_CH_B_TIMER            EQU AUDIO_STATE_BASE + 7
AUDIO_CH_B_PTR              EQU AUDIO_STATE_BASE + 8

audio_init:
        xor a
        ld (AUDIO_FRAME_COUNTER), a
        ld (AUDIO_FRAME_COUNTER + 1), a
        ld (AUDIO_CH_A_EFFECT), a
        ld (AUDIO_CH_A_TIMER), a
        ld (AUDIO_CH_B_EFFECT), a
        ld (AUDIO_CH_B_TIMER), a

        ld b, PSG_REG_A_FINE
        ld c, 0x01
        call audio_psg_write_bc
        ld b, PSG_REG_A_COARSE
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_B_FINE
        ld c, 0x01
        call audio_psg_write_bc
        ld b, PSG_REG_B_COARSE
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_C_FINE
        ld c, 0x01
        call audio_psg_write_bc
        ld b, PSG_REG_C_COARSE
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_NOISE
        ld c, 0x1F
        call audio_psg_write_bc
        ld b, PSG_REG_MIXER
        ld c, PSG_MIXER_TONE_AB
        call audio_psg_write_bc
        ld b, PSG_REG_A_VOLUME
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_B_VOLUME
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_C_VOLUME
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_ENV_FINE
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_ENV_COARSE
        ld c, 0x00
        call audio_psg_write_bc
        ld b, PSG_REG_ENV_SHAPE
        ld c, 0x00
        jp audio_psg_write_bc

audio_update_frame:
        call audio_review_script
        call audio_update_channel_a
        call audio_update_channel_b
        ld hl, (AUDIO_FRAME_COUNTER)
        inc hl
        ld (AUDIO_FRAME_COUNTER), hl
        ret

audio_review_script:
        ld hl, (AUDIO_FRAME_COUNTER)
        ld a, h
        or a
        ret nz
        ld a, l
        or a
        jp z, audio_trigger_siren
        cp 12
        jp z, audio_trigger_pellet
        cp 36
        jp z, audio_trigger_waka
        cp 72
        jp z, audio_trigger_ghost_eaten
        cp 112
        jp z, audio_trigger_extra_life
        ret

audio_trigger_waka:
        ld hl, audio_waka_steps
        ld a, AUDIO_EFFECT_WAKA
        jp audio_start_channel_a

audio_trigger_pellet:
        ld hl, audio_pellet_steps
        ld a, AUDIO_EFFECT_PELLET
        jp audio_start_channel_a

audio_trigger_siren:
        ld hl, audio_siren_steps
        ld a, AUDIO_EFFECT_SIREN
        jp audio_start_channel_b

audio_trigger_ghost_eaten:
        ld hl, audio_ghost_eaten_steps
        ld a, AUDIO_EFFECT_GHOST_EATEN
        jp audio_start_channel_a

audio_trigger_extra_life:
        ld hl, audio_extra_life_a_steps
        ld a, AUDIO_EFFECT_EXTRA_LIFE
        call audio_start_channel_a
        ld hl, audio_extra_life_b_steps
        ld a, AUDIO_EFFECT_EXTRA_LIFE
        jp audio_start_channel_b

audio_start_channel_a:
        ld (AUDIO_CH_A_PTR), hl
        ld (AUDIO_CH_A_EFFECT), a
        xor a
        ld (AUDIO_CH_A_TIMER), a
        ret

audio_start_channel_b:
        ld (AUDIO_CH_B_PTR), hl
        ld (AUDIO_CH_B_EFFECT), a
        xor a
        ld (AUDIO_CH_B_TIMER), a
        ret

audio_update_channel_a:
        ld a, (AUDIO_CH_A_EFFECT)
        or a
        ret z
        ld a, (AUDIO_CH_A_TIMER)
        or a
        jr z, .load_step
        dec a
        ld (AUDIO_CH_A_TIMER), a
        ret
.load_step:
        ld hl, (AUDIO_CH_A_PTR)
        ld a, (hl)
        or a
        jr z, .stop
        ld d, a
        inc hl
        ld b, PSG_REG_A_FINE
        ld c, (hl)
        call audio_psg_write_bc
        inc hl
        ld b, PSG_REG_A_COARSE
        ld c, (hl)
        call audio_psg_write_bc
        inc hl
        ld b, PSG_REG_A_VOLUME
        ld c, (hl)
        call audio_psg_write_bc
        inc hl
        ld (AUDIO_CH_A_PTR), hl
        ld a, d
        dec a
        ld (AUDIO_CH_A_TIMER), a
        ret
.stop:
        xor a
        ld (AUDIO_CH_A_EFFECT), a
        ld (AUDIO_CH_A_TIMER), a
        ld b, PSG_REG_A_VOLUME
        ld c, 0x00
        jp audio_psg_write_bc

audio_update_channel_b:
        ld a, (AUDIO_CH_B_EFFECT)
        or a
        ret z
        ld a, (AUDIO_CH_B_TIMER)
        or a
        jr z, .load_step
        dec a
        ld (AUDIO_CH_B_TIMER), a
        ret
.load_step:
        ld hl, (AUDIO_CH_B_PTR)
        ld a, (hl)
        or a
        jr z, .stop
        ld d, a
        inc hl
        ld b, PSG_REG_B_FINE
        ld c, (hl)
        call audio_psg_write_bc
        inc hl
        ld b, PSG_REG_B_COARSE
        ld c, (hl)
        call audio_psg_write_bc
        inc hl
        ld b, PSG_REG_B_VOLUME
        ld c, (hl)
        call audio_psg_write_bc
        inc hl
        ld (AUDIO_CH_B_PTR), hl
        ld a, d
        dec a
        ld (AUDIO_CH_B_TIMER), a
        ret
.stop:
        xor a
        ld (AUDIO_CH_B_EFFECT), a
        ld (AUDIO_CH_B_TIMER), a
        ld b, PSG_REG_B_VOLUME
        ld c, 0x00
        jp audio_psg_write_bc

audio_psg_write_bc:
        ld a, b
        out (PSG_ADDR_PORT), a
        ld a, c
        out (PSG_DATA_PORT), a
        ret

; Step format: duration_frames, tone_period_fine, tone_period_coarse, volume.
; A zero duration terminates the effect and mutes the owning channel.

audio_waka_steps:
        db 4, 0xF0, 0x00, 0x0D
        db 4, 0xB4, 0x00, 0x0F
        db 4, 0xF0, 0x00, 0x0C
        db 4, 0xB4, 0x00, 0x0E
        db 0

audio_pellet_steps:
        db 2, 0x80, 0x01, 0x0A
        db 2, 0x20, 0x01, 0x0C
        db 2, 0xD8, 0x00, 0x0B
        db 2, 0xA8, 0x00, 0x09
        db 0

audio_siren_steps:
        db 8, 0x40, 0x01, 0x08
        db 8, 0x18, 0x01, 0x09
        db 8, 0xF0, 0x00, 0x0A
        db 8, 0x18, 0x01, 0x09
        db 8, 0x40, 0x01, 0x08
        db 8, 0x68, 0x01, 0x09
        db 8, 0x90, 0x01, 0x0A
        db 8, 0x68, 0x01, 0x09
        db 8, 0x40, 0x01, 0x08
        db 8, 0x18, 0x01, 0x09
        db 8, 0xF0, 0x00, 0x0A
        db 8, 0x18, 0x01, 0x08
        db 0

audio_ghost_eaten_steps:
        db 3, 0x80, 0x00, 0x0F
        db 3, 0xA0, 0x00, 0x0F
        db 3, 0xC8, 0x00, 0x0E
        db 3, 0xF8, 0x00, 0x0D
        db 3, 0x30, 0x01, 0x0B
        db 3, 0x80, 0x01, 0x09
        db 0

audio_extra_life_a_steps:
        db 5, 0xC0, 0x01, 0x0C
        db 5, 0x60, 0x01, 0x0D
        db 5, 0x00, 0x01, 0x0F
        db 5, 0xC0, 0x00, 0x0E
        db 5, 0x90, 0x00, 0x0C
        db 0

audio_extra_life_b_steps:
        db 5, 0x50, 0x01, 0x08
        db 5, 0x08, 0x01, 0x09
        db 5, 0xC0, 0x00, 0x0A
        db 5, 0x90, 0x00, 0x09
        db 5, 0x6C, 0x00, 0x08
        db 0
