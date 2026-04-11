# T004 — Palette conversion + dual-VDP upload

| Field | Value |
|---|---|
| ID | T004 |
| State | completed |
| Phase | 1 Visual |
| Depends on | T002, T003 |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §3.1 |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/02-video.md` §Palette |

## Goal

Convert the arcade Pac-Man master palette (`82s123.7f`) into a Vanguard 8
9-bit RGB palette and upload it to both VDPs at boot, replacing the test
palette from T002. Render a 16-color swatch on VDP-B so each converted
color is visually identifiable on the captured frame.

## Scope

In scope:

- Replace the `conv_palette.py` stub with real logic:
  - Decode `82s123.7f` using the same resistor-weighted formula already
    present in `tools/extract_mame_assets.py` (R: 0x21/0x47/0x97,
    G: 0x21/0x47/0x97, B: 0x51/0xAE).
  - Drop duplicate/unused black entries so the 16 meaningful arcade
    colors fit into the 16-slot V9938 palette.
  - Nearest-match each 8-bit-per-channel arcade color to a 3-bit-per-
    channel V9938 value. Emit `palette_a.bin` and `palette_b.bin` as
    16 × 2-byte entries in the V9938 palette-write wire format.
- Document the slot assignment in a comment at the top of
  `conv_palette.py` AND in `vanguard8_port/assets/src/palette_map.md`
  (slot 0 must be transparent on VDP-A, slot 0 on VDP-B is maze black).
- At boot, `main.asm` reads the palette blobs via `INCBIN` and uploads
  them to both VDPs via ports 0x82 / 0x86.
- Replace the solid-color T002 background with a **16-color horizontal
  swatch** on VDP-B: 16 vertical bars, each 16 pixels wide and 212 tall,
  using palette slots 0 through 15. This is a visual correctness check —
  at a glance, every palette slot is identifiable.

Out of scope:

- Real maze or sprite content (T005 / T006 / T008).
- HUD rendering on VDP-A (T007) — VDP-A remains transparent for now.

## Implementation notes

V9938 palette write, 2-byte format per entry (see spec §Writing Palette
Entries):

```
Byte 1 = (R << 4) | G     ; each channel 0..7
Byte 2 = B                ; 0..7
```

Per the arcade decode, the non-black master-palette entries are
(indices to confirm from the dump, not from memory):

- black, red, light peach, white/pink, cyan, sky blue, tan, yellow,
  blue (maze wall), green, orange, plus a few duplicates.

Write the 16 entries out with an explicit mapping table in
`conv_palette.py` so the slot assignment is source-controlled. If the
nearest-match quantization collapses two distinct arcade colors into the
same V9938 entry, print a warning and keep the distinguishing one — we
have 16 slots and only 11–12 actually needed.

Swatch rendering originally targeted HMMV rectangles, one per slot, same
pattern as the T002 background clear. The accepted implementation uses a
direct Graphic 4 VRAM stream instead: each row writes 16 groups of 8 packed
bytes (`0x00`, `0x11`, ..., `0xFF`) to produce 16 solid 16-pixel-wide bars.
This keeps the review artifact independent of VDP command-completion behavior
while still exercising the uploaded palette slots.

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/tests/evidence/T004-palette/swatch.png` — captured frame
  showing the 16 color bars.
- `vanguard8_port/tests/evidence/T004-palette/slot_map.txt` — a text
  table produced by `conv_palette.py` listing each slot: `slot | arcade
  RGB (hex) | v9938 RGB (0..7) | role`. This is the agent-authored
  checklist artifact the reviewer uses to confirm the quantization.
- `vanguard8_port/tests/evidence/T004-palette/frame_hash.txt` — for
  regression detection. Current frame-60 SHA-256:
  `680738b26715e28175a12855123559974c36e55085cf19bffaf40fcfd22153c9`.
- `vanguard8_port/tests/evidence/T004-palette/rerun_log.txt` — clean rerun
  log for the documented command.

**Reviewer checklist:**

- [ ] 16 distinct vertical bars are visible in `swatch.png` (or, if two
      bars collapsed due to quantization, `slot_map.txt` documents the
      collision and the reviewer agrees it is acceptable)
- [ ] Slot 0 (leftmost bar) is black — required for transparency semantics
- [ ] A bar clearly matching "maze wall blue" is present
- [ ] A bar clearly matching "Pac-Man yellow" is present
- [ ] Red / pink / cyan / orange (the 4 ghost colors) all visually
      distinct
- [ ] Rerun produces an identical frame hash

**Rerun command:**

```
cd /home/djglxxii/src/pacman/vanguard8_port && rm -rf build && python3 tools/pack_rom.py && \
  /home/djglxxii/src/Vanguard8/build/src/vanguard8_headless \
    --rom build/pacman.rom --frames 60 \
    --dump-frame tests/evidence/T004-palette/swatch.ppm \
    --hash-frame 60
```

## Progress log

- 2026-04-10 — created, state: planned.
- 2026-04-10 — activated. Reviewed `docs/VANGUARD8_PORT_PLAN.md` §3.1,
  `docs/spec/02-video.md` §Palette, and the current boot/converter path
  before replacing the T002 test palette with generated palette assets.
- 2026-04-10 — implemented `tools/conv_palette.py` with explicit slot
  mapping, resistor-weight decoding, V9938 3-bit quantization,
  `assets/palette_{a,b}.bin` generation, and the human-readable
  `assets/src/palette_map.md` / `assets/palette_slot_map.txt` outputs.
- 2026-04-10 — replaced the T002 hardcoded test palette in
  `vanguard8_port/src/main.asm` with palette uploads sourced from the
  `INCBIN` blobs and added a 16-bar VDP-B swatch path for review capture.
- 2026-04-10 — blocked on the current emulator build. Narrowing the ROM-side
  instruction set removed the earlier palette-upload crash, but the headless
  timed path still aborts once the swatch renderer starts
  (`tests/evidence/T004-palette/vclk_4000_run.txt`). The config-backed
  `VCLK: off` mode runs deterministically and reproduces the same frame hash
  `e46b5246bda293e09e199967b99ac352f931c04e2ad88e775b06a3b93ccb838c`, but
  the captured frame remains solid black (`tests/evidence/T004-palette/swatch.png`),
  so T004 cannot produce the required review artifact yet.
- 2026-04-10 — resumed after user reported the emulator-side blocker fixed.
  Moving T004 back to active and rerunning the build/capture path.
- 2026-04-10 — captured acceptance evidence under
  `vanguard8_port/tests/evidence/T004-palette/`. A clean rebuild and headless
  run produced `swatch.png` with 16 visible vertical bars and frame-60 hash
  `680738b26715e28175a12855123559974c36e55085cf19bffaf40fcfd22153c9`.
  Pixel sampling at y=106 sees all expected slot colors, including maze blue,
  Pac-Man yellow, Blinky red, Pinky pink, Inky cyan, and Clyde orange.
- 2026-04-10 — approved by human reviewer and ready to move to
  `docs/tasks/completed/`.
