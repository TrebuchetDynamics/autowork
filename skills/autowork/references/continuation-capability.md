# Original-card continuation capability

`continuation_capability.py` is a compatibility boundary, with no installed native
binding. Reconciliation reports `unavailable`; owner recovery retains that exact
blocker for continuation-held cards and does not replace their dispatch. This
report does not prevent already-authorized verification or integration of completed
work. It is not a probe that launches a worker.

The installed Hermes source inspected at revision `6a2662a4aa` exposes an initial
`--goal-max-turns` in `hermes_cli/kanban_parser.py`. Its `unblock` parser and
`hermes_cli/kanban.py::_cmd_unblock` take no remaining cap or original-session
selector. `hermes_cli/kanban_db.py::unblock_task` handles blocked/scheduled cards;
`edit_task` changes descriptive/recovery fields, not a cumulative allocation or a
done-to-implementation transition. These read-only observations do not establish
complete original accounting or a safe continuation operation. No upstream source
was changed. New runtime support needs explicit integration and qualification.

## Explicit native adapter contract

A trusted host integration may call `assess(identity, runtime,
original_allocation=allocation, rework=False)` for a fresh report, or `resume` with
the same arguments for **one** atomic native call. Neither accepts executable
commands, imports, callback paths or capability declarations from worker metadata.
There is no CLI flag that enables a fictional native implementation.

The caller supplies the preserved original allocation `{amount: integer, unit:
actual_runtime_unit}` and exact board, card, profile, original session, allocation
and expected claim identity. A later invocation cannot supply a larger allocation;
the runtime must retain its immutable original record as well. Counts of assistant
messages cannot be converted into goal iterations. This version supports exact
nonnegative integer accounting; other accounting types require a separately
validated native binding.

The runtime object provides these three operations:

- `capabilities()` returns version `1` with true `accounting`, `atomic_continue`,
  `cumulative_cap`, `compare_and_swap`, `idempotent`, `same_session` and
  `retry_rework_cap`. Explicit rework also requires `completed_rework`. These are
  guarantees of trusted integration code, not authentication by a Boolean field.
- `read_accounting(identity)` returns authoritative `identity`, nonempty `revision`,
  `status`, `claim_active`, immutable original `allocation`, `complete`,
  `unknown_charges`, ordered complete `attempt_ids`, and matching `attempts`.
  Each attempt has an ID, original session ID, exact allocation unit and consumed
  count. Completeness must include interrupted/retried/review work and outstanding
  charges. The adapter refuses incomplete, mixed-unit, changed-identity, active or
  exhausted observations. It cannot authenticate a fabricated accounting provider.
- `continue_atomic(request)` atomically compares the **entire** `expected` snapshot
  (identity, claim activity, status, revision, original allocation and history),
  enforces `remaining_cap` in `unit`, and continues the original card/session.
  `operation` is `continue` or explicit `rework`; `request_id` is deterministic for
  the expected state and operation. Native enforcement must persist across every
  retry, interruption and review-rework attempt, preserve original history and
  deduplicate repeated requests. It must reject changed claims/accounting. The
  helper's subtraction is validation, never the enforcement mechanism.

An accepted native receipt must echo the request ID, exact identity, unit and cap.
A native refusal stays refused. A timeout or malformed receipt is `unverified`,
requires fresh native readback and never retries automatically. `accepted` reports
native admission only, not completed implementation, review, integration or live
qualification. The adapter stores no replenishable local budget.

The stateful native double in `test_continuation_capability.py` exercises the
supported contract and missing-control refusals, including interruption after a
native commit and changed claims at the atomic boundary. These are offline
contract tests. The external prerequisite remains a supported installed runtime
operation plus authoritative original task accounting; neither passing fixtures
nor an experimental budget-controller receipt supplies it.
