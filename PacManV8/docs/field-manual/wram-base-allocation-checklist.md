# WRAM Base Allocation Checklist

**Context:** T023 review caught a RAM overlap between `GAME_STATE_BASE`
(0x8230) and `AUDIO_STATE_BASE` (0x8230) that the implementation missed.
The pre-flight grep was done against a subset of `_BASE` symbols instead
of every one in `src/*.asm`.

**The insight:** When allocating a new `_BASE` block in WRAM, a
mechanical checklist prevents silent RAM corruption:

1. List every `_BASE EQU` in `src/*.asm` and compute its extent (read the
   source to find the highest offset within the block).
2. Pick a base that starts after the highest used byte of the preceding
   block.
3. Verify the chosen address does not appear in any `src/*.asm` file.
4. Document the claimed range in a comment near the `_BASE` EQU.

## Current RAM map (2026-04-26)

```
0x8100  MOVEMENT_STATE_BASE      (movement.asm:25)       ~0x8106
0x8120  GHOST_STATE_BASE         (ghost_ai.asm:50)       ~0x813F
0x8160  GHOST_WORK_BASE          (ghost_ai.asm:103)      ~0x816E
0x8170  GHOST_MODE_STATE_BASE    (ghost_ai.asm:119)      ~0x8179
0x8180  COLLISION_STATE_BASE     (collision.asm:16)      ~0x8208
0x8210  COLLISION_WORK_BASE      (collision.asm:28)      ~0x8215
0x8220  GHOST_HOUSE_STATE_BASE   (ghost_house.asm:20)    ~0x822E
0x8230  AUDIO_STATE_BASE         (audio.asm:43)          ~0x8240
0x8241  GAME_STATE_BASE          (game_state.asm:6)      ~0x8245
0x8250  GAME_FLOW_STATE_BASE     (game_flow.asm:36)      ~0x825C
0x8260  LEVEL_STATE_BASE         (level_progression.asm:48) ~0x8268
0x8270  INTERMISSION_STATE_BASE  (intermission.asm:32)   ← CONFLICT
0x8270  PATTERN_REPLAY_STATE_BASE(pattern_replay.asm:6)  ← CONFLICT
0x8300  SPRITE_STATE_BASE        (sprites.asm:61)        ~0x8395
```

## Known overlaps

- **0x8230** (fixed in T023): `GAME_STATE_BASE` was placed on top of
  `AUDIO_STATE_BASE`. Game-state init zeroed SCORE/LIVES bytes that
  belong to `AUDIO_FRAME_COUNTER` and channel-A state. Every VBlank,
  `audio_update_frame` incremented what game_state.asm believed was
  SCORE. Moved `GAME_STATE_BASE` to 0x8241 (after `AUDIO_FM_TMP_LEVEL`).
- **0x8270** (pre-existing, tracked as MEDIUM-4 in the audit):
  `INTERMISSION_STATE_BASE` and `PATTERN_REPLAY_STATE_BASE` share the
  same address. Benign only because these modules are never both active
  in the live loop simultaneously. Still needs fixing before the
  integrated game ships.

## Pre-commit sanity check

```bash
# List all _BASE declarations and their source locations.
grep -n '_BASE\s*EQU\s*0x8' src/*.asm

# Verify a candidate address is not referenced anywhere.
grep -rn '0x<CANDIDATE>' src/
```
