# T015 — Coordinate Transform and Rotation Validation

| Field | Value |
|---|---|
| ID | T015 |
| State | completed |
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

- [x] T013 and T014 are completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Orientation, Phase 2 Screen Layout, Phase 4.1,
  and Phase 4.2 before implementation.
- [x] Review `docs/tasks/completed/T006-maze-tile-re-authoring-for-256x212.md`
  and `docs/tasks/completed/T007-vdp-b-maze-render-and-pellet-display.md`
  for the fitted maze framebuffer and coordinate artifacts.
- [x] Review `docs/tasks/completed/T008-movement-system-and-turn-buffering.md`
  for the 8.8 fixed-point position contract.
- [x] Review `docs/tasks/completed/T013-sprite-rendering-and-animation.md`
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

**Observed evidence values:**

- `transform_frame.ppm` SHA-256:
  `c0a29b0596a4b01ab1fb061291d74664bb3eed6b3e27342f156450eca5989281`
- Headless runtime `--hash-frame 60` SHA-256:
  `4a63cec305375edd4b20e85ba9830d83888e2eaf4327a29c229cfc7ce7a79693`
- Headless frame dump source: `runtime`
- Headless frame size: `256x212`
- Event log digest: `6563162820683566367`
- `transform_tests.txt` SHA-256:
  `0633c3a210d486e455bc1f0158410c21c373aa345277373eb362a8b86dd23765`
- `transform_vectors.txt` SHA-256:
  `e1a701a9597efaa6e8c88b45188c2f8d9ff21580ad24f0a12deb3b5f7c25c084`
- `tools/transform_tests.py`: `74/74 passed`
- ROM SHA-256:
  `8384f4863df488a57feba017eb8023b4aa08ac26c8d19a20938ccff247e95caf`
- Generated SAT shadow SHA-256:
  `9297f195f528177eedae9478d1b7bf27f488a43491c591dc1940c8b16ce333b2`
- Generated color shadow SHA-256:
  `5d86eb101f66c814c0fb238448a80c0ae6a26193e62eace05398001198b5e87a`
- Deterministic transformed sprite slots:
  - Pac-Man slot `0`: arcade tile `(14,26)`, fixed `0x7400,0xD400`,
    screen center `(132,156)`, sprite XY `(124,148)`.
  - Blinky slot `1`: arcade tile `(14,14)`, fixed `0x7400,0x7400`,
    screen center `(132,80)`, sprite XY `(124,72)`.
  - Pinky slot `2`: arcade tile `(0,17)`, fixed `0x0400,0x8C00`,
    screen center `(20,99)`, sprite XY `(12,91)`.
  - Inky slot `3`: arcade tile `(14,17)`, fixed `0x7400,0x8C00`,
    screen center `(132,99)`, sprite XY `(124,91)`.
  - Clyde slot `4`: arcade tile `(26,26)`, fixed `0xD400,0xD400`,
    screen center `(228,156)`, sprite XY `(220,148)`.
- Build verification: `python3 tools/build.py` passed; ROM size `49,152`
  bytes, symbol count `103`.
- Regression verification: Python compilation passed for
  `tools/coordinate_transform.py`, `tools/generate_sprite_review_shadow.py`,
  `tools/transform_tests.py`, `tools/sprite_render_tests.py`, and
  `tools/build.py`; `tools/sprite_render_tests.py` passed `8/8` against the
  T015 frame dump.

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-18 | Created, state: planned. |
| 2026-04-19 | Activated task; starting pre-flight review and transform implementation. |
| 2026-04-19 | Implemented `tools/coordinate_transform.py` as the shared 8.8 arcade-to-V8 transform, changed the sprite shadow generator and build to emit transform-derived SAT positions, added `tools/transform_tests.py`, generated frame/text evidence under `tests/evidence/T015-coordinate-transform-and-rotation/`, verified build, headless runtime capture, transform tests, Python compilation, and the legacy sprite render harness. Stopping for human review. |
| 2026-04-19 | Accepted by human reviewer and moved to completed. |

## Blocker (only if state = blocked)

*(None.)*
