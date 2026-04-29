# Live Render Replay With Game-Flow Warmup

**Context:** T027 needed frame evidence for sprites committed from the live
PLAYING tick rather than from the older pattern replay validation owner.

**The insight:** Do not press Start when the evidence target is a live
game-flow render path. Start activates `pattern_replay_update_frame`, and
`game_flow_update_frame` then skips the normal PLAYING tick because pattern
replay owns gameplay validation. For live rendering evidence, write a replay
that leaves Start high, waits through ATTRACT plus READY, then applies
direction inputs after PLAYING starts.

**Example:** T027 captured gameplay-sequence frames 30, 90, and 180 at
absolute headless frames 390, 450, and 540. The first 360 frames cover
`GAME_FLOW_DURATION_ATTRACT` plus `GAME_FLOW_DURATION_READY`; subsequent
controller bytes exercise `game_state_tick_playing`, including the
post-collision `sprite_commit_from_game_state` SAT upload.
