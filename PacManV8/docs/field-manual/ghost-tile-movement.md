# Ghost Tile-Based Movement

**Context:** T025 — implementing live ghost movement for the first time.
Ghosts store their position as tile coordinates (X_TILE, Y_TILE) rather than
the 8.8 fixed-point used by Pac-Man. The ghost house state determines
movement eligibility.

**The insight:** A simple per-ghost frame counter (increment each frame, move
one tile when counter reaches threshold) works well for tile-based ghost
movement. Ghosts outside the house move; ghosts inside (WAITING,
PENDING_RELEASE) are stationary. Reversal flags from the ghost mode system
must be consulted on each move to allow a one-time direction reversal.

Key design points:
- Staggered initial counters prevent all ghosts moving on the same frame.
- Direction choice happens at every tile step via `ghost_choose_direction`
  (chase/scatter) or `ghost_choose_frightened_direction` (frightened).
- Tunnel wrap for tile coordinates: decrement from 0 wraps to 27; increment
  from 27 wraps to 0.
- The ghost record's CHOSEN_DIR field should be kept in sync with DIR for
  downstream consumers.

**Example:** See `src/game_state.asm` — `GHOST_MOVE_COUNTER`,
`movement_update_ghosts`, and `movement_ghost_step`.
