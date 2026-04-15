# T001 — Build System and Minimal Boot ROM

| Field | Value |
|---|---|
| ID | T001 |
| State | completed |
| Phase | Phase 0 — Project Setup |
| Depends on | none |
| Plan reference | `docs/PLAN.md` Phase 0 |

## Goal

Create a working build pipeline and a minimal ROM that boots on the Vanguard 8
emulator, initializes both VDPs to Graphic 4 mode, and displays a solid
background color. This proves the toolchain, ROM packaging, and basic hardware
init before any game logic is attempted.

## Scope

- In scope:
  - `tools/build.py` — Python build script using SjASM, modeled on the
    Vanguard 8 showcase build script
  - `src/main.asm` — entry point with HD64180 MMU setup (CBAR=0x48,
    CBR=0xF0, BBR=0x04), stack init, IM1 interrupt mode
  - VDP-A and VDP-B initialization to Graphic 4, 212-line mode, display
    enabled
  - VDP-A TP bit set (R#8 bit 5) for compositing transparency
  - VDP-B palette entry 0 set to a visible color (e.g., dark blue) to
    confirm VDP-B is active and compositing works
  - IM1 V-blank interrupt handler stub at 0x0038 (reads S#0 to clear flag,
    returns)
  - ROM padded to 16 KB page boundary
  - `run.sh` convenience script to launch in headless emulator

- Out of scope:
  - Any game logic, asset extraction, or rendering beyond a solid color
  - Audio initialization
  - Controller input

## Pre-flight

- [x] `sjasmplus` is on PATH (`/home/djglxxii/.local/bin/sjasmplus`)
- [x] Vanguard 8 emulator binaries exist at expected paths

## Implementation notes

Reference the Vanguard 8 showcase build script at
`/home/djglxxii/src/Vanguard8/showcase/tools/package/build_showcase.py` for
the SjASM invocation pattern, symbol conversion, and ROM padding logic.

Reference `/home/djglxxii/src/Vanguard8/docs/spec/02-video.md` for VDP
register setup (Graphic 4 mode bits, R#0/R#1 values, VRAM layout, palette
write procedure).

Reference `/home/djglxxii/src/Vanguard8/docs/spec/00-overview.md` for
memory map and MMU register values.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T001-build-and-boot/boot.ppm` — PPM frame dump from
  headless emulator showing the solid background color
- `tests/evidence/T001-build-and-boot/boot.png` — PNG preview of the same
  frame for easier visual inspection
- `tests/evidence/T001-build-and-boot/build.log` — build output
- `tests/evidence/T001-build-and-boot/headless.log` — 60-frame headless run
  output, including frame hash and dump metadata
- `tests/evidence/T001-build-and-boot/frame_stats.txt` — PPM dimensions and
  color count summary

**Reviewer checklist** (human ticks these):

- [ ] `python3 tools/build.py` completes without errors
- [ ] `build/pacman.rom` exists and is a multiple of 16,384 bytes
- [ ] `build/pacman.sym` exists with at least the entry point symbol
- [ ] Frame dump shows a solid colored screen (VDP-B background visible
  through VDP-A transparency): `256x212`, one unique RGB color `#000049`
- [ ] No crash or hang in the first 60 frames of headless execution

**Observed values:**

- ROM size: `16,384` bytes
- Symbol count: `7`
- Frame SHA-256 at frame 60:
  `6d50809775a5c8351c94582adc254c4242855455b17560180811caa6ac9864fb`
- Frame dump source: `runtime`
- Frame dump size: `256x212`

**Rerun command:**

```bash
python3 tools/build.py
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --hash-frame 60 --dump-frame tests/evidence/T001-build-and-boot/boot.ppm
```

## Progress log

| Date | Entry |
|------|-------|
| 2026-04-14 | Created, state: planned. |
| 2026-04-15 | Activated task. Pre-flight confirmed `sjasmplus` and Vanguard 8 emulator binaries are available. |
| 2026-04-15 | Built initial minimal ROM and hit unsupported opcode errors while trying to use an alternate headless dump path. Paused work per user instruction so the emulator can be patched rather than working around important missing opcodes. |
| 2026-04-15 | Moved to blocked because emulator opcode support prevents completing the frame-capture evidence. |
| 2026-04-15 | Reactivated after confirming the patched `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` runtime progressed past the earlier unsupported opcodes. It then exposed unsupported opcode `0x2B` in the ROM's CPU framebuffer clear loop, so the boot ROM was changed to use the documented V9938 `HMMV` fill command instead of a CPU byte loop. |
| 2026-04-15 | Produced acceptance evidence: build succeeds, the timed runtime completes 60 frames, and `boot.ppm` is a solid `256x212` dark-blue frame with one unique color `#000049`. Stopping for human review. |
| 2026-04-15 | Accepted by human reviewer and moved to completed. |

## Blocker

**External system:** Vanguard 8 emulator headless runtime.

**Exact symptom:**

- `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless` aborts during
  runtime frame dumping with `Unsupported timed Z180 opcode 0x16 at PC 0x12A`.
- Before the clear-loop rewrite, the same runtime path reported
  `Unsupported timed Z180 opcode 0x0E at PC 0x12A`.
- After the emulator patch, the same CPU byte-loop approach progressed further
  and reported `Unsupported timed Z180 opcode 0x2B at PC 0x130`.
- The `cmake-build-debug` trace path also cannot be used to inspect execution
  because it reports `Unsupported extracted Z180 ED opcode 0x56` for the ROM's
  `IM 1` instruction.

**Minimal repro:**

```bash
python3 tools/build.py
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --hash-frame 60 --dump-frame tests/evidence/T001-build-and-boot/boot.ppm
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --trace tests/evidence/T001-build-and-boot/trace.log --trace-instructions 80 --symbols build/pacman.sym
```

**Resolution used:** The patched timed headless runtime now supports the earlier
blocking opcodes far enough to execute this boot ROM when framebuffer clearing
uses the V9938 `HMMV` command engine. The old CPU byte-loop clear path remains a
useful emulator compatibility finding, but it is no longer required for T001's
minimal boot evidence.
