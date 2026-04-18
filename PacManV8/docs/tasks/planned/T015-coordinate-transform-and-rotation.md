# T015 — Coordinate Transform and Rotation Validation

| Field | Value |
|---|---|
| ID | T015 |
| State | planned |
| Phase | Phase 4 — Rendering Layer |
| Depends on | T013, T014 |
| Plan reference | `docs/PLAN.md` Orientation; Phase 2 Screen Layout; Phase 4.1 Frame Update Flow; Phase 4.2 Sprite Rendering |

## Goal

Validate and wire the final gameplay-to-screen coordinate transform so maze
features, Pac-Man, ghosts, HUD clearance, tunnels, and sprite anchors line up
in the fitted 256x212 Vanguard 8 presentation without changing gameplay
coordinates.

## Scope

- In scope:
  - Define the authoritative transform from the 28x36 arcade tile coordinate
    space, including 8.8 fixed-point entity positions, to V8 screen pixels.
  - Use the existing fitted maze layout and HUD/status bands as the visible
    frame of reference.
  - Replace any temporary T013 sprite review placement with transform-derived
    positions for deterministic test states.
  - Validate Pac-Man, ghost, tunnel, house-door, pellet, energizer, and corner
    anchor positions against the VDP-B maze render.
  - Produce deterministic frame and text evidence under
    `tests/evidence/T015-coordinate-transform-and-rotation/`.

- Out of scope:
  - Changing gameplay movement, ghost AI, scatter/chase timing, frightened
    mode, collision rules, pellet consumption, scoring, lives, or level flow.
  - Redrawing or redesigning maze art except for fixing clear transform
    alignment defects discovered by this validation.
  - New sprite art extraction, HUD content changes, fruit/score popups, audio,
    attract mode, intermissions, or speed-table work.
  - Replacing the T014 CPU HUD band upload fallback with HMMM.

## Scope changes

*(None.)*

## Pre-flight

- [ ] T013 and T014 are completed and accepted.
- [ ] Confirm no other task is active before activation.
- [ ] Review `docs/PLAN.md` Orientation, Phase 2 Screen Layout, Phase 4.1,
  and Phase 4.2 before implementation.
- [ ] Review `docs/tasks/completed/T006-maze-tile-re-authoring-for-256x212.md`
  and `docs/tasks/completed/T007-vdp-b-maze-render-and-pellet-display.md`
  for the fitted maze framebuffer and coordinate artifacts.
- [ ] Review `docs/tasks/completed/T008-movement-system-and-turn-buffering.md`
  for the 8.8 fixed-point position contract.
- [ ] Review `docs/tasks/completed/T013-sprite-rendering-and-animation.md`
  and `docs/tasks/completed/T014-hud-rendering-score-lives-fruit.md` for
  current VDP-A sprite/HUD ownership and evidence commands.

## Implementation notes

The architectural intent is not to rotate runtime gameplay. The gameplay core
continues to use the arcade's 28-column by 36-row coordinate space; rendering
maps that space into the V8's landscape 256x212 output with an 8-pixel top HUD
band, a 196-pixel maze area, and an 8-pixel bottom status band.

The transform should become a single documented code/data path, not a scatter
of ad hoc offsets. Where possible, generate or validate mapping tables from
tracked source data in `tools/`, then consume the generated assets from
assembly. Evidence should make the scale, offsets, cell boundaries, and sample
anchor points explicit enough for a reviewer to catch off-by-one and
orientation mistakes.

This task should preserve T013 slot ownership and T014 HUD behavior:

- Sprite slots `0..4` remain Pac-Man and ghosts.
- Sprite slot `5` remains reserved for fruit/score popup use.
- VDP-A color `0` remains transparent outside sprite and HUD pixels.
- HUD rows stay at y=`0..7` and y=`204..211`.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T015-coordinate-transform-and-rotation/transform_frame.ppm`
  — PPM frame dump from the headless emulator showing transformed Pac-Man and
  ghost positions aligned to the rendered maze and clear of HUD/status bands.
- `tests/evidence/T015-coordinate-transform-and-rotation/transform_tests.txt`
  — stdout from a deterministic transform validation script or harness.
- `tests/evidence/T015-coordinate-transform-and-rotation/transform_vectors.txt`
  — readable summary of transform constants, sample tile/entity mappings,
  sprite anchors, frame hash, and pass/fail results.

**Reviewer checklist** (human ticks these):

- [ ] Frame capture shows Pac-Man and ghosts placed by the final transform,
  not by the temporary T013 review row.
- [ ] Sample anchors for tunnel exits, ghost house door, corners, pellets, and
  energizers align with the visible VDP-B maze.
- [ ] Top and bottom HUD/status bands remain unobstructed.
- [ ] VDP-A remains transparent outside sprite and HUD pixels; the VDP-B maze
  remains visible.
- [ ] Evidence output records transform constants, representative mappings,
  sprite slot fields, frame hash, and deterministic pass/fail results.
- [ ] No gameplay rule, scoring, audio, attract-mode, level progression, or
  HMMM HUD fallback replacement work is introduced.

**Rerun command:**

```bash
python3 tools/build.py
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --dump-frame tests/evidence/T015-coordinate-transform-and-rotation/transform_frame.ppm --hash-frame 60
python3 tools/transform_tests.py --vectors-output tests/evidence/T015-coordinate-transform-and-rotation/transform_vectors.txt --frame-dump tests/evidence/T015-coordinate-transform-and-rotation/transform_frame.ppm > tests/evidence/T015-coordinate-transform-and-rotation/transform_tests.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-18 | Created, state: planned. |

## Blocker (only if state = blocked)

*(None.)*
