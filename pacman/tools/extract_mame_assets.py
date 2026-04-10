#!/usr/bin/env python3
"""
Extract graphics and audio assets from a MAME Pac-Man ROM set.

Inputs (in ./pacman/):
  pacman.5e    tile ROM  (4 KB, 256 tiles, 8x8, 2bpp)
  pacman.5f    sprite ROM (4 KB, 64 sprites, 16x16, 2bpp)
  82s123.7f    32-byte palette PROM
  82s126.4a    256-byte color lookup table
  82s126.1m    sound waveform PROM (8 waveforms x 32 samples x 4 bit)

Outputs (in ./extracted/):
  tiles.png        sprite sheet of all 256 tiles (all 64 palette entries)
  sprites.png      sprite sheet of all 64 sprites (all 64 palette entries)
  tiles_raw.png    tiles in plain 4-color palette (plane values 0..3)
  sprites_raw.png  sprites in plain 4-color palette
  palette.png      32-color master palette swatch
  waveform_NN.wav  each of the 8 WSG waveforms as a short .wav
  waveforms.png    visual plot of all 8 waveforms
"""

import os
import struct
import wave
from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_DIR = os.path.join(REPO_ROOT, "source_rom")
OUT_DIR = os.path.join(REPO_ROOT, "extracted")
os.makedirs(OUT_DIR, exist_ok=True)


def load(name):
    with open(os.path.join(ROM_DIR, name), "rb") as f:
        return f.read()


# ---------- Palette decoding ----------
def decode_master_palette(prom):
    """32-byte PROM -> list of 32 (r,g,b) tuples.

    Bit layout (per MAME pacman_state::pacman_palette):
      bits 0..2 = red, bits 3..5 = green, bits 6..7 = blue
    Resistor weights: r/g use 1k/470/220 ohm -> ~0x21,0x47,0x97;
                      b     uses   470/220 ohm -> ~0x51,0xae.
    """
    rw = (0x21, 0x47, 0x97)
    gw = (0x21, 0x47, 0x97)
    bw = (0x51, 0xAE)
    pal = []
    for b in prom:
        r = rw[0] * ((b >> 0) & 1) + rw[1] * ((b >> 1) & 1) + rw[2] * ((b >> 2) & 1)
        g = gw[0] * ((b >> 3) & 1) + gw[1] * ((b >> 4) & 1) + gw[2] * ((b >> 5) & 1)
        blu = bw[0] * ((b >> 6) & 1) + bw[1] * ((b >> 7) & 1)
        pal.append((min(r, 255), min(g, 255), min(blu, 255)))
    return pal


def decode_clut(prom):
    """256-byte PROM -> 64 color sets of 4 palette indices."""
    clut = []
    for i in range(64):
        clut.append(tuple(prom[i * 4 + j] & 0x0F for j in range(4)))
    return clut


# ---------- MAME gfx_layout decoder ----------
def get_bit(data, bit_offset):
    byte = data[bit_offset >> 3]
    return (byte >> (7 - (bit_offset & 7))) & 1


def decode_gfx(rom, width, height, plane_offsets, x_offsets, y_offsets, char_inc):
    planes = len(plane_offsets)
    count = (len(rom) * 8) // char_inc
    tiles = []
    for n in range(count):
        base = n * char_inc
        tile = [[0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                pix = 0
                for p in range(planes):
                    bit = get_bit(
                        rom,
                        base + y_offsets[y] + x_offsets[x] + plane_offsets[p],
                    )
                    pix |= bit << p
                tile[y][x] = pix
        tiles.append(tile)
    return tiles


# Pac-Man tile layout (8x8, 2bpp)
TILE_LAYOUT = dict(
    width=8, height=8,
    plane_offsets=(0, 4),
    x_offsets=(8 * 8 + 0, 8 * 8 + 1, 8 * 8 + 2, 8 * 8 + 3, 0, 1, 2, 3),
    y_offsets=tuple(i * 8 for i in range(8)),
    char_inc=16 * 8,
)

# Pac-Man sprite layout (16x16, 2bpp)
SPRITE_LAYOUT = dict(
    width=16, height=16,
    plane_offsets=(0, 4),
    x_offsets=(
        8 * 8 + 0, 8 * 8 + 1, 8 * 8 + 2, 8 * 8 + 3,
        16 * 8 + 0, 16 * 8 + 1, 16 * 8 + 2, 16 * 8 + 3,
        24 * 8 + 0, 24 * 8 + 1, 24 * 8 + 2, 24 * 8 + 3,
        0, 1, 2, 3,
    ),
    y_offsets=tuple(i * 8 for i in range(8)) + tuple(32 * 8 + i * 8 for i in range(8)),
    char_inc=64 * 8,
)


# ---------- Sheet rendering ----------
def render_all_palettes_sheet(tiles, tw, th, clut, master_pal, cols_per_pal=None):
    """Render every tile under every one of the 64 palettes.

    Layout: rows = palettes (64), cols = tiles.
    """
    n = len(tiles)
    cols = cols_per_pal or n
    rows = 64
    img = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
    px = img.load()
    for pi, colors4 in enumerate(clut):
        rgb4 = [master_pal[c] for c in colors4]
        for ti, tile in enumerate(tiles[:cols]):
            ox = ti * tw
            oy = pi * th
            for y in range(th):
                row = tile[y]
                for x in range(tw):
                    px[ox + x, oy + y] = rgb4[row[x]]
    return img


def render_raw_sheet(tiles, tw, th, cols=16):
    """Render tiles with a fixed 4-color grayscale-ish palette."""
    n = len(tiles)
    rows = (n + cols - 1) // cols
    img = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    px = img.load()
    fixed = [(0, 0, 0), (80, 80, 80), (170, 170, 170), (255, 255, 255)]
    for i, tile in enumerate(tiles):
        cx = (i % cols) * tw
        cy = (i // cols) * th
        for y in range(th):
            for x in range(tw):
                px[cx + x, cy + y] = fixed[tile[y][x]]
    return img


def render_palette_swatch(pal, sw=24):
    img = Image.new("RGB", (16 * sw, 2 * sw), (0, 0, 0))
    px = img.load()
    for i, c in enumerate(pal):
        bx = (i % 16) * sw
        by = (i // 16) * sw
        for y in range(sw):
            for x in range(sw):
                px[bx + x, by + y] = c
    return img


# ---------- Audio ----------
def extract_waveforms(sound_prom):
    """8 waveforms x 32 samples x 4-bit (low nibble of each byte)."""
    waves = []
    for w in range(8):
        samples = [sound_prom[w * 32 + i] & 0x0F for i in range(32)]
        waves.append(samples)
    return waves


def write_waveform_wav(path, samples4bit, sample_rate=8000, cycles=400):
    """Repeat the 32-sample wavetable so the .wav is ~1.6s long and audible."""
    # Map 0..15 -> signed 16-bit, centered.
    mapped = [((s - 7) * 2000) for s in samples4bit]
    frames = bytearray()
    for _ in range(cycles):
        for m in mapped:
            frames += struct.pack("<h", max(-32768, min(32767, m)))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))


def render_waveform_plot(waves):
    w, h = 32 * 8, 8 * 64
    img = Image.new("RGB", (w, h), (16, 16, 16))
    d = ImageDraw.Draw(img)
    for wi, samples in enumerate(waves):
        y0 = wi * 64
        d.line([(0, y0 + 32), (w, y0 + 32)], fill=(64, 64, 64))
        for i, s in enumerate(samples):
            x1 = i * 8
            x2 = x1 + 8
            y = y0 + (60 - int(s * 60 / 15))
            d.rectangle([x1, y, x2 - 1, y0 + 62], fill=(80, 200, 120))
        d.text((4, y0 + 2), f"wave {wi}", fill=(220, 220, 220))
    return img


def main():
    # Load ROMs
    tile_rom = load("pacman.5e")
    sprite_rom = load("pacman.5f")
    palette_prom = load("82s123.7f")
    clut_prom = load("82s126.4a")
    sound_prom = load("82s126.1m")

    print(f"tile ROM     {len(tile_rom)} bytes")
    print(f"sprite ROM   {len(sprite_rom)} bytes")
    print(f"palette PROM {len(palette_prom)} bytes")
    print(f"clut PROM    {len(clut_prom)} bytes")
    print(f"sound PROM   {len(sound_prom)} bytes")

    master_pal = decode_master_palette(palette_prom)
    clut = decode_clut(clut_prom)

    tiles = decode_gfx(tile_rom, **TILE_LAYOUT)
    sprites = decode_gfx(sprite_rom, **SPRITE_LAYOUT)
    print(f"decoded {len(tiles)} tiles, {len(sprites)} sprites")

    # Palette swatch
    render_palette_swatch(master_pal).save(os.path.join(OUT_DIR, "palette.png"))

    # Raw (plane value) sheets - useful for inspecting shapes regardless of palette
    render_raw_sheet(tiles, 8, 8, cols=16).save(os.path.join(OUT_DIR, "tiles_raw.png"))
    render_raw_sheet(sprites, 16, 16, cols=8).save(os.path.join(OUT_DIR, "sprites_raw.png"))

    # All tiles under all 64 palettes (the "full" sprite sheet)
    render_all_palettes_sheet(tiles, 8, 8, clut, master_pal).save(
        os.path.join(OUT_DIR, "tiles.png")
    )
    render_all_palettes_sheet(sprites, 16, 16, clut, master_pal).save(
        os.path.join(OUT_DIR, "sprites.png")
    )

    # Audio waveforms
    waves = extract_waveforms(sound_prom)
    for i, w in enumerate(waves):
        write_waveform_wav(os.path.join(OUT_DIR, f"waveform_{i}.wav"), w)
    render_waveform_plot(waves).save(os.path.join(OUT_DIR, "waveforms.png"))

    print("done ->", OUT_DIR)


if __name__ == "__main__":
    main()
