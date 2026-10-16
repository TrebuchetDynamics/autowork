# Pi Autowork component

Pi-specific parts of the `pi-autowork` runner. `scripts/pi-autowork.sh` remains the
entry point and service command; the generic task lifecycle (admission, slots,
integration, closure) stays in the shared engine under `skills/autowork/scripts`,
which is the only authority for task state. Runtime state lives outside the
repository, under `${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`.

| Module | Role |
| --- | --- |
| `pi_autowork/pi_runtime.py` | Runs one Pi job: model choice and fallback, bounded retries, timeouts, budget, redacted `runs.jsonl` records (a straight port of the runner's Bash; the formal worker-runtime boundary is TOOLSET-117-cb) |
| `pi_autowork/health.py` | Per-runner `status.json`, one stall announcement per episode with its root blockers, and the `--fleet` view |
| `pi_autowork/touches_inference.py` | Finds tasks without Touches, records proposed lists, and widens a list the runner inferred (`scripts/pi_autowork_touches.py` remains as a compatibility entry point) |
| `pi_autowork/workspaces.py` | Links `PI_AUTOWORK_LINK_PATHS` gitignored dependencies into task and review worktrees |
| `pi_autowork/release.py` | Safe-checkpoint test before a self-update: fleet idle, and the new release reads current state |

Design: [coordinator redesign](../docs/plans/2026-10-16-pi-autowork-coordinator.md),
[component layout](../docs/plans/pi-autowork-component-layout.md). Tests run from
`python3 scripts/check.py` (`pi-autowork/tests`).
