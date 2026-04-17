# Pac-Man for Vanguard 8

This file is the operating contract for any coding agent working in this repo.
Read it fully before taking any action. Re-read it at the start of every new
conversation.

## What this project is

A from-scratch port of arcade Pac-Man to the Vanguard 8 fantasy console. The
gameplay core must be arcade-faithful — patterns, ghost AI, timing, and feel
indistinguishable from the original. The presentation layer is purpose-built
for the Vanguard 8's dual-V9938 VDP hardware, re-authoring visuals to fit
256x212 natively rather than scaling the arcade framebuffer.

The design is captured in **`docs/PLAN.md`**. That document is the
architectural source of truth. If you need to deviate from it, update it
first — do not silently diverge.

## Repository layout

```
.
├── CLAUDE.md                         # Agent operating contract (Claude Code)
├── AGENTS.md                         # Agent operating contract (other agents)
├── docs/
│   ├── PLAN.md                       # Architectural plan (source of truth)
│   └── tasks/
│       ├── README.md                 # Task workflow rules
│       ├── task-template.md          # Template for new task files
│       ├── INDEX.md                  # Master task list with states
│       ├── planned/                  # Tasks not yet started
│       ├── active/                   # Currently in progress (max 1)
│       ├── blocked/                  # Waiting on external dependency
│       └── completed/                # Accepted by human reviewer
├── pacman/                           # MAME arcade ROM files (do not commit)
├── src/                              # Z80/HD64180 assembly source code
├── tools/                            # Python extraction/conversion/build scripts
├── assets/                           # Converted binary assets for ROM inclusion
├── build/                            # Build output: ROM + symbols (gitignored)
├── docs/
│   └── field-manual/                 # Developer's field manual (accumulated learnings)
└── tests/
    └── evidence/                     # Per-task acceptance artifacts
```

Key external references:

- **Vanguard 8 hardware spec** — `/home/djglxxii/src/Vanguard8/docs/spec/`
  Consult for all V9938 VDP register details, VRAM layouts, sprite modes,
  palette format, audio chip registers, I/O ports, and interrupt wiring.
  This is the authoritative hardware reference.

- **Vanguard 8 emulator docs** — `/home/djglxxii/src/Vanguard8/docs/emulator/`
  Consult for emulator-specific behavior, headless runtime options, frame
  dump format, and any known emulator limitations or deviations from spec.

- **Vanguard 8 showcase ROM** — `/home/djglxxii/src/Vanguard8/showcase/`
  Reference for build tooling patterns (SjASM + Python build script), ROM
  packaging, and working V8 assembly code examples.

- **MAME Pac-Man ROM files** — `pacman/` (this repo)
  The source arcade ROM split. See `docs/PLAN.md` "ROM File Inventory"
  for what each file contains and its binary format.

## Build and run

```bash
# Build
python3 tools/build.py

# Run (interactive, human use)
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_frontend build/pacman.rom

# Run (headless, agent/CI use)
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless build/pacman.rom --frames 60
```

The headless binary supports `--frames N`, `--expect-frame-hash`,
`--expect-audio-hash`, PPM frame dumps, and input replay. Use it for
automated build verification and regression testing.

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
blocker you cannot resolve in-repo, move it to `blocked/` with a note
explaining why, and start a new planned task only if the user authorizes it.

### 3. Every completed task has a human-verifiable deliverable

A task is not "done" because code compiles or tests pass. A task is done
when a human can inspect an artifact and confirm correctness. Every task's
**Acceptance Evidence** section must describe exactly what artifact the
reviewer should inspect and what they should be checking for.

Preferred evidence types, in priority order:

1. **Frame capture** — PPM frame dump from the headless emulator showing
   the visual output at a specific frame. The reviewer visually inspects
   the image for correctness (correct colors, layout, tile placement, etc.).
2. **Test output** — stdout/stderr from the headless emulator or a Python
   tool showing pass/fail results, hash matches, or extracted data summaries.
   The reviewer confirms expected values match.
3. **Checklist** — A manually-verified list of observable behaviors (e.g.,
   "ghost reverses direction on mode switch"). The reviewer runs the ROM
   in the frontend emulator and checks each item.

Store every artifact under `tests/evidence/T###-short-name/` so it survives
into git history alongside the task file.

### 4. Stop for review at every task boundary

When a task's acceptance evidence is ready, **stop and report**. Do not pick
up the next task. The user must explicitly approve the deliverable and point
you at the next one. This is non-negotiable — no silent rollovers.

### 5. Do not fabricate capabilities

Only use documented, implemented surfaces of external tools and libraries.
If you need a feature that isn't documented or doesn't work as expected,
create a **blocked** task describing the exact missing behavior and wait for
the user to resolve it. Do not work around bugs with hacks.

If the Vanguard 8 emulator reports an unsupported opcode, stop and report the
exact opcode, PC, command, and minimal repro. Do not rewrite the ROM to avoid
the opcode unless the opcode is clearly accidental or unimportant. Let the user
patch the emulator when the missing opcode is important to the implementation.

**Look ahead for additional missing opcodes before reporting.** Handling
opcodes one at a time has proven slow and tedious — each round trip requires
an emulator patch, rebuild, and re-run. Instead, when you encounter the first
missing opcode:

1. Scan the remaining code you expect to execute in the current task (the
   active code paths, not the entire ROM) and identify any other opcodes
   that are plausibly unimplemented — e.g., instructions from the same
   family (ED-prefixed block ops, DD/FD index-register variants, bit
   instructions on `(IX+d)`/`(IY+d)`, etc.) or unusual instructions you've
   emitted that you haven't yet seen the emulator execute.
2. If practical, probe for them (short test harness, targeted frame runs,
   or static inspection of the assembled listing) to confirm which are
   actually missing versus merely suspected.
3. In the blocker task's **Blocker** section, list **all** anticipated
   missing opcodes — the one that actually tripped, plus any others you
   have strong reason to believe will trip next — so the user can patch
   them in a single pass. Clearly mark which are confirmed-missing versus
   suspected-missing, and include PC/context for the confirmed one.

Do not fabricate opcode requests to pad the list — only include opcodes the
current task genuinely needs.

If any external-tool or emulator error prevents the active task from continuing,
move the task file to `docs/tasks/blocked/`, add a precise **Blocker** section
to the task file, update `docs/tasks/INDEX.md`, report the blocker, and stop.

### 6. Build reproducibility

Every artifact the project consumes must be produced by a script in `tools/`
from tracked inputs. Hand-edited binaries or generated files that bypass the
build pipeline are forbidden. If an asset needs manual authoring, the
authored source lives in a designated source directory and a conversion
script produces the build input.

### 7. No autonomy creep

Do not:

- Commit without being asked.
- Push, tag, or create PRs without being asked.
- Modify files outside this repo tree.
- Mark a task complete on your own authority.
- Add features, refactor code, or make improvements beyond what the active
  task specifies.

### 8. Restricted sources

The following files/directories must NOT be read or used as implementation
reference:

- **`pacman/pacman.6e` through `pacman/pacman.6j`** (program ROMs) — These
  contain the original Pac-Man Z80 machine code. Do not disassemble or
  reverse-engineer the program logic from these files. The gameplay core
  must be implemented from publicly documented Pac-Man behavior (the
  Pac-Man Dossier, etc.), not from disassembly of the arcade code. The
  Python extraction tools may read these files to locate data tables
  (tilemap layout, color assignments) but must not extract or replicate
  program logic.

- **`pacman/82s126.1m` and `pacman/82s126.3m`** (sound PROMs) — These may
  be read by extraction tools for waveform documentation purposes only.
  Audio on the Vanguard 8 is re-authored using the YM2151/AY-3-8910/MSM5205,
  not replicated from arcade waveform data.

The character ROM (`pacman.5e`), sprite ROM (`pacman.5f`), and color PROMs
(`82s123.7f`, `82s126.4a`) ARE permitted extraction sources — these contain
graphical asset data, not program logic.

### 9. Maintain the developer's field manual

As you work, record non-obvious learnings, techniques, and gotchas in
`docs/field-manual/`. This is a knowledge base that captures hard-won
insights — things a future agent (or human) doing similar work would
benefit from knowing but couldn't easily derive from reading the code alone.

**What to record:**

- **Hardware quirks** — VDP behavior that surprised you, register
  interactions that aren't obvious from the spec, timing constraints
  discovered empirically, DMA sequencing requirements.
- **Asset pipeline techniques** — how source ROM formats were decoded,
  bit-packing schemes, palette mapping strategies, coordinate transforms
  between source and target screen geometry.
- **Assembly patterns** — Z80/HD64180 idioms that worked well, pitfalls
  with specific instructions or addressing modes, patterns for
  VBlank-safe VRAM updates, interrupt handling techniques.
- **Tooling lessons** — assembler behaviors, Python build script patterns,
  headless emulator usage tricks, debugging techniques.
- **Porting patterns** — general strategies for translating source hardware
  concepts to the Vanguard 8 (e.g., mapping foreign sprite systems to
  V8's dual-VDP setup, adapting different tile formats, handling resolution
  or aspect ratio differences).
- **Game logic techniques** — AI implementations, state machine patterns,
  timing/frame-budget strategies, input handling approaches that proved
  effective.

**What NOT to record:**

- Things obvious from reading the code or spec.
- Task-specific progress notes (those belong in the task file).
- Anything that duplicates `docs/PLAN.md`.

**Format:** Each entry is a standalone markdown file in `docs/field-manual/`
named descriptively (e.g., `vdp-sprite-overflow-workaround.md`,
`color-prom-palette-mapping.md`). Each file should have:

```markdown
# Title

**Context:** What task or problem prompted this discovery.
**The insight:** What you learned, stated clearly enough to be actionable.
**Example:** A concrete code snippet, register sequence, or before/after
showing the technique in practice.
```

Keep entries concise and self-contained. A good field manual entry is
something you'd want to grep for six months from now when doing similar
work on a different project.

**When to write entries:** At the end of each task, before reporting to
the user, review your work and ask: "Did I learn anything here that wasn't
obvious going in?" If yes, write a field manual entry. Also write entries
whenever you encounter and resolve a surprising bug or hardware behavior,
even mid-task.

## Session startup checklist

At the start of every conversation:

1. Read this file.
2. Read `docs/tasks/INDEX.md` to see current state.
3. Look in `docs/tasks/active/` — if there's a task there, that's the
   current focus. Resume it.
4. If `active/` is empty, do not grab a planned task on your own. Ask the
   user which task to start next.
5. Read `docs/PLAN.md` sections relevant to the active task before writing
   code.

## Session shutdown checklist

When wrapping up a session:

1. Make sure the active task file reflects the current state (what's done,
   what's left, any new findings).
2. If you produced verifiable evidence, it's under
   `tests/evidence/T###-.../` and referenced from the task file.
3. Update `docs/tasks/INDEX.md` if a task changed state.
4. Review your work for field manual entries — write any non-obvious
   learnings to `docs/field-manual/` before signing off.
5. Report to the user with: (a) what you did, (b) where the evidence is,
   (c) any new field manual entries written, (d) what decision you need
   from them.
