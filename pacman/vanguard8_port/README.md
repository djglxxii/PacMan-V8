# Pac-Man Vanguard 8 Port

This directory contains the Vanguard 8 cartridge project for the Pac-Man port.

## Build

From this directory:

```bash
python3 tools/pack_rom.py
```

Outputs:

- `build/pacman.rom`
- `build/pacman.sym`

The build pads the ROM to a 16 KB cartridge page boundary so it matches the
HD64180 MMU banking model described in the Vanguard 8 spec.

## Run

From the repository root.

Interactive frontend:

```bash
/home/djglxxii/src/Vanguard8/build/src/vanguard8_frontend --rom vanguard8_port/build/pacman.rom
```

Headless smoke test:

```bash
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom vanguard8_port/build/pacman.rom --frames 1
```

T001 only produces a minimal boot ROM with MMU setup and a halt loop. Video
initialization and visible output start in later tasks.
