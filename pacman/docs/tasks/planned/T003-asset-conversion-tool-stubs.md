# T003 — Asset conversion tool stubs

| Field | Value |
|---|---|
| ID | T003 |
| State | planned |
| Phase | 0 Scaffold |
| Depends on | T001 |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §3, §3.6 |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/02-video.md`, `03-audio.md` |

## Goal

Create the empty shells of every asset conversion script, wired into the
build driver, so subsequent tasks can focus on conversion logic rather than
pipeline plumbing. Each stub must be runnable, read its declared inputs,
and write a placeholder output that downstream tooling can consume.

## Scope

In scope — create each of these under `vanguard8_port/tools/`:

| Script | Input | Output | Placeholder behavior |
|---|---|---|---|
| `conv_palette.py` | `source_rom/82s123.7f` | `assets/palette_a.bin`, `assets/palette_b.bin` | Emit 32 bytes of zeros per palette |
| `conv_tiles.py` | `source_rom/pacman.5e`, `source_rom/82s126.4a` | `assets/tiles_vdpb.bin`, `assets/tile_nametable.bin` | Emit empty files |
| `conv_sprites.py` | `source_rom/pacman.5f`, `source_rom/82s126.4a` | `assets/sprites_patterns.bin`, `assets/sprites_colors.bin` | Emit empty files |
| `conv_hud_font.py` | `source_rom/pacman.5e` | `assets/hud_font.bin` | Empty file |
| `conv_audio.py` | `source_rom/82s126.1m` | `assets/wsg_instruments.bin`, `assets/music_data.bin` | Empty files |

- Each script is a standalone `python3 tools/conv_xxx.py` invocation with
  no arguments, resolving paths relative to the `vanguard8_port/` directory.
- Extend `pack_rom.py` to run every `conv_*.py` before invoking the
  assembler. Conversion failures must fail the build.
- Add a new ASM file `src/data.asm` that `INCBIN`s every expected asset
  file. The `INCBIN`s must succeed even when the file is empty (sjasmplus
  allows zero-size includes). Reference `data.asm` from `main.asm`.
- Every script must print a one-line summary: `conv_palette: 32 + 32 bytes
  written to assets/palette_{a,b}.bin`, etc. The build log shows the
  pipeline is live.

Out of scope:

- Any actual conversion logic. Tasks T004+ implement real content.
- Using the converted assets at runtime beyond their `INCBIN` footprint.

## Implementation notes

Use a small shared helper module `vanguard8_port/tools/_common.py` for
path resolution (`REPO_ROOT`, `SOURCE_ROM_DIR`, `ASSETS_DIR`), so all five
scripts have consistent path handling and the downstream tasks can focus
on the algorithm rather than rewriting boilerplate.

`pack_rom.py` should run the converters in this order: palette, tiles,
sprites, hud_font, audio. If any converter exits non-zero, stop and
propagate the failure.

Keep the stub output files at zero bytes (or the minimum required by
later layout — 32 bytes of zeros for palettes is fine because the
palette upload will overwrite those values in T004). Downstream tasks
will replace each stub by filling in real logic; none of the stubs should
need to be touched for anything other than the acceptance checklist item
"the pipeline runs end-to-end".

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/tests/evidence/T003-tool-stubs/build_log.txt` — full
  stdout of a clean `pack_rom.py` run showing every converter firing and
  the assembler succeeding.
- `vanguard8_port/tests/evidence/T003-tool-stubs/assets_listing.txt` —
  output of `ls -la vanguard8_port/assets/` showing every expected file
  exists.

**Reviewer checklist:**

- [ ] `build_log.txt` contains one summary line per converter in the
      documented order
- [ ] `assets_listing.txt` shows all 8 asset files
- [ ] `pacman.rom` built successfully and is still a multiple of 16 KB
- [ ] Deliberately corrupting one input (e.g. `rm source_rom/82s123.7f`)
      causes the next `pack_rom.py` run to fail fast with a clear error
      message — reviewer runs this check manually and restores the file
      afterward
- [ ] No regression in T001 or T002 evidence (rerun those commands)

**Rerun command:**

```
cd /home/djglxxii/src/pacman/vanguard8_port && rm -rf build && python3 tools/pack_rom.py
```

## Progress log

- 2026-04-10 — created, state: planned.
