# Audit — Runtime Integration Gaps

**Date:** 2026-04-25
**Trigger:** While starting T022 (visual polish), it became apparent the ROM
is not in a playable state despite 21 of 22 tasks being marked completed. This
audit was scoped to find every gap of the same shape ("module exists in source
but is never reached from the live runtime") so that the integration work can
be planned with full information rather than discovered piecemeal.
**Method:** Read-only static analysis. Trace every code path reachable from
`reset_entry` → `idle_loop` and compare against the symbols defined across
`src/*.asm`. Spot-check the evidence directories for each completed task to
classify what was actually demonstrated.
**Outcome:** This report. No code or assets were changed.

---

## Executive summary

The arcade-faithful gameplay core, ghost AI, ghost house, collision/pellet
system, level progression, intermission cutscenes, audio engine, sprite
renderer, HUD renderer, and game-flow state machine **all exist as
self-consistent modules** in `src/`. They were each delivered with passing
evidence. However, **the live runtime exercises almost none of it**. The boot
ROM produces a static maze-and-sprites screenshot, plays a fixed 4–8 second
audio demo reel triggered by the boot frame counter, and then ticks a
gameplay-free state-machine timer in a loop. The only path that touches real
gameplay code per frame is the T021 pattern-replay test harness, which is
gated on a Start-button press and was authored to validate determinism, not
to be the game.

The single *largest* missing piece is **integration**: a live "PLAYING" tick
that reads input, runs movement/AI/collision/ghost-house each frame, pushes
state into the SAT shadow and HUD VRAM, and reacts to gameplay events
(collisions, dots eaten, level complete, life lost) instead of fixed timers.

There are also several **smaller gaps** — pellet/energizer erasure on
VDP-B, score/lives storage, fruit, score popups, attract-mode demo, audio
events tied to gameplay — that depend on the integration layer existing
before they can be wired up. They are listed here so they don't get
rediscovered mid-implementation.

---

## What the live runtime actually does

`src/main.asm` reset path:

1. HD64180 MMU setup, IM1, stack at 0xFF00.
2. `audio_init` — initializes PSG and YM2151 to documented quiescent state.
3. `game_flow_init` — initializes level progression, sets state to ATTRACT,
   loads attract-state timer (120 frames).
4. `init_video` — both V9938 chips to Graphic 4 / 212-line, palettes uploaded,
   VDP-A framebuffer cleared, VDP-B maze framebuffer DMA'd in from ROM banks,
   `sprite_renderer_init`, `hud_renderer_init`, then display + VBlank IRQ on.
5. `idle_loop`: `ei` / `halt` / `game_flow_update_frame` /
   `pattern_replay_update_frame`.

The IM1 handler (`im1_handler`) reads VDP-A S#0 to clear V-blank and calls
`audio_update_frame`. That's the entirety of the per-frame work outside the
two idle-loop calls.

### What `game_flow_update_frame` does

It ticks the state-machine timer and transitions
ATTRACT → READY → PLAYING → DYING → CONTINUE → PLAYING →
LEVEL_COMPLETE → NEXT_LEVEL → INTERMISSION on hardcoded frame durations
(`GAME_FLOW_DURATION_*`). **No call into movement, ghost AI, ghost house,
collision, sprite update, HUD update, or input.** PLAYING is a 180-frame
timer with no interior content.

### What `pattern_replay_update_frame` does

Reads controller port `0x00`. If Start has not been pressed, returns. Once
Start is pressed it sets a flag, calls `level_progression_init`,
`movement_init_pacman`, `ghost_init_state`, `collision_init`, then on every
subsequent frame runs `movement_update_pacman`,
`collision_update_pellet_at_pacman`, `ghost_mode_tick`,
`ghost_update_all_targets`, `collision_check_all_ghosts`, and snapshots state
into SRAM mirrors for headless inspection. **It does not commit any sprite
or HUD VRAM update**, does not erase consumed pellets from VDP-B, and
bypasses game_flow's PLAYING state. It exists to feed the headless emulator
deterministic playback for T021 fidelity hashes — not to be played.

### What `audio_update_frame` does (called from VBlank IRQ)

Calls `audio_review_script`, which on the very first frames after boot fires
a fixed sequence:

| Frame | Cue |
|-------|-----|
| 0     | siren |
| 12    | pellet |
| 36    | waka |
| 72    | ghost-eaten |
| 112   | extra-life |
| 144   | intro music |
| 196   | intermission music |
| 240   | death music |

After frame 240 the audio engine just ticks idle channel/music updates. **No
gameplay event triggers any audio cue.** The audio engine is correct in
isolation but is driven by a one-shot demo sequencer, not by collisions,
energizer consumption, ghost eating, or life loss.

---

## Findings

Severity legend:

- **CRITICAL** — blocks "the game is playable."
- **HIGH** — required for arcade-faithful play but depends on CRITICAL fixes.
- **MEDIUM** — visible but not functionally blocking.
- **LOW** — cleanup / hygiene.

### CRITICAL-1 — No live PLAYING tick

`game_flow_update_frame`'s PLAYING state contains no gameplay calls. Movement,
ghost AI, collision, ghost-house, frightened-mode tick, dot-stall tick, and
input reading are all absent from the per-frame path during PLAYING.

**Symbols never reached from `idle_loop` (live runtime):**

- `movement_update_pacman`, `movement_request_direction`,
  `movement_apply_tunnel_wrap`
- `ghost_mode_tick`, `ghost_update_all_targets`, `ghost_enter_frightened`
- `ghost_house_tick`, `ghost_house_on_dot_event`,
  `ghost_house_begin_next_exit`, `ghost_house_complete_exit`,
  `ghost_house_clear_release_flags`
- `collision_update_pellet_at_pacman`, `collision_check_all_ghosts`,
  `collision_tick_dot_stall`, `collision_clear_erase_queue`
- `level_progression_complete_current_level` (only reached via the same
  game_flow timer chain, so technically called — but always with a level the
  player never actually completed)

**Comment in `src/movement.asm:4`:** *"This file is assembled into the ROM
now, while later tasks will wire it into input, rendering, pellet, and ghost
systems."* That wiring was never done.

### CRITICAL-2 — Sprite SAT is uploaded once at boot and never changes during play

`sprite_renderer_init` uploads a static SAT shadow built by
`sprite_build_shadow` (which `INCLUDE`s the build-time-generated
`sprite_review_shadow.inc`). The shadow contains five hardcoded sprite slots
showing Pac-Man and four ghosts at fixed positions chosen to validate the
T013/T015 coordinate transform. **Nothing in the live loop ever rewrites the
SAT shadow or DMAs an updated SAT to VRAM.** So even if PLAYING ran movement,
nothing would move on screen. The only runtime SAT writers in the codebase
are inside `intermission.asm` and `pattern_replay`-adjacent test paths.

Affected: `sprite_upload_sat_shadow`, `sprite_upload_color_shadow`, the
SAT-shadow helper macros in `intermission.asm` — none of these are called
each frame from a live gameplay tick.

### CRITICAL-3 — HUD is uploaded once at boot and never changes

`hud_renderer_init` DMAs a single 2 KB patch into VDP-A bands and returns.
There is no live runtime mechanism to:

- Increment the score on pellet/energizer/ghost-eaten events.
- Decrement lives on death.
- Swap fruit icons on level transition.
- Animate "READY!" or "GAME OVER" overlays during the corresponding states.

The label `hud_draw_review_rows` (which `INCLUDE`s an unused
`hud_review_draw.inc`) is defined but never called from anywhere in the
ROM — see LOW-2.

### CRITICAL-4 — No input handling on the gameplay path

The only `in a, (0x00)` (controller port 0) is inside
`pattern_replay_update_frame`. The live PLAYING state never reads the
controller. Even if PLAYING ran movement, there would be no way for the
player to request a direction.

### CRITICAL-5 — Subsystems are not initialized for actual play

`ghost_init_state`, `collision_init`, and `ghost_house_init` are only called
from `pattern_replay_start` (gated on Start-press). Boot leaves the ghost
records, pellet bitset, and ghost-house state uninitialized. The static
sprite shadow at boot does not represent a coherent gameplay state — it
mixes one ghost in CHASE, one in FRIGHTENED, one in SCATTER, one in SCATTER,
chosen to populate all the visual variants.

### CRITICAL-6 — No per-frame VBlank-driven update of the game world

The IM1 handler calls only `audio_update_frame`. Game ticking is done in the
post-`halt` foreground (`game_flow_update_frame` /
`pattern_replay_update_frame`). That's actually fine in principle (foreground
sees one tick per frame because `halt` parks the CPU until V-blank), but it
means the VBlank-only window for SAT/HUD/maze DMAs is unused — a real game
loop will need to either move SAT-commit into the IM1 handler or schedule
DMAs immediately after `halt` returns and before the next frame's logic.

---

### HIGH-1 — Pellets are tracked in RAM but never erased from VRAM

`collision_update_pellet_at_pacman` clears a pellet bit and sets
`COLLISION_ERASE_PENDING` with the tile coordinates. **Nothing consumes that
queue and writes to VDP-B's framebuffer.** Even if PLAYING ran the
collision system, every pellet would still be visually present forever.

The maze on VDP-B is a static framebuffer DMA'd in from `pacman.rom` banks at
boot. Erasing a pellet means writing 8×8 zero-bits at the right framebuffer
coordinates via VDP-B HMMV. No code does this.

### HIGH-2 — No score, lives, or game-over storage

There is no `SCORE` / `LIVES` variable in the main game's state. The pattern
replay keeps a local 16-bit `PATTERN_REPLAY_SCORE` and `PATTERN_REPLAY_LIVES`
is absent. There is no game-over path — `GAME_FLOW_STATE_DYING` transitions
straight to CONTINUE → PLAYING after fixed timers, with no "out of lives"
check. High-score storage is also absent.

### HIGH-3 — No fruit (bonus item) implementation

`level_progression_get_fruit` returns the fruit kind for the current level,
but no code spawns the fruit sprite, schedules its appearance/disappearance,
checks collision, or awards the bonus score. The fruit table is data-only.

### HIGH-4 — Audio cues are not bound to gameplay events

`audio_review_script` is the only caller of any `audio_trigger_*`. Once the
post-boot demo sequence ends, no event in the codebase triggers a sound:

- `collision_update_pellet_at_pacman` → should call `audio_trigger_waka`
  (waka pattern alternation) on each dot.
- Energizer consumption → should switch to frightened-mode music or siren
  pitch shift.
- Ghost-eaten collision → should call `audio_trigger_ghost_eaten`.
- Pac-Man dies → should call `audio_trigger_death_music`.
- Extra life threshold → should call `audio_trigger_extra_life`.
- Level start → should call `audio_trigger_intro_music`.
- Intermission triggers `audio_trigger_intermission_music` correctly (only
  bright spot — `intermission_start` does call it, but `intermission_start`
  itself is only reached if the timer-only game_flow times out long enough
  to "complete" levels 2/5/9, which won't happen with no real gameplay).

### HIGH-5 — Attract mode draws nothing

`GAME_FLOW_STATE_ATTRACT` exists but no code draws an attract-mode demo
(scrolling "CHARACTER / NICKNAME" table, ghost-eats-Pac-Man playback, "PUSH
START" prompt). It's a 120-frame idle.

### HIGH-6 — Frightened-mode visuals never apply

Frightened ghost color/sprite swap is in the sprite shadow generator
(palette index `SPRITE_PALETTE_FRIGHTENED = 8`, pattern
`SPRITE_PINKY_FRIGHT_ID = 50`) but no live code sets a ghost's slot to those
values when `GHOST_MODE_FRIGHTENED` is entered. The flashing-blue/white
phase in the last 2 seconds of frightened is also unimplemented.

### HIGH-7 — Sprite animation frames are never advanced

Pac-Man's mouth open/close frames and ghost wobble frames exist in
`sprites.bin` but the SAT pattern field is a static value baked into the
review shadow. There's no per-frame counter incrementing the pattern index.

---

### MEDIUM-1 — Coordinate transform runs only at build time

`tools/generate_sprite_review_shadow.py` produces `sprite_review_shadow.inc`
which contains static `db` lines emitting fixed Y/X bytes already passed
through the arcade-to-V8 fitted-coordinate map. The runtime never applies
the transform — there's no Z80 routine that takes 8.8 arcade coordinates
and produces V8 SAT Y/X. T015's evidence is a frame capture of those static
fixed positions; the transform code lives in Python only. A real game loop
needs the transform in Z80, or a precomputed lookup table consulted per
frame.

### MEDIUM-2 — Maze flash on level-clear is ungrounded

T022's scope assumes a level-clear flash exists to be polished. The plan
documents this as a VDP-B palette cycle, but no level-clear hook fires the
cycle today, and `GAME_FLOW_STATE_LEVEL_COMPLETE` runs no rendering code.

### MEDIUM-3 — Tunnel slow-zone is documented but unused

`movement_apply_tunnel_wrap` handles wrap. There is no separate
ghosts-in-tunnel speed lookup actually consulted in the AI step routine
because the AI step routine itself runs at 1 tile-per-call cadence, not at
sub-pixel speed. Speed tables in `level_progression.asm` (`LEVEL_SPEED_FP_*`)
are exposed but never read by movement or AI code.

### MEDIUM-4 — `pattern_replay_update_frame` and `intermission` share state

Both modules use `0x8270` as their state base
(`PATTERN_REPLAY_STATE_BASE EQU 0x8270` in `pattern_replay.asm` line 6;
`INTERMISSION_STATE_BASE EQU 0x8270` in `intermission.asm` line 32). This
overlap is benign today because pattern replay and intermissions are never
both active in the live loop, but a real integration must pick one base
address per module to prevent state corruption when the integrated game
plays an intermission after a level.

### MEDIUM-5 — Cornering (turn buffering) is implemented but never observed in the live game

`movement_request_direction` accepts a turn within a 4-pixel window before
the intersection center, which is the cornerstone of arcade pattern play.
Because no input feeds into it from the live loop, this is effectively
dead capability today — but it will be the difference between
"arcade-faithful" and "feels off" once integration lands. Worth verifying
behavior on real input as the integration goes in.

---

### LOW-1 — Comment lying in `movement.asm:4`

Says *"later tasks will wire it"* — they didn't. Update or remove once
integration lands.

### LOW-2 — `hud_draw_review_rows` is dead

Defined in `src/hud.asm:35`, includes `hud_review_draw.inc`, and is
unreferenced. Either it was a debug-time scaffold left behind, or the
intent was to call it from the per-frame HUD update that doesn't exist.

### LOW-3 — `sprite_init_debug_state` mixes ghost modes for screenshot

`src/sprites.asm:92` deliberately sets Pinky to FRIGHTENED, Inky/Clyde to
SCATTER, Blinky to CHASE so that the static screenshot demonstrates all
four palette/pattern combinations. This must be replaced by
`ghost_init_state` once the live loop owns ghost initialization.

### LOW-4 — `sprite_color_data` unused

`src/sprites.asm:146` defines `sprite_color_data:` with `INCBIN
"../assets/sprite_colors.bin"` but nothing references the symbol. The color
data actually used is the per-slot color shadow built by the review-shadow
generator into `SPRITE_COLOR_SHADOW` RAM, then DMA'd by
`sprite_upload_color_shadow`. The raw asset block in ROM is dead weight.

### LOW-5 — `audio_review_script` runs at boot regardless of game flow

Even after integration, leaving the boot demo in place means every reset
plays an 8-second "audio sampler" before anything meaningful happens.
Should be gated on a debug build flag or removed when audio is wired to
gameplay events.

### LOW-6 — `intermission_select_review_level_for_game_flow`

Pure test-determinism scaffolding driving the intermission cutscene picker
from `INTERMISSION_REVIEW_INDEX` rather than `LEVEL_COMPLETED_NUMBER`. Will
need to be replaced (or short-circuited) once real level completions feed
the picker via the actual completed-level number.

### LOW-7 — `level_progression_set_current_level_2_for_review`

Same flavor as LOW-6 — test scaffolding to skip to level 2 for harness
runs. Remove or relegate to debug paths once integration lands.

---

## What was actually validated by each completed task's evidence

This is *not* an accusation — each task's evidence demonstrates the
module is correct in isolation. The point is that "module correct in
isolation" is what was demonstrated, not "module works in the running
game." Where evidence was integration-level, that's noted.

| Task | Evidence shape | Integration coverage |
|------|----------------|----------------------|
| T001 build/boot | PPM frame: empty maze framebuffer | yes — actual ROM boots |
| T002–T005 extract | Python tool stdout, hashes, summaries | n/a (build-time) |
| T006 maze re-author | PPM frame of fitted maze | yes (static) |
| T007 VDP-B maze render | PPM frame of maze + pellets in framebuffer | yes (static) |
| T008 movement | `movement_tests.py` stdout, no live frame | **isolated** — Python harness drives the routine, never proven from real ROM input |
| T009 ghost AI | `ghost_ai_tests.py` stdout vectors | **isolated** — same |
| T010 scatter/chase/frightened | `mode_timer_tests.py` stdout + checklist | **isolated** |
| T011 collision | `collision_tests.py` stdout | **isolated** |
| T012 ghost house | `ghost_house_tests.py` stdout + checklist | **isolated** |
| T013 sprite render | `sprite_render_tests.py` + PPM of static shadow | **static frame** — proves the renderer can paint *a* sprite at *some* coordinate; does not prove sprites move on input |
| T014 HUD render | `hud_render_tests.py` + PPM of static patch | **static frame** |
| T015 transform | `transform_tests.py` Python output | **build-time only** — transform is Python, no Z80 |
| T016 PSG | `psg_sound_tests.py` audio hash + checklist | **boot demo** — siren/waka/etc fire from `audio_review_script`, no gameplay binding |
| T017 FM | `fm_music_tests.py` audio hash + checklist | **boot demo** |
| T018 game flow | `game_flow_tests.py` + checklist + PPM at frame 960 | **timer-only** — proves the state machine cycles correctly through hardcoded durations; PLAYING state is empty |
| T019 level progression | `level_progression_tests.py` stdout | **isolated** — table reads only |
| T020 intermission | `intermission_tests.py` + PPMs of cutscene panels | **partially live** — cutscene draws to SAT, but is reached by a test path that artificially advances `LEVEL_COMPLETED_NUMBER`; not by real level completion |
| T021 pattern replay | recorded inputs replayed headlessly; checkpoint hashes match arcade reference | **harness only** — proves the gameplay subsystems compose deterministically when called from a test path; does not exercise the live `idle_loop` |

So the audit's structural claim — *the modules are correct, but no task
delivered an integrated playable loop* — is consistent with each task's
own evidence.

---

## Recommendations

### A. Stop, replan, then resume

T022 (visual polish) is meaningless until the game actually plays. Move
T022 back to `planned/`. Insert two new tasks ahead of it:

#### Proposed **T023 — Live gameplay integration**

Goal: replace `game_flow_update_frame`'s PLAYING state with a real
gameplay tick. Acceptance is a frame capture sequence (or a recorded
input replay seeded from the headless tool) showing:

- Pac-Man moves on user input from controller port 0x00.
- Pac-Man stops at walls, corners with the 4-px window, wraps through the
  tunnel.
- Pellets disappear from VDP-B as eaten; pellet count decrements.
- Ghosts leave the house in order (Blinky out, Pinky on dot 0, Inky on 30,
  Clyde on 60).
- Ghosts pursue per Blinky/Pinky/Inky/Clyde target rules.
- Energizer consumption switches all ghosts to frightened, reverses their
  direction, swaps palette/pattern, lasts the level-1 duration (6 s), and
  flashes white in the final 2 s.
- Same-tile collision either kills Pac-Man (DYING transition) or eats the
  ghost (eyes return to house).
- Score, lives, and current level update on the HUD each frame.

In-scope wiring:

- New `game_state_init` called from boot that initializes ghosts, ghost
  house, collision bitset, score=0, lives=3.
- New per-frame `game_state_tick_playing` running the existing module
  routines in arcade order.
- New `pellet_erase_commit` that consumes `COLLISION_ERASE_PENDING` and
  writes 8×8 transparent pixels to VDP-B at the right framebuffer
  coordinates (VDP-B HMMV).
- New `sprite_commit_from_game_state` that walks ghost records + Pac-Man
  state, applies the arcade→V8 coordinate transform (port the Python
  transform from T015 to a Z80 routine or a precomputed table), writes
  the SAT shadow, then DMAs to VRAM.
- New input reader that maps controller port 0 to
  `movement_request_direction`.
- HUD score/lives/level update routines.
- Audio bindings: `collision_update_pellet_at_pacman` →
  `audio_trigger_waka`, energizer → frightened cue, ghost eaten →
  `audio_trigger_ghost_eaten`, life lost → `audio_trigger_death_music`,
  level start → `audio_trigger_intro_music`.
- DYING and CONTINUE states wired to actual life-loss + life-count check
  (game-over → ATTRACT).
- LEVEL_COMPLETE wired to the actual "all 244 dots eaten" predicate (count
  reaches zero).

Out-of-scope for T023:

- Fruit / bonus item.
- Attract-mode demo content.
- Level 256 kill screen.
- Visual polish (palette refinement, maze flash) — that's still T022.

#### Proposed **T024 — Fruit, attract demo, and game-over polish**

Bonus fruit, attract-mode demo, score popups, intro flash, "GAME OVER"
text. Smaller than T023; depends on it.

#### Then **T022** — visual polish, on top of a working game.

### B. Reorder the index, don't relabel completed tasks

The 21 completed tasks should *stay* completed. Their evidence is what
it is — module-level correctness was proven. Don't rewrite history;
just acknowledge that integration was implicit between tasks rather
than owned by a task, and that this audit closes the loop by adding the
explicit integration task.

### C. Add an integration test as ongoing acceptance

`tests/evidence/T023-.../` should include an input replay (controller
inputs + expected frame hashes / score / pellet count at checkpoints)
that the headless emulator runs under `--frames N --expect-frame-hash`.
This gives a green-or-red signal that the integrated loop hasn't
regressed when later tasks touch shared state.

### D. Field-manual entry to record the lesson

Add a field manual entry under `docs/field-manual/`, something like
`per-task-evidence-vs-integration.md`, capturing:

- Module-level evidence does not prove integration.
- A plan needs an explicit integration owner for any project where
  modules are built independently before being wired together.
- Running the ROM under the frontend emulator and pressing buttons is
  an irreducible acceptance step that headless harnesses cannot replace.

This is exactly the kind of insight CLAUDE.md §9 was written for.

---

## Confidence and limits of this audit

- The audit was static-only. The actual ROM was not run under the frontend
  emulator. The findings are derived from reading every file under `src/`,
  the task index, and a sample of evidence directories. If a runtime path
  exists that the static read missed (e.g., self-modifying jump table, a
  hook in the assembler-included files I didn't open), it could change a
  finding — but the call graph from `idle_loop` is small and explicit, so
  high confidence in CRITICAL-1..6.
- I did not re-read every Python tool. The build pipeline is described
  from `tools/build.py` only; if other tools have integration logic that
  isn't surfaced through `build.py`, it's not in this report.
- The restricted-source rule (no reading `pacman.6e`–`6j`) was respected.
