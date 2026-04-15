#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
from collections import Counter
from dataclasses import dataclass


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DEFAULT_NAMETABLE_PATH = REPO_ROOT / "assets" / "maze_nametable.bin"
DEFAULT_SEMANTIC_PATH = REPO_ROOT / "assets" / "maze_semantic.bin"
DEFAULT_GRAPH_PATH = REPO_ROOT / "assets" / "maze_graph.bin"
DEFAULT_TILE_ASSET_PATH = REPO_ROOT / "assets" / "tiles_vdpb.bin"
DEFAULT_PALETTE_PATH = REPO_ROOT / "assets" / "palette_b.bin"

DEFAULT_COORDMAP_PATH = REPO_ROOT / "assets" / "maze_v8_coordmap.bin"
DEFAULT_DRAWLIST_PATH = REPO_ROOT / "assets" / "maze_v8_drawlist.bin"
DEFAULT_FRAMEBUFFER_PATH = REPO_ROOT / "assets" / "maze_v8_framebuffer.bin"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "assets" / "maze_v8_manifest.txt"
DEFAULT_SUMMARY_PATH = REPO_ROOT / "assets" / "maze_v8_summary.txt"
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / "T006-maze-tile-re-authoring"
DEFAULT_PREVIEW_PATH = DEFAULT_EVIDENCE_DIR / "maze_v8_preview.ppm"
DEFAULT_EVIDENCE_SUMMARY_PATH = DEFAULT_EVIDENCE_DIR / "summary.txt"

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 212
FRAMEBUFFER_BYTES_PER_ROW = SCREEN_WIDTH // 2
FRAMEBUFFER_SIZE = FRAMEBUFFER_BYTES_PER_ROW * SCREEN_HEIGHT

ARCADE_WIDTH = 28
ARCADE_HEIGHT = 36
MAZE_TOP = 3
MAZE_ROWS = 31
MAZE_NATIVE_WIDTH = 224
MAZE_FIT_HEIGHT = 196
MAZE_X = (SCREEN_WIDTH - MAZE_NATIVE_WIDTH) // 2
MAZE_Y = 8
HUD_HEIGHT = 8
STATUS_Y = 204

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
GRAPH_WALKABLE_CLASSES = {PATH, PELLET, ENERGIZER, GHOST_DOOR, TUNNEL}
DRAWN_CLASSES = {WALL, PELLET, ENERGIZER, GHOST_HOUSE, GHOST_DOOR, TUNNEL}

GRAPH_MAGIC = b"PMVGRAF1"
GRAPH_VERSION = 1
GRAPH_HEADER_SIZE = 16
GRAPH_NODE_SIZE = 8
GRAPH_EDGE_SIZE = 8
FLAG_WARP_EDGE = 0x0040

COORD_RECORD = struct.Struct("<BBBBBBH")
COORD_RECORD_SIZE = COORD_RECORD.size
COORD_FLAG_MAPPED = 0x01
COORD_FLAG_WALKABLE = 0x02
COORD_FLAG_GRAPH_NODE = 0x04
COORD_FLAG_PELLET = 0x08
COORD_FLAG_WARP_ENDPOINT = 0x10

DRAWLIST_MAGIC = b"PMV8DRAW"
DRAWLIST_VERSION = 1
DRAW_HEADER = struct.Struct("<8sHHHH")
DRAW_RECORD = struct.Struct("<BBBBBBH")
DRAW_RECORD_SIZE = DRAW_RECORD.size


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2


@dataclass(frozen=True)
class GraphNode:
    node_id: int
    x: int
    y: int
    semantic_class: int
    degree: int
    flags: int


@dataclass(frozen=True)
class GraphEdge:
    from_id: int
    to_id: int
    length: int
    flags: int


@dataclass(frozen=True)
class TopologyChecks:
    graph_nodes: int
    graph_edges: int
    mapped_graph_nodes: int
    graph_node_center_overlaps: int
    walkable_adjacencies: int
    contiguous_adjacencies: int
    warp_edges: int
    mapping_bounds: Rect


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: pathlib.Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def read_exact(path: pathlib.Path, expected_size: int, label: str) -> bytes:
    data = path.read_bytes()
    if len(data) != expected_size:
        raise ValueError(f"{relative(path)} must be {expected_size} bytes for {label}; got {len(data)}.")
    return data


def make_bounds(total: int, segments: int) -> list[int]:
    return [(index * total) // segments for index in range(segments + 1)]


Y_BOUNDS = make_bounds(MAZE_FIT_HEIGHT, MAZE_ROWS)


def parse_graph(graph: bytes) -> tuple[list[GraphNode], list[GraphEdge]]:
    if len(graph) < GRAPH_HEADER_SIZE:
        raise ValueError("maze_graph.bin is too small to contain a graph header.")

    magic, version, node_count, edge_count, reserved = struct.unpack_from("<8sHHHH", graph, 0)
    if magic != GRAPH_MAGIC:
        raise ValueError(f"maze_graph.bin magic was {magic!r}; expected {GRAPH_MAGIC!r}.")
    if version != GRAPH_VERSION:
        raise ValueError(f"maze_graph.bin version was {version}; expected {GRAPH_VERSION}.")
    if reserved != 0:
        raise ValueError(f"maze_graph.bin reserved header field was {reserved}; expected 0.")

    expected_size = GRAPH_HEADER_SIZE + node_count * GRAPH_NODE_SIZE + edge_count * GRAPH_EDGE_SIZE
    if len(graph) != expected_size:
        raise ValueError(f"maze_graph.bin must be {expected_size} bytes from header counts; got {len(graph)}.")

    offset = GRAPH_HEADER_SIZE
    nodes: list[GraphNode] = []
    for _ in range(node_count):
        node_id, x, y, semantic_class, degree, flags = struct.unpack_from("<HBBBBH", graph, offset)
        nodes.append(GraphNode(node_id, x, y, semantic_class, degree, flags))
        offset += GRAPH_NODE_SIZE

    edges: list[GraphEdge] = []
    for _ in range(edge_count):
        from_id, to_id, length, flags = struct.unpack_from("<HHHH", graph, offset)
        edges.append(GraphEdge(from_id, to_id, length, flags))
        offset += GRAPH_EDGE_SIZE

    return nodes, edges


def is_mapped_cell(x: int, y: int) -> bool:
    return 0 <= x < ARCADE_WIDTH and MAZE_TOP <= y < MAZE_TOP + MAZE_ROWS


def rect_for_cell(x: int, y: int) -> Rect:
    if not is_mapped_cell(x, y):
        return Rect(0, 0, 0, 0)

    row = y - MAZE_TOP
    y0 = MAZE_Y + Y_BOUNDS[row]
    y1 = MAZE_Y + Y_BOUNDS[row + 1]
    return Rect(MAZE_X + x * 8, y0, 8, y1 - y0)


def semantic_at(semantic: bytes, x: int, y: int) -> int:
    return semantic[y * ARCADE_WIDTH + x]


def is_graph_walkable(semantic: bytes, x: int, y: int) -> bool:
    return is_mapped_cell(x, y) and semantic_at(semantic, x, y) in GRAPH_WALKABLE_CLASSES


def build_coordmap(nametable: bytes, semantic: bytes, nodes: list[GraphNode]) -> bytes:
    node_positions = {(node.x, node.y) for node in nodes}
    records = bytearray()

    for y in range(ARCADE_HEIGHT):
        for x in range(ARCADE_WIDTH):
            value = semantic_at(semantic, x, y)
            rect = rect_for_cell(x, y)
            flags = 0
            if rect.width and rect.height:
                flags |= COORD_FLAG_MAPPED
            if value in GRAPH_WALKABLE_CLASSES:
                flags |= COORD_FLAG_WALKABLE
            if (x, y) in node_positions:
                flags |= COORD_FLAG_GRAPH_NODE
            if value in {PELLET, ENERGIZER}:
                flags |= COORD_FLAG_PELLET
            if value == TUNNEL and x in {0, ARCADE_WIDTH - 1}:
                flags |= COORD_FLAG_WARP_ENDPOINT

            records.extend(
                COORD_RECORD.pack(
                    rect.x,
                    rect.y,
                    rect.width,
                    rect.height,
                    value,
                    flags,
                    nametable[y * ARCADE_WIDTH + x],
                )
            )

    expected_size = ARCADE_WIDTH * ARCADE_HEIGHT * COORD_RECORD_SIZE
    if len(records) != expected_size:
        raise ValueError(f"Coordinate map had unexpected size {len(records)}.")
    return bytes(records)


def neighbor_class(semantic: bytes, x: int, y: int, dx: int, dy: int) -> int | None:
    nx = x + dx
    ny = y + dy
    if not is_mapped_cell(nx, ny):
        return None
    return semantic_at(semantic, nx, ny)


def edge_mask_for_wall(semantic: bytes, x: int, y: int) -> int:
    mask = 0
    for bit, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
        adjacent = neighbor_class(semantic, x, y, dx, dy)
        if adjacent is not None and adjacent != WALL:
            mask |= 1 << bit
    return mask


def build_drawlist(semantic: bytes) -> bytes:
    records = bytearray()
    count = 0

    for y in range(ARCADE_HEIGHT):
        for x in range(ARCADE_WIDTH):
            value = semantic_at(semantic, x, y)
            if value not in DRAWN_CLASSES:
                continue

            rect = rect_for_cell(x, y)
            if rect.width == 0 or rect.height == 0:
                continue

            style = edge_mask_for_wall(semantic, x, y) if value == WALL else 0
            source_index = y * ARCADE_WIDTH + x
            records.extend(DRAW_RECORD.pack(rect.x, rect.y, rect.width, rect.height, value, style, source_index))
            count += 1

    header = DRAW_HEADER.pack(DRAWLIST_MAGIC, DRAWLIST_VERSION, count, DRAW_RECORD_SIZE, 0)
    return header + bytes(records)


def decode_palette_entry(palette: bytes, index: int) -> tuple[int, int, int]:
    byte0 = palette[index * 2]
    byte1 = palette[index * 2 + 1]
    red = (byte0 >> 4) & 0x07
    green = byte0 & 0x07
    blue = byte1 & 0x07
    return tuple(int(channel * 255 / 7 + 0.5) for channel in (red, green, blue))


def set_pixel(pixels: list[list[int]], x: int, y: int, color: int) -> None:
    if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
        pixels[y][x] = color


def fill_rect(pixels: list[list[int]], rect: Rect, color: int) -> None:
    for py in range(rect.y, rect.y2):
        for px in range(rect.x, rect.x2):
            set_pixel(pixels, px, py, color)


def stroke_rect(pixels: list[list[int]], rect: Rect, color: int) -> None:
    for px in range(rect.x, rect.x2):
        set_pixel(pixels, px, rect.y, color)
        set_pixel(pixels, px, rect.y2 - 1, color)
    for py in range(rect.y, rect.y2):
        set_pixel(pixels, rect.x, py, color)
        set_pixel(pixels, rect.x2 - 1, py, color)


def draw_disc(pixels: list[list[int]], cx: int, cy: int, radius: int, color: int) -> None:
    radius_squared = radius * radius
    for py in range(cy - radius, cy + radius + 1):
        for px in range(cx - radius, cx + radius + 1):
            if (px - cx) * (px - cx) + (py - cy) * (py - cy) <= radius_squared:
                set_pixel(pixels, px, py, color)


def draw_wall(pixels: list[list[int]], semantic: bytes, x: int, y: int, rect: Rect) -> None:
    fill_rect(pixels, rect, 1)
    mask = edge_mask_for_wall(semantic, x, y)

    if mask & 0x01:
        for px in range(rect.x, rect.x2):
            set_pixel(pixels, px, rect.y, 2)
    if mask & 0x02:
        for py in range(rect.y, rect.y2):
            set_pixel(pixels, rect.x2 - 1, py, 2)
    if mask & 0x04:
        for px in range(rect.x, rect.x2):
            set_pixel(pixels, px, rect.y2 - 1, 2)
    if mask & 0x08:
        for py in range(rect.y, rect.y2):
            set_pixel(pixels, rect.x, py, 2)


def render_pixels(semantic: bytes) -> list[list[int]]:
    pixels = [[0 for _ in range(SCREEN_WIDTH)] for _ in range(SCREEN_HEIGHT)]

    for y in range(ARCADE_HEIGHT):
        for x in range(ARCADE_WIDTH):
            value = semantic_at(semantic, x, y)
            rect = rect_for_cell(x, y)
            if rect.width == 0 or rect.height == 0:
                continue

            if value == WALL:
                draw_wall(pixels, semantic, x, y, rect)
            elif value == GHOST_HOUSE:
                stroke_rect(pixels, rect, 2)
            elif value == GHOST_DOOR:
                fill_rect(pixels, rect, 5)
            elif value == TUNNEL:
                cx, cy = rect.center
                fill_rect(pixels, Rect(rect.x, cy, rect.width, 1), 2)
                set_pixel(pixels, cx, cy, 3)
            elif value == PELLET:
                cx, cy = rect.center
                fill_rect(pixels, Rect(cx - 1, cy - 1, 2, 2), 3)
            elif value == ENERGIZER:
                cx, cy = rect.center
                draw_disc(pixels, cx, cy, 2, 4)

    return pixels


def pack_framebuffer(pixels: list[list[int]]) -> bytes:
    packed = bytearray()
    for row in pixels:
        if len(row) != SCREEN_WIDTH:
            raise ValueError("Rendered framebuffer row had unexpected width.")
        for x in range(0, SCREEN_WIDTH, 2):
            packed.append(((row[x] & 0x0F) << 4) | (row[x + 1] & 0x0F))

    if len(packed) != FRAMEBUFFER_SIZE:
        raise ValueError(f"Packed framebuffer had unexpected size {len(packed)}.")
    return bytes(packed)


def write_ppm(path: pathlib.Path, pixels: list[list[int]], palette: bytes) -> None:
    rgb_palette = [decode_palette_entry(palette, index) for index in range(16)]
    payload = bytearray()
    for row in pixels:
        for value in row:
            payload.extend(rgb_palette[value & 0x0F])

    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"P6\n{SCREEN_WIDTH} {SCREEN_HEIGHT}\n255\n".encode("ascii")
    path.write_bytes(header + bytes(payload))


def rects_touch(a: Rect, b: Rect) -> bool:
    vertical_edge_touch = (a.x2 == b.x or b.x2 == a.x) and max(a.y, b.y) < min(a.y2, b.y2)
    horizontal_edge_touch = (a.y2 == b.y or b.y2 == a.y) and max(a.x, b.x) < min(a.x2, b.x2)
    return vertical_edge_touch or horizontal_edge_touch


def compute_topology_checks(semantic: bytes, nodes: list[GraphNode], edges: list[GraphEdge]) -> TopologyChecks:
    graph_centers: dict[tuple[int, int], tuple[int, int]] = {}
    overlaps = 0

    for node in nodes:
        rect = rect_for_cell(node.x, node.y)
        if rect.width == 0 or rect.height == 0:
            continue
        center = rect.center
        if center in graph_centers:
            overlaps += 1
        graph_centers[center] = (node.x, node.y)

    walkable_adjacencies = 0
    contiguous_adjacencies = 0
    for y in range(MAZE_TOP, MAZE_TOP + MAZE_ROWS):
        for x in range(ARCADE_WIDTH):
            if not is_graph_walkable(semantic, x, y):
                continue
            for dx, dy in ((1, 0), (0, 1)):
                nx = x + dx
                ny = y + dy
                if is_graph_walkable(semantic, nx, ny):
                    walkable_adjacencies += 1
                    if rects_touch(rect_for_cell(x, y), rect_for_cell(nx, ny)):
                        contiguous_adjacencies += 1

    mapped_cells = [
        rect_for_cell(x, y)
        for y in range(ARCADE_HEIGHT)
        for x in range(ARCADE_WIDTH)
        if rect_for_cell(x, y).width and rect_for_cell(x, y).height
    ]
    min_x = min(rect.x for rect in mapped_cells)
    min_y = min(rect.y for rect in mapped_cells)
    max_x = max(rect.x2 for rect in mapped_cells)
    max_y = max(rect.y2 for rect in mapped_cells)

    return TopologyChecks(
        graph_nodes=len(nodes),
        graph_edges=len(edges),
        mapped_graph_nodes=len(graph_centers),
        graph_node_center_overlaps=overlaps,
        walkable_adjacencies=walkable_adjacencies,
        contiguous_adjacencies=contiguous_adjacencies,
        warp_edges=sum(1 for edge in edges if edge.flags & FLAG_WARP_EDGE),
        mapping_bounds=Rect(min_x, min_y, max_x - min_x, max_y - min_y),
    )


def validate_inputs(nametable: bytes, semantic: bytes, graph_nodes: list[GraphNode]) -> None:
    if len(nametable) != ARCADE_WIDTH * ARCADE_HEIGHT:
        raise ValueError("maze_nametable.bin must be 36*28 bytes.")
    if len(semantic) != ARCADE_WIDTH * ARCADE_HEIGHT:
        raise ValueError("maze_semantic.bin must be 36*28 bytes.")
    if any(value >= len(CLASS_NAMES) for value in semantic):
        raise ValueError("maze_semantic.bin contains an unknown semantic class ID.")
    if any(not is_mapped_cell(node.x, node.y) for node in graph_nodes):
        raise ValueError("At least one graph node is outside the fitted maze rows.")


def output_lines(
    inputs: dict[str, tuple[pathlib.Path, bytes]],
    outputs: dict[str, tuple[pathlib.Path, bytes]],
    checks: TopologyChecks,
    preview_path: pathlib.Path,
) -> tuple[list[str], list[str]]:
    class_counts = Counter(inputs["semantic"][1])
    row_heights = [Y_BOUNDS[index + 1] - Y_BOUNDS[index] for index in range(MAZE_ROWS)]

    manifest = [
        "# Pac-Man Vanguard 8 portrait maze re-authoring manifest",
        "",
        "Layout:",
        f"- Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}",
        f"- HUD band: y=0-{HUD_HEIGHT - 1}",
        f"- Maze area: x={MAZE_X}-{MAZE_X + MAZE_NATIVE_WIDTH - 1}, y={MAZE_Y}-{MAZE_Y + MAZE_FIT_HEIGHT - 1}",
        f"- Side margins: left={MAZE_X}px, right={SCREEN_WIDTH - (MAZE_X + MAZE_NATIVE_WIDTH)}px",
        f"- Status band begins at y={STATUS_Y}",
        "- Orientation: no render rotation; arcade player-view portrait maze is preserved.",
        f"- Arcade maze rows mapped: {MAZE_TOP}-{MAZE_TOP + MAZE_ROWS - 1}",
        "- V8 column widths across arcade columns: 8px each",
        f"- V8 row heights across arcade maze rows: min={min(row_heights)}, max={max(row_heights)}, sequence={','.join(str(v) for v in row_heights)}",
        "",
        "Input hashes:",
    ]
    for label, (path, data) in inputs.items():
        manifest.append(f"- {label}: {relative(path)} bytes={len(data)} sha256={sha256(data)}")

    manifest.extend(
        [
            "",
            "Output formats:",
            f"- coordmap: {ARCADE_HEIGHT}*{ARCADE_WIDTH} row-major records, {COORD_RECORD_SIZE} bytes each, <x,y,width,height,class,flags,source_tile_id>",
            f"  flags: mapped=0x{COORD_FLAG_MAPPED:02X}, walkable=0x{COORD_FLAG_WALKABLE:02X}, graph_node=0x{COORD_FLAG_GRAPH_NODE:02X}, pellet=0x{COORD_FLAG_PELLET:02X}, warp_endpoint=0x{COORD_FLAG_WARP_ENDPOINT:02X}",
            f"- drawlist: header <8s magic,u16 version,u16 count,u16 record_size,u16 reserved>, records <x,y,width,height,class,style,source_cell_index>",
            f"- framebuffer: V9938 Graphic 4 packed pixels, {SCREEN_HEIGHT} rows * {FRAMEBUFFER_BYTES_PER_ROW} bytes",
            "",
            "Output hashes:",
        ]
    )
    for label, (path, data) in outputs.items():
        manifest.append(f"- {label}: {relative(path)} bytes={len(data)} sha256={sha256(data)}")

    manifest.extend(["", "Semantic counts:"])
    for index, name in enumerate(CLASS_NAMES):
        manifest.append(f"- {name}: {class_counts[index]}")

    manifest.extend(
        [
            "",
            "Topology checks:",
            f"- graph_nodes: {checks.graph_nodes}",
            f"- mapped_graph_nodes: {checks.mapped_graph_nodes}",
            f"- graph_node_center_overlaps: {checks.graph_node_center_overlaps}",
            f"- graph_edges: {checks.graph_edges}",
            f"- walkable_adjacencies: {checks.walkable_adjacencies}",
            f"- contiguous_adjacencies: {checks.contiguous_adjacencies}",
            f"- warp_edges: {checks.warp_edges}",
            f"- mapping_bounds: x={checks.mapping_bounds.x}-{checks.mapping_bounds.x2 - 1}, y={checks.mapping_bounds.y}-{checks.mapping_bounds.y2 - 1}, width={checks.mapping_bounds.width}, height={checks.mapping_bounds.height}",
            f"- preview: {relative(preview_path)}",
        ]
    )

    summary = [
        "Pac-Man Vanguard 8 portrait maze re-authoring summary",
        f"Maze area: {MAZE_NATIVE_WIDTH}x{MAZE_FIT_HEIGHT} at ({MAZE_X},{MAZE_Y}); display {SCREEN_WIDTH}x{SCREEN_HEIGHT}",
        f"Side margins: left={MAZE_X}px, right={SCREEN_WIDTH - (MAZE_X + MAZE_NATIVE_WIDTH)}px",
        f"Mapped arcade maze rows: {MAZE_TOP}-{MAZE_TOP + MAZE_ROWS - 1}; columns: 0-{ARCADE_WIDTH - 1}",
        "Column widths: 8px each",
        f"Row heights: min={min(row_heights)}, max={max(row_heights)}, sequence={','.join(str(v) for v in row_heights)}",
    ]
    for label, (path, data) in outputs.items():
        summary.append(f"{label}: {relative(path)} bytes={len(data)} sha256={sha256(data)}")
    summary.extend(
        [
            f"Graph nodes mapped: {checks.mapped_graph_nodes}/{checks.graph_nodes}",
            f"Graph node center overlaps: {checks.graph_node_center_overlaps}",
            f"Walkable adjacencies contiguous: {checks.contiguous_adjacencies}/{checks.walkable_adjacencies}",
            f"Warp edges preserved as non-contiguous wrap links: {checks.warp_edges}",
            f"Mapping bounds: x={checks.mapping_bounds.x}-{checks.mapping_bounds.x2 - 1}, y={checks.mapping_bounds.y}-{checks.mapping_bounds.y2 - 1}",
            f"Preview: {relative(preview_path)}",
        ]
    )

    return manifest, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-author the extracted Pac-Man maze into a fitted portrait Vanguard 8 layout."
    )
    parser.add_argument("--nametable", type=pathlib.Path, default=DEFAULT_NAMETABLE_PATH)
    parser.add_argument("--semantic", type=pathlib.Path, default=DEFAULT_SEMANTIC_PATH)
    parser.add_argument("--graph", type=pathlib.Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--tiles", type=pathlib.Path, default=DEFAULT_TILE_ASSET_PATH)
    parser.add_argument("--palette", type=pathlib.Path, default=DEFAULT_PALETTE_PATH)
    parser.add_argument("--coordmap-out", type=pathlib.Path, default=DEFAULT_COORDMAP_PATH)
    parser.add_argument("--drawlist-out", type=pathlib.Path, default=DEFAULT_DRAWLIST_PATH)
    parser.add_argument("--framebuffer-out", type=pathlib.Path, default=DEFAULT_FRAMEBUFFER_PATH)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--summary", type=pathlib.Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--preview", type=pathlib.Path, default=DEFAULT_PREVIEW_PATH)
    parser.add_argument("--evidence-summary", type=pathlib.Path, default=DEFAULT_EVIDENCE_SUMMARY_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    nametable_path = args.nametable.resolve()
    semantic_path = args.semantic.resolve()
    graph_path = args.graph.resolve()
    tiles_path = args.tiles.resolve()
    palette_path = args.palette.resolve()

    nametable = read_exact(nametable_path, ARCADE_WIDTH * ARCADE_HEIGHT, "arcade nametable")
    semantic = read_exact(semantic_path, ARCADE_WIDTH * ARCADE_HEIGHT, "semantic maze")
    graph = graph_path.read_bytes()
    tiles = read_exact(tiles_path, 8192, "Graphic 4 tile bank")
    palette = read_exact(palette_path, 32, "VDP-B palette")

    nodes, edges = parse_graph(graph)
    validate_inputs(nametable, semantic, nodes)

    coordmap = build_coordmap(nametable, semantic, nodes)
    drawlist = build_drawlist(semantic)
    pixels = render_pixels(semantic)
    framebuffer = pack_framebuffer(pixels)
    checks = compute_topology_checks(semantic, nodes, edges)

    expected_bounds = Rect(MAZE_X, MAZE_Y, MAZE_NATIVE_WIDTH, MAZE_FIT_HEIGHT)
    if checks.mapped_graph_nodes != checks.graph_nodes:
        raise ValueError("Not every graph node mapped into the V8 maze area.")
    if checks.graph_node_center_overlaps != 0:
        raise ValueError("At least one mapped graph node center overlaps another graph node.")
    if checks.walkable_adjacencies != checks.contiguous_adjacencies:
        raise ValueError("At least one adjacent walkable cell is not contiguous in the V8 layout.")
    if checks.mapping_bounds != expected_bounds:
        raise ValueError("Mapping bounds do not match the planned portrait maze area.")

    output_paths = {
        "coordmap": args.coordmap_out.resolve(),
        "drawlist": args.drawlist_out.resolve(),
        "framebuffer": args.framebuffer_out.resolve(),
    }
    outputs = {
        "coordmap": (output_paths["coordmap"], coordmap),
        "drawlist": (output_paths["drawlist"], drawlist),
        "framebuffer": (output_paths["framebuffer"], framebuffer),
    }
    inputs = {
        "nametable": (nametable_path, nametable),
        "semantic": (semantic_path, semantic),
        "graph": (graph_path, graph),
        "tiles": (tiles_path, tiles),
        "palette": (palette_path, palette),
    }

    for path, data in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    preview_path = args.preview.resolve()
    write_ppm(preview_path, pixels, palette)

    manifest_lines, summary_lines = output_lines(inputs, outputs, checks, preview_path)
    manifest_text = "\n".join(manifest_lines) + "\n"
    summary_text = "\n".join(summary_lines) + "\n"

    manifest_path = args.manifest.resolve()
    summary_path = args.summary.resolve()
    evidence_summary_path = args.evidence_summary.resolve()
    for path, text in (
        (manifest_path, manifest_text),
        (summary_path, summary_text),
        (evidence_summary_path, summary_text),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    print(summary_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
