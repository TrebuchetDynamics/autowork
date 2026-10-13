# Work queue

Central queue for Hermes Toolset. Scope and current architecture: [project contract](docs/project.md).
No task below is implemented by this documentation pass. There is no goals.json
execution index yet; native ledger admission must not be inferred from this queue.

## Now

### TOOLSET-001 — Align portable skill discovery with the current public workflows

- Status: open
- Goal: Consistent primary workflow names across Hermes, Codex and Pi.
- Sources: [public workflow mapping](docs/workflows.md), [portable adapters](adapters/skills/COMMON.md), [Pi registration](adapters/pi.mjs).
- Evidence: Hermes folds Grill Me into Plan With Me and publishes Plan For Me;
  the portable package still discovers separate Grill Me and Autoresearch skills.
- Scope: Align portable public discovery and challenge/research routing; update
  host-specific examples and registration tests. Preserve non-planning protocols
  and supported compatibility invocations.
- Exclusions: No Hermes Agent edits, permission changes or removal of user skills.
- Acceptance: Canonical skills are discoverable on each host; challenge mode and
  every research protocol resolve to valid instructions without recursive routing.
  Package references remain valid after installation.
- Checks: `python3 -m unittest discover -s tests -p test_portable_package.py`;
  `node --test tests/portable_pi.test.mjs`; native installation/discovery in temporary homes.
- Dependencies: None.
- Owner: Next authorized Autowork coordinator; no active claim recorded here.

## Next

### TOOLSET-002 — Provide a supported first-time task-index initialization path

- Status: open
- Goal: Let Docs Sync bootstrap a native-consumable backlog without manual JSON edits.
- Sources: [goals helper](skills/repo-docs/scripts/goals.py), [document scaffold](skills/repo-docs/references/document-scaffold.md), [project contract](docs/project.md).
- Evidence: The CLI documents command-only ledger mutation but exposes no init or
  add-goal command. This repository currently has TODO.md and no goals.json.
- Scope: Establish and document a supported bootstrap operation; preserve full task
  bodies and existing IDs, then validate/render a machine index for this queue.
- Exclusions: No invented accepted plans, completion evidence or overwrite of an
  existing ledger; do not launch workers as part of document initialization.
- Acceptance: Empty-repository bootstrap and an existing TODO-only repository have
  reproducible coverage; repeated initialization preserves bytes; existing/conflicting
  state is preserved; generated task/body links pass consumer checks.
- Checks: Extend goals-helper fixture tests; run `python3 scripts/check.py` and the
  supported validator/render idempotency checks on the generated queue.
- Dependencies: None.
- Owner: Next authorized Autowork coordinator; no active claim recorded here.

### TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow

- Status: open
- Goal: Prove that recovery reaches execution instead of stopping at a planning receipt.
- Sources: [recovery contract](skills/autowork/references/backlog-planning.md),
  [planning tests](skills/autowork/scripts/test_backlog_plan.py), [verification limits](docs/testing.md).
- Evidence: Offline tests cover preparation routing and receipt reuse; they do not
  prove a model calls Plan For Me, updates tasks and starts the supported worker.
- Scope: Use a disposable repository and an isolated configured test environment.
  Reproduce missing prerequisites and candidate drift; capture the actual planning,
  TODO update and handoff sequence, or record the specific failing transition.
- Exclusions: No production messaging, deployment, real user repositories, forbidden
  prerequisite commits, concurrent-writer takeover or manufactured completion.
- Acceptance: The workflow invokes planning without another user command, preserves
  no-commit exclusions, retries an eligible in-scope slice, and reports execution
  separately from planning. Unchanged inputs reuse the saved recovery decision.
- Checks: Offline regression suite plus an explicitly recorded model/native smoke
  run; exact task, checks, commit or none, and remaining blocker in its receipt.
- Dependencies: None; requires a configured isolated model/native environment.
- Owner: Next authorized Autowork coordinator; no active claim recorded here.

## Needs decision

None currently identified for the bounded tasks above. Unavailable live test access
must be reported when encountered; it is not evidence that a product task is done.

## Completed local changes

### TOOLSET-004 — Reduce fragmented Autowork handoffs and misleading zero-progress reports

- Status: done (local implementation and focused contract tests; not a live throughput claim).
- Goal: Complete connected accepted outcomes with fewer redundant preparation/review cycles.
- Sources: [delivery batch contract](skills/autowork/references/delivery-batches.md),
  [worker body generation](skills/autowork/scripts/start_goal.py), [cron prompts](scripts/wire-owner-cron.py).
- Scope delivered: Coherent-batch guidance, worker/cron prompt propagation, portable
  coordinator guidance and delivery-first reporting with truthful parent status.
- Acceptance checked: Generated worker text retains the explicit scope/exclusions,
  directs completion of every admitted consumer, and retains independent review;
  generated cron text includes batching, evidence reuse limits and parent reporting.
- Checks: Worker role contracts (5 tests) and cron prompt tests (15 tests) passed.
- Remaining qualification: Real model batching and reduced elapsed time are unverified;
  TOOLSET-003 still owns live bounded recovery qualification.
- Dependencies: None.
- Owner: Current repository change; no claim on any product worker or schedule.

### TOOLSET-005 — Recover registration context across filtered terminal environments

- Status: done (local helper regression; live worker recovery not yet verified).
- Goal: Prevent a missing terminal environment field from holding a correctly registered task.
- Source: [workspace guard](skills/autowork/scripts/pass_workspace.py).
- Scope delivered: Exact original-handoff recovery for registration only; no environment
  forgery, registry mutation, candidate repinning or native ownership bypass.
- Checks: 22 workspace tests pass, including missing, stale, wrong-task, wrong-card
  and conflicting handoffs plus conflicting inherited context.
- Remaining qualification: Existing workers retain their original admitted contracts;
  they need same-card reconciliation before using a changed helper.

### TOOLSET-006 — Preserve review progress and direct coordinator closeout

- Status: done (local regression coverage; autonomous model follow-through unverified).
- Goal: Keep new review outcomes visible and direct completed cards to integration checks.
- Source: [reconciliation helper](skills/autowork/scripts/reconcile.py).
- Scope delivered: Report-cache identity includes run and outcome; phase-specific next
  actions distinguish active/queued cards, recovery and terminal closeout.
- Checks: 12 reconciliation tests pass; terminal hints never claim delivery or approval.
- Remaining qualification: A model must execute the advised closeout; the read-only
  helper itself does not merge, dispatch, authenticate liveness or resume jobs.

### TOOLSET-007 — Resume execution and reuse checks across calls

- Status: implemented; offline validation recorded in the current change.
- Scope: Saved reconciliation projection produces continuation/change fields;
  pending closeout precedes discovery. Run-or-reuse preserves stale receipts and
  reuses passing checks under their original input contract. Terminal display
  IDs are removed from execution and fingerprints; task/security inputs stay bound.
- Checks: Regression coverage for continuation, actual filtered subprocess
  environment, relevant environment changes, first execution, reuse and stale refusal.
- Limits: No automated Git integration or model throughput claim; arbitrary
  source files and live ownership still require fresh checks before action.
