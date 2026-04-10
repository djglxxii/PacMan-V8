# Pac-Man → Vanguard 8

A port of arcade Pac-Man to the [Vanguard 8](../Vanguard8/) fantasy 8-bit
console. The goal is a cartridge ROM that runs on `vanguard8_frontend` and
plays indistinguishably from the arcade original.

## Layout

```
CLAUDE.md                  Operating contract for coding agents — read first
README.md                  This file
docs/
  VANGUARD8_PORT_PLAN.md   Architectural plan (source of truth)
  tasks/                   Task queue driving execution
source_rom/                MAME Pac-Man ROM set (read-only input)
extracted/                 Decoded art + audio from source_rom/
tools/
  extract_mame_assets.py   One-shot MAME asset extraction
vanguard8_port/            The cartridge project (src, assets, tools, build)
```

## Where to start

- **Humans:** read `docs/VANGUARD8_PORT_PLAN.md` for the design, then
  `docs/tasks/INDEX.md` for current progress.
- **Coding agents:** read `CLAUDE.md` first. Always.

## Asset extraction

The MAME ROM set in `source_rom/` has already been decoded once into
`extracted/` (tile sheets, sprite sheets, palette swatch, WSG wavetables).
To regenerate:

```
python3 tools/extract_mame_assets.py
```

## Building the cartridge

Once `vanguard8_port/` is scaffolded (task T001):

```
cd vanguard8_port
python3 tools/pack_rom.py
```

Output lands in `vanguard8_port/build/pacman.rom` and can be launched with:

```
~/src/Vanguard8/build/vanguard8_frontend --rom vanguard8_port/build/pacman.rom
```

## Legal

The arcade ROM files in `source_rom/` are © Namco. This project exists for
personal study, reverse engineering, and Vanguard 8 platform demonstration.
Do not redistribute `source_rom/`, `extracted/`, or any derived asset
blobs outside your own machine. The Vanguard 8 implementation code in
`vanguard8_port/src/` is written clean-room from published Pac-Man
behavior documentation and is original work.
