#!/usr/bin/env python3

from __future__ import annotations

from _common import asset_relpath, require_input, run_tool, write_output


def main() -> int:
    def action() -> None:
        require_input("pacman.5e")
        require_input("82s126.4a")
        tiles_path = write_output("tiles_vdpb.bin", b"")
        nametable_path = write_output("tile_nametable.bin", b"")
        print(
            "conv_tiles: 0 + 0 bytes written to "
            f"{asset_relpath(tiles_path)}, {asset_relpath(nametable_path)}"
        )

    return run_tool("conv_tiles", action)


if __name__ == "__main__":
    raise SystemExit(main())
