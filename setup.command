#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET=${1:-"$(pwd)"}
exec python3 "$ROOT/scripts/install.py" "$TARGET"
