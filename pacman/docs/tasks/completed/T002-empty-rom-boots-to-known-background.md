# T002 — Empty ROM boots to known background

| Field | Value |
|---|---|
| ID | T002 |
| State | completed |
| Phase | 0 Scaffold |
| Depends on | T001 |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §5.3, §6 |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/02-video.md` |

## Goal

Prove the ROM can initialize both V9938 chips into their target modes and
present a stable, deterministic background image on real hardware (via the
emulator). This is the "hello world" of the project and the smoke test for
every later visual task.

## Scope

In scope:

- Initialize VDP-B into **Graphic 4** (256×212, 4bpp, LN=1, TP=1).
- Initialize VDP-A into **Graphic 3** (tile mode + Sprite Mode 2, LN=1,
  TP=1, display enabled).
- Upload a **test palette** to each VDP:
  - VDP-B slot 0 = dark blue (`R=0 G=0 B=3`), slots 1–15 = a visible ramp.
  - VDP-A slot 0 = transparent (color 0 with TP=1), slots 1–15 = high
    contrast set.
- Fill VDP-B's active framebuffer with slot 0 (dark blue) via the HMMV
  hardware command, so the background is a known solid color.
- Leave VDP-A's Pattern Name Table cleared (all zero) so VDP-B shows
  through everywhere. This also proves the compositing path works.
- Enable VDP-A's V-blank interrupt and install a stub INT0 handler at
  `0x0038` that reads S#0 to clear the flag and returns.
- Main loop becomes `halt` + increment a frame counter in SRAM.

Out of scope:

- Any actual game content
- Audio (completely silent is correct for this task)
- Sprites (patterns undefined — SAT Y = 0xD0 to disable all 32)

## Implementation notes

Verified mode bytes in the current Vanguard 8 implementation are:

- VDP-B Graphic 4: `R#0 = 0x06`
- VDP-A Graphic 3: `R#0 = 0x04`
- Shared graphics-mode `R#1` base: `0x00`; add `0x40` to enable display and
  `0x20` on VDP-A for V-blank IRQ enable

These values match the working showcase scenes and the current emulator's
`V9938` mode constants.

V9938 palette write protocol (port 0x82 / 0x86):

```
out (palport), index_byte       ; index 0..15
out (palport), (R<<4) | G       ; red/green
out (palport), B                ; blue
```

HMMV for the framebuffer clear (VDP-B, Graphic 4):

```
DX = 0, DY = 0
NX = 256, NY = 212
CLR = 0x00 (both nibbles = palette index 0)
CMD = 0xC0 (HMMV)
```

Wait on S#2.CE = 0 before issuing any further commands.

Don't forget to write R#11 for the VDP-B SAT base (set all 32 sprite Y's
to 0xD0 to hide them) so the undefined sprite pattern bytes don't cause
garbage along the top scanlines.

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/tests/evidence/T002-boot-background/frame_060.png` —
  runtime frame captured after 60 frames of emulation via
  `vanguard8_headless --rom build/pacman.rom --frames 60 --hash-frame 60
  --dump-frame ...`. The captured frame is a uniform dark blue field.
- `vanguard8_port/tests/evidence/T002-boot-background/frame_hash.txt` —
  the headless runner's frame hash output from two consecutive runs,
  recorded so future runs can detect regressions. Current reference hash:
  `0421e581a0ed677c60406cfb9884571cd904bfe94db13acb26ace122c92fadcb`.
- `vanguard8_port/tests/evidence/T002-boot-background/run_1.txt` —
  first headless capture log.
- `vanguard8_port/tests/evidence/T002-boot-background/run_2.txt` —
  second headless capture log used for the determinism check.

**Reviewer checklist:**

- [ ] `frame_060.png` shows a single solid color filling the full 256×212
      active area (no garbage, no stripes, no checkerboard)
- [ ] That color visibly matches the chosen VDP-B slot 0 (dark blue)
- [ ] No sprite garbage along any edge
- [ ] Running the rerun command twice produces identical frame hashes
      (determinism check)
- [ ] The emulator does not print any "VDP command in progress" or
      invalid-write warnings to stderr during the 60-frame run

**Rerun command:**

```bash
cd /home/djglxxii/src/pacman/vanguard8_port && \
  python3 tools/pack_rom.py && \
  /home/djglxxii/src/Vanguard8/build/src/vanguard8_headless \
    --rom build/pacman.rom \
    --frames 60 \
    --hash-frame 60 \
    --dump-frame tests/evidence/T002-boot-background/frame_060.ppm
```

## Progress log

- 2026-04-10 — created, state: planned.
- 2026-04-10 — activated. Replaced the placeholder frontend/headless capture
  command with the actual `vanguard8_headless` flags supported by the current
  emulator build, and corrected the Graphic 3 mode byte to the value the
  emulator and showcase actually implement (`R#0 = 0x04`).
- 2026-04-10 — implemented dual-VDP boot setup, palette upload, VDP-B HMMV
  clear, IM1 V-blank stub handling, and SRAM frame counting in
  `vanguard8_port/src/main.asm`. Initial headless runs exposed emulator CPU
  timing gaps rather than a ROM assembly/build failure.
- 2026-04-10 — resumed after emulator patch. Moving the task back from
  `blocked/` to `active/` and rerunning the headless capture/evidence path.
- 2026-04-10 — corrected the ROM's palette upload to stream palette bytes
  using the emulator's implemented port protocol. Final evidence capture now
  produces a uniform dark-blue frame with matching 60-frame hashes across two
  headless runs.
- 2026-04-10 — approved by human reviewer and moved to `completed/`.

## Blocker

- External system: `/home/djglxxii/src/Vanguard8/` emulator CPU timing path
- Symptom: headless execution aborts immediately with `Unsupported timed Z180
  ED opcode 0x56 at PC 0x314`
- Evidence: `vanguard8_port/tests/evidence/T002-boot-background/blocker_run.txt`
- Minimal repro:

```bash
cd /home/djglxxii/src/pacman/vanguard8_port && \
  python3 tools/pack_rom.py && \
  /home/djglxxii/src/Vanguard8/build/src/vanguard8_headless \
    --rom build/pacman.rom \
    --frames 1
```

- Unblock condition: the emulator's timed Z180 adapter must accept the ROM's
  `IM 1` instruction (`ED 56`) and continue execution normally. After that,
  rerun the T002 headless capture command and verify the frame output/hash.
- Resolved 2026-04-10 — patched emulator now accepts the ROM's `IM 1`
  setup path; the task proceeded to successful headless frame capture.

## Evidence notes

- `frame_060.png` was generated from `frame_060.ppm` using ImageMagick after a
  successful 60-frame `vanguard8_headless` run.
- `run_1.txt` and `run_2.txt` both report the same frame hash:
  `0421e581a0ed677c60406cfb9884571cd904bfe94db13acb26ace122c92fadcb`.
- Neither run log contains any `VDP command in progress` or invalid-write
  warnings.
