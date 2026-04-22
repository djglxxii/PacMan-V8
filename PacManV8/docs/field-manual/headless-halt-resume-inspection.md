# Headless HALT Resume Inspection

**Context:** T020 needed to distinguish whether intermission drawing was not
visible, crashing, or never reached in the Vanguard 8 headless runtime.

**The insight:** Use `--run-until-pc` on the instruction after the foreground
`HALT` before probing the later feature entry point. If the post-`HALT`
instruction is not hit and SRAM state remains initialized, later render probes
will be misleading because the game-flow owner has not advanced at all.
Pair this with `--peek-logical` on the relevant SRAM state blocks so the report
shows both the CPU halt state and the game-owned counters.

**Example:**

```bash
rg -n "idle_loop|game_flow_update_frame|intermission_start" build/pacman.sym

/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless \
  --rom build/pacman.rom \
  --frames 20 \
  --run-until-pc 0x0068:20 \
  --symbols build/pacman.sym

/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless \
  --rom build/pacman.rom \
  --frames 1100 \
  --inspect-frame 1100 \
  --dump-cpu \
  --peek-logical 0x8250:0x30 \
  --peek-logical 0x8270:0x10
```

For the blocked T020 run, `0x0068` was not hit, CPU inspection ended at
`PC=0x0067` with `halted=true`, and `GAME_FLOW_FRAME_COUNTER` remained
`0x0000`. That proved the intermission owner was not reached, independent of
VDP-B drawing or compositor state.
