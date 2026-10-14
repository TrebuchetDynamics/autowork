# Completed tasks


<!-- archived from TODO.md -->

Source section: Completed local changes

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



<!-- archived from TODO.md -->

Source section: Completed local changes

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



<!-- archived from TODO.md -->

Source section: Completed local changes

### TOOLSET-006 — Preserve review progress and direct coordinator closeout

- Status: done (local regression coverage; autonomous model follow-through unverified).
- Goal: Keep new review outcomes visible and direct completed cards to integration checks.
- Source: [reconciliation helper](skills/autowork/scripts/reconcile.py).
- Scope delivered: Report-cache identity includes run and outcome; phase-specific next
  actions distinguish active/queued cards, recovery and terminal closeout.
- Checks: 12 reconciliation tests pass; terminal hints never claim delivery or approval.
- Remaining qualification: A model must execute the advised closeout; the read-only
  helper itself does not merge, dispatch, authenticate liveness or resume jobs.

<!-- End of migrated task history. -->


<!-- archived from TODO.md -->

Source section: Next

- [x] TOOLSET-010 — Bind Telegram reports and setup confirmation independently of invocation
  - Status: done (source instructions, offline contract checks and independent scenario review).
  - Goal: CRON-REPORTING — Resolve Telegram reporting independently of the invoking surface.
  - Sources: User request to report in Telegram from any invocation surface;
    [native workflow](skills/cron-autowork/SKILL.md),
    [portable workflow](adapters/skills/cron-autowork/SKILL.md),
    [workflow documentation](docs/workflows.md).
  - Scope delivered: Explicit profile/chat/topic routing, one setup confirmation,
    nonempty per-occurrence reports, delivery receipt checks and truthful failure reporting.
  - Exclusions: No live profile/job changes, unrequested immediate execution,
    cross-profile messaging, push, deployment or real-device operations.
  - Acceptance checked: Guidance covers CLI and Telegram topic setup, explicit local/quiet
    preferences, existing-job repair, missing transports and queued/ambiguous delivery.
    Setup confirmation remains distinct from scheduled execution and message delivery.
  - Checks: `uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests`
    passed: 246 tests run, two skipped; five cron contract tests passed. Independent
    before/after scenario review approved the source changes. Markdown links and diff checks passed.
  - Remaining qualification: Instructions and fixtures do not prove live agent behavior;
    TOOLSET-011 owns installation and Telegram receipt verification on the affected host.
  - Dependencies: None.
  - Ownership: Current Autowork coordinator for local closeout; no live worker claim.

Closeout repair for TOOLSET-010: task-source links to archive policies and test
code were incorrectly treated as history destinations, blocking this move.
Owner discovery now uses navigation outside task bodies; default/custom-owner
regression cases reproduce the failure and pass after the fix. All 36 archive,
policy and redaction tests passed, with independent preservation review.
Combined closeout validation: `uv run --python 3.12 --no-project
--with-requirements requirements-test.txt python scripts/check.py` passed
(803 tests run, two skipped; eight live/native modules excluded).
Existing open bodies and prior archive bytes were preserved; the completed
entry appears exactly once and a repeated render was byte-stable.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-009 — Account for archival in the shared rendering contract

- Task: TOOLSET-009 — Account for archival in the shared rendering contract
- Status: done (source contract acceptance and offline preservation checks).
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
- Closeout: Reviewed every acceptance criterion against the shared cycle, Docs Sync
  and render/archive_tasks. Added explicit open/closed-body preservation, actual
  custom archive path, links, unchanged second-pass bytes and handoff/commit checks.
  Removed Docs Sync's contradictory claim that rendering never changes task bodies.
- Verification: `cd skills/docs-sync/scripts && python3 -m unittest test_todo_archive test_archive_policy test_render_safety`
  passed (31 tests); changed Markdown links and diff checks passed. Independent
  acceptance review approved both contract corrections. No model/live qualification claimed.
- Closure normalization: The duplicate checkbox title is retained as a Task field;
  the heading and explicit Status own this completed entry's archival boundary.

<!-- End of verified TOOLSET-009 entry. -->


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-001 — Align portable skill discovery with the current public workflows

- [x] TOOLSET-001 — Align portable skill discovery with the current public workflows
- Status: done; independent review approved `5e5d043`, integrated locally at `af8e567`.
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
- Ownership: Original Autowork worker and independent reviewer completed the local
  slice; the current coordinator verified and integrated it. No live claim remains.
- Completion evidence: `5e5d043b758c63592bade98eae04d3670e1e2376` contains the nine
  reviewed implementation/test/document paths; `af8e56723e2c3c10f7068bba06cbbed23ef246b8`
  integrates them while preserving the earlier documentation work.
  Integration checks: portable Python regressions (3 tests), Pi Node regressions
  (3 tests), `uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py`
  (247 + 427 + 122 + 8 tests, all four directories passed; eight live/native modules
  excluded), local Markdown links/anchors and `git diff --cached --check` passed.
  Exact-source independent review also verified native Codex 0.162.1 and Pi 1.2.0
  discovery in isolated credential-free homes. Model compliance, Telegram delivery,
  unattended execution and minimum supported versions remain NOT_CHECKED.

<!-- End of verified TOOLSET-001 entry. -->


<!-- TOOLSET-002 local integration -->

### TOOLSET-002 — Provide a supported first-time task-index initialization path

- [x] TOOLSET-002 — Provide a supported first-time task-index initialization path
- Status: done; reviewed commit 7f07b182 integrated into local main at 73a8efc.
- Completion evidence: Independent same-card review approved the exact implementation;
  the composed integration candidate passed all four offline directories (247/437/135/8
  tests, two skipped). Empty/TODO-only initialization, conflict preservation and
  repeat-byte stability are covered. Live model/native/Telegram qualification is excluded.
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
- Ownership: Original worker and independent reviewer finished the local candidate;
  canonical integration and closure remain with its coordinator. Do not redispatch.

<!-- end TOOLSET-002 -->


<!-- archived from TODO.md -->

Source section: Next

- [x] TOOLSET-012 — Start ready tasks through one composed default preflight
- Status: done; independent review approved fef4241; integrated locally as e2a0838.
- Goal: STARTUP — Reach useful implementation sooner with less preparation/chat.
- Sources: [accepted full contract](docs/project.md#faster-ready-task-startup), [coordinator](skills/autowork/scripts/owner_cycle.py), [admission](skills/autowork/scripts/start_goal.py), [source capture](skills/autowork/scripts/source_freshness.py), [Autowork](skills/autowork/SKILL.md), [engineering adapter](skills/engineering/SKILL.md), [router](skills/engineering/scripts/route.py).
- Evidence: Composed owner_cycle ready preflight and concise contracts are implemented and independently reviewed. Integration e2a0838 passed the full offline check inventory (252/448/135/8 tests; 2 skipped; 8 live/integration modules excluded). Native timing remains TOOLSET-013.
- Scope: Finish one default ready-task command: reconcile → select/read body → capture sources → generate short complete contract → real native handoff → bookkeeping. Keep routing references optional, phase bundles optional, and workflow authority in Autowork. Use existing helpers/tests; preserve upstream protocol bytes.
- Acceptance: No separate validate-only call, planner, docs audit, full suite or optional skill load before normal dispatch. Preserve required contract fields, immutable base, canonical authority, freshness, ownership, budgets and original startup guard. Stale, held, incomplete, interrupted and already-owned cases fail/recover safely without replacement cards. Compact reports expose failures. Exact-one protocol selection and phase compatibility retain unknown-name/tamper refusal, mandatory tests and independent review; protocols never expand authority.
- Checks: From skills/autowork/scripts run `python3 -m unittest test_owner_cycle test_goal_handoff test_source_freshness test_response_tail`. At root run `python3 -m unittest discover -s tests -p test_engineering_vendor.py`, `python3 -m unittest discover -s tests -p test_workflow_cycle.py`, and `uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py`; check affected links and `git diff --check`. Reuse partial-delivery checks only when their inputs still match.
- Exclusions: No speculative cache acceptance, weaker guards/review, writer takeover, new scheduler/parallelism, upstream Agent/model/provider changes, push/deployment or live job edits.
- Dependencies: None.
- Ownership: Existing native worker and original coordinator; preserve its card, pinned inputs, scope and consumed budget. This wording change grants no new authority.
- Next action: TOOLSET-013 paired native measurement after its enforced environment limits are established; offline implementation does not qualify measured savings.


<!-- archived from TODO.md: TOOLSET-014 residue reconciliation -->

Source section: Next

The empty heading below was left live by the earlier checkbox-only move.
Its exact matching completed checkbox and full evidence body are already above
in this archive, with Status: done, review fef4241 and integration e2a0838;
goals.json also records TOOLSET-012 as done. Preserve that existing body unchanged.
This reconciliation adds no completion or native measurement claim.

### TOOLSET-012 — Start ready tasks through one composed default preflight



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-014 — Archive completed task headings with their checkbox bodies

- [x] TOOLSET-014 — Archive completed task headings with their checkbox bodies
- Status: done; reviewed 218865cc530bf9fb2711bce984e9af4b1a6e4f77 and integrated locally.
- Completion evidence: Original worker and native same-card reviewer passed 48 focused tests. Coordinator reran Python 3.12 scripts/check.py on the exact reviewed commit: 253/448/139/8 tests across four offline directories passed; two skipped and eight live/native/integration modules excluded. Complete-unit CLI conservation and archive/render idempotency verified; no live qualification or publication.
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



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-015 — Preserve explicit source refs in behind-only realignment

- [x] TOOLSET-015 — Preserve explicit source refs in behind-only realignment
- Status: done; minimal source-default repair committed at 16a750ce8aaea2ed914606edf4b97770a1fc85d3 and independently approved on the original native card. Coordinator integration candidate passed the Python 3.12 offline inventory (263/448/139/8 tests; 2 skipped; 8 native/model/integration modules excluded). Seven real-Git regressions, Bash syntax and whitespace checks passed. Local integration only; TOOLSET-003 remains unqualified.
- Goal: RECOVERY — Keep authorized local recovery usable without weakening preservation checks.
- Sources: [accepted recovery scope](docs/project.md#accepted-requirements), [realignment helper](skills/git-pull-merge/scripts/behind-only-realign.sh), [delivery safeguards](skills/git-pull-merge/SKILL.md).
- Scope: Repair explicit source-ref parsing in the behind-only helper and add disposable real-Git regression coverage. Own the helper and a focused test in tests/; preserve all existing ancestry, staged-index, safety-ref and writer-byte safeguards.
- Current evidence: Bash expands `SRC=${1:-@{u}}` with a supplied argument into that argument plus a literal `}`; an explicit immutable commit therefore fails before realignment.
- Decision: Fix the bounded parser defect under existing recovery authority; do not replace the realignment algorithm or reinterpret its exclusions.
- Acceptance: Explicit full commit and named-ref inputs resolve exactly; omitted input still resolves the configured upstream. Successful behind-only runs preserve dirty tracked and untracked bytes. Diverged history and staged changes still refuse without moving HEAD or altering bytes.
- Checks: Add and run `python3 -m unittest discover -s tests -p test_behind_only_realign.py`; run `bash -n skills/git-pull-merge/scripts/behind-only-realign.sh` and `git diff --check`. Use disposable repositories only; independent native review and scoped local commit are required before closure.
- Exclusions: No canonical realignment test, remote publication, live profiles/jobs, upstream Hermes edits, safety bypass, unrelated refactoring or native/model qualification claim.
- Dependencies: None.
- Ownership: Next authorized toolset worker; no overlapping live claim observed at booking.
- Next action: Reproduce with disposable Git, repair parsing, verify success/refusal and request review. TOOLSET-003 retains its bounded native-environment prerequisite.



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-016 — Apply clean incoming additions and deletions during behind-only realignment

- [x] TOOLSET-016 — Apply clean incoming additions and deletions during behind-only realignment
- Status: done; reviewed repair 9b894fd integrated locally as b470c68. Clean incoming additions/deletions apply with preservation-safe collision preflight; offline only.
- Goal: RECOVERY — Make the bounded Git recovery result usable without overwriting local writer bytes.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [realignment helper](skills/git-pull-merge/scripts/behind-only-realign.sh), [existing regressions](tests/test_behind_only_realign.py), [preservation contract](skills/git-pull-merge/SKILL.md).
- Scope: Repair clean incoming additions and deletions through the existing helper. Cover modifications, local deletions, untracked/ignored collisions and file/directory conflicts; fail safely before pointer movement when an incoming change cannot be applied while preserving local work. Keep explicit and default source handling.
- Acceptance: Clean added files materialize, clean deleted files disappear, helper exits successfully with HEAD/index matching the incoming tree; dirty and untracked bytes and local absences survive. Unsupported collisions refuse without HEAD/index/worktree mutation. Existing refusal and preservation cases remain passing.
- Checks: Add failure-first disposable real-Git regressions; run python3 -m unittest discover -s tests -p test_behind_only_realign.py, bash -n skills/git-pull-merge/scripts/behind-only-realign.sh and git diff --check; finish_task.py scoped commit and independent same-card review required. Offline Git only, not native recovery qualification.
- Exclusions: No real shared-checkout realignment, upstream Hermes edits, writer takeover, force/reset-hard, publication, deployment, profile/job/settings changes or budget resets.
- Dependencies: TOOLSET-015.
- Ownership: toolset coordinator; implementation through one isolated bounded native worker.
- Decision: Extend the existing helper with the smallest complete preservation-safe correction; do not create another dispatcher or relax the behind-only preconditions.
- Completion evidence: Original same-card independent review approved 9b894fd; fresh b470c68 integration candidate passed Python 3.12 scripts/check.py (283/448/139/8 tests; 2 skipped, 8 excluded), Bash syntax and whitespace. TOOLSET-003 remains the separate environment-held native successor; no push.



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-008 — Make Autowork continuation authority consistent

- [x] TOOLSET-008 — Make Autowork continuation authority consistent
- Status: done; corrected candidate 9d1c7dc independently reviewed and integrated locally.
- Priority: High; existing goal priority preserved.
- Goal: CONTINUATION — Execute authorized work without repeated permission rounds.
- Sources: [accepted autonomy policy](docs/project.md#autonomous-execution-authority), [original-task recovery plan](docs/project.md#end-to-end-original-task-recovery), [cycle](skills/shared/ENGINEERING-CYCLE.md), [Autowork](skills/autowork/SKILL.md), [scheduled policy](skills/autowork/references/scheduled-policy.md), [portable contract](adapters/skills/autowork/SKILL.md), [worker payload](skills/autowork/scripts/start_goal.py).
- Decision: Caller scope and saved stop/batch limits control continuation. Recurrence does not widen them or reset budgets. Within authorized work, local engineering/fixes/recovery/closeout proceed without another permission question. The saved one-new-batch job limit is unchanged; explicit multi-batch/whole-spec mandates remain supported. This replaces the former routine policy question, not a claim that the user separately selected a new batch count.
- Scope: Align native/portable/cycle instructions and generated worker contracts. Planning owns consequential choices and ready acceptance; workers execute, adapt failing approaches, fix tests/fixtures/user-space tooling and restore attributable inputs on the original task. Reuse concurrent implementation only after provenance, current ownership, checks and review are verified.
- Acceptance: No reconfirmation for ready local work, first check failure, routine tooling or known recovery. No invented inspect-only, one-rerun, extra-review or planning barriers. Preserve default/caller stop limits, one-task overrides, explicit continuation, saved schedules, review, active writers, pins and consumed budgets. A genuine pending approval holds its operation only; independent authorized work continues. Unknown product outcomes go to bounded planning; external authority and exhausted allocations are not fabricated.
- Checks: Extend/run `python3 -m unittest discover -s tests -p test_workflow_cycle.py`; from skills/autowork/scripts run `python3 -m unittest test_worker_role_contract test_owner_cycle test_retry_selection`. Cover local fix/recovery, default interactive, explicit one-task/continuation, recurring limits, pending review/approval, exhausted budget and non-overlapping fallback. Run the required source-bound final gate, links and `git diff --check`; these new acceptance checks are not executed here and fixtures do not prove live model behavior.
- Exclusions: No live job edits, scheduler/dispatch in this planning pass, new permission framework, guard/protection bypass, takeover, budget reset, upstream Agent edits or broader money/deployment/destructive authority.
- Dependencies: None.
- Coordination: Independent of TOOLSET-009; preserve other task order and leases.
- Ownership: Original card and candidate retained; coordinator owns integration correction. Recheck actual writers before execution; this plan creates no claim.
- Completion: Core reduced from 16,654 to 15,960 bytes; detailed mode and archive guidance remain reachable. Updated the stale unconditional-continuation assertion while preserving caller stops. Full Python 3.12 offline gate passed: 288/451/139/8 tests, two skips and eight excluded native/model modules. Independent review reran 26 focused checks and approved the exact correction. Original worker/card history and unknown usage preserved; no native restart, push or live behavior qualification claimed.



<!-- archived from TODO.md -->

Source section: Completed local changes

### TOOLSET-007 — Resume execution and reuse checks across calls

- Status: done; existing source verified by the current full offline gate.
- Scope: Saved reconciliation projection produces continuation/change fields;
  pending closeout precedes discovery. Run-or-reuse preserves stale receipts and
  reuses passing checks under their original input contract. Terminal display
  IDs are removed from execution and fingerprints; task/security inputs stay bound.
- Checks: Regression coverage for continuation, actual filtered subprocess
  environment, relevant environment changes, first execution, reuse and stale refusal.
- Evidence: Existing fingerprint repair e1d18d0 and continuation/check-receipt
  regressions passed in the 9d1c7dc full gate (288/451/139/8 offline tests,
  two skips and eight excluded native/model modules). This archives delivered
  history; no new implementation or native recovery is claimed for this task.
- Limits: No automated Git integration or model throughput claim; arbitrary
  source files and live ownership still require fresh checks before action.


<!-- end of verified closeout archive -->


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-020 — Reconcile permitted direct-main delivery truthfully

- [x] TOOLSET-020 — Reconcile permitted direct-main delivery truthfully
- Status: done; exact candidate 5e05e6b independently reviewed and integrated locally. Final Python 3.12 offline gate passed 319/475/139/8 tests (two skips, eight native/model modules excluded). Publication and live qualification remain separate.
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


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-021 — Preserve verified historical local integration after main advances

- [x] TOOLSET-021 — Preserve verified historical local integration after main advances
- Status: done; exact ab12f821 independently approved in native review and integrated locally at 49739eff. Historical delivery recognition is separate from strict current-target admission. Integration-candidate Python 3.12 scripts/check.py passed all four directories (332/495/139/8 tests, three skips, eight native/model modules excluded); whitespace passed. No publication or native/model/live/startup qualification claimed.
- Goal: RECOVERY — Recognize completed local delivery without repeating integration or changing original evidence.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [delivery evaluator](skills/autowork/scripts/delivery_state.py), [delivery regressions](skills/autowork/scripts/test_delivery_state.py), [reconciliation](skills/autowork/scripts/reconcile.py), [owner cycle](skills/autowork/scripts/owner_cycle.py).
- Scope: Add an explicit historical reviewed-local integration evaluation distinct from current-target admission. Carry the source-bound result through reconciliation and owner-cycle closeout. Preserve strict current-tip admission, original candidate/review/check pins, publication uncertainty and milestone boundaries.
- Acceptance: A valid independently reviewed fast-forward or exact two-parent/candidate-tree integration remains recognized when main subsequently advances and retains that integration in ancestry. Divergent/reset main, moved candidate refs, forged policy/review, malformed topology and missing qualification still refuse the corresponding claim. A historical result grants no new integration or publication authority. Owner-cycle can select eligible work after verified historical closeout without repeating the old merge.
- Checks: Add failing-then-passing real-Git regressions for unchanged-tree and changed-tree descendants, reset/divergence, moved refs and forged provenance; run Python 3.12 unittest test_delivery_state, test_reconcile and test_owner_cycle plus git diff --check. Required independent review and owned finish_task commit precede completion. Offline checks do not qualify native/model recovery or startup timing.
- Dependencies: None.
- Ownership: Toolset coordinator/new bounded isolated worker; completed TOOLSET-020 card/run/evidence stay unchanged.
- Exclusions: No upstream Hermes edits, evidence repinning, old-card replacement/retry, budget reset, profile/job changes, push or live operations.
- Decision: Separate historical delivery truth from current-target mutation admission rather than remove the current-tip safety check. New source-backed maintenance under standing repository authority; no historical approval invented.
- Current evidence: A real-Git delivery fixture returns locally integrated at the reviewed tip, then unknown after a tree-identical descendant on main. Existing line 113 requires main to equal the integration tip. The original completed Toolset card remains blocked at verify_and_integrate despite preserved local-main ancestry.
- Next action: Implement the explicit historical path, regressions and connected consumers in one bounded worker batch; preserve original cards and qualification limits.

