#!/usr/bin/env bash
# Thin wrapper: runs main.py via uv so dependencies are always in sync.
set -euo pipefail
cd "$(dirname "$0")"
exec uv run main.py "$@"
