# Fleet recovery — 2026-10-24

## Authorized scope

The owner requested recovery of idle/stalled repository runners. Restore actual
eligible progress, not artificial busywork: preserve unfinished candidates,
paused development jobs, existing publication policy and explicit live/owner
gates. A service restart is not evidence of task progress. This work does not
activate the isolated Pi RPC implementation.

## Observer overlap defect

`Src/pi_autowork/cli.py::hermes_jobs` currently treats every enabled repository
cron job mentioning `autowork` as a competing writer. A read-only hourly progress
monitor therefore prevents runner startup with exit 4, despite its explicit
prohibition on edits, dispatch, claims and service actions. Disabled/paused
development jobs are already correctly excluded.

Repair this narrowly and fail closed. A verified observer may be explicitly
identified for one repository without ignoring other jobs. Bind any exemption
to the exact job identity and execution contract; changed, unknown or writer
jobs must still block. Do not infer safety merely from a name or the phrase
`read-only`, and do not enable the blanket `ALLOW_HERMES` override. Keep the
configuration local/private and public examples generic. This classifies an
accepted job contract; it is not a sandbox or proof that a historical invocation
complied.

Acceptance requires offline observer/writer/unknown/changed-contract fixtures,
consistent install/start/restart policy, documentation and independent review.
Runtime activation additionally requires the supported toolset update path and
fresh writer-custody checks. Preserve existing interrupted attempts and the
independent interactive session; do not clear its claim or kill it to start a
competing writer. Installation/readiness and actual dispatch must be reported
separately.
