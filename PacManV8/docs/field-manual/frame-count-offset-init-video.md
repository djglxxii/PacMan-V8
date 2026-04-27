# Frame-count offset due to init_video timing

**Context:** T024 controller input testing required knowing when the game state machine enters PLAYING. The frame count at which this happens is not simply ATTRACT(120) + READY(240) = 360.

**The insight:** `init_video` (palette uploads, framebuffer clears, maze load, sprite init, HUD init) runs to completion BEFORE the main `idle_loop` / `halt` loop starts. The `game_flow_init` call sets the ATTRACT timer to 120 before `init_video` runs, but `game_flow_update_frame` only decrements the timer once per `halt` iteration. This means ~23 frames of timer head start are "consumed" during init before the first `halt`-driven frame. The game enters PLAYING at approximately frame 383 rather than 360.

**Example:** When writing replay-based tests that need to hit a specific game flow state, don't assume the state transitions happen at exact multiples of timer durations. Instead, probe `GAME_FLOW_CURRENT_STATE` (0x8250) and `GAME_FLOW_STATE_TIMER` (0x8254) at a few candidate frames to calibrate the offset for the current build.
