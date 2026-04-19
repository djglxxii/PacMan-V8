#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import struct
from dataclasses import dataclass


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
COORDMAP_PATH = REPO_ROOT / "assets" / "maze_v8_coordmap.bin"

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 212
HUD_HEIGHT = 8
STATUS_Y = 204

ARCADE_WIDTH = 28
ARCADE_HEIGHT = 36
ARCADE_TILE_SIZE = 8
ARCADE_TILE_CENTER = 4
ARCADE_MAZE_WIDTH_PX = ARCADE_WIDTH * ARCADE_TILE_SIZE
MAZE_TOP = 3
MAZE_ROWS = 31
MAZE_X = 16
MAZE_Y = 8
MAZE_WIDTH = 224
MAZE_HEIGHT = 196
SPRITE_SIZE = 16
SPRITE_ANCHOR_OFFSET = SPRITE_SIZE // 2

COORD_RECORD = struct.Struct("<BBBBBBH")
COORD_RECORD_SIZE = COORD_RECORD.size
COORDMAP_BYTES = ARCADE_WIDTH * ARCADE_HEIGHT * COORD_RECORD_SIZE

COORD_FLAG_MAPPED = 0x01
COORD_FLAG_WALKABLE = 0x02
COORD_FLAG_GRAPH_NODE = 0x04
COORD_FLAG_PELLET = 0x08
COORD_FLAG_WARP_ENDPOINT = 0x10

CLASS_NAMES = (
    "WALL",
    "PATH",
    "PELLET",
    "ENERGIZER",
    "GHOST_HOUSE",
    "GHOST_DOOR",
    "TUNNEL",
    "BLANK",
)


@dataclass(frozen=True)
class CoordRecord:
    x: int
    y: int
    width: int
    height: int
    semantic_class: int
    flags: int
    source_tile_id: int

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    @property
    def mapped(self) -> bool:
        return bool(self.flags & COORD_FLAG_MAPPED)

    @property
    def class_name(self) -> str:
        if 0 <= self.semantic_class < len(CLASS_NAMES):
            return CLASS_NAMES[self.semantic_class]
        return f"UNKNOWN_{self.semantic_class}"


@dataclass(frozen=True)
class TransformResult:
    arcade_x_fp: int
    arcade_y_fp: int
    tile_x: int
    tile_y: int
    screen_center_x: int
    screen_center_y: int
    sprite_x: int
    sprite_y: int
    cell: CoordRecord


def load_coordmap(path: pathlib.Path = COORDMAP_PATH) -> bytes:
    data = path.read_bytes()
    if len(data) != COORDMAP_BYTES:
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must be {COORDMAP_BYTES} bytes; got {len(data)}.")
    return data


def record_at(coordmap: bytes, tile_x: int, tile_y: int) -> CoordRecord:
    if not (0 <= tile_x < ARCADE_WIDTH and 0 <= tile_y < ARCADE_HEIGHT):
        raise ValueError(f"arcade tile ({tile_x},{tile_y}) is outside {ARCADE_WIDTH}x{ARCADE_HEIGHT}.")
    offset = (tile_y * ARCADE_WIDTH + tile_x) * COORD_RECORD_SIZE
    values = COORD_RECORD.unpack_from(coordmap, offset)
    return CoordRecord(*values)


def fixed_tile_center(tile_index: int) -> int:
    return ((tile_index * ARCADE_TILE_SIZE) + ARCADE_TILE_CENTER) << 8


def fixed_point_for_tile(tile_x: int, tile_y: int) -> tuple[int, int]:
    return fixed_tile_center(tile_x), fixed_tile_center(tile_y)


def transform_entity(coordmap: bytes, arcade_x_fp: int, arcade_y_fp: int) -> TransformResult:
    normalized_x_fp = arcade_x_fp % (ARCADE_MAZE_WIDTH_PX << 8)
    arcade_x_px = normalized_x_fp >> 8
    arcade_y_px = arcade_y_fp >> 8
    tile_x = arcade_x_px // ARCADE_TILE_SIZE
    tile_y = arcade_y_px // ARCADE_TILE_SIZE
    cell = record_at(coordmap, tile_x, tile_y)
    if not cell.mapped:
        raise ValueError(f"arcade tile ({tile_x},{tile_y}) has no V8 screen mapping.")

    within_x_fp = normalized_x_fp - ((tile_x * ARCADE_TILE_SIZE) << 8)
    within_y_fp = arcade_y_fp - ((tile_y * ARCADE_TILE_SIZE) << 8)
    screen_center_x = cell.x + ((within_x_fp * cell.width) >> 11)
    screen_center_y = cell.y + ((within_y_fp * cell.height) >> 11)
    return TransformResult(
        arcade_x_fp=arcade_x_fp,
        arcade_y_fp=arcade_y_fp,
        tile_x=tile_x,
        tile_y=tile_y,
        screen_center_x=screen_center_x,
        screen_center_y=screen_center_y,
        sprite_x=screen_center_x - SPRITE_ANCHOR_OFFSET,
        sprite_y=screen_center_y - SPRITE_ANCHOR_OFFSET,
        cell=cell,
    )


def transform_tile_center(coordmap: bytes, tile_x: int, tile_y: int) -> TransformResult:
    x_fp, y_fp = fixed_point_for_tile(tile_x, tile_y)
    return transform_entity(coordmap, x_fp, y_fp)


def sprite_box_clear_of_hud(result: TransformResult) -> bool:
    return result.sprite_y >= HUD_HEIGHT and result.sprite_y + SPRITE_SIZE <= STATUS_Y
