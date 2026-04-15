#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEADLESS_BIN="/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless"

python3 "$ROOT_DIR/tools/build.py"
"$HEADLESS_BIN" --rom "$ROOT_DIR/build/pacman.rom" --frames "${1:-60}"
