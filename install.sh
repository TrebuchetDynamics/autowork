#!/usr/bin/env bash
# One entry point for complete profile setup and gateway wiring.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 "$script_dir/setup_bundle.py" "$@"
