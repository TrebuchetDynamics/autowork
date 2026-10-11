#!/usr/bin/env bash
# Copy bundled skills through the same offline provisioner used by plugin load.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 "$script_dir/install_skills.py" "$@"
