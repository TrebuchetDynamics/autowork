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
- Scope: Gateway logs on 2026-10-14 show 44 failed reads of `<profile>/autowork/state.json` across bravo, toolset and landing, where no run had written the journal; it exists in only 3 of 9 profiles. Say the journal may be absent, check for it instead of reading blindly, and create it when the first run records progress.
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
