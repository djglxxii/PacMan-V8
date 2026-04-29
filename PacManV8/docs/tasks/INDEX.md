# Task Index

Master list of all tasks for Pac-Man for Vanguard 8. The authoritative state of
each task is the location of its file (`planned/` vs `active/` vs `blocked/`
vs `completed/`), not this index — but this index should be kept in sync for
quick scanning.

See `README.md` for the workflow. See `../PLAN.md` for the architectural plan
each task implements against.

**Rule:** at most one task may be in `active/` at a time. Tasks must be
human-approved before advancing.

## Current focus

- Active: *(none — awaiting next task approval)*
- Blocked: *(none)*
- Next proposed: T030 — Frightened visuals + final-2s flash (Phase 9)

T022 was activated and then aborted on 2026-04-25 once an audit
(`../AUDIT-2026-04-25-runtime-integration-gaps.md`) revealed the live
runtime is missing the integration that connects the Phase 1–7 modules
into a playable loop. Phases 9 (Live Gameplay Integration) and 10 (Final
Presentation) were added to address those gaps. T022 will resume after
Phase 10 closes.

## Phase 0 — Project Setup

| ID   | Title                              | State   | Depends on | Evidence type   |
|------|------------------------------------|---------|------------|-----------------|
| T001 | Build system and minimal boot ROM  | completed | none       | frame capture   |

## Phase 1 — ROM Data Extraction

| ID   | Title                              | State   | Depends on | Evidence type   |
|------|------------------------------------|---------|------------|-----------------|
| T002 | Tile extraction from character ROM  | completed | T001       | test output     |
| T003 | Sprite extraction from sprite ROM   | completed | T001       | test output     |
| T004 | Palette extraction and V8 conversion| completed | T001       | test output     |
| T005 | Maze data extraction and semantic map| completed | T002, T004 | test output    |

## Phase 2 — Maze Reconstruction

| ID   | Title                              | State   | Depends on | Evidence type   |
|------|------------------------------------|---------|------------|-----------------|
| T006 | Portrait maze re-authoring for 256x212 | completed | T005       | frame capture   |
| T007 | VDP-B maze render and pellet display| completed | T006       | frame capture   |

## Phase 3 — Gameplay Core

| ID   | Title                              | State   | Depends on | Evidence type   |
|------|------------------------------------|---------|------------|-----------------|
| T008 | Movement system and turn buffering | completed | T007       | test output     |
| T009 | Ghost AI and targeting             | completed | T008       | test output     |
| T010 | Scatter/chase timer and frightened mode| completed | T009    | checklist       |
| T011 | Collision, pellets, and dot-stall  | completed | T008, T010 | test output     |
| T012 | Ghost house logic                  | completed | T009, T010, T011 | checklist       |

## Phase 4 — Rendering Layer

| ID   | Title                              | State   | Depends on   | Evidence type   |
|------|------------------------------------|---------|--------------|-----------------|
| T013 | Sprite rendering and animation     | completed | T003, T008, T009, T010, T012 | frame capture   |
| T014 | HUD rendering (score, lives, fruit)| completed | T013         | frame capture   |
| T015 | Coordinate transform and rotation  | completed | T013, T014   | frame capture   |

## Phase 5 — Audio

| ID   | Title                              | State   | Depends on | Evidence type   |
|------|------------------------------------|---------|------------|-----------------|
| T016 | PSG sound effects (waka, siren, etc)| completed | T011       | checklist       |
| T017 | FM music (intro, intermission, death)| completed | T016      | checklist       |

## Phase 6 — Game Flow

| ID   | Title                              | State   | Depends on       | Evidence type   |
|------|------------------------------------|---------|------------------|-----------------|
| T018 | Game state machine and attract mode| completed | T014, T015, T016 | checklist       |
| T019 | Level progression and speed tables | completed | T018             | test output     |
| T020 | Intermission cutscenes             | completed | T019             | frame capture   |

## Phase 7 — Validation

| ID   | Title                              | State   | Depends on | Evidence type   |
|------|------------------------------------|---------|------------|-----------------|
| T021 | Pattern replay and fidelity testing| completed | T019       | test output     |

## Phase 8 — Polish

| ID   | Title                              | State   | Depends on | Evidence type   |
|------|------------------------------------|---------|------------|-----------------|
| T022 | Visual polish and palette refinement| planned | T038       | frame capture   |

## Phase 9 — Live Gameplay Integration

| ID   | Title                              | State   | Depends on        | Evidence type   |
|------|------------------------------------|---------|-------------------|-----------------|
| T023 | Boot-time game state initialization| completed | none              | frame capture + test output |
| T024 | Controller input → movement request| completed | T023              | test output     |
| T025 | Per-frame PLAYING tick             | completed | T023, T024        | test output     |
| T026 | Z80 arcade→V8 coordinate transform | completed | T023              | test output     |
| T027 | Sprite SAT commit from game state  | completed | T026              | frame capture   |
| T028 | Sprite frame animation             | completed | T027              | frame capture   |
| T029 | Pellet erase to VDP-B framebuffer  | completed | T025              | frame capture   |
| T030 | Frightened visuals + final-2s flash| planned | T027              | frame capture   |
| T031 | Live HUD update                    | planned | T025              | frame capture   |
| T032 | Audio cue bindings                 | planned | T025              | test output     |
| T033 | Game-flow predicate wiring         | planned | T025, T031        | test output     |
| T034 | Integration replay test            | planned | T023–T033         | test output     |

## Phase 10 — Final Presentation

| ID   | Title                              | State   | Depends on        | Evidence type   |
|------|------------------------------------|---------|-------------------|-----------------|
| T035 | Bonus fruit                        | planned | T025, T027, T031  | frame capture   |
| T036 | Score popups                       | planned | T031              | frame capture   |
| T037 | Attract mode demo content          | planned | T027              | frame capture   |
| T038 | READY! / GAME OVER overlays        | planned | T031, T033        | frame capture   |

## Legend

- **Evidence type** gives the reviewer a hint about what kind of artifact
  they'll be checking. Each task file contains the full acceptance criteria.
  - `frame capture` — PPM frame dump from headless emulator
  - `test output` — stdout from extraction tool or headless run
  - `checklist` — manual verification in frontend emulator
