#!/usr/bin/env bash
# pi-autowork.sh: run Hermes Toolset's Parallel Autowork engine with Pi workers.
#
# The engine (skills/autowork/scripts/owner_cycle.py --parallel) plans, dispatches,
# verifies and closes tasks; the pi-autowork component (pi-autowork/pi_autowork/)
# drives its coordinator loop and supplies what the engine leaves to the host: Pi
# workers with model choice and fallback, an independent verification step, budgets,
# a session branch merged into the main branch at the end, locking, graceful shutdown
# and a systemd service. This file only finds that component and runs it; the
# component then continues in the toolset release it resolves. See --help.
set -uo pipefail
SCRIPT=$(readlink -f "${BASH_SOURCE[0]}")
is_component() { [[ -f $1/pi_autowork/cli.py ]]; }
# Workers inherit the runner's component; otherwise PI_AUTOWORK_TOOLSET, this file's
# own release, then the package Pi loads (a copy of this file in a repository).
COMPONENT=${PI_AUTOWORK_COMPONENT:-}
if ! { [[ -n $COMPONENT ]] && is_component "$COMPONENT"; }; then
  COMPONENT=''
  for candidate in "${PI_AUTOWORK_TOOLSET:+$PI_AUTOWORK_TOOLSET/pi-autowork}" "$(dirname "$SCRIPT")/../pi-autowork"; do
    [[ -n $candidate ]] && is_component "$candidate" && { COMPONENT=$candidate; break; }
  done
  if [[ -z $COMPONENT ]]; then
    while IFS= read -r line; do
      line=${line#"${line%%[![:space:]]*}"}
      [[ $line == /* ]] && is_component "$line/pi-autowork" && { COMPONENT=$line/pi-autowork; break; }
    done < <("${PI_BIN:-pi}" list 2>/dev/null)
  fi
fi
if [[ -z $COMPONENT ]]; then
  printf 'pi-autowork: Hermes Toolset not found. Install it in Pi (pi install git:github.com/TrebuchetDynamics/hermes-toolset) or set PI_AUTOWORK_TOOLSET.\n' >&2
  exit 2
fi
command -v python3 >/dev/null 2>&1 || { printf 'pi-autowork: Missing required command: python3\n' >&2; exit 2; }
export PI_AUTOWORK_SCRIPT=$SCRIPT
exec python3 "$COMPONENT/pi_autowork/cli.py" "$@"
