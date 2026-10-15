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
