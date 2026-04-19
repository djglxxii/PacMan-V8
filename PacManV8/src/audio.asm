; AY-3-8910 PSG effects and YM2151 FM music engine for Phase 5 audio.
; Sounds are re-authored approximations.  The deterministic review script
; starts after boot and exercises each cue through VBlank ticks.

PSG_ADDR_PORT               EQU 0x50
PSG_DATA_PORT               EQU 0x51
YM_ADDR_PORT                EQU 0x40
YM_DATA_PORT                EQU 0x41

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

YM_REG_KEY_ON               EQU 0x08
YM_REG_CHANNEL_BASE         EQU 0x20
YM_REG_KEY_CODE_BASE        EQU 0x28
YM_REG_KEY_FRACTION_BASE    EQU 0x30
YM_REG_OPERATOR_TL_BASE     EQU 0x60
YM_KEY_ALL_OPERATORS        EQU 0x78
YM_REST                     EQU 0xFF
YM_TL_MUTE                  EQU 0x7F

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
AUDIO_MUSIC_EFFECT          EQU AUDIO_STATE_BASE + 10
AUDIO_MUSIC_TIMER           EQU AUDIO_STATE_BASE + 11
AUDIO_MUSIC_PTR             EQU AUDIO_STATE_BASE + 12
AUDIO_FM_TMP_CH             EQU AUDIO_STATE_BASE + 14
AUDIO_FM_TMP_KEY            EQU AUDIO_STATE_BASE + 15
AUDIO_FM_TMP_LEVEL          EQU AUDIO_STATE_BASE + 16

AUDIO_MUSIC_NONE            EQU 0
AUDIO_MUSIC_INTRO           EQU 1
AUDIO_MUSIC_INTERMISSION    EQU 2
AUDIO_MUSIC_DEATH           EQU 3

audio_init:
        xor a
        ld (AUDIO_FRAME_COUNTER), a
        ld (AUDIO_FRAME_COUNTER + 1), a
        ld (AUDIO_CH_A_EFFECT), a
        ld (AUDIO_CH_A_TIMER), a
        ld (AUDIO_CH_B_EFFECT), a
        ld (AUDIO_CH_B_TIMER), a
        ld (AUDIO_MUSIC_EFFECT), a
        ld (AUDIO_MUSIC_TIMER), a

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
        call audio_psg_write_bc
        jp audio_fm_init

audio_update_frame:
        call audio_review_script
        call audio_update_channel_a
        call audio_update_channel_b
        call audio_update_music
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
        cp 144
        jp z, audio_trigger_intro_music
        cp 196
        jp z, audio_trigger_intermission_music
        cp 240
        jp z, audio_trigger_death_music
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

audio_trigger_intro_music:
        ld hl, audio_fm_intro_rows
        ld a, AUDIO_MUSIC_INTRO
        jp audio_start_music

audio_trigger_intermission_music:
        ld hl, audio_fm_intermission_rows
        ld a, AUDIO_MUSIC_INTERMISSION
        jp audio_start_music

audio_trigger_death_music:
        ld hl, audio_fm_death_rows
        ld a, AUDIO_MUSIC_DEATH
        jp audio_start_music

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

audio_fm_init:
        ld hl, audio_fm_init_table
.loop:
        ld a, (hl)
        inc hl
        cp YM_REST
        ret z
        ld b, a
        ld c, (hl)
        inc hl
        call audio_ym_write_bc
        jr .loop

audio_start_music:
        ld (AUDIO_MUSIC_PTR), hl
        ld (AUDIO_MUSIC_EFFECT), a
        xor a
        ld (AUDIO_MUSIC_TIMER), a
        ret

audio_update_music:
        ld a, (AUDIO_MUSIC_EFFECT)
        or a
        ret z
        ld a, (AUDIO_MUSIC_TIMER)
        or a
        jr z, .load_row
        dec a
        ld (AUDIO_MUSIC_TIMER), a
        ret
.load_row:
        ld hl, (AUDIO_MUSIC_PTR)
        ld a, (hl)
        or a
        jr z, .stop
        ld d, a
        inc hl

        ld e, (hl)
        inc hl
        ld c, (hl)
        inc hl
        xor a
        push hl
        call audio_fm_apply_channel
        pop hl

        ld e, (hl)
        inc hl
        ld c, (hl)
        inc hl
        ld a, 0x01
        push hl
        call audio_fm_apply_channel
        pop hl

        ld e, (hl)
        inc hl
        ld c, (hl)
        inc hl
        ld a, 0x02
        push hl
        call audio_fm_apply_channel
        pop hl

        ld e, (hl)
        inc hl
        ld c, (hl)
        inc hl
        ld a, 0x03
        push hl
        call audio_fm_apply_channel
        pop hl

        ld (AUDIO_MUSIC_PTR), hl
        ld a, d
        dec a
        ld (AUDIO_MUSIC_TIMER), a
        ret
.stop:
        xor a
        ld (AUDIO_MUSIC_EFFECT), a
        ld (AUDIO_MUSIC_TIMER), a
        ld a, 0x00
        call audio_fm_mute_channel
        ld a, 0x01
        call audio_fm_mute_channel
        ld a, 0x02
        call audio_fm_mute_channel
        ld a, 0x03
        jp audio_fm_mute_channel

audio_fm_apply_channel:
        ld (AUDIO_FM_TMP_CH), a
        ld a, e
        ld (AUDIO_FM_TMP_KEY), a
        ld a, c
        ld (AUDIO_FM_TMP_LEVEL), a
        ld a, (AUDIO_FM_TMP_KEY)
        cp YM_REST
        jr z, .mute

        ld b, YM_REG_KEY_ON
        ld a, (AUDIO_FM_TMP_CH)
        ld c, a
        call audio_ym_write_bc

        ld a, (AUDIO_FM_TMP_CH)
        add a, YM_REG_KEY_CODE_BASE
        ld b, a
        ld a, (AUDIO_FM_TMP_KEY)
        ld c, a
        call audio_ym_write_bc

        ld a, (AUDIO_FM_TMP_CH)
        add a, YM_REG_KEY_FRACTION_BASE
        ld b, a
        ld c, 0x00
        call audio_ym_write_bc

        call audio_fm_write_tmp_level

        ld b, YM_REG_KEY_ON
        ld a, (AUDIO_FM_TMP_CH)
        or YM_KEY_ALL_OPERATORS
        ld c, a
        jp audio_ym_write_bc
.mute:
        ld a, (AUDIO_FM_TMP_CH)
        jp audio_fm_mute_channel

audio_fm_mute_channel:
        ld (AUDIO_FM_TMP_CH), a
        ld b, YM_REG_KEY_ON
        ld a, (AUDIO_FM_TMP_CH)
        ld c, a
        call audio_ym_write_bc
        ld a, YM_TL_MUTE
        ld (AUDIO_FM_TMP_LEVEL), a
        jp audio_fm_write_tmp_level

audio_fm_write_tmp_level:
        ld a, (AUDIO_FM_TMP_CH)
        add a, YM_REG_OPERATOR_TL_BASE
        ld b, a
        ld a, (AUDIO_FM_TMP_LEVEL)
        ld c, a
        call audio_ym_write_bc
        ld a, b
        add a, 0x08
        ld b, a
        ld a, (AUDIO_FM_TMP_LEVEL)
        ld c, a
        call audio_ym_write_bc
        ld a, b
        add a, 0x08
        ld b, a
        ld a, (AUDIO_FM_TMP_LEVEL)
        ld c, a
        call audio_ym_write_bc
        ld a, b
        add a, 0x08
        ld b, a
        ld a, (AUDIO_FM_TMP_LEVEL)
        ld c, a
        jp audio_ym_write_bc

audio_ym_write_bc:
.wait_address:
        in a, (YM_ADDR_PORT)
        and 0x80
        jr nz, .wait_address
        ld a, b
        out (YM_ADDR_PORT), a
.wait_data:
        in a, (YM_ADDR_PORT)
        and 0x80
        jr nz, .wait_data
        ld a, c
        out (YM_DATA_PORT), a
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

; YM2151 init table: register, value pairs terminated by 0xFF.
; Channels 0-3 are melodic review voices. Channels 4-7 are explicitly muted.

audio_fm_init_table:
        db 0x14, 0x00, 0x18, 0x00, 0x19, 0x00, 0x1B, 0x00, 0x0F, 0x00
        db 0x08, 0x00, 0x08, 0x01, 0x08, 0x02, 0x08, 0x03
        db 0x08, 0x04, 0x08, 0x05, 0x08, 0x06, 0x08, 0x07
        db 0x20, 0xC7, 0x21, 0xC7, 0x22, 0xC7, 0x23, 0xC7
        db 0x24, 0xC7, 0x25, 0xC7, 0x26, 0xC7, 0x27, 0xC7
        db 0x30, 0x00, 0x31, 0x00, 0x32, 0x00, 0x33, 0x00
        db 0x34, 0x00, 0x35, 0x00, 0x36, 0x00, 0x37, 0x00
        db 0x38, 0x00, 0x39, 0x00, 0x3A, 0x00, 0x3B, 0x00
        db 0x3C, 0x00, 0x3D, 0x00, 0x3E, 0x00, 0x3F, 0x00
        db 0x40, 0x01, 0x48, 0x02, 0x50, 0x03, 0x58, 0x01
        db 0x41, 0x01, 0x49, 0x02, 0x51, 0x03, 0x59, 0x01
        db 0x42, 0x01, 0x4A, 0x02, 0x52, 0x03, 0x5A, 0x01
        db 0x43, 0x01, 0x4B, 0x02, 0x53, 0x03, 0x5B, 0x01
        db 0x60, 0x7F, 0x68, 0x7F, 0x70, 0x7F, 0x78, 0x7F
        db 0x61, 0x7F, 0x69, 0x7F, 0x71, 0x7F, 0x79, 0x7F
        db 0x62, 0x7F, 0x6A, 0x7F, 0x72, 0x7F, 0x7A, 0x7F
        db 0x63, 0x7F, 0x6B, 0x7F, 0x73, 0x7F, 0x7B, 0x7F
        db 0x64, 0x7F, 0x6C, 0x7F, 0x74, 0x7F, 0x7C, 0x7F
        db 0x65, 0x7F, 0x6D, 0x7F, 0x75, 0x7F, 0x7D, 0x7F
        db 0x66, 0x7F, 0x6E, 0x7F, 0x76, 0x7F, 0x7E, 0x7F
        db 0x67, 0x7F, 0x6F, 0x7F, 0x77, 0x7F, 0x7F, 0x7F
        db 0x80, 0x1F, 0x88, 0x1F, 0x90, 0x1F, 0x98, 0x1F
        db 0x81, 0x1F, 0x89, 0x1F, 0x91, 0x1F, 0x99, 0x1F
        db 0x82, 0x1F, 0x8A, 0x1F, 0x92, 0x1F, 0x9A, 0x1F
        db 0x83, 0x1F, 0x8B, 0x1F, 0x93, 0x1F, 0x9B, 0x1F
        db 0xA0, 0x08, 0xA8, 0x08, 0xB0, 0x06, 0xB8, 0x06
        db 0xA1, 0x08, 0xA9, 0x08, 0xB1, 0x06, 0xB9, 0x06
        db 0xA2, 0x08, 0xAA, 0x08, 0xB2, 0x06, 0xBA, 0x06
        db 0xA3, 0x08, 0xAB, 0x08, 0xB3, 0x06, 0xBB, 0x06
        db 0xC0, 0x04, 0xC8, 0x04, 0xD0, 0x03, 0xD8, 0x03
        db 0xC1, 0x04, 0xC9, 0x04, 0xD1, 0x03, 0xD9, 0x03
        db 0xC2, 0x04, 0xCA, 0x04, 0xD2, 0x03, 0xDA, 0x03
        db 0xC3, 0x04, 0xCB, 0x04, 0xD3, 0x03, 0xDB, 0x03
        db 0xE0, 0x0F, 0xE8, 0x0F, 0xF0, 0x0F, 0xF8, 0x0F
        db 0xE1, 0x0F, 0xE9, 0x0F, 0xF1, 0x0F, 0xF9, 0x0F
        db 0xE2, 0x0F, 0xEA, 0x0F, 0xF2, 0x0F, 0xFA, 0x0F
        db 0xE3, 0x0F, 0xEB, 0x0F, 0xF3, 0x0F, 0xFB, 0x0F
        db 0xFF

; FM row format: duration_frames, then four channel pairs of key_code, level.
; Key code 0xFF rests/mutes the channel for that row.  Lower level is louder.

audio_fm_intro_rows:
        db 6, 0x4B, 0x28, 0x37, 0x38, 0x24, 0x42, YM_REST, 0x7F
        db 6, 0x50, 0x24, 0x39, 0x36, 0x27, 0x40, YM_REST, 0x7F
        db 6, 0x52, 0x24, 0x3B, 0x34, 0x29, 0x3E, YM_REST, 0x7F
        db 6, 0x57, 0x22, 0x40, 0x34, 0x2B, 0x3C, YM_REST, 0x7F
        db 6, 0x54, 0x24, 0x3B, 0x36, 0x2C, 0x40, YM_REST, 0x7F
        db 6, 0x50, 0x26, 0x39, 0x38, 0x29, 0x42, YM_REST, 0x7F
        db 6, 0x52, 0x24, 0x3B, 0x36, 0x27, 0x40, YM_REST, 0x7F
        db 6, 0x4B, 0x2C, 0x37, 0x3C, 0x24, 0x48, YM_REST, 0x7F
        db 0

audio_fm_intermission_rows:
        db 5, 0x47, 0x2A, 0x3B, 0x38, 0x30, 0x42, 0x27, 0x4A
        db 5, 0x4B, 0x28, 0x40, 0x36, 0x33, 0x42, 0x2B, 0x48
        db 5, 0x50, 0x26, 0x43, 0x34, 0x37, 0x40, 0x30, 0x46
        db 5, 0x52, 0x24, 0x47, 0x34, 0x39, 0x40, 0x33, 0x46
        db 5, 0x54, 0x26, 0x49, 0x36, 0x3B, 0x42, 0x37, 0x48
        db 5, 0x52, 0x28, 0x47, 0x38, 0x39, 0x44, 0x33, 0x4A
        db 5, 0x50, 0x2A, 0x43, 0x3A, 0x37, 0x46, 0x30, 0x4C
        db 5, 0x4B, 0x30, 0x40, 0x40, 0x33, 0x4A, 0x2B, 0x50
        db 0

audio_fm_death_rows:
        db 4, 0x57, 0x20, 0x43, 0x34, 0x37, 0x40, YM_REST, 0x7F
        db 4, 0x56, 0x22, 0x42, 0x36, 0x36, 0x42, YM_REST, 0x7F
        db 4, 0x54, 0x26, 0x40, 0x3A, 0x34, 0x46, YM_REST, 0x7F
        db 4, 0x52, 0x2A, 0x3B, 0x3E, 0x32, 0x4A, YM_REST, 0x7F
        db 4, 0x50, 0x30, 0x39, 0x44, 0x30, 0x50, YM_REST, 0x7F
        db 4, 0x4B, 0x38, 0x37, 0x4C, 0x2B, 0x58, YM_REST, 0x7F
        db 4, 0x49, 0x44, 0x34, 0x58, 0x29, 0x64, YM_REST, 0x7F
        db 4, 0x47, 0x54, 0x30, 0x68, 0x27, 0x74, YM_REST, 0x7F
        db 0
