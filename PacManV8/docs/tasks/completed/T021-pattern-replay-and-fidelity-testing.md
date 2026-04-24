# T021 — Pattern Replay and Fidelity Testing

| Field | Value |
|---|---|
| ID | T021 |
| State | completed |
| Phase | Phase 7 — Validation |
| Depends on | T019 |
| Plan reference | `docs/PLAN.md` Phase 7 — Validation; Build and Run headless testing notes |

## Goal

Add deterministic pattern replay and fidelity validation so arcade-documented
Pac-Man routes can be replayed against the Vanguard 8 build and checked for
path, timing, score, and ghost-position drift.

## Scope

- In scope:
  - Review `docs/PLAN.md` Phase 7 and the emulator replay/headless
    documentation before implementation.
  - Review completed gameplay-core tasks T008 through T012, level/speed task
    T019, and any accepted game-flow evidence needed to start a replay from a
    deterministic state.
  - Add a reproducible replay asset pipeline that can create or validate
    `.v8r` inputs from tracked, human-readable source under this repo.
  - Add at least two deterministic replay cases:
    - a short movement/cornering route that validates pre-turns, pellet
      consumption, score, and frame count;
    - a longer early-level pattern route that validates ghost positions at
      documented checkpoints and final score/timing.
  - Record checkpoint data for Pac-Man tile position, ghost tile positions,
    score, dots eaten, current level, mode state, and frame count.
  - Run replay cases through the documented headless emulator surface
    (`--replay`, frame hashes, inspection output, and PPM dumps where useful).
  - Add a validation harness that reports per-checkpoint pass/fail details,
    deterministic hashes, ROM hash, replay hash, and any measured drift from
    expected arcade-documented timing.
  - Produce human-verifiable evidence under
    `tests/evidence/T021-pattern-replay-and-fidelity-testing/`.

- Out of scope:
  - Visual polish, palette refinement, or HUD art changes; T022 owns polish.
  - New gameplay features or broad AI rewrites beyond narrow fixes required to
    make already-specified behavior match accepted fidelity checkpoints.
  - Changing maze topology, movement graph, speed tables, scatter/chase tables,
    dot-stall constants, ghost-house rules, or level-progression values without
    updating the plan and explicitly recording the fidelity reason.
  - Level-256 visual corruption unless the plan is updated first.
  - Reading, disassembling, or reverse-engineering restricted Pac-Man program
    ROMs. Replay expectations must come from public behavior documentation,
    previously accepted project evidence, and authored test vectors.

## Scope changes

*(None.)*

## Pre-flight

- [x] T019 is completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Phase 7 validation requirements and known
  frame-rate constraint.
- [x] Review `/home/djglxxii/src/Vanguard8/docs/emulator/02-emulation-loop.md`
  input replay and headless CLI documentation.
- [x] Confirm the current `vanguard8_headless --help` still lists `--replay`,
  `--hash-frame`, `--expect-frame-hash`, `--inspect`, and the needed
  controller input/replay flags.
- [x] Identify the public documentation source(s) used for each pattern and
  checkpoint before encoding expected values.

## Implementation notes

The emulator `.v8r` format is binary and ROM-hash anchored. Keep authored
pattern sources in a readable format, then generate replay files with a tool
under `tools/` so replay assets are reproducible from tracked inputs. The tool
should write the current `build/pacman.rom` SHA-256 into generated replays and
should fail clearly when the ROM hash changes without regenerated evidence.

Prefer a harness such as `tools/pattern_replay_tests.py` that:

- builds or verifies the replay files;
- runs `vanguard8_headless --rom build/pacman.rom --replay <case>.v8r`;
- collects frame hashes, inspection output, and selected PPM dumps;
- compares checkpoints against authored expectations;
- writes readable vectors and a concise pass/fail transcript.

Checkpoint expectations should be expressed in game-space terms where
possible, not just framebuffer hashes. Frame hashes and PPMs are useful
regression artifacts, but the fidelity question is whether Pac-Man, ghosts,
score, mode, and timing match the expected path at named checkpoints.

If a replay exposes drift caused by an earlier task, keep fixes narrow and
well-evidenced. Any intentional deviation from arcade timing or public pattern
expectations must be recorded in the task file with the exact reason and
measured impact.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T021-pattern-replay-and-fidelity-testing/pattern_replay_tests.txt`
  — stdout from the deterministic replay validation harness.
- `tests/evidence/T021-pattern-replay-and-fidelity-testing/pattern_replay_vectors.txt`
  — readable pattern metadata, public sources, checkpoint expectations,
  observed values, replay hashes, ROM hash, frame hashes, and pass/fail
  results.
- `tests/evidence/T021-pattern-replay-and-fidelity-testing/replays/` —
  generated `.v8r` replay files, if tracked as evidence, or a manifest naming
  the generated replay files and their SHA-256 hashes.
- `tests/evidence/T021-pattern-replay-and-fidelity-testing/*.ppm` —
  representative frame captures for the short route and the longer pattern at
  meaningful checkpoints.

**Reviewer checklist** (human ticks these):

- [ ] The short replay proves deterministic input playback, pre-turn behavior,
  pellet scoring, and frame count.
- [ ] The longer pattern replay reports Pac-Man and ghost positions at named
  checkpoints, with score and timing matching the documented expectations or
  explicitly measured drift.
- [ ] Evidence includes ROM hash, replay hashes, frame hashes, and readable
  checkpoint vectors.
- [ ] Replay assets are reproducible from tracked human-readable source and a
  tool under `tools/`.
- [ ] No restricted Pac-Man program ROMs were read or used as a behavior
  reference.
- [ ] Visual polish, palette changes, unrelated gameplay rewrites, and T022
  work are not introduced.

**Rerun command:**

```bash
python3 tools/build.py
python3 tools/pattern_replay_tests.py \
  --evidence-dir tests/evidence/T021-pattern-replay-and-fidelity-testing \
  > tests/evidence/T021-pattern-replay-and-fidelity-testing/pattern_replay_tests.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-22 | Created, state: planned. |
| 2026-04-22 | Activated after confirming no other active task and T019 completed. Beginning plan, emulator, and prior gameplay-task review. |
| 2026-04-22 | Added an opt-in replay validation SRAM surface in `src/pattern_replay.asm`, wired it into the frame loop, added human-readable replay sources under `tests/replays/pattern_sources/`, and added `tools/pattern_replay_tests.py` to generate `.v8r` files and run headless checkpoint inspections. Build and Python compilation passed, but the first replay validation run is blocked by missing timed-opcode support in the Vanguard 8 headless emulator. |
| 2026-04-22 | Verified the no-input path remains inert with a 60-frame headless smoke run: frame hash `4a63cec305375edd4b20e85ba9830d83888e2eaf4327a29c229cfc7ce7a79693`, event log digest `6563162820683566367`. Moved task to blocked per workflow. |
| 2026-04-22 | User reported the emulator was patched. Moved task back to active and resuming replay evidence generation. |
| 2026-04-22 | Rebuilt the ROM and reran `tools/pattern_replay_tests.py`; the patched emulator passed the earlier `DEC BC`/register-pair/CB-prefix gaps but stopped on a new timed opcode gap, `0xEB` (`EX DE,HL`) at `PC=0x11DA` in `collision_init`. Moving task back to blocked. |
| 2026-04-22 | User reported the emulator was patched for the latest blocker. Moved task back to active and resuming replay evidence generation. |
| 2026-04-22 | Rebuilt the ROM and reran `tools/pattern_replay_tests.py`; the patched emulator passed the `EX DE,HL` and `OR (HL)` site, then stopped on a new timed CB-prefixed opcode gap, `0xCB 0x3C` (`SRL H`) at `PC=0x1302` in `collision_tile_info`. Moving task back to blocked. |
| 2026-04-23 | Vanguard8 milestone M42 then M43 cleared the remaining emulator-side blockers relevant to this task: timed `SCF` support was added, and the headless inspection emitter now prints logical peek rows with 4-digit `0xHHHH:` prefixes while preserving 5-digit physical `0xHHHHH:` rows. |
| 2026-04-23 | Re-ran `tools/pattern_replay_tests.py` against the rebuilt Vanguard8 binary. The task still fails with `inspection report did not contain logical 0x8270:13`, but direct inspection shows the Vanguard8 report is now correct. The remaining resume point is local to PacManV8: `tools/pattern_replay_tests.py` currently defines `BYTE_ROW_PATTERN = re.compile(r"^\\\\s+0x([0-9a-f]{4}):((?: [0-9a-f]{2})+)$")`, which matches a literal `\\s` sequence rather than leading whitespace. |
| 2026-04-23 | User reported the emulator-side fixes are in place and updated the task with the remaining local parser issue. Moved T021 back to active, fixed the `BYTE_ROW_PATTERN` whitespace regex in `tools/pattern_replay_tests.py`, and resumed the full replay evidence run. |
| 2026-04-23 | The parser fix worked: `tools/pattern_replay_tests.py` advanced far enough to generate `tests/evidence/T021-pattern-replay-and-fidelity-testing/replays/early-level-pattern.v8r` and `early-level-pattern_frame_0169.ppm`. The task is blocked again by a new timed-opcode gap in Vanguard8: `0x93` (`SUB E`) at `PC=0x0FAE` in `ghost_update_all_targets`. Direct replay repro now shows `--frames 443` passes and `--frames 444` fails. Moving task back to blocked. |
| 2026-04-23 | User reported the emulator was patched for the `SUB E` timed-opcode blocker. Moved T021 back to active and resuming replay evidence generation. |
| 2026-04-23 | Rebuilt and reran replay validation. The `SUB E` blocker is resolved. Fixed a local PacManV8 runtime movement bug where `movement_try_turn_at_center` lost the requested direction because `movement_direction_passable_from_current_tile` clobbered `B`, causing Pac-Man to stop immediately. The replay now reaches pellet consumption and is blocked by a new Vanguard8 timed opcode gap, `0xA3` (`AND E`) at `PC=0x125B`. Direct repro shows `--frames 39` passes and `--frames 40` fails. Moving task back to blocked. |
| 2026-04-24 | User reported the emulator was patched for the `AND E`/`AND (HL)` blocker (Vanguard8 commit `16bc3c5` "Add timed AND opcode coverage"). Moved T021 back to active, rebuilt the ROM, and re-ran `tools/pattern_replay_tests.py`. The AND blocker is resolved and the replay advances into `movement_distance_to_next_center_px`, where it stops on a new timed-opcode gap: `0xD6` (`SUB n`) at `PC=0x3EA`. Moving task back to blocked. |
| 2026-04-24 | User reported the emulator was patched for the ALU register/immediate tail (`SUB n`, `SUB r`, `ADC A,r`, `SBC A,r`, `XOR r`, `ADC A,n`, `SBC A,n`, `XOR n`). Rebuilt ROM and re-ran `tools/pattern_replay_tests.py`: both cases now pass end-to-end. `short-corner-route` (4 checkpoints at frames 90/137/185/242) and `early-level-pattern` (5 checkpoints at frames 90/169/265/449/598) all match expected vectors; replay SHAs `3bca8153…397a3f48` and `95c7bea8…5b0423d`; ROM SHA `a423b8a9…52934a`. Evidence refreshed under `tests/evidence/T021-pattern-replay-and-fidelity-testing/`. Stopping for human review. |

## Blocker

*(Resolved — see "ALU register/immediate tail timed opcode blocker" under
Prior resolved blocker history. Task is active and awaiting human review of
the evidence artifacts listed under Acceptance Evidence.)*

## Prior resolved blocker history (ALU tail)

### ALU register/immediate tail timed opcode blocker

**External system:** Vanguard 8 headless emulator timed HD64180/Z180 execution
path at `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless`.

**Pre-patch symptom:**

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  Unsupported timed Z180 opcode 0xD6 at PC 0x3EA
```

**Confirmed missing opcode (pre-patch):**

- `0xD6` / `SUB n`, confirmed at `PC=0x3EA` in
  `movement_distance_to_next_center_px`, on the `.negative_after_center`
  branch executed when Pac-Man is moving LEFT or UP and is past the tile
  center: [src/movement.asm](/home/djglxxii/src/PacManV8/src/movement.asm:325).
- Listing correlation from the rebuilt ROM (bytes around `0x3E7..0x3EC`):
  ```text
  03E7 C6 04    add a, MOVEMENT_TILE_CENTER    ; .horizontal_left / .vertical_up path
  03E9 C9       ret
  03EA D6 04    sub MOVEMENT_TILE_CENTER       ; .negative_after_center  <-- FAILING
  03EC C9       ret
  ```

**Minimal direct repro:**

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless \
  --rom build/pacman.rom \
  --replay tests/evidence/T021-pattern-replay-and-fidelity-testing/replays/early-level-pattern.v8r \
  --frames 60 \
  --hash-frame 60
```

`tools/pattern_replay_tests.py` reproduces the same trap on its first
short-route run (exit code 250).

**Additional anticipated missing opcodes for this same active code path:**

After inspecting the Vanguard8 timed-dispatch table in
`/home/djglxxii/src/Vanguard8/src/core/cpu/z180_adapter.cpp` (`opcode_tstates`
switch, ~lines 350–492), several instruction families used by the arcade-core
code path are still missing from the timed surface. The emitted code will hit
them as soon as Pac-Man turns or the ghost-targeting code runs.

- **Confirmed same-function next trap (sibling of the current fail site):**
  - `0x90` / `SUB B`, used three times in `movement_distance_to_next_center_px`
    on the `.horizontal_right`, `.vertical_down`, and `.positive_before_center`
    branches: [src/movement.asm](/home/djglxxii/src/PacManV8/src/movement.asm:294),
    [src/movement.asm](/home/djglxxii/src/PacManV8/src/movement.asm:303),
    [src/movement.asm](/home/djglxxii/src/PacManV8/src/movement.asm:308).
    ROM bytes confirm opcode `0x90` emitted at `0x3BE`, `0x3CA`, and `0x3D2`.
    The current dispatch table lists only `0x91` (`SUB C`) and `0x93`
    (`SUB E`); every other `SUB r` (`0x90`, `0x92`, `0x94`, `0x95`, `0x96`,
    `0x97`) is missing. Moving Pac-Man RIGHT or DOWN during the replay will
    trip `0x90` immediately.
  - `0xD6` / `SUB n` also appears at
    [src/movement.asm](/home/djglxxii/src/PacManV8/src/movement.asm:363)
    (`sub MOVEMENT_MAZE_WIDTH_PX` in `movement_apply_tunnel_wrap`), so the
    same opcode will also be hit by tunnel-wrap logic once patched here.

- **Strongly suspected same-path traps in ghost AI (runs every frame):**
  - `0x87` / `ADD A,A`, used in `ghost_update_all_targets` at
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:580) and
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:588)
    (Inky X/Y target computation — the same function that previously tripped
    `SUB E`), and in `ghost_advance_frightened_prng` at
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:404) and
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:405). The
    dispatch table contains no `ADD A,r` entry in the `0x80..0x87` range.
  - `0x80` / `ADD A,B`, used at
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:388) and
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:406)
    (same Inky-targeting / frightened PRNG paths as above).
  - `0xA8` / `XOR B`, used at
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:243).
    The table supports only `0xAF` (`XOR A`); every other `XOR r`
    (`0xA8..0xAD`, `0xAE`) is missing.

- **Suspected broader family gaps worth closing in the same pass:**
  - `0xCE` (`ADC A,n`), `0xDE` (`SBC A,n`), `0xEE` (`XOR n`) — the immediate
    arithmetic peers of the confirmed `0xD6`. The table already covers
    `ADD A,n`, `AND n`, `OR n`, `CP n`, so these three are the natural
    complement.
  - `0x88..0x8F` (`ADC A,r`) and `0x98..0x9F` (`SBC A,r`) — no entries in the
    current dispatch table. Not confirmed reached by the current replay, but
    natural neighbors of the above gaps.

**Resolution (applied):**

The Vanguard8 agent closed the entire ALU register/immediate timed-opcode
tail in a single patch per the recommendation below. After rebuilding the
emulator and the PacManV8 ROM, `tools/pattern_replay_tests.py` advances to
completion and both replay cases pass end-to-end.

**Original recommended fix (now applied):**

### Recommended fix (Vanguard8 repo)

**File to edit:** `src/core/cpu/z180_adapter.cpp`, function
`Z180Adapter::current_instruction_tstates()` (starts at line 335 in the
current checkout).

**Step 1 — add four new range-checks for the remaining register-ALU
families.** Insert these alongside the existing range-checks, right after
the `AND r` block (currently near line 348) and before the opening
`switch (opcode)`:

```cpp
    // ADC A,r  (0x88..0x8F; 0x8E = ADC A,(HL))
    if (opcode >= 0x88U && opcode <= 0x8FU) {
        return opcode == 0x8EU ? 7 : 4;
    }
    // SUB r    (0x90..0x97; 0x96 = SUB (HL))
    if (opcode >= 0x90U && opcode <= 0x97U) {
        return opcode == 0x96U ? 7 : 4;
    }
    // SBC A,r  (0x98..0x9F; 0x9E = SBC A,(HL))
    if (opcode >= 0x98U && opcode <= 0x9FU) {
        return opcode == 0x9EU ? 7 : 4;
    }
    // XOR r    (0xA8..0xAF; 0xAE = XOR (HL))
    if (opcode >= 0xA8U && opcode <= 0xAFU) {
        return opcode == 0xAEU ? 7 : 4;
    }
```

These range-checks subsume several opcodes that are already handled
explicitly further down the function. Remove the now-redundant explicit
entries to keep a single source of truth:

- `case 0x91:` and `case 0x93:` in the `return 4` block (current lines
  384–385). Both are covered by the new `SUB r` range-check.
- `case 0xAF:` in the `return 4` block (current line 376). Covered by the
  new `XOR r` range-check.

Do **not** touch the existing explicit `OR r` (`0xB0..0xB7`) or
`CP r` (`0xB8..0xBF`) entries — those ranges are already fully covered and
are out of scope for this patch.

**Step 2 — add the four missing immediate-arithmetic peers to the existing
uniform-7-cycle group.** The `return 7` case-label list (current lines
439–452) already contains `ADD A,n` (`0xC6`), `AND n` (`0xE6`), `OR n`
(`0xF6`), and `CP n` (`0xFE`). Add the four missing peers in the same
block:

```cpp
    case 0xCE:   // ADC A,n
    case 0xD6:   // SUB n           <-- confirmed failing at PC=0x3EA
    case 0xDE:   // SBC A,n
    case 0xEE:   // XOR n
        return 7;
```

**Step 3 — tests.** Extend `tests/test_cpu.cpp` with timed-opcode coverage
for the new families, following whatever pattern the earlier milestone tests
(e.g., the `SUB C/E` and `AND r` tests) use. At minimum, assert that
`current_instruction_tstates()` returns:

- 4 for each register form of `ADC A,r` (`0x88..0x8D`, `0x8F`),
  `SUB r` (`0x90..0x95`, `0x97`), `SBC A,r` (`0x98..0x9D`, `0x9F`), and
  `XOR r` (`0xA8..0xAD`, `0xAF`).
- 7 for the four `(HL)` forms: `ADC A,(HL)` (`0x8E`), `SUB (HL)` (`0x96`),
  `SBC A,(HL)` (`0x9E`), `XOR (HL)` (`0xAE`).
- 7 for each immediate form: `ADC A,n` (`0xCE`), `SUB n` (`0xD6`),
  `SBC A,n` (`0xDE`), `XOR n` (`0xEE`).

Cycle counts above follow the same Z180 ALU timing already used by the
existing `ADD A,r` and `AND r` range-checks — no Z180-specific deviations
apply to these families.

**Total diff:** ~18 lines added to `z180_adapter.cpp`, 3 lines removed
(redundant explicit `0x91`, `0x93`, `0xAF` entries), plus test additions.

### Verification command (from PacManV8, after the emulator is patched and rebuilt)

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
python3 tools/pattern_replay_tests.py \
  --evidence-dir tests/evidence/T021-pattern-replay-and-fidelity-testing \
  > tests/evidence/T021-pattern-replay-and-fidelity-testing/pattern_replay_tests.txt
```

Any new `Unsupported timed Z180 opcode` trap beyond these families becomes
the next blocker entry in this task file.

## Prior resolved blocker history

### AND E / AND (HL) timed opcode blocker

**External system:** Vanguard 8 headless emulator timed HD64180/Z180 execution
path at `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless`.

**Exact confirmed symptom (pre-patch):**

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  Unsupported timed Z180 opcode 0xA3 at PC 0x125B
```

**Confirmed missing opcode (pre-patch):**

- `0xA3` / `AND E`, confirmed at `PC=0x125B` in `collision_consume_tile`
  while checking whether the pellet bit under Pac-Man is still present
  ([src/collision.asm](/home/djglxxii/src/PacManV8/src/collision.asm:164)).
  The suspected companion `0xA6` (`AND (HL)` at `PC=0x1260`) was confirmed
  on the same success path.

Resolved by Vanguard8 commit `16bc3c5` ("Add timed AND opcode coverage"),
which added the full `AND r` / `AND (HL)` range in a single pass.

### SUB E timed opcode blocker

**External system:** Vanguard 8 headless emulator timed HD64180/Z180 execution
path at `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless`.

**Exact confirmed symptom:**

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  Unsupported timed Z180 opcode 0x93 at PC 0xFAE
```

**Confirmed missing opcode:**

- `0x93` / `SUB E`, confirmed at `PC=0x0FAE` in `ghost_update_all_targets`
  while computing Inky's X target from the early-level replay path:
  [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:585).
- Listing correlation from the rebuilt ROM:
  ```text
  0FA9 3A 20 81   ld a, (GHOST_BLINKY_X_TILE)
  0FAC 5F         ld e, a
  0FAD 7A         ld a, d
  0FAE 93         sub e
  0FAF 32 35 81   ld (GHOST_INKY_TARGET_X), a
  ```

**Minimal direct repro found in this session:**

- `--frames 443` passes.
- `--frames 444` fails with the timed-opcode trap above.

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless \
  --rom build/pacman.rom \
  --replay tests/evidence/T021-pattern-replay-and-fidelity-testing/replays/early-level-pattern.v8r \
  --frames 444 \
  --inspect-frame 444 \
  --inspect /tmp/t021-444.txt \
  --peek-logical 8270:13 \
  --hash-frame 444
```

**Additional anticipated missing opcodes for this same active code path:**

- **Confirmed same-opcode sites already present later in the current replay
  path:**
  - `0x93` / `SUB E` at `PC=0x0FBA` in `ghost_update_all_targets`
    ([src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:593)).
  - `0x93` / `SUB E` at `PC=0x1053` and `PC=0x1062` in
    `ghost_clyde_chases_pacman`
    ([src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:714),
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:723)).
- **Suspected same-family next traps once `0x93` is implemented:**
  - `0x91` / `SUB C` at `PC=0x1169` and `PC=0x117A` in
    `ghost_candidate_distance`
    ([src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:880),
    [src/ghost_ai.asm](/home/djglxxii/src/PacManV8/src/ghost_ai.asm:889)).
  - These `SUB C` sites are in the immediate ghost-direction evaluation path
    reached after target updates during the same replay route, so they are the
    most plausible next timed-opcode gaps to patch alongside `0x93`.

**Resolution needed to resume T021:**

- Add timed headless support for `0x93` (`SUB E`) in the Vanguard8 emulator.
- Strongly consider patching `0x91` (`SUB C`) in the same pass, since the
  current T021 replay path enters `ghost_candidate_distance` immediately after
  the now-failing target-update path.
- After the emulator is patched, rerun the documented T021 evidence command.
  Any new failure beyond these sites should become the next blocker entry.

### EX DE,HL timed opcode blocker

**External system:** Vanguard 8 headless emulator timed HD64180/Z180 execution
path at `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless`.

**Exact confirmed symptom:**

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  Unsupported timed Z180 opcode 0xEB at PC 0x11DA
```

**Confirmed missing opcode:**

- `0xEB` / `EX DE,HL`, confirmed at `PC=0x11DA` while executing
  `collision_init` from the T021 replay validation path. The command that
  reproduced it was:

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
mkdir -p tests/evidence/T021-pattern-replay-and-fidelity-testing
python3 tools/pattern_replay_tests.py \
  --evidence-dir tests/evidence/T021-pattern-replay-and-fidelity-testing \
  > tests/evidence/T021-pattern-replay-and-fidelity-testing/pattern_replay_tests.txt
```

The relevant ROM bytes around the failure are:

```text
000011d0: fe 02 28 06 fe 03 28 14 18 22 eb 3a 12 82 b6 77
                                          ^^
                                          EX DE,HL at PC=0x11DA
```

`build/pacman.sym` maps the surrounding code to `collision_init`
(`collision_init` begins at `0x1198`). Source context:

```asm
.set_pellet:
        ex de, hl
        ld a, (COLLISION_WORK_MASK)
        or (hl)
        ld (hl), a
        ex de, hl
```

**Strongly suspected next timed-opcode gap in the same immediate path:**

- `0xB6` / `OR (HL)`, immediately after the confirmed `EX DE,HL` site in
  `collision_init`. This was suspected from the earlier timed-dispatch table
  and is now apparently resolved by the current emulator patch.

**Previously blocked opcode history, now apparently resolved by the emulator
patch:** `0x0B` / `DEC BC`, `0x13` / `INC DE`, `0x2B` / `DEC HL`, and the
needed `0xCB` prefix forms (`SRL A`, `BIT 4,A`, `BIT 5,A`, `BIT 6,A`,
`BIT 7,A`) are now present in the inspected timed-dispatch table.

**Resolution needed to unblock T021:** patch/rebuild the Vanguard 8 headless
emulator timed opcode surface for confirmed `EX DE,HL` and likely same-path
`OR (HL)`, then rerun the command above. Do not change PacManV8 to avoid these
opcodes; they are normal Z80 instructions used by the gameplay validation
path.

### DEC BC timed opcode blocker

**External system:** Vanguard 8 headless emulator timed HD64180/Z180 execution
path at `/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless`.

**Exact confirmed symptom:**

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  Unsupported timed Z180 opcode 0xB at PC 0x1209
```

**Confirmed missing opcode:**

- `0x0B` / `DEC BC`, confirmed at `PC=0x1209` while executing
  `collision_init` from the T021 replay validation path. The command that
  reproduced it was:

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
python3 tools/pattern_replay_tests.py \
  --evidence-dir tests/evidence/T021-pattern-replay-and-fidelity-testing
```

The relevant ROM bytes around the failure are:

```text
00001200: 87 20 03 3e 01 13 32 12 82 0b 78 b1 20 c1 c9 af
                                  ^^
                                  DEC BC at PC=0x1209
```

`build/pacman.sym` maps the surrounding code to `collision_init`
(`collision_init` begins at `0x1198`).

**Strongly suspected next timed-opcode gaps in the same active T021 path:**

- `0x13` / `INC DE`, used in `collision_init` when advancing to the next
  pellet-bitset byte after each 8-cell mask wrap. The current emulator
  timed-dispatch table does not list `0x13`.
- `0x2B` / `DEC HL`, used by `ghost_mode_tick` / `ghost_mode_tick_frightened`
  and score/dot bookkeeping paths reached by replay validation. The current
  emulator timed-dispatch table does not list `0x2B`.
- `0xCB` prefix for `SRL A` and `BIT b,A` forms. Existing movement/collision
  code uses `SRL A`; the new replay input decoder uses `BIT 7,A`, `BIT 5,A`,
  `BIT 6,A`, and `BIT 4,A`. The current emulator timed-dispatch table does
  not list base opcode `0xCB`, so the replay path is expected to fail on the
  first CB-prefixed instruction after `collision_init` can complete.

**Resolution needed to unblock T021:** patch/rebuild the Vanguard 8 headless
emulator timed opcode surface for the confirmed `DEC BC` gap and the listed
same-path register-pair/CB-prefixed gaps, then rerun the command above. Do not
change PacManV8 to avoid these opcodes; they are normal Z80 instructions used
by the gameplay validation path.
