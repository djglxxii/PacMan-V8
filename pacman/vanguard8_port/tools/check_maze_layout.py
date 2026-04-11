#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import conv_tiles


EXPECTED_ROTATED_WALL_SEAM_EXCEPTIONS = {
    (4, 12, "v", "dc", "e7"),
    (4, 16, "v", "db", "eb"),
    (4, 18, "v", "dc", "e7"),
    (4, 22, "v", "db", "eb"),
    (5, 12, "h", "e7", "d2"),
    (5, 15, "h", "d2", "eb"),
    (5, 18, "h", "e7", "d2"),
    (5, 21, "h", "d2", "eb"),
    (22, 12, "h", "e6", "d3"),
    (22, 12, "v", "e6", "dc"),
    (22, 15, "h", "d3", "ea"),
    (22, 16, "v", "ea", "db"),
    (22, 18, "h", "e6", "d3"),
    (22, 18, "v", "e6", "dc"),
    (22, 21, "h", "d3", "ea"),
    (22, 22, "v", "ea", "db"),
}


def is_wall_token(token: str) -> bool:
    tile_id = int(token, 16)
    return tile_id >= 0xC0 and tile_id != 0xC0


def main() -> int:
    tile_rom = conv_tiles.require_input("pacman.5e")
    clut_prom = conv_tiles.require_input("82s126.4a")
    tiles = conv_tiles.decode_tiles(tile_rom)
    clut = conv_tiles.decode_clut(clut_prom)
    prom_to_slot = conv_tiles.load_prom_to_slot_map(conv_tiles.PALETTE_MAP_PATH)
    converted, _warnings, source_to_index = conv_tiles.convert_tiles(tiles, clut, prom_to_slot)
    payload = b"".join(tile.packed for tile in converted)
    tile_pixels = conv_tiles.unpack_graphic4_tiles(payload)
    layout = conv_tiles.rotate_arcade_layout_ccw(
        conv_tiles.load_maze_layout(conv_tiles.MAZE_LAYOUT_PATH)
    )

    seam_count = 0
    unexpected: list[tuple[int, int, str, str, str]] = []
    observed_exceptions: set[tuple[int, int, str, str, str]] = set()

    for row_index, row in enumerate(layout):
        for column_index, token in enumerate(row):
            tile = tile_pixels[source_to_index[int(token, 16)]]
            if column_index + 1 < len(row) and is_wall_token(token) and is_wall_token(row[column_index + 1]):
                right_token = row[column_index + 1]
                right_tile = tile_pixels[source_to_index[int(right_token, 16)]]
                seam_count += 1
                left_edge = tuple(tile[y][-1] for y in range(conv_tiles.TILE_HEIGHT))
                right_edge = tuple(right_tile[y][0] for y in range(conv_tiles.TILE_HEIGHT))
                if left_edge != right_edge:
                    mismatch = (row_index, column_index, "h", token, right_token)
                    observed_exceptions.add(mismatch)
                    if mismatch not in EXPECTED_ROTATED_WALL_SEAM_EXCEPTIONS:
                        unexpected.append(mismatch)

            if row_index + 1 < len(layout) and is_wall_token(token) and is_wall_token(layout[row_index + 1][column_index]):
                down_token = layout[row_index + 1][column_index]
                down_tile = tile_pixels[source_to_index[int(down_token, 16)]]
                seam_count += 1
                if tile[-1] != down_tile[0]:
                    mismatch = (row_index, column_index, "v", token, down_token)
                    observed_exceptions.add(mismatch)
                    if mismatch not in EXPECTED_ROTATED_WALL_SEAM_EXCEPTIONS:
                        unexpected.append(mismatch)

    missing = EXPECTED_ROTATED_WALL_SEAM_EXCEPTIONS - observed_exceptions
    if unexpected or missing:
        print("check_maze_layout: unexpected seam mismatches:")
        for mismatch in unexpected:
            print(f"  {mismatch}")
        print("check_maze_layout: expected seam exceptions not observed:")
        for mismatch in sorted(missing):
            print(f"  {mismatch}")
        return 1

    framebuffer = conv_tiles.render_static_maze_framebuffer(payload, source_to_index)
    if len(framebuffer) != conv_tiles.FRAME_HEIGHT * conv_tiles.FRAME_ROW_BYTES:
        print(f"check_maze_layout: bad framebuffer size {len(framebuffer)}")
        return 1

    print(
        "check_maze_layout: "
        f"{seam_count} wall seams checked; "
        f"{len(observed_exceptions)} known arcade seam exceptions; "
        "0 unexpected mismatches"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
