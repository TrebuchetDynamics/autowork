# Pi Autowork component

Pi-specific parts of the `pi-autowork` runner. `scripts/pi-autowork.sh` remains the
entry point and service command; the generic task lifecycle (admission, slots,
integration, closure) stays in the shared engine under `skills/autowork/scripts`,
which is the only authority for task state. Runtime state lives outside the
repository, under `${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`.

| Module | Role |
| --- | --- |
| `pi_autowork/health.py` | Per-runner `status.json`, one stall announcement per episode with its root blockers, and the `--fleet` view |

Design: [coordinator redesign](../docs/plans/2026-10-16-pi-autowork-coordinator.md),
[component layout](../docs/plans/pi-autowork-component-layout.md). Tests run from
`python3 scripts/check.py` (`pi-autowork/tests`).
