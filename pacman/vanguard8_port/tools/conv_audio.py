#!/usr/bin/env python3

from __future__ import annotations

from _common import asset_relpath, require_input, run_tool, write_output


def main() -> int:
    def action() -> None:
        require_input("82s126.1m")
        instruments_path = write_output("wsg_instruments.bin", b"")
        music_path = write_output("music_data.bin", b"")
        print(
            "conv_audio: 0 + 0 bytes written to "
            f"{asset_relpath(instruments_path)}, {asset_relpath(music_path)}"
        )

    return run_tool("conv_audio", action)


if __name__ == "__main__":
    raise SystemExit(main())
