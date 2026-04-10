# T001 — Repository scaffold + build driver

| Field | Value |
|---|---|
| ID | T001 |
| State | active |
| Phase | 0 Scaffold |
| Depends on | none |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §3.6, §7.1 |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/00-overview.md` |

## Goal

Stand up the `vanguard8_port/` project scaffold and a working build driver
that produces a valid (but nearly empty) Vanguard 8 cartridge image. This is
the foundation every later task builds on.

## Scope

In scope:

- Populate `vanguard8_port/src/` with:
  - `main.asm` — minimum viable entry point at `ORG 0x0000`, HD64180 MMU
    init (CBAR / CBR / BBR to the Vanguard 8 standard values from the
    spec), stack pointer setup into SRAM at `0x8100`, infinite `halt` loop.
  - `vdp.inc` — shared macros for VDP-A / VDP-B register writes and palette
    writes. May be copied verbatim from the Vanguard 8 showcase
    (`/home/djglxxii/src/Vanguard8/showcase/src/showcase.asm`) with
    attribution in a comment — this is reference code for the spec, not
    game logic, so clean-room discipline does not apply.
- Add `vanguard8_port/tools/pack_rom.py` adapted from
  `/home/djglxxii/src/Vanguard8/showcase/tools/package/build_showcase.py`.
  It must:
  - Invoke `sjasmplus` on `src/main.asm`
  - Produce `build/pacman.rom` and `build/pacman.sym`
  - Pad the ROM image to the next 16 KB page boundary
  - Emit the same reproducible symbol file format used by the showcase
- Add `vanguard8_port/README.md` explaining how to build and run.
- Create empty `.gitkeep` files in `assets/`, `build/`, `tests/` so the
  directories survive until real content lands.

Out of scope:

- Any VDP register configuration (covered by T002)
- Any asset conversion (covered by T003)
- Any game logic

## Implementation notes

The Vanguard 8 boot-time MMU setup is:

```
OUT0 (0x3A), 0x48   ; CBAR — CA0 ends 0x3FFF, CA1 starts 0x8000
OUT0 (0x38), 0xF0   ; CBR  — CA1 physical base = 0xF0000 (SRAM)
OUT0 (0x39), 0x04   ; BBR  — bank window physical base = 0x04000 (bank 0)
```

`OUT0` is an HD64180 instruction — the assembler macro is already in the
showcase's `OUT0_A` macro. Copy it.

The showcase `build_showcase.py` is ~120 lines of straightforward Python.
Adapt paths: `REPO_ROOT` becomes the `vanguard8_port/` directory; source is
`src/main.asm`; output is `build/pacman.rom` and `build/pacman.sym`.

Verify `sjasmplus` is available: `which sjasmplus`. If not installed,
mark this task blocked with a note asking the user to install it (it is a
prerequisite for the whole project).

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/build/pacman.rom` — built ROM, 16384 bytes, with the MMU
  init sequence at offset 0x0000.
- `vanguard8_port/build/pacman.sym` — reproducible symbol file containing
  `reset` and `main_loop`.
- `vanguard8_port/tests/evidence/T001-scaffold/build_log.txt` — captured
  output of a clean `pack_rom.py` run from an empty `build/` directory.
- `vanguard8_port/tests/evidence/T001-scaffold/rom_head.hex` — first 64
  bytes of `pacman.rom` as a hex dump; begins with `3e 48 ed 39 3a`.
- `vanguard8_port/tests/evidence/T001-scaffold/headless_smoke.txt` —
  output from a 1-frame `vanguard8_headless` run proving the ROM loads and
  exits cleanly in the deterministic runtime.

**Reviewer checklist:**

- [ ] `cd vanguard8_port && rm -rf build && python3 tools/pack_rom.py`
      completes with exit code 0
- [ ] `build/pacman.rom` exists, size is a non-zero multiple of 16384
- [ ] `build/pacman.sym` exists and lists `reset`
- [ ] The first 5 bytes of `rom_head.hex` are `3E 48 ED 39 3A`, confirming
      the required `LD A,0x48` + `OUT0 (0x3A),A` MMU init sequence starts at
      offset 0
- [ ] Running `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom
      /home/djglxxii/src/pacman/vanguard8_port/build/pacman.rom --frames 1`
      exits 0 and matches `tests/evidence/T001-scaffold/headless_smoke.txt`
- [ ] `source_rom/`, `extracted/`, and `tools/extract_mame_assets.py` are
      untouched — no regression to the asset extraction pipeline

**Rerun command:**

```
cd /home/djglxxii/src/pacman/vanguard8_port && rm -rf build && python3 tools/pack_rom.py
```

## Progress log

- 2026-04-10 — created, state: planned.
- 2026-04-10 — activated. Verified `sjasmplus` is installed at
  `/home/djglxxii/.local/bin/sjasmplus`. Corrected the ROM-head byte
  expectation in the reviewer checklist: HD64180 `OUT0` writes require the
  accumulator to be loaded first, so the MMU-init sequence begins with
  `LD A,imm` rather than an impossible immediate `OUT0`.
- 2026-04-10 — implemented the `vanguard8_port/` scaffold: `src/main.asm`
  with MMU init and halt loop, shared `src/vdp.inc` macros, `tools/pack_rom.py`,
  and a project `README.md`. Clean-build evidence captured under
  `vanguard8_port/tests/evidence/T001-scaffold/`. Headless smoke test passed
  via `/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --frames 1`.
