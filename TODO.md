# Work queue

[Completed tasks](TODO.archive.md)


Central queue for Hermes Toolset. Scope and current architecture: [project contract](docs/project.md).
No task below is implemented by this documentation pass. [goals.json](goals.json)
indexes the open work below; historical completion notes remain in their existing
owners. Ledger eligibility is not worker admission or live qualification.

TOOLSET-002's reviewed first-index initialization is integrated locally;
TOOLSET-003 remains the isolated live-recovery qualification. TOOLSET-001 and
TOOLSET-002 completion evidence is in [the archive](TODO.archive.md).
Fast-startup plan: TOOLSET-012 is reviewed and integrated locally; TOOLSET-013
retains the measured native startup qualification. TOOLSET-003/011 need their named environments; TOOLSET-008 needs
the existing policy answer. Preserve this queue's order and ownership.

Execution notes: Each task states the remaining action, acceptance, checks and stop
conditions. Read linked detail only for a concrete gap; do not re-plan settled work
or redo verified partial delivery. Reuse check evidence only while source, tests,
dependencies and environment match. Required tests, review, ownership protections,
integrity checks and live qualification remain mandatory. Editing this queue does
not change a running worker's assigned contract or authorize dispatch/scheduling.

## Next

### TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow

- [ ] TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow
- Status: open; live qualification not run.
- Goal: RECOVERY — Prove recovery reaches execution, not just a planning receipt.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [recovery contract](skills/autowork/references/backlog-planning.md), [existing regressions](skills/autowork/scripts/test_backlog_plan.py), [verification limits](docs/testing.md).
- Scope: In a disposable repository, reproduce missing prerequisites and candidate drift. Observe automatic planning, TODO update and retry of the eligible original slice; repeat unchanged inputs once to verify decision reuse.
- Acceptance: No extra user planner command; original exclusions and ownership survive; execution is reported separately from planning.
- Checks: Run focused recovery regressions and one bounded isolated model/native smoke journey covering both cases. Retain exact source, task, commands/results, commit or none, and remaining blocker. Offline tests alone cannot close this task.
- Exclusions: No production messages/deployment, real user repositories, forbidden prerequisite commits, writer takeover or fabricated completion.
- Dependencies: None.
- Environment prerequisite: Configured isolated model/native environment.
- Ownership: Next authorized coordinator; no active claim recorded.
- Next action: Establish that environment, then execute the bounded recovery journey.

- [ ] TOOLSET-011 — Qualify the updated reporting workflow on the affected profile
- Status: open; original target environment unavailable.
- Goal: CRON-REPORTING — Verify setup confirmation and scheduled Telegram delivery separately.
- Sources: [reporting contract](skills/cron-autowork/SKILL.md), [verification boundaries](docs/workflows.md), archived TOOLSET-010 source delivery.
- Scope: On the original host/profile, install the updated bundle through its supported path. Identify the existing job, preserve its state/scope, verify its requested Telegram route, then inspect the next scheduled result.
- Acceptance: A setup request from another surface confirms once in the intended chat/topic; a scheduled occurrence has attributable execution and Telegram message receipts. Report failed, queued or unverified delivery honestly.
- Checks: Read back installed source and saved route/state; verify the actual setup message and scheduled result/delivery. These live checks are not run.
- Exclusions: No duplicate job, implicit resume, immediate development run, budget reset, push/deployment, USB formatting or real-PC changes. Never substitute another profile.
- Dependencies: TOOLSET-010.
- Environment prerequisite: Original host, affected profile/job and authorized Telegram transport.
- Ownership: Coordinator with that access; no active claim.
- Next action: Obtain the original environment; do not create a replacement job.

### TOOLSET-012 — Start ready tasks through one composed default preflight

### TOOLSET-013 — Measure time to useful worker action and qualify the faster startup

- [ ] TOOLSET-013 — Measure time to useful worker action and qualify the faster startup
- Status: open; TOOLSET-012 is integrated; isolated bounded environment still required.
- Goal: STARTUP — Verify lower preparation overhead without weaker startup safety.
- Sources: [accepted measurement contract](docs/project.md#faster-ready-task-startup), TOOLSET-012, [admission](skills/autowork/scripts/start_goal.py), [reporting boundaries](skills/autowork/references/dispatch-and-reporting.md).
- Scope: Compare manual and composed startup on the same disposable accepted task, source, model/environment and cold/warm conditions. Separate request-to-handoff, queue wait, admission and first useful test/reproduction/edit after the guard. Count coordinator tool/model round trips and routine messages.
- Acceptance: Fewer preparation round trips/messages with no observed comparable startup regression; preserve stale/ownership/dependency refusals. A heartbeat/queued card is not useful action; offline fixtures cannot close native qualification. Investigate contradictory timing.
- Checks: Run both routes with source-bound implementation commands; retain exact argv, dependency/interpreter/model identity, enforced limits, timestamps, native admission/run evidence and failures. Harness/baseline runs are not yet executed.
- Exclusions: No production repositories/messages, fabricated measurements, absolute latency/minimum-version promises, budget reset, protection bypass, push/deployment or live schedule/profile edits.
- Dependencies: TOOLSET-012.
- Environment prerequisite: Isolated configured native/model environment with external spending/descendant limits; unknown usage is not zero.
- Ownership: Authorized coordinator with that environment; no active claim.
- Next action: After TOOLSET-012, execute the paired bounded comparison and report actual results.

### TOOLSET-014 — Archive completed task headings with their checkbox bodies

- [ ] TOOLSET-014 — Archive completed task headings with their checkbox bodies
- Status: open; reproduced offline, not fixed.
- Goal: ARCHIVAL — Keep complete closed units in history without empty live task headings.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [archive implementation](skills/docs-sync/scripts/todo_archive.py), [archive regressions](skills/docs-sync/scripts/test_todo_archive.py), [archive contract](skills/docs-sync/references/todo-archive.md).
- Scope: Correct matching heading-plus-checkbox archival boundaries; add CLI regression coverage and reconcile the existing empty TOOLSET-012 heading only against exact archived completion evidence. Preserve open tasks, ambiguous/conflicting units, nested evidence, CRLF and lossless history.
- Current evidence: prepare() on a ledger-done T1 with matching heading and closed checkbox moves the checkbox body but retains the empty T1 heading and reports T1 retained. Canonical TOOLSET-012 exhibits that residue.
- Decision: Fix the complete unit boundary, not a blanket heading cleanup; agent maintenance decision under broad repository authority, not a new user priority.
- Acceptance: A matching completed heading and checkbox archive together exactly once; open/conflicting/ambiguous bodies remain unchanged; second archive/render is byte-stable. Existing history is not rewritten and no live acceptance is claimed.
- Checks: Run test_todo_archive, test_archive_policy, test_render_safety and test_backlog_recovery from skills/docs-sync/scripts, then the safe offline scripts/check.py inventory with the documented Python 3.12 dependencies; validate ledger, links and diff. Required native review remains separate.
- Exclusions: No jobs/profile edits, native/model smoke, remote publication, upstream edits, history rewriting or completion inference from an empty heading.
- Dependencies: None.
- Ownership: Next authorized isolated worker; canonical integration stays coordinator-owned.
- Next action: Reproduce the failing full-unit CLI case, repair boundaries, verify and request review on the same bounded card.

## Needs decision

### TOOLSET-008 — Make Autowork continuation authority consistent

- [ ] TOOLSET-008 — Make Autowork continuation authority consistent
- Status: needs decision; preserve the existing policy gate.
- Priority: High; ordering unchanged.
- Goal: CONTINUATION — Closeout must not silently authorize another batch.
- Sources: [cycle](skills/shared/ENGINEERING-CYCLE.md), [Autowork](skills/autowork/SKILL.md), [scheduled policy](skills/autowork/references/scheduled-policy.md), [portable contract](adapters/skills/autowork/SKILL.md), [regressions](tests/test_workflow_cycle.py).
- Scope: After the policy answer, align interactive/native/portable/scheduled wording and existing tests. Keep current-batch closeout separate from new-batch admission.
- Decision pending: Does recurrence itself allow multiple batches, or must the saved prompt explicitly permit continuation? Recommendation: one batch unless explicitly permitted. No universal policy answer is recorded.
- Acceptance: Default interactive stops after one batch; explicit one-task wins; explicit multi-batch/whole-spec stays within scope/budget/ownership/review. Scheduled behavior follows the resolved answer. Pending review or exhausted budget cannot create new authority.
- Checks: Cover default interactive, explicit one-task, explicit continuation, recurring default, and exhausted budget/pending review. Run `python3 -m unittest discover -s tests -p test_workflow_cycle.py`, affected links and `git diff --check`. New policy checks are not executed; fixtures do not prove agent behavior.
- Exclusions: No live job/scheduler edits, dispatch, new runtime gates, permission expansion, budget reset or implementation in this planning pass.
- Dependencies: None.
- Coordination: Independent of TOOLSET-009.
- Ownership: User for the unresolved policy; next authorized implementer afterward.
- Next action: Record that answer before implementing the scheduled case.

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
| ARCHIVAL: Integrate archival and reconcile the rendering contract | partial | executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass | TOOLSET-014 |
| CONTINUATION: Resolve and align continuation authority | unmet | — | TOOLSET-008 |
| CRON-REPORTING: Make Telegram scheduling reports reliable across invocation surfaces | partial | executed <code>Offline source guidance: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests (246 run, 2 skipped; no live delivery qualification)</code> → pass | TOOLSET-011 |
| STARTUP: Start useful implementation sooner with less preparation | unmet | executed <code>Reviewed fef4241; integration e2a0838: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (252/448/135/8 offline tests; 2 skipped; 8 live/integration modules excluded); native timing remains TOOLSET-013</code> → pass | TOOLSET-013 |

<!-- goals:coverage:end -->
