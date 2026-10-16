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



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-022 — Reconcile independently reviewed changed-base local delivery

- [x] TOOLSET-022 — Reconcile independently reviewed changed-base local delivery
- Status: done; exact 816678e3 independently approved in native review run406 and integrated locally in 5f49a2e0. Frozen integration Python 3.12 scripts/check.py passed 332/510/139/8 offline tests (three skips; eight native/model/integration modules excluded); whitespace passed. Historical original-card structured evidence backfill remains coordinator work; native/model/live/startup qualification is not claimed.
- Goal: RECOVERY — Unblock truthful source-bound closeout after independent review and integration onto newer main.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [reconciliation](skills/autowork/scripts/reconcile.py), [delivery evaluator](skills/autowork/scripts/delivery_state.py), [owner cycle](skills/autowork/scripts/owner_cycle.py), [local evidence contract](skills/autowork/references/owner-cycle.md#reviewed-local-delivery-evidence).
- Scope: Repair connected reconciliation, delivery evaluation, owner-cycle consumers and regressions for independently reviewed original implementation plus verified changed-base local integration. Permit explicit trusted coordinator evidence bound to original implementation run and independently observed review; verify actual merge topology and exact reviewed delta preservation without rewriting candidate base/tree. Retain legacy fail-closed policy and historical readback.
- Acceptance: Original implementation and independent review remain separately bound; changed-base integration validates only with exact source-bound checks of the coherent integration result and preserved reviewed changes. Missing/stale/foreign/conflicting evidence and unrelated or altered candidate changes refuse. A completed original card can select again only after truthful delivery verification. No fixture claims native/model/live qualification.
- Checks: Python 3.12 unittest test_delivery_state test_reconcile test_owner_cycle test_retry_selection from skills/autowork/scripts; git diff --check; integration owner runs scripts/check.py on frozen integration candidate after independent review.
- Dependencies: None.
- Ownership: toolset coordinator and one isolated native worker; canonical local integration belongs to coordinator.
- Exclusions: No upstream edits, direct board/run metadata writes, repinning historical candidates, replacement of original cards, budget resets, push/deploy, profile/job/schedule changes or live qualification.
- Decision: Bounded offline consumer repair under standing repository authority; retain original TOOLSET-021 card/runs and completed status. Existing TOOLSET-003/017/018/019 live prerequisites stay open; no focus or ordering change.
- Current evidence: reconcile.py excludes delivery evidence when latest run is the independent reviewer; reviewed-local evaluator requires before equal original candidate base and merge tree equal candidate tree. Actual TOOLSET-021 integration merged its reviewed candidate onto newer main. These constraints keep owner_cycle in verify_and_integrate despite historical completion.



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-023 — Align current project status with reviewed offline delivery

- [x] TOOLSET-023 — Align current project status with reviewed offline delivery
- Status: done; exact candidate 645b6597 independently reviewed and locally integrated in d6f842a; offline documentation only.
- Goal: STARTUP — Avoid repeated preparation of already delivered work while retaining native timing qualification.
- Sources: [accepted startup](docs/project.md#faster-ready-task-startup), [current project status](docs/project.md#planned-work-and-verification), [reviewed delivery history](TODO.archive.md), [current queue](TODO.md).
- Scope: Correct stale present-tense TOOLSET-002/012 review/integration and TOOLSET-008 policy statements in docs/project.md. Label requirement-capture/task-context prose as historical where appropriate. Preserve original historical IDs, measurements, accepted scope and live gates. Add a focused offline regression for current versus historical status prose in tests/test_project_status.py.
- Acceptance: Current project status matches reviewed archived TOOLSET-002/008/012 delivery. Historical task-context reduction measurements and original five IDs remain intact and explicitly historical. TOOLSET-003/011/013 live qualification remains open; no native startup speed claim, task reopening or priority/focus change.
- Checks: Run `python3 -m unittest discover -s tests -p test_project_status.py`, `python3 skills/docs-sync/scripts/goals.py validate .`, and `git diff --check`; inspect changed document links/anchors against the complete candidate and review exact scoped diff. These checks prove offline documentation only.
- Dependencies: None.
- Ownership: toolset native worker in its pinned isolated workspace; coordinator owns canonical ledger and local integration.
- Exclusions: No upstream Hermes edits, native/model/live qualification, profile/job/settings changes, publication, deployment or unrelated docs rewrite.
- Decision: Use this bounded documentation correction under standing repository maintenance authority because existing runnable-ledger tasks require unavailable live environments, original-card runtime capabilities or excluded profile deployment. Preserve RECOVERY ordering and absent focus; do not reimplement TOOLSET-012.
- Completion evidence: Independent exact-candidate review approved 645b659713ddcc9561f2d0c104cc5bf71c32aaec; 58 local links and seven fragments verified. Frozen integration d6f842a passed Python 3.12 scripts/check.py: 337/513/139/8 tests, three skips, eight native/model/integration modules excluded. Canonical five-test project-status regression, goals validation and whitespace checks passed. TOOLSET-003/011/013 remain open; no native timing or remote publication claim.



<!-- archived from TODO.md -->

Source section: Next

Disposition: Superseded; not completed
Successors: TOOLSET-026
Reason: Accepted TODO-first execution decision retires native-card-only recovery; shipped fixes and unpassed historical acceptance remain preserved.
Original task and unchecked acceptance retained below.

### TOOLSET-017 — Prepare and recover exact-card writer registration

- [ ] TOOLSET-017 — Prepare and recover exact-card writer registration
- Status: in_progress; shared reservation and prerequisite preparation are implemented and integrated in eb72be6; new-card transactional registration and verified disjoint fallback are now implemented; original-card native migration remains unavailable.
- Goal: RECOVERY — Make required registration compatible with immutable startup admission.
- Sources: [accepted recovery plan](docs/project.md#end-to-end-original-task-recovery), [launcher](skills/autowork/scripts/start_goal.py), [startup guard](skills/autowork/scripts/pass_workspace.py), [registration verifier](skills/autowork/scripts/writer_registration.py), [handoff](skills/autowork/references/handoff.md).
- Scope: Implement deferred initial dispatch for explicitly required registration and an attributed original-card prerequisite transition through supported controls. Preserve original evidence; keep declared coordination state separate from executable source. Include executable helper/runtime migration compatibility and exact identity/scope verification.
- Acceptance: No worker starts before required registration is verified. Old pins/refusals remain retained; recovery changes only the permitted prerequisite. Mismatched card/task/base/workspace/scope, duplicate evidence, source drift and live writers refuse. Missing native transition is reported as unavailable, never emulated by board writes or a replacement card. Actual profile recovery is checked in the original task, not claimed from fixtures.
- Checks executed: 58 registration/workspace/runtime fixtures passed. Independent review found a partial-write retry defect; its regression reproduced the failure and passed after atomic publication. Final Python 3.12 offline gate passed 318/470/139/8 tests (two skips, eight native/model modules excluded). Native same-card recovery remains unrun. The transactional-new-card correction passed independent review, the 328/488/139/8 offline gate (three skips), and installed-native isolated commit/rollback checks. An existing-profile independent fallback was then admitted and observed running in its exact frozen runtime; its product acceptance and review remain pending.
- Dependencies: None.
- Ownership: Authorized shared maintainer; original product owners/cards remain unchanged.
- Exclusions: No upstream edits, silent repinning, new product cards, budget reset, live profile writes or pause changes in the offline implementation slice.
- Next action: Use transactional new-card admission for genuinely independent accepted work; retain original stopped cards and allocations. Existing cards still need a supported original-card prerequisite/runtime migration and cumulative continuation cap. The new reservation/preparation path deliberately retains the original guard and old evidence; it does not recover an already frozen native card. Do not recreate the card or repeat the completed offline implementation.



<!-- archived from TODO.md -->

Source section: Next

Disposition: Superseded; not completed
Successors: TOOLSET-026
Reason: Accepted TODO-first execution decision retires native-card-only recovery; shipped fixes and unpassed historical acceptance remain preserved.
Original task and unchecked acceptance retained below.

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



<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-025 — Execute Autowork directly from repository tasks without Kanban

- [x] TOOLSET-025 — Execute Autowork directly from repository tasks without Kanban
- Status: done; reviewed shared implementation and bounded qualification complete.
- Goal: RECOVERY — Make repository tasks executable without a second task board.
- Sources: [accepted TODO-first decision](docs/project.md#todo-first-execution-without-kanban), [current coordinator](skills/autowork/scripts/owner_cycle.py), [portable execution](adapters/skills/autowork/SKILL.md), [scoped updater](update_bundle.py).
- Scope: Replace mandatory native-card dispatch/reconciliation with direct current-session execution and optional host-native delegation. Reuse task selection, real writer checks, isolated workspaces, input-bound check/review evidence and supported runtime limits. Keep TODO-only repositories usable and existing goals.json supported.
- Acceptance: A ready TODO task reaches useful implementation with no Kanban installation, database, card creation or board lookup. Concurrent automated writers for one canonical repo are excluded, real active work is preserved, explicit budgets are enforced by actual host controls, and required checks/review/integration remain. No second task registry or mandatory contributor tool.
- Checks: 37 direct-execution regressions passed; independent review reproduced and verified repairs for dependency/plan binding, malformed budgets, command attribution, source freshness and detached children.
- Dependencies: None.
- Ownership: Toolset coordinator; independent source review complete.
- Exclusions: No upstream Agent edits, consumer product repairs, card deletion, destructive migration, fabricated completion, budget reset, unrequested publication or live schedule activation.
- Delivery: Reviewed shared source at 0a50f24; local integration is recorded separately. Existing production schedules, private profile installations, model behavior and Telegram delivery are not claimed by these fixtures.



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-026 — Recover existing work without historical card gates

- [x] TOOLSET-026 — Recover existing work without historical card gates
- Status: done; reviewed shared implementation and bounded qualification complete.
- Goal: RECOVERY — Make repository tasks executable without a second task board.
- Sources: [accepted TODO-first decision](docs/project.md#todo-first-execution-without-kanban), [current coordinator](skills/autowork/scripts/owner_cycle.py), [portable execution](adapters/skills/autowork/SKILL.md), [scoped updater](update_bundle.py).
- Scope: Remove old-card, board-status and unsupported native-continuation prerequisites from recovery and scoped installer admission. Use attributable candidate/source/check evidence and actual process/workspace activity. Keep historical native records untouched; reconcile original TODO work without replacing it with duplicate tasks.
- Acceptance: Missing, malformed, blocked, done or mismatched old cards neither block safe work nor count as ownership/completion evidence. Idle candidates retain their changes and valid receipts, active writers remain protected, explicit task allocations are not reset, and updater deferral reflects actual runtime/file compatibility rather than card status alone.
- Checks: 71 scoped-updater, 17 worktree-concurrency and 12 read-only audit tests passed; independent real two-repository lease reproduction passed. Old handoffs and native authority bindings cannot gate the direct path.
- Dependencies: TOOLSET-025.
- Ownership: Toolset coordinator; independent source review complete.
- Exclusions: No upstream Agent edits, consumer product repairs, card deletion, destructive migration, fabricated completion, budget reset, unrequested publication or live schedule activation.
- Delivery: Reviewed shared source at 0a50f24; local integration is recorded separately. Existing production schedules, private profile installations, model behavior and Telegram delivery are not claimed by these fixtures.



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-027 — Align cron and contributor workflows with the TODO-first execution path

- [x] TOOLSET-027 — Align cron and contributor workflows with the TODO-first execution path
- Status: done; reviewed shared implementation and bounded qualification complete.
- Goal: RECOVERY — Make repository tasks executable without a second task board.
- Sources: [accepted TODO-first decision](docs/project.md#todo-first-execution-without-kanban), [current coordinator](skills/autowork/scripts/owner_cycle.py), [portable execution](adapters/skills/autowork/SKILL.md), [scoped updater](update_bundle.py).
- Scope: Update native/portable skills, cron generation, reporting, README/architecture/runbooks and supported scoped rollout to the card-free path. Reconcile superseded native-only remaining queue entries explicitly without fabricated success. Keep TODO/archive/index authoritative and preserve existing evidence.
- Acceptance: A new developer can select, implement, test and review a TODO task without learning Hermes cards. Generated and migrated prompts use the same direct path while preserving pauses, scopes, self-repair bindings, delivery and runtime limits. Superseded native prerequisites no longer appear as required next actions. A bounded disposable cron journey proves execution separately from source installation and message delivery.
- Checks: Prompt/installer/contributor regressions passed; independent review approved the runtime and worktree deltas. Isolated native script and scheduler journeys passed implementation, checks, stale-evidence rejection, archival and no duplicate execution; no model or external delivery claim.
- Dependencies: TOOLSET-026.
- Ownership: Toolset coordinator; independent source review complete.
- Exclusions: No upstream Agent edits, consumer product repairs, card deletion, destructive migration, fabricated completion, budget reset, unrequested publication or live schedule activation.
- Delivery: Reviewed shared source at 0a50f24; local integration is recorded separately. Existing production schedules, private profile installations, model behavior and Telegram delivery are not claimed by these fixtures.



<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-028 — Enforce TODO.md priority order offline with drift guard, reconciliation and bootstrap

- [x] TOOLSET-028 — Enforce TODO.md priority order offline with drift guard, reconciliation and bootstrap
- Status: done
- Evidence: `python3 scripts/check.py` (4 directories, 0 failures) and `git diff --check` on the priority-order candidate; new suites `skills/docs-sync/scripts/test_priority_order.py` and `skills/autowork/scripts/test_priority_selection.py`. Re-run probe: unmigrated READY T1 with UNMIGRATED; bootstrap keeps T1; human swap gives PRIORITY_DRIFT (`goals.py next` exit 3); `reorder` then selects T2. Offline only; TOOLSET-029 holds the live fleet migration.
- Goal: PRIORITY — Make TODO.md order the enforced human priority.
- Sources: [accepted decision](docs/project.md#todo-owned-task-priority), [ledger helper](skills/docs-sync/scripts/goals.py), [direct selection](skills/autowork/scripts/task_execution.py).
- Scope: Add the versioned `priority_order` record, ordering precedence, one shared drift guard used by every selection entry point, `goals.py reorder`, idempotent `goals.py bootstrap-order` with `--dry-run`, Docs Sync/Autowork guidance and offline regressions. No consumer repository changes.
- Acceptance: T1/T2 regression: bootstrap of TODO T2,T1 with ledger order T1,T2 moves blocks to T1,T2 and selection stays T1; a later human move to T2,T1 yields PRIORITY_DRIFT from `goals.py next` and direct selection; after `reorder`, both select T2. Unmigrated ledgers keep legacy order with a visible UNMIGRATED flag. Reconcile writes only goals.json under lock/revision guard and refuses missing or duplicated bodies. Bootstrap is a no-op when a record exists, preserves block bytes and the eligible order, and requires the dry-run revision. Tests also cover unchanged renders, cross-goal reorders, dependencies, later-eligible tasks, stale revisions, an active claim, missing index and idempotent sync.
- Checks: `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Current toolset coordinator.
- Exclusions: No consumer repository edits, fleet job pauses, push or live migration; TOOLSET-003 stays recovery-only.
- Next action: Add the failing T1/T2 regression, then implement the record, guard, reconcile and bootstrap operations.



## Superseded native-card recovery design

Historical provenance from `docs/project.md` at `b021c54659e899880e45c225bc45dd55c5bd1247`.
The later [TODO-first decision](docs/project.md#todo-first-execution-without-kanban)
supersedes native-card prerequisites. The quoted acceptance and relative links are
retained in their original source context, not reactivated as current instructions.

```markdown
## End-to-end original-task recovery

Status: Accepted

The user selected planning end-to-end recovery of the affected original tasks,
including shared fixes and supported scoped deployment, while preserving pauses
and budgets. Success means attributable implementation, required checks and review,
permitted integration and truthful task closure on those original tasks. A shared
helper commit, installed file, refreshed cron prompt or passing unrelated fixture
is an intermediate result. This planning selection does not itself run workers,
resume paused jobs, authorize publication or authorize upstream Agent edits.

Keep profile names, original card/run IDs, paths and private evidence in the existing
profile recovery receipts. The following shared work extends the existing tasks;
it creates no replacement product card or parallel product backlog. Refresh actual
card/run/process and candidate state before any execution or deployment.

### 1. Finish the held continuation candidate

TOOLSET-008 already has an independently reviewed candidate, but its integration
gate failed. The retained candidate has a 16,654-byte core skill against a strict
16,000-byte limit and an obsolete unconditional-continuation assertion. Focused
review approval remains historical evidence, not approval of an eventual correction.

- Preserve the original candidate and card. Inspect current writers and prepare
  attributable coordinator corrections in an isolated checkout of that candidate.
  Keep native worker restart, local correction, review and integration distinct.
  Do not require a done-to-running transition merely to prepare local corrections;
  this does not authorize restarting a worker or resetting its allocation.
- Move detailed mode guidance into existing references and retain a compact core
  rule. Keep the size limit and each reference reachable. Update the stale picker
  assertion to exercise caller-limited continuation; retain default-one-slice,
  explicit-stop, explicit-continuation and scheduled-limit coverage.
- Touch `skills/autowork/SKILL.md`, its existing mode/iteration references,
  `skills/autowork/scripts/test_picker_policy.py` and affected existing workflow
  tests only as needed. Reconcile the seven original candidate paths against main;
  preserve later shared repairs and dirty canonical bookkeeping.
- Run `python3 -m unittest discover -s tests -p 'test_workflow_*.py'` and, from
  `skills/autowork/scripts`, `python3 -m unittest test_picker_policy
  test_worker_role_contract test_owner_cycle test_retry_selection` on the corrected
  candidate. Then run the repository's offline integration gate once. Obtain fresh
  independent review for the corrected bytes before permitted local integration.
  If the required review/lifecycle route is unavailable, retain the verified
  correction and name that operation; never reuse approval for changed bytes.

### 2. Repair registration preparation, not the verifier's refusal

TOOLSET-017 owns the Toolset change. Current `start_goal.py` creates the native card
after freezing candidate/source inputs; the required registration needs that card's
identity, while the registry itself may already be in the immutable snapshot.
Appending the required row then invalidates the original guard. A clearer error or
more permissive prompt cannot supply the missing transition.

Plan the lifecycle as reserve without dispatch, register exact identity/scope,
freeze final startup prerequisites, verify, then release. Treat an explicitly
declared coordination registry separately from executable product inputs; never
automatically exempt arbitrary source files from fingerprinting. Use supported
native lifecycle controls and the repository's registration operation. No direct
board database writes, fabricated worker identity or unrestricted shell callback.

For an existing original card, preserve old manifests, requirement bytes, refusals
and consumed usage. A supported recovery must record the before/after prerequisite
identities and allow only the attributed registration change; it must reject
unrelated source, scope, base, ownership or runtime drift. Existing frozen runtimes
require an explicit supported migration, not replacement of helper files in place.
If the host cannot record/release that transition, report the capability unavailable
and keep native execution held. Implement and test the Toolset-side preparation
separately; do not label it end-to-end recovery.

### 3. Establish real continuation and review-rework capability

TOOLSET-018 owns the accounting/capability contract. The inspected native CLI exposes
an initial goal limit, but its `unblock` operation supplies no remaining-turn cap or
original-session selector. Its edit operation does not provide that cap either.
No verified cumulative-accounting operation is currently established for the held
tasks. Assistant-message counts and outer goal-loop counts are different units.

Before resumption, read authoritative attempt/session accounting, explicit original
allocation, retry history and unknown charges. Compute a remainder only when the
units and complete history agree. Require the runtime to enforce that remainder
on the original card and retain it across retries and review rework. A prompt,
new max-turns value, replacement session or helper-only counter is not enforcement.

Use a Toolset compatibility adapter only when the installed native runtime exposes
the needed operations. The adapter must explicitly report missing capabilities;
do not invent CLI flags or patch upstream. If unavailable, the concrete external
prerequisite is a supported runtime operation for original-card continuation with
atomic accounting/cap enforcement and, where needed, completed-card rework.
Offline adapter refusals can be tested now; native recovery remains held until
that operation and the original accounting are established. No extra allocation
is inferred from this plan or a later cron tick.

### 4. Deploy only the reviewed change to eligible selected profiles

TOOLSET-019 owns supported scoped deployment. Extend `update_bundle.py` and its
existing tests with explicit profile selection and a reviewed immutable local
source, without an implicit fetch or all-profile expansion. Retain native security
admission for installation/update; prior scanner approvals apply only to their
recorded scope. Planning source changes is not approval of a new scan override.

Preflight the complete selected change before writes: source identity and closure,
installed bytes/customizations, active helper references, affected frozen runtimes
and ownership. Stage and back up attributable changes, install through the supported
path, verify installed hashes and command registration, and record actual results
per profile. Preserve paused jobs, settings, models, delivery and budgets. Defer
active pinned consumers; a newer installation never silently migrates their cards.
Continue independent eligible profiles without touching unselected/shared active
consumers. Repeated unchanged deployment is a no-op; interruption resumes from the
original source/backup record rather than fetching a different revision.

### 5. Close the affected original work in independent lanes

The existing private recovery receipts map these lanes to the original product
tasks. Add outcomes there and in their existing task ledgers, not new product IDs.

- Registration-held work: after the original-card prerequisite transition and
  accounting are verified, resume its accepted implementation and exact acceptance,
  review and integration. Record successful initial admission and useful execution;
  a verified registration alone does not close the product task.
- Continuation-held work: use the enforced original-card remainder and corrected
  existing scope. Complete its implementation, visual/affected backend checks,
  review and integration; retain separate live qualification.
- Approved integration: refresh exact candidate/review and current target state,
  then perform authorized closeout without waiting for unrelated registration or
  continuation repairs. Source changes require affected checks and new review.
- Paused ownership: preserve the pause and original claim; recover attributable
  preview prerequisites and disposition as preparation only. No worker/schedule
  resume is implied. Report this lane as intentionally paused, not recovered.

TOOLSET-003 remains the separate disposable native recovery qualification;
TOOLSET-011 and TOOLSET-013 retain their delivery and startup-measurement scopes.
Do not make their unavailable environments prerequisites for an independent local
source correction or already-authorized integration.

Verification must cover registry changes before/after freeze, duplicate/mismatched
identity, changed product inputs, incomplete accounting, exhausted remainder,
interrupted continuation, already-running claims, completed-card review rework,
paused/unselected profiles and source changes during deployment. Use offline real
Git and native doubles for deterministic contracts, then the bounded actual native
journey when its capabilities are available. Offline success never substitutes
for original-task recovery. Report implemented, reviewed, integrated, installed,
running, qualified and intentionally paused separately.

### Execution evidence

TOOLSET-008 is complete: correction `9d1c7dc` passed the full offline inventory
(288/451/139/8 tests, two skips and eight excluded native/model modules), received
fresh independent review, and was integrated locally. Its native core is 15,960
bytes, under the unchanged 16,000-byte limit. The original native worker/card was
not restarted. Verified completed bodies are retained in TODO.archive.md.

The original reporting target is absent from this host; TOOLSET-011 remains open.
TOOLSET-003 and TOOLSET-013 still need an isolated model environment with externally
enforced spend and descendant limits. The existing containment/controller fixtures
explicitly exclude provider execution and cannot qualify those tasks.

TOOLSET-017/018/019 shared implementation is integrated in `eb72be6`: blocked
registration reservation and attributable preparation, an explicit native
continuation/accounting contract, and selected-profile local updates with native
security admission. Independent review found three defects (partial evidence
writes, shared-board ownership discovery and interrupted staging); failing
regressions reproduced each, repairs passed, and the final offline inventory
passed 318/470/139/8 tests (two skips, eight native/model modules excluded).
Concurrent consultation repairs already on main were preserved.

These source changes do not complete original-card recovery. The installed runtime
still lacks the required prerequisite migration and cumulative-cap continuation
operations/accounting. Selected-profile installation remains subject to fresh
ownership and native security admission; pauses and original budgets remain intact.

Final selected-profile preflight against clean `51d99d6` deferred three targets for
nonterminal/pinned native ownership and one for a customized Autoresearch skill.
The customization adds candidate-selection guidance and was preserved. No profile
installation, scanner override, schedule change or original-worker restart occurred.
Installation and product recovery therefore remain open in TOOLSET-017/018/019.


```


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-030 — Add a document role manifest and offline docs check

- [x] TOOLSET-030 — Add a document role manifest and offline docs check
- Status: done
- Goal: DOCS-COMPLETENESS — Make core-document role coverage and link/command integrity checkable instead of prose-only.
- Sources: [accepted completeness plan](docs/project.md#checkable-core-document-completeness), [Docs Sync core owners](skills/docs-sync/SKILL.md), [document scaffold](skills/docs-sync/references/document-scaffold.md), [goals helper conventions](skills/docs-sync/scripts/goals.py).
- Scope: Add a versioned manifest schema and a `docs.py` helper beside `goals.py` with `validate` and `check` commands. A role entry records path or `path#section`, outcome status (Docs Sync's existing role outcomes), covered source paths and last-verified commit. `check` reports broken local links/anchors in mapped documents, documented repository script paths that do not exist, and baseline roles neither mapped nor recorded with a not-applicable reason. Document the manifest in the scaffold and teach the Docs Sync skill to run the check when a manifest exists. Add focused offline unittest regressions to the existing docs-sync test directory.
- Acceptance: A valid manifest passes; a broken link or anchor, a missing documented script path, an unmapped baseline role and a malformed entry each fail with a diagnostic naming the role and path. The helper is read-only, refuses symlinked or out-of-repo paths, and repositories without a manifest keep current behavior. External URLs are not fetched.
- Checks: New `test_docs_manifest.py` under `skills/docs-sync/scripts`; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No consumer-repository manifests, network link checking, document rewriting, upstream Hermes edits or push.
- Open question: Manifest location (default: `docs/roles.json`).
- Current evidence: Adds `skills/docs-sync/scripts/docs.py` (`validate`, `check`), `test_docs_manifest.py` (17 offline tests; the first 11 failed before the helper existed), the scaffold's optional role manifest section and Docs Sync/adapter references. A throwaway manifest over ten of this repository's documents, including TODO.md and the Docs Sync skill, reported no findings.
- Review: An independent read-only review found one blocker (absolute links resolved outside the repository) and four should-fix defects (traceback on overlong paths, underscore and setext anchors, scripts after `cd`); all were reproduced as regressions and fixed, along with reference-style links, query strings, unclosed fences, path-naming diagnostics and a missing repository path.
- Checks run: `python3 scripts/check.py` passed offline after the review fixes: 403/571/185/8 tests in 4 directories, 1 skipped, 8 modules excluded; `git diff --check` clean. The run set aside the uncommitted TOOLSET-031/032 test files.
- Closure: Offline helper and documentation only; no repository has adopted a manifest yet.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-031 — Report stale document roles from covered-path history

- [x] TOOLSET-031 — Report stale document roles from covered-path history
- Status: done
- Goal: DOCS-COMPLETENESS — Detect documentation drift from source changes instead of relying on an agent rereading files.
- Sources: [accepted completeness plan](docs/project.md#checkable-core-document-completeness), TOOLSET-030 manifest schema.
- Scope: Add a read-only `docs.py stale` command that lists roles whose covered source paths changed between the recorded last-verified commit and HEAD, with the changing commits. Docs Sync uses the list to scope Maintain passes and updates last-verified commits only for roles it actually verified.
- Acceptance: Unchanged covered paths report nothing; a covered-path commit after last-verified reports that role with the commit; an unknown or non-ancestor last-verified commit is reported as unverifiable, not fresh. No files are written.
- Checks: Real-Git fixture regressions in the docs-sync test directory; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-030.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No automatic document edits, timestamp churn, history rewriting or push.
- Current evidence: Adds read-only `docs.py stale` (Git history only, inherited `GIT_*` overrides removed, literal pathspecs) and `test_docs_stale.py` (7 real-Git fixture tests, all failing before the command existed), plus scaffold, Docs Sync, adapter and CHANGELOG notes. A throwaway manifest over this repository reported exactly the roles whose covered paths changed after their verified commits.
- Checks run: `python3 scripts/check.py` passed offline: 403/571/192/8 tests in 4 directories, 1 skipped, 8 modules excluded, with the uncommitted TOOLSET-032 test file set aside; `git diff --check` clean. Self-reviewed; no separate independent review for this read-only increment.
- Closure: Offline helper only; no repository has adopted a manifest yet.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-032 — Define repository-type role profiles in the Docs Sync scaffold

- [x] TOOLSET-032 — Define repository-type role profiles in the Docs Sync scaffold
- Status: done
- Goal: DOCS-COMPLETENESS — Make role applicability consistent per repository type and cover user-facing reference roles.
- Sources: [accepted completeness plan](docs/project.md#checkable-core-document-completeness), [document scaffold](skills/docs-sync/references/document-scaffold.md), [Docs Sync core owners](skills/docs-sync/SKILL.md).
- Scope: Define service, library, CLI/plugin, application and infrastructure profiles with baseline roles in the scaffold. Add reference (commands/configuration), glossary, troubleshooting and installation/upgrade roles with ownership boundaries. The manifest records the selected profile and `docs.py check` uses that profile's baseline. Keep the portable adapter skill aligned.
- Acceptance: Each profile lists its baseline roles; a CLI/plugin manifest missing a reference role fails `check` while a service manifest without one does not; manifests without a profile keep the current baseline. No empty documents are required.
- Checks: Profile regressions in the docs-sync test directory; portable package/adapter tests already in `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-030.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No consumer-repository migration, document generation or push.
- Current evidence: `docs.py` gains five profiles, manifest `profile` validation and a `profiles` command; the scaffold documents the profile table and reference, install-upgrade, troubleshooting, user-guide and glossary roles, with Docs Sync/adapter pointers. `test_docs_profiles.py` (5 tests) failed before the change. A throwaway `cli-plugin` manifest for this repository reported exactly its unmapped `reference` and `troubleshooting` roles.
- Checks run: `python3 scripts/check.py` passed offline: 403/571/197/8 tests in 4 directories, 1 skipped, 8 modules excluded; `git diff --check` clean. Self-reviewed.
- Closure: Offline helper and scaffold only; adopting a manifest or writing the missing roles in this or any consumer repository is separate work.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-033 — Read the runtime-policy opt-out from the plugin settings path in finalize verification

- [x] TOOLSET-033 — Read the runtime-policy opt-out from the plugin settings path in finalize verification
- Status: done
- Goal: POLICY-OPTOUT — A profile opted out the documented way is not reported as incomplete.
- Sources: [documented opt-out](docs/installation.md#install), [reference](docs/reference.md#plugin-settings), [`runtime_defaults.py`](runtime_defaults.py) `_opted_out` and `apply_runtime_defaults`, [`setup_runtime.py`](setup_runtime.py) finalize, [existing regression](tests/test_telegram_menu_policy.py), [loader integration](tests/integration_plugin.py).
- Scope: Found while writing docs/reference.md (source inspection, not a reproduced run). Hermes' `PluginContext.get_config` reads `plugins.entries.hermes-toolset.settings.apply_runtime_defaults` (with a legacy `config` fallback), and the docs and loader integration test use that path, so loading honors the opt-out. `verify_runtime_defaults()` uses `_opted_out()`, which reads `plugins.entries.hermes-toolset.apply_runtime_defaults` without `settings`, and `tests/test_telegram_menu_policy.py` asserts that entry-level shape. Make `_opted_out` read the settings path (and the legacy `config` path), keeping or explicitly retiring the entry-level form.
- Acceptance: With `settings.apply_runtime_defaults: false` and user-restored approval values, `verify_runtime_defaults()` returns no drift and finalize does not fail that profile; with the opt-out absent or `true`, drift is still reported. Loading behavior is unchanged.
- Checks: Failing focused regression first in the existing policy tests; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No upstream Hermes edits, profile configuration changes or push.
- Current evidence: Reproduced offline: with `settings.apply_runtime_defaults: false` and restored approval values, `verify_runtime_defaults()` reported `approvals.mode` and other paths as drift, which finalize turns into `Profile settings not healed`. `_opted_out` now mirrors Hermes' `get_config` (`settings`, then legacy `config`); the entry-level form, which the loader never honored, is retired and its old assertion inverted. The same ineffective entry-level opt-out in `update_bundle_native.py`'s disposable registration probe now uses `settings` via `PROBE_CONFIG`. Three new regressions in `tests/test_telegram_menu_policy.py` failed before the fix.
- Checks run: `python3 scripts/check.py --timeout 300` passed offline: 406/571/197/8 tests in 4 directories, 1 skipped, 8 modules excluded; `git diff --check` clean. The longer per-directory timeout reflects host load, not a test change. Self-reviewed.
- Closure: Offline verification only; no installed profile was re-finalized and no native registration probe was run.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-034 — Make install-omh report when OMH did not take the memory provider slot

- [x] TOOLSET-034 — Make install-omh report when OMH did not take the memory provider slot
- Status: done
- Goal: OMH-SETUP-REPORT — Setup output must not imply OMH memory is active when it is off.
- Sources: [memory guide](docs/memory.md), [`install-omh.py`](install-omh.py), pinned OMH `src/install/config_adapter.py` `set_memory_provider` (refuses to replace another `memory.provider` and reports "clear it first" without failing setup).
- Scope: Found during external-claim verification (source inspection, not a reproduced run). When a profile already selects another memory provider, OMH setup leaves it in place and still succeeds, and `install-omh.py` prints `OMH setup: <profile>` without checking. After setup, read the profile's `memory.provider` and report profiles where it is not `omh` as memory-off, without changing the provider.
- Acceptance: A profile with another provider selected is reported as OMH memory off with the provider name and the clear-it-first remedy; a profile that selected OMH reports as before; no provider is overwritten.
- Checks: Failing focused offline regression with a fake OMH runner first; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No upstream OMH or Hermes edits, real profile writes or push.
- Current evidence: After each profile's setup and store binding, `install-omh.py` rereads `memory.provider` with its existing bounded reader and prints `OMH setup: <profile> (memory off: memory.provider is <name>; run `hermes [-p <profile>] memory off`, then rerun setup to use OMH memory)`, `(memory off: memory.provider is not set)`, or a plain line when OMH holds the slot; an unreadable config after setup is reported as unverified instead of failing. The exit status and the provider are unchanged. Four regressions in `tests/test_install_omh.py` (fake OMH can now claim the slot); the two memory-off cases failed before the change. Memory and troubleshooting docs and CHANGELOG updated.
- Checks run: `python3 scripts/check.py --timeout 300` passed offline: 410/572/197/8 tests in 4 directories, 1 skipped, 8 modules excluded; `git diff --check` clean. Self-reviewed.
- Closure: Offline only; no real profile was set up and upstream OMH's refusal was confirmed by source inspection of the pinned commit.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-035 — Make the Cron Autowork Codex adapter explicit-only like the other adapters

- [x] TOOLSET-035 — Make the Cron Autowork Codex adapter explicit-only like the other adapters
- Status: done
- Goal: PORTABLE — Installing the Codex package must not let any adapter run implicitly.
- Sources: [cross-host contract](docs/cross-host.md#codex), `adapters/skills/*/agents/openai.yaml` (10 of the 11 adapter skills set `policy.allow_implicit_invocation: false`), codex-cli 0.162.1 `skills/src/model.rs` (a missing policy defaults to implicit invocation allowed), [portable package test](tests/test_portable_package.py).
- Scope: Found during claim-by-claim docs verification. `adapters/skills/cron-autowork/` has no `agents/openai.yaml`. Add one matching the sibling adapters' explicit-only policy, add a portable-package regression that every adapter skill ships an explicit-only policy, and then drop the Cron Autowork exception from docs/cross-host.md.
- Acceptance: Every directory under `adapters/skills/` that contains `SKILL.md` has `agents/openai.yaml` with `allow_implicit_invocation: false`; the new regression fails before the file is added; the npm package file list still includes it.
- Checks: `python3 scripts/check.py`; `node --test tests/portable_pi.test.mjs`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No Codex marketplace publication, live Codex install or push.
- Current evidence: Added `adapters/skills/cron-autowork/agents/openai.yaml` (`policy.allow_implicit_invocation: false`, identical to the sibling adapters) and `test_every_codex_adapter_is_explicit_only` in `tests/test_portable_package.py`, which failed only for cron-autowork before the file existed. `npm pack --dry-run` includes the new file. docs/cross-host.md no longer carries the exception; CHANGELOG updated.
- Checks run: `python3 scripts/check.py` passed offline: 411/572/201/8 tests in 4 directories, 1 skipped, 8 modules excluded; `node --test tests/portable_pi.test.mjs` 3 passed; `git diff --check` clean. Self-reviewed.
- Closure: Offline only; no live Codex install was run.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-024 — Reject malformed goal source fields before task selection

- [x] TOOLSET-024 — Reject malformed goal source fields before task selection
- Status: done
- Goal: BACKLOG — Keep accepted-source identity structurally trustworthy for backlog consumers.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [task-index contract](docs/project.md#interface-and-state-contract), [validator](skills/docs-sync/scripts/goals.py), [regressions](skills/docs-sync/scripts/test_goals.py).
- Scope: Reject non-string goal source fields in the existing ledger shape validator and add focused offline API/CLI regressions. Preserve supported string sources and additional metadata; document the diagnostic if needed.
- Acceptance: Object, list, Boolean and numeric source fields cannot validate, normalize or yield eligible tasks. Diagnostics identify the affected goal field without leaking supplied values or traceback. Existing valid string sources, version checks and duplicate-key refusals remain passing. Refused CLI mutations leave ledger/TODO bytes unchanged.
- Checks: `uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s skills/docs-sync/scripts -p test_goals.py`; repeat for test_milestone_focus.py and test_goal_concurrency.py; `git diff --check`. Independently review the exact candidate before coordinator local integration.
- Dependencies: None.
- Ownership: toolset coordinator and one isolated native worker; coordinator owns canonical ledger and integration.
- Exclusions: No upstream edits, deployment, publication, profile/job/settings changes, live/model qualification, acceptance weakening or foreign edits.
- Decision: Use the existing shape validator, not new path-format policy. This is a routine agent decision under authorized repository maintenance, not historical user approval. Current reproduction: a nonempty object source returns no shape/semantic errors and an eligible task despite the source-heading contract.
- Delivery: Candidate `fffe414` (branch `autowork/TOOLSET-024`) was integrated as `3389de1` with an identical patch (same `git patch-id`). Its independent review approved the exact five-file slice with no findings (coordinator receipts `occurrence-977177-closeout.json` and `occurrence-1285855-closeout.json`; review transcript `deleg_38441a22`).
- Closure evidence (2026-10-15, on `main` at 5db9ccf): `uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s skills/docs-sync/scripts -p` for test_goals.py, test_milestone_focus.py and test_goal_concurrency.py all passed. A CLI probe with object, list, Boolean and numeric sources made `validate`, `next --json` and `task T1 in_progress` exit 1 with a diagnostic naming `source`, never printed the supplied sentinel value or a traceback, and left goals.json and TODO.md byte-identical; a string source still validated and selected T1. The full offline gate on the integrated code passed in the coordinator receipt (403/571/201/8). Offline only; no live qualification is implied.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-040 — Report active sessions in other checkouts separately from idle sessions

- [x] TOOLSET-040 — Report active sessions in other checkouts separately from idle sessions
- Status: done
- Goal: STARTUP — Start useful implementation sooner with less preparation.
- Sources: [writer classification](skills/autowork/scripts/task_execution.py), [ownership rules](skills/autowork/SKILL.md#ownership-limits-and-continuation), [task execution tests](skills/autowork/scripts/test_task_execution.py).
- Scope: Found while running Autowork from an isolated worktree: `execute()` and `--writers` listed every non-blocking session as `idle_sessions`, including an active session in another checkout (evidence "running commands"), which an integrator could read as safe to merge there. Report idle sessions and active or unknown-activity sessions elsewhere under separate keys, and update the skill wording that names them.
- Acceptance: A session idle past the threshold appears only under `idle_sessions`; an active session that touches only another checkout appears only under `other_checkout_sessions`; blocking behavior is unchanged; `--writers` from the other checkout still reports that session as blocking.
- Checks: `python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py`; `python3 scripts/check.py`; `git diff --check`; independent review.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to which sessions block, no process signalling, no push.
- Current evidence: Commit e881deb adds `nonblocking_sessions()` and the regression in `test_active_session_blocks_only_its_checkout_and_names_an_isolated_branch` (it fails before the split: the active session was listed under `idle_sessions`). 42 task-execution tests and the full offline check passed; independent review APPROVE.
- Closure: Offline; no live fleet run.



<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-041 — Treat a missing Autowork progress journal as a normal first run

- [x] TOOLSET-041 — Treat a missing Autowork progress journal as a normal first run
- Status: done
- Goal: STARTUP — Start useful implementation sooner with less preparation.
- Sources: [journal guidance](skills/autowork/references/blockers-and-history.md), [state and recovery](skills/autowork/references/state-and-recovery.md).
- Scope: Gateway logs on 2026-10-14 show 44 failed reads of `<profile>/autowork/state.json` across three profiles, where no run had written the journal; it exists in only 3 of 9 profiles. Say the journal may be absent, check for it instead of reading blindly, and create it when the first run records progress.
- Acceptance: The guidance tells agents to test for the file before reading, treats absence as a first run (not lost continuity or an error), and requires the first recorded run to create it. No other journal semantics change.
- Checks: Read back both references; `python3 skills/docs-sync/scripts/docs.py check .`; `python3 scripts/check.py`; `git diff --check`; independent review.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No new state file, schema or helper; no profile state edits.
- Current evidence: Commit 0a4d45e edits both references; the pinned phrase in `test_picker_policy` still holds. Full offline check passed; independent review APPROVE.
- Closure: Guidance only; agent behavior in live runs not yet observed.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-042 — End the archive file with one newline after a closeout

- [x] TOOLSET-042 — End the archive file with one newline after a closeout
- Status: done
- Goal: ARCHIVAL — Integrate archival and reconcile the rendering contract.
- Sources: [archiver](skills/docs-sync/scripts/todo_archive.py), [archive contract](skills/docs-sync/references/todo-archive.md), [archive tests](skills/docs-sync/scripts/test_todo_archive.py), [supersession tests](skills/docs-sync/scripts/test_supersession.py).
- Scope: A task block ends with the blank line that separates it from the next heading, and `archive_completed()` appends the block verbatim, so the archive ends with an extra blank line and `git diff --check` fails after an ordinary closeout (reproduced closing TOOLSET-040/041 on 2026-10-14). Decided approach: treat trailing blank lines as a separator, not task content. Archive `block.rstrip(newlines) + newline` (preserving CRLF), use that same trimmed block for the conservation and retry checks, and update the archive contract wording and the 12 exact-byte assertions in `test_todo_archive.py` and `test_supersession.py` to the trimmed form.
- Acceptance: After archiving any closed task, the archive ends with exactly one newline and `git diff --check` passes; task content bytes (excluding trailing blank lines) are preserved, including CRLF; retry and render remain byte-stable; live TODO.md is unchanged apart from the moved block.
- Checks: `python3 -m unittest discover -s skills/docs-sync/scripts -p 'test_todo_archive.py'`; same for `test_supersession.py` and `test_goals.py`; `python3 scripts/check.py`; `git diff --check` after a fixture closeout.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to which tasks are archived or to archive ordering; no push.
- Current evidence: `prepare()` in `todo_archive.py` (the archiver; there is no `archive_completed()`) now archives each body as `rstrip` of line breaks plus one line break of its own style, and uses that trimmed block for conservation and retry, which still recognizes bodies archived earlier with their separator. Updated the 12 exact-byte assertions in `test_todo_archive.py`/`test_supersession.py` through an `archived_form()` helper, plus one in `tests/test_workflow_cycle.py`; added LF/CRLF one-newline, real-Git `git diff --check` and legacy-retry regressions (the first two failed against the old code). Archive contract and CHANGELOG updated. This closeout itself archived with no manual trim.
- Checks run: `python3 scripts/check.py` passed offline: 411/572/204/8 tests in 4 directories, 1 skipped, 8 modules excluded; `git diff --check` clean after this closeout. Self-reviewed.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-043 — Stop loose checklist lines and dependency prose from refusing runnable Autowork tasks

- [x] TOOLSET-043 — Stop loose checklist lines and dependency prose from refusing runnable Autowork tasks
- Status: done
- Goal: RELIABILITY-2026-10 — Autowork selects the runnable task the ledger and `goals.py next` agree on.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [task_execution.py](skills/autowork/scripts/task_execution.py) duplicate-ID check and dependency parsing
- Scope: A checklist line without a task ID anywhere in TODO.md (for example `- [ ] Add dark mode` under a Backlog heading) makes `owner_cycle.py` return `ACTION_REQUIRED: duplicate TODO task IDs`; `Dependencies: None. <prose>` is read as unresolved dependencies. Limit the duplicate check to executable task IDs, and treat a Dependencies field whose first clause is `None` as having none.
- Acceptance: With either fixture change, `owner_cycle.py REPO` returns the same `READY` selection as the unmodified fixture; genuine duplicate task IDs and real unresolved dependencies are still refused.
- Checks: New regressions in `skills/autowork/scripts/test_task_execution.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to ledger-mode dependency semantics beyond the `None` prefix; no edits to consumer repositories.
- Current evidence: Implemented in `57cc6c0` (isolated worktree, reviewed by the coordinator before integration). The duplicate-ID refusal now considers only executable IDs (ledger tasks, or Now/Next without a ledger, plus `--tasks`), and a Dependencies field whose first clause is `None` has no dependencies. Regressions `test_loose_checklist_lines_without_task_ids_do_not_refuse_selection` and `test_none_dependency_followed_by_prose_is_no_dependency` failed before the fix; genuine duplicates and real unresolved dependencies are still refused. The planner's original fixture repro now returns `READY` for both cases.
- Checks run: integrated `main` passed `python3 scripts/check.py` (415/575/207/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed) and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-044 — Detect the installed hermes launcher as a live writer

- [x] TOOLSET-044 — Detect the installed hermes launcher as a live writer
- Status: done
- Goal: RELIABILITY-2026-10 — A live Hermes session in the checkout blocks Autowork like other agents.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [task_execution.py](skills/autowork/scripts/task_execution.py) `is_agent`
- Scope: The installed launcher runs `python3 -I -c '<launcher … hermes_cli.main …>' -p PROFILE`, which `is_agent` does not recognize, so `--writers` reports `CLEAR` beside an active Hermes chat. Recognize `hermes_cli` in the `-c` program text or `-m` module argument.
- Acceptance: A fixture process with that argv and its cwd in the repo is reported as an agent session (active or idle by the existing rules); unrelated Python processes are still ignored.
- Checks: New regression in `skills/autowork/scripts/test_task_execution.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to idle thresholds or to Autowork-command blocking; never signal or kill processes.
- Current evidence: Implemented in `646b040` (isolated worktree, reviewed by the coordinator before integration). `is_agent` also inspects the interpreter's own options and recognizes `hermes_cli` in `-c` program text or a `-m hermes_cli…` module. Regression `test_installed_hermes_launcher_is_an_agent_session` (direct and real-process `--writers` checks) failed before the fix. Known limit: an interpreter option taking a value (`-X`, `-W`) before `-c` is not scanned past; the installed launcher uses only `-I`.
- Checks run: integrated `main` passed `python3 scripts/check.py` (415/575/207/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed) and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-045 — Honor the runtime-defaults opt-out during setup

- [x] TOOLSET-045 — Honor the runtime-defaults opt-out during setup
- Status: done
- Goal: RELIABILITY-2026-10 — Setup never reverses a profile's documented runtime-policy opt-out.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [install-plugins.sh](install-plugins.sh) `apply_bundle_defaults`, [setup_preflight.py](setup_preflight.py), [runtime_defaults.py](runtime_defaults.py) `_opted_out`
- Scope: With `plugins.entries.hermes-toolset.settings.apply_runtime_defaults: false`, setup (full and `--bundle-only`) still runs `config set approvals.mode off` and the other policy keys. Skip the policy keys for opted-out profiles using the same settings-then-legacy-config rule as `_opted_out`, and say so in the preflight plan.
- Acceptance: For an opted-out fixture profile, setup issues no approval, injection or skill-list `config set` and the plan reports the skip; other profiles are unchanged.
- Checks: New regression in the existing setup tests (`tests/test_complete_setup.py` or `tests/test_preflight.py`); `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to plugin-load behavior; no real profile writes.
- Current evidence: Implemented in `782ccfc` (isolated worktree, reviewed by the coordinator before integration). Setup reads the profile config with `runtime_defaults.setup_opted_out` (the same settings-then-legacy rule as `_opted_out`), skips all six policy keys for an opted-out profile, says so in the preflight plan and install output, and refuses rather than guesses when the opt-out cannot be read without PyYAML. Regressions in `tests/test_install_plugins.py`, `tests/test_preflight.py` and `tests/test_telegram_menu_policy.py` failed before the fix; installation, reference and README docs updated.
- Checks run: integrated `main` passed `python3 scripts/check.py` (415/575/207/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed) and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-046 — Keep the plugin loading when one native skill copy cannot be provisioned

- [x] TOOLSET-046 — Keep the plugin loading when one native skill copy cannot be provisioned
- Status: done
- Goal: RELIABILITY-2026-10 — One incomplete native skill folder never removes every bundled command.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [__init__.py](__init__.py) `register`, [install_skills.py](install_skills.py)
- Scope: `register()` raises when `install()` reports any failure, for example a profile `skills/engineering/` folder without `SKILL.md`, so no command, skill or `/toolset` registers. Log the provisioning messages as a warning and continue registration; plugin commands load skills by qualified name, not from native copies.
- Acceptance: With an incomplete same-named native folder, registration completes, the failure is logged, and other missing native skills are still provisioned.
- Checks: New regression in `tests/test_plugin.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No overwriting of the incomplete user folder.
- Current evidence: Implemented in `e761bca` (isolated worktree, reviewed by the coordinator before integration). `register()` logs incomplete native provisioning as a warning and continues; the incomplete user folder is preserved and other skills are provisioned. Regression `test_incomplete_native_folder_is_logged_and_registration_continues` failed with the RuntimeError before the fix; installation doc updated. `doctor` does not check native skill copies, so the plugin-load warning is the only signal.
- Checks run: integrated `main` passed `python3 scripts/check.py` (415/575/207/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed) and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-047 — Parse CRLF and trailing-space section headings and never delete content under a legacy coverage heading

- [x] TOOLSET-047 — Parse CRLF and trailing-space section headings and never delete content under a legacy coverage heading
- Status: done
- Goal: RELIABILITY-2026-10 — TODO.md line endings and legacy layouts never break selection or lose content.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [goals.py](skills/docs-sync/scripts/goals.py) section parsing and coverage rendering
- Scope: Level-2 headings are captured with a trailing `\r` or space, so CRLF TODO files fail `init` and backlog checks with `section Now\r differs`. `render` replaces a marker-less legacy coverage section up to the next level-1 or level-2 heading, deleting level-3 subsections such as a decisions log. Trim heading text; stop the replaced span at any heading or refuse when it holds more than the coverage table.
- Acceptance: A CRLF copy of a valid fixture initializes and selects like the LF one; a `Now ` heading with a trailing space matches `Now`; rendering a legacy coverage section keeps following level-3 content byte-identical.
- Checks: New regressions in `skills/docs-sync/scripts/test_goals.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to the marker-delimited coverage block format.
- Current evidence: Implemented in `d3acb6a`, `c1a509e` (isolated worktree, reviewed by the coordinator before integration). `task_bodies` trims `\r` and trailing blanks from level-2 section names, and a marker-less legacy coverage section is replaced only up to the next heading of any level. `HeadingLineEndingTests` (CRLF parity across init/validate/next/backlog-check/bootstrap-order, trailing-space headings, level-3 content kept) failed before the fix. Known limit: the generated coverage block is still written with LF lines in a CRLF file.
- Checks run: integrated `main` passed `python3 scripts/check.py` (415/575/207/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed) and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-048 — Report finished or killed chat updates correctly and accept a symlinked Hermes home

- [x] TOOLSET-048 — Report finished or killed chat updates correctly and accept a symlinked Hermes home
- Status: done
- Goal: RELIABILITY-2026-10 — `/toolset update status` reflects the real updater state.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [bundle.py](bundle.py) `start_update`, `update_status`
- Scope: The gateway never reaps the chat-started updater, so `os.kill(pid, 0)` succeeds on the zombie and status says starting/running forever; a symlinked Hermes home is refused only in chat. Reap or detect zombies before liveness checks and resolve the home before the symlink check.
- Acceptance: A finished, refused or killed child is reported from its receipt or as stopped; a symlinked home starts the update as the terminal command does.
- Checks: New regressions in `tests/test_bundle.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to the updater itself.
- Current evidence: Implemented in `f5da55c` (isolated worktree, reviewed by the coordinator before integration). A new `updater_alive()` reaps the gateway's own exited child, treats `/proc` zombie states as dead and a `PermissionError` as alive, and the home is resolved before the state-directory symlink check. Four regressions in `tests/test_bundle.py` (refused child shows its latest receipt, SIGKILLed child shows stopped, other-user pid still running, symlinked home starts) failed before the fix; a symlinked state directory is still refused. Zombie tests need Linux `/proc`.
- Checks run: integrated `main` passed `python3 scripts/check.py` (437/575/209/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed), `docs.py check` and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-049 — Accept Hermes-written YAML and stray profile symlinks during setup and update

- [x] TOOLSET-049 — Accept Hermes-written YAML and stray profile symlinks during setup and update
- Status: done
- Goal: RELIABILITY-2026-10 — Valid Hermes configs and leftover profile entries never block setup.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [install-omh.py](install-omh.py) `config_values`, [scripts/preflight_config.py](scripts/preflight_config.py), [setup_bundle.py](setup_bundle.py) `live_profiles`
- Scope: Indentless lists (`enabled:` followed by `- omh` at the same indent), `memory: {}`, a UTF-8 BOM and empty sections are rejected; a symlink under `profiles/` that Hermes ignores (tombstoned or invalid name) aborts setup and update. Accept those shapes on non-target keys and apply the symlink refusal after the profile filters.
- Acceptance: Each recorded fixture passes preflight and the OMH plan; real target-key conflicts and live shared/symlinked profiles are still refused.
- Checks: New regressions in `tests/test_install_omh.py` and `tests/test_preflight.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: Keep the readers bounded; no PyYAML bootstrap dependency.
- Current evidence: Implemented in `22107d8`, `2e0d110` (isolated worktree, reviewed by the coordinator before integration). `install-omh.py` strips a BOM, keeps indentless `- item` lines under their key and accepts `key: {}` on non-target keys; `preflight_config.py` treats empty sections and entries as empty mappings; `live_profiles` refuses only symlinks that would be live profiles. Regressions in `tests/test_install_omh.py`, `tests/test_preflight.py` and `tests/test_complete_setup.py` failed before the fixes, and target-key lists or `{}`, duplicates and live symlinked profiles are still refused; each recorded bug-hunt fixture now passes.
- Checks run: integrated `main` passed `python3 scripts/check.py` (437/575/209/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed), `docs.py check` and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-050 — Make Telegram menu healing robust to .env comments, odd chat IDs and per-chat failures

- [x] TOOLSET-050 — Make Telegram menu healing robust to .env comments, odd chat IDs and per-chat failures
- Status: done
- Goal: RELIABILITY-2026-10 — Every configured owner and home chat is checked once per update.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [update_bundle.py](update_bundle.py) `read_env`, `heal_chat_menus`, [telegram_menu_policy.py](telegram_menu_policy.py) `chat_ids`, `stale_chat_menus`
- Scope: Inline ` # comments` stay in unquoted values (corrupting the token and chat IDs), `--5` or non-ASCII digits raise, and the first chat whose `getMyCommands` fails stops healing for the rest. Strip inline comments as dotenv does, accept only `-?[0-9]+`, and handle each chat independently, reporting failures.
- Acceptance: The recorded `.env` fixtures yield the dotenv values; a failing chat is reported while the remaining chats are still healed.
- Checks: New regressions in `tests/test_telegram_menu_policy.py` and `tests/test_update_bundle.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No live Bot API calls in tests.
- Current evidence: Implemented in `77ec9a5` (isolated worktree, reviewed by the coordinator before integration). `read_env` reads values as python-dotenv does (quoted content, inline ` #` comments dropped), `chat_ids` accepts only `-?[0-9]+`, and `stale_chat_menus` handles each chat independently, recording failures so `heal_chat_menus` still reports cleared chats and adds masked `failed` chats. Six regressions in `tests/test_telegram_menu_policy.py` and `tests/test_update_bundle.py` failed before the fix; installation doc updated. Escape sequences in double-quoted values are not decoded.
- Checks run: integrated `main` passed `python3 scripts/check.py` (437/575/209/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed), `docs.py check` and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-051 — Remove docs.py false positives for footnotes, commented-out links and home-relative scripts

- [x] TOOLSET-051 — Remove docs.py false positives for footnotes, commented-out links and home-relative scripts
- Status: done
- Goal: RELIABILITY-2026-10 — `docs.py check` reports only real documentation defects.
- Sources: [harvest plan](docs/project.md#reliability-bug-harvest-2026-10-15), [docs.py](skills/docs-sync/scripts/docs.py)
- Scope: Footnote definitions (`[^1]: text`) parse as reference links, HTML-commented links are checked, and `python3 ~/...` script paths are reported missing. Exclude footnotes, mask HTML comments before scanning and skip `~` paths.
- Acceptance: Each recorded fixture checks clean while real broken links and missing repository scripts are still reported.
- Checks: New regressions in `skills/docs-sync/scripts/test_docs_manifest.py`; `python3 scripts/check.py`; `git diff --check`
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No network link checking.
- Current evidence: Implemented in `ada728c` (isolated worktree, reviewed by the coordinator before integration). Footnote definitions are no longer reference links, HTML comments are masked before scanning, `~` script paths are skipped, code-span headings keep their underscores in anchors, and single-quoted link titles are checked. Two regressions in `test_docs_manifest.py` failed before the fix while real broken links and missing scripts are still reported; `docs.py check` on this repository prints ok.
- Checks run: integrated `main` passed `python3 scripts/check.py` (437/575/209/8 offline tests, 1 skipped, 8 modules excluded), `node --test tests/portable_pi.test.mjs` (3 passed), `docs.py check` and `git diff --check`. Offline only.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-052 — Vendor the pinned UI Taste skill into skills/ui-taste

- [x] TOOLSET-052 — Vendor the pinned UI Taste skill into skills/ui-taste
- Status: done
- Goal: UI-TASTE — Hermes profiles get `/ui-taste` (Telegram `/ui_taste`) offline from a reproducible, licensed snapshot.
- Sources: [UI Taste plan](docs/project.md#vendored-ui-taste-skill), upstream https://github.com/uizze/uizze/tree/afd703a14a5db5f2fe6c2860badbe811058aa9e5/skills/ui-taste, domain index https://uizze.sh/.well-known/skills/index.json, precedent [Impeccable pin](skills/impeccable/UPSTREAM.json) and [its test](tests/test_impeccable_bundle.py).
- Scope: In a scratch directory run `git clone https://github.com/uizze/uizze.git` and, for each of the 16 paths from `git ls-tree -r --name-only afd703a14a5db5f2fe6c2860badbe811058aa9e5 skills/ui-taste`, write `git show <revision>:<path>` byte-for-byte to `skills/ui-taste/<relative path>`. Add `skills/ui-taste/UPSTREAM.json` with `repository`, `revision`, `path` (`skills/ui-taste`), `version` (`0.2.0`), `license` (`Apache-2.0`), `sha256` for every vendored file, and a `domain_check` note (2026-10-15: uizze.sh copy identical on the 13 content files; `MANIFEST.json`, `MODIFICATIONS.md`, `CHECKSUMS.sha256` differ as packaging metadata). Add `tests/test_ui_taste_bundle.py` and document the skill: dependencies table row, licensing bullet and refresh procedure in docs/dependencies.md, a workflows.md command row, README mention beside Impeccable, CHANGELOG entry, and `skills/ui-taste/UPSTREAM.json` in the `dependencies` role's `covers` in docs/roles.json.
- Acceptance: `skills/ui-taste/` holds exactly the 16 upstream files plus UPSTREAM.json, each byte-identical to the pinned commit; upstream `CHECKSUMS.sha256` verifies; no file is executable; LICENSE and NOTICE are present. Plugin load registers `/ui-taste`, `hermes-toolset:ui-taste` and provisions the native copy (existing auto-discovery; no registration code change expected). Bundled Impeccable is unchanged.
- Checks: `python3 -m unittest discover -s tests -p test_ui_taste_bundle.py` (pinned revision, exact file set, sha256 per file, upstream checksums, LICENSE/NOTICE, no executable bit, `name: ui-taste` frontmatter); `python3 -m unittest discover -s tests -p 'test_impeccable_bundle.py'` (clean-profile provisioning, extend it to assert `skills/ui-taste/SKILL.md`); `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No edits to upstream files, no `npx` or network fetch at install/setup/update time, no Uizze MCP configuration, no other Uizze skills, no Telegram menu priority change, no push.
- Current evidence: The 16 files at Uizze commit `afd703a` were written byte-for-byte with `git show` into `skills/ui-taste/` (mode 0644) with UPSTREAM.json (revision, path, version 0.2.0, Apache-2.0, per-file sha256, domain cross-check). `tests/test_ui_taste_bundle.py` (pinned exact file set and hashes, upstream CHECKSUMS.sha256, LICENSE/NOTICE, no executable bit, `name: ui-taste`, clean-profile provisioning) failed before vendoring; spot checks against the live uizze.sh copy matched. The plugin's `_discover_skills()` registers it as `ui-taste`. `tests/test_doctor_modes.py`'s registered-skill fixture gained `ui-taste`, since doctor derives expected skills from `skills/`. Docs: dependencies (pin, licensing, refresh procedure), workflows command row, README, CHANGELOG, roles.json covers.
- Checks run: `python3 scripts/check.py` passed offline (440/575/209/8 tests, 1 skipped, 8 modules excluded); `docs.py check` ok; `git diff --check` clean. Offline only; no live Hermes load.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-060 — Vendor and adapt the Beautify GitHub README skill

- [x] TOOLSET-060 — Vendor and adapt the Beautify GitHub README skill
- Status: done
- Goal: README-DESIGN — Vendor the README design skill and use it on this README.
- Sources: [accepted plan](docs/project.md#readme-design-skill-2026-10-15), [engineering vendor pattern](skills/engineering/SKILL.md), [engineering provenance](skills/engineering/UPSTREAM.json), [portable package test](tests/test_portable_package.py).
- Scope: Add `skills/beautify-github-readme/` with a toolset adapter `SKILL.md`, the pinned upstream skill under `upstream/` (`SKILL.md` renamed `PROTOCOL.md`; references, scripts and LICENSE byte-exact), `UPSTREAM.json` with repository, revision, license, file hashes, transform and exclusions, and a hash/licence test. Add a Codex/Pi adapter with an explicit-only `agents/openai.yaml`. Document the command, licensing and changelog.
- Acceptance: The skill registers as `/beautify-github-readme` (`/beautify_github_readme` in Telegram) without a second nested skill; every vendored file matches its recorded hash; the adapter states the toolset rules from the accepted plan; the bundled audit script runs from its vendored path; existing bundle, plugin, install and portable-package tests pass.
- Checks: `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; `python3 skills/beautify-github-readme/upstream/scripts/audit_readme.py README.md`; `git diff --check`; independent review.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No upstream edits, showcase images, image generation, publication or push.
- Current evidence: Commits b15bbc7 and 5a9c044. Twelve upstream files pinned byte-exact at d6562a5 with sha256 in UPSTREAM.json (modes match); only the adapter registers; Codex/Pi adapters added (12 skills, 26 Pi commands). Full offline check, Pi package test, docs.py check and the vendored audit passed. Independent review verified the bytes against GitHub and requested two fixes (stale cross-host counts, scope wording), both applied.
- Closure: Offline; live Codex/Pi discovery not re-run.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-053 — Expose UI Taste on Codex and Pi

- [x] TOOLSET-053 — Expose UI Taste on Codex and Pi
- Status: done
- Goal: UI-TASTE — Codex and Pi users reach the same vendored skill explicitly.
- Sources: [UI Taste plan](docs/project.md#vendored-ui-taste-skill), [Impeccable adapter](adapters/skills/impeccable/SKILL.md), [Pi extension](adapters/pi.mjs), [portable tests](tests/test_portable_package.py), [Pi tests](tests/portable_pi.test.mjs), [cross-host guide](docs/cross-host.md).
- Scope: Add `adapters/skills/ui-taste/SKILL.md` (frontmatter `name: ui-taste`, modeled on the Impeccable adapter, pointing to `../../../skills/ui-taste/SKILL.md` under the host contract) and `adapters/skills/ui-taste/agents/openai.yaml` with `policy.allow_implicit_invocation: false`. Add `ui_taste: ['ui-taste', 'Improve UI taste with Uizze playbooks']` to the workflows map in adapters/pi.mjs. Update the expected adapter set in tests/test_portable_package.py, the skill count 11→12 and command count 25→26 in tests/portable_pi.test.mjs, and the current-fact counts and command list in docs/cross-host.md (leave its dated receipt unchanged).
- Acceptance: Portable discovery exposes `ui-taste` explicit-only in Codex; Pi registers `/ui_taste` passing literal arguments; `npm pack --dry-run` includes the adapter and the vendored skill; all existing portable guarantees still hold.
- Checks: `python3 -m unittest discover -s tests -p test_portable_package.py`; `node --test tests/portable_pi.test.mjs`; `npm pack --dry-run --json`; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-052.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No Codex marketplace publication, live Codex or Pi install, or push.
- Current evidence: Added `adapters/skills/ui-taste/SKILL.md` (host contract, bundled guidance, optional MCP only through an existing host connection) and `agents/openai.yaml` with `allow_implicit_invocation: false`, plus the Pi command `ui_taste`. The updated portable tests (adapter set with `ui-taste`; Pi 12 skills and 26 commands; `/ui_taste` routes literal arguments) failed before the change. `npm pack --dry-run` ships the adapter and all 17 vendored files. docs/cross-host.md now lists 12 skills and `/ui_taste` and notes that its live Codex/Pi validation predates UI Taste.
- Checks run: `python3 scripts/check.py` passed offline (440/575/209/8 tests, 1 skipped, 8 modules excluded); `node --test tests/portable_pi.test.mjs` 3 passed (including the packed-archive install test); `docs.py check` ok; `git diff --check` clean. No live Codex or Pi install was run.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-061 — Give this README a project-native visual refresh

- [x] TOOLSET-061 — Give this README a project-native visual refresh
- Status: done
- Goal: README-DESIGN — Vendor the README design skill and use it on this README.
- Sources: [accepted plan](docs/project.md#readme-design-skill-2026-10-15), [README](README.md), [skill adapter](skills/beautify-github-readme/SKILL.md).
- Scope: README mode, visual refresh: keep the current information architecture and every safety statement, add a pure-SVG hero built from the project's real plan → queue → execute loop and a workflow diagram under `assets/readme/`, with alt text and light/dark legibility.
- Acceptance: The first screen states the value and shows the real loop; SVGs use system fonts, no scripts or `foreignObject`, a 1200-unit viewBox and readable text at 900 px; the README still reads correctly with images off; the upstream audit script and `docs.py check` pass; no claim is added that lacks evidence.
- Checks: `python3 skills/beautify-github-readme/upstream/scripts/audit_readme.py README.md`; `python3 skills/docs-sync/scripts/docs.py check .`; rendered previews at 900 and 360 px reviewed; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-060.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No raster generation, GIF, attribution badge, showcase PR or push.
- Current evidence: Commit ff7196f adds assets/readme/hero.svg (3.6 KB) and workflow.svg (4.1 KB), pure SVG with system fonts and no scripts, foreignObject or remote resources, previewed at 900 and 360 px and in a GitHub-rendered page screenshot. The vendored audit (2 local images) and docs.py check passed; every safety statement was kept.
- Closure: Visual review by the coordinator; owner approval of the design not yet given.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-062 — Make the README audit catch dark-mode and reference-style images

- [x] TOOLSET-062 — Make the README audit catch dark-mode and reference-style images
- Status: done (2026-10-15). `skills/beautify-github-readme/scripts/audit_readme.py` reuses the upstream SVG checks and adds `srcset`, reference-style, root-relative and `<…>` handling; both adapters run it. Five new regressions failed first, then passed; `python3 scripts/check.py` 448/575 (1 skipped)/209/8, `node --test tests/portable_pi.test.mjs` 3 passed, `docs.py check` ok. Offline only.
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [review findings](docs/project.md#new-skill-review-2026-10-15), [adapter](skills/beautify-github-readme/SKILL.md), [vendored audit](skills/beautify-github-readme/upstream/scripts/audit_readme.py).
- Scope: Add a toolset `scripts/audit_readme.py` to the Beautify skill that reuses the upstream SVG checks and also audits `<source srcset>` candidates and reference-style images, resolves root-relative paths against the repository root and accepts `<…>` destinations; ignore images inside fenced code. Point the adapter (and its Codex/Pi wrapper) at it. Upstream bytes stay unchanged.
- Acceptance: A missing dark-mode `srcset` image, a missing or undefined reference-style image and a missing root-relative image each fail; existing root-relative and angle-bracket images pass; this README still passes.
- Checks: Failing-first fixture regressions in `tests/test_beautify_readme_vendor.py`, then `python3 scripts/check.py` and the Node package test.
- Dependencies: None.
- Exclusions: No edits to vendored upstream files; no network.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-063 — Put UI Taste behind a toolset adapter

- [x] TOOLSET-063 — Put UI Taste behind a toolset adapter
- Status: done (2026-10-15). The 16 pinned files moved byte-exact (git mv) to `skills/ui-taste/upstream/` with `SKILL.md` stored as `PROTOCOL.md`; a toolset `SKILL.md` (54-character trigger) adds design-skill precedence, read-only scheduled runs, paid-tool limits and verification rules; UPSTREAM.json, the Codex/Pi wrapper, dependency docs and CHANGELOG follow. Updated `tests/test_ui_taste_bundle.py` failed first (5), then passed; Hermes' skill linter reports no description-length warning; `python3 scripts/check.py` 450/575 (1 skipped)/209/8, Node 3 passed, `docs.py check` ok. Offline only: installed profiles keep their old native copy until `/toolset update` applies the move.
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [review findings](docs/project.md#new-skill-review-2026-10-15), [UI Taste plan](docs/project.md#vendored-ui-taste-skill), [Beautify layout](docs/project.md#readme-design-skill-2026-10-15).
- Scope: Move the 16 pinned files byte-exact to `skills/ui-taste/upstream/` with `SKILL.md` renamed `PROTOCOL.md`; add a toolset `SKILL.md` with a trigger-first description of at most 60 characters and the accepted rules (design-skill precedence, audit-only scheduled runs, paid Uizze tools only through an existing host connection); update `UPSTREAM.json`, the Codex/Pi wrapper, tests and the refresh procedure.
- Acceptance: Only the adapter registers as a skill; every upstream file matches its pinned hash and upstream's own checksums after the recorded rename; a clean profile receives the adapter and playbooks; Hermes' skill linter reports no description-length warning for `ui-taste`.
- Checks: Failing-first updates to `tests/test_ui_taste_bundle.py`, `python3 scripts/check.py`, the Node package test and `docs.py check`.
- Dependencies: None.
- Exclusions: No upstream text changes, MCP configuration or runtime fetches.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-065 — Ship a Claude Code plugin marketplace for the portable adapters

- [x] TOOLSET-065 — Ship a Claude Code plugin marketplace for the portable adapters
- Status: done (2026-10-15). `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (entry `source: ./`, `skills: [./adapters/skills/]`); all 13 adapters carry `disable-model-invocation: true`; host contract, cross-host install section, README, contributing and CHANGELOG updated. New package tests failed first for the frontmatter and host contract (the manifest test was written after the manifests); `python3 scripts/check.py` 455/575 (1 skipped)/209/8, Node 3 passed, `claude plugin validate . --strict` and the marketplace validation passed, and Claude Code 2.1.300 installed it into an isolated config listing exactly the 13 adapters, no hooks, agents or MCP servers, all 49 adapter links resolving in the cache copy, then uninstalled cleanly. Offline only: no model session ran a workflow.
- Goal: CLAUDE-CODE — Install the portable workflows in Claude Code.
- Sources: [Claude Code decision](docs/project.md#claude-code-package-2026-10-15), [install guide](docs/cross-host.md#claude-code).
- Scope: Marketplace and plugin manifests at the repository root that load only `adapters/skills/`, explicit-only adapters, tests and docs.
- Acceptance: A strict plugin validation passes; an isolated install lists exactly the 13 adapters and no root Hermes skills, hooks, agents or MCP servers; adapter links resolve in the installed copy.
- Checks: `tests/test_portable_package.py`, `python3 scripts/check.py`, `node --test tests/portable_pi.test.mjs`, `claude plugin validate . --strict`.
- Dependencies: None.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-069 — Run check.py test directories concurrently

- [x] TOOLSET-069 — Run check.py test directories concurrently
- Status: done
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [plan](docs/project.md#test-suite-optimization-method-2026-10-15), [check runner](scripts/check.py), [check runner tests](tests/test_check.py).
- Scope: Run the per-directory `unittest` subprocesses of `scripts/check.py` concurrently (default: one worker per directory, `--jobs N` to limit, `--jobs 1` keeps today's sequential behavior). Keep each directory's output contiguous and printed in the current directory order, keep the per-directory timeout and process-group kill, and keep the final summary line byte-identical in format. Document the option in docs/testing.md and the CHANGELOG.
- Acceptance: Three consecutive full runs pass with the default; wall time is measured before and after on the same machine (baseline 242 s on `75fb76f`) and recorded in the task evidence; output order and the summary format match `--jobs 1`; a timed-out directory still fails the run and is killed while others finish.
- Checks: the existing check-runner tests plus new ones for ordering, `--jobs 1` and timeout with concurrency; `python3 scripts/check.py` three times with `/usr/bin/time`; `python3 scripts/check.py --jobs 1`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to which tests run or to the excluded native modules; no parallelism inside a directory (left to TOOLSET-068's findings); no push.
- Current evidence: `scripts/check.py` submits each directory to a thread pool (`--jobs`, default one worker per directory, positive integers only) and prints each directory's buffered output in the original order; timeouts still kill the process group and fail only that directory. Four new tests in `tests/test_check.py` cover overlap with ordered output, `--jobs 1` parity, `--jobs` validation and a concurrent timeout; the first two failed before the change.
- Checks run: three default full runs passed in 174.8 s, 165.2 s and 164.0 s, and `--jobs 1` passed in 235.4 s, on the same machine as the 242 s baseline (`75fb76f`); the `CHECK`/summary lines of `--jobs 1` and the default are identical; `tests/test_check.py` 10 passed. Offline only.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-067 — Add the test-suite-optimization engineering protocol

- [x] TOOLSET-067 — Add the test-suite-optimization engineering protocol
- Status: done
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [plan](docs/project.md#test-suite-optimization-method-2026-10-15), [engineering adapter](skills/engineering/SKILL.md), [router](skills/engineering/scripts/route.py), [engineering cycle](skills/shared/ENGINEERING-CYCLE.md), [pinned TDD protocol](skills/engineering/upstream/skills/test-driven-development/PROTOCOL.md).
- Scope: Write `skills/engineering/local/test-suite-optimization/PROTOCOL.md` (about 80–120 lines, toolset-owned). It covers: (1) baseline first: wall time per check directory, the slowest tests, line and branch coverage with coverage.py per-test contexts (`--context=test` or `dynamic_context = test_function`), and a mutation score only when a tool is available from a disposable environment outside the repository; (2) candidate classes: exact duplicates, subsumed tests (same seam, assertions a subset of another test's), families to parametrize, slow fixtures or repeated setup, and low-value tests (no assertion, tautological expected values, implementation-coupled mocks); (3) keep rules: regression tests named for a bug or task, tests that alone cover a branch or kill a mutant, composed or cross-seam tests; (4) output: findings plus one TODO.md task per change with measured before values, never edits during the audit; (5) acceptance template: the changed tests pass, line/branch coverage and the mutation score of the touched modules do not drop, the time change is measured, and removed tests are listed with the test that covers them. Credit the tautological-assertion and public-seam ideas to Matt Pocock's MIT TDD skill without copying its text or its user-confirmation step. Extend `route.py` with a `LOCAL` map so `--protocol test-suite-optimization` returns `{name, path, source: "toolset"}` without a hash, and error unchanged for unknown names; local names cannot shadow pinned ones. Add the protocol to the engineering adapter's text and to the engineering cycle's need table ("Slow, redundant or low-signal tests"). Add a CHANGELOG entry.
- Acceptance: `route.py --protocol test-suite-optimization` prints the local path with `source: toolset`; every pinned protocol still routes with hash verification; a local name equal to a pinned name is rejected by a test; the protocol contains the five parts above and the anti-goals from the plan; Codex/Pi packages include the new file (`npm pack --dry-run`).
- Checks: `python3 -m unittest discover -s tests -p 'test_engineering*.py'` (add a routing test there if none fits); `python3 skills/engineering/scripts/route.py --protocol test-suite-optimization`; `npm pack --dry-run --json | grep test-suite-optimization`; `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No vendoring of Pocock's skill, no new slash command or Telegram menu entry, no repository dependency on a mutation tool, no edits to pinned upstream files, no push.
- Current evidence: `skills/engineering/local/test-suite-optimization/PROTOCOL.md` (89 lines) has the five parts (Measure first, Find candidates, Keep, Record tasks do not edit, Acceptance for each change) plus a Never list, credits the tautology and seam criteria to Matt Pocock's MIT `tdd` skill without copying text, and drops its user-confirmation step. `route.py` gained a `LOCAL` map: `--protocol test-suite-optimization` returns `source: toolset` without a hash; a local name equal to a pinned one and a local name in a phase `--domain` are rejected. The engineering adapter, Codex/Pi engineering adapter, engineering cycle table, dependencies table and CHANGELOG name it. The new routing test failed before the change.
- Checks run: `tests/test_engineering_vendor.py` 8 passed; `route.py --protocol test-suite-optimization` and `--protocol performance-optimization` both route; `npm pack --dry-run` and a temporary profile install include the protocol; `docs.py check` ok; `git diff --check` clean. Full `scripts/check.py` runs on the merged tree.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-070 — Advertise UI Taste and Beautify GitHub README in the Telegram menu

- [x] TOOLSET-070 — Advertise UI Taste and Beautify GitHub README in the Telegram menu
- Status: done (2026-10-15). Hermes' default 60-entry Telegram menu already held 67 built-ins, so both commands were registered but never listed. The user chose to add `ui_taste` and `beautify_github_readme` to the bundle's managed menu priority (`telegram_menu_policy.py`), displacing the last two built-ins (`memory`, `bundles`), which stay typeable. Updated menu tests failed first, then passed; Hermes' own `telegram_menu_commands` on a copy of the toolset profile config lists both right after the five workflows; `python3 scripts/check.py` 460/575 (1 skipped)/209/8; `docs.py check` ok. Offline only: running gateways re-apply the priority and push the menu on their next plugin load.
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [superseded menu call](docs/project.md#vendored-ui-taste-skill), [menu policy](telegram_menu_policy.py).
- Scope: Bundle menu priority, its tests and the docs that list advertised commands.
- Acceptance: A clean profile's priority ends with `ui_taste` and `beautify_github_readme`; user entries, mode and cap are preserved; Hermes' menu builder shows both.
- Checks: `tests/test_telegram_menu_policy.py`, `python3 scripts/check.py`, `docs.py check`.
- Dependencies: None.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-071 — Advertise Impeccable and LGTM in the Telegram menu

- [x] TOOLSET-071 — Advertise Impeccable and LGTM in the Telegram menu
- Status: done (2026-10-15). At the user's request `impeccable` and `lgtm` follow `ui_taste` and `beautify_github_readme` in the bundle's managed menu priority; at Hermes' 60-entry default the built-ins `voice`, `busy`, `memory` and `bundles` leave the menu and stay typeable. Updated menu tests failed first, then passed; Hermes' own `telegram_menu_commands` on a copy of the toolset profile config lists all four right after the five workflows; `python3 scripts/check.py` passed; `docs.py check` ok.
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [menu policy](telegram_menu_policy.py), [superseded menu call](docs/project.md#vendored-ui-taste-skill).
- Scope: Bundle menu priority, its tests and the docs that list advertised commands.
- Acceptance: A clean profile's priority ends with `impeccable` and `lgtm`; Hermes' menu builder shows both.
- Checks: `tests/test_telegram_menu_policy.py`, `python3 scripts/check.py`, `docs.py check`.
- Dependencies: None.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-068 — Audit this repository's test suite and record bounded follow-ups

- [x] TOOLSET-068 — Audit this repository's test suite and record bounded follow-ups
- Status: done
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [plan](docs/project.md#test-suite-optimization-method-2026-10-15), [check runner](scripts/check.py), [the protocol from TOOLSET-067](skills/engineering/local/test-suite-optimization/PROTOCOL.md).
- Scope: Apply the protocol in audit mode to the offline inventory of `python3 scripts/check.py` (excluded native modules stay out). Measure in a scratch directory: per-directory wall time (3 runs), the 30 slowest tests, line and branch coverage of the toolset's Python sources with per-test contexts, and groups of tests whose covered-line sets are identical or strict subsets. Mutation testing is optional: if used, install the tool only in a disposable virtual environment outside the repository and sample the modules with the most redundancy candidates. Inspect the top candidates by reading the tests. Record the baseline and findings in the plan section of docs/project.md, and add up to five follow-up tasks in TODO.md under the TEST-SUITE goal, each with its measured before values, the exact tests involved, the protocol's acceptance template and its checks. Start with `test_delivery_state.py` setup cost (about 40 s of the slowest 15 tests).
- Acceptance: The plan section records the measured baseline (counts, times, coverage percentages, method and commit); each follow-up task names concrete tests and measurable before values; no test or source file changes in this task; candidates without evidence are listed as unverified, not as tasks.
- Checks: `python3 skills/docs-sync/scripts/goals.py validate .`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --stat` shows only docs/project.md, TODO.md and goals.json; `git diff --check`.
- Dependencies: TOOLSET-067.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No test deletion, consolidation or source edit; no repository dependency changes; no push.
- Current evidence: Audit on `376f7ed` recorded in the [baseline audit](docs/project.md#baseline-audit-toolset-068-2026-10-15): 1,253 tests; sequential 225–237 s over 3 passing `--jobs 1` runs (Autowork 132–139 s); 67% combined line and branch coverage of toolset sources; 760 tests with per-test records; 58 identical-coverage groups (187 tests) and 248 subset cases; mutation not measured. cProfile of `test_delivery_state.py` attributes about 42 s of 110 s to `check_receipt.runtime()` package metadata and 7 s to executable hashing. Sampled identical groups are distinct contracts; no removal recommended. Follow-ups TOOLSET-072 and TOOLSET-073 recorded; no test or source file changed.
- Checks run: `goals.py validate` ok; `docs.py check` ok; `git diff --stat` limited to docs/project.md, TODO.md and goals.json; `git diff --check` clean.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-074 — Advertise Engineering and the Git commands in the Telegram menu

- [x] TOOLSET-074 — Advertise Engineering and the Git commands in the Telegram menu
- Status: done (2026-10-15). At the user's request `engineering`, `git_commit_push` and `git_pull_merge` follow `lgtm` in the bundle's managed menu priority, so all 12 toolset menu commands lead the menu; at Hermes' 60-entry default the built-ins `yolo`, `approvals` and `fast` also leave it and stay typeable. Updated menu tests failed first, then passed; Hermes' own `telegram_menu_commands` on a copy of the toolset profile config lists all 12 first; `python3 scripts/check.py` passed; `docs.py check` ok.
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [menu policy](telegram_menu_policy.py), [superseded menu call](docs/project.md#vendored-ui-taste-skill).
- Scope: Bundle menu priority, its tests and the docs that list advertised commands.
- Acceptance: A clean profile's priority ends with `engineering`, `git_commit_push` and `git_pull_merge`; Hermes' menu builder shows them.
- Checks: `tests/test_telegram_menu_policy.py`, `python3 scripts/check.py`, `docs.py check`.
- Dependencies: None.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-075 — Restart the gateway only in a quiet window

- [x] TOOLSET-075 — Restart the gateway only in a quiet window
- Status: done (2026-10-15). `update_bundle.py` restarts at once only when `chat_turns()` (Hermes' `active_agents` minus claimed cron runs) is 0; otherwise, or when activity is unknown, it reports `deferred` and starts a detached `--restart-when-quiet` waiter (30 s checks, 6 h window) that records `requested`, `reloaded` or `deferred_expired` without ever forcing; a live waiter makes later updates report `pending`; `/toolset update status` shows its progress. Quiet was redefined to exclude cron runs (recorded in the plan). Ten new regressions failed first, then passed; three immediate-restart tests now pin `chat_turns=0`; the waiter's command-line path was smoke-tested; `python3 scripts/check.py` 473/575 (1 skipped)/209/8; `docs.py check` ok. Offline only: no live deferred restart has been observed yet.
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: [rollout findings](docs/project.md#gentler-update-rollout-2026-10-15), [update guide](docs/installation.md#update-all-profiles), [updater](update_bundle.py).
- Scope: When an applied update needs a restart, read `gateway_state.json` (`active_agents`, Hermes' busy contract) and each served profile's `cron/external-workers/`; call `hermes gateway restart` only when no agent turn or cron run is in flight. Otherwise record `gateway_restart: deferred` with what it waits on and keep checking in the background up to a bounded window; when the window ends, leave the restart deferred and report it instead of forcing. `/toolset update restart` (or the terminal form) remains the explicit way to restart now.
- Acceptance: With a busy fixture the updater never invokes the restart and reports `deferred` with the blocking work; with an idle fixture it restarts once; a window that never goes quiet ends `deferred`, not forced; no Hermes config or timeout is changed.
- Checks: Failing-first regressions in `tests/test_update_bundle.py` with fake gateway state and worker files, then `python3 scripts/check.py`.
- Dependencies: None.
- Exclusions: No Hermes code changes; no edits to `restart_after_turn_timeout` or `cron_drain_timeout`.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-076 — Coalesce restarts across a burst of updates

- [x] TOOLSET-076 — Coalesce restarts across a burst of updates
- Status: done (2026-10-15). `restart.json` carries `covers` (each update's `started_ns`); an update that finds an outstanding requested or deferred restart joins it under the update lock and reports `pending`; the waiter takes the same lock for every check, so it never restarts while an update is applying files, and records its outcome on the latest receipt whenever that update is covered (`gateway_restart_covers`); `/toolset update status` says how many updates a restart covers. New regressions (three busy updates → one waiter, one restart, latest receipt `requested` covering 3; waiter blocked by a held lock; covered count in status) failed first, then passed; `python3 scripts/check.py` 478/575 (1 skipped)/209/8; `docs.py check` ok. Offline only. A requested restart that is already draining still records no outcome for its covered updates; that is TOOLSET-077.
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: [rollout findings](docs/project.md#gentler-update-rollout-2026-10-15), [update guide](docs/installation.md#update-all-profiles), [updater](update_bundle.py).
- Scope: A deferred or pending restart absorbs later updates: further applied updates extend the same deferred restart instead of requesting another, so a burst of updates causes one restart after the last one.
- Acceptance: Three updates applied while the gateway is busy produce exactly one restart once it is quiet; status lists every update the restart covers.
- Checks: Regressions in `tests/test_update_bundle.py`, then `python3 scripts/check.py`.
- Dependencies: TOOLSET-075.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-077 — Record the restart outcome in the update status

- [x] TOOLSET-077 — Record the restart outcome in the update status
- Status: done (2026-10-15). Every restart request records the gateway PID it replaces; `finish_restart()` (called by `/toolset update status` once the restart process is gone and a gateway runs) records `completed` with `gateway_restart_result` (new PID and start, Telegram bots with a menu-resend log line after the request versus not seen, forced-drain interruptions) or `restart_failed` when the old gateway still runs, on the covered receipt under the update lock, once; the one-message summary shows it. Six new regressions failed first, then passed; a read-only run of the parsing against the live 12:11 restart found 9 bots resent and 1 interrupted cron run, matching the logs; `python3 scripts/check.py` 484/575 (1 skipped)/209/8; `docs.py check` ok. Offline only.
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: [rollout findings](docs/project.md#gentler-update-rollout-2026-10-15), [update guide](docs/installation.md#update-all-profiles), [updater](update_bundle.py).
- Scope: After a requested or deferred restart completes, record the new gateway PID, the time, whether each served bot re-sent its Telegram menu and any work the shutdown interrupted, so `/toolset update status` stops reporting a finished restart as `requested`.
- Acceptance: Status shows `gateway_restart: completed` with PID and per-profile menu resend results after a fixture restart; an incomplete restart stays visible.
- Checks: Regressions in `tests/test_update_bundle.py`, then `python3 scripts/check.py`.
- Dependencies: TOOLSET-075.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-080 — Disable unused OMH skills through a managed skills.disabled list

- [x] TOOLSET-080 — Disable unused OMH skills through a managed skills.disabled list
- Status: done
- Goal: OMH-TRIM — Keep the OMH skills profiles use and drop the rest from every prompt.
- Sources: [plan](docs/project.md#omh-catalog-trim-2026-10-15), [OMH installer](install-omh.py), [runtime defaults](runtime_defaults.py), [setup preflight](setup_preflight.py), [installer settings](install-plugins.sh), [bundle defaults](plugins/defaults.json).
- Scope: Add `omh.keep_skills` to `plugins/defaults.json` with these 35 names: code-review, verification-gate, automation-blueprint, visual-qa, mobile-release, web-research, release-cut, agent-instructions, product-brief, agent-debug, design-quality-gate, frontend, failure-signal-audit, workflow-learning, agent-ops-review, git-workflow, agent-board, build-failure-triage, harness-session-inventory, todo-checklist, application-threat-model, deploy-and-monitor, doctor, gateway-intent-card, provider-profile-posture, model-setup, memory-sync, run-efficiency, workspace-audit, cancel, oh-my-hermes, skill, memory-new, decision-recall, wiki. In each profile with OMH installed, the OMH-managed skills are the `skills[].name` entries of `<store>/manifest.json`, with the store resolved exactly as `install-omh.py`'s `profile_plan` does (profile `.env` `OMH_HOME`, else `<home>/omh`, else `~/.omh` when OMH is the memory provider). First confirm the names Hermes registers for those skills (plain `code-review` or a prefixed form) and use those in `skills.disabled`. The managed trim is every OMH-managed skill not in the keep list. Runtime defaults (plugin load, so also `/toolset update`) set `skills.disabled` to the sorted union of the user's own entries and the managed trim, removing only names that were managed but are now kept or no longer OMH skills; setup (`install-plugins.sh`, `setup_preflight.py`) stops resetting `skills.disabled` to empty and applies the same merge. Leave `skills.platform_disabled` alone except for the existing setup behavior on non-OMH entries. Profiles without OMH get no entries. Honor the existing `apply_runtime_defaults: false` opt-out. Record which entries are managed so a later keep-list change can remove them (for example `plugins.entries.hermes-toolset.omh_trim` with the applied list). Document the trim, the keep list and how to undo it (opt out, or remove names) in docs/installation.md, docs/reference.md and the CHANGELOG.
- Acceptance: A fixture profile with a fake OMH manifest of kept and unkept skills plus a user-disabled skill ends with exactly the user entry plus the unkept OMH names in `skills.disabled`; rerunning changes nothing; moving a skill into the keep list removes only that managed entry; an opted-out profile and a profile without OMH are unchanged; setup no longer empties a user's `skills.disabled`; no OMH file, store or memory setting is modified.
- Checks: new regressions beside the existing runtime-defaults tests in `tests/test_telegram_menu_policy.py` (`SelfHealTests`, `RuntimePolicyOptOutTests`) and in `tests/test_install_plugins.py`; `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No `omh setup --core`, `omh skill-profile reconcile`, file deletion, OMH capability-policy change or memory change; no live profile edits (TOOLSET-081); no push.
- Current evidence: `runtime_defaults.py` finds OMH skills through `skills.external_dirs` folders whose parent `manifest.json` names the `oh-my-hermes` package, reads each SKILL.md's registered name, and sets `skills.disabled` to the user's entries plus the unkept OMH names, recorded in `plugins.entries.hermes-toolset.omh_trim`; it removes only previously managed names and never leaves a bundled toolset skill disabled; without a keep list it trims nothing. Setup (`install-plugins.sh`, `setup_preflight.py`) no longer empties `skills.disabled`. The keep list is top-level `omh_keep_skills` because `install-omh.py` requires the `omh` block's exact keys. Recount by registered name: 35 used skills (364 loads), 41 kept with core and memory skills. New `tests/test_omh_trim.py` (6 tests: registered names, idempotence, keep-list change, no-OMH and no-keep-list profiles, foreign manifest and escaping paths, bundled skills); run against the unchanged code, five failed and the no-OMH case already passed. Read-only preview on live configs: two OMH profiles keep 41 of 142 and disable 101; a profile without OMH is unchanged.
- Checks run: `python3 scripts/check.py` passed offline; `tests/test_omh_trim.py` 6 passed; `test_install_plugins.py`, `test_telegram_menu_policy.py`, `test_setup_runtime.py` passed; `install-omh.py` defaults still validate; `docs.py check` ok; `git diff --check` clean. Not merged into the shared checkout: profiles that load the plugin from it would get the trim at their next load, before TOOLSET-081's one-profile qualification.

### TOOLSET-078 — Report a concurrent update clearly

- [x] TOOLSET-078 — Report a concurrent update clearly
- Status: done (2026-10-15). The updater retries the lock for up to 10 s (a restart waiter holds it only briefly per check), then prints `status: busy` with the running update's PID, mode and start and exits 3 without touching its receipt; the running record now carries `mode` (`update` or `check`); chat `/toolset update` checks `running_update()` first and names the running update instead of spawning an updater that exits silently. Five new regressions failed first, then passed (one existing chat test exposed a SystemExit from a stubbed updater, now handled); a live read-only `running_update()` found the lock free; `python3 scripts/check.py` 489/575 (1 skipped)/209/8; `docs.py check` ok. Offline only.
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: [rollout findings](docs/project.md#gentler-update-rollout-2026-10-15), [update guide](docs/installation.md#update-all-profiles), [updater](update_bundle.py).
- Scope: When another update is running, a new update or `--check` reports `busy` with that run's PID, start time and mode, and either waits for it or exits without overwriting its record.
- Acceptance: A check started during a running update never returns the running record as its own result and never overwrites it.
- Checks: Regressions in `tests/test_update_bundle.py`, then `python3 scripts/check.py`.
- Dependencies: None.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-081 — Qualify the OMH trim on one profile, then roll it out

- [x] TOOLSET-081 — Qualify the OMH trim on one profile, then roll it out
- Status: done
- Goal: OMH-TRIM — Keep the OMH skills profiles use and drop the rest from every prompt.
- Sources: [plan](docs/project.md#omh-catalog-trim-2026-10-15).
- Scope: On one profile with OMH whose cron is paused, record before values: the OMH share of the skill index in a real request prompt (characters and skill count), `omh doctor --json` and the memory provider status. Apply TOOLSET-080 there (plugin reload or `/toolset update` scoped to that profile), then repeat the measurements, load `code-review` and `verification-gate` in a short questions-only chat, and ask OMH's router for a trimmed workflow to see how a disabled recommendation is handled. If all pass, run `/toolset update` for the fleet and record per-profile managed entry counts.
- Acceptance: The trimmed profile's prompt skill index loses the unkept OMH entries (measured characters before and after); kept skills load; `omh doctor` and memory provider status are unchanged; a router recommendation of a disabled skill does not break the turn (or the keep list gains that skill with the reason recorded); fleet rollout lists managed entries per profile; results recorded with Hermes and OMH versions.
- Checks: before/after prompt measurements, `omh doctor --json` before and after, the chat transcript, `/toolset update status`.
- Dependencies: TOOLSET-080.
- Environment prerequisite: A profile with OMH installed and its cron paused; owner availability for the short chat.
- Exclusions: No memory-store changes, no OMH reinstall, no resumed cron jobs.
- Current evidence: Qualified on one OMH profile with its cron paused, Hermes 0.22.0 and OMH 3.0.0. Measured with Hermes' own `build_skills_system_prompt`: the skill index fell from 24,016 to 15,253 characters (318 to 218 lines); OMH entries from 142 lines and 12,349 characters to 41 lines and 3,522. `omh doctor --json` stayed ok, 54/54 with 4 warnings, before and after; `hermes memory status` was unchanged (see TOOLSET-082). A questions-only `hermes chat -Q` in an empty scratch folder loaded `omh-code-review` and `omh-verification-gate`, and `omh-plan` returned "Skill 'omh-plan' is disabled" without breaking the turn; nothing was edited. Only `skills.disabled` and `plugins.entries.hermes-toolset.omh_trim` changed in that profile. Fleet rollout: merged as `1200fe7`, pushed, `/toolset update` ready on all 10 profiles; each of the 9 OMH profiles has 101 managed entries and the profile without OMH none. The gateway restart was deferred until no chat turn was in flight.
- Checks run: before/after index measurement, `omh doctor --json` before and after, the chat transcript, per-profile config read-back after `/toolset update`.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-083 — Keep unattributed cron stagnation unknown

- [x] TOOLSET-083 — Keep unattributed cron stagnation unknown
- Status: done; independent review approved. Focused collector/correctness: 25 passed; Python 3.12 offline gate: 495/576/209/8 passed, one skip and eight excluded modules. Installed consumer replay returns unknown/null for every observed profile, preserves historical counters and run IDs, and is stable on replay. No worker recovery or scheduler state change is inferred.
- Goal: RECOVERY — Preserve evidence-bounded scheduled maintenance.
- Sources: [accepted requirements](docs/project.md#accepted-requirements), [collector](skills/autowork/scripts/audit_profiles.py).
- Scope: Stop the audit collector from classifying unchanged historical handoffs plus unrelated cron completions as repeated task failure; retain historical counters, deduplicated occurrence IDs and log cursors.
- Acceptance: Without exact job/occurrence/task attribution and fresh structured evidence, stagnation and its count remain unknown; same-job, cross-job and replay fixtures cannot create a stall claim; retained historical evidence is preserved.
- Checks: Focused collector and correctness modules, same-receipt before/after replay, installed-consumer readback and independent review; `git diff --check`.
- Dependencies: None.
- Exclusions: No product writes, worker recovery, automatic pause/resume, runtime edits or publication.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-079 — Report linked profiles and offer pinned clones

- [x] TOOLSET-079 — Report linked profiles and offer pinned clones
- Status: done (2026-10-15). `linked_profiles()` reports each profile whose plugin is a link, with the checkout's revision, whether it is dirty and whether that revision is on upstream `main` as last fetched; `/toolset update status` (live, plus `linked_profiles` in the receipt) and `hermes toolset doctor` (`linked_profiles`, never a failure) list them. `hermes toolset pin --profile NAME [--dry-run]` clones the checkout at the linked revision under the update lock, saves the link and its record in `maintenance/toolset-update/pinned/`, and swaps the clone in; it refuses a dirty checkout, an unreleased revision or a running update. `--unpin` restores the link and keeps the clone. Twelve new regressions, including an update advancing the pinned clone while a later local commit does not reach it; a read-only live dry run listed 7 linked profiles and refused pinning while main is ahead of origin; `python3 scripts/check.py` 506/576 (1 skipped)/209/8; Pi 3 passed. Offline only; no live profile converted.
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: [rollout findings](docs/project.md#gentler-update-rollout-2026-10-15), [update guide](docs/installation.md#update-all-profiles), [updater](update_bundle.py).
- Scope: Report which profiles load the plugin through a link to a working checkout (they go live with whatever that checkout contains on any restart) and offer an explicit, reversible conversion to a pinned clone that only an update advances.
- Acceptance: Status and `/toolset` doctor list linked profiles; an opt-in conversion leaves the profile on the same revision, keeps a backup of the link and is covered by a dry run.
- Checks: Regressions in `tests/test_update_bundle.py` and the doctor tests, then `python3 scripts/check.py`.
- Dependencies: None.
- Exclusions: No automatic conversion of live profiles; converting them is a separate, user-authorized live step.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-085-1a — Select several eligible tasks and decide which can run together

- [x] TOOLSET-085-1a — Select several eligible tasks and decide which can run together
- Status: done
- Local delivery: Implemented pure multi-task selection and declared path/resource/dependency conflict planning; no workers or CLI changes. Python 3.12 offline gate passed 506/586/212/8 tests (one skip; eight modules excluded). Independent review approved after regressions fixed malformed glob classes/newlines, ledger-only running status and directory-glob verification. Integrated into main on 2026-10-15 by the interactive coordinator after re-running `python3 -m unittest skills/autowork/scripts/test_parallel_plan.py` (10 passed) and `python3 scripts/check.py` (4 directories passed) on the merge with `b5092b3`.
- Planner call: Preserve TOOLSET-064 pending integration and avoid the active canonical writers by using an isolated branch for this ready task. Reuse sequential contract checks lazily and standard-library fnmatch semantics; broad patterns that can include serial paths run alone.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [task selection](skills/autowork/scripts/task_execution.py), [ledger eligibility](skills/docs-sync/scripts/goals.py).
- Scope: Add `skills/autowork/scripts/parallel_plan.py` with a pure function that takes the ordered runnable tasks (reuse `task_execution.select()`'s per-task contract checks, refactored so one function returns every passing task in order instead of the first) plus the running set, and returns the tasks to dispatch now and a reason for each waiting task. Parse two new optional TODO fields: `Touches:` (comma list of repo paths, directory prefixes ending in `/`, or globs) and `Resources:` (tokens; `live` and `exclusive` mean run alone). Conflict rules from the plan: direct or transitive dependency, overlapping paths (prefix or glob match in either direction), a shared resource token, a serial path (built-in list: package manifests, lockfiles, migration and schema folders, CI workflow files), or a missing `Touches:` means not together. Never dispatch `in_progress` tasks or tasks held by a live slot; an `in_progress` task without a slot counts as running work with its `Touches:`, and without `Touches:` it blocks all dispatch beside it (reported). Fill rule: the highest-priority runnable task is always considered first; if it must run alone or conflicts with running work, nothing lower is dispatched. Also export `overlap(actual_paths, declared, other_sets)` for TOOLSET-088's check of reported files. No dispatch, lease or CLI changes.
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/scripts/task_execution.py
- Acceptance: Unit tests show: two independent tasks with disjoint `Touches:` are both selected; a dependent pair (including transitive) is not; overlapping paths, globs, a shared resource token, `live`/`exclusive`, a serial path and a missing `Touches:` each serialize; the top task that must run alone blocks lower dispatch; an `in_progress` task without a slot blocks overlapping dispatch, and blocks everything without `Touches:`; existing `select()` behavior and every existing `test_task_execution.py`/`test_priority_selection.py` case are unchanged.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_plan.py` (new); `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No inference of file sets from prose or by an LLM; no changes to goals.py ordering.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-086-9f — Add a repository coordinator lease, worker slots and an execution journal

- [x] TOOLSET-086-9f — Add a repository coordinator lease, worker slots and an execution journal
- Status: done
- Readiness: Offline implementation reviewed and verified in the isolated candidate; canonical integration and task closure remain pending. No worker dispatch or live host qualification.
- Local evidence: 13 new lease/recovery tests and 49 unchanged execution/priority tests passed on Python 3.12.14. `python3 scripts/check.py` passed all four offline directories (506/589/212/8 tests; one skip; eight modules excluded). Independent review approved after two reproduced retry defects were fixed (relative retry worktree storage and clean second-attempt release).
- Planner call: Preserve the active canonical writers; use an isolated task checkout rather than overlap their workspace. Reuse existing process identity, file safety, Git and writer-lock helpers; standard library only (bundled Ponytail fallback).
- Integration: merged into main on 2026-10-15 by the interactive coordinator with TOOLSET-085-1a already integrated; `test_parallel_state.py` and `test_parallel_plan.py` passed together and `python3 scripts/check.py` passed all four offline directories on the merge. Worker dispatch remains TOOLSET-087-32.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [current lease](skills/autowork/scripts/task_execution.py).
- Scope: Add `skills/autowork/scripts/parallel_state.py` storing `coordinator.json`, `slots/<TASK>.json` and append-only `journal.jsonl` under `<git-common-dir>/autowork-execution/`, written atomically under the existing `writer.lock` and reusing `task_execution`'s process identity (PID, start ticks, boot ID). Functions: claim/release the coordinator lease bound to the `--owner-pid` identity of the persistent coordinator session (refuse a second live coordinator; supersede a dead one; reject a missing or non-ancestor owner), create/update slots through the state machine in the plan, including the retry transitions from its builder-check answers (`interrupted` → `dispatched` attempt 2 in the same worktree; `held` → a fresh attempt on `autowork/<TASK>-r2`; a second failure stays `held`); illegal transitions raise, append journal events, and `reconcile(repo)` that classifies each slot as live worker (adopt), dead with commit (queue integration), dead with uncommitted changes (`interrupted`, worktree kept), or clean without commit (`released`). Make `task_execution.execute()` return `BUSY` while a live parallel coordinator exists, and make the coordinator claim refuse while a live sequential `active.json` owner exists. A live lease never expires by age.
- Touches: skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_state.py, skills/autowork/scripts/task_execution.py
- Acceptance: Tests show two coordinators cannot both claim one repository (also across two linked worktrees); a sequential claim and a parallel coordinator exclude each other; a dead coordinator is superseded; reconcile is idempotent (running it twice gives the same states and journal adds nothing new the second time) and classifies the four worker cases above with real Git fixtures; an illegal slot transition is refused; existing lease tests pass unchanged.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_state.py` (new); `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No worker launch, worktree creation or integration (TOOLSET-087/088); no heartbeat-based expiry.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-087-32 — Dispatch workers in their own worktrees with a refilled worker pool

- [x] TOOLSET-087-32 — Dispatch workers in their own worktrees with a refilled worker pool
- Status: done
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [bounded runner and isolate suggestion](skills/autowork/scripts/task_execution.py); builds on TOOLSET-085-1a and TOOLSET-086-9f.
- Scope: Add `skills/autowork/scripts/parallel_dispatch.py` and new `task_execution` flags: `--parallel [N]` (default 2, cap 4 unless `--max-workers`, hard limit 8), `--max-workers`, `--worker-host hermes|codex|pi`, `--worker-command JSON` (argv with `{worktree}`, `{prompt_file}`, `{timeout}`), `--worker-timeout` (default 3600), `--min-free-mem-mb` (default 1500), and `--wait --timeout S`. With `--apply --parallel`, claim the coordinator lease, reconcile slots, compute the dispatch set (TOOLSET-085-1a), and for each task create worktree `<parent>/<repo>-autowork-<TASK>` on branch `autowork/<TASK>` at the recorded canonical HEAD (refuse an existing branch or folder that the journal does not show Autowork created), write the self-contained worker prompt from the plan (task body, worktree, branch, baseline, rules, `report.json` schema), and start the worker CLI in its own process group with cwd = worktree, its own `TMPDIR`, `AUTOWORK_SLOT` and `AUTOWORK_PORT_BASE`, without `HERMES_TOOLSET_EXECUTION_COMMON`. Record worker identity and log path in the slot. Resource gate: hold dispatch while MemAvailable < `--min-free-mem-mb` × (running workers + 1) or the 1-minute load average ≥ CPU count. Restart an `interrupted` slot once in its own worktree with a resume note. Templates never add approval- or sandbox-bypass flags (Codex adds only the worktree and Git common directory as write roots); `--parallel` output shows each worker command. Hermes workers use the coordinator's profile unless `--worker-profile` is given. `--apply --parallel` and every later parallel call require the coordinator's `--owner-pid`. `--wait` blocks until a worker exits or the timeout passes and returns the changed slots; a worker past `--worker-timeout` gets its process group stopped and becomes `interrupted`. Calling `--apply --parallel` again refills free slots. Verify the shipped templates against the installed CLIs (`hermes chat --query-file F --oneshot --in DIR --run-budget S`; `codex exec -C DIR` with the sandbox setting that still allows commits from a linked worktree; Pi's prompt argument) and ship only verified ones; with no usable template, non-Linux or a Claude Code coordinator without `--worker-command`, return `SEQUENTIAL_FALLBACK` plus the ordinary single-task contract. Tests use a deterministic fake worker script (edits files, sleeps, commits, writes `report.json`).
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/task_execution.py, skills/autowork/scripts/fixtures/
- Acceptance: With the fake worker: two independent tasks start in separate worktrees and run at the same time (overlapping process lifetimes recorded in the journal); a dependent or conflicting task is not started; a third task fills the slot freed by the first finisher; a timed-out worker is stopped and its worktree kept; a crashed worker's slot reconciles per TOOLSET-086-9f without a duplicate start, and an interrupted slot restarts once in the same worktree; low memory holds dispatch; user branches/folders with the target names are refused untouched; the unsupported-host path returns `SEQUENTIAL_FALLBACK`; plain `owner_cycle.py --apply` output is unchanged.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_dispatch.py` (new); `python3 scripts/check.py`; `git diff --check`; the template verification commands recorded in task evidence.
- Dependencies: TOOLSET-085-1a, TOOLSET-086-9f.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No integration or task closing (TOOLSET-088-a7); no real LLM worker run in tests; no Claude Code approval-mode template.
- Delivery (2026-10-15): `parallel_dispatch.py` plus `--parallel [N]`, `--max-workers`, `--worker-host`, `--worker-command`, `--worker-profile`, `--worker-timeout`, `--min-free-mem-mb` and `--wait` on `owner_cycle.py`. Workers start in their own process group with cwd = worktree, their own `TMPDIR`, `AUTOWORK_SLOT` and `AUTOWORK_PORT_BASE`, without `HERMES_TOOLSET_EXECUTION_COMMON`; the prompt, report path, log and command are kept under `<git-common-dir>/autowork-execution/slot-data/<TASK>/attempt-N/`. Results: `DISPATCHED`, `WAITING`, `IDLE`, `CHANGED`, `TIMEOUT`, `SEQUENTIAL_FALLBACK`.
- Template verification (installed CLIs' `--help`, 2026-10-15): Hermes `chat --query-file --oneshot --in --run-budget -Q` and global `-p`; Codex `exec -C DIR --sandbox workspace-write --add-dir DIR -` (prompt on stdin); Pi `-p @file`. No template adds an approval or sandbox bypass. Real worker runs remain TOOLSET-091-00.
- Planner calls while implementing: the prompt arrives both as a file and on stdin; a slot whose clean worker died is retried once like an interrupted one; held slots are left to TOOLSET-088-a7; a `--worker-host auto` coordinator is identified from its process ancestry.
- Independent review (2026-10-15) found and this task fixed: Hermes coordinators (`python3 -I -c '<hermes_cli>'`) were not auto-detected; the worker timeout came from each call instead of the worker's start; a child surviving its leader let a restart put a second writer in the worktree (liveness and stop now cover the whole process group, escalating to SIGKILL); a dispatch interrupted before its slot blocked the task forever (the journal-recorded worktree is now adopted); launch failures spent the retry (now held with the cause); malformed queues looked idle (`NoEligibleTask` now separates them); dispatch and wait passes are serialized by `dispatch.lock`.
- Checks run: `test_parallel_dispatch.py` 17 passed (the 6 new regressions fail on the pre-fix commit `0a84fb2`), the first 10 passed 5 consecutive runs; `test_parallel_state.py` and `test_parallel_plan.py` pass; `python3 scripts/check.py` passed all four offline directories; `git diff --check` clean. The dispatch-lock race has no deterministic test.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-092-f2 — Keep the restart outcome when a later update replaces the receipt

- [x] TOOLSET-092-f2 — Keep the restart outcome when a later update replaces the receipt
- Status: done (2026-10-15). `finish_restart` stores the outcome in `restart.json` (`finished`, `outcome`), rereads the marker under the update lock so an update that joined meanwhile keeps its `covers`, and every update records a finished restart before it replaces the receipt. `/toolset update status` shows `Last gateway restart (requested …): completed, PID N, menus resent K of M` (`last_gateway_restart` in the full receipt) when the latest receipt does not cover that restart. Four new regressions failed on the previous code and pass; `python3 scripts/check.py` passed. Offline only; live confirmation stays in TOOLSET-084.
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: TOOLSET-084 live evidence (receipts replaced at 15:52 and 15:53 on 2026-10-15), [updater](update_bundle.py), [status](bundle.py).
- Scope: Keep a finished restart's outcome durable and visible even when a later update or check replaces the receipt it covers.
- Acceptance: The outcome survives in `restart.json`; the next update records it before writing its own receipt; status shows it for a receipt that does not cover the restart; a concurrent join is not lost.
- Checks: `tests/test_update_quiet_restart.py` RestartOutcomeTests, `tests/test_bundle.py`, `python3 scripts/check.py`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No Hermes changes; no live restart in this task.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-084 — Qualify the gentler update rollout live

- [x] TOOLSET-084 — Qualify the gentler update rollout live
- Status: done (2026-10-15). Confirming run after TOOLSET-092-f2 (afe1482): `hermes toolset update` requested the restart at once with no chat turn in flight; the gateway restarted as PID 553964 at 16:49:53; `/toolset update status`, run through the pinned plugin's own code, showed `Gateway restart: completed, new gateway PID 553964` with menus resent for all nine Telegram profiles and none missing, and `restart.json` kept the same outcome. The only timeout logged was Hermes' 30 s cron drain; cron workers started 43 and 59 minutes earlier were still running afterwards. Earlier live evidence follows.
- Evidence: Live evidence 2026-10-15. (1) The 15:33 restart was requested by the deferred waiter with no chat turn in flight; a Telegram turn that started at the same moment made Hermes wait, and it ended on its own at 15:37:26 with 1590 s left before any forced drain, and the gateway restarted at 15:38:24. (2) The 15:50 restart was requested at once (no chat turn) and completed as PID 3947525 at 15:51:05; all nine Telegram profiles logged a menu resend. Both restarts logged only the 30 s cron-drain timeout ("interrupting remaining work"); the three external cron workers of the 15:50 restart kept running. (3) Two concurrent `update_bundle.py --check` runs: the second waited 10 s, exited 3 with `busy`, the first run's PID/mode/start, and left its receipt untouched. (4) All seven linked profiles were pinned at the linked revision 02c017c; each is a clean clone and later updates advanced them (57ca912, then the other writer's 82c78a5) while the checkout's unreleased state no longer reaches them. Gap: two later updates (15:52, 15:53) replaced the 15:49 receipt before its outcome was recorded, so no receipt kept `completed`; fixed offline in TOOLSET-092-f2.
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: [rollout findings](docs/project.md#gentler-update-rollout-2026-10-15), [update guide](docs/installation.md#update-all-profiles), [linked profiles](docs/installation.md#linked-profiles-and-pinned-clones).
- Scope: After the user publishes TOOLSET-075..079 and asks for an update, run `hermes toolset update` and confirm from the receipt and gateway log that the restart was requested only with no chat turn in flight (or deferred and later completed), that `/toolset update status` shows the new gateway PID and menu resends, and that a second update during the first reports `busy`. With the user's OK, pin one linked profile and confirm it loads the clone after the next restart.
- Acceptance: A live receipt records `gateway_restart: completed` with `gateway_restart_result`, or a deferred restart that later completed; no forced drain appears in the gateway log for that restart; any pinned profile runs the same revision as before.
- Checks: `/toolset update status full`; the gateway log around the restart; `git -C PROFILE/plugins/hermes-toolset rev-parse HEAD` for a pinned profile.
- Dependencies: TOOLSET-092-f2.
- Prior work: TOOLSET-079 (done, archived).
- Ownership: Toolset coordinator; live steps need the user's request.
- Exclusions: No push, update, restart or pinning without the user's request.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-088-a7 — Integrate finished workers one at a time and close tasks only after validation

- [x] TOOLSET-088-a7 — Integrate finished workers one at a time and close tasks only after validation
- Status: done
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [delivery verifier](skills/autowork/scripts/delivery_state.py), [bounded runner](skills/autowork/scripts/task_execution.py).
- Scope: Add `skills/autowork/scripts/parallel_integrate.py` and flags `--integrate TASK --run ARGV... --timeout S` and `--parallel-close TASK`. Integrate in priority order among `reported` slots, under the writer lock: verify the commit descends from the slot baseline and matches `report.json`; compare `git diff --name-only baseline..commit` with the task's `Touches:`, coordinator-owned files and other slots' files (`parallel_plan.overlap`), holding the task on any mismatch; in the coordinator-owned integration worktree (`<parent>/<repo>-autowork-integration`, detached), check out canonical HEAD and run `git merge --no-ff autowork/<TASK>`, aborting and holding on conflict; run the validation argv in that worktree through the bounded process core factored out of `command()` (cwd parameter, no `active.json`, `writer.lock` only around state writes; sequential `command()` output byte-identical); then fast-forward the canonical checkout with `git merge --ff-only` only if its HEAD is unchanged (redo the merge once on a moved HEAD; hold after that). Record `integrated` with the merge commit and check receipt. `--parallel-close` refuses unless the slot is `integrated` with a passing validation receipt, then runs `goals.py task TASK done` (and `goals.py archive`), journals it, and removes the clean worker worktree and branch it created. Held and failed slots keep their worktrees. Once no worker is running, a held slot gets one fresh attempt on `autowork/<TASK>-r2` from the current canonical HEAD; a second failure stays held for Plan For Me's fix-or-skip.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/task_execution.py
- Acceptance: Tests show: a clean worker branch merges and validates, then closes; `--parallel-close` before integration or after a failed validation is refused and the ledger is unchanged; a merge conflict leaves the canonical checkout, its dirty user files and the worker branch untouched and holds the task; a file outside `Touches:` or a coordinator-owned file holds integration; a moved canonical HEAD is re-merged once; a held task gets exactly one fresh `-r2` attempt after the pool drains, keeping the first attempt's branch; sequential `--run` output is unchanged; a failed worker never removes another slot's commit or worktree; the canonical checkout is only ever fast-forwarded.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_integrate.py` (new); `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-087-32.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No rebase, automatic conflict resolution, reset of the canonical checkout, push or remote integration.
- Delivery (2026-10-15): `parallel_integrate.py` plus `--integrate TASK --run ARGV... --timeout S` and `--parallel-close TASK` on `owner_cycle.py`; results `INTEGRATED`, `CLOSED`, `RETRIED`. Validation runs in the detached integration worktree through `bounded_command()`, factored out of the sequential `command()` (whose lease, budget and receipt output are unchanged); the canonical checkout is only fast-forwarded. Held slots get one fresh `autowork/<TASK>-r2` attempt once no worker runs (`dispatch_with_retries`). Close cleanup is retryable and follows Docs Sync's archive owner, including legacy and linked archives.
- Implementation: by the toolset Autowork cron (b8ac329, review fixes 2927cca, archive-owner fix 0e2fa22, refreshed onto main as 1e5b97b), with the cron's independent review approving the final source. Canonical integration was held by the cron while other sessions were active in canonical main; the interactive coordinator took the released lease and integrated.
- Checks run: `test_parallel_integrate.py` (48) with `test_parallel_dispatch.py` 65 passed together; every acceptance item has a named test (clean merge/close, close refusal and byte-identical ledger, conflict preserving dirty files and other slots, outside-Touches and coordinator-file holds, moved HEAD re-merged once then held, single `-r2` retry after drain, sequential output byte-identical, ff-only canonical updates); `python3 scripts/check.py` passed all four offline directories on the merge (510/664/212/8); `git diff --check` clean. Offline only; real workers remain TOOLSET-091-00.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-093-01 — Build the continuous Pi Autowork runner

- [x] TOOLSET-093-01 — Build the continuous Pi Autowork runner
- Status: done (2026-10-15). `scripts/pi-autowork.sh` selects each task with `goals.py next` (no model call on an empty queue; drift and ledger errors reported separately), runs `pi --mode json` with an explicit provider/model, `/skill:autowork` naming exactly that task, `--no-approve` and a per-task session, then confirms completion from `goals.json`. It falls back to DeepSeek V4.1 Flash for 30 minutes on provider errors read from the JSON events (even with exit 0) or an unauthenticated primary, and resumes the same session; retries crashes with backoff; skips no-progress tasks until the ledger changes; stops on uncommitted foreign changes, an in-progress Git operation or a Hermes Autowork job on the same repository; holds a `flock` lock; blocks pushes through Git config; forwards Ctrl+C and resumes interrupted tasks; keeps compact redacted records outside the repository. 20 fake-Pi tests in `tests/test_pi_autowork.py` cover the spec's 15 cases and more; ShellCheck is clean. Live smoke on a throwaway repository: GPT-6.1 Sol completed, committed, closed and archived a one-file task in 74 s (462k tokens). Fallback switching and a multi-task continuous run are unverified live (TOOLSET-094-65).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/project.md#continuous-pi-runner-2026-10-15), [usage](docs/cross-host.md#run-autowork-continuously), [Pi adapter](adapters/skills/autowork/SKILL.md).
- Scope: A standalone Bash runner, deterministic tests with a fake Pi and disposable repositories, and a concise usage guide; no change to Autowork's contracts, no scheduler, daemon or database.
- Acceptance: The spec's 15 test cases pass offline; ShellCheck passes; a bounded real Pi run completes one task in a disposable repository.
- Checks: `python3 -m unittest tests/test_pi_autowork.py`; `shellcheck scripts/pi-autowork.sh`; `python3 scripts/check.py`; one `--once` run against a disposable repository.
- Dependencies: None.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No push; no change to the Autowork skill.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-094-65 — Qualify the Pi runner's fallback and a multi-task run live

- [x] TOOLSET-094-65 — Qualify the Pi runner's fallback and a multi-task run live
- Status: done (2026-10-15). Live in a disposable repository with five one-file tasks and a bare `origin`: (1) a continuous run (`--max-cycles 2`) completed T1 and T2 once each on GPT-6.1 Sol (85 s, 74 s); (2) a wrapper gave the first primary run an empty Pi agent directory, so the real Pi exited 1 with "No API key found for openai-codex"; the runner first classified that as a crash and retried the primary (T3), which exposed a missing pattern; after the fix (TOOLSET-094-65 regression `test_missing_credentials_at_run_time_fall_back`) the same failure on T4 was a provider failure, the primary cooled for 30 minutes, and DeepSeek V4.1 Flash resumed T4 in the same session and completed it (2 commits, 32 s, $0.007 reported, `fallback_reason` recorded); (3) SIGINT 26 s into T5 stopped the real Pi promptly, the runner exited 130 and kept the in-flight record, and the next `--until-empty` run resumed T5 in the same session, completed it and exited on an empty queue. All five tasks are done once; `origin` has no refs; tests 21 passed and ShellCheck is clean.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/project.md#continuous-pi-runner-2026-10-15), [usage](docs/cross-host.md#run-autowork-continuously).
- Scope: In a disposable repository with two or three small tasks, run `--until-empty` live; then force the fallback (for example by making the primary fail authentication in a throwaway Pi agent directory) and confirm DeepSeek V4.1 Flash resumes and completes a task, and that Ctrl+C mid-task resumes cleanly.
- Acceptance: `runs.jsonl` shows each task completed once, a provider failure followed by a fallback completion with `fallback_reason`, and an interrupted run resumed in the same session; no push.
- Checks: `runs.jsonl`, `git log` of the disposable repository, and the runner's output.
- Dependencies: TOOLSET-093-01.
- Ownership: Toolset coordinator; spends OpenRouter credit, so run it on the owner's request.
- Exclusions: No run against a real project repository.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-095-48 — Run Pi Autowork from the main branch with per-task worktrees merged at the end

- [x] TOOLSET-095-48 — Run Pi Autowork from the main branch with per-task worktrees merged at the end
- Status: done (2026-10-15). Owner request: the runner works from the main branch, uses worktrees and merges everything at the end. `scripts/pi-autowork.sh` now refuses any branch but the main branch; each session creates `pi-autowork/<session>` from it in a worktree under the state directory and reads the queue there; each task runs in a fresh worktree branched from that tip, told to commit there and not merge; finished or partial work joins the integration branch; unfinished work stays in its worktree for review while other tasks continue; when the queue empties or the runner stops, the main branch is merged into the integration branch (Pi resolves conflicts once per session with Git Commit Push), the main checkout fast-forwards, and worktrees and branches are removed; uncommitted changes in the main checkout block only that last step and are reported as `Merge pending`. 25 fake-Pi tests pass four times in a row, including merge resolution, an unresolved conflict, a blocked fast-forward and a non-main branch; ShellCheck clean. Offline only; live run in TOOLSET-096-7e.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [usage](docs/cross-host.md#run-autowork-continuously), [plan](docs/project.md#continuous-pi-runner-2026-10-15).
- Scope: Worktree isolation and end-of-session merge in the runner, its tests and guide.
- Acceptance: Work lands on the main branch only through the end-of-session merge; the main checkout's uncommitted changes are never touched; a conflicting merge is resolved or reported pending with the branch kept.
- Checks: `python3 -m unittest tests/test_pi_autowork.py`; `shellcheck scripts/pi-autowork.sh`; `python3 scripts/check.py`.
- Dependencies: TOOLSET-094-65.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No push by the runner.
### TOOLSET-089-72 — Report parallel progress and metrics, with an end-to-end fixture and benchmark

- [x] TOOLSET-089-72 — Report parallel progress and metrics, with an end-to-end fixture and benchmark
- Status: done.
- Delivery stage: Verified isolated local candidate; canonical integration remains pending while canonical sessions are active.
- Evidence: Real CLI E2E/status suite passed five consecutive runs (9 tests per run). Combined integration/status suite passed 60 tests; independent corrective review approved. `python3 scripts/check.py` passed all four offline directories; eight native/model/integration modules excluded, with subprocess ResourceWarnings retained. `git diff --check` passed.
- Benchmark: Linux 7.0.0-31-generic x86_64, 24 logical CPUs, Python 3.12.14; disposable Git A/B/C tasks with one-second fake-worker sleeps, commits, validation, sequential integration and closure. `python3 scripts/bench_parallel.py`: one slot 6.796823 s, two slots 5.651354 s; elapsed-minus-sleep-critical-path overhead 3.796823 s / 3.651354 s. These include CLI/Git/validation/wait costs, not isolated coordinator CPU time or LLM speedups.
- Review rework (2026-10-15): Independent review reproduced a scheduling-sensitive acceptance assertion: delaying the initial status observation by one second failed with `active_workers` 0 versus 2 even though A/B overlapped. Replaced that instantaneous assertion with journal peak concurrency, preserving report-time overlap and C-after-closure assertions. The new delayed-observation regression failed before the change; the revised 10-test module passed five consecutive times and an independent re-review run. The original candidate's full offline gate passed four directories before this test-only rework; this is baseline evidence plus affected-module reruns, not a fresh full-suite run on the revised tree. Canonical integration remains pending.
- Corrective review: Reproduced and fixed inherited TOOLSET-088-a7 timeout bypass and checked/archived contract-drift loopholes. Also fixed status capacity after changing refill concurrency. Required acceptance is unchanged; native/model/live qualification remains TOOLSET-091-00.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15); reads the journal from TOOLSET-086-9f.
- Scope: Add `--parallel-status [--json]` printing the plan's table (header `AUTOWORK — PARALLEL`, `Workers: a/m active`, one row per task with state, worker slot, elapsed, blocked reason; then completed, failed and integration-queue counts) and, with `--json`, worktree, checks, commit and integration fields. Compute metrics from the journal: total wall time, worker time, integration time, waiting/blocked time, peak workers, conflict and retry counts. Add an end-to-end test with a disposable repository whose TODO has task A and B (independent, disjoint `Touches:`) and C (depends on A), driven through the real CLI with the fake worker: A and B overlap in time, C starts only after A is closed, and the final canonical checkout passes the fixture's own test. Add `scripts/bench_parallel.py` running the same controlled workload sequentially and with `--parallel 2`, printing elapsed times and coordinator overhead.
- Touches: skills/autowork/scripts/parallel_status.py, skills/autowork/scripts/test_parallel_e2e.py, scripts/bench_parallel.py, skills/autowork/scripts/task_execution.py
- Acceptance: Status output matches a golden snapshot for a fixed journal and stays under 25 lines for 4 workers; the A/B/C end-to-end test passes deterministically 5 times in a row; the benchmark's measured sequential and parallel times and overhead are recorded in this task's evidence with the machine and workload, without claiming LLM-worker speedups.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_e2e.py`; `python3 scripts/bench_parallel.py`; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-088-a7.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No live host workers (TOOLSET-091-00); no change to sequential output.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-097-57 — Install the Pi runner as a per-repository systemd user service

- [x] TOOLSET-097-57 — Install the Pi runner as a per-repository systemd user service
- Status: done (2026-10-15). Owner decision: background runners are set up from hermes-toolset, not by hand. `pi-autowork.sh --install-service [--repo PATH] [--allow-hermes]` writes the template unit `pi-autowork@.service` (working directory from the instance, `KillMode=mixed`, `KillSignal=SIGINT`, `SuccessExitStatus=130`, `Restart=on-abnormal`) and a 0600 environment file with the installer's `PATH` and `PI_AUTOWORK_*` settings, then reloads, enables and restarts `pi-autowork@<escaped path>`; it refuses a Hermes Autowork job on the repository without `--allow-hermes` and warns when lingering is off. `--remove-service` disables and stops the instance and removes its environment file. Two tests with a fake `systemctl` cover both; 27 runner tests and ShellCheck pass.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [usage](docs/cross-host.md#run-autowork-continuously).
- Scope: Service install/remove in the runner, tests and guide; no change to how a run behaves.
- Acceptance: One command installs and starts a repository's service; stopping it is the runner's graceful stop; deliberate exits do not restart it.
- Checks: `python3 -m unittest tests/test_pi_autowork.py`; `shellcheck scripts/pi-autowork.sh`; `python3 scripts/check.py`.
- Dependencies: TOOLSET-095-48.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No system-wide units; no automatic installation.

### TOOLSET-090-2d — Document parallel Autowork and wire it into each host

- [x] TOOLSET-090-2d — Document parallel Autowork and wire it into each host
- Status: done
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [Autowork skill](skills/autowork/SKILL.md), [adapter skill](adapters/skills/autowork/SKILL.md), [cross-host guide](docs/cross-host.md).
- Scope: Add a short parallel-mode section to `skills/autowork/SKILL.md` and a reference `skills/autowork/references/parallel-workers.md` with the coordinator loop (claim, dispatch, `--wait`, review report, `--integrate`, `--parallel-close`, metadata commit, refill), `Touches:`/`Resources:` authoring, conflict handling, worktrees, recovery and authority. Mirror the invocation in `adapters/skills/autowork/SKILL.md` (Claude Code: sequential unless `--worker-command` is given; Codex and Pi: their templates). Document the `Touches:`/`Resources:` fields in the shared TODO rules and Docs Sync so planners write them. Fix the stale "Delegation does not create Git worktrees" line in `references/accepted-plan-execution.md`. Update README (one short paragraph and a link, no internals), docs/workflows.md, docs/cross-host.md (host capability table), docs/testing.md and the CHANGELOG. Add tests: sequential `owner_cycle.py --apply` results are byte-identical to before for an existing fixture, and an unsupported host returns `SEQUENTIAL_FALLBACK`.
- Touches: skills/autowork/SKILL.md, skills/autowork/references/, adapters/skills/autowork/SKILL.md, skills/shared/TODO-WORKCENTER.md, skills/docs-sync/SKILL.md, README.md, docs/workflows.md, docs/cross-host.md, docs/testing.md, CHANGELOG.md, skills/autowork/scripts/test_parallel_compat.py
- Acceptance: Docs describe only implemented behavior and flags (checked against `--help`); the host table states which hosts run parallel workers and which fall back; compatibility and fallback tests pass; `docs.py check` passes; skill bundle and adapter tests pass.
- Checks: `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; `node --test tests/portable_pi.test.mjs`; `git diff --check`.
- Dependencies: TOOLSET-089-72.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No new Telegram command (the flag passes through `/autowork` arguments); no Hermes Agent changes.
- Delivery (2026-10-15): `skills/autowork/references/parallel-workers.md` (coordinator loop with exact outcomes, `--run` last, Touches/Resources admission, coordinator-owned root files, host templates and every fallback condition, held `-r2` retries, restart reconciliation, resource gate, release semantics); an opt-in section in `skills/autowork/SKILL.md` and `adapters/skills/autowork/SKILL.md` (Claude Code: sequential unless `--worker-command`; Codex and Pi: built-in templates); Touches/Resources authoring in the shared TODO rules and Docs Sync; the stale worktree line in `accepted-plan-execution.md` fixed; README, docs/workflows.md, docs/cross-host.md (host table), docs/testing.md and CHANGELOG updated.
- Checks run: every flag named in the new docs matches `owner_cycle.py --help` or the worker templates (`--no-ff` is the `git merge` flag integration uses); `test_parallel_compat.py` 5 passed, and its two golden tests also pass when run against the pre-parallel tree `b5092b3` (sequential output byte-identical with and without goals.json); fallback tests cover Claude Code without `--worker-command` and missing Hermes/Codex/Pi CLIs with no journal, slots, coordinator lease, worktrees or branches; `docs.py check` ok; `node --test tests/portable_pi.test.mjs` 3 passed; skill-policy, workflow-cycle, portable-package and update-bundle tests pass; `python3 scripts/check.py` passed all four offline directories; `git diff --check` clean.
- Independent review (2026-10-15) found and this task fixed: the documented `--integrate ... --run ... --timeout` order could not work (`--run` takes the rest of the line); `IDLE` was described as queue completion; missing outcomes, hold reasons, retry/restart/launch-failure rules, reconcile states, name-collision behavior, close's archive and cleanup scope, root-only coordinator files, undetected-host fallback and the release caveat; the test gained a goals.json golden, a clean `GIT_*` environment and a coordinator-lease assertion. Not changed: the `--worker-profile` help text (task_execution.py is outside this task's Touches).


<!-- archived from TODO.md -->

Source section: Next

Disposition: Superseded; not completed
Successors: TOOLSET-091-00
Reason: The measured startup path (native start_goal admission) is retired historical execution; current startup is owner_cycle selection, whose real-host timing TOOLSET-091-00 records. Planner's call in the 2026-10-15 replan.
Original task and unchecked acceptance retained below.

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


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-098-4c — Drive pi-autowork through the Parallel Autowork engine

- [x] TOOLSET-098-4c — Drive pi-autowork through the Parallel Autowork engine
- Status: done (2026-10-15), offline. Owner decision: use the toolset's own engine, no third-party orchestrator. `scripts/pi-autowork.sh` no longer selects tasks: it drives `owner_cycle.py --parallel` (dispatch with `--worker-command`, `--wait`, `--integrate` with `--run pi-autowork.sh --verify`, `--parallel-close`, coordinator metadata commit, refill, `--release` after the session merges into the main branch). `--worker` runs Pi on the engine prompt with model choice, JSON-event provider fallback that resumes the session, the push guard re-applied (the engine strips `GIT_*`) and `timeout --foreground` so the engine's process-group stop reaches Pi. `--verify` runs `PI_AUTOWORK_VALIDATE` then a read-only Pi review that must print `PI_AUTOWORK_VERIFY: pass` and leave the checkout unchanged. `--workers` 1-4 (default 2); `--status` maps slot states to pending/running/implemented/verifying/integrated/done/failed; `PI_AUTOWORK_MAX_COST` counts a rolling `PI_AUTOWORK_COST_WINDOW` over `runs.jsonl` from all processes. With `--allow-hermes` the engine lease keeps Pi and Hermes Autowork from owning tasks at once (tested both ways). Fixed an engine bug: a restarted interrupted/released worker was held as `unexpected worker branch` (`parallel_integrate.expected_branch`, regression in `test_parallel_integrate.py`). 24 runner tests (parallel overlap barrier, C after A, verification failure, tampering reviewer, blocked worker, fallback, missing credentials, interrupt/resume, budget persistence, merge conflict resolved and pending, dirty main, Hermes lease both ways, push guard, status/dry run, setup, service) and 106 engine tests pass; `python3 scripts/check.py` passes. Live qualification in TOOLSET-091-00.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [usage](docs/cross-host.md#run-autowork-continuously), [engine](skills/autowork/references/parallel-workers.md), [parallel plan](docs/project.md#parallel-autowork-2026-10-15).
- Scope: Replace the runner's own selection loop with the engine's coordinator loop; keep model selection, fallback, services, locks, shutdown, budgets and recovery.
- Acceptance: No second scheduler; tasks close only after verified integration; budgets survive restarts; Hermes and Pi never own a task at once; existing options keep working.
- Checks: `python3 -m unittest tests/test_pi_autowork.py`; engine tests in `skills/autowork/scripts`; `shellcheck scripts/pi-autowork.sh`; `python3 scripts/check.py`.
- Dependencies: TOOLSET-097-57.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No third-party orchestration; no push by the runner.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-091-00 — Qualify parallel Autowork with real host workers

- [x] TOOLSET-091-00 — Qualify parallel Autowork with real host workers
- Status: done (2026-10-15). Pi qualified live; Codex fails live and now falls back to sequential; Hermes workers not run, by owner decision (Hermes plans tasks, the pi-autowork service executes them with Pi workers), so `/autowork --parallel` from Hermes stays unqualified. Evidence below.
- Evidence (2026-10-15): disposable repository (A, B independent with `Touches:`; C depends on A; combined `check.sh`; bare `origin`).
  - **Pi qualified** (Pi 1.2.0, `openai-codex/gpt-6.1-sol`, workers through `pi-autowork.sh --worker` as `--worker-command`, Pi review as validation). Parallel run: A and B overlapped (peak 2 workers), A integrated while B ran, C dispatched only after A closed, sequential merge commits, combined check passed, 0 retries/conflicts, no push, wall 158 s (worker 162 s, integration 104 s). Sequential control (`--workers 1`): 240 s, one hold then a passing retry. Interruption: the coordinator was killed with SIGKILL while both workers ran; the restart adopted A's live worker (no second worker started), integrated B (finished meanwhile) and completed C after one held first attempt (its report listed an early failing check; the worker prompt now asks for final results only).
  - **Codex fails** (codex-cli 0.162.1, scripted coordinator following the documented loop): two workers ran at once and passed their checks, but neither could commit, because the workspace-write sandbox keeps Git metadata read-only; dispatch now returns `SEQUENTIAL_FALLBACK` for Codex workers.
  - **Hermes not run**: the scope excludes fleet profiles, and a disposable Hermes profile would be loaded by the live gateway; that needs the owner's go-ahead.
  - Found and fixed on the way: restarted interrupted/released workers were held as `unexpected worker branch`; a killed coordinator's helper kept the runner lock (helpers no longer inherit it); writer holds now name their processes.
- Decision (owner, 2026-10-15): Hermes workers are not needed; no disposable Hermes profile is created.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15).
- Scope: On a disposable local repository (not a fleet project) with three small real tasks (A, B independent; C depends on A), run `/autowork --parallel 2` from a Hermes coordinator with Hermes workers, then repeat with Codex and Pi workers where installed. Record per run: worker overlap, integration order, C waiting for A, combined test result, wall time against a sequential run of the same tasks, worker and integration time, and any held or interrupted slot. Interrupt one run's coordinator mid-way and confirm a restart adopts live workers without duplicates.
- Acceptance: Each qualified host shows two real workers overlapping in separate worktrees, sequential integration, C after A, a passing combined check and no push; the interruption test starts no duplicate worker; measured times recorded with host versions; any host that fails stays documented as sequential-only.
- Checks: `--parallel-status --json` at each step, the journal, `git log --graph` of the disposable repository, and the recorded elapsed times.
- Dependencies: TOOLSET-090-2d.
- Environment prerequisite: Installed host CLIs with working model access; owner availability to observe the run.
- Current evidence (2026-10-15): Hermes 0.22.0, Codex CLI 0.162.1 and Pi 1.2.0 are installed; model access and owner availability are not verified.
- Exclusions: No fleet repositories or profiles, no push, no cron schedule.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-064 — Give bundled skills trigger-first descriptions within Hermes' 60-character index

- [x] TOOLSET-064 — Give bundled skills trigger-first descriptions within Hermes' 60-character index
- Status: done
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [review findings](docs/project.md#new-skill-review-2026-10-15), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: Rewrite toolset-owned `description` fields over 60 characters (autoresearch, autowork, beautify-github-readme, cron-autowork, engineering, lgtm, plan-for-me, plan-with-me) to one trigger-first sentence; vendored Impeccable stays unchanged.
- Acceptance: Hermes' skill linter reports no `description-length` warning for toolset-owned skills, and a test enforces the limit.
- Checks: A regression over `skills/*/SKILL.md`, then `python3 scripts/check.py`.
- Dependencies: None.
- Exclusions: No vendored-file edits.
- Candidate: `autowork/TOOLSET-064` at `2e3ef49` combines the retained reviewed descriptions with main `7882845` and the reviewed TOOLSET-097-41 repair. The conflict-free refresh preserves every owned skill body against that pinned main. The description regression and all 40 Pi tests pass; the fresh full offline gate passes 556/689/212/8 tests across four directories (one skipped test; eight excluded modules). Bash syntax, docs/index validation and whitespace checks pass. The earlier Hermes linter result remains zero description-length warnings for the unchanged descriptions; no new independent review is claimed. The first combined gate failure remains retained, not relabeled passed.
- Planner's call: Preserve the reviewed combined implementation and refresh it against pinned main in the idle isolated candidate rather than overlapping canonical writers. The refresh merged without conflicts; the original independent approvals remain historical evidence, and this occurrence adds fresh offline qualification, not a new review. Main still matched `7882845` at final admission, but two active canonical sessions prevent integration. Keep both tasks open.
- Completion: Integrated locally by conflict-free fast-forward to 9f84355 after canonical writer admission cleared. Fresh combined full gate passed 558/698/212/8 tests (one skip, eight excluded modules); retained review and linter evidence applies to unchanged skill descriptions. No push or deployment.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-082 — Restore the OMH memory plugin on Hermes 0.22

- [x] TOOLSET-082 — Restore the OMH memory plugin on Hermes 0.22
- Status: done
- Goal: OMH-TRIM — Keep the OMH skills profiles use and drop the rest from every prompt.
- Sources: [plan](docs/project.md#omh-catalog-trim-2026-10-15), [OMH installer](install-omh.py), [bundle defaults](plugins/defaults.json), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: On Hermes 0.22.0, loading OMH 3.0.0 logs "Plugin 'omh' skipped: requires hermes >=0.21.1,<0.22.0, running 0.22.0", and `hermes memory status` in a profile whose `memory.provider` is `omh` reports the plugin as not installed, so OMH memory is likely inactive fleet-wide. Confirm across profiles, find the OMH release or pin that supports Hermes 0.22, and update `plugins/defaults.json`'s pinned `omh.source` (or document the incompatibility and the safe interim provider) without changing memory stores.
- Acceptance: `plugins/defaults.json` pins an OMH release whose plugin manifest admits Hermes 0.22 and whose skill names cover the trim's keep list; a fresh-install preview uses that pin; docs/memory.md records the incompatibility and the interim handling for profiles still on the old release; OMH stores and existing memories are untouched. Refreshing already installed profiles is TOOLSET-098-5d.
- Checks: `python3 -m unittest discover -s tests -p test_install_omh.py`; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No memory-store migration or deletion; no provider switch without the owner.
- Candidate: `autowork/TOOLSET-082` (bdc34d3) retains the reviewed official OMH v3.0.2 pin (manifest `>=0.21.1`), all 41 kept-name mappings, offline tests and interim guidance from c4644bb; refreshed against main 7882845. Independent review approved the TODO merge resolution; original pin/docs/tests are unchanged.
- Planner's call (2026-10-15 replan): split the live refresh of installed profiles into TOOLSET-098-5d so the reviewed offline pin can close; the live checks moved there unchanged.
- Planner's call (2026-10-16 recovery): while canonical admission is busy, qualify this retained candidate rather than repeat the TOOLSET-064 hold. The first full gate exposed the already-fixed nested-profile diagnostic; merge the reviewed TOOLSET-064/097-41 candidate instead of duplicating its fix. Preserve all three original task IDs and keep integration pending, with no live profile changes.
- Checks (2026-10-16): combined full offline gate passed 558/689/212/8 tests (one skip; eight modules excluded); focused OMH 28, Pi 40 and skill-description 1 passed; Bash syntax, docs/index validation and whitespace passed. The original failing gate remains failure evidence, not a pass.
- Recovery qualification (2026-10-16): reconciled this task's TODO status with its existing `in_progress` index entry; isolated owner admission now returns `EXECUTE`. A fresh standalone Pi run passes all 40 tests in 166.821 seconds, resolving the prior combined-command timeout without changing runner code; the interrupted run remains incomplete evidence. Fresh OMH 28 and description 1 tests, goals/docs validation, Bash syntax and whitespace checks pass. Canonical main still matches 7882845; one active canonical session prevents integration. No new full offline gate or independent review is claimed.
- Completion: Integrated locally by conflict-free fast-forward to 9f84355 after canonical writer admission cleared. Fresh combined full gate passed 558/698/212/8 tests (one skip, eight excluded modules); original reviewed pin, tests and guidance are preserved. Installed-profile refresh and native existing-store qualification remain TOOLSET-098-5d. No push or deployment.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-097-41 — Report the correct Hermes profile from nested installation paths

- [x] TOOLSET-097-41 — Report the correct Hermes profile from nested installation paths
- Status: done
- Goal: PI-RUNNER
- Sources: [accepted repository scope](docs/project.md#accepted-requirements), [Pi runner](scripts/pi-autowork.sh), [offline regressions](tests/test_pi_autowork.py), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: Repair the Hermes coexistence diagnostic when the installation root itself contains a profiles directory; derive the label relative to the selected root, not the first matching ancestor.
- Acceptance: Named and default-profile jobs display their actual profile below a nested installation root; active matching jobs still refuse execution and paused jobs stay excluded.
- Checks: `python3 -m unittest discover -s tests -p test_pi_autowork.py`; `python3 scripts/check.py`; `bash -n scripts/pi-autowork.sh`; `git diff --check`.
- Dependencies: None.
- Ownership: Next Autowork coordinator. Before starting, check the `pi-par` worktree under `.claude/worktrees/`, which held uncommitted edits to both touched files on 2026-10-15; adopt or wait for that writer instead of duplicating it.
- Touches: scripts/pi-autowork.sh, tests/test_pi_autowork.py
- Candidate: `autowork/pi-profile-reconcile` adopts only the implementation and regression from retained candidate `9625a6e` onto `73c6f7e`, preserving the newer parallel runner and service/worktree fixes. All 33 Pi tests, the full offline gate (four directories), Bash syntax, goals validation and whitespace checks passed; independent read-only review approved the two-file diff. Test subprocess/stream ResourceWarnings remain, and one offline test was skipped.
- Planner's call: Canonical writers prevent integration, not verification in an isolated candidate. Keep this task open until the reviewed candidate is integrated; do not import the old candidate's stale archive/index changes. Next action: integrate this branch only after the canonical writer gate clears, recheck changed inputs, then archive this task.
- Current evidence: Found by the toolset cron on 2026-10-15: the full offline gate fails one Pi test when the checkout path contains `/profiles/` (as in profile cron runs) and passes elsewhere.
- Completion: The reviewed nested-profile implementation and regression are integrated locally in 9f84355, preserving the current runner. Fresh combined full gate passed 558/698/212/8 tests (one skip, eight excluded modules). One unchanged Pi restart test failed an earlier attempt; all 40 Pi tests and then a fresh full gate passed on retry. No job mutation, push or deployment.
- Exclusions: No job mutation, provider execution, push or deployment; no change to coexistence refusal policy.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-072 — Cache the check receipt runtime inventory without losing drift detection

- [x] TOOLSET-072 — Cache the check receipt runtime inventory without losing drift detection
- Status: done
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [audit](docs/project.md#baseline-audit-toolset-068-2026-10-15), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md), [check_receipt.py](skills/autowork/scripts/check_receipt.py), [receipt tests](skills/autowork/scripts/test_check_receipt.py), [delivery tests](skills/autowork/scripts/test_delivery_state.py), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: In `check_receipt.runtime()`, memoize the `packages` list and `executable_sha256` per process, keyed by a cheap stamp: for packages, the `(path, st_mtime_ns, st_ino)` of every existing `sys.path` directory (installing, removing or upgrading a distribution adds or removes a `*.dist-info`/`*.egg-info` entry and changes its directory's mtime); for the executable, `(st_dev, st_ino, st_size, st_mtime_ns)` of `sys.executable`. Return the same receipt fields and values as today. Measured before (`376f7ed`): `test_delivery_state.py` 23 tests, about 45 s of call time in a normal run; profile 42 s of 110 s in package metadata and 7 s in executable hashing.
- Acceptance: Receipt contents are unchanged for an unchanged environment; a distribution directory added to a `sys.path` entry between the before and after `runtime()` calls is still reported as in-check drift (new regression test); replacing the executable file changes its hash; `test_check_receipt.py` and `test_delivery_state.py` pass; time for those two modules and for the Autowork directory is measured before and after on the same machine (3 runs each) and recorded.
- Checks: `cd skills/autowork/scripts && python3 -m unittest test_check_receipt test_delivery_state`; the new drift regression; `python3 scripts/check.py`; `python3 scripts/check.py --jobs 1` with `/usr/bin/time` 3 times; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to receipt schema, reuse rules or drift semantics; no caching across processes or on disk; no push.
- Planner's call (2026-10-16): Canonical integration remains occupied; skip that write, not verification, and advance this independent offline task. Adopt the idle original worktree's two attributable uncommitted files into `autowork/TOOLSET-072-recovery`, based on the combined TOOLSET-082/064/097-41 candidate at 20cbcc5. Preserve the original worktree unchanged. Actual writer inspection found no writer there; file timestamps predate this occurrence.
- Partial delivery: Process-local package/executable caches preserve receipt values and mutable-value isolation. Metadata-content stamps retain in-place upgrade detection; custom providers and inaccessible filesystem stamps fall back to uncached discovery. Independent review reproduced an unreadable-directory regression; a failing-then-passing regression fixes it, and re-review approved the exact two-file implementation.
- Qualification: 50 receipt tests passed; the receipt/delivery pair passes all 73 tests on three final runs. Same-machine Python 3.12 pair timings before: 72.477/75.685/74.835 s; final: 33.928/34.628/34.930 s, including nine additional regressions. These are focused timings, not full-gate speedup. The first final full gate passed Autowork 698 (one skip), Docs Sync 212 and delivery-policy 8, but failed one unchanged Pi runner restart test; all 40 Pi tests passed on retry. A fresh full-gate retry passed all four directories: 558/698/212/8 tests (one skip; eight excluded modules). A serial baseline gate was interrupted by the tool transport timeout and remains incomplete.
- Integration: Implementation is integrated locally in 9f84355 after canonical writer admission cleared. TOOLSET-064/082/097-41 were closed separately from their verified offline evidence. No push or deployment.
- Completion: All six interleaved serial offline gates passed on Linux x86_64, Python 3.12.14: baseline 20cbcc5 versus final 9f84355, three runs each with `/usr/bin/time python3 scripts/check.py --jobs 1`. Full-gate wall seconds before: 495.42/468.81/446.33; after: 423.98/420.92/416.30 (medians 468.81 → 420.92, 10.2% lower). Autowork unittest suite elapsed before: 190.695/189.849/183.746; after: 140.612/143.317/135.945 (medians 189.849 → 140.612, 25.9% lower); this excludes subprocess startup/import and is not default parallel-gate wall time. Baseline counts 558/689/212/8; final 558/698/212/8, each with one skip and eight excluded modules. Every tracked input matched the named commit and stayed unchanged; the interpreter/package snapshot captured during the first baseline matched after run six. Independent method review identified parser/completion checks; separate validation requires six zero exits, exact four-directory summaries and inventories, and rejects missing-summary cross-block attribution. Prior focused final-pair receipts were pre-commit candidates whose recorded inputs match 9f84355. Details: [verification](docs/testing.md#verify).


<!-- archived from TODO.md -->

Source section: Now

### AUDIT-QUOTED-SECRET — Redact complete quoted credential values in fleet observations

- [x] AUDIT-QUOTED-SECRET — Redact complete quoted credential values in fleet observations
- Status: done
- Verified implementation: Complete quoted values are masked before delimiter redaction; complete JSON documents are decoded and scrubbed before re-encoding. Initial regression reproduced 72 failures; independent review found two serialized-message cases, reproduced and repaired. Final independent review approved the source; its in-memory removal controls failed as expected.
- Progress: Original 25 focused checks and Python 3.12 gate passed. After reconciling newer canonical task-ID/planning changes, 39 focused collector/response tests and the Python 3.12 offline gate passed 506 / 581 / 212 / 8 tests, one skip and eight excluded modules. RED controls reproduced scrubber stack exhaustion, JSON-key disclosure and contextual/numeric masking regressions; the decoded envelope now supplements rather than bypasses existing masking. Final independent review approved; 1,304 differential cases included 1,167 baseline-masked cases with zero regressions. Same-input read-only response replay covered all discovered profiles/jobs and preserved source bytes and existing projections. Integration and installed adoption remain unverified; no second collector or worker ran.
- Planner's call: Keep canonical integration and native scanned deployment open; current live canonical writers and the retained scan refusal are not permission to bypass either gate. Extend this coherent redaction batch to the disjoint consultation consumer: its JSON scrubber could abort original-evidence projection on deep envelopes and left credential-bearing keys/contextual credential fields visible. No product worker or schedule recovery is inferred.
- Verification (consultation extension): Two new regressions reproduced 14 masking failures and one stack-exhaustion error before the fix. The helper now redacts JSON keys and contextual credential fields while preserving valid shallow JSON; parsing/scrubbing stack exhaustion returns an explicit redacted sentinel. The original-evidence regression verifies read-only database bytes. All 39 consultation tests passed; the Python 3.12 offline gate passed 508 / 591 / 212 / 8 tests with one skip and eight excluded modules. Independent review approved with 283 synthetic differential probes and zero observed masking, exception, idempotence or shallow-JSON regressions. Same-input read-only replay covered all discovered profiles/jobs, with unchanged real projections and synthetic RED-to-GREEN controls. Installed adoption remains unverified; no second collector or consultation wave ran.
- Verification (Cookie consultation boundary): Four synthetic regression cases reproduced Cookie disclosure in original-evidence injection. Added Cookie to the existing assignment, quoted-value and JSON-key vocabularies; the composed regression also checks reply/stdout/stderr projection, idempotence, parseable shallow JSON and unchanged fixture database bytes. Independent review approved with a four-failure in-memory removal control. All 40 consultation tests and the Python 3.12 offline gate passed (509 / 623 / 212 / 8 tests; one skip, eight excluded modules). This bounded hardening does not reset the canonical integration hold or establish worker recovery; arbitrary unquoted multi-cookie header tails are outside this slice.
- Verification (partial contextual keys): The planner retained the canonical integration/deployment hold and chose a disjoint confidentiality repair in the same task. A composed regression reproduced 24 leaks from quoted contextual keys in malformed JSON/header text before the fix. Both existing assignment expressions now accept the closing key quote; original-evidence injection, reply/stdout/stderr and nested valid envelopes mask closed, unterminated and numeric values without changing fixture database bytes. All 41 consultation tests and the Python 3.12 offline gate passed (514 / 671 / 212 / 8 tests; one skip, eight excluded modules). Independent review approved the exact source, reproduced 24 pre-fix failures in memory and passed 96 additional checks. Read-only installed/candidate response and original-evidence replays matched on real inputs; the installed synthetic leak persists and the candidate masks it. No canonical integration, installed adoption or product recovery is inferred.
- Verification (whole Cookie header): Planner's call: retain the unavailable canonical integration/scanned-deployment operations and repair the independently reproduced consultation leak from unquoted multi-cookie headers within this confidentiality batch. Two composed cases failed before repair. Whole-header masking now follows quoted-value masking so multiline quoted tails stay protected; independent review caught the initial ordering regression, two new cases reproduced it, and the corrected exact source was approved. All 41 consultation tests and the Python 3.12 offline gate pass; the review's in-memory baseline control reproduces two failures and 16 additional probes pass. This does not reset primary-blocker history or establish installed adoption or worker recovery.
- Verification (Authorization header schemes): Planner's call: preserve the still-held integration and scanned-deployment operations; fix the independently reproduced confidentiality disclosure from Basic, Digest and Negotiate Authorization headers within this retained batch. Four composed original-evidence/reply projection cases failed before repair. Existing whole-header masking now includes Authorization and Proxy-Authorization after quoted-value masking. Independent review approves the exact source, with four failing HEAD controls and four additional before/after probes; all 41 consultation tests and the Python 3.12 offline gate pass (514 / 671 / 212 / 8 tests, one skip and eight excluded modules). This security repair neither changes task admission nor resets the primary hold.
- Verification (retained parallel gate correction): Planner's call: preserve the canonical integration/scanned-deployment hold and recover the existing scheduling-sensitive test correction rather than extend adjacent redaction hardening. A delayed real-CLI status observation reproduced `0 != 2`; the retained correction checks journal peak concurrency while preserving report-time overlap and dependency assertions. All ten focused parallel acceptance tests pass, including the delayed observation. Reconciled newer canonical Pi idle-session/worktree-preservation changes without replacing them. Aggregate offline qualification initially failed under host load at the unchanged real resource gate; retain that failure separately from the demonstrated assertion repair and do not waive the gate.
- Reconciliation: Preserved the newer canonical Pi/Touches and readoption implementation. Independent review reproduced inherited priority drift: TOOLSET-099-87 was absent from the recorded order and generated coverage. Planner's call: repair that bounded selection gate with the supported revision-guarded reorder/render, not another masking extension. The same selector now reports synced; archive bytes and an unchanged second render are preserved. Canonical integration and scanned deployment remain separate open operations.
- Remaining action: Recheck canonical writers; integrate the reviewed candidate when the supported writer check is CLEAR, then verify installed helper hashes and the same read-only consumer. The native scanned updater's existing refusal requires its own supported approval; do not repeat an unchanged scan or bypass it. No push or schedule activation.
- Goal: RECOVERY — Preserve credential boundaries during read-only fleet collection.
- Sources: [collector](skills/autowork/scripts/audit_profiles.py), [response regressions](skills/autowork/scripts/test_response_tail.py), [consultation consumer](scripts/profile-consult.py), [consultation regressions](tests/test_profile_consult.py), [testing contract](docs/testing.md).
- Scope: Fix `safe()` masking of quoted credential values containing commas, semicolons, newlines, escapes or an omitted closing quote; cover the actual response consumer without changing collection cursors. Apply the same bounded JSON confidentiality/stack-safety boundary to consultation `redact()` without altering discovery, transport, authority or reuse policy.
- Acceptance: No quoted-value suffix survives in projected responses; ordinary diagnostics remain; source bytes and cursor history remain untouched. Consultation JSON keys/contextual credential fields are masked, shallow JSON remains parseable and stack-exhausting envelopes cannot abort evidence projection. Independent review approves the exact candidate. Integration/deployment remain separate if canonical writers are active.
- Checks: Failing-then-passing response regression, focused collector suites, Python 3.12 offline gate, same-input read-only consumer replay and `git diff --check`.
- Dependencies: None.
- Exclusions: No product, credential, runtime, sibling profile or schedule mutation; no push.
- Local closeout: Integrated as 4b79912 after independent exact-tree review and the complete Python 3.12 offline gate (562/709/212/8 tests, one skip, eight excluded modules). Same canonical read-only consumer passes; original output and database bytes are preserved during replay. Installed adoption remains open under TOOLSET-101-f6; no deployment or recovered product worker is claimed.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-092-18 — Reject in-profile output directory aliases during fleet collection

- [x] TOOLSET-092-18 — Reject in-profile output directory aliases during fleet collection
- Status: done
- Goal: RECOVERY
- Sources: [collector](skills/autowork/scripts/audit_profiles.py), [response regressions](skills/autowork/scripts/test_response_tail.py), [maintenance contract](skills/autowork/references/profile-feedback.md).
- Scope: Reject response directories redirected to another location inside the same profile, including an aliased output parent; keep ordinary job directories and source bytes untouched.
- Acceptance: Aliases produce an explicit gap and no falsely attributed response; a healthy neighboring job is still collected; independent review approves the candidate. Canonical integration and managed deployment remain separate gates.
- Checks: `python3.12 -m unittest test_response_tail test_audit_profiles test_collector_correctness` from `skills/autowork/scripts`; `python3.12 scripts/check.py`; same-input read-only response-consumer replay; `git diff --check`.
- Dependencies: None.
- Ownership: Current shared-source maintenance coordinator.
- Planner's call: Skip only the busy canonical integration operation for AUDIT-QUOTED-SECRET; implement this independently reproduced collector identity-boundary repair in the retained isolated candidate. It neither resets that hold nor proves product recovery.
- Progress: Two new fixture regressions failed before repair. Collector now checks exact resolved job-directory identity as well as profile containment. Focused collector suites pass 41 tests; independent review approves. Reconciled newer canonical source and repaired a consultation-test scheduling assumption exposed by the aggregate gate: mock outcomes now bind to profile identity, not thread call order. Forced reverse-order control fails before repair and passes afterward. Python 3.12 offline qualification passes 508 / 623 / 212 / 8 tests, one skip and eight excluded modules; metadata/docs and whitespace checks pass. Real read-only response projections remain unchanged across all discovered profiles/jobs, preserving source bytes. Canonical integration and installed adoption remain pending; this does not reset AUDIT-QUOTED-SECRET hold history or establish worker recovery.
- Exclusions: No product, schedule, sibling profile, credential, live-service or upstream Agent edits; no push.
- Local closeout: Integrated as 4b79912 after independent exact-tree review and the complete Python 3.12 offline gate (562/709/212/8 tests, one skip, eight excluded modules). Same canonical read-only consumer passes; original output and database bytes are preserved during replay. Installed adoption remains open under TOOLSET-101-f6; no deployment or recovered product worker is claimed.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-100-78 — Retain execution evidence for every existing profile job

- [x] TOOLSET-100-78 — Retain execution evidence for every existing profile job
- Status: done
- Goal: RECOVERY
- Sources: [collector](skills/autowork/scripts/audit_profiles.py), [regressions](skills/autowork/scripts/test_collector_correctness.py), [verification](docs/testing.md).
- Scope: Collect up to twelve recent execution records per existing job instead of twelve across a profile; preserve chronological output, redaction and read-only behavior. No changes to log collection or response framing.
- Acceptance: A busy sync job cannot hide an older paused development job's records; removed jobs are excluded; empty jobs produce no execution rows; unknown job schemas fail closed; source bytes are unchanged. Independent review approves the exact candidate.
- Checks: `python3 -m unittest test_collector_correctness test_audit_profiles test_response_tail` in `skills/autowork/scripts`; `python3 scripts/check.py`; read-only execution metadata replay; `git diff --check`.
- Dependencies: None.
- Ownership: Current shared-source maintenance coordinator.
- Planner's call: Skip only the held canonical integration and scanned deployment operations; fix the independently reproduced cross-job evidence starvation in the retained candidate. This neither resets AUDIT-QUOTED-SECRET hold history nor proves worker recovery.
- Progress: The starvation regression fails before repair. Independent review found lookup used redacted IDs; a new RED regression reproduced that omission and raw IDs now remain SQL-only inputs. All 44 focused tests pass. Read-only replay restores twelve paused-development records while retaining twelve sync records, with unchanged database bytes. Canonical inclusion and managed deployment remain pending; final review/gate evidence is retained privately.
- Exclusions: No product, schedule, sibling profile, credentials, live-service or Agent edits; no push.
- Local closeout: Integrated as 4b79912 after independent exact-tree review and the complete Python 3.12 offline gate (562/709/212/8 tests, one skip, eight excluded modules). Same canonical read-only consumer passes; original output and database bytes are preserved during replay. Installed adoption remains open under TOOLSET-101-f6; no deployment or recovered product worker is claimed.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-073 — Measure subprocess coverage, then review identical and subset test groups

- [x] TOOLSET-073 — Measure subprocess coverage, then review identical and subset test groups
- Status: done
- Evidence: Source de0f3ac; scratch subprocess measurement recorded 1,278/1,491 test contexts. All 31 large groups and five slow subset cases classified in [the assertion audit](docs/test-suite-audit.md); no removals, one measured fixture-cost successor TOOLSET-102-ea. Protocol updated, no tests/source changed. Required goal/docs/whitespace checks passed; ordinary `python3 scripts/check.py` passed 562/709/212/8 tests, one skip/eight excluded. Retained instrumented cache failure passed after harness output isolation; no full instrumented green claim.
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [audit](docs/project.md#baseline-audit-toolset-068-2026-10-15), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md).
- Scope: In a scratch directory, rerun per-test coverage with subprocess measurement (coverage.py `COVERAGE_PROCESS_START` with a scratch `sitecustomize.py` or `.pth`, `parallel = True`, then `coverage combine`), so the 493 tests without records gain them. Recompute identical and strict-subset groups. Read every group of 3 or more and every subset case among the 30 slowest tests; classify each as distinct contract, parametrize candidate or removal candidate under the protocol's Keep rules. Add the subprocess-coverage recipe to the protocol's "Measure first" section. Record results in the audit section and up to three follow-up tasks with exact tests and measured before values.
- Acceptance: Per-test records exist for at least 1,150 of the 1,253 tests or the shortfall is explained; every group read has a recorded classification with its reason; removal candidates name the remaining test that covers their behavior; no test or source file outside the protocol changes.
- Checks: `python3 skills/docs-sync/scripts/goals.py validate .`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --stat`; `git diff --check`.
- Dependencies: None.
- Prior work: TOOLSET-068 (done, archived).
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No test removal or consolidation in this task; no repository dependency on coverage plugins; no push.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-103-fe — Preserve native cron response framing in fleet evidence

- [x] TOOLSET-103-fe — Preserve native cron response framing in fleet evidence
- Status: done
- Evidence: Reviewed source tree 23b46fb938cd9cbe9bfcab014602880092f56569; original RED lost the opening blocker, corrected response tests and consultation tests pass. Full Python 3.12 offline retry passed 562/712/212/8 tests, one skip and eight excluded modules with no source drift. Initial full run's unrelated idle-runner log-line assertion failed; unchanged focused and complete reruns passed, with the original failure retained. Independent exact-tree source review approved. Read-only fleet replay validated 20 complete native answers, including 12 formerly tail-truncated files; source outputs stayed unchanged. Installed adoption remains open under TOOLSET-101-f6.
- Goal: RECOVERY
- Sources: [accepted maintenance scope](docs/project.md#accepted-requirements), [feedback contract](skills/autowork/references/profile-feedback.md).
- Touches: skills/autowork/scripts/audit_profiles.py, skills/autowork/scripts/cron_output.py, scripts/profile-consult.py, skills/autowork/scripts/test_response_tail.py, skills/autowork/references/profile-feedback.md, docs/testing.md, CHANGELOG.md
- Scope: The collector currently splits at the last Response heading, losing a native answer's opening blocker when that answer itself quotes the heading. Reuse the consultation helper's character-framed parser for bounded native outputs; retain explicitly unverified legacy tails. Preserve response redaction, exact job-directory checks and read-only source bytes.
- Acceptance: A complete native answer survives embedded headings and Unicode; malformed or oversized framed outputs produce explicit gaps instead of a guessed response. Existing legacy-tail, confidentiality, ranking and consultation reuse regressions pass. The same read-only fleet response consumer returns exact framed bodies within its display bound, without product or job mutations.
- Checks: RED/GREEN response-tail regression; python3 -m unittest discover -s skills/autowork/scripts -p test_response_tail.py; python3 -m unittest discover -s tests -p test_profile_consult.py; python3 scripts/check.py; exact-tree independent review; same-consumer read-only replay; git diff --check.
- Dependencies: None.
- Ownership: Default shared-source maintainer under existing audit repair authority.
- Planner's call: Skip only TOOLSET-101-f6's already-separated installed adoption because its native scan approval remains unavailable. This independent reporting repair does not clear or reset that primary hold.
- Exclusions: No scan bypass, installation, product/Agent edits, schedule changes, worker launch, push or live qualification.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-102-ea — Replace the empty-queue Pi test warm-up with equivalent completed-session setup

- [x] TOOLSET-102-ea — Replace the empty-queue Pi test warm-up with equivalent completed-session setup
- Status: done
- Delivery evidence: [Measured fixture result](docs/test-suite-audit.md#completed-session-fixture-result-toolset-102-ea): focused wall median 5.390 to 0.709 s (86.8% lower); the changed test plus unchanged composed sibling retain all 1,536 owned Python lines and 403 branch arcs in paired subprocess-attributed runs. Normal module 40 passed; final offline gate 562/712/212/8 passed, one skip/eight exclusions. Independent review approved after correcting historical coordinator payloads and adding a pre-dispatch real status assertion. Mutation score not measured; no runtime/model/live change.
- Method: Bundled Ponytail fallback reused the existing task-text fixture and real shell runner; omitted duplicate worker/reviewer warm-up. The test-suite-optimization protocol kept assertions and composed coverage, measured ordinary timing separately, and retained failed/incomplete harness evidence in the linked result.
- Goal: TEST-SUITE
- Payoff: Reduce real Git/fake-worker fixture cost without reducing defect detection.
- Sources: [audit decision](docs/project.md#subprocess-coverage-audit-toolset-073-2026-10-16), [assertion review](docs/test-suite-audit.md#bounded-follow-up), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md).
- Touches: tests/test_pi_autowork.py
- Scope: Optimize only `EngineTests.test_empty_queue_calls_no_model` and the smallest needed fixture helper. Replace its full A/B/C warm-up with equivalent completed-session setup; first inspect the warm-up's actual task/archive/session artifacts, then preserve every artifact relevant to the second invocation. Keep its named test, real shell-runner entrypoint, fresh mutable fixture and complete empty-rerun assertions. Baseline at de0f3ac: three ordinary wall times 5.158/5.003/5.187 s (median 5.158 s); instrumented 19.433 s is not the baseline.
- Acceptance: The empty rerun still exits successfully, reports `Queue empty` and records zero fake-model calls; no stale session causes dispatch. Existing task/archive/session semantics and all assertions remain. The changed test and full normal offline gate pass; touched owned-source line and branch coverage do not drop in same-config before/after runs with subprocess attribution. Report same-machine three-run wall medians even if no speedup. Mutation score remains not measured unless a tool is already available; no new dependency.
- Checks: `python3 -m unittest discover -s tests -p test_pi_autowork.py`; `python3 scripts/check.py`; three focused ordinary timings and paired scratch subprocess line/branch coverage of the exact test; `git diff --check`.
- Dependencies: None.
- Prior work: TOOLSET-073 (audit and measured baseline delivered before this task).
- Ownership: Toolset coordinator under Autowork local repository authority.
- Planner's call: Prefer this measured fixture-cost seam to unmeasured thin-wrapper parametrization; no test removal or new model/live operation is authorized.
- Exclusions: No weakened assertions, no runner/source changes, no live model or fleet repository, no coverage plugin dependency, no push.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-104-cc — Keep offline test discovery inside real owned directories

- [x] TOOLSET-104-cc — Keep offline test discovery inside real owned directories
- Status: done
- Goal: TEST-SUITE
- Sources: [offline verification](docs/testing.md#verify), scripts/check.py, tests/test_check.py.
- Scope: Skip maintained test directories when any component beneath the repository root is a symlink, not only the final directory. Preserve import-free discovery and ordinary suite execution.
- Touches: scripts/check.py, tests/test_check.py, docs/testing.md, CHANGELOG.md
- Acceptance: Symlinks at tests, skills, workflow and scripts levels cannot import external test modules; normal owned tests still list and run. A symlink alias for the checkout root remains supported.
- Checks: `python3 tests/test_check.py`; `python3 scripts/check.py`; `git diff --check`; independent diff review.
- Dependencies: None.
- Ownership: Current Toolset coordinator under broad repository-development authority.
- Planner's call: Skip live/model and installed-profile queue work without changing its acceptance. Reuse the existing live qualification tasks. Repair the demonstrated offline discovery seam instead; no new dependency or runner redesign.
- Verification: Focused checker suite passed 11 tests, including four symlink placements and checkout aliases. Independent review approved the exact code/test/docs hashes. Initial full gate ran 563/712/212/8 tests but failed one existing Pi restart assertion comparing whole timestamped log lines; its focused retry and a fresh complete 563-test top-level directory passed without code changes. Combined directory evidence passes; the original full invocation remains failed. One skip and eight excluded modules remain; ResourceWarnings were emitted.
- Method: Ponytail bundled fallback; reuse pathlib and the existing discovery loop; omit new dependencies and sandbox claims. `git diff --check` passed.
- Exclusions: No live tests, deployment, scheduler changes, push or upstream Agent edits. This is a static discovery boundary, not a hostile filesystem-race sandbox.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-105-79 — Make the Pi restart PID assertion independent of log timestamps

- [x] TOOLSET-105-79 — Make the Pi restart PID assertion independent of log timestamps
- Status: done
- Evidence: Deterministic original assertion failed `2 != 1`; repaired focused journey and full 40-test Pi module passed. Negative replay rejected a changed PID, one startup and no startups. Independent exact-source review approved and reran the focused journey. `python3 scripts/check.py` passed 563/712/212/8 offline tests, one skip/eight exclusions. No runtime or live-model qualification change.
- Goal: TEST-SUITE
- Sources: [verification](docs/testing.md#verify), tests/test_pi_autowork.py, scripts/pi-autowork.sh.
- Scope: Repair the idle-update regression's comparison of timestamped startup lines; force different display timestamps across the exec restart and compare actual process IDs. Preserve update, queue completion and signal-exit assertions.
- Acceptance: The real fake-Pi update journey passes with different startup timestamps and proves at least two startup events retain the original runner PID; different PIDs still fail the assertion.
- Checks: Deterministic old-assertion failure, focused restart test, complete Pi module, `python3 scripts/check.py`, independent review, ledger validation and whitespace check.
- Dependencies: None.
- Ownership: Current Toolset coordinator under autonomous repository authority.
- Touches: tests/test_pi_autowork.py, docs/testing.md, CHANGELOG.md.
- Exclusions: No runner runtime change, live models, installed profile edits, push or deployment.
- Planner's call: Small independent fixture correction. Skip TOOLSET-099-87's already separated live qualification under TOOLSET-096-7e; no permission for that excluded operation is inferred. Choose deterministic display-time variation rather than sleeps across a real minute boundary or weaker restart assertions.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-106-5d — Mask complete credential-header lines in fleet collector evidence

- [x] TOOLSET-106-5d — Mask complete credential-header lines in fleet collector evidence
- Status: done
- Evidence: Ten native/legacy header regression cases fail before repair and pass after; 48 focused collector tests and the full Python 3.12 offline gate pass (563/713/212/8, one skip/eight exclusions). Independent exact-source review approved. Same read-only synthetic consumer passes; installed adoption remains TOOLSET-101-f6.
- Goal: RECOVERY
- Sources: [accepted requirements](docs/project.md#accepted-requirements), [collector](skills/autowork/scripts/audit_profiles.py), [response regressions](skills/autowork/scripts/test_response_tail.py), [verification](docs/testing.md).
- Scope: Reuse the consultation helper's full-line HTTP credential-header masking in the fleet collector before generic delimiter masking. Preserve native/legacy response identity, surrounding diagnostics and read-only source bytes.
- Acceptance: Cookie, Set-Cookie, Authorization and Proxy-Authorization credential tails after commas/semicolons are absent from collector response evidence; case/indentation variants pass in native and legacy consumers; unrelated status/check lines survive. Existing response/collector tests and the complete offline gate pass with independent exact-source review.
- Checks: `python3 -m unittest discover -s skills/autowork/scripts -p test_response_tail.py`; focused collector union; `python3 scripts/check.py`; same read-only synthetic consumer before/after; `git diff --check`.
- Dependencies: None.
- Ownership: Shared-source maintenance coordinator under the existing audit repair authority.
- Touches: skills/autowork/scripts/audit_profiles.py, skills/autowork/scripts/test_response_tail.py, docs/testing.md, CHANGELOG.md
- Exclusions: No push, installed scan override, profile/job/product writes, worker replacement, schedule activation or comprehensive-redaction claim. Installed adoption stays open under TOOLSET-101-f6.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-107-93 — Ignore commented-out document anchors

- [x] TOOLSET-107-93 — Ignore commented-out document anchors
- Status: done
- Evidence: Reproduced hidden-anchor false passes and reviewer-found literal-marker regressions before repair; 22 focused CLI tests passed; independent re-review approved after rework; Python 3.12 `scripts/check.py` passed 563/713/215/8 tests (one skip, eight excluded modules); repository docs check passed. Offline only.
- Goal: DOCS-COMPLETENESS
- Sources: [verification contract](docs/testing.md#verify), skills/docs-sync/scripts/docs.py, skills/docs-sync/scripts/test_docs_manifest.py.
- Scope: Exclude HTML comments from the document-anchor inventory using the existing comment/code-span handling. Preserve visible headings, duplicate numbering, explicit anchors and literal comment markers in inline code.
- Acceptance: CLI checks reject links and mapped roles targeting hidden headings or HTML anchors, including unclosed comments; hidden headings do not consume visible duplicate suffixes. Valid visible targets pass and input files remain unchanged.
- Checks: `python3 -m unittest discover -s skills/docs-sync/scripts -p test_docs_manifest.py`; `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; independent diff review; `git diff --check`.
- Dependencies: None.
- Ownership: Current Toolset coordinator under autonomous repository-development authority.
- Touches: skills/docs-sync/scripts/docs.py, skills/docs-sync/scripts/test_docs_manifest.py, docs/testing.md
- Exclusions: No external fetching, renderer replacement, installed-profile updates or live qualification.
- Planner's call: TOOLSET-099-87's excluded live acceptance remains separately tracked by TOOLSET-096-7e; skip it without waiver. Fix this independently reproduced docs-checker defect rather than repeat a live hold or add another Pi refusal guard.
