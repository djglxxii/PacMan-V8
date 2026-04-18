# T014 — HUD Rendering (Score, Lives, Fruit)

| Field | Value |
|---|---|
| ID | T014 |
| State | completed |
| Phase | Phase 4 — Rendering Layer |
| Depends on | T013 |
| Plan reference | `docs/PLAN.md` Display; VDP Configuration; Phase 2 Screen Layout; Phase 4.1 Frame Update Flow; Phase 4.2 Sprite Rendering |

## Goal

Render the non-gameplay foreground HUD on VDP-A: the top score labels and
digits, the bottom lives display, and the level fruit/status icon area. This
fills the remaining fixed foreground presentation around the already-rendered
maze and sprites.

## Scope

- In scope:
  - Add a compact HUD/font rendering path for VDP-A Graphic 4 output, using
    reproducible tracked inputs and build-script generation where assets are
    needed.
  - Render the top HUD row with `1UP`, `HIGH SCORE`, `2UP`, and deterministic
    score values suitable for review.
  - Render the bottom status row with a deterministic lives display and fruit
    icon strip or current-level fruit marker.
  - Keep VDP-A color `0` transparent everywhere outside HUD glyph/icon pixels
    so the VDP-B maze and existing VDP-A sprites remain visible.
  - Integrate HUD updates with the existing frame-update path so score/lives
    changes can be redrawn without redrawing the full foreground every frame.
  - Reserve or coordinate with sprite slot `5` for fruit/score popup usage
    without implementing point popups or gameplay scoring transitions.
  - Produce deterministic frame and text evidence under
    `tests/evidence/T014-hud-rendering-score-lives-fruit/`.

- Out of scope:
  - Final coordinate transform and rotation validation; T015 owns that work.
  - New gameplay scoring rules, extra-life thresholds, level progression, or
    fruit-award timing.
  - Point-value popup animation after eating fruit or ghosts.
  - VDP-B pellet erase updates, energizer blinking, or maze redraw changes.
  - Audio, attract mode, start/ready/game-over flow, intermissions, or level
    speed-table work.
  - Revisiting accepted sprite extraction or T013 sprite placement except for
    keeping HUD rendering compatible with existing VDP-A sprite data.

## Scope changes

- Initial implementation uses generated CPU VRAM dirty-band uploads for the
  top and bottom HUD rows instead of VDP command-engine HMMM glyph blits.
  The attempted VDP-A HMMM path was not reliable enough for acceptance
  evidence in the current emulator: S#2.CE polling could remain set before
  the first HUD blit, and no visible HUD pixels appeared when commands were
  issued without polling. The generated patch keeps the same transparent
  foreground semantics and records per-glyph placement metadata so later
  HMMM wiring can replace the band uploads without changing HUD content. The
  VDP-A framebuffer clear now uses a CPU VRAM fill for the same reason, keeping
  the review path independent of VDP-A command-engine state.

## Pre-flight

- [x] T013 is completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Display, VDP Configuration, Phase 2 Screen
  Layout, Phase 4.1, and Phase 4.2 before implementation.
- [x] Review `docs/tasks/completed/T007-vdp-b-maze-render-and-pellet-display.md`
  for current framebuffer layout and maze review evidence.
- [x] Review `docs/tasks/completed/T013-sprite-rendering-and-animation.md`
  for VDP-A transparency, sprite slot ownership, palette usage, and current
  headless frame-capture command.
- [x] Consult the Vanguard 8 V9938 spec for Graphic 4 HMMM/LMMM command
  behavior and VRAM timing before adding HUD blits.

## Implementation notes

VDP-A is the foreground plane. HUD pixels should be written into the VDP-A
framebuffer and should use palette entries that remain readable over black
top/bottom bands. Color `0` must remain transparent anywhere the HUD does not
explicitly draw text or icons.

The planned fixed layout from `docs/PLAN.md` is:

- Top 8 px: `1UP`, `HIGH SCORE`, `2UP`, and score digits.
- Maze area: y=`8..203`.
- Bottom 8 px: lives and level fruit/status icons.

Prefer a generated font/icon asset over hand-authored binary data. If arcade
character graphics from `pacman.5e` are reused for HUD glyphs, route them
through a tool in `tools/` and document the mapping. Do not read or derive
logic from the restricted program ROM files.

Keep the HUD slice deterministic. A review mode or test fixture may draw fixed
values such as player score, high score, lives, and fruit markers, as long as
the evidence records those values and the runtime path is suitable for later
game-state wiring.

Coordinate with T013 sprite ownership:

- Sprite slots `0..4` remain Pac-Man and ghosts.
- Slot `5` remains reserved for fruit or score popup display.
- HUD text and lives/fruit status icons should not consume the entity sprite
  slots unless the task explicitly documents why that is necessary.

Because V-blank budget is limited, full HUD redraw should happen at scene init
or review setup. Per-frame updates should be narrow dirty-region blits for
changed score/lives/fruit fields, even if this task only exercises a
deterministic review update.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T014-hud-rendering-score-lives-fruit/hud_frame.ppm` —
  PPM frame dump from the headless emulator showing the HUD rendered on
  VDP-A over the existing maze/sprite scene.
- `tests/evidence/T014-hud-rendering-score-lives-fruit/hud_render_tests.txt`
  — stdout from a deterministic HUD evidence script or test harness.
- `tests/evidence/T014-hud-rendering-score-lives-fruit/hud_render_vectors.txt`
  — readable summary of HUD values, glyph/icon asset hashes, palette indices,
  dirty rectangles or blit regions, and frame hash.

**Reviewer checklist** (human ticks these):

- [ ] Frame capture shows readable top HUD labels and score digits in the top
  8 px band.
- [ ] Frame capture shows lives and fruit/status icons in the bottom 8 px
  band without overlapping the maze play area.
- [ ] VDP-A remains transparent outside HUD glyph/icon pixels and existing
  sprite pixels; the VDP-B maze is still visible.
- [ ] Pac-Man and ghost sprites from T013 still render correctly, with sprite
  slots `0..4` unchanged and slot `5` reserved or explicitly documented.
- [ ] Evidence output records deterministic HUD values, asset hashes, palette
  indices, updated regions, frame hash, and pass/fail results.
- [ ] No coordinate-transform task work, scoring/game-flow logic, audio,
  pellet erase rendering, attract mode, or level progression is introduced.

**Observed evidence values:**

- Headless frame dump SHA-256:
  `f484d6ec0574b67faa5c8f0f0089f7c79a0cee1b93451e6e58ef915e478d0506`
- Headless runtime frame hash at frame 60:
  `5947003ed28e4c389a7341ff492ff9ba89ee8b12db424b3cf60f2ce18471f8a6`
- `hud_render_tests.py`: `11/11 passed`
- Top HUD band nonblack pixels: `476`
- Bottom HUD band nonblack pixels: `317`
- HUD patch SHA-256:
  `80497cf90dae9f0d36e1fb0514efd27e86778570c0d3c6e5ba5583270bd3d043`
- HUD tile atlas SHA-256:
  `d16e7061eb9b043b88bc2ba8b11402f9bda728b59f5d216fb6ac4888a297165e`

**Rerun command:**

```bash
python3 tools/build.py
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --dump-frame tests/evidence/T014-hud-rendering-score-lives-fruit/hud_frame.ppm --hash-frame 60
python3 tools/hud_render_tests.py --vectors-output tests/evidence/T014-hud-rendering-score-lives-fruit/hud_render_vectors.txt --frame-dump tests/evidence/T014-hud-rendering-score-lives-fruit/hud_frame.ppm > tests/evidence/T014-hud-rendering-score-lives-fruit/hud_render_tests.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-18 | Created, state: planned. |
| 2026-04-18 | Activated after confirming no other task was active. |
| 2026-04-18 | Implemented deterministic generated HUD tiles, patch asset, VDP-A band upload, build-time asset regeneration, and evidence validation. |
| 2026-04-18 | Accepted by human reviewer and moved to completed. |

## Blocker (only if state = blocked)

*(None.)*
