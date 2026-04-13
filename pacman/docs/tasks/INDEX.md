# Task Index

Master list of all tasks for the Pac-Man → Vanguard 8 port. The authoritative
state of each task is the location of its file (`planned/` vs `active/` vs
`blocked/` vs `completed/`), not this index — but this index should be kept
in sync for quick scanning.

See `README.md` for the workflow. See `../VANGUARD8_PORT_PLAN.md` for the
architectural plan each task implements against.

**Rule:** at most one task may be in `active/` at a time. Tasks must be
human-approved before advancing.

## Current focus

- Active: *(none)*
- Next proposed: **T008**

## Phase 0 — Scaffolding

| ID   | Title                                       | State   | Evidence type       |
|------|---------------------------------------------|---------|---------------------|
| T001 | Repository scaffold + build driver          | completed | checklist + ROM   |
| T002 | Empty ROM boots to known background         | completed | frame capture     |
| T003 | Asset conversion tool stubs                 | completed | checklist           |

## Phase 1 — Visual bring-up

| ID   | Title                                       | State   | Evidence type   |
|------|---------------------------------------------|---------|-----------------|
| T004 | Palette conversion + dual-VDP upload        | completed | frame capture |
| T005 | Tile conversion with 90° rotation           | completed | PNG diff      |
| T006 | Static maze render on VDP-B                 | completed | frame capture |
| T007 | HUD overlay text on VDP-A                   | completed | frame capture |
| T008 | Sprite pattern + color table conversion     | planned | PNG diff        |
| T009 | Static sprite placement (Pac-Man + ghosts)  | planned | frame capture   |

## Phase 2 — Movement

| ID   | Title                                       | State   | Evidence type         |
|------|---------------------------------------------|---------|-----------------------|
| T010 | Controller input reading + debug overlay    | planned | frame capture         |
| T011 | Pac-Man movement with cornering             | planned | video / frame series  |
| T012 | Dot eating + score increment                | planned | frame series + hash   |
| T013 | Power pellet + frightened color swap        | planned | frame capture         |

## Phase 3 — Ghost AI

| ID   | Title                                       | State   | Evidence type         |
|------|---------------------------------------------|---------|-----------------------|
| T014 | Ghost FSM scaffolding + scatter targeting   | planned | deterministic replay  |
| T015 | Blinky direct chase targeting               | planned | deterministic replay  |
| T016 | Pinky 4-ahead targeting (with up bug)       | planned | deterministic replay  |
| T017 | Inky Blinky-vector targeting                | planned | deterministic replay  |
| T018 | Clyde 8-tile cutoff targeting               | planned | deterministic replay  |
| T019 | Mode timing table + reversal on flip        | planned | frame series          |
| T020 | Ghost house dot counter release             | planned | deterministic replay  |
| T021 | Cruise Elroy escalation                     | planned | deterministic replay  |
| T022 | Frightened LFSR pseudo-random turning       | planned | deterministic replay  |

## Phase 4 — Life cycle

| ID   | Title                                       | State   | Evidence type         |
|------|---------------------------------------------|---------|-----------------------|
| T023 | Pac-Man vs ghost collision                  | planned | frame capture         |
| T024 | Ghost eating chain (200/400/800/1600)       | planned | frame capture + hash  |
| T025 | Death animation                             | planned | frame series          |
| T026 | Life reset + respawn                        | planned | frame capture         |
| T027 | Level complete + maze reset                 | planned | frame series          |

## Phase 5 — Scoring and fruit

| ID   | Title                                       | State   | Evidence type   |
|------|---------------------------------------------|---------|-----------------|
| T028 | Fruit spawn scheduler (70 / 170 dots)       | planned | frame capture   |
| T029 | Per-level fruit + points table              | planned | frame capture   |
| T030 | 10 000-point extra life                     | planned | frame + audio   |
| T031 | In-session high score tracking              | planned | frame capture   |

## Phase 6 — Audio

| ID   | Title                                       | State   | Evidence type   |
|------|---------------------------------------------|---------|-----------------|
| T032 | YM2151 driver bring-up + test tone          | planned | audio capture   |
| T033 | Timer-A driven audio sequencer              | planned | audio capture   |
| T034 | Intro jingle                                | planned | audio capture   |
| T035 | Siren voices (normal / frightened / eyes)   | planned | audio capture   |
| T036 | Pac-Man chomp SFX                           | planned | audio capture   |
| T037 | Ghost-eaten + extra-life chimes             | planned | audio capture   |
| T038 | Death jingle                                | planned | audio capture   |

## Phase 7 — Intermissions and polish

| ID   | Title                                       | State   | Evidence type   |
|------|---------------------------------------------|---------|-----------------|
| T039 | Intermission 1 (after level 2)              | planned | frame series    |
| T040 | Intermission 2 (after level 5)              | planned | frame series    |
| T041 | Intermission 3 (after level 9)              | planned | frame series    |
| T042 | Attract mode cycle                          | planned | frame series    |
| T043 | Checkpoint + replay regression suite        | planned | hash manifest   |

## Legend

- **Evidence type** gives the reviewer a hint about what kind of artifact
  they'll be checking. Each task file contains the full acceptance criteria.
- Tasks in Phase 1 and later will not typically be written out in full
  until the preceding phase is accepted — they exist here as placeholders
  with rough scope only. Full task specs for T001–T005 are provided in
  `planned/` as concrete starting points.
