# Work queue

[Completed tasks](TODO.archive.md)


Central queue for Hermes Toolset. Scope and current architecture: [project contract](docs/project.md).
No task below is implemented by this documentation pass. [goals.json](goals.json)
indexes the open work below; historical completion notes remain in their existing
owners. Ledger eligibility is not worker admission or live qualification.

Now: TOOLSET-001 aligns portable discovery. Next: TOOLSET-002 provides a repeatable
initialization interface, followed by TOOLSET-003's isolated live qualification.
TOOLSET-009 reconciles the rendering contract; TOOLSET-008 remains an owner policy
question. Existing order is preserved, not a new implementation mandate.

## Now

### TOOLSET-001 — Align portable skill discovery with the current public workflows

- [ ] TOOLSET-001 — Align portable skill discovery with the current public workflows
- Status: open
- Goal: PORTABLE — Consistent primary workflow names across Hermes, Codex and Pi.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [public workflow mapping](docs/workflows.md), [portable adapters](adapters/skills/COMMON.md), [Pi registration](adapters/pi.mjs).
- Evidence: Hermes folds Grill Me into Plan With Me and publishes Plan For Me;
  the portable package still discovers separate Grill Me and Autoresearch skills;
  Hermes now also registers Autoresearch separately from Plan For Me.
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
- Ownership: Next authorized Autowork coordinator; no active claim recorded here.

## Next

### TOOLSET-002 — Provide a supported first-time task-index initialization path

- [ ] TOOLSET-002 — Provide a supported first-time task-index initialization path
- Status: open
- Goal: BACKLOG — Let Docs Sync bootstrap a native-consumable backlog without manual JSON edits.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [goals helper](skills/docs-sync/scripts/goals.py), [document scaffold](skills/docs-sync/references/document-scaffold.md), [project contract](docs/project.md).
- Evidence: The CLI documents command-only ledger mutation but exposes no init or
  add-goal command. Docs Sync can seed the documented JSON schema and run fmt;
  this pass initializes this repository's index without implementing a CLI entry point.
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
- Ownership: Next authorized Autowork coordinator; no active claim recorded here.

### TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow

- [ ] TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow
- Status: open
- Goal: RECOVERY — Prove that recovery reaches execution instead of stopping at a planning receipt.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [recovery contract](skills/autowork/references/backlog-planning.md),
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
- Dependencies: None.
- Environment prerequisite: Requires a configured isolated model/native environment.
- Ownership: Next authorized Autowork coordinator; no active claim recorded here.

### TOOLSET-009 — Account for archival in the shared rendering contract

- [ ] TOOLSET-009 — Account for archival in the shared rendering contract
- Status: open; rendering description landed concurrently, acceptance review remains.
- Priority: Medium; independent of TOOLSET-008.
- Goal: ARCHIVAL — Agents review and deliver every artifact changed by a render operation.
- Sources: [engineering cycle](skills/shared/ENGINEERING-CYCLE.md),
  [renderer](skills/docs-sync/scripts/goals.py),
  [archive contract](skills/docs-sync/references/todo-archive.md),
  [archive regression tests](skills/docs-sync/scripts/test_todo_archive.py).
- Evidence: Commit `08701bd` now describes coverage rendering, automatic archival
  and readback of TODO plus the selected archive in ENGINEERING-CYCLE.md.
  The original user's planning request adopted the earlier drift finding.
  This pass does not reopen that implemented wording correction or claim that
  its complete acceptance criteria have been reviewed by the integration owner.
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
  This pass ran test_todo_archive, test_archive_policy, test_render_safety,
  test_goals and test_handoff_reconciliation: 74 tests passed. Canonical local
  links, archive-prefix preservation and unchanged second-render bytes passed.
  These checks do not establish model adherence or replace acceptance review.
- Dependencies: None; the archival implementation and regression tests are now
  included with the archive changes. No dependency on TOOLSET-008.
- Ownership: Next authorized implementer; no active claim or implementation authority
  is created by this planning pass.
- Next action: Review the landed wording against all acceptance criteria; make only
  evidenced remaining corrections, then reconcile this same task's completion.


## Needs decision

### TOOLSET-008 — Make Autowork continuation authority consistent

- [ ] TOOLSET-008 — Make Autowork continuation authority consistent
- Status: needs decision; planned, not implemented.
- Priority: High.
- Goal: CONTINUATION — Closing an authorized batch cannot silently authorize starting another.
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
- Dependencies: None.
- Decision gate: Resolve the scheduled-run question; no dependency on TOOLSET-009.
- Ownership: User for the open policy choice; next authorized implementer for the fix.
- Next action: Record the answer and finalize this task's scheduled acceptance case.

## Completed local changes

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


## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| PORTABLE: Align portable workflow discovery | unmet | — | TOOLSET-001 |
| BACKLOG: Provide repeatable first-time backlog initialization | partial | — | TOOLSET-002 |
| RECOVERY: Qualify bounded automatic planning recovery | unverified | — | TOOLSET-003 |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | partial | — | TOOLSET-009 |
| CONTINUATION: Resolve and align continuation authority | unmet | — | TOOLSET-008 |

<!-- goals:coverage:end -->
