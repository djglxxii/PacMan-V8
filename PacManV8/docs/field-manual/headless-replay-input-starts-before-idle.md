# Headless Replay Input Starts Before Idle

**Context:** T021 added deterministic `.v8r` replay validation for gameplay
state checkpoints.

**The insight:** `vanguard8_headless --replay` applies controller bytes from
the first emulated frame, but PacManV8 may still be inside boot/video
initialization for those early frames. Controller reads in the idle/gameplay
loop therefore may not see a one-frame Start pulse at replay frame zero. For
power-on replay activation, hold the activation input across the boot window
or record the activation frame from SRAM and compare gameplay checkpoints
relative to that frame.

**Example:** A replay with Start pressed only on frame 0 showed controller
port `0xFE` at completed frame 1, but the T021 SRAM activation flag was still
zero because the ROM had not reached the replay-aware frame loop. Holding Start
for the initial warmup segment gives the ROM a deterministic activation window
without changing no-input boot behavior.
