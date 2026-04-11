# AGENTS.md — Pac-Man → Vanguard 8 Port

This file is the operating contract for any coding agent working in this repo.
Read it fully before taking any action. Re-read it at the start of every new
conversation.

## What this project is

A from-scratch port of arcade Pac-Man to the **Vanguard 8** fantasy console
(`/home/djglxxii/src/Vanguard8/`). The goal is a cartridge ROM that runs on
`vanguard8_frontend` and preserves the arcade's **gameplay**: ghost
personalities, frame-rule timing, Cruise Elroy, fruit schedule, intermissions,
and the characteristic audio.

The **visual presentation necessarily deviates** from the arcade original
because the Vanguard 8's 256×212 landscape framebuffer cannot fit the
arcade's 224×288 portrait playfield pixel-for-pixel in any orientation. The
chosen compromise — maze rotated 90° CCW with sprites and HUD kept upright,
outer tunnel-border rows clipped, HUD overlaid on decorative wall regions —
is documented in `docs/VANGUARD8_PORT_PLAN.md` §2. Do not treat "pixel-
perfect arcade match" as the target; treat "authentic gameplay on Vanguard
8 within its display constraints" as the target.

The design is captured in **`docs/VANGUARD8_PORT_PLAN.md`**. That document is
the architectural source of truth. If you need to deviate from it, update it
first — do not silently diverge.

## Repository layout

```
.
├── CLAUDE.md                         This file
├── docs/
│   ├── VANGUARD8_PORT_PLAN.md        Architectural plan (source of truth)
│   └── tasks/                        Task queue (see docs/tasks/README.md)
│       ├── README.md                 Task workflow rules
│       ├── task-template.md          Template for new task files
│       ├── INDEX.md                  Master task list with states
│       ├── planned/                  Tasks not yet started
│       ├── active/                   Currently in progress (max 1)
│       ├── blocked/                  Waiting on external fix
│       └── completed/                Accepted by human reviewer
├── source_rom/                       MAME Pac-Man ROM set (read-only input)
├── extracted/                        Decoded art + audio from source_rom/
├── tools/
│   └── extract_mame_assets.py        One-shot asset extraction
└── vanguard8_port/                   The cartridge project
    ├── src/                          Z80/HD64180 assembly source
    ├── assets/                       Converted binary assets (INCBIN inputs)
    ├── tools/                        Asset conversion + build scripts
    ├── build/                        Build outputs (pacman.rom, .sym)
    ├── tests/                        Checkpoint hashes, replay fixtures
    └── docs/                         Per-milestone notes and captures
```

Key external references:

- Vanguard 8 spec: `/home/djglxxii/src/Vanguard8/docs/spec/`
  - `00-overview.md` — memory map, I/O ports, MMU, interrupts
  - `01-cpu.md` — HD64180 registers and extended instructions
  - `02-video.md` — dual V9938, modes, VRAM layouts, sprites, compositing
  - `03-audio.md` — YM2151 + AY-3-8910 + MSM5205
  - `04-io.md` — controllers, timing, interrupt wiring
- Showcase ROM as an example build: `/home/djglxxii/src/Vanguard8/showcase/`
- Emulator binary: `/home/djglxxii/src/Vanguard8/build/vanguard8_frontend`

## Operating rules

### 1. Work is task-driven

All work happens inside a task file under `docs/tasks/`. You never do
engineering work that does not correspond to an open task. If the user asks
for something that isn't in a task, either:

- create a new planned task for it and stop for review, OR
- append it to the active task if it's genuinely a sub-step of current work.

See `docs/tasks/README.md` for the full workflow.

### 2. Exactly one task may be active at a time

Before starting work, move the task file from `planned/` to `active/`. When
the user accepts the deliverable, move it to `completed/`. If you hit a
blocker you cannot resolve in-repo (e.g. an emulator bug), move it to
`blocked/` with a note explaining why, and start a new planned task only if
the user authorizes it.

### 3. Every completed task has a human-verifiable deliverable

A task is not "done" because code compiles. A task is done when a human can
look at a screenshot, listen to a capture, or walk a checklist and say "yes,
that matches." Every task's **Acceptance Evidence** section must describe
exactly what artifact the reviewer should inspect and what they should be
checking for.

Preferred evidence types, in priority order:

1. **Frame capture** (PNG from `vanguard8_frontend --headless` or screenshot)
2. **Audio capture** (WAV from the headless runner's audio hash path)
3. **Deterministic replay log** (input sequence + expected tile/state dump)
4. **Agent-authored checklist** the reviewer can tick through manually

Store every artifact under `vanguard8_port/tests/evidence/T###-short-name/`
so it survives into git history alongside the task file.

### 4. Stop for review at every task boundary

When a task's acceptance evidence is ready, **stop and report**. Do not pick
up the next task. The user must explicitly approve the deliverable and point
you at the next one. This is non-negotiable — no silent rollovers.

### 5. Clean-room discipline for game logic

Game behavior (ghost AI, frame rules, speeds, mode timings, targeting) is
implemented from **published behavioral documentation only**. Do not read,
paste, or translate the arcade Z80 disassembly. The extracted graphics and
wavetables in `extracted/` are data assets and fair game; the arcade code in
`source_rom/pacman.6[efhj]` is not a reference for implementation.

If a behavior is underspecified and you can't find a public description,
flag it in the task and ask the user — don't guess by peeking at the ROM.

### 6. Do not invent Vanguard 8 behavior

Only use documented, implemented emulator surfaces. If you need a feature
that isn't in `docs/spec/` or isn't implemented in the current emulator
build, create a **blocked** task describing the exact missing behavior,
and wait for the user to resolve it upstream. Do not work around emulator
bugs by implementing ROM-side hacks.

### 7. Build reproducibility

Every artifact the ROM consumes — palette binaries, tile banks, sprite
tables, music data — must be produced by a script in `vanguard8_port/tools/`
from inputs in `source_rom/` or `extracted/`. Hand-edited binaries in
`assets/` are forbidden. If an asset needs manual authoring (e.g. the maze
layout text file), the authored source lives in `vanguard8_port/assets/src/`
and a conversion script produces the binary.

### 8. No autonomy creep

Do not:

- Commit without being asked.
- Push, tag, or create PRs without being asked.
- Modify files outside this repo tree (especially not `../Vanguard8/`).
- Run `vanguard8_frontend` in GUI mode without the user watching — prefer
  the headless runner for automated evidence capture.
- Mark a task complete on your own authority.

## Session startup checklist

At the start of every conversation:

1. Read this file.
2. Read `docs/tasks/INDEX.md` to see current state.
3. Look in `docs/tasks/active/` — if there's a task there, that's the
   current focus. Resume it.
4. If `active/` is empty, do not grab a planned task on your own. Ask the
   user which task to start next.
5. Read `docs/VANGUARD8_PORT_PLAN.md` sections relevant to the active task
   before writing code.

## Session shutdown checklist

When wrapping up a session:

1. Make sure the active task file reflects the current state (what's done,
   what's left, any new findings).
2. If you produced verifiable evidence, it's under
   `vanguard8_port/tests/evidence/T###-.../` and referenced from the task
   file.
3. Update `docs/tasks/INDEX.md` if a task changed state.
4. Report to the user with: (a) what you did, (b) where the evidence is,
   (c) what decision you need from them.
