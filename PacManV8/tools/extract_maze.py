#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
from collections import Counter, deque
from dataclasses import dataclass


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ROM_DIR = REPO_ROOT / "pacman"
DEFAULT_TILE_ROM_PATH = DEFAULT_ROM_DIR / "pacman.5e"
DEFAULT_TILE_ASSET_PATH = REPO_ROOT / "assets" / "tiles_vdpb.bin"
DEFAULT_PALETTE_ASSET_PATH = REPO_ROOT / "assets" / "palette_b.bin"
DEFAULT_NAMETABLE_PATH = REPO_ROOT / "assets" / "maze_nametable.bin"
DEFAULT_SEMANTIC_PATH = REPO_ROOT / "assets" / "maze_semantic.bin"
DEFAULT_GRAPH_PATH = REPO_ROOT / "assets" / "maze_graph.bin"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "assets" / "maze_manifest.txt"
DEFAULT_SUMMARY_PATH = REPO_ROOT / "assets" / "maze_summary.txt"

PROGRAM_ROM_NAMES = ("pacman.6e", "pacman.6f", "pacman.6h", "pacman.6j")
PROGRAM_ROM_SIZE = 0x4000
TILE_ROM_SIZE = 0x1000
TILESET_ASSET_SIZE = 0x2000
PALETTE_ASSET_SIZE = 32

SCREEN_WIDTH = 28
SCREEN_HEIGHT = 36
MAZE_TEMPLATE_TOP = 3

MAZE_TILE_TABLE_START = 0x3435
MAZE_COLOR_TABLE_START = 0x35B5
MAZE_COLOR_TABLE_END = 0x36A5
MAZE_HALF_EXPANDED_BYTES = 14 * 32
MAZE_CENTER_VRAM_START = 0x040
MAZE_CENTER_VRAM_END = 0x3BF

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
WALL, PATH, PELLET, ENERGIZER, GHOST_HOUSE, GHOST_DOOR, TUNNEL, BLANK = range(8)

GRAPH_MAGIC = b"PMVGRAF1"
GRAPH_VERSION = 1

FLAG_INTERSECTION = 0x0001
FLAG_CORNER = 0x0002
FLAG_TUNNEL_ENDPOINT = 0x0004
FLAG_ENERGIZER = 0x0008
FLAG_GHOST_ENTRY = 0x0010
FLAG_GHOST_HOUSE = 0x0020
FLAG_WARP_EDGE = 0x0040
FLAG_TUNNEL_EDGE = 0x0080

WALKABLE_CLASSES = {PATH, PELLET, ENERGIZER, TUNNEL, GHOST_DOOR, GHOST_HOUSE}
GRAPH_WALKABLE_CLASSES = {PATH, PELLET, ENERGIZER, TUNNEL, GHOST_DOOR}

SEMANTIC_TEMPLATE = (
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #HHHHHH# ##.######",
    "TTTTTT.   #HHHHHH#   .TTTTTT",
    "######.## #HHHHHH# ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#o..##.......  .......##..o#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
)


@dataclass(frozen=True)
class RleResult:
    start: int
    end: int
    destination_offset: int
    encoded_size: int
    expanded: bytes


@dataclass(frozen=True)
class GraphNode:
    node_id: int
    x: int
    y: int
    semantic_class: int
    flags: int


@dataclass(frozen=True)
class GraphEdge:
    from_id: int
    to_id: int
    length: int
    flags: int


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_program_roms(rom_dir: pathlib.Path) -> tuple[bytes, list[tuple[pathlib.Path, bytes]]]:
    pieces: list[tuple[pathlib.Path, bytes]] = []
    for name in PROGRAM_ROM_NAMES:
        path = (rom_dir / name).resolve()
        data = path.read_bytes()
        if len(data) != 0x1000:
            raise ValueError(f"{path.relative_to(REPO_ROOT)} must be 4096 bytes; got {len(data)}.")
        pieces.append((path, data))

    program = b"".join(data for _, data in pieces)
    if len(program) != PROGRAM_ROM_SIZE:
        raise ValueError(f"Concatenated program ROM must be {PROGRAM_ROM_SIZE} bytes.")
    return program, pieces


def decode_tile(tile_rom: bytes, tile_id: int) -> tuple[tuple[int, ...], ...]:
    start = tile_id * 16
    tile_bytes = tile_rom[start : start + 16]
    if len(tile_bytes) != 16:
        raise ValueError(f"Tile {tile_id:02X} is outside the character ROM.")

    pixels: list[tuple[int, ...]] = []
    for y in range(8):
        right_half = tile_bytes[y]
        left_half = tile_bytes[8 + y]
        row: list[int] = []

        for x in range(4):
            low = (left_half >> x) & 0x01
            high = (left_half >> (x + 4)) & 0x01
            row.append(low | (high << 1))

        for x in range(4):
            low = (right_half >> x) & 0x01
            high = (right_half >> (x + 4)) & 0x01
            row.append(low | (high << 1))

        pixels.append(tuple(row))

    return tuple(pixels)


def build_horizontal_flip_map(tile_rom: bytes) -> dict[int, int]:
    tiles = [decode_tile(tile_rom, tile_id) for tile_id in range(256)]
    by_pixels = {pixels: tile_id for tile_id, pixels in enumerate(tiles)}
    flip_map: dict[int, int] = {}

    for tile_id, pixels in enumerate(tiles):
        flipped = tuple(tuple(reversed(row)) for row in pixels)
        match = by_pixels.get(flipped)
        if match is not None:
            flip_map[tile_id] = match

    return flip_map


def decode_maze_rle(program_rom: bytes, start: int) -> RleResult:
    position = start
    destination_offset = program_rom[position]
    position += 1
    expanded = bytearray()

    while position < len(program_rom):
        value = program_rom[position]
        position += 1

        if value == 0x00:
            break

        if value < 0x80:
            if position >= len(program_rom):
                raise ValueError("Maze RLE repeat count reached end of ROM.")
            repeated = program_rom[position]
            position += 1
            expanded.extend([repeated] * value)
        else:
            expanded.append(value)
    else:
        raise ValueError("Maze RLE table was not zero-terminated.")

    return RleResult(
        start=start,
        end=position,
        destination_offset=destination_offset,
        encoded_size=position - start,
        expanded=bytes(expanded),
    )


def vram_offset_to_xy(offset: int) -> tuple[int, int] | None:
    if 0x000 <= offset < 0x040:
        row = 34 + (offset // 32)
        column_32 = 31 - (offset % 32)
        x = column_32 - 2
        return (x, row) if 0 <= x < SCREEN_WIDTH else None

    if MAZE_CENTER_VRAM_START <= offset <= MAZE_CENTER_VRAM_END:
        column_from_right = (offset - MAZE_CENTER_VRAM_START) // 32
        y = 2 + ((offset - MAZE_CENTER_VRAM_START) % 32)
        x = 27 - column_from_right
        return x, y

    if 0x3C0 <= offset <= 0x3FF:
        row = (offset - 0x3C0) // 32
        column_32 = 31 - ((offset - 0x3C0) % 32)
        x = column_32 - 2
        return (x, row) if 0 <= x < SCREEN_WIDTH else None

    raise ValueError(f"Video RAM offset {offset:03X} is outside the 1 KB tile RAM.")


def build_nametable(half_table: RleResult, horizontal_flip: dict[int, int]) -> bytes:
    if half_table.destination_offset != MAZE_CENTER_VRAM_START:
        raise ValueError(
            f"Maze tile table destination was {half_table.destination_offset:02X}; "
            f"expected {MAZE_CENTER_VRAM_START:02X}."
        )
    if len(half_table.expanded) != MAZE_HALF_EXPANDED_BYTES:
        raise ValueError(
            f"Maze tile table expanded to {len(half_table.expanded)} bytes; "
            f"expected {MAZE_HALF_EXPANDED_BYTES}."
        )

    grid = [[0xFC for _ in range(SCREEN_WIDTH)] for _ in range(SCREEN_HEIGHT)]
    for index, tile_id in enumerate(half_table.expanded):
        offset = half_table.destination_offset + index
        xy = vram_offset_to_xy(offset)
        if xy is None:
            continue
        x, y = xy
        grid[y][x] = tile_id

    for y in range(2, 34):
        for right_x in range(14, 28):
            left_x = 27 - right_x
            source_tile = grid[y][right_x]
            grid[y][left_x] = horizontal_flip.get(source_tile, source_tile)

    return bytes(tile_id for row in grid for tile_id in row)


def build_semantic_grid() -> bytes:
    if len(SEMANTIC_TEMPLATE) != 31:
        raise ValueError("Semantic template must describe 31 maze rows.")
    for row in SEMANTIC_TEMPLATE:
        if len(row) != SCREEN_WIDTH:
            raise ValueError("Semantic template rows must be 28 columns wide.")

    grid = [[BLANK for _ in range(SCREEN_WIDTH)] for _ in range(SCREEN_HEIGHT)]
    for template_y, row in enumerate(SEMANTIC_TEMPLATE):
        y = MAZE_TEMPLATE_TOP + template_y
        for x, char in enumerate(row):
            if char == "#":
                value = WALL
            elif char == ".":
                value = PELLET
            elif char == "o":
                value = ENERGIZER
            elif char == "H":
                value = GHOST_HOUSE
            elif char == "-":
                value = GHOST_DOOR
            elif char == "T":
                value = TUNNEL
            elif char == " ":
                value = PATH
            else:
                raise ValueError(f"Unknown semantic template character {char!r}.")
            grid[y][x] = value

    return bytes(value for row in grid for value in row)


def semantic_at(semantic: bytes, x: int, y: int) -> int:
    return semantic[y * SCREEN_WIDTH + x]


def is_graph_walkable(semantic: bytes, x: int, y: int) -> bool:
    if not (0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT):
        return False
    return semantic_at(semantic, x, y) in GRAPH_WALKABLE_CLASSES


def neighbors(semantic: bytes, x: int, y: int) -> list[tuple[int, int, int]]:
    result: list[tuple[int, int, int]] = []
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        nx = x + dx
        ny = y + dy
        if is_graph_walkable(semantic, nx, ny):
            result.append((nx, ny, 0))

    if y == 17 and x == 0 and is_graph_walkable(semantic, 27, y):
        result.append((27, y, FLAG_WARP_EDGE | FLAG_TUNNEL_EDGE))
    elif y == 17 and x == 27 and is_graph_walkable(semantic, 0, y):
        result.append((0, y, FLAG_WARP_EDGE | FLAG_TUNNEL_EDGE))

    return result


def node_flags(semantic: bytes, x: int, y: int, adjacent: list[tuple[int, int, int]]) -> int:
    value = semantic_at(semantic, x, y)
    flags = 0

    if value == ENERGIZER:
        flags |= FLAG_ENERGIZER
    if value == GHOST_DOOR:
        flags |= FLAG_GHOST_ENTRY
    if value == GHOST_HOUSE:
        flags |= FLAG_GHOST_HOUSE
    if value == TUNNEL and x in {0, 27}:
        flags |= FLAG_TUNNEL_ENDPOINT

    normal_dirs = {(nx - x, ny - y) for nx, ny, edge_flags in adjacent if edge_flags == 0}
    if len(adjacent) >= 3:
        flags |= FLAG_INTERSECTION
    elif len(adjacent) == 2:
        if normal_dirs not in ({(0, -1), (0, 1)}, {(-1, 0), (1, 0)}):
            flags |= FLAG_CORNER
    elif len(adjacent) == 1:
        flags |= FLAG_CORNER

    return flags


def should_create_node(semantic: bytes, x: int, y: int) -> bool:
    adjacent = neighbors(semantic, x, y)
    flags = node_flags(semantic, x, y, adjacent)
    value = semantic_at(semantic, x, y)
    if value in {ENERGIZER, GHOST_DOOR}:
        return True
    if value == TUNNEL and x in {0, 27}:
        return True
    return bool(flags & (FLAG_INTERSECTION | FLAG_CORNER))


def build_graph(semantic: bytes) -> tuple[list[GraphNode], list[GraphEdge], bytes]:
    node_positions = [
        (x, y)
        for y in range(SCREEN_HEIGHT)
        for x in range(SCREEN_WIDTH)
        if is_graph_walkable(semantic, x, y) and should_create_node(semantic, x, y)
    ]
    node_ids = {position: node_id for node_id, position in enumerate(node_positions)}

    nodes = [
        GraphNode(
            node_id=node_id,
            x=x,
            y=y,
            semantic_class=semantic_at(semantic, x, y),
            flags=node_flags(semantic, x, y, neighbors(semantic, x, y)),
        )
        for (x, y), node_id in node_ids.items()
    ]

    edges_by_key: dict[tuple[int, int], GraphEdge] = {}
    for x, y in node_positions:
        start_id = node_ids[(x, y)]
        for nx, ny, first_flags in neighbors(semantic, x, y):
            previous = (x, y)
            current = (nx, ny)
            length = 1
            flags = first_flags

            while current not in node_ids:
                current_neighbors = [
                    (cx, cy, edge_flags)
                    for cx, cy, edge_flags in neighbors(semantic, *current)
                    if (cx, cy) != previous
                ]
                if len(current_neighbors) != 1:
                    raise ValueError(f"Corridor walk from {(x, y)} reached ambiguous cell {current}.")

                cx, cy, edge_flags = current_neighbors[0]
                if semantic_at(semantic, *current) == TUNNEL:
                    flags |= FLAG_TUNNEL_EDGE
                flags |= edge_flags
                previous = current
                current = (cx, cy)
                length += 1

                if length > SCREEN_WIDTH * SCREEN_HEIGHT:
                    raise ValueError("Movement graph walk did not terminate.")

            end_id = node_ids[current]
            if start_id == end_id:
                continue
            key = tuple(sorted((start_id, end_id)))
            if key not in edges_by_key:
                edges_by_key[key] = GraphEdge(
                    from_id=key[0],
                    to_id=key[1],
                    length=length,
                    flags=flags,
                )

    edges = [edges_by_key[key] for key in sorted(edges_by_key)]
    graph = bytearray()
    graph.extend(GRAPH_MAGIC)
    graph.extend(struct.pack("<HHHH", GRAPH_VERSION, len(nodes), len(edges), 0))

    for node in nodes:
        graph.extend(
            struct.pack(
                "<HBBBBH",
                node.node_id,
                node.x,
                node.y,
                node.semantic_class,
                len(neighbors(semantic, node.x, node.y)),
                node.flags,
            )
        )

    for edge in edges:
        graph.extend(struct.pack("<HHHH", edge.from_id, edge.to_id, edge.length, edge.flags))

    return nodes, edges, bytes(graph)


def symbol_for_class(value: int) -> str:
    return {
        WALL: "#",
        PATH: " ",
        PELLET: ".",
        ENERGIZER: "o",
        GHOST_HOUSE: "H",
        GHOST_DOOR: "-",
        TUNNEL: "T",
        BLANK: "_",
    }[value]


def format_semantic_map(semantic: bytes) -> list[str]:
    return [
        "".join(symbol_for_class(semantic_at(semantic, x, y)) for x in range(SCREEN_WIDTH))
        for y in range(SCREEN_HEIGHT)
    ]


def write_manifest(
    path: pathlib.Path,
    program_rom: bytes,
    program_pieces: list[tuple[pathlib.Path, bytes]],
    tile_rom: bytes,
    tiles_asset: bytes,
    palette_asset: bytes,
    tile_table: RleResult,
    color_table_raw: bytes,
    nametable: bytes,
    semantic: bytes,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    graph: bytes,
) -> None:
    class_counts = Counter(semantic)
    lines = [
        "# Pac-Man maze extraction manifest",
        "",
        "Source confirmation:",
        "- Pac-Man video RAM 0x4000-0x43FF and color RAM 0x4400-0x47FF use the",
        "  28x36 tile screen mapping documented in Chris Lomont's Pac-Man emulator notes.",
        "  Source: https://www.lomont.org/software/games/pacman/PacmanEmulation.pdf",
        "- The level-1 maze drawing table is read as data from CPU ROM address 0x3435,",
        "  using the documented run-length scheme and mirrored half-maze storage.",
        "  Source: https://pacmanc.blogspot.com/2024/05/characters-sprites-and-colours.html",
        "- Public split-screen research documents playable/video area 0x4040-0x43BF",
        "  and color area 0x4440-0x47BF; color values mark tunnel/no-up zones.",
        "  Source: https://www.debigare.com/pac-man-has-parallel-universes/",
        "",
        "Restricted-source boundary:",
        "- Program ROMs are read only as byte data tables.",
        "- This extractor does not decode opcodes, emulate control flow, or derive gameplay logic.",
        "",
        "Program ROM inputs:",
    ]

    for rom_path, data in program_pieces:
        lines.append(
            f"- {rom_path.relative_to(REPO_ROOT)} bytes={len(data)} sha256={sha256(data)}"
        )

    lines.extend(
        [
            f"Concatenated program ROM bytes: {len(program_rom)}",
            f"Concatenated program ROM SHA-256: {sha256(program_rom)}",
            "",
            f"Character ROM: {DEFAULT_TILE_ROM_PATH.relative_to(REPO_ROOT)}",
            f"Character ROM bytes: {len(tile_rom)}",
            f"Character ROM SHA-256: {sha256(tile_rom)}",
            f"Tile asset: {DEFAULT_TILE_ASSET_PATH.relative_to(REPO_ROOT)}",
            f"Tile asset bytes: {len(tiles_asset)}",
            f"Tile asset SHA-256: {sha256(tiles_asset)}",
            f"VDP-B palette asset: {DEFAULT_PALETTE_ASSET_PATH.relative_to(REPO_ROOT)}",
            f"VDP-B palette bytes: {len(palette_asset)}",
            f"VDP-B palette SHA-256: {sha256(palette_asset)}",
            "",
            "Maze tile table:",
            f"- source CPU address: 0x{tile_table.start:04X}",
            f"- end CPU address: 0x{tile_table.end:04X}",
            f"- encoded bytes including destination and terminator: {tile_table.encoded_size}",
            f"- destination video RAM offset: 0x{tile_table.destination_offset:03X}",
            f"- expanded half-maze bytes: {len(tile_table.expanded)}",
            f"- expanded half-maze SHA-256: {sha256(tile_table.expanded)}",
            "",
            "Maze color table:",
            f"- source CPU address range: 0x{MAZE_COLOR_TABLE_START:04X}-0x{MAZE_COLOR_TABLE_END - 1:04X}",
            f"- raw bytes: {len(color_table_raw)}",
            f"- raw SHA-256: {sha256(color_table_raw)}",
            "- semantic color roles used by later movement code:",
            "  wall/path/pellet=0x10, ghost_door=0x18, no_turn_up=0x1A, tunnel=0x1B",
            "",
            "Output formats:",
            f"- {DEFAULT_NAMETABLE_PATH.relative_to(REPO_ROOT)}: 36*28 row-major tile IDs, one byte per cell",
            f"- {DEFAULT_SEMANTIC_PATH.relative_to(REPO_ROOT)}: 36*28 row-major class IDs, one byte per cell",
            "- class IDs: " + ", ".join(f"{index}={name}" for index, name in enumerate(CLASS_NAMES)),
            f"- {DEFAULT_GRAPH_PATH.relative_to(REPO_ROOT)}: 16-byte header, 8-byte nodes, 8-byte edges",
            "  header=<8s magic, u16 version, u16 nodes, u16 edges, u16 reserved>",
            "  node=<u16 id, u8 x, u8 y, u8 class, u8 degree, u16 flags>",
            "  edge=<u16 from, u16 to, u16 length, u16 flags>",
            "",
            "Output hashes:",
            f"- maze_nametable bytes={len(nametable)} sha256={sha256(nametable)}",
            f"- maze_semantic bytes={len(semantic)} sha256={sha256(semantic)}",
            f"- maze_graph bytes={len(graph)} sha256={sha256(graph)}",
            "",
            "Semantic counts:",
        ]
    )

    for index, name in enumerate(CLASS_NAMES):
        lines.append(f"- {name}: {class_counts[index]}")

    lines.extend(
        [
            "",
            f"Movement graph nodes: {len(nodes)}",
            f"Movement graph edges: {len(edges)}",
            "Movement graph flag bits:",
            f"- 0x{FLAG_INTERSECTION:04X}: intersection",
            f"- 0x{FLAG_CORNER:04X}: corner/dead-end",
            f"- 0x{FLAG_TUNNEL_ENDPOINT:04X}: tunnel endpoint",
            f"- 0x{FLAG_ENERGIZER:04X}: energizer",
            f"- 0x{FLAG_GHOST_ENTRY:04X}: ghost door/entry",
            f"- 0x{FLAG_GHOST_HOUSE:04X}: ghost house",
            f"- 0x{FLAG_WARP_EDGE:04X}: warp edge",
            f"- 0x{FLAG_TUNNEL_EDGE:04X}: tunnel edge",
            "",
            "Semantic map (_ = blank/HUD):",
        ]
    )

    lines.extend(format_semantic_map(semantic))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    path: pathlib.Path,
    program_rom: bytes,
    program_pieces: list[tuple[pathlib.Path, bytes]],
    tile_table: RleResult,
    color_table_raw: bytes,
    nametable: bytes,
    semantic: bytes,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    graph: bytes,
) -> None:
    class_counts = Counter(semantic)
    lines = [
        "Pac-Man maze extraction summary",
        f"Program ROM bytes: {len(program_rom)}",
        f"Program ROM SHA-256: {sha256(program_rom)}",
    ]
    for rom_path, data in program_pieces:
        lines.append(f"  {rom_path.relative_to(REPO_ROOT)} SHA-256: {sha256(data)}")

    lines.extend(
        [
            f"Maze tile table source: 0x{tile_table.start:04X}-0x{tile_table.end - 1:04X}",
            f"Maze tile table encoded bytes: {tile_table.encoded_size}",
            f"Maze tile table expanded bytes: {len(tile_table.expanded)}",
            f"Maze color table source: 0x{MAZE_COLOR_TABLE_START:04X}-0x{MAZE_COLOR_TABLE_END - 1:04X}",
            f"Maze color table raw bytes: {len(color_table_raw)}",
            f"Maze color table raw SHA-256: {sha256(color_table_raw)}",
            f"Output nametable: {DEFAULT_NAMETABLE_PATH.relative_to(REPO_ROOT)}",
            f"Output nametable bytes: {len(nametable)}",
            f"Output nametable SHA-256: {sha256(nametable)}",
            f"Output semantic: {DEFAULT_SEMANTIC_PATH.relative_to(REPO_ROOT)}",
            f"Output semantic bytes: {len(semantic)}",
            f"Output semantic SHA-256: {sha256(semantic)}",
            f"Output graph: {DEFAULT_GRAPH_PATH.relative_to(REPO_ROOT)}",
            f"Output graph bytes: {len(graph)}",
            f"Output graph SHA-256: {sha256(graph)}",
            "Semantic counts:",
        ]
    )

    for index, name in enumerate(CLASS_NAMES):
        lines.append(f"  {name}: {class_counts[index]}")

    lines.extend(
        [
            f"Movement graph nodes: {len(nodes)}",
            f"Movement graph edges: {len(edges)}",
            "Restricted program ROM handling: data-table reads only; no disassembly/emulation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Pac-Man maze nametable, semantic grid, and movement graph."
    )
    parser.add_argument("--rom-dir", type=pathlib.Path, default=DEFAULT_ROM_DIR)
    parser.add_argument("--tile-rom", type=pathlib.Path, default=DEFAULT_TILE_ROM_PATH)
    parser.add_argument("--tile-asset", type=pathlib.Path, default=DEFAULT_TILE_ASSET_PATH)
    parser.add_argument("--palette-asset", type=pathlib.Path, default=DEFAULT_PALETTE_ASSET_PATH)
    parser.add_argument("--nametable", type=pathlib.Path, default=DEFAULT_NAMETABLE_PATH)
    parser.add_argument("--semantic", type=pathlib.Path, default=DEFAULT_SEMANTIC_PATH)
    parser.add_argument("--graph", type=pathlib.Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--summary", type=pathlib.Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    program_rom, program_pieces = read_program_roms(args.rom_dir.resolve())

    tile_rom = args.tile_rom.resolve().read_bytes()
    if len(tile_rom) != TILE_ROM_SIZE:
        raise ValueError(f"{args.tile_rom} must be {TILE_ROM_SIZE} bytes; got {len(tile_rom)}.")

    tiles_asset = args.tile_asset.resolve().read_bytes()
    if len(tiles_asset) != TILESET_ASSET_SIZE:
        raise ValueError(f"{args.tile_asset} must be {TILESET_ASSET_SIZE} bytes; got {len(tiles_asset)}.")

    palette_asset = args.palette_asset.resolve().read_bytes()
    if len(palette_asset) != PALETTE_ASSET_SIZE:
        raise ValueError(
            f"{args.palette_asset} must be {PALETTE_ASSET_SIZE} bytes; got {len(palette_asset)}."
        )

    tile_table = decode_maze_rle(program_rom, MAZE_TILE_TABLE_START)
    color_table_raw = program_rom[MAZE_COLOR_TABLE_START:MAZE_COLOR_TABLE_END]
    horizontal_flip = build_horizontal_flip_map(tile_rom)
    nametable = build_nametable(tile_table, horizontal_flip)
    semantic = build_semantic_grid()
    nodes, edges, graph = build_graph(semantic)

    for path in (
        args.nametable.resolve(),
        args.semantic.resolve(),
        args.graph.resolve(),
        args.manifest.resolve(),
        args.summary.resolve(),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    args.nametable.resolve().write_bytes(nametable)
    args.semantic.resolve().write_bytes(semantic)
    args.graph.resolve().write_bytes(graph)
    write_manifest(
        args.manifest.resolve(),
        program_rom,
        program_pieces,
        tile_rom,
        tiles_asset,
        palette_asset,
        tile_table,
        color_table_raw,
        nametable,
        semantic,
        nodes,
        edges,
        graph,
    )
    write_summary(
        args.summary.resolve(),
        program_rom,
        program_pieces,
        tile_table,
        color_table_raw,
        nametable,
        semantic,
        nodes,
        edges,
        graph,
    )

    print(f"Read {len(program_rom)} bytes from {args.rom_dir.resolve().relative_to(REPO_ROOT)} program ROMs")
    print(
        f"Decoded maze tile table 0x{tile_table.start:04X}-0x{tile_table.end - 1:04X} "
        f"to {len(tile_table.expanded)} half-maze bytes"
    )
    print(
        f"Read raw maze color table 0x{MAZE_COLOR_TABLE_START:04X}-"
        f"0x{MAZE_COLOR_TABLE_END - 1:04X} ({len(color_table_raw)} bytes)"
    )
    print(f"Wrote {len(nametable)} bytes to {args.nametable.resolve().relative_to(REPO_ROOT)}")
    print(f"Wrote {len(semantic)} bytes to {args.semantic.resolve().relative_to(REPO_ROOT)}")
    print(f"Wrote {len(graph)} bytes to {args.graph.resolve().relative_to(REPO_ROOT)}")
    print(f"Movement graph: {len(nodes)} nodes, {len(edges)} edges")
    print(f"Wrote manifest to {args.manifest.resolve().relative_to(REPO_ROOT)}")
    print(f"Wrote summary to {args.summary.resolve().relative_to(REPO_ROOT)}")
    print(f"Nametable SHA-256: {sha256(nametable)}")
    print(f"Semantic SHA-256: {sha256(semantic)}")
    print(f"Graph SHA-256: {sha256(graph)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
