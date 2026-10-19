#!/usr/bin/env bash
# One entry point: install autowork, tx, the Hermes plugin, Claude Code, Codex and Pi
# with the full available suite and verbose output by default; --menu selects items.
# `install.sh update` runs the same items as an in-place update of what is installed.
# Live progress and terminal colors: scripts/install_menu.py. See: install.sh --help
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 "$script_dir/scripts/install_menu.py" "$@"
