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
- Sources: [goals helper](skills/docs-sync/scripts/goals.py), [document scaffold](skills/docs-sync/references/document-scaffold.md), [project contract](docs/project.md).
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

### TOOLSET-009 — Account for archival in the shared rendering contract

- Status: open; planned, not implemented.
- Priority: Medium; independent of TOOLSET-008.
- Goal: Agents review and deliver every artifact changed by a render operation.
- Sources: [engineering cycle](skills/shared/ENGINEERING-CYCLE.md),
  [renderer](skills/docs-sync/scripts/goals.py),
  [archive contract](skills/docs-sync/references/todo-archive.md).
- Evidence: ENGINEERING-CYCLE.md says rendering changes only the goal table;
  the separate local archival changes make goals.py render delegate to
  archive_tasks with coverage rendering enabled and move completed bodies into
  the established archive. Those changes and test_todo_archive.py remain outside
  this delivery. The user's planning
  request adopts the audit finding and asks to document and inspect that effect.
- Scope: Correct the shared cycle's render description and closeout sequence.
  Require readback/diff review of TODO.md and the actual archive selected by the
  helper; include attributable archive changes in the handoff and any separately
  authorized commit. Reuse the existing archive contract and regression coverage.
- Exclusions: No renderer behavior change, archive rename, mass task migration,
  unrelated contract rewrite, implementation during planning, or implied commit.
- Acceptance: The contract states both coverage rendering and automatic archival;
  it requires post-render verification of preserved open bodies, complete archived
  bodies, valid links and byte stability on an unchanged second pass. When an
  existing archive has a custom path, verification uses that path. No claim that
  instruction tests prove model adherence or live completion.
- Checks: From skills/docs-sync/scripts, run
  `python3 -m unittest test_todo_archive`; check changed Markdown links and
  `git diff --check`. Review the final wording against render/archive_tasks.
  These are planned implementation checks, not new passing evidence.
- Dependencies: Separate integration of the local archival implementation and
  skills/docs-sync/scripts/test_todo_archive.py; verify their presence before
  applying the contract change. No dependency on TOOLSET-008.
- Owner: Next authorized implementer; no active claim or implementation authority
  is created by this planning pass.
- Next action: Make the bounded contract correction after implementation is authorized.

## Needs decision

### TOOLSET-008 — Make Autowork continuation authority consistent

- Status: needs decision; planned, not implemented.
- Priority: High.
- Goal: Closing an authorized batch cannot silently authorize starting another.
- Sources: [engineering cycle](skills/shared/ENGINEERING-CYCLE.md),
  [Autowork contract](skills/autowork/SKILL.md),
  [scheduled policy](skills/autowork/references/scheduled-policy.md),
  [portable Autowork](adapters/skills/autowork/SKILL.md),
  [workflow checks](tests/test_workflow_cycle.py).
- Evidence: The cycle's introduction limits default Autowork to one slice, while
  its final step tells an active invocation/job to hand off the next batch. The
  user's planning request adopts the correction: separate closeout from new work
  and require standing continuation authority for another batch.
- Scope: Align the cycle's introduction and final step with the accepted stopping
  rule; reconcile directly affected native/portable and scheduled instructions.
  Keep closeout of the current batch distinct from admission of a new batch.
- Decision pending: Does recurrence itself authorize multiple batches within an
  occurrence, or must the saved job prompt explicitly grant that authority?
  Recommendation: one batch unless the prompt explicitly authorizes continuation.
  No answer or acceptance of that recommendation has been recorded.
- Exclusions: No live job edits, scheduler changes, worker dispatch, new runtime
  gates, permission expansion, budget reset, or implementation during planning.
- Acceptance: A default interactive invocation stops after its one batch; required
  closeout can finish without admitting another. An explicit one-task restriction
  always wins. An explicit multi-batch/whole-spec mandate can continue within its
  existing scope, budget, ownership and review gates. Scheduled runs follow the
  user's resolved policy consistently across the affected instructions.
- Checks: Review a scenario table covering default interactive, explicit one-task,
  explicit continuation, recurring default, and exhausted budget/pending review.
  Extend the relevant contract checks where useful; run
  `python3 -m unittest discover -s tests -p test_workflow_cycle.py`, check affected
  links and `git diff --check`. New scenarios and checks have not yet been executed;
  offline policy checks do not prove agent behavior.
- Dependencies: Resolve the scheduled-run question; no dependency on TOOLSET-009.
- Owner: User for the open policy choice; next authorized implementer for the fix.
- Next action: Record the answer and finalize this task's scheduled acceptance case.

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
