# Work queue

[Completed tasks](TODO.archive.md)


Central queue for Hermes Toolset. Scope and current architecture: [project contract](docs/project.md).
[goals.json](goals.json) indexes the remaining work below; verified completed
tasks move to the archive automatically. Ledger eligibility is not worker
admission or live qualification.

TOOLSET-002's reviewed first-index initialization is integrated locally;
TOOLSET-003 remains the isolated live-recovery qualification. TOOLSET-001 and
TOOLSET-002 completion evidence is in [the archive](TODO.archive.md).
Fast-startup plan: TOOLSET-012 is reviewed and integrated locally; TOOLSET-013
retains measured native startup qualification. TOOLSET-003/011 still need their
named environments; TOOLSET-008's reviewed continuation correction is integrated
and archived. Preserve caller limits, queue priorities and ownership.

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
- Current evidence: The shipped containment backend admits only local fixture executables and explicitly excludes provider/network dispatch. Its synthetic spending controller is not a model spending limit. No qualifying model journey was run.
- Next action: Supply an isolated model endpoint with externally enforced spend and descendant limits, then execute the bounded recovery journey; existing offline fixtures cannot replace it.

### TOOLSET-017 — Prepare and recover exact-card writer registration

- [ ] TOOLSET-017 — Prepare and recover exact-card writer registration
- Status: in_progress; shared reservation and prerequisite preparation are implemented and integrated in eb72be6; original-card native migration remains unavailable.
- Goal: RECOVERY — Make required registration compatible with immutable startup admission.
- Sources: [accepted recovery plan](docs/project.md#end-to-end-original-task-recovery), [launcher](skills/autowork/scripts/start_goal.py), [startup guard](skills/autowork/scripts/pass_workspace.py), [registration verifier](skills/autowork/scripts/writer_registration.py), [handoff](skills/autowork/references/handoff.md).
- Scope: Implement deferred initial dispatch for explicitly required registration and an attributed original-card prerequisite transition through supported controls. Preserve original evidence; keep declared coordination state separate from executable source. Include executable helper/runtime migration compatibility and exact identity/scope verification.
- Acceptance: No worker starts before required registration is verified. Old pins/refusals remain retained; recovery changes only the permitted prerequisite. Mismatched card/task/base/workspace/scope, duplicate evidence, source drift and live writers refuse. Missing native transition is reported as unavailable, never emulated by board writes or a replacement card. Actual profile recovery is checked in the original task, not claimed from fixtures.
- Checks executed: 58 registration/workspace/runtime fixtures passed. Independent review found a partial-write retry defect; its regression reproduced the failure and passed after atomic publication. Final Python 3.12 offline gate passed 318/470/139/8 tests (two skips, eight native/model modules excluded). Native same-card recovery remains unrun.
- Dependencies: None.
- Ownership: Authorized shared maintainer; original product owners/cards remain unchanged.
- Exclusions: No upstream edits, silent repinning, new product cards, budget reset, live profile writes or pause changes in the offline implementation slice.
- Next action: Use a supported native original-card prerequisite release/runtime-migration operation when available. The new reservation/preparation path deliberately retains the original guard and old evidence; it does not recover an already frozen native card. Do not recreate the card or repeat the completed offline implementation.

### TOOLSET-018 — Bind original-card continuation to supported budget enforcement

- [ ] TOOLSET-018 — Bind original-card continuation to supported budget enforcement
- Status: in_progress; offline capability/accounting contract implemented and integrated in eb72be6; native continuation still lacks supported enforcement and complete original accounting.
- Goal: RECOVERY — Preserve allocation and history across original-card continuation and review rework.
- Sources: [accepted recovery plan](docs/project.md#end-to-end-original-task-recovery), [reconciliation](skills/autowork/scripts/reconcile.py), [owner cycle](skills/autowork/scripts/owner_cycle.py), [runtime limits](skills/autowork/references/owner-cycle.md), [budget fixture](skills/autowork/scripts/budget_controller.py).
- Scope: Add skills/autowork/scripts/continuation_capability.py and test_continuation_capability.py as a Toolset compatibility adapter and explicit capability report for original-card continuation/rework. Bind complete runtime accounting to its actual units, original allocation, attempts and identity. Invoke only an available native operation that enforces the remaining allocation; the existing experimental budget controller is not native integration proof.
- Acceptance: Unknown or mixed-unit usage, exhausted allocation, active/changed claims and unavailable cap/rework controls refuse the affected operation. Supported fixture paths preserve original identity/history and apply the cap atomically; retry/interruption cannot replenish it. No new session/card/max-turns prompt is represented as cumulative enforcement. Missing host capability remains an explicit external prerequisite.
- Checks executed: 114 capability/reconciliation/owner-cycle/budget/picker fixtures passed, covering unknown/mixed units, exhaustion, claim races, interrupted continuation, review rework and ordinary closeout. Independent review found no defect in this adapter. The combined 318/470/139/8 offline gate passed; actual native continuation is unqualified.
- Dependencies: None.
- Ownership: Shared maintainer for adapter; supported runtime supplier for absent host operations. No upstream source changes authorized.
- Exclusions: No direct board database writes, fabricated accounting, replenished budgets, replacement workers or unbounded native probes.
- Next action: Bind an actual supported runtime operation providing authoritative original allocation/history and atomic cumulative cap enforcement (including completed-card rework where needed). The installed unblock/edit controls do not provide it. Do not count messages as turns, reset allowances or loop on unchanged unblock capabilities.

### TOOLSET-019 — Deploy reviewed local fixes to selected eligible profiles

- [ ] TOOLSET-019 — Deploy reviewed local fixes to selected eligible profiles
- Status: in_progress; reviewed scoped local updater is implemented and integrated in eb72be6; selected-profile deployment remains pending.
- Goal: RECOVERY — Deliver reviewed repairs without remote fetches or fleet-wide side effects.
- Sources: [accepted recovery plan](docs/project.md#end-to-end-original-task-recovery), [updater](update_bundle.py), [updater tests](tests/test_update_bundle.py), [installation](docs/installation.md).
- Scope: Extend the existing updater with explicit selected profiles and immutable reviewed local source, native security admission, preflight/staging/backups, installed hash readback and resumable per-profile results. Preserve unselected consumers of shared sources and pinned runtimes.
- Acceptance: No implicit fetch, profile expansion, scan override, worker restart or configuration/schedule change. Active affected consumers defer; independent eligible targets proceed. Drift/source races refuse before unsafe writes. Retry reuses the same source and backups, unchanged deployment is a no-op, and installed bytes/registrations are verified without claiming product recovery.
- Checks executed: 52 real-Git/fake-native updater fixtures passed. Independent review found shared-board ownership and interrupted-clone defects; both reproduced and passed after repair. The combined 318/470/139/8 offline gate passed. Native scoped preflight ran; installation and live registration remain unverified.
- Dependencies: None.
- Ownership: Shared maintainer for implementation; authorized coordinator for selected-profile deployment.
- Exclusions: No implicit remote publication, dependency overrides, native scanner bypass, global configuration changes or active-runtime rebinding.
- Deployment result: Fresh native preflight against clean 51d99d6 deferred three selected profiles for their nonterminal/pinned native ownership. The fourth has a customized `skills/autoresearch/SKILL.md` with additional candidate-selection guidance; its bytes were preserved. No profile installation, scanner override or job change occurred.
- Next action: Reconcile original ownership through supported controls and preserve/reconcile the customized skill before scoped installation. Reuse the reviewed updater; do not repeat its completed implementation or label preflight as deployment.

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
- Current evidence: Exact original profile directory and original job ID are absent from this host's root and existing-profile job stores. No replacement job, profile or message was created.
- Next action: Restore access to the original host/profile/job and its authorized Telegram route, then inspect the setup and scheduled delivery receipts.

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
- Current evidence: No externally capped isolated model environment is established; the existing local containment/controller fixtures exclude provider execution. No useful-action timing or speed claim was inferred from them.
- Next action: With the same isolated model environment required by TOOLSET-003, execute the paired cold/warm comparison and report actual results.

### TOOLSET-020 — Reconcile permitted direct-main delivery truthfully

- [ ] TOOLSET-020 — Reconcile permitted direct-main delivery truthfully
- Status: open; bounded offline repair adopted under standing repository-development authority.
- Goal: RECOVERY — Let verified repository-permitted local integration close its delivery lane without invented protected-PR provenance.
- Sources: [accepted requirements](docs/project.md#accepted-requirements), [existing recovery plan](docs/project.md#end-to-end-original-task-recovery), [delivery evaluator](skills/autowork/scripts/delivery_state.py), [delivery tests](skills/autowork/scripts/test_delivery_state.py), [reconciliation](skills/autowork/scripts/reconcile.py).
- Scope: Extend existing read-only delivery evaluation and reconciliation for explicit policy-bound reviewed local integration. Bind exact candidate/base/tree, allowed target policy, review and observed integration evidence. Keep publication separate and retain the default protected-PR requirements. Update only the evaluator, reconciliation consumers, focused tests and necessary existing guidance.
- Acceptance: Permitted reviewed local integration is recognized without fabricated PR evidence; absent/contradictory authority, foreign review, changed candidates, stale targets and forged provenance refuse. Existing protected-PR behavior remains unchanged. Offline delivery does not close native/model/live acceptance or assert remote publication. Reconciliation preserves original card, sessions, retry limits and unknown usage.
- Checks: Run uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -B -m unittest discover -s skills/autowork/scripts -p test_delivery_state.py; repeat for test_reconcile.py and test_owner_cycle.py. Add failing-then-passing real-Git local-integration and refusal regressions; finish_task.py must run focused acceptance before owned commit; independent exact-candidate review is required before local integration.
- Dependencies: None.
- Ownership: toolset coordinator and one newly admitted isolated worker; no active native claim found at adoption.
- Decision: Reuse the existing delivery evaluator rather than inventing PR metadata, resetting the original card or implementing another dispatcher. This is an agent implementation decision under current authority, not a new historical user approval.
- Exclusions: No upstream edits, Git mutations in the evaluator, push/publication, deployment, profile/job/setting changes, original-card replacement, budget resets or live qualification. Coordinator owns local integration and canonical task closure.
- Stop conditions: One new coherent worker batch; stop on admission refusal or demonstrated overlapping writer. Preserve retained proposal and original closeout evidence.

## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| PORTABLE: Align portable workflow discovery | met | executed <code>Integration af8e567: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests -p test_portable_package.py; node --test tests/portable_pi.test.mjs; uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py; exact 5e5d043 independent review and isolated Codex 0.162.1/Pi 1.2.0 discovery verified</code> → pass | — |
| BACKLOG: Provide repeatable first-time backlog initialization | met | executed <code>Reviewed 7f07b182; integrated 73a8efc: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (247/437/135/8 offline tests; 2 skipped; native/model excluded)</code> → pass | — |
| RECOVERY: Qualify bounded automatic planning recovery | unverified | executed <code>Shared TOOLSET-017/018/019 implementation integrated eb72be6; independent review findings repaired with failing-then-passing regressions; final Python 3.12 scripts/check.py passed 318/470/139/8 tests, two skips/eight excluded. Native recovery, deployment and model qualification remain incomplete.</code> → pass; executed <code>TOOLSET-015 reviewed 16a750ce: seven disposable real-Git regressions, Bash syntax and whitespace passed; coordinator integration candidate uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 263/448/139/8 offline tests, 2 skipped and 8 excluded; native recovery NOT_CHECKED</code> → pass; executed <code>TOOLSET-016: exact 9b894fd same-card review approved; integration b470c68 Python 3.12 scripts/check.py passed 283/448/139/8 offline tests (2 skipped, 8 excluded), bash -n and git diff --check passed; native recovery NOT_CHECKED</code> → pass | TOOLSET-003, TOOLSET-017, TOOLSET-018, TOOLSET-019, TOOLSET-020 |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | met | executed <code>Reviewed 218865c; coordinator exact-commit Python 3.12 scripts/check.py: 253/448/139/8 offline tests passed, 2 skipped, 8 excluded; native same-card review approved; local integration only</code> → pass; executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass | — |
| CONTINUATION: Resolve and align continuation authority | met | executed <code>TOOLSET-007 historical check-reuse implementation verified in 9d1c7dc offline gate: check_receipt/retry_selection/reconcile regression modules passed; full 288/451/139/8, two skips and eight excluded native/model modules. Historical task archived; TOOLSET-008 independently reviewed and integrated.</code> → pass; executed <code>TOOLSET-008: independently reviewed and integrated 9d1c7dc; Python 3.12 scripts/check.py passed 288/451/139/8 tests, 2 skipped and 8 native/model modules excluded; exact correction review reran 26 checks. Native behavior not qualified.</code> → pass | — |
| CRON-REPORTING: Make Telegram scheduling reports reliable across invocation surfaces | partial | executed <code>Offline source guidance: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests (246 run, 2 skipped; no live delivery qualification)</code> → pass | TOOLSET-011 |
| STARTUP: Start useful implementation sooner with less preparation | unmet | executed <code>Reviewed fef4241; integration e2a0838: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (252/448/135/8 offline tests; 2 skipped; 8 live/integration modules excluded); native timing remains TOOLSET-013</code> → pass | TOOLSET-013 |

<!-- goals:coverage:end -->
