#!/usr/bin/env python3

from __future__ import annotations

from _common import asset_relpath, require_input, run_tool, write_output


def main() -> int:
    def action() -> None:
        require_input("pacman.5e")
        font_path = write_output("hud_font.bin", b"")
        print(f"conv_hud_font: 0 bytes written to {asset_relpath(font_path)}")

    return run_tool("conv_hud_font", action)


if __name__ == "__main__":
    raise SystemExit(main())
