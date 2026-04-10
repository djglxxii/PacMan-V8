#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import sys
from typing import Callable


TOOLS_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
SOURCE_ROM_DIR = REPO_ROOT.parent / "source_rom"
ASSETS_DIR = REPO_ROOT / "assets"


def require_input(relative_path: str) -> bytes:
    path = SOURCE_ROM_DIR / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"required input not found: {path}")
    return path.read_bytes()


def write_output(relative_path: str, data: bytes) -> pathlib.Path:
    path = ASSETS_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def asset_relpath(path: pathlib.Path) -> pathlib.Path:
    return path.relative_to(REPO_ROOT)


def run_tool(tool_name: str, action: Callable[[], None]) -> int:
    try:
        action()
    except Exception as error:  # pragma: no cover - command wrapper path
        print(f"{tool_name} error: {error}", file=sys.stderr)
        return 1
    return 0
