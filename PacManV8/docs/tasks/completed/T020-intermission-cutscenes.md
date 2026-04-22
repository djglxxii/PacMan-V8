# T020 — Intermission Cutscenes

| Field | Value |
|---|---|
| ID | T020 |
| State | completed |
| Phase | Phase 6 — Game Flow |
| Depends on | T019 |
| Plan reference | `docs/PLAN.md` Phase 3.8 Level Progression; Phase 5 — Audio; Phase 6 — Game Flow and State Machine |

## Goal

Implement the playable-build intermission cutscene owner so the level `2`,
`5`, and `9` handoffs established by T019 show deterministic, human-reviewable
visual sequences with the existing FM intermission music cue.

## Scope

- In scope:
  - Review the Phase 3.8, Phase 5, and Phase 6 plan sections before
    implementation.
  - Review T017's FM intermission cue, T018's `INTERMISSION` state handoff, and
    T019's level-trigger decisions before changing game-flow code.
  - Add a compact intermission cutscene owner under `src/` with explicit scene
    IDs, frame timers, completion state, and deterministic review data.
  - Implement three distinct cutscene scripts selected from the completed level
    family: after levels `2`, `5`, and `9`.
  - Re-author the intermission visuals for the Vanguard 8 native 256x212
    presentation using existing sprite, coordinate-transform, HUD/audio, and
    VDP update patterns where practical.
  - Trigger the T017 FM intermission music cue from actual intermission flow or
    a documented bridge from the cutscene owner to the existing audio module.
  - Return from `INTERMISSION` into the next-level/ready flow deterministically
    once the cutscene finishes.
  - Add a Python validation harness that records scene selection, frame
    schedule, completion behavior, hashes, and pass/fail results.
  - Produce frame-capture evidence under
    `tests/evidence/T020-intermission-cutscenes/`.

- Out of scope:
  - Pattern replay/fidelity validation; T021 owns full pattern validation.
  - Visual polish beyond clear cutscene readability; T022 owns final polish.
  - New level-speed values, fruit schedules, scatter/chase timing, frightened
    timing, Elroy behavior, or kill-screen behavior.
  - Changing Pac-Man movement physics, ghost targeting, collision, pellet
    handling, ghost-house rules, maze topology, HUD score/life semantics, or
    accepted PSG sound effects.
  - Exact arcade program-code reproduction or use of restricted Pac-Man program
    ROMs. Cutscene behavior should be authored from public behavior
    documentation and project plan constraints.

## Scope changes

*(None.)*

## Pre-flight

- [x] T019 is completed and accepted.
- [x] Confirm no other task is active before activation.
- [x] Review `docs/PLAN.md` Phase 3.8, Phase 5 music notes, and Phase 6 game
  flow state machine.
- [x] Review `docs/tasks/completed/T017-fm-music.md` for the accepted FM
  intermission cue and audio evidence contract.
- [x] Review `docs/tasks/completed/T018-game-state-machine-and-attract-mode.md`
  for accepted state IDs, transition frames, review flags, and current
  `INTERMISSION` handoff behavior.
- [x] Review
  `docs/tasks/completed/T019-level-progression-and-speed-tables.md` for
  intermission trigger decisions after levels `2`, `5`, and `9`.
- [x] Review current `src/game_flow.asm`, `src/level_progression.asm`,
  `src/audio.asm`, `src/sprites.asm`, and `src/main.asm` entry points before
  wiring the cutscene owner.
- [x] Identify public intermission behavior references before encoding scene
  beats. Do not use restricted program ROMs.

## Implementation notes

T019 already records intermission handoff decisions for completed levels `2`,
`5`, and `9`; T020 should consume that decision rather than duplicating level
family logic. Keep scene selection in one owner so later validation can query
"which intermission scene should run after this completed level" without
walking game-flow state.

Prefer a small module such as `src/intermission.asm` plus a harness such as
`tools/intermission_tests.py`. The module should expose enough state for tests
and frame evidence:

- current scene ID
- frame counter within scene
- completion flag
- selected visual script/frame group
- whether the FM intermission cue was requested
- next game-flow state after completion

The visual sequence does not need to be pixel-identical to the arcade
framebuffer; the project plan requires native 256x212 re-authoring. It should
preserve the recognizable arcade intermission beats, timing intent, and level
trigger points while staying inside the established V8 rendering architecture.

If the cutscenes need new sprite poses or text/props, add authored sources or a
scripted generator path so build inputs remain reproducible. Do not hand-edit
binary assets.

Frame-capture evidence should include at least one representative frame from
each of the three intermission scenes and one completion/return frame showing
that game flow leaves `INTERMISSION` deterministically.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T020-intermission-cutscenes/intermission_tests.txt` — stdout
  from a deterministic cutscene selection/timing validation harness.
- `tests/evidence/T020-intermission-cutscenes/intermission_vectors.txt` —
  readable scene IDs, trigger levels, frame schedule, FM cue requests,
  completion behavior, hashes, and pass/fail results.
- `tests/evidence/T020-intermission-cutscenes/intermission_scene_1.ppm` —
  representative frame capture for the level-2 intermission scene.
- `tests/evidence/T020-intermission-cutscenes/intermission_scene_2.ppm` —
  representative frame capture for the level-5 intermission scene.
- `tests/evidence/T020-intermission-cutscenes/intermission_scene_3.ppm` —
  representative frame capture for the level-9 intermission scene.
- `tests/evidence/T020-intermission-cutscenes/intermission_completion.ppm` —
  frame capture or documented equivalent showing deterministic return from
  `INTERMISSION` into the next playable flow.
- `tests/evidence/T020-intermission-cutscenes/intermission_checklist.txt` —
  manual review checklist with frame hashes, ROM hash, and rerun notes.

Current acceptance evidence, regenerated after the 2026-04-22 `RET NC`
timed-opcode emulator patch:

- `intermission_tests.txt` reports `5/5 passed`; sha256
  `d486103bcf5e69753cf11a911e51714b0fd97f5111838547aa0d3b59ad272fcb`.
- `intermission_vectors.txt` records schedule hash
  `9439cc6fdcf0ab6dc9eb7184731d937d02302bdb9c1df28103e60479d21c0833`;
  file sha256
  `726498bbf238e00a3f75be4e6e02fd4ab2850715bf54d2a2c3bdcb189799ea14`.
- `intermission_scene_1.ppm` was dumped at frame `1020`; headless frame hash
  `a79b667aef218838fbe9ef205a615f11606a08a6f73a730d40fe60127cc60a28`;
  file sha256
  `0dc7626d705d6af7f9f511683981af46b9a9295dab3d25812163bc253d683efa`;
  headless log sha256
  `19125c7c01409f1259f2e77e7bc98e15379b2800ba1ce65fd014f829e7458741`.
- `intermission_scene_2.ppm` was dumped at frame `1770`; headless frame hash
  `082dd26d090aa2632128d266bddd6faa0c50b5b96819dfc7e6f02f3276d93066`;
  file sha256
  `5b916d0a62acfa691f7c9be85642daa5f1eb9620f15e1f48885a1ce23f93993a`;
  headless log sha256
  `67f0ad8a02ca0bbe0bc144ce44c64cbf0e577005d768f9f0efcc063ec41ec2e3`.
- `intermission_scene_3.ppm` was dumped at frame `2520`; headless frame hash
  `c80b7468c3a56d2383582b717f17bc36fde775f5821ab4311081d796e4f0a2ff`;
  file sha256
  `397f473d3e81e2f25b8db7926073d8a274153ce183186470621248af813be3d1`;
  headless log sha256
  `654ca5b20c458dd43efce7ba45139def8877c521fe0c723badbe797fa6d4f0dd`.
- `intermission_completion.ppm` was dumped at frame `2640`; headless frame
  hash
  `31f8226ca0fe920a1b85e33ecd0625ba0846439a3a15d146e1497c817285d34c`;
  file sha256
  `7dc5ba37bf9dd9d98aa6df51be29d7d11c5947c680dd398633e199b13a0479bd`;
  headless log sha256
  `16e29ee82f9398b346ea52cc9e920182b7ee35f9de41d0c381f2dadb4530c80c`.
- `intermission_checklist.txt` sha256
  `8c880678b11421591d353fef2d668129c95656661c2dfdb9f97238c7e38ba897`.
- Rebuilt `build/pacman.rom` sha256
  `ac70f956456e2ac188f66d9f26eb96375b119207893973bc176aea36ff1ebb60`;
  `build/pacman.sym` sha256
  `0b34367455b37e469fe10998d460627e677bafc5c0515a1a61289a228ee9124c`.

Stale captured evidence from the rejected 2026-04-20 run. Do not use this set
for acceptance; the PPM/headless files remain for history, and the text/vector
files have since been regenerated for the blocker diagnostics below:

- `intermission_scene_1.ppm` was dumped at frame `108`; headless frame hash
  `9817633e20bdbdbaa8bb32321e3e914bb606f5ac07ded7b1538f1249b135d68b`;
  file sha256
  `3bec0e1586e13e510050c19c223ade8b3acfda96da56a42bdb86c6f4927bc65b`.
- `intermission_scene_2.ppm` was dumped at frame `312`; headless frame hash
  `653afc48f0ee7c48c7aafe0430223304195dd1a86eb6ea71acd0eed859627039`;
  file sha256
  `54b787633109ff64ac478ae7528fe3afda5fb59bf0c1f2810ba17b2199d1b3f6`.
- `intermission_scene_3.ppm` was dumped at frame `516`; headless frame hash
  `4a63cec305375edd4b20e85ba9830d83888e2eaf4327a29c229cfc7ce7a79693`;
  file sha256
  `c0a29b0596a4b01ab1fb061291d74664bb3eed6b3e27342f156450eca5989281`.
- `intermission_completion.ppm` was dumped at frame `636`; headless frame hash
  `e7205ce38fec4490bd466f0e54fbc552d42f8542ccb6069c4349ecdde7846ed8`;
  file sha256
  `7998ee6badd72a65ec204ee4b1e21cb5805306dae72949b72555f74b39c411ff`.
- `intermission_tests.txt` reports `5/5 passed`; sha256
  `c9517cb9dd52ff6ae0d1098880e3ef82bae22c1981ef22e1c026d2c11d408606`.
- `intermission_vectors.txt` records the schedule hash
  `d5e8ddf81c4ad0bc195e28e777e80d25b8a6e5d92184e2905e04d645b6a63561`;
  file sha256
  `13b29773fe238aae13a03474aacabec6f63df729c6c34844a94fc3eb4cb10bb7`.

Current blocker diagnostics, captured after the 2026-04-21 headless
observability update and T020 rewiring:

- `intermission_tests.txt` reports `5/5 passed`; sha256
  `d486103bcf5e69753cf11a911e51714b0fd97f5111838547aa0d3b59ad272fcb`.
- `intermission_vectors.txt` sha256
  `9019f9c6bc083d47fd4b32d9c249092821205747337775d7f7f3cf9c971cf4d0`.
- `halt_resume_probe.txt` shows `--run-until-pc 0x0068:20` does not reach
  the instruction after `HALT`; sha256
  `dcfbc491238dac3a556a05d8321633314620a1a24a9291f7fd13174abdd7700d`.
- `intermission_start_probe.txt` shows `--run-until-pc 0x2EE3:1100` does not
  reach `intermission_start`; sha256
  `de5173578b6a55ff56d024da0790252beb3e8de29f3ebc6916cbba3078db0ef8`.
- `runtime_inspection_1100.txt` shows CPU halted at `PC=0x0067` while
  `GAME_FLOW_FRAME_COUNTER` remains `0x0000` and intermission state remains
  zero; sha256
  `6d3ca4510b3be16a8c9533644a2593e7d6a655e39c2bd43b6068ec33232bd88b`.
- Rebuilt `build/pacman.rom` sha256
  `1dcb64c7f662cb0321d68bd5948c0ab2b4664c9c6f7511eae672a455b766fd37`;
  `build/pacman.sym` sha256
  `0b34367455b37e469fe10998d460627e677bafc5c0515a1a61289a228ee9124c`.

Current blocker diagnostics, captured after the 2026-04-21 HALT-resume patch:

- `intermission_tests.txt` reports `5/5 passed`; sha256
  `d486103bcf5e69753cf11a911e51714b0fd97f5111838547aa0d3b59ad272fcb`.
- `intermission_vectors.txt` sha256
  `726498bbf238e00a3f75be4e6e02fd4ab2850715bf54d2a2c3bdcb189799ea14`.
- `timed_opcode_1e_probe.txt` records the runtime abort at `PC=0x332E`;
  sha256 `a9350a0728bfa07cbbfda165ea43f84a493e4f6b9a35f54f45d3ae4dabb72b7f`.
- Rebuilt `build/pacman.rom` sha256
  `ac70f956456e2ac188f66d9f26eb96375b119207893973bc176aea36ff1ebb60`;
  `build/pacman.sym` sha256
  `0b34367455b37e469fe10998d460627e677bafc5c0515a1a61289a228ee9124c`.

Current blocker diagnostics, captured after the 2026-04-21 `LD E,n` timed
opcode patch:

- `intermission_tests.txt` reports `5/5 passed`; sha256
  `d486103bcf5e69753cf11a911e51714b0fd97f5111838547aa0d3b59ad272fcb`.
- `intermission_vectors.txt` sha256
  `726498bbf238e00a3f75be4e6e02fd4ab2850715bf54d2a2c3bdcb189799ea14`.
- `intermission_scene_1.ppm` was dumped at frame `1020`; headless frame hash
  `a79b667aef218838fbe9ef205a615f11606a08a6f73a730d40fe60127cc60a28`;
  file sha256
  `0dc7626d705d6af7f9f511683981af46b9a9295dab3d25812163bc253d683efa`.
- `intermission_scene_1_headless.txt` sha256
  `2e8ef3ce0ac596b8793edffe12f1671c1f79fde03de7a9218d1e3f6cee507be8`.
- `timed_opcode_d0_probe.txt` records the runtime abort at `PC=0x2F75`;
  sha256 `38b53689a6c75e5b170b57304df1d96b57104fc11e48bce606e1b33d8f3f6254`.
- Rebuilt `build/pacman.rom` sha256
  `ac70f956456e2ac188f66d9f26eb96375b119207893973bc176aea36ff1ebb60`;
  `build/pacman.sym` sha256
  `0b34367455b37e469fe10998d460627e677bafc5c0515a1a61289a228ee9124c`.

**Reviewer checklist** (human ticks these):

- [ ] Completing levels `2`, `5`, and `9` selects three distinct intermission
  scenes through the T019 handoff path.
- [ ] Each captured scene frame is readable at 256x212 and visibly represents
  its authored intermission beat without relying on scaled arcade framebuffer
  output.
- [ ] The FM intermission cue is requested during cutscene flow and T017 PSG/FM
  compatibility expectations are not regressed.
- [ ] Each cutscene completes on a documented frame schedule and returns to the
  next-level/ready flow deterministically.
- [ ] Evidence records scene IDs, trigger levels, frame numbers, hashes, and
  deterministic pass/fail results.
- [ ] T021 pattern replay validation, T022 visual polish, level-speed table
  changes, maze topology changes, and unrelated gameplay/rendering/audio
  changes are not introduced.

**Rerun command:**

```bash
python3 tools/build.py
python3 tools/intermission_tests.py --vectors-output tests/evidence/T020-intermission-cutscenes/intermission_vectors.txt > tests/evidence/T020-intermission-cutscenes/intermission_tests.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 1020 --dump-frame tests/evidence/T020-intermission-cutscenes/intermission_scene_1.ppm --hash-frame 1020 > tests/evidence/T020-intermission-cutscenes/intermission_scene_1_headless.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 1770 --dump-frame tests/evidence/T020-intermission-cutscenes/intermission_scene_2.ppm --hash-frame 1770 > tests/evidence/T020-intermission-cutscenes/intermission_scene_2_headless.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 2520 --dump-frame tests/evidence/T020-intermission-cutscenes/intermission_scene_3.ppm --hash-frame 2520 > tests/evidence/T020-intermission-cutscenes/intermission_scene_3_headless.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 2640 --dump-frame tests/evidence/T020-intermission-cutscenes/intermission_completion.ppm --hash-frame 2640 > tests/evidence/T020-intermission-cutscenes/intermission_completion_headless.txt
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-20 | Created, state: planned. |
| 2026-04-20 | Activated after confirming no other task was active. Beginning plan/code review for implementation. |
| 2026-04-20 | Added `src/intermission.asm`, wired `INTERMISSION` state ownership through `src/main.asm`, `src/game_flow.asm`, and `src/level_progression.asm`, and added `tools/intermission_tests.py` for deterministic scene/timing validation. |
| 2026-04-20 | Rewrote active-path intermission loops and branch math away from unsupported timed emulator opcodes (`DJNZ`, `ADD A,A`, `RLCA`, `JR C/NC`, `ADD HL,BC`) while preserving the authored scene schedule. |
| 2026-04-20 | Rebuilt `build/pacman.rom`, reran the deterministic harness, and captured representative frames at 108, 312, 516, and 636 under `tests/evidence/T020-intermission-cutscenes/`. Evidence is ready for human review; task remains active pending acceptance. |
| 2026-04-20 | Review rejected: the accepted T018/T019 runtime semantics had been altered to work around unsupported timed opcodes. Restored `src/main.asm`, `src/game_flow.asm`, and `src/level_progression.asm` to their accepted behavior and removed T020 wiring from the main ROM until the emulator is patched. |
| 2026-04-20 | Moved to `blocked/`. Do not rely on the current T020 evidence set for acceptance; it was captured from a ROM with out-of-scope timing and frame-pacing changes that have now been reverted. |
| 2026-04-20 | Reactivated after the Vanguard 8 emulator opcode gap was reported fixed. Restored the intended T020 wiring without the earlier ROM-side opcode workarounds, rebuilt successfully, and confirmed the static intermission harness passes `5/5` against the wired source. |
| 2026-04-20 | Re-blocked after runtime verification. The canonical headless emulator no longer aborts on the intermission opcode path, but frame output at the expected intermission review frames remains unchanged from the accepted T018/T019 baseline even when the WIP intermission owner is wired in and forced to issue visible VDP-B writes. Restored `src/main.asm` and `src/game_flow.asm` to the accepted non-T020 wiring until the runtime/frame-observability issue is resolved. |
| 2026-04-21 | Reactivated after new Vanguard 8 headless observability flags were added. Beginning runtime inspection with `--run-until-pc`, CPU/VDP dumps, logical memory peeks, and VRAM dumps before changing ROM code. |
| 2026-04-21 | Reapplied the intended T020 wiring, rebuilt successfully, and confirmed `tools/intermission_tests.py` reports `5/5 passed`. New headless inspection shows the foreground loop remains halted at `idle_loop` `HALT` (`PC=0x0067`) and never reaches `call game_flow_update_frame` at `0x0068`, so `intermission_start` is not hit and runtime frame evidence remains blocked by the canonical emulator/runtime path. |
| 2026-04-21 | Reactivated after the Vanguard 8 emulator HALT resume path was reported patched. Verifying with the recorded `0x0068` foreground-resume and `intermission_start` probes before regenerating frame evidence. |
| 2026-04-21 | Confirmed the emulator HALT-resume patch unblocks foreground game-flow execution: state bytes now advance through ATTRACT, READY, PLAYING, DYING, CONTINUE, LEVEL_COMPLETE, and NEXT_LEVEL. Fixed a ROM-side transition bug where `game_flow_mark_state_seen` clobbered the target state in `B` before timer loading. Re-blocked on the next external timed-core gap: unsupported opcode `0x1E` (`LD E,n`) at `PC=0x332E` in the intermission panel setup path. |
| 2026-04-21 | Reactivated after the Vanguard 8 emulator `LD E,n` timed-opcode gap was reported patched. Verifying the recorded `PC=0x332E` repro before regenerating frame evidence. |
| 2026-04-21 | Confirmed the `LD E,n` patch unblocks the scene-1 intermission drawing path and captured `intermission_scene_1.ppm` at frame `1020` with distinct frame hash `a79b667aef218838fbe9ef205a615f11606a08a6f73a730d40fe60127cc60a28`. Re-blocked on the next external timed-core gap: unsupported opcode `0xD0` (`RET NC`) at `PC=0x2F75` in `intermission_advance_review_index`. |
| 2026-04-22 | Reactivated after the Vanguard 8 emulator `RET NC` timed-opcode gap was reported patched. Verifying the recorded `PC=0x2F75` repro before regenerating frame evidence. |
| 2026-04-22 | Confirmed the `RET NC` patch unblocks the remaining review-scene path. Rebuilt, reran the deterministic harness, captured scene frames at `1020`, `1770`, and `2520`, captured completion at `2640`, refreshed `intermission_checklist.txt`, and verified the four PPM captures are nonblank and visually distinct. Evidence is ready for human review; task remains active pending acceptance. |
| 2026-04-22 | Human reviewer accepted T020 after confirming the frontend-visible review flow shows the cutscenes when waiting long enough from boot. Moving task to completed. |

## Previous Blocker

**External system:** Vanguard 8 canonical headless runtime/compositor
(`cmake-build-debug/src/vanguard8_headless`).

**Exact symptom:** After the timed-opcode gap was fixed, the T020 WIP ROM can
be rebuilt with the intended intermission wiring and no longer crashes the
emulator. However, the runtime frame output never changes at the expected
intermission review points. The source-level harness reports `5/5 passed`, but
the headless frame hash remains the accepted baseline
`4a63cec305375edd4b20e85ba9830d83888e2eaf4327a29c229cfc7ce7a79693` at:

- frame `1020` (scene 1 representative under accepted T018/T019 timing)
- frame `1770` (scene 2 representative)
- frame `2520` (scene 3 representative)
- frame `2640` (scene 3 completion / return-to-ready point)

This persisted across three WIP render strategies inside `src/intermission.asm`:

- original mixed sprite + raw VDP-A VRAM writes
- explicit VDP-A / VDP-B HMMV panel fills
- direct CPU-written VDP-B rectangle fills using `vdp_b_seek_write_bc`

Because the frame output never diverges, T020 cannot currently produce the
required human-verifiable frame-capture evidence under the accepted runtime
timing.

**Minimal repro:** from the T020 WIP integration state that:

- includes `src/intermission.asm` from `src/main.asm`
- routes `GAME_FLOW_STATE_INTERMISSION` to
  `intermission_start` / `intermission_update_frame`
- replaces the hardcoded level-2 review hook with
  `intermission_select_review_level_for_game_flow`

run:

```bash
python3 tools/build.py
python3 tools/intermission_tests.py --vectors-output /tmp/t020_vectors.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 1020 --hash-frame 1020
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 1770 --hash-frame 1770
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 2520 --hash-frame 2520
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 2640 --hash-frame 2640
```

Observed result:

- `tools/intermission_tests.py` prints `5/5 passed`
- all four headless runs report the same frame hash
  `4a63cec305375edd4b20e85ba9830d83888e2eaf4327a29c229cfc7ce7a79693`
  instead of distinct intermission/completion captures

**What resolution would unblock it:** A reliable way to observe the live
intermission runtime in the canonical emulator path. That could be either:

- fixing the headless/runtime video path so post-handoff intermission drawing
  changes the composed frame hashes/dumps, or
- exposing enough supported runtime state inspection in the canonical toolchain
  to prove whether the intermission owner is not being reached versus being
  reached but not presented.

## Resolved Blocker — HALT Resume

**External system:** Vanguard 8 canonical headless runtime CPU/HALT foreground
resume path (`cmake-build-debug/src/vanguard8_headless`).

**Exact symptom:** With the intended T020 integration wired in, the ROM builds
and the deterministic source/symbol harness passes `5/5`, but the live
foreground frame loop never resumes after `idle_loop` executes `HALT`.
The instruction after `HALT` is `call game_flow_update_frame` at `0x0068`; it
is not reached by frame `20`, so the Phase 6 state machine stays in its
initial ATTRACT state and cannot reach T020's intermission owner.

Observed with `--inspect-frame 1100`:

- CPU: `PC=0x0067`, `halted=true`, `IFF1=true`, `IFF2=true`.
- `GAME_FLOW_CURRENT_STATE=0`, `GAME_FLOW_FRAME_COUNTER=0x0000`,
  `GAME_FLOW_STATE_TIMER=0x0078`, `GAME_FLOW_REVIEW_FLAGS=0x01`.
- `INTERMISSION_CURRENT_SCENE=0`, `INTERMISSION_FRAME_COUNTER=0x0000`,
  `INTERMISSION_COMPLETE_FLAG=0`.
- `AUDIO_FRAME_COUNTER=0x0437`, showing the audio/interrupt-side review state
  is advancing while the foreground code after `HALT` is not.

The new observability flags therefore resolve the previous ambiguity: this is
not yet a T020 draw/compositor problem. The intermission owner is not reached
because the accepted T018 foreground update point after `HALT` is not being
executed in the canonical headless runtime.

**Minimal repro:**

```bash
python3 tools/build.py
python3 tools/intermission_tests.py --vectors-output /tmp/t020_vectors.txt
rg -n "idle_loop|intermission_start|game_flow_update_frame" build/pacman.sym
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 20 --run-until-pc 0x0068:20 --symbols build/pacman.sym
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 1100 --run-until-pc 0x2EE3:1100 --symbols build/pacman.sym
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 1100 --inspect-frame 1100 --dump-cpu --peek-logical 0x8230:0x20 --peek-logical 0x8250:0x30 --peek-logical 0x8270:0x10
```

Observed result:

- `tools/intermission_tests.py` prints `5/5 passed`.
- Symbol file contains `idle_loop=0x0066`,
  `game_flow_update_frame=0x2D70`, and `intermission_start=0x2EE3`.
- `--run-until-pc 0x0068:20` reports `not-hit`.
- `--run-until-pc 0x2EE3:1100` reports `not-hit`.
- The frame-1100 inspection reports CPU halted at `0x0067` and the game-flow
  state bytes unchanged from initialization.

**What resolution would unblock it:** The canonical headless runtime should
resume foreground execution at the instruction after `HALT` once the accepted
VBlank/IM1 interrupt service has completed, so the existing T018 frame-loop
contract (`HALT` then `game_flow_update_frame`) actually executes. After that,
rerun the same probes: `0x0068` should be hit early, `GAME_FLOW_FRAME_COUNTER`
should advance, and `intermission_start` should be hit at the documented
handoff frame before T020 frame-capture evidence is regenerated.

## Resolved Blocker — Timed `LD E,n`

**External system:** Vanguard 8 canonical headless runtime timed Z180 opcode
coverage (`cmake-build-debug/src/vanguard8_headless`).

**Exact symptom:** After the HALT-resume patch, the foreground game-flow state
machine advances far enough to enter the T020 intermission handoff path.
The ROM then aborts in the canonical headless runtime with:

```text
Unsupported timed Z180 opcode 0x1E at PC 0x332E
```

`PC=0x332E` is inside `intermission_fill_panel`'s scene-1 panel setup. The
bytes around the confirmed failing site are:

```text
0x3329: 01 18 24    LD BC,0x2418
0x332C: 16 44       LD D,0x44
0x332E: 1E 50       LD E,0x50   ; confirmed missing timed opcode
0x3330: 3E 22       LD A,0x22
0x3332: CD 67 33    CALL intermission_fill_vdp_b_rect
```

This instruction is standard Z80 `LD E,n`, and T020 genuinely needs it for
the accepted rectangle-fill API (`BC=VRAM offset`, `D=height`, `E=width`,
`A=fill byte`). Rewriting the ROM to avoid this opcode would be an out-of-scope
emulator workaround.

**Look-ahead for same active path:** The same `0x1E` opcode is used repeatedly
by T020's current intermission rectangle setup code, so implementing only the
confirmed single PC will almost certainly expose the same opcode again at later
scene/propery setup sites. In the current assembled ROM, `LD E,n` appears in
the intermission drawing block at:

- `0x330E`, `0x3317`, `0x3321`, `0x332E`, `0x3337`, `0x3341`
- `0x3355`, `0x335E`
- `0x3394`, `0x33A1`, `0x33AE`, `0x33BB`

The immediately preceding `LD D,n` (`0x16`) at `0x332C` executed without being
reported missing, so the strongly supported request is specifically `0x1E`
(`LD E,n`), not the whole `LD r,n` family.

**Minimal repro:**

```bash
python3 tools/build.py
python3 tools/intermission_tests.py --vectors-output /tmp/t020_vectors.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless \
  --rom build/pacman.rom \
  --frames 1020 \
  --inspect-frame 1020 \
  --dump-cpu \
  --peek-logical 0x8250:0x30 \
  --peek-logical 0x8270:0x10 \
  --hash-frame 1020
```

Observed result:

- `tools/intermission_tests.py` prints `5/5 passed`.
- The canonical headless runtime aborts with
  `Unsupported timed Z180 opcode 0x1E at PC 0x332E`.

**What resolution would unblock it:** Add timed Z180 support for opcode
`0x1E` (`LD E,n`: `E <- immediate byte`, `PC += 2`, 7 T-states, flags
untouched), with regression coverage that reaches the PacManV8 T020
intermission fill setup path past `PC=0x332E`.

## Resolved Blocker — Timed `RET NC`

**External system:** Vanguard 8 canonical headless runtime timed Z180 opcode
coverage (`cmake-build-debug/src/vanguard8_headless`).

**Exact symptom:** After the `LD E,n` timed-opcode patch, the ROM reaches and
renders the first intermission scene. The next runtime run aborts while
advancing from scene 1 to the next review scene:

```text
Unsupported timed Z180 opcode 0xD0 at PC 0x2F75
```

`PC=0x2F75` is inside `intermission_advance_review_index`. The bytes around
the confirmed failing site are:

```text
0x2F70: 3A 77 82    LD A,(INTERMISSION_REVIEW_INDEX)
0x2F73: FE 02       CP INTERMISSION_REVIEW_LAST_INDEX
0x2F75: D0          RET NC   ; confirmed missing timed opcode
0x2F76: 3C          INC A
0x2F77: 32 77 82    LD (INTERMISSION_REVIEW_INDEX),A
0x2F7A: C9          RET
```

This instruction is standard Z80 `RET NC`. T020 genuinely needs this guard so
the deterministic review driver advances from scenes 1 to 2 to 3 without
walking past the last review scene. Rewriting the ROM around it would be an
out-of-scope emulator workaround.

**Look-ahead for related active-path conditional returns:** The current T020
source uses only this `RET NC` in `src/intermission.asm`. Other accepted
runtime modules contain `RET C` / `RET NC` sites that may become relevant once
deeper gameplay paths are exercised:

- `src/ghost_house.asm`: `RET NC` at line 114; `RET C` at lines 122, 173,
  181, and 189.
- `src/movement.asm`: `RET C` at line 360.
- `src/ghost_ai.asm`: `RET C` at line 392.

For the active T020 cutscene path, the confirmed missing opcode is `0xD0`
(`RET NC`). `RET Z` (`0xC8`) and `RET NZ` (`0xC0`) have already executed in
the intermission path before this failure, so they should not be included in
the emulator request.

**Minimal repro:**

```bash
python3 tools/build.py
python3 tools/intermission_tests.py --vectors-output /tmp/t020_vectors.txt
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless \
  --rom build/pacman.rom \
  --frames 1770 \
  --dump-frame tests/evidence/T020-intermission-cutscenes/intermission_scene_2.ppm \
  --hash-frame 1770 \
  --inspect-frame 1770 \
  --peek-logical 0x8250:0x30 \
  --peek-logical 0x8270:0x10
```

Observed result:

- `tools/intermission_tests.py` prints `5/5 passed`.
- Frame `1020` scene-1 evidence can now be captured successfully.
- The canonical headless runtime aborts with
  `Unsupported timed Z180 opcode 0xD0 at PC 0x2F75` before scene-2 evidence can
  be captured.

**What resolution would unblock it:** Add timed Z180 support for opcode
`0xD0` (`RET NC`: if carry is clear, pop PC from stack and take 11 T-states;
if carry is set, advance PC by one and take 5 T-states; flags untouched), with
regression coverage that reaches the PacManV8 T020 intermission review-index
advance path past `PC=0x2F75`.

**Resolved result:** On 2026-04-22, the same frame-`1770` path completed
without aborting, produced scene-2 frame hash
`082dd26d090aa2632128d266bddd6faa0c50b5b96819dfc7e6f02f3276d93066`,
and allowed scene-3 and completion evidence to be regenerated.
