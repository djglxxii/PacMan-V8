#!/usr/bin/env python3

from __future__ import annotations

from _common import asset_relpath, require_input, run_tool, write_output


def main() -> int:
    def action() -> None:
        require_input("pacman.5f")
        require_input("82s126.4a")
        patterns_path = write_output("sprites_patterns.bin", b"")
        colors_path = write_output("sprites_colors.bin", b"")
        print(
            "conv_sprites: 0 + 0 bytes written to "
            f"{asset_relpath(patterns_path)}, {asset_relpath(colors_path)}"
        )

    return run_tool("conv_sprites", action)


if __name__ == "__main__":
    raise SystemExit(main())
