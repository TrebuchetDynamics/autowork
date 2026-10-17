#!/usr/bin/env bash
# One entry point: install autowork, tx, the Hermes plugin, Claude Code, Codex and Pi
# from a checkbox menu (scripts/install_menu.py). See: install.sh --help
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 "$script_dir/scripts/install_menu.py" "$@"
