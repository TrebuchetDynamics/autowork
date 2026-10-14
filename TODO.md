# Work queue

[Completed tasks](TODO.archive.md)


Central queue for Hermes Toolset. Scope and current architecture: [project contract](docs/project.md).
No task below is implemented by this documentation pass. [goals.json](goals.json)
indexes the open work below; historical completion notes remain in their existing
owners. Ledger eligibility is not worker admission or live qualification.

TOOLSET-002's reviewed first-index initialization is integrated locally;
TOOLSET-003 remains the isolated live-recovery qualification. TOOLSET-001 and
TOOLSET-002 completion evidence is in [the archive](TODO.archive.md).
Fast-startup plan: TOOLSET-012 implements the composed default preflight; TOOLSET-013
qualifies measured startup after it. Existing queue priorities and ownership are
preserved. TOOLSET-008 remains an owner policy question.

## Next

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

- [ ] TOOLSET-011 — Qualify the updated reporting workflow on the affected profile
  - Status: open; target environment unavailable in this checkout.
  - Goal: CRON-REPORTING — Verify setup confirmation and scheduled delivery separately.
  - Sources: [reporting contract](skills/cron-autowork/SKILL.md),
    [verification boundaries](docs/workflows.md), TOOLSET-010 archived source delivery.
  - Evidence: The user-referenced profile/job was absent from this machine's local
    profile job stores during source diagnosis; no live confirmation or cron run was verified.
  - Scope: On the original configured host, install the updated bundle through its
    supported path, identify the existing job and inspect execution/output/delivery evidence.
    Reconcile the requested Telegram route and capture setup and next scheduled-report receipts.
  - Exclusions: No duplicate job, implicit resume, immediate development run, budget reset,
    push, deployment, USB formatting or changes to real PCs. Preserve existing task scope.
  - Acceptance: A setup request from another surface confirms once in the intended
    profile's Telegram chat/topic; a scheduled occurrence has separately attributable
    execution and Telegram delivery evidence. Failed/queued delivery is reported honestly.
  - Checks: Installed skill/source readback, saved job route/state comparison and actual
    message receipt; scheduled result/readback. These live checks have not been executed.
  - Dependencies: TOOLSET-010.
  - Environment prerequisite: Access to the original host with the affected profile/job
    and its authorized Telegram transport; do not substitute another profile.
  - Ownership: Next coordinator with access to that environment; no active claim.

### TOOLSET-012 — Start ready tasks through one composed default preflight

- [ ] TOOLSET-012 — Start ready tasks through one composed default preflight
- Status: open; composed preflight candidate implemented; independent review/integration pending.
- Goal: STARTUP — Reach useful implementation sooner with less preparation and chat.
- Sources: [accepted startup plan](docs/project.md#faster-ready-task-startup),
  [coordinator](skills/autowork/scripts/owner_cycle.py),
  [real admission](skills/autowork/scripts/start_goal.py),
  [source capture](skills/autowork/scripts/source_freshness.py),
  [existing ready-path policy](skills/autowork/SKILL.md),
  [engineering adapter](skills/engineering/SKILL.md),
  [protocol router](skills/engineering/scripts/route.py).
- Evidence: Current manual handoff requires source capture, contract composition,
  separate validate-only and real dispatch; real dispatch validates the same
  contract and freshness. At capture (`f617808`) the engineering router required a
  phase and prepended its bundle. Exact single-protocol selection and optional
  routing are now implemented, with independent review approval and passing vendor,
  workflow-cycle and offline-suite checks. The composed candidate now derives
  source/contract/base and invokes one real admission from owner_cycle.py;
  independent exact-candidate review and integration still gate TOOLSET-012 closure.
- Scope: Compose a supported default ready-task entry point; reconcile prior work,
  select/read the accepted body, capture bounded authoritative sources, generate
  the complete contract, invoke real native admission and persist bookkeeping
  within one normal-path command. Update affected native/portable guidance and tests.
  Generate a short task-specific worker execution contract; load the routing
  reference only for a concrete need. Extend engineering selection to exactly one
  named protocol without an automatic bundle; retain phase bundles as optional
  compatible requests. Keep workflow authority in Autowork and engineering
  protocols as technique-specific guidance. Routine status is compact; details
  go to private receipts. Reuse the engineering router, adapter, shared cycle and
  existing routing/workflow tests; preserve the upstream protocol snapshot.
- Exclusions: No speculative source-cache acceptance, skipped ownership/freshness
  checks, weaker review, arbitrary worker takeover, new scheduler/parallelism,
  upstream Hermes edits, model/provider changes, push/deployment or live job edits.
- Acceptance: A complete, dependency-ready fixture follows one composed preflight
  and one real handoff without invoking separate validate-only, planning, docs audit,
  a full suite or optional skill loader before dispatch. Required contract fields,
  source/authority/immutable-base/ownership guards remain. Stale, held, incomplete,
  interrupted and already-owned cases preserve refusal, original card and budgets;
  failures are visible and fallback performs only the missing preparation.
  Worker contracts preserve objective/scope, acceptance/checks, original admission,
  ownership/source identity, budgets and stop conditions without unconditional
  injection of routing references. Single-protocol selection returns exactly the
  requested protocol; unknown names or changed vendored protocols/references fail
  integrity checks. Optional phase calls remain compatible. Engineering guidance
  cannot dispatch, commit, widen permission or replace Autowork's mandatory tests,
  independent review, active-writer protections or integrity checks.
- Checks: Add focused composition and command-count regressions to existing owner
  cycle/goal-handoff/response-tail suites; run from skills/autowork/scripts
  `python3 -m unittest test_owner_cycle test_goal_handoff test_source_freshness test_response_tail`;
  at repository root extend and run
  `python3 -m unittest discover -s tests -p test_engineering_vendor.py` and
  `python3 -m unittest discover -s tests -p test_workflow_cycle.py` for exact-one
  selection, optional phase compatibility, tamper refusal and authority boundaries;
  run `uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py`
  on the finished candidate, plus affected links and `git diff --check`.
  Composed-preflight regressions now cover dispatch count, real isolated Git
  admission with native calls mocked, refusal/reuse and compact status. Retain
  the exact executed candidate/check receipts at review; fixtures do not close TOOLSET-013.
- Dependencies: None.
- Ownership: Next authorized Autowork coordinator; no new claim or dispatch.
- Decision: Default fast ready path, not opt-in; preserve real admission validation
  while removing the duplicate coordinator invocation. Native timing belongs to TOOLSET-013.

### TOOLSET-013 — Measure time to useful worker action and qualify the faster startup

- [ ] TOOLSET-013 — Measure time to useful worker action and qualify the faster startup
- Status: open; accepted successor, not started.
- Goal: STARTUP — Verify lower preparation overhead without weakening startup safety.
- Sources: [accepted startup plan](docs/project.md#faster-ready-task-startup),
  TOOLSET-012, [native admission](skills/autowork/scripts/start_goal.py),
  [reporting boundaries](skills/autowork/references/dispatch-and-reporting.md).
- Scope: Compare manual and composed startup using the same bounded disposable
  accepted task, source/model/environment and cold/warm conditions. Record request,
  handoff, queue, admission and first useful action times, tool/model round trips,
  routine user-visible messages and refusal outcomes in private source-bound receipts.
  Keep native runtime observations distinct from offline composition tests.
- Exclusions: No production repositories/messaging, invented benchmark values,
  arbitrary absolute latency promise, minimum-version claim, budget reset,
  protection bypass, push/deployment or live schedule/profile changes.
- Acceptance: Offline comparison demonstrates fewer coordinator preparation round
  trips and routine messages. Actual isolated native observations identify the
  first scoped test/reproduction or implementation action after the original guard,
  not a heartbeat or queued card; comparable timings show no startup regression.
  Stale/ownership/dependency refusals remain. Report contradictory timings and
  unqualified environments honestly; a fixture-only pass cannot close live qualification.
- Checks: Execute TOOLSET-012's composed entry point and its preserved manual
  baseline in disposable consumers; retain exact argv, source/test/dependency hashes,
  interpreter/model, enforced limits, timestamps and native run/admission history.
  The measurement harness/commands must be bound to the implementation at execution;
  they do not exist as executed evidence in this planning pass.
- Dependencies: TOOLSET-012.
- Environment prerequisite: Configured isolated native/model environment with
  externally enforced spending and descendant limits; unknown usage is not zero.
- Ownership: Next authorized coordinator with that environment; no active claim.

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
| PORTABLE: Align portable workflow discovery | met | executed <code>Integration af8e567: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests -p test_portable_package.py; node --test tests/portable_pi.test.mjs; uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py; exact 5e5d043 independent review and isolated Codex 0.162.1/Pi 1.2.0 discovery verified</code> → pass | — |
| BACKLOG: Provide repeatable first-time backlog initialization | met | executed <code>Reviewed 7f07b182; integrated 73a8efc: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (247/437/135/8 offline tests; 2 skipped; native/model excluded)</code> → pass | — |
| RECOVERY: Qualify bounded automatic planning recovery | unverified | — | TOOLSET-003 |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | met | executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass | — |
| CONTINUATION: Resolve and align continuation authority | unmet | — | TOOLSET-008 |
| CRON-REPORTING: Make Telegram scheduling reports reliable across invocation surfaces | partial | executed <code>Offline source guidance: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests (246 run, 2 skipped; no live delivery qualification)</code> → pass | TOOLSET-011 |
| STARTUP: Start useful implementation sooner with less preparation | unmet | — | TOOLSET-012, TOOLSET-013 |

<!-- goals:coverage:end -->
