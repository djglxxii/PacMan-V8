#!/usr/bin/env python3

from __future__ import annotations

from _common import asset_relpath, require_input, run_tool, write_output


def main() -> int:
    def action() -> None:
        require_input("82s123.7f")
        palette_a_path = write_output("palette_a.bin", bytes(32))
        palette_b_path = write_output("palette_b.bin", bytes(32))
        print(
            "conv_palette: 32 + 32 bytes written to "
            f"{asset_relpath(palette_a_path)}, {asset_relpath(palette_b_path)}"
        )

    return run_tool("conv_palette", action)


if __name__ == "__main__":
    raise SystemExit(main())
