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


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-108-21 — Retain two readable cron responses across a damaged newest output

- [x] TOOLSET-108-21 — Retain two readable cron responses across a damaged newest output
- Status: done.
- Evidence: Reproduced one-versus-two response loss; all 22 response tests and 12 audit tests pass. Independent exact-source review approved, including a discriminating private mutation. Complete Python 3.12 offline gate passed 563/715/215/8 tests, one skip/eight excluded modules. Identical read-only replay retains two prior frames with ranks 3/2 and both latest=false. Source integrated locally; installation remains gated under TOOLSET-101-f6.
- Goal: RECOVERY
- Sources: [maintenance contract](skills/autowork/references/profile-feedback.md), [response consumer](skills/autowork/scripts/audit_profiles.py), [regressions](skills/autowork/scripts/test_response_tail.py).
- Scope: The response consumer currently slices the newest two filenames before validation; one damaged frame drops the preceding healthy comparison. Inspect at most twelve newest regular output files until two readable responses are retained. Preserve invalid-file gaps, literal filename ranks, latest-file identity, source bytes and the unproved execution-binding boundary.
- Acceptance: With two healthy native frames followed by a damaged frame, return both healthy responses in chronological filename order, ranks 3 and 2, neither labeled latest; report the damaged frame. Stop after two readable outputs or twelve candidates, reporting any uninspected older history.
- Checks: Failing-then-passing response-consumer regression, focused audit/consultation tests, Python 3.12 `scripts/check.py`, independent exact-source review and identical read-only consumer replay.
- Dependencies: None.
- Ownership: Current authorized shared-source maintenance coordinator.
- Touches: skills/autowork/scripts/audit_profiles.py, skills/autowork/scripts/test_response_tail.py, skills/autowork/references/profile-feedback.md
- Exclusions: No product writes, publication, schedule changes, worker launch or native scan override. Installed adoption remains TOOLSET-101-f6.
- Planner's call: Skip the already-separated native installation gate and excluded live backlog; deliver this independently useful evidence-consumer fix without claiming worker recovery.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-109-f1 — Keep generated document anchors unique across suffix collisions

- [x] TOOLSET-109-f1 — Keep generated document anchors unique across suffix collisions
- Status: done
- Goal: DOCS-COMPLETENESS
- Sources: [accepted document checks](docs/project.md#checkable-core-document-completeness), [checker](skills/docs-sync/scripts/docs.py).
- Scope: Resolve heading slug collisions against all previously generated heading IDs; retain explicit HTML anchor handling, comments and fenced-code behavior. No new dependency or live operation.
- Acceptance: Repeated headings after an explicitly suffixed heading get distinct IDs; links and mapped manifest fragments to those generated IDs validate; nonexistent suffixes still fail.
- Checks: `python3 -m unittest discover -s skills/docs-sync/scripts -p test_docs_manifest.py`; `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --check`.
- Dependencies: None.
- Ownership: Current Autowork coordinator.
- Evidence: Three collision scenarios failed before repair; all 23 focused CLI tests passed after repair. Python 3.12 `python3 scripts/check.py` passed 563/715/216/8 tests, one skip/eight excluded modules. Independent exact-source review approved; docs check and whitespace check passed. Offline only; no deployment.
- Touches: skills/docs-sync/scripts/docs.py, skills/docs-sync/scripts/test_docs_manifest.py, skills/docs-sync/references/document-scaffold.md
- Planner's call: Small independent maintenance fix under repository authority. TOOLSET-099-87 remains open with live qualification already separated into TOOLSET-096-7e; other queued tasks require excluded model/live/deployment or cross-repository actions. Skip those operations, not their acceptance. Reuse the current checker and standard-library sets; do not introduce a Markdown parser.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-110-61 — Preserve offline check results with non-UTF-8 subprocess diagnostics

- [x] TOOLSET-110-61 — Preserve offline check results with non-UTF-8 subprocess diagnostics
- Status: done
- Goal: TEST-SUITE
- Sources: [offline gate](docs/testing.md#verify), scripts/check.py, tests/test_check.py.
- Scope: Decode captured unittest diagnostics as UTF-8 with replacement for malformed bytes, retaining process exit verdicts and ordered sibling-directory output.
- Touches: scripts/check.py, tests/test_check.py, docs/testing.md, CHANGELOG.md
- Acceptance: Invalid diagnostic bytes do not crash aggregation; successful and failing suites retain their verdicts and sibling output appears in the final summary.
- Checks: `python3 -m unittest discover -s tests -p test_check.py`; `python3 scripts/check.py`; independent review; `git diff --check`.
- Dependencies: None.
- Ownership: Current Autowork coordinator.
- Planner's call: Small independent reliability fix. TOOLSET-099-87's excluded live acceptance remains under TOOLSET-096-7e; skip that operation, not its acceptance. Reproduced malformed-output aggregation failure in both successful and failing unittest subprocesses.
- Exclusions: No native/model/live checks, schedule changes or publication.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-111-b3 — Preserve TODO bytes when Pi proposes file scope

- [x] TOOLSET-111-b3 — Preserve TODO bytes when Pi proposes file scope
- Status: done
- Goal: PI-RUNNER
- Sources: [accepted requirements](docs/project.md#accepted-requirements), [scope helper](scripts/pi_autowork_touches.py), [runner tests](tests/test_pi_autowork.py).
- Scope: Preserve unrelated TODO bytes while adding a proposed Touches field. Read and write UTF-8 without newline normalization and use the target Scope line ending for the insertion.
- Acceptance: LF, CRLF and mixed-newline task documents gain exactly one parsed Touches field; removing only the inserted bytes recovers the original document, including sibling tasks, Unicode and trailing whitespace.
- Checks: `python3 -m unittest discover -s tests -p test_pi_touches.py -v`; `python3 -m unittest discover -s tests -p test_pi_autowork.py`; `python3 scripts/check.py`; independent diff review; `git diff --check`.
- Dependencies: None.
- Ownership: Current Toolset coordinator under autonomous local repository authority.
- Touches: scripts/pi_autowork_touches.py, tests/test_pi_touches.py, docs/testing.md, CHANGELOG.md
- Exclusions: No live model runs, fleet edits, schedules, publication or deployment.
- Planner's call: Use the existing parser and standard-library newline-preserving I/O, not a Markdown rewrite. Skip TOOLSET-099-87's already-separated live acceptance under TOOLSET-096-7e; neither parent is closed by this repair.
- Evidence: Four byte-preservation subcases failed before the fix and pass after it; existing fake-Pi suite 40 passed; full offline check passed 565/715/216/8 tests (one skipped; eight native/model/integration modules excluded). Independent exact-source review approved; no live qualification.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-112-29 — Preserve consultation replies across malformed diagnostic bytes

- [x] TOOLSET-112-29 — Preserve consultation replies across malformed diagnostic bytes
- Status: done
- Evidence: Baseline malformed-stderr regression failed for zero and nonzero subprocess exits. Corrected canonical source passed all 44 consultation tests; independent exact-source review approved and strict-stderr/permissive-stdout mutations failed as intended. Final `python3 scripts/check.py` passed 568/715/216/8 offline tests, one skip and eight excluded modules. Installed adoption remains separately unproved under TOOLSET-101-f6.
- Goal: RECOVERY
- Sources: [accepted requirements](docs/project.md#accepted-requirements), [consultation transport](scripts/profile-consult.py), [feedback contract](skills/autowork/references/profile-feedback.md).
- Scope: Decode subprocess stderr independently from strict UTF-8 protocol stdout so malformed diagnostics do not erase valid replies and actual exit status. Preserve existing timeout cleanup and refusal of malformed protocol bytes.
- Acceptance: Valid replies survive malformed stderr for successful subprocesses; nonzero subprocess exits remain failed with their diagnostics retained; malformed stdout remains refused; existing consultation and timeout tests pass.
- Checks: `python3 -m unittest discover -s tests -p test_profile_consult.py -v`; strict-stderr and permissive-stdout negative controls; `python3 scripts/check.py`; independent exact-source review; documentation and whitespace checks.
- Dependencies: None.
- Ownership: Current shared-source maintenance coordinator under autonomous local authority.
- Touches: scripts/profile-consult.py, tests/test_profile_consult.py, skills/autowork/references/profile-feedback.md, docs/testing.md, CHANGELOG.md
- Planner's call: Preserve TOOLSET-101-f6's separate native confirmation gate; skip its unavailable deployment operation without another unchanged scan. Execute this reproduced independent source defect, not product or worker recovery.
- Exclusions: No extra live consultation wave, profile/product edits, scan bypass, worker replacement, schedule activation, push or deployment.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-113-04 — Report malformed role statuses without crashing

- [x] TOOLSET-113-04 — Report malformed role statuses without crashing
- Status: done
- Goal: DOCS-COMPLETENESS
- Sources: [accepted requirements](docs/project.md#accepted-requirements), [manifest validator](skills/docs-sync/scripts/docs.py), [CLI regressions](skills/docs-sync/scripts/test_docs_manifest.py).
- Scope: Validate role status types before set membership; report malformed JSON container statuses through the existing diagnostic path in validate, check and stale.
- Acceptance: Array/object role statuses produce a role-specific unknown-status diagnostic and exit 1 without traceback or file changes; supported status values retain existing behavior and independent malformed fields are still reported.
- Checks: `python3 -m unittest discover -s skills/docs-sync/scripts -p test_docs_manifest.py -v`; `python3 scripts/check.py`; independent diff review; `git diff --check`.
- Dependencies: None.
- Ownership: Current Toolset coordinator under autonomous local repository authority.
- Touches: skills/docs-sync/scripts/docs.py, skills/docs-sync/scripts/test_docs_manifest.py, docs/testing.md, CHANGELOG.md
- Exclusions: No installed-profile edits, live models, deployment, schedules or push.
- Evidence: Twelve container-status/CLI subcases failed before the fix; all 24 manifest CLI tests passed afterward. Independent exact-source review approved. Python 3.12 `scripts/check.py` passed 568/715/217/8 tests across four directories, one skip and eight native/model/integration modules excluded. Offline only.
- Planner's call: Reuse the existing validator and unknown-status diagnostic, adding only a string-type guard. Skip the already-separated fleet/model acceptance under TOOLSET-096-7e; other current tasks need excluded live or deployment access. Preserve their acceptance and priority.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-114-c4 — Preserve Unicode separators in consultation stream events

- [x] TOOLSET-114-c4 — Preserve Unicode separators in consultation stream events
- Status: done
- Evidence: Twelve real-subprocess Unicode/exit/tool subcases failed before repair; all 45 consultation tests passed afterward. Independent exact-source review approved; separate parser and receipt-decoding negative controls both detected the regression. Native emitter replay with identical local consumer inputs changed failed to replied while masking synthetic credentials. Python 3.12 `scripts/check.py` passed 569/715/217/8 tests, one skip and eight excluded modules. Source-only completion; installed adoption remains TOOLSET-101-f6.
- Goal: RECOVERY
- Sources: [maintenance contract](skills/autowork/references/profile-feedback.md), [consultation transport](scripts/profile-consult.py), [verification](docs/testing.md).
- Scope: Parse the native LF-delimited stream-json without treating Unicode NEL, line separator or paragraph separator inside JSON strings as event boundaries. Preserve those characters in sanitized receipts and retain subprocess/protocol failure verdicts.
- Acceptance: Valid Unicode-bearing replies are retained exactly, sanitized event receipts remain parseable JSON, forbidden tool events remain visible and synthetic credentials stay masked. Nonzero exits and malformed stdout remain failures.
- Checks: Reproduce the regression before repair; run the focused consultation suite, the identical local read-only consumer before/after, independent exact-source review and `python3 scripts/check.py`.
- Dependencies: None.
- Touches: scripts/profile-consult.py, tests/test_profile_consult.py, docs/testing.md, skills/autowork/references/profile-feedback.md
- Ownership: Current shared-source maintenance coordinator under existing local repair authority.
- Planner's call: Skip installed adoption already isolated in TOOLSET-101-f6; native scan confirmation remains unavailable under this grant. Fix this reproduced disjoint transport defect without counting it as primary recovery.
- Exclusions: No new consultation wave, model/product worker launch, profile mutation, scan bypass, deployment or push.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-116-c1 — Port stale-result and cancellation scenarios from reference Pi orchestrators into engine fixtures

- [x] TOOLSET-116-c1 — Port stale-result and cancellation scenarios from reference Pi orchestrators into engine fixtures
- Status: done (9c46aaf); seven fixtures in `test_parallel_adversarial.py`, three engine gaps fixed; coverage recorded in the research doc.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [research: stale-result protection](docs/research/pi-autowork-reference-architectures.md#stale-result-protection-agent-orchestrator--agwab), [adapter checks](docs/research/pi-autowork-reference-architectures.md#concrete-adapter-checks-added-by-this-wave), [design](docs/plans/2026-10-16-pi-autowork-coordinator.md).
- Touches: skills/autowork/scripts/test_parallel_*.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/parallel_integrate.py, docs/research/pi-autowork-reference-architectures.md
- Scope: Owner direction (2026-10-16): use the research's reuse findings. Reproduce, as offline fixtures with controlled subprocess workers, the adversarial cases from Agent Orchestrator (`ActivitySignal` expected revision/launch identity), AgwaB (`commitAttemptResultIfActive`), MinhDuyDEV (generation-fenced resource transfer), Gas Town (launch happened but receipt write failed) and Kyle Boas (old final text must not complete a new assignment): late report from a superseded attempt, cancellation during spawn, out-of-order completion, report written after a runner restart, receipt-write failure after launch. Port scenarios and invariants only, not code; record which upstream case each fixture mirrors. Fix only gaps the fixtures expose, against the existing slot identity and attempt guards.
- Acceptance: Each listed scenario has a fixture that passes against the engine, or a fix that makes it pass; a superseded attempt can never move a slot or reach integration; the research doc records which scenarios were already covered.
- Checks: engine tests in `skills/autowork/scripts`; `python3 scripts/check.py`.
- Dependencies: None.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No upstream code copied (MIT notices would apply); no live Pi or fleet runs; avoid editing `pi-autowork.sh` while TOOLSET-115-bf phase 5 is active.

<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-115-aa — Report malformed runtime installation facts without crashing

- [x] TOOLSET-115-aa — Report malformed runtime installation facts without crashing
- Status: done
- Evidence: 21 malformed-facts subcases reproduced the defect then passed; all 12 preflight tests passed, including interpreter selection and parser fallback. Independent exact-source review approved. Python 3.12 `python3 scripts/check.py` passed 571/715/217/8 tests (one skip; eight native/model/integration modules excluded). Offline implementation only; canonical integration remains subject to the writer gate.
- Goal: RECOVERY
- Sources: [accepted purpose](docs/project.md#accepted-requirements), [runtime preflight](setup_preflight.py), [fixtures](tests/test_preflight.py).
- Scope: Validate the installation-facts shape consumed by runtime_check so malformed JSON structures produce the existing safe admission diagnostic, not an uncaught TypeError. Preserve valid interpreter selection and read-only preflight behavior.
- Touches: setup_preflight.py, tests/test_preflight.py, docs/testing.md, CHANGELOG.md
- Acceptance: Malformed root/packages/venv/environment shapes fail preflight without traceback or metadata disclosure; valid facts select their interpreter and preserve configuration validation verdicts; fixture files remain byte-identical.
- Checks: `python3 -m unittest discover -s tests -p test_preflight.py -v`; `python3 scripts/check.py`; independent source review; `git diff --check`.
- Dependencies: None.
- Ownership: Current isolated Autowork coordinator; canonical integration requires a clear writer gate.
- Exclusions: No live setup, installed-profile writes, model runs, push or Hermes Agent changes.
- Planner's call: Skip already separated live/fleet qualification under TOOLSET-096-7e and the other existing external-gate tasks; preserve their acceptance. Use the existing safe runtime diagnostic and explicit shape validation rather than swallowing arbitrary exceptions or silently ignoring corrupt facts.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-121-3d — Rename the repository and plugin from hermes-toolset to autowork

- [x] TOOLSET-121-3d — Rename the repository and plugin from hermes-toolset to autowork
- Status: done offline (efdde94: full offline gate passed); owner decisions (2026-10-16): the new name is `autowork`, the maintenance commands become `/autowork update|status|list` and `hermes autowork …`, and there is no backwards compatibility. Source rename implemented on `autowork/TOOLSET-121-3d`; GitHub repository renamed to `TrebuchetDynamics/autowork` by the owner's approval. Reinstalling live installs is TOOLSET-123-a0 below.
- Goal: PORTABLE — Align portable workflow discovery.
- Sources: [README host table](README.md), [cross-host adapters](docs/cross-host.md), [project contract](docs/project.md).
- Touches: README.md, CHANGELOG.md, AGENTS.md, plugin.yaml, package.json, .claude-plugin/, adapters/, update_bundle.py, update_bundle_native.py, setup_runtime.py, setup_preflight.py, install.sh, install-plugins.sh, install-skills.sh, install_skills.py, scripts/, skills/, tmux/, pi-autowork/, docs/, tests/
- Scope: Planning happens in any host (Hermes, Claude Code, Codex, Pi); pi-autowork builds the queued work, so the name should not name one host. Rename the project, the plugin and the command namespace to `autowork` in every manifest (`plugin.yaml`, `package.json`, `.claude-plugin/plugin.json` and `marketplace.json`, the Codex and Pi adapters), the upstream URL in `update_bundle.py`, install scripts, docs and tests (about 78 files reference `hermes-toolset`; inventory them with `rg -l hermes-toolset` first). Keep host-specific parts named for their host: the Hermes plugin's fleet, scheduler and Telegram features are documented as Hermes-only. No compatibility layer (owner direction): no aliases, legacy fallbacks or migration code; an installation from before the rename is removed and installed again. The `/toolset` maintenance command moves to exact `/autowork update|status|list` forms and `hermes toolset` to `hermes autowork`. Record the rename in CHANGELOG.md.
- Acceptance: `rg -i 'hermes[ -]toolset'` returns only historical text (CHANGELOG past entries, archive, evidence, the rename notes); each host's registration test finds the plugin as `autowork`; `/autowork update|status|list` reach maintenance and other `/autowork` arguments run the skill; README and the hero use the new name.
- Checks: `python3 scripts/check.py`; `node --test tests/portable_pi.test.mjs`; adapter registration tests; `docs.py check`. Registration checks do not prove live installs on the hosts.
- Dependencies: none.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: The local checkout directory rename, marketplace republication and reinstalling installed profiles and hosts are owner/live steps (TOOLSET-123-a0). No direct edits in fleet repositories; per-profile state folders (`maintenance/toolset-update/`) keep their names.

<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-116-fc — Ignore inline code examples in README image audits

- [x] TOOLSET-116-fc — Ignore inline code examples in README image audits
- Status: done
- Goal: README-DESIGN
- Sources: [README audit adapter](skills/beautify-github-readme/SKILL.md), [auditor](skills/beautify-github-readme/scripts/audit_readme.py), [fixtures](tests/test_beautify_readme_vendor.py).
- Scope: Exclude confirmed single-line Markdown code spans from the image inventory without modifying pinned upstream files or adding a Markdown dependency. Preserve visible image checks and source files.
- Acceptance: Literal Markdown/HTML image examples in matched single-line backtick spans cause no missing-image, undefined-reference or alt-text errors; actual adjacent images, unmatched delimiters, mismatched delimiter runs and multiline/block-boundary ambiguities remain audited conservatively.
- Checks: `python3 -m unittest discover -s tests -p test_beautify_readme_vendor.py -v`; `python3 scripts/check.py`; README audit and documentation check; independent source review.
- Dependencies: None.
- Ownership: Current autonomous Toolset coordinator; isolated branch pending canonical integration.
- Touches: skills/beautify-github-readme/scripts/audit_readme.py, skills/beautify-github-readme/SKILL.md, tests/test_beautify_readme_vendor.py, docs/testing.md, CHANGELOG.md
- Planner's call: Preserve the active canonical writer and continue in the existing isolated candidate. Complete remaining mixed-text single-line acceptance with a stdlib literal-region scanner before indexed delimiter masking; track angle destinations, quoted titles and balanced parentheses across continuation lines. Reuse existing image recognizers; omit new dependencies and multiline code support. This supersedes only the earlier complete-image-only restriction, not visible-image safeguards or full-parser exclusions.
- Prior partial delivery: Complete-image-only support in 5001be3 passed 11 focused tests and the 574/715/217/8 offline gate. That evidence remains historical; mixed-text acceptance is now implemented and independently approved after three reproduced link-context review defects were repaired.
- Current verification: All 12 focused tests pass. Exact-source independent review approved the auditor and tests, including adversarial adjacent-image probes. `python3 scripts/check.py` passed all four offline directories (one skipped test, eight excluded modules); source/test hashes match the reviewed candidate. README audit checks two local images. Offline acceptance is complete; canonical integration and installed adoption are separate.
- Next action: Integrate the coherent reviewed branch after the canonical writer gate clears; reconcile only attributable ledger and archive deltas against fresh main. No push or installed-profile change is authorized.
- Exclusions: No README redesign, assets, pinned upstream edits, installed-profile changes, push or live qualification.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-159-30 — A git timeout under host load waits as busy, not as an engine fault

- [x] TOOLSET-159-30 — A git timeout under host load waits as busy, not as an engine fault
- Status: done (2026-10-17)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [monitor findings](docs/plans/2026-10-16-pi-autowork-coordinator.md#fleet-monitor-findings-delivery-environment-and-stall-repair), [engine entry](skills/autowork/scripts/task_execution.py) (`git`, `parallel_main`, `main`), [claims](skills/autowork/scripts/parallel_claims.py) (`_last_change`, `_worktrees`), [coordinator](pi-autowork/pi_autowork/coordinator.py) (the `BUSY` and `The engine needs attention` paths).
- Evidence (2026-10-17 09:44 monitor pass): with seven runners and their test runs on one 22-CPU host, the load average reached 124 and free memory 2 GB. A runner logged `The engine needs attention: Command '['git', …, 'worktree', 'list', '--porcelain']' timed out after 10 seconds` and, at 09:49, the same for the claim probe `git log -1 --format=%ct -E -G <task token> -- TODO.md goals.json`. Its STALLED line then named `the engine needs attention … (the runner cannot proceed, holds 44)` as the root blocker. The same probe takes 0.04 s on an idle host. `task_execution.git` has a fixed 10 s timeout, and `subprocess.TimeoutExpired` falls into the generic `SubprocessError` handler, which reports `ACTION_REQUIRED`.
- Touches: skills/autowork/scripts/task_execution.py, skills/autowork/scripts/test_task_execution.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: In `parallel_main` and `main`, catch `subprocess.TimeoutExpired` before the generic handler and answer `{'outcome': 'BUSY', 'reason': 'host busy: <command name> took over <N>s (load <1-minute load>/<CPUs> CPUs)'}`. The coordinator already waits on `BUSY` without a failure streak. Its stall summary names it as a transient host-load wait, not `the runner cannot proceed`. Nothing else changes: other `SubprocessError`s stay `ACTION_REQUIRED`, and no timeout is raised or retried in a loop.
- Acceptance: In a fixture where `git` is replaced by a command that sleeps past the timeout, the engine prints `BUSY` with a `host busy:` reason and exit code 1. The coordinator logs `Repository busy (host busy: …)` once per change and no `engine needs attention` line, and the next cycle dispatches normally once git is fast again. A non-timeout git failure still reports `ACTION_REQUIRED`.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py; python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator. TOOLSET-118-68 owns host budgets, which keep load from getting this high; this task only stops a transient timeout from looking like an engine fault.
- Exclusions: No change to the 10 s git timeout, the resource gate or worker counts.
- Planner's call: report it as `BUSY`, not a new outcome. The coordinator already has a quiet, non-failing wait for it, and an owner reading the TUI sees `busy`, which is true, instead of a fault that needs them.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-148-88 — One malformed Touches field holds its task, not the whole engine

- [x] TOOLSET-148-88 — One malformed Touches field holds its task, not the whole engine
- Status: done (2026-10-17)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [monitor findings](docs/plans/2026-10-16-pi-autowork-coordinator.md#fleet-monitor-findings-delivery-environment-and-stall-repair), [Touches parser](skills/autowork/scripts/parallel_plan.py) (`paths`), [coordinator](pi-autowork/pi_autowork/coordinator.py) (the `The engine needs attention` path).
- Evidence (2026-10-16 23:50 monitor pass): runner B logs `The engine needs attention: Touches must contain repository-relative paths without dot segments; checking again in 60s`. `autowork ls` shows `runner: the engine needs attention` for all 55 waiting tasks. The cause is two task bodies on its session branch ending `Touches: …, tests/, docs/notes/.`: the sentence-final period becomes the path `docs/notes/.`. `paths()` raises for the whole plan, so no task in the repository can be admitted.
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py
- Scope: (1) Prose tolerance: strip exactly one sentence-final period from the last Touches item when what remains is a valid path (`docs/notes/.` becomes `docs/notes/`, and `a.py.` becomes `a.py`). Never strip interior dots or `..`, and keep everything else fail-closed. (2) Isolation: a Touches value that is still invalid holds only its own task, with reason `invalid Touches: <path>`, which TOOLSET-129-c4 shows as agent repair and TOOLSET-141-c4 can repair. Other tasks are planned and admitted as usual. The engine-wide `needs attention` state is reserved for failures that are not specific to one task.
- Acceptance: In fixtures, `x/, docs/notes/.` parses to `['x/', 'docs/notes/']`. `../a`, `/abs`, `a/./b` and `a/../b` stay rejected, and an interior `a/.b/` is preserved as a path. A plan with one invalid task holds that task with its reason while independent tasks are admitted and dispatched in the same cycle. No `engine needs attention` line appears for a per-task contract error.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_plan.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator; reconcile active TOOLSET-115-bf output in coordinator.py first. The runner B queue is not edited by hand; it recovers through the delivered release.
- Exclusions: No widening of the safety rules for absolute, backslash, NUL or parent paths.
- Planner's call: first in Now. It is the smallest change, and it unblocks an entire repository whose runner is otherwise dead.
- Planner answer (2026-10-17 09:15, monitor pass): its worker asked for `skills/autowork/scripts/parallel_integrate.py`. It and its test are added to Touches. Resume or reverify the existing candidate; do not reimplement.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-157-cd — Held slots release file ownership so holds cannot deadlock the queue

- [x] TOOLSET-157-cd — Held slots release file ownership so holds cannot deadlock the queue
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [monitor findings](docs/plans/2026-10-16-pi-autowork-coordinator.md#fleet-monitor-findings-delivery-environment-and-stall-repair), [admission](skills/autowork/scripts/parallel_plan.py), [integration](skills/autowork/scripts/parallel_integrate.py), [slot state](skills/autowork/scripts/parallel_state.py).
- Evidence (2026-10-17 09:11 monitor pass): this repository's own runner was STALLED with 0 running, 46 waiting and 5 held. The single root was one held task whose candidate conflicts on two files with another held slot's ownership; it blocked 45 tasks. Every other hold was waiting for a planning answer, so no worker could start and the fixes that would heal the fleet could not land. The other six runners were stalled at the same time on their own holds.
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/test_parallel_state.py, skills/autowork/references/parallel-workers.md, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py
- Scope: (1) A slot that is held, with no live worker and waiting on an answer or repair, keeps its candidate branch and report but stops counting as an owner of its Touches for admission once it has been held for one stall threshold. Its files are recorded as `released`. (2) When the held task is answered or retried, it reacquires ownership through normal admission. If main or another slot changed its files meanwhile, it merges main into its candidate first. A conflict is an agent repair, using the existing Pi merge resolver, not fresh reimplementation. (3) Integration conflicts between two held candidates are ordered by TODO priority. The higher-priority candidate integrates first, and the other is rebased and reverified once. (4) `STALLED` root reporting names a `held-ownership deadlock` explicitly when holds alone block runnable work, and the release in (1) clears it automatically.
- Additional scope (2026-10-17 09:35 monitor pass): a stalled runner never saw the planner's answers to its held tasks. It commits quiet owner planning files only inside a merge, and with nothing to merge they stayed uncommitted for more than 20 minutes. The held tasks resumed only after the planning edits were committed by hand. (5) A runner that is stalled or idle, with planning files in the canonical checkout that are uncommitted and quiet for 10 minutes, commits them with the same rules as `commit_owner_planning`, without waiting for a merge, then rereads held tasks.
- Additional scope (2026-10-17 10:34 monitor pass): admission and integration disagree about interrupted slots. `parallel_dispatch.dispatch_locked` drops restartable (interrupted or released) slots from the owners passed to `parallel_plan.plan` ("A restartable slot's own files are not someone else's running work"), but `parallel_integrate`'s ownership check counts every other slot that is not released, closed or exhausted, interrupted ones included. On one runner a fresh task was admitted onto the two files an interrupted candidate had changed. Its commit was then held `overlap` for conflicting with that interrupted slot, and the interrupted task now waits `overlapping paths with` the held one: 12 tasks blocked, no question raised and no recovery path. (6) One ownership rule for both: a restartable slot owns its Touches for admission until it is resumed. A resumed candidate is preferred over fresh overlapping work at equal or higher priority, since its work already exists. (7) Recovery for the existing shape: a held `overlap` slot whose conflicts are owned only by a restartable slot stops counting as an owner for that slot's admission (as in (1), without waiting a stall threshold). The interrupted candidate resumes and integrates, then the held commit merges main and is reverified once, as in (2). Acceptance for (6) and (7): in a fixture with an interrupted slot on `x.dart` and a fresh task touching `x.dart`, the fresh task waits with `overlapping paths with <interrupted>`. With the deadlock already present (held overlap plus interrupted owner), the interrupted task resumes in the next cycle, then the held commit integrates after one reverify, with no new implementation run.
- Acceptance: In fixtures, two held slots with overlapping Touches and 40 waiting tasks that touch those files lead, after one stall threshold, to waiting tasks being admitted and dispatched. The held candidates are preserved byte for byte. When answered, each reacquires its files, merges main, and reverifies without reimplementing. A conflicting pair integrates in priority order. A live, running slot never releases ownership. No model call is made unless a merge conflict needs the resolver.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p 'test_parallel_*.py'; python3 scripts/check.py with TMPDIR set to a fresh short directory (see TOOLSET-154-d3's planner answer)
- Dependencies: None.
- Ownership: Toolset coordinator; reconcile the held TOOLSET-147-54, TOOLSET-140-f4 and TOOLSET-148-88 candidates, which overlap these engine files, in priority order.
- Exclusions: No discarding of candidates, no forced integration of unverified work, and no change to the serial-path rule for genuinely exclusive tasks.
- Planner's call: first in Now. A deadlock among holds stops every other self-healing fix from landing. The release is time-bounded and candidate-preserving, so it is safe to automate.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-160-df — A serial file conflicts only with other serial work, so one manifest task no longer idles every worker

- [x] TOOLSET-160-df — A serial file conflicts only with other serial work, so one manifest task no longer idles every worker
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17): "i want more workers active per repo. most only uses 1"; [admission](skills/autowork/scripts/parallel_plan.py) (`_solo`, `plan.conflict`, the `stopped` backfill rule), [integration scope check](skills/autowork/scripts/parallel_integrate.py) (`verify_scope`, protected files).
- Evidence (2026-10-17 10:45 monitor pass): every runner allows 8 workers (`PI_AUTOWORK_WORKERS` default), but most run one. Waiting reasons across the fleet: `priority waits for <task>` 14 in this repository, 9 in a second runner and most of a third runner's queue; `serial path; must run alone (beside …)` heads each of those chains. One task whose Touches include a manifest, lockfile or build file (`SERIAL_PATHS`) is `_solo`: it conflicts with every other task, and when it waits for running work, `stopped` ends all lower-priority dispatch so the pool drains for it. Each worker has its own worktree, so a manifest change in one cannot affect another worker's build; the real conflict is only between tasks that both change serial files (two lockfile edits do not merge).
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/references/parallel-workers.md
- Scope: (1) Split `_solo` into its two meanings. Exclusive (no Touches, or a `live`/`exclusive` resource) keeps today's behaviour: it runs alone, and while it waits for running work it stops lower dispatch. Serial (Touches include a `SERIAL_PATHS` file) conflicts only with another task that also touches a serial file, reason `serial path shared with <task>`. It does not stop backfill: independent tasks keep running beside it. (2) `_solo` keeps returning the serial reason for callers outside admission, so `verify_scope`'s protected-file check (a new manifest needs serial admission in the original contract) is unchanged. (3) Document the rule in parallel-workers.md.
- Acceptance: In fixtures, a serial task and two independent tasks without serial files dispatch together in one cycle. Two tasks that each touch a different serial file (a manifest and a lockfile) never run at once, and the lower-priority one waits with `serial path shared with <task>`. A task without Touches, or with an exclusive resource, still runs alone and still stops lower dispatch while it waits. Integration still holds a commit that creates a new manifest without serial admission in its original contract.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p 'test_parallel_*.py'; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator (owner session).
- Exclusions: No change to the worker cap, the resource gate, Touches overlap, or the protected-file integration check.
- Planner's call: narrow serial admission to serial-vs-serial instead of raising worker counts. The cap is already 8; admission is what keeps runners at one worker, and per-worker worktrees remove the reason a manifest change had to run alone.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-152-d4 — Widen a held task's Touches by the exact paths its worker names, then reverify the same candidate

- [x] TOOLSET-152-d4 — Widen a held task's Touches by the exact paths its worker names, then reverify the same candidate
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [monitor findings](docs/plans/2026-10-16-pi-autowork-coordinator.md#fleet-monitor-findings-delivery-environment-and-stall-repair), [integration scope check](skills/autowork/scripts/parallel_integrate.py), [question block](pi-autowork/pi_autowork/questions.py).
- Evidence (2026-10-16/17 monitor passes): the most frequent hold is a worker needing one or two exact files outside its Touches. Examples: runner C a fleet task (one script), runner A a fleet task (two bracketed route files), hermes-toolset TOOLSET-099-87 (`pi-autowork/pi_autowork/coordinator.py`) and runner B a fleet task (one contract test). The last was logged more than 10 times in 6 hours. Each becomes an owner question, although the worker names the exact path and the evidence.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/questions.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/tests/test_questions.py, tests/test_pi_autowork.py
- Scope: When a hold's cause is `outside Touches` or a worker blocker naming paths it needs, the coordinator widens automatically only if every condition holds. (a) There are at most 3 exact repository-relative file paths: no globs, no directories, and nothing the existing `paths()` rules reject. (b) None is TODO.md, goals.json or BLOCKERS.md. A serial path from `SERIAL_PATHS` (a dependency manifest, lockfile, CI file or migration) may be added, but the task then becomes exclusive and runs alone, which is what the serial rule already requires. That widening is recorded as `serial`. Evidence (2026-10-17): a worker asked to add a manifest and its lockfile, which the earlier rule would have sent to the owner. (c) No live slot or other held candidate claims the path. (d) The task has not already been widened once. If so, it appends the paths to that task's `Touches:` in the runner's own planning commit on the session branch, in the same style as the question block. It records `Touches widened by the runner from worker evidence: <paths>` in the task body. It then reverifies the existing candidate, without fresh implementation. Anything else, a second request, or a path another task owns stays an owner question with the exact paths. Acceptance and checks are never changed.
- Acceptance: In fixtures, a one-path outside-Touches hold is widened, committed once and reverified, then integrates without a new attempt or model implementation run. A serial path is added with the task made exclusive. A glob, a fourth path, a path owned by another slot, or a second widening request each become exactly one question. A widened task whose reverification fails is held with that reason, not widened again. The question block no longer lists widened tasks.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s pi-autowork/tests -p test_questions.py; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator; reconcile active TOOLSET-115-bf and TOOLSET-120-fc output in overlapping files first (120-fc owns candidate reuse and this task only adds the scope repair).
- Exclusions: No change to acceptance, checks or dependencies; no widening by a model; no direct edits in fleet repositories outside the runner's own planning commit.
- Evidence (2026-10-17 10:21 monitor pass): after the fleet restart onto the 148-88/159-30 release, one runner's only runnable chain (one task holding four dependants) is held by a worker blocker before any edit: it names two exact build files it must change and asks for them in Touches. This is the same shape as the earlier examples and now the most common reason a working runner goes idle. The `worker blocker naming paths` case in (Scope) covers it: no candidate exists, so after widening the task is simply rerun, not reverified.
- Planner's call: bounded auto-widening (exact files, once, non-protected, unowned). A worker naming an exact file it must change is engineering evidence, not a product decision. The bounds keep the scope check meaningful.


<!-- archived from TODO.md -->

Source section: Next

Disposition: Superseded; not completed
Successors: TOOLSET-164-f1
Reason: Owner decision 2026-10-17: planning repair moves to the standing DOCS-MAINTAINER worker (docs/plans/2026-10-17-docs-maintainer.md, decision 5)
Original task and unchecked acceptance retained below.

### TOOLSET-141-c4 — Repair incomplete fleet task contracts with a bounded planning worker instead of stalling

- [ ] TOOLSET-141-c4 — Repair incomplete fleet task contracts with a bounded planning worker instead of stalling
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [automatic recovery continuation](docs/plans/2026-10-16-pi-autowork-coordinator.md#automatic-stall-recovery-and-conditional-docs-sync), [monitor findings](docs/plans/2026-10-16-pi-autowork-coordinator.md#fleet-monitor-findings-delivery-environment-and-stall-repair), [admission reasons](skills/autowork/scripts/task_execution.py) (`needs unique Scope, Acceptance and Checks fields`, `missing TODO contract`, `duplicate task contract fields`), [design](docs/plans/2026-10-16-pi-autowork-coordinator.md) (deferred causes with automatic actions), [Docs Sync](adapters/skills/docs-sync/SKILL.md).; [manual blocker contract repair](docs/plans/2026-10-16-pi-autowork-coordinator.md#blockers-repairs-for-malformed-task-contracts).
- Evidence (2026-10-16 23:40 monitor pass): runner B has been STALLED for 7h26m with 0 running, 53 waiting and 4 held. Its roots are ledger tasks without full bodies (for example `a fleet task: needs unique Scope, Acceptance and Checks fields`), and its runner.log repeats that reason 414 times. a fleet task is held because TODO.md lacks the a fleet task body. TOOLSET-129-c4 labels these as agent repairs, but no agent performs them.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/worker.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_questions.py, tests/test_pi_autowork.py, skills/blockers/, skills/docs-sync/, adapters/skills/
- Scope: When a runner is STALLED and its root causes include those three contract reasons, the coordinator dispatches one planning-repair worker for the affected task IDs. The worker is Pi with the docs-sync skill, `Touches: TODO.md, goals.json`, exclusive on planning files. It completes the bodies only from each task's own Sources, goal and accepted plan section. It fills only the fields those sources support and never invents product acceptance, scope or authority. If the sources cannot support a field, that becomes one BLOCKERS question naming the field. The result integrates like any task: `goals.py validate` passes and the admission reasons clear. Attempt each task-body fingerprint at most once. An unchanged fingerprint becomes a question rather than a loop. Log a repeated admission reason once per change, not every cycle.
- Acceptance: In a fixture repository, three ledger tasks lack fields but have sources. A fake Pi repair adds the fields, and the tasks are admitted on the next cycle. A task without a supporting source produces exactly one question. The same fingerprint is never retried. Edits outside TODO.md or goals.json fail integration. A runner with no contract roots, idle or stalled, makes zero model calls. A repeated reason appears once in runner.log.
- Checks: python3 -m unittest tests/test_pi_autowork.py; python3 -m unittest discover -s pi-autowork/tests -p test_questions.py; python3 scripts/check.py; planned focused repair regressions: `python3 -m unittest discover -s skills/docs-sync/scripts -p test_backlog_recovery.py` (new cases unrun).
- Design (planner's call, after the builder check): no deferred-cause action hook exists in `coordinator.py` yet. Add one small dispatch point for stall causes; the lifecycle redesign reuses it instead of adding another. The repair is a coordinator job using the existing `pi_job` pattern (as the merge resolver does). It runs in a disposable worktree off the session branch, outside engine admission. It takes one slot, consumes no task attempt and creates no TODO entry. The coordinator integrates it by checking that the diff touches only TODO.md and goals.json and that `goals.py validate` passes, then commits it on the session branch, as `commit_owner_planning` does. Fingerprints of attempted bodies live in the state directory as `contract-repairs.json`.
- Dependencies: None. Overlapping coordinator Touches already serialize it behind the active lifecycle redesign.
- Ownership: Toolset coordinator; preserve TOOLSET-120-fc's question block format.
- Exclusions: No repair of product decisions and no edits beyond the fleet repository's TODO.md and goals.json, made through its own runner's integration. A human or toolset session never edits the fleet repository directly. No model call when the runner is idle.
- Planner's call: a repair spends tokens only when a stall's root is a repairable contract. That keeps "idle = zero tokens" intact.

- Accepted refinement (2026-10-16): Trigger on an observed repairable blocked root at the next cycle, including when unrelated workers are active; do not wait for STALLED. Use the existing lifecycle repair hook and serialize planning-file writers, not all repository work. Bind the single attempt to task plus accepted source/candidate and relevant recovery-handler evidence, so restart/cosmetic edits cannot reset it but corrected source can. Validate full bodies and actual admission after repair. An unchanged failed repair stays an internal repair failure with its candidate/evidence and next retry condition; only an actual unavailable owner decision/input creates a question. This supersedes the earlier blanket unchanged-fingerprint-becomes-question behavior. Observe source movement and stop/budget limits before applying. No second watchdog or independent coordinator.
- Additional acceptance: A corrected accepted source permits one new repair; unchanged loops and crash recovery do not duplicate a model invocation. Conflicting acceptance is not guessed. An unrelated task continues while planning-file repair is serialized, and an exhausted internal attempt produces no fake owner decision. Preserve existing zero-token idle/no-contract cases.

- Manual blocker repair refinement: Implement the cited accepted repair contract in the blockers skill and shared Docs Sync operation, reused by the automatic hook. A target-repository agent may apply source-supported clerical duplicate-field repairs within documentation-only scope, without asking to code or restart a runner. Identical fields collapse losslessly; Checks plus historical Verification evidence is normalized without discarding required checks or fabricating an execution pass. Conflicting values are reconciled only from accepted sources; unresolved intent remains held. This prospectively refines the no-direct-fleet-edit exclusion only for the target repository's own authorized agent, never the Toolset monitoring session. Preserve all other boundaries.
- Repair proof required: Add multiline/fence, alias-collision, conflicting-source, dry-run/idempotence and stale/live-owner negative fixtures; demonstrate documentation-only repair through actual admission without a model call or service mutation. Ledger validation alone is not proof of admission or runner pickup. Do not rewrite already-done or archived example tasks.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-166-b4 — The runner view says whether it is stuck and why, and what each worker is doing

- [x] TOOLSET-166-b4 — The runner view says whether it is stuck and why, and what each worker is doing
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17, plan-with-me): "tui for individual runners needs a lot of work"; the two questions a runner view must answer: "is it stuck and why, and what each worker is doing". [TUI](pi-autowork/pi_autowork/tui.py), [fleet view](pi-autowork/pi_autowork/fleet_view.py), [health](pi-autowork/pi_autowork/health.py).
- Evidence (2026-10-17 owner capture): panes repainted over each other; the log opened on lines two hours old with repeated `No task can start now` and restart blocks; Needs and question previews were cut at the part that says what to do (`runner: 1 verified commit(s) wait fo…`); runners restarting onto a new toolset showed `not running — start it`; worker rows showed a truncated shell command or `subagent_wait: 7m ago`; waiting tasks and their reasons appeared only in log lines.
- Touches: pi-autowork/pi_autowork/tui.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/pi_autowork/health.py, pi-autowork/tests/test_fleet_view.py, pi-autowork/tests/test_health.py, pi-autowork/tests/tui_pilot.py
- Scope (owner decisions, 2026-10-17): (1) A verdict line at the top, wrapped, never cut, from the runner's own status: `Working — N of M workers busy`, `Waiting on you — N questions, easiest X (unblocks k)`, `Stuck <age> — <root> holds N (<why>)`, `Host busy — <resource gate reason>`, `Restarting onto <commit>`, `Paused`, `Not running`, `Idle`. Model and fallback move into the dim details line. (2) One row per worker with a plain-words `Doing` column (`running tests: …`, `editing <path>`, `reading <path>`, `searching`, `waiting on a sub-agent`, `reviewer: …`, `waiting to integrate: <reason>`), phase, try, elapsed, and `quiet Nm` when its last action is 5+ minutes old; Enter on a row shows its last 10 actions. (3) The runner writes waiting tasks grouped by cause into status.json (`waiting_groups`: reason, count, tasks), and the view shows them as one line (`23 wait for X (overlapping files) · 12 on dependencies · …`) without calling the engine. (4) The inline log covers the last hour, folds each restart into one `restarted onto <commit>` line and collapses consecutive repeats (`×N`). (5) Planner's calls: panes update only when their content changed (no clear-and-rewrite every refresh), text wraps instead of being cut, the fleet table shows `restarting` instead of `not running` while a service stops or starts or within 3 minutes of a `restarting on it` line, no model calls and no new dependency.
- Acceptance: In fixtures, each verdict case renders its sentence from status, service state and log; `doing` maps tool calls to the plain phrases and flags quiet workers; `health.update` writes `waiting_groups` with counts that add up to the waiting total; `log_lines` folds a stop/start/update sequence into one line and collapses three identical `No task can start now` lines into one with `×3`; the 80-column headless pilot shows the verdict, a worker row with `Doing`, the waiting groups and the action list, and Enter on a worker opens its recent actions.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p 'test_fleet_view.py'; python3 -m unittest discover -s pi-autowork/tests -p 'test_health.py'; python3 scripts/check.py
- Dependencies: None.
- Ownership: Owner session. TOOLSET-129-c4 (one evidence-backed Needs action) and TOOLSET-132-af (log search and copy) stay open for what this does not cover.
- Exclusions: No new dependency, theme or web change; no change to actions or their confirmations; no engine call on refresh.


<!-- archived from TODO.md -->

Source section: Now

Disposition: Superseded; not completed
Successors: TOOLSET-165-f7
Reason: duplicate: same own-worker writer bug, planned in parallel
Original task and unchecked acceptance retained below.

### TOOLSET-167-03 — A runner's own worker is never an outside session that holds integration

- [ ] TOOLSET-167-03 — A runner's own worker is never an outside session that holds integration
- Status: open
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [writers check](skills/autowork/scripts/task_execution.py) (`external_workers`, `blocking_workers`), [integration](skills/autowork/scripts/parallel_integrate.py) (`require_no_writers`).
- Evidence (2026-10-17 11:31–11:43): this repository's runner kept a verified commit waiting with `waiting to integrate until another session leaves the main checkout (live or unknown external writer/session; preserve canonical checkout: pid … pi in …/.worktrees/autowork-<task>-r2 (running commands))`, then `pid … pi in …/.worktrees/autowork-<task> (no terminal; activity unknown)`. Both pids were this runner's own workers in their own task worktrees, not sessions in the main checkout. The commit waited 12 minutes and was then held for validation; a fleet TUI showed `runner: 1 verified commit(s) wait for…` meanwhile.
- Touches: skills/autowork/scripts/task_execution.py, skills/autowork/scripts/test_task_execution.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py
- Scope: A process is this runner's worker when its working directory is a worktree recorded by a live slot of this repository (journal `worktree_created`), or it carries the slot's `AUTOWORK_WORKTREE` marker; such a process never blocks integration of another slot. Sessions in the canonical checkout or the session worktree still block as today. The waiting reason names the blocking process's checkout relative to the repository.
- Acceptance: In fixtures, a live Pi process in another slot's task worktree does not hold integration; one in the main checkout still does; the reason line names `main checkout` or the worktree.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No weakening of the canonical-checkout writer guard.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-168-ff — Auto-commit of quiet main-checkout work never pins a submodule to an unpushed commit

- [x] TOOLSET-168-ff — Auto-commit of quiet main-checkout work never pins a submodule to an unpushed commit
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [coordinator](pi-autowork/pi_autowork/coordinator.py) (`commit_owner_changes`), owner direction (2026-10-16) that auto work commits all quiet work.
- Evidence (2026-10-17 12:18 monitor pass): a runner committed 18 quiet paths from its main checkout as `chore: uncommitted work in the main checkout (pi-autowork)`, including two submodule pointer changes. One submodule now points at a commit that is on no branch of the submodule's remote. The push failed for an unrelated reason (non-fast-forward, TOOLSET-158-08); once that resolves, the superproject's main would reference a submodule commit no other clone can fetch.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: Before committing, `commit_owner_changes` finds gitlink paths (mode 160000 in the index or in `git diff --raw`). A submodule pointer change is committed only when its new commit is reachable from a remote-tracking branch of that submodule (after a quiet `git fetch` limited to 30 seconds); otherwise the path is left uncommitted and logged once per commit: `left <path> uncommitted: submodule commit <sha> is not on its remote yet`. Everything else commits as today. The pointer is committed in a later cycle once the submodule commit is pushed.
- Acceptance: In fixtures with a submodule, a pointer to a pushed commit is committed with the other quiet work; a pointer to a local-only commit stays uncommitted, is logged once, and is committed after the submodule commit reaches its remote; a repository without submodules behaves exactly as before.
- Checks: python3 -m unittest tests/test_pi_autowork.py (the owner-planning and uncommitted-work tests); python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to which other files auto work commits; no pushing of submodules by the runner.
- Planner's call: hold back only the unpublishable pointer, not the whole commit; the rest of the owner's quiet work still lands.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-169-1d — Toolchains a task provisions are kept in a per-repository cache that later tasks and reviews reuse

- [x] TOOLSET-169-1d — Toolchains a task provisions are kept in a per-repository cache that later tasks and reviews reuse
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [worker prompt](skills/autowork/scripts/parallel_dispatch.py) (`prompt`, the worker environment), [review](pi-autowork/pi_autowork/worker.py) (`verify`, `worker_tmp`).
- Evidence (2026-10-17 12:15 monitor pass): one runner's bootstrap task installed a pinned SDK under its worker's `$TMPDIR` as its own docs say; the next task in its chain and that task's reviewer each started with a fresh `$TMPDIR`, found no SDK, and the reviewer failed the commit with `no pinned … SDK was available, so the analyze and test checks could not be run`. The earlier fix (the reviewer reads the finished worker's `$TMPDIR`) only covers the same task.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, skills/autowork/references/parallel-workers.md
- Scope: Every worker and reviewer gets `AUTOWORK_CACHE`, one directory per repository on disk (`<git common dir>/autowork-execution/cache`), kept across tasks and runs. Prompts say: download or extract SDKs, toolchains and package caches into `$AUTOWORK_CACHE/<name>-<version>` (reuse one that is already there), and keep only scratch in `$TMPDIR`. The reviewer is told the same and may use the cache read-only. The cache is never committed, has a size note in status (`cache N GB`), and is removed only by `autowork` housekeeping when a person asks.
- Acceptance: In fixtures, a worker's prompt and environment carry `AUTOWORK_CACHE`, the same path for two tasks of one repository and a different one for another repository; a reviewer's prompt names it; the cache directory survives a task's close and set-aside.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest discover -s pi-autowork/tests -p test_worker_tmp.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No edits to fleet repositories' docs; no automatic deletion of the cache.
- Planner's call: a per-repository cache rather than sharing one task's `$TMPDIR` with the next: tasks run in parallel and are removed when they close, while a pinned SDK is a repository-wide prerequisite.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-162-d2 — The memory gate counts only what a new worker needs, and agent scratch stops filling RAM-backed /tmp

- [x] TOOLSET-162-d2 — The memory gate counts only what a new worker needs, and agent scratch stops filling RAM-backed /tmp
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17): "i want more workers active per repo"; [resource gate](skills/autowork/scripts/parallel_dispatch.py) (`resource_gate`), [worker prompt](skills/autowork/scripts/parallel_dispatch.py) (`prompt`), [coordinator](pi-autowork/pi_autowork/coordinator.py) (`pi_job`).
- Evidence (2026-10-17 11:01 monitor pass): `/tmp` is a 48 GB tmpfs, so files there are RAM. It held 39 GB in 7,839 entries, none touched for 2+ hours or open by any process: review and verify copies of whole repositories (`<task>-review.XXXXXX`, `<task>-verify.XXXXXX`), capture databases, SQL probes and logs that Pi workers and reviewers made with explicit `mktemp -d /tmp/...` paths, which ignore `TMPDIR`. MemAvailable read 7 GB. `resource_gate` refuses a new worker unless `available >= PI_AUTOWORK_MIN_FREE_MB * (running + 1)` (3000 MB each), though the memory running workers use is already subtracted from `available`: it reserved it twice, and with 7 GB no runner could start a third worker. The owner approved removing the stale entries; that freed 39 GB (available 7 GB to 36 GB).
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/janitor.py, pi-autowork/tests/test_janitor.py, skills/autowork/references/parallel-workers.md
- Scope: (1) `resource_gate` needs `2 * PI_AUTOWORK_MIN_FREE_MB` available for one more worker (its budget plus one spare), whatever this runner already runs, and keeps the load check. The waiting reason names both numbers. (2) Worker, reviewer and resolver prompts say: put scratch files and copies under `$TMPDIR`, never directly under `/tmp`; every Pi job already gets a per-job `TMPDIR` on disk, which is removed when the job's slot closes. (3) A janitor, run by each runner at most every 15 minutes, removes top-level `/tmp` entries owned by the runner's user that nothing inside has changed for `PI_AUTOWORK_TMP_STALE` seconds (default 7200), that no process uses as its working directory or holds open, excluding sockets and system directories (`.X11-unix`, `.ICE-unix`, `tmux-*`, `ssh-*`, `systemd-*`). It logs one line with the count and size freed. `PI_AUTOWORK_TMP_STALE=0` turns it off.
- Acceptance: In fixtures, with 7 GB available and two workers running, a third starts when `PI_AUTOWORK_MIN_FREE_MB=3000`, and none starts below 6 GB. The janitor removes a stale fixture directory, keeps one changed within the window, one that is a process's working directory and one with an open file, and never touches an excluded name or another user's entry. Prompts carry the `$TMPDIR` rule.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest discover -s pi-autowork/tests -p test_janitor.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator (owner session). TOOLSET-118-68 keeps cgroup budgets and process-tree stops; TOOLSET-140-f4 keeps the short socket-safe TMPDIR.
- Exclusions: No deletion of anything recent, in use or not owned by the runner's user; no change to the worker cap or load check.
- Evidence (2026-10-17 11:49 monitor pass): 45 minutes after the cleanup, `/tmp` held 5.9 GB again (available memory 37 GB to 31 GB) with eight runners working: about 8 GB an hour, so the 3-worker memory cap returns within hours unless the janitor and the `$TMPDIR` rule land.
- Evidence (2026-10-17 12:10 monitor pass): `/tmp` reached 16 GB 70 minutes after the cleanup (about 13 GB an hour); the largest entries were review copies of whole repositories (`<task>-review.XXXXXX`, up to 4.7 GB each) made by reviewers with explicit `/tmp` paths although their `TMPDIR` was on disk.
- Done by the owner session (2026-10-17): part of (2). Each review runs with its own `TMPDIR` under the runner's state directory, removed (and `git worktree prune`d) when the review ends; reviewer and worker prompts say never to write directly under `/tmp` and to make a scratch copy with `git worktree add --detach "$TMPDIR/copy" HEAD`. Still open: (1) the gate arithmetic and (3) the janitor.
- Planner's call: fix the double-counted reservation and clean the scratch that caused it, rather than lower `PI_AUTOWORK_MIN_FREE_MB`. The gate's purpose stays; only its arithmetic and the leak change.


<!-- archived from TODO.md -->

Source section: Next

### TOOLSET-124-97 — Audit this repository's suite against the test budget

- [x] TOOLSET-124-97 — Audit this repository's suite against the test budget
- Status: done
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: owner direction (2026-10-16: "make less tests and thinner; if a project has many tests we have to optimize"), [test budget](skills/shared/ENGINEERING-CYCLE.md#test-budget), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md), [earlier audit](docs/test-suite-audit.md), [accepted thinning plan](docs/test-suite-audit.md#suite-thinning-plan-2026-10-16).
- Touches: docs/test-suite-audit.md, docs/project.md
- Scope: Resume the accepted whole-suite thinning plan, preserving TOOLSET-073's historical results. Build a keep/thin/investigate disposition for all 126 current offline Python modules, the JavaScript suite and the eight excluded suites (static review only for excluded suites); refresh counts at execution. Inspect inherited repeats, prose-only assertions, duplicated fixture setup, fixed sleeps and legacy/component overlap. Prioritize the named implementation batches and record further tasks only for proven findings. This is qualitative thinning: use focused timings/coverage for candidate equivalence; repeated idle full-gate measurements are required only for quantitative suite-speedup claims, not to re-plan this work. Retain the 600-second timeout as nonpassing evidence, never as a successful baseline.
- Acceptance: docs/test-suite-audit.md accounts for every owned suite, distinguishes proven removals from unverified leads, names retained detection seams and coverage blind spots, records the precise candidate-specific before evidence, and keeps named safety/data-loss/authorization/composed regressions. The linked implementation tasks have bounded scope and checks; unknown candidates stay findings. No tests changed and no speedup claimed from static counts.
- Checks: `python3 scripts/check.py --list`; static AST inventory and narrow candidate collection; bounded candidate checks only where needed; `python3 skills/docs-sync/scripts/goals.py validate .`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No test edits, no new dependency (coverage runs from a scratch environment), no mutation tool added.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-142-85 — Query pending and completed tasks from repository evidence without writes

- [x] TOOLSET-142-85 — Query pending and completed tasks from repository evidence without writes
- Status: done
- Goal: BACKLOG
- Payoff: Produce a usable repository backlog for Autowork.
- Sources: [accepted tasks query plan](docs/workflows.md#tasks-query-skill), [priority and task parsing](skills/docs-sync/scripts/goals.py), [archive ownership and entries](skills/docs-sync/scripts/todo_archive.py).
- Touches: skills/pending/scripts/task_query.py, skills/pending/scripts/test_task_query.py, skills/pending/references/query-contract.md
- Scope: Add a standard-library read-only helper with structured pending/detail/search/history modes, ID/text, date bounds, timezone and limit. Reuse existing pure Docs Sync parsers/order functions without invoking mutations. Preserve TODO human ordering and blocked work while explaining eligible selection separately. Support TODO-only repositories, current/legacy archives and bounded local Git completion-transition evidence. Return records, source/date provenance and partial-result warnings for the skill to explain. Use explicit date evidence first; Git recording time and undated history remain distinct. Resolve the defaults and degraded cases exactly as recorded in the accepted plan.
- Acceptance: Fixtures demonstrate five-item pending output with totals and blocked/focus/drift distinctions; exact-ID and ambiguous-description lookup; current/legacy archive lookup; reopened/superseded records never falsely completed; timezone-correct date filtering and explicitly undated/partial Git history. Conflicting/malformed/changing sources remain attributed and cannot yield a false confirmed completion or runnable claim. All modes leave repository bytes and Git refs unchanged; hostile query/task text remains data. No dependency, index, cache, network, source repair or live worker inference.
- Checks: python3 -m unittest discover -s skills/pending/scripts -p test_task_query.py (new, unrun); python3 -m unittest discover -s skills/docs-sync/scripts -p test_todo_archive.py; git diff --check. Use compact behavioral fixtures and a temporary local Git history; no per-phrase assertions or full-suite benchmark project.
- Dependencies: None.
- Ownership: Toolset coordinator; helper work is independent of the planner-quality batch and preserves active worker contracts.
- Exclusions: No task mutations, new required ledger fields, host registration, installation, fleet scans, remote lookups, service changes or publication. Conversational packaging is TOOLSET-143-62.
- Planner's call: Keep new query files under skills/pending and reuse existing parsing; no second task store or search dependency. Default five results and 500 relevant commits for bounded Git fallback, with explicit truncation and requested expansion. Support /pending and /done through the same helper; latest recorded completions use evidence/Git transition dates, with explicit undated/partial results and no task-number or archive-order inference.

- Command refinement: The helper lives under skills/pending/scripts/ and supports both read-only frontends. Pending descriptions default to unfinished work; done descriptions to currently completed work. Default /done returns five latest dated recorded completions, or explicitly undated records when dates are unavailable; reopened/superseded tasks stay distinct. Extend the existing query fixtures for latest ordering, date provenance, ties, undated-only and bounded-history cases.
- Next action: Resume candidate 958fa5cbb80f6cad2b20b9ce6ed9adf3fe4542b6 and fix the integration reviewer's concrete DST-fold failure within the existing query scope: America/New_York 2026-11-01T01:30-04:00 to 01:15-05:00 is a forward interval despite reversed local clock labels. Reproduce the case and compare/order timezone-aware UTC instants, retaining genuinely reversed-interval rejection and all date-provenance/immutability checks. Reverify the repaired candidate through the existing integration owner; do not rescope or reimplement the whole helper.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-171-35 — An exclusive task drains the pool only after a grace period, so short independent work keeps running

- [x] TOOLSET-171-35 — An exclusive task drains the pool only after a grace period, so short independent work keeps running
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [admission](skills/autowork/scripts/parallel_plan.py) (the `stopped` backfill rule in `plan`), [dispatch](skills/autowork/scripts/parallel_dispatch.py), [status groups](pi-autowork/pi_autowork/health.py) (`waiting_groups`).
- Evidence (2026-10-17 13:49 monitor pass): this repository ran one worker while `28 wait behind TOOLSET-149-df, which runs alone`. That task is `Resources: exclusive` by its author's call. Every task above it waited on the one running task (overlap or dependency), so admission reached it, and because it waits on running work the rule stops all lower dispatch until the pool drains. Moving it down the list did not help: the tasks between it and the running one all waited too. The 28 held back were independent of both.
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/references/parallel-workers.md
- Scope: (1) An exclusive task (no Touches, or a `live`/`exclusive` resource) that waits on running work stops lower dispatch only after it has been the first exclusive task waiting for `PI_AUTOWORK_DRAIN_AFTER` seconds (default 1800), measured from the engine's own dispatch observations (`dispatch_observed` events already record waiting tasks). Before that, independent lower tasks backfill as for any waiting task, and the exclusive task still reserves what it declares. (2) Once draining, the waiting reason says so: `draining for <task> (waited 31m)`, and `waiting_groups` shows `wait for <task>, which runs alone (draining)`. (3) When it starts, it runs alone as today.
- Acceptance: In fixtures, an exclusive task behind running work lets an independent task dispatch in the first cycle; after the drain period (a short value in the fixture) it stops lower dispatch and is the next to start when the pool empties; a runner restart keeps the waiting clock (journal-based). Serial-file tasks are unchanged (TOOLSET-160-df).
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p 'test_parallel_*.py'; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to which tasks are exclusive or to how they run once started; no change to the worker cap.
- Planner's call: a time-bounded drain instead of an immediate one. It keeps the anti-starvation guarantee (an exclusive task still gets the whole pool within the grace period plus one task's run) while short independent work stops idling behind it.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-175-2b — Main passes the offline check again after the /pending skill landed without SKILL.md and the priority guard

- [x] TOOLSET-175-2b — Main passes the offline check again after the /pending skill landed without SKILL.md and the priority guard
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [/pending query](skills/pending/scripts/task_query.py) (TOOLSET-142-85, landed as f7cb607 and closed as 9ea176b), [skill installer](install_skills.py), [preflight](tests/test_preflight.py), [priority guard test](skills/docs-sync/scripts/test_priority_order.py) (`test_selection_entry_points_use_the_shared_guard`).
- Evidence (2026-10-17 15:30, `python3 scripts/check.py` on main): five failures, one cause. `skills/pending/` has `references/` and `scripts/` but no `SKILL.md`, so `install_skills.install` raises `Invalid skill folder or missing SKILL.md: …/skills/pending` (test_preflight ×2, test_impeccable_bundle, test_ui_taste_bundle), and `skills/pending/scripts/task_query.py` selects tasks without `goals.queue(data, todo_text)` (test_priority_order: `call goals.queue(data, todo_text) so drift cannot be bypassed`). TOOLSET-142-85's review ran only its own Checks.
- Touches: skills/pending/, skills/docs-sync/scripts/test_priority_order.py, install_skills.py, tests/test_preflight.py
- Scope: (1) Give `skills/pending/` a real `SKILL.md` (name, description and use of `task_query.py`, in the style of the other skills), or, if TOOLSET-143-62 owns the skill's entry point, a minimal one that 143-62 then extends; do not special-case the folder in the installer. (2) Make `task_query.py` read the queue through `goals.queue(data, todo_text)` like every other selection entry point, keeping its read-only, no-write behaviour and its existing tests. (3) No other change.
- Acceptance: `python3 scripts/check.py` passes on main (all five test directories), `/pending` behaves as TOOLSET-142-85's acceptance says, and the priority guard test passes without an allow-list entry.
- Checks: python3 -m unittest discover -s skills/pending/scripts; python3 -m unittest discover -s skills/docs-sync/scripts -p test_priority_order.py; python3 -m unittest tests/test_preflight.py tests/test_impeccable_bundle.py tests/test_ui_taste_bundle.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No installer or guard exceptions for this folder.
- Planner's call: first in Now. A red main makes every reviewer's full check fail and hides new regressions behind old ones.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-176-98 — A red main after a landing opens its own repair task, naming the failing tests and the commits since green

- [x] TOOLSET-176-98 — A red main after a landing opens its own repair task, naming the failing tests and the commits since green
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [coordinator](pi-autowork/pi_autowork/coordinator.py) (`merge_main`, `land`), [DOCS-MAINTAINER](pi-autowork/pi_autowork/maintainer.py) (TOOLSET-164-f1), `PI_AUTOWORK_VALIDATE`.
- Evidence (2026-10-17 15:30): TOOLSET-142-85 integrated and closed after its own Checks passed, but main then failed five tests in other directories; nothing noticed, and the next tasks' reviewers would have met the same failures.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, tests/test_pi_autowork.py, docs/cross-host.md
- Scope: (1) A repository may declare its full offline check (`PI_AUTOWORK_MAIN_CHECK`, for this repository `python3 scripts/check.py`). After the session lands on main, and at most once per main revision while nothing else needs the host (load below the CPU count, no verification running), the runner runs it in a disposable checkout of main with a short private TMPDIR. (2) A pass records `main green at <commit>`. A failure records the failing test names and the commits since the last green revision, and gives the DOCS-MAINTAINER a trigger to add one repair task first in Now, with that evidence, unless one is already open for the same failures. (3) Status and the runner view show `main red since <commit>: N failing` until it is green again.
- Acceptance: In fixtures, a landing that breaks an unrelated test yields exactly one repair task with the failing test and the commit range; a second landing with the same failures adds none; a green run clears the status line; a repository without `PI_AUTOWORK_MAIN_CHECK` runs nothing.
- Checks: python3 -m unittest discover -s pi-autowork/tests; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: TOOLSET-164-f1 (the maintainer writes the repair task).
- Ownership: Toolset coordinator.
- Exclusions: No full check on every task integration (too slow on loaded hosts); no automatic revert of landed work.
- Planner's call: check main after landing rather than before every integration: the full check takes about 25 minutes here, and one red result per main revision is enough to start the repair.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-177-d0 — A runner busy with its own job shows that job, not 'not cycling'

- [x] TOOLSET-177-d0 — A runner busy with its own job shows that job, not 'not cycling'
- Status: done (2026-10-17, owner session)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [coordinator](pi-autowork/pi_autowork/coordinator.py) (`pi_job`, `maintain`, `provision_and_reverify`, `resolve_task_conflict`, `merge_main`), [health](pi-autowork/pi_autowork/health.py) (`fleet`, `STALE_AFTER`), [fleet view](pi-autowork/pi_autowork/fleet_view.py) (`collect`, `verdict`).
- Evidence (2026-10-17 16:05 monitor pass): a runner whose DOCS-MAINTAINER job had been running for five minutes showed `not cycling 3h46m` in `autowork ls`. The coordinator runs its own Pi jobs (docs maintainer, toolchain provisioning, merge resolution) synchronously, so `status.json` is not refreshed during them; after `STALE_AFTER` the fleet view reads the old record as `not cycling`, and the age came from a stall record hours old.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/health.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/tests/test_fleet_view.py, pi-autowork/tests/test_health.py
- Scope: (1) Before each of its own Pi jobs the coordinator writes a `job` record into status (`{role: DOCS-MAINTAINER | provision | merge, task, started, pid}`) and clears it after. (2) `health.fleet` treats a live job pid as cycling, whatever `updated_at` says; the fleet view shows state `working` with Now `DOCS-MAINTAINER 5m` (or `provisioning <task>`, `resolving a merge`), and the verdict says `Working — DOCS-MAINTAINER repairing <tasks> (5m)`. (3) A dead job pid with a stale record is `not cycling` as today.
- Acceptance: In fixtures, a status record older than `STALE_AFTER` with a live job pid reads `working` with the job named; with a dead pid it reads `not cycling`; the job record is gone after the job.
- Checks: python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to how the jobs run; making them asynchronous is separate.
- Planner's call: report the job rather than make the jobs asynchronous now: the jobs are short and rare, and the false `not cycling` is the user-visible problem.

## MAIN receipt at 3bd1d95

Evidence supplement for TOOLSET-184-b3, not completion or a new executable task.
The existing repair remains first in Now with its original Scope, Acceptance,
Checks, Touches, Dependencies and Ownership unchanged. Its attempt-1 worker was
still running when inspected: the recorded process birth identity and worktree
matched the live process, and no terminal `report.json` existed. There is no
`slot-data/MAIN/` worker report. Do not replace the active worker or repin its inputs.

### Receipt binding and coverage

The runner's retained `main_check.json` records red revision
`3bd1d95a3bc6e7ba44c68109d67220da928388df`, `green: null`, and
`red_since: 36e2b7c0ea0c6096a7b20197edcacf68dc11dfa4`.
Its `main-check.exit` is `1`. The completed `main-check.log` lists 131 offline
modules in five directories and ends:

```text
Offline result: 2 test directories passed; 3 failed; 8 modules excluded.
```

The 16 distinct ERROR identities in the full log exactly match the 16 names in
this receipt. These are reported results, not tests repeated by this docs pass.
Receipt SHA-256 bindings (files under the existing private runner-state directory):

- `main_check.json`: `a39452955a1c16356aa7a955988704f0278f75abf8354e633bf66d98dfc67e55`
- `main-check.log`: `7bfb94086d445bdd1fe2048d7d459d05342a79d83b7bb2c017a3268d6d0eaf46`
- `main-check.exit`: `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`

Latest error inventory, retaining full unittest identities:

- `test_pi_autowork.EngineTests.test_merged_work_is_pushed_to_main_upstream`
- `test_pi_autowork.EngineTests.test_a_backlog_left_unpushed_is_published_at_start`
- `test_pi_autowork.EngineTests.test_upstream_commits_are_pulled_into_main_after_a_task_before_its_push`
- `test_pi_autowork.EngineTests.test_a_rejected_push_merges_the_upstream_and_pushes_again`
- `test_pi_autowork.SetupTests.test_an_idle_runner_updates_its_toolset_and_restarts_on_the_new_code`
- `test_pi_autowork.SetupTests.test_a_release_that_cannot_read_current_state_is_never_installed`
- `test_pi_autowork.SetupTests.test_a_broken_toolset_update_keeps_the_running_code`
- `test_publication_readiness.PublicationReadinessTests.test_ancestry_conflict_never_becomes_force_push_readiness`
- `test_publication_readiness.PublicationReadinessTests.test_multiple_remotes_are_resolved_by_bound_authority_not_origin_guess`
- `test_publishable.PublishableTests.test_a_pointer_to_a_local_only_commit_stays_out_until_it_is_pushed`
- `test_publishable.PublishableTests.test_an_untracked_nested_repository_is_not_added`
- `test_publishable.PublishableTests.test_ordinary_files_are_unchanged`
- `test_release.ReleaseCheckTests.test_a_compatible_release_may_be_installed`
- `test_release.ReleaseCheckTests.test_a_release_that_cannot_read_this_state_is_refused`
- `test_release.ReleaseCheckTests.test_another_runner_with_work_in_flight_defers_the_update`
- `test_release.ReleaseCheckTests.test_fetched_declarations_are_parsed_never_executed`

### Reconciliation with the assigned repair

Fourteen identities were already named in TOOLSET-184-b3. The two additional
EngineTests, `test_a_backlog_left_unpushed_is_published_at_start` and
`test_upstream_commits_are_pulled_into_main_after_a_task_before_its_push`, were added
by `ef85685`; both stop in the same `EngineTests.origin` fixture's initial local
Git push as the existing push cases. They are covered by the repair's existing
`tests/test_pi_autowork.py` scope and full-suite gate, not a separate product task.
The other fourteen previously recorded identities are absent from this latest error
inventory; their absence does not remove any original acceptance or required check.

All 16 tracebacks stop at disposable-repository Git pushes with exit 128, before
exercising the behavior their assertions would qualify. The publication-readiness
cases also print `fatal: transport 'pi-autowork-push-disabled' not allowed`.
This supports investigating the existing fixture-environment seam; it is not a
verified common cause or permission to disable the production worker push guard.

The latest receipt's reported history window is `3bd1d95`, `b5b4944`, `ef85685`,
`36e2b7c`, `7b77f3d`, `99813f9`, `ce43743`, `d9e39b4`, `db2e4ba`, `69937f0`,
`0749177`, `b40d85f`, `2f27806`, `e22cee9`, `605a302`, `1515af8`, `2e415c4`,
`a01e061`, `6aacc26`, `6fee26e`. With no recorded green revision, this is not a
proven since-green range or attribution of fault. Relevant file evidence from
those commits and failing fixtures:

- `3bd1d95`: `scripts/check.py`, `tests/test_check.py`, `tests/test_pi_autowork.py`;
  changes default test concurrency and filters inherited runner settings. It does
  not establish that the remaining Git-fixture errors are fixed.
- `ef85685`: `pi-autowork/pi_autowork/coordinator.py`,
  `pi-autowork/pi_autowork/maintainer.py`, `tests/test_pi_autowork.py`; includes
  the two additional EngineTests and upstream synchronization behavior.
- `36e2b7c`: `scripts/check.py`, `tests/test_check.py`; parallel checker/sharding.
- `7b77f3d`: `pi-autowork/pi_autowork/coordinator.py`,
  `skills/autowork/scripts/parallel_integrate.py`, `tests/test_pi_autowork.py`.
- Failing fixture owners also include
  `skills/autowork/scripts/test_publication_readiness.py`,
  `pi-autowork/tests/test_publishable.py` and `pi-autowork/tests/test_release.py`.
  All these files already fall within TOOLSET-184-b3's declared Touches; no widening
  or dependency change is needed for this receipt.

Reuse the existing repair, not a duplicate of it or of the completed detection
work in TOOLSET-176-98. Its accepted source remains
[Continuous Pi runner](docs/project.md#continuous-pi-runner-2026-10-15).
The required full check remains the task's existing command, planned here rather
than executed by this documentation-only pass:

```sh
tmp=$(mktemp -d /tmp/aw-XXXXXX) && (trap 'rm -rf "$tmp"' EXIT; export TMPDIR="$tmp"; python3 scripts/check.py)
```

Next action remains with the assigned repair worker: diagnose and repair the
fixture boundary, retain every original failing case and assertion, and run the
full gate. No live provider, publication, fleet qualification or repair completion
is inferred from this supplemental receipt.

## MAIN receipt at 3ca53ce and TOOLSET-184-b3 review

Evidence supplement, not completion. TOOLSET-184-b3 still owns the full offline
repair; no competing task is needed. Its Acceptance, status, goal, dependencies
and queue position are unchanged. Its continuation now names the failed review's
fixture seams and the two additional top-level test files it may need to edit.
There is no `slot-data/MAIN/` worker report.

### MAIN receipt binding

The retained `main_check.json` reports red revision
`3ca53ce5d08f8c245ea1be9073a6543e6853ae98`, `green: null`, and
`red_since: 36e2b7c0ea0c6096a7b20197edcacf68dc11dfa4`.
`main-check.exit` is 1. The completed log ends
`Offline result: 2 test directories passed; 3 failed; 8 modules excluded.`
Its 25 distinct FAIL/ERROR identities exceed the summary's first 20 names;
retain the full inventory rather than treating the truncated user trigger as a
complete list. Receipt SHA-256 bindings:

- `main_check.json`: `426e458f20c54d33c9656b33b57836a1829e819a89ebf8a74e10f5c1868b0504`
- `main-check.log`: `93da2aab6d99498a059dc53a387e89feee538f33d01999a466cb73151d59857e`
- `main-check.exit`: `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`

Full failure inventory:

- `test_pi_autowork.EngineTests.test_merged_work_is_pushed_to_main_upstream`
- `test_pi_autowork.EngineTests.test_a_backlog_left_unpushed_is_published_at_start`
- `test_pi_autowork.EngineTests.test_upstream_commits_are_pulled_into_main_after_a_task_before_its_push`
- `test_pi_autowork.EngineTests.test_a_rejected_push_merges_the_upstream_and_pushes_again`
- `test_pi_autowork.SetupTests.test_an_idle_runner_updates_its_toolset_and_restarts_on_the_new_code`
- `test_pi_autowork.SetupTests.test_a_release_that_cannot_read_current_state_is_never_installed`
- `test_pi_autowork.SetupTests.test_a_broken_toolset_update_keeps_the_running_code`
- `test_budget_controller.BudgetTests.test_failed_race_evidence_survives_assertion_and_temp_cleanup`
- `test_budget_controller.BudgetTests.test_final_effect_read_error_fails_qualification_without_erasing_evidence`
- `test_budget_controller.BudgetTests.test_final_snapshot_error_preserves_real_deadline_failure`
- `test_budget_controller.BudgetTests.test_final_snapshot_error_retains_normal_process_evidence`
- `test_budget_controller.BudgetTests.test_final_source_read_error_fails_qualification_without_erasing_evidence`
- `test_parallel_adversarial.AdversarialWorkerTests.test_a_report_written_after_a_coordinator_restart_is_adopted`
- `test_parallel_e2e.EndToEndTests.test_abc_real_cli`
- `test_parallel_e2e.EndToEndTests.test_abc_with_delayed_initial_observation`
- `test_parallel_e2e.EndToEndTests.test_serial_control`
- `test_publication_readiness.PublicationReadinessTests.test_ancestry_conflict_never_becomes_force_push_readiness`
- `test_publication_readiness.PublicationReadinessTests.test_multiple_remotes_are_resolved_by_bound_authority_not_origin_guess`
- `test_publishable.PublishableTests.test_a_pointer_to_a_local_only_commit_stays_out_until_it_is_pushed`
- `test_publishable.PublishableTests.test_an_untracked_nested_repository_is_not_added`
- `test_publishable.PublishableTests.test_ordinary_files_are_unchanged`
- `test_release.ReleaseCheckTests.test_a_compatible_release_may_be_installed`
- `test_release.ReleaseCheckTests.test_a_release_that_cannot_read_this_state_is_refused`
- `test_release.ReleaseCheckTests.test_another_runner_with_work_in_flight_defers_the_update`
- `test_release.ReleaseCheckTests.test_fetched_declarations_are_parsed_never_executed`

The five budget cases are newly recorded in this MAIN receipt. Normal fixture
processes were killed with exit -9 instead of 0, a duplicate race exceeded its
deadline, and the explicit deadline case took 5.265 seconds against its existing
less-than-2-second assertion. The three end-to-end cases refused admission at
load 25.75 against 24 CPUs. Local Git setup still failed at push with exit 128.
These observations do not prove a common cause or permit relaxing assertions,
timeouts, production admission or push denial.

The receipt's reported history window is `3ca53ce`, `3bd1d95`, `c15b392`,
`b5b4944`, `ef85685`, `36e2b7c`, `7b77f3d`, `99813f9`, `ce43743`, `d9e39b4`,
`db2e4ba`, `69937f0`, `0749177`, `b40d85f`, `2f27806`, `e22cee9`, `605a302`,
`1515af8`, `2e415c4`, `a01e061`. This is not a proven since-green range or fault
attribution. `3bd1d95` and merge `3ca53ce` changed `scripts/check.py`,
`tests/test_check.py` and `tests/test_pi_autowork.py`; `c15b392` changed runner
CLI/command/coordinator/fleet/service code, command/engine tests and runner docs.
`ef85685` changed coordinator/maintainer code and engine tests. None of these
commits changed the five budget fixtures; their owning module is nevertheless
inside the existing `skills/autowork/scripts/` Touches and full-suite gate.

### Failed independent review and continuation

Worker report `slot-data/TOOLSET-184-b3/attempt-1/report.json` names commit
`2c23b62f63e3accd07cabf3b6fa70541ad5aad03`, based on `26018cf`, and reports
1,807 passing tests on tree `708adc7fe41d413cf91545521dda9478899dd2f9` with a short
private TMPDIR. This is retained worker evidence, not a repeated docs-pass check.
The candidate adds fixture isolation, bounded checker concurrency and async-review
in-flight tracking. It was not an ancestor of canonical main when inspected.

The runner's `review-findings/TOOLSET-184-b3.json` rejects merged candidate
`a7d3f9f791b3648635e651f23051356903b0908a` with the exact verdict:

> PI_AUTOWORK_VERIFY: fail — Full offline gate exits 1: only 2/5 directories pass. Required TMPDIR exposes socket-path, worktree-cleanup and tx fixture failures; full-gate acceptance is unmet.

The retained review session `pi-autowork-verify-TOOLSET-184-b3-20261017190444`
records a completed canonical-scratch full run, exit 1, 488.41 seconds, with:

- AF_UNIX path overflow in `test_native_containment.PlanTests` (two socket cases),
  six `SyntheticLaunchTests` registration cases (including subtests), and
  `test_janitor.JanitorTests.test_only_stale_unused_entries_are_removed`.
- `test_worktree_closeout.WorktreeCloseoutTests.test_documented_closeout_command_on_main_and_master`
  failing for both merged branch cases, and
  `test_task_execution.DirectExecutionTests.test_claiming_a_task_removes_finished_worktrees_and_keeps_unfinished_ones`
  plus the inherited `RecoveryTests` case: disposable finished worktrees were kept
  under the real review-state ancestor as managed by the runner.
- `test_tx.TxTests.test_tx_has_no_autowork_commands`: the help output's temporary
  config path contained the word, while the failure did not demonstrate a new tx
  command. Inspect the fixture/assertion seam before changing product behavior.

The original review TMPDIR was 85 characters; its expected janitor socket path
was 108. `/proc` aliases avoided that limit but produced canonical-path assertion
failures in fleet/workspace fixtures, so those exploratory runs are not gate passes.
An intermediate interrupt-check failure passed with default SIGINT handling.
The reviewer also reported unreaped fixture processes during earlier runs; that
is a launcher observation, not a proved product defect. The review scratch logs
were removed afterwards; the session retains their commands and output, so no
current-file hash or independent rerun is claimed for those deleted logs.

Worker PID 812010 and reviewer/launcher PIDs 2589109, 2588665, 2775534 and 2775548
were gone when inspected; the retained slot still said `integrating`. The docs
pass changes no slot state, assigned-input hash, budget or review receipt.
Reconcile the retained candidate through the coordinator and fix/recheck the
explicit findings, including the mismatch between the task's short physical
scratch and the reviewer's scratch restriction, before claiming full acceptance.
The existing [accepted runner source](docs/project.md#continuous-pi-runner-2026-10-15)
and every original Acceptance item remain binding; no implementation, full-gate
rerun, live qualification or task closure was performed by this documentation pass.

## MAIN receipt at 7745319

Evidence supplement for TOOLSET-184-b3, not completion or a new task. The runner's
new `main_check.json` reports red revision
`77453195adf012f245ee44487de8cb5e4446664a`, `green: null`, and unchanged
`red_since: 36e2b7c0ea0c6096a7b20197edcacf68dc11dfa4`. The completed
`main-check.log` contains exactly 16 distinct ERROR identities, matching the JSON
summary, and ends `Offline result: 2 test directories passed; 3 failed; 8 modules excluded.`
`main-check.exit` is 1. This is retained runner evidence, not a docs-pass rerun.
Receipt SHA-256 bindings:

- `main_check.json`: `1ea7823a85aa42fb1a8637a4ae76dff6a709204bbb1d07f4d954ebb45a957cfd`
- `main-check.log`: `a9aee7ae725734b90a9eb351a5d085ab8c6f35f1b02507c0c1acea81b37cf22a`
- `main-check.exit`: `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`

Full failure inventory (the maintainer trigger truncated the last test name):

- `test_pi_autowork.EngineTests.test_merged_work_is_pushed_to_main_upstream`
- `test_pi_autowork.EngineTests.test_a_backlog_left_unpushed_is_published_at_start`
- `test_pi_autowork.EngineTests.test_upstream_commits_are_pulled_into_main_after_a_task_before_its_push`
- `test_pi_autowork.EngineTests.test_a_rejected_push_merges_the_upstream_and_pushes_again`
- `test_pi_autowork.SetupTests.test_an_idle_runner_updates_its_toolset_and_restarts_on_the_new_code`
- `test_pi_autowork.SetupTests.test_a_release_that_cannot_read_current_state_is_never_installed`
- `test_pi_autowork.SetupTests.test_a_broken_toolset_update_keeps_the_running_code`
- `test_publication_readiness.PublicationReadinessTests.test_ancestry_conflict_never_becomes_force_push_readiness`
- `test_publication_readiness.PublicationReadinessTests.test_multiple_remotes_are_resolved_by_bound_authority_not_origin_guess`
- `test_publishable.PublishableTests.test_a_pointer_to_a_local_only_commit_stays_out_until_it_is_pushed`
- `test_publishable.PublishableTests.test_an_untracked_nested_repository_is_not_added`
- `test_publishable.PublishableTests.test_ordinary_files_are_unchanged`
- `test_release.ReleaseCheckTests.test_a_compatible_release_may_be_installed`
- `test_release.ReleaseCheckTests.test_a_release_that_cannot_read_this_state_is_refused`
- `test_release.ReleaseCheckTests.test_another_runner_with_work_in_flight_defers_the_update`
- `test_release.ReleaseCheckTests.test_fetched_declarations_are_parsed_never_executed`

Reported commit window: `7745319`, `7e804d0`, `0de0ae6`, `c3f3230`, `3ca53ce`,
`3bd1d95`, `c15b392`, `b5b4944`, `ef85685`, `36e2b7c`, `7b77f3d`, `99813f9`,
`ce43743`, `d9e39b4`, `db2e4ba`, `69937f0`, `0749177`, `b40d85f`, `2f27806`,
`e22cee9`. With no recorded green revision this is neither fault attribution nor
a proven since-green range. The existing repair's Touches cover the failing
modules: `tests/test_pi_autowork.py`, `skills/autowork/scripts/test_publication_readiness.py`,
`pi-autowork/tests/test_publishable.py` and `pi-autowork/tests/test_release.py`.
Relevant history already covered by its Touches includes `ef85685`'s coordinator,
maintainer and engine-test changes and `3bd1d95`'s checker and fixture changes.
`7e804d0` changes bundle/update code and tests; `0de0ae6` changes Docs Sync and its
first-index tests. Neither is evidence that those unrelated paths must be added
to this repair. Local bare-remote fixture pushes still exit 128 before the tested
behavior runs; preserve production push denial and the existing fixture-only
isolation boundary, not a broader publication permission.

### Existing repair and live ownership

The accepted [continuous runner source](docs/project.md#continuous-pi-runner-2026-10-15),
TOOLSET-184-b3's full-suite Acceptance and Checks, and its explicit failed-review
continuation already cover this inventory. All 16 names are also preserved in the
preceding receipt. A smaller inventory at a different revision does not qualify
that candidate or waive the socket, cleanup, tx or budget checks from its contract.
No `add-task`, supersession, scope widening or priority change is warranted.

The current slot records a running repair worker at baseline `0c420d5`, PID
3084725, start ticks 307194372; both process birth and boot identity matched when
inspected. There is no current `attempt-1/report.json` yet. The older report is
retained under `slot-history/TOOLSET-184-b3/1/slot-data/attempt-1/report.json`;
it names worker commit `2c23b62`, not a result from this running worker. That commit
is not an ancestor of the recorded red main. The retained review finding still
rejects merged candidate `a7d3f9f`; neither old receipt establishes current success.

Only the queue overview is corrected to observe the running repair rather than
instruct another resume of the old candidate. Every task body, Acceptance item,
Checks command, dependency, ledger state and queue position is preserved. Collect
the current worker's result through the existing coordinator and obtain the
required full gate and independent review; do not repin, release, reset or start
a competing worker. No runtime repair, full offline rerun, dispatch, live acceptance
or task closure was performed by this documentation pass.

Consumer check limitation: `backlog-check` for TOOLSET-184-b3 against the accepted
continuous-runner heading returns `draft_saved` (exit 1) both in this candidate and
the runner's session checkout, because two existing Sources links in TOOLSET-179-cf
and TOOLSET-130-15 target the absent `canonical-plan-and-session-reconciliation`
heading in the coordinator plan. Those bodies and the missing plan section are
outside this MAIN repair; no replacement approval or plan content is invented.
`next --json` still selects TOOLSET-184-b3 first with synchronized priority; that
ledger eligibility does not authorize another worker or certify consumer readiness.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-174-1d — Restarting a runner keeps its workers running

- [x] TOOLSET-174-1d — Restarting a runner keeps its workers running
- Status: done 2026-10-17 by the owner session (c15b392, merged in 3ca53ce): `autowork restart` reloads in place by SIGHUP; live, six runners reloaded with their workers running and one deferred behind its review.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17): "plan a task so restarts don't interrupt workers"; [service commands](pi-autowork/pi_autowork/command.py) (`cmd_stop` for `restart`, the model change, the package move), [service unit](pi-autowork/pi_autowork/service.py) (`UNIT`, the install restart), [self-restart and signals](pi-autowork/pi_autowork/coordinator.py) (`restart_if_updated`, `on_signal`), [TUI restart action](pi-autowork/pi_autowork/fleet_view.py), [service docs](docs/cross-host.md).
- Evidence (2026-10-17, this repository's runner): `autowork restart` runs `systemctl restart`. The unit stops with SIGINT and `KillMode=mixed`, so every worker pauses, and systemd kills what is left of the service's processes when the stop ends. Two restarts cut off TOOLSET-165-f7: at 13:43, five seconds after its worker started, and at 14:42, 34 seconds after the runner had already restarted itself on the new release. The second cost a 10-minute run and about 1M tokens. Both resumed only because a pause keeps the attempt. The runner's own self-update (`restart_if_updated`) re-executes in place with the same PID and adopts running workers, so a restart that only needs new code or settings does not have to stop anything.
- Touches: pi-autowork/pi_autowork/command.py, pi-autowork/pi_autowork/service.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/fleet_view.py, tests/test_autowork_command.py, tests/test_pi_autowork.py, pi-autowork/tests/test_fleet_view.py, docs/cross-host.md
- Scope: (1) `autowork restart`, the TUI restart action and the model change reload the runner in place: the unit gets `ExecReload` sending SIGHUP to the main process, and on SIGHUP the runner re-executes at its next safe point exactly as `restart_if_updated` does, keeping its PID and adopting running workers and reviews. (2) A reload re-reads the service's env file, so new settings (such as a changed model) apply to every run that starts afterwards; running workers keep theirs. (3) A runner that is not running is started, as today. When the reload cannot take effect (the unit's `ExecStart` itself changed, or the runner has not re-executed within `TimeoutStopSec`), the command says so and names `autowork restart --stop-workers`, the only form that stops the service and pauses workers. (4) Installing or moving the service reloads running services instead of restarting them, unless their `ExecStart` changed. `autowork stop` and host shutdown keep the pause-and-resume behavior. (5) Output says what happened: `Reloaded <unit>; <n> workers kept running`.
- Acceptance: In fixtures with a fake systemctl and a fake Pi, `autowork restart` during a running worker leaves the worker's process and attempt unchanged, the runner keeps its PID, the run finishes and integrates, and the log shows one reload line and no `Stopping: pausing workers`. A model change by reload starts the next worker with the new model and leaves the running one alone. `autowork restart --stop-workers` and `autowork stop` still pause and resume on the same attempt. A runner that ignores the reload past the timeout gets the clear message and is not killed.
- Checks: python3 -m unittest discover -s tests -p test_autowork_command.py; python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 -m unittest discover -s pi-autowork/tests -p test_fleet_view.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the self-update, to how a stop pauses workers, or to resume and retry rules. No worker survival across a real service stop or a reboot.
- Planner's call: third in Now, behind TOOLSET-165-f7 and TOOLSET-170-f6. Each interrupted run is paid again, and interactive sessions restart runners after every push.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-183-d6 — A review runs beside the runner's loop, so dispatch, status and questions continue while a commit is verified

- [x] TOOLSET-183-d6 — A review runs beside the runner's loop, so dispatch, status and questions continue while a commit is verified
- Status: done 2026-10-17 by the owner session (7b77f3d, merged in b5b4944): the review runs as a child the loop polls; offline check passed apart from load-gated tests that passed on rerun.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [coordinator](pi-autowork/pi_autowork/coordinator.py) (`settle`, which calls `self.engine('--integrate', …)` and waits), [integration](skills/autowork/scripts/parallel_integrate.py) (`integrate`, `retry_held` and their `dispatch.lock`/`integration.lock`), [dispatch](skills/autowork/scripts/parallel_dispatch.py) (`dispatch_with_retries`).
- Evidence (2026-10-17 16:49–17:10, this repository's runner): after a restart the runner started integrating one held commit whose review runs the full offline check (about 25 minutes, twice in parallel inside the reviewer). For the whole review the runner ran 0 workers with 56 tasks waiting, wrote no `status.json` (last at 16:19), logged nothing and could not start its new main check (TOOLSET-176-98), because `settle` waits on the engine call. The fleet view kept it `working` only through the reviewer's transcript activity.
- Touches: pi-autowork/pi_autowork/coordinator.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/test_parallel_dispatch.py, tests/test_pi_autowork.py, skills/autowork/references/parallel-workers.md
- Scope: (1) The coordinator starts each `--integrate` as a child it tracks (like a worker), records it in `job.json`-style state (task, started, pid) and polls it each cycle; one integration at a time stays the rule. (2) While it runs, the loop goes on: dispatch of independent tasks, health and status, questions, the janitor. The engine's dispatch path must not wait on `integration.lock`: `dispatch_with_retries` skips its held-slot retry pass (which takes the integration lock) while an integration owns it, and plain dispatch never takes that lock. (3) A task being integrated keeps its files reserved for admission exactly as today, so nothing dispatched beside the review can touch them. (4) A runner restart during an integration leaves the engine's existing recovery to resume or redo it.
- Acceptance: In fixtures with a slow reviewer, the runner dispatches an independent task and refreshes `status.json` while the review runs; the integrated result is closed as today when it ends; a task overlapping the one under review still waits; two integrations never run at once; a restart mid-review recovers as today.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p 'test_parallel_*.py'; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator; reconcile TOOLSET-174-1d (restart keeps workers running) in the coordinator first.
- Exclusions: No parallel integrations; no change to what a review checks.
- Planner's call: high in Now. A review that runs a full check idles a whole runner for half an hour, every time.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-187-1d — A reload or self-update waits until the finished review's answer is collected

- [x] TOOLSET-187-1d — A reload or self-update waits until the finished review's answer is collected
- Status: done 2026-10-17 by the owner session (f4a7d11, merged in ced5a52); its regression test fails on the old code and passes now.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [re-execution](pi-autowork/pi_autowork/coordinator.py) (`reexec`, `restart_if_updated`, `session_busy`, `collect_integration`, the order of `cycle`); TOOLSET-174-1d and TOOLSET-183-d6, both done.
- Evidence (2026-10-17, this repository's runner): `autowork restart` at 19:06 found TOOLSET-184-b3 under review and deferred the reload, as designed. The review finished; at 19:30 the next cycle re-executed (`Reloading: settings and release re-read`) before collecting it, because `reexec` waits only while `session_busy()` (the review process still runs) and `restart_if_updated` runs at the top of `cycle`, before the integration's answer is read. The answer file was dropped with the old process; at 19:35 the engine failed the task with `abandoned integration lacks exact candidate/contract/branch evidence`, and the task ran again from scratch. Every reload or self-update deferred behind a review re-executes at exactly this point, so each one loses that review.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) Re-execution is a safe point only when no integration is recorded at all: `self.integration` is None, not merely a finished process. (2) A finished integration is collected and its outcome applied (integrated, held or failed, with its log line) before the cycle re-executes, in the same cycle. (3) The same rule covers the self-update and the reload, and a Pi job (`self.child`) as today.
- Acceptance: In a fixture, a SIGHUP sent while a slow review runs re-executes only after the log shows that task's `integrated` line, the task integrates once with no `abandoned integration` failure, and the runner keeps its PID. The same holds for a toolset update during a review. The existing reload and review-beside-the-loop tests still pass.
- Checks: python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to when a reload is requested, to the review itself or to how a stop ends a review.
- Planner's call: first in Now, ahead of TOOLSET-186-07: each deferred reload or self-update costs a full review (about 25 minutes of model time here), and interactive sessions reload runners after every push.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-186-07 — The offline check runs tests without the runner's push guard

- [x] TOOLSET-186-07 — The offline check runs tests without the runner's push guard
- Status: done 2026-10-17 by the owner session (f4a7d11, merged in ced5a52); its regression test fails on the old code and passes now.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [push guard](pi-autowork/pi_autowork/common.py) (`push_guard`), [offline check](scripts/check.py) (the environment it gives test processes), [main check](pi-autowork/pi_autowork/main_check.py).
- Evidence (2026-10-17, this repository's runner): its main check reported main red at 3ca53ce with 20 failing tests, and the same full gate failed TOOLSET-184-b3's review. Every failure that names a cause is a fixture's own `git push` to a temporary bare repository: `test_merged_work_is_pushed_to_main_upstream` fails in `self.origin()` on `git push -q -u origin main`, and `test_publishable` fails in `setUp` on `git push -q origin HEAD:main`. The same commit passed `python3 scripts/check.py` outside the runner (apart from load-gated tests that passed on rerun). The runner calls `push_guard()`, which sets `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_n` and `GIT_CONFIG_VALUE_n` so that every push fails; the main check and every reviewer inherit them, and `scripts/check.py` strips only `PI_AUTOWORK_*` and `AUTOWORK_*`. TOOLSET-184-b3 started fixing this per test module (`local_git_env` in three modules), which leaves `tests/test_pi_autowork.py` and any new fixture exposed. A false red also makes the DOCS-MAINTAINER plan repairs for tests that are not broken.
- Touches: scripts/check.py, tests/test_check.py
- Scope: (1) `scripts/check.py` removes the push guard's variables (`GIT_CONFIG_COUNT` and every `GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n` whose key is one of `push_guard`'s) from the environment of the test processes it starts, next to the `PI_AUTOWORK_*` removal; other `GIT_CONFIG_*` entries are kept. (2) The test processes still cannot push to a real remote by accident: fixtures push only to temporary file remotes, as today. (3) Nothing else in the runner's own guard changes: the runner, its workers and Pi's tools keep failing every push.
- Acceptance: With the push guard set in the calling environment, `python3 scripts/check.py` (or a test-sized fixture of it in `tests/test_check.py`) runs a test that pushes to a temporary bare repository and passes, and a test process sees no `pi-autowork-push-disabled` configuration. The runner's own `git push` still fails under the guard.
- Checks: python3 -m unittest discover -s tests -p test_check.py; python3 scripts/check.py with TMPDIR set to a fresh short directory, run once with the push guard's variables exported
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to `push_guard`, to fixture code beyond what TOOLSET-184-b3 already owns, or to how the main check records results.
- Planner's call: first in Now, ahead of TOOLSET-184-b3's retry: until it lands, every review and main check of this repository fails on fixture pushes, so 184-b3 cannot pass review however its fixtures are repaired. It shares `scripts/check.py` with 184-b3, so integrate it first and let 184-b3 rebase onto it.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-185-74 — An idle runner waits out its interval instead of re-cycling on its own ref changes

- [x] TOOLSET-185-74 — An idle runner waits out its interval instead of re-cycling on its own ref changes
- Status: done 2026-10-17 by the owner session (f4a7d11, merged in ced5a52); its regression test fails on the old code and passes now.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [the idle wait](pi-autowork/pi_autowork/coordinator.py) (`pause`, `plan_signature`, the `IDLE` branch of `cycle` with `end_session`).
- Evidence (2026-10-17, one fleet runner with an empty queue and one held task): 213 `Session pi-autowork/<stamp> started from <base>` lines in 40 minutes, each followed by `Queue empty; checking again in 60s` and, about one second later, `main changed; checking now`. The base branch's ref had not moved for 24 minutes. Its `packed-refs` held only the header line, yet its mtime was the last cycle's second: ending the empty session deletes the session branch, Git 2.43 rewrites `packed-refs` on that delete, and `plan_signature` stats `packed-refs` as part of "main", so the runner's own cleanup ends its wait. Each loop creates and deletes a branch and a worktree and runs the engine; no model is called, but the runner never rests and its log is unreadable.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) The main-branch part of `plan_signature` is the base branch's commit, not file stats: read the loose ref, or the base's line in `packed-refs` when there is no loose ref, only when either file's stat changed since the last read (still no Git subprocess per second). (2) A `packed-refs` rewrite that leaves the base's commit unchanged is not a change. (3) The planning files keep their stat comparison.
- Acceptance: In a fixture with an empty queue, a runner started with `--interval 5` logs at most one session start and one `Queue empty` per interval over 20 seconds, while `git pack-refs` and deleting an unrelated branch run in the meantime. A commit to the base branch (loose or packed ref) still ends the wait within the settle time, as the existing plan-change tests show.
- Checks: python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to session creation or ending, to the interval, or to how planning-file edits end the wait.
- Planner's call: first in Now. It is small, and a runner with an empty queue spins without pause until it is fixed; the existing Now tasks keep their order behind it.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-188-75 — A session's planning commits land on main within minutes, not only when a task closes

- [x] TOOLSET-188-75 — A session's planning commits land on main within minutes, not only when a task closes
- Status: done 2026-10-17 by the owner session (6e1f39a, merged in e905fb4); its regression test fails on the old code and passes now.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [landing](pi-autowork/pi_autowork/coordinator.py) (`land`, `merge_main`, `sync_upstream`, the `IDLE` branch of `cycle`, `maintain`, `update_questions`); owner direction (2026-10-17: commit, push to upstream and pull-merge after every task).
- Evidence (2026-10-17, this repository's runner): its session `pi-autowork/<stamp>` was started at 13:43 and by 20:30 held 13 commits not on main: DOCS-MAINTAINER repairs (three `changed MAIN` runs and the restatement of TOOLSET-184-b3) and BLOCKERS.md question updates. A session lands only after a task closes (`land`) or when the queue is empty; for seven hours every task was running, held or waiting, so neither happened. The owner and other sessions read main, so they saw neither the questions nor the repaired task, and TOOLSET-184-b3 existed only on the session branch.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) After a DOCS-MAINTAINER merge, a questions commit or a Touches widening, and at least every `PI_AUTOWORK_LAND_EVERY` seconds (default 600) while the session is ahead of main, the runner calls `land()` once no review or Pi job runs, exactly as after a closed task: merge the base in, fast-forward main, pull what upstream gained and push. (2) Running workers do not prevent it: they work in their own worktrees and are unaffected by the session moving forward. (3) A landing that cannot happen (main checkout busy or on another branch) keeps today's pending reason; TOOLSET-125-3c reports it.
- Acceptance: In a fixture whose only task runs a slow worker, a BLOCKERS.md question and a maintainer planning commit made on the session reach main (and the fixture upstream) within `PI_AUTOWORK_LAND_EVERY` (set to a few seconds) while the worker still runs; the worker then finishes and integrates normally. With a review running, the landing waits for its answer.
- Checks: python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to what the maintainer or the questions write, to conflict resolution or to the push setting.
- Planner's call: top of the toolset's own Now: the runner's planning, including its repairs of its own held tasks, is invisible until it lands.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-140-f4 — Give workers a short temporary directory that browsers and sockets accept

- [x] TOOLSET-140-f4 — Give workers a short temporary directory that browsers and sockets accept
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [monitor findings](docs/plans/2026-10-16-pi-autowork-coordinator.md#fleet-monitor-findings-delivery-environment-and-stall-repair), [worker launch](skills/autowork/scripts/parallel_dispatch.py) (`launch` sets `TMPDIR=<slot data>/tmp`).
- Evidence (2026-10-16 monitor pass): runner C's a fleet task is held because `/usr/bin/chromium fails with the configured long TMPDIR`. Slot paths under `~/.local/state/pi-autowork/<hash>/…` already exceed 100 characters. Unix-domain socket paths are limited to 108 bytes, which breaks Chromium's SingletonSocket and also ssh, gpg and test servers.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/references/parallel-workers.md, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py
- Touches widened by the runner from worker evidence: pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py
- Scope: Give each slot a private temp directory at `$XDG_RUNTIME_DIR/aw/<state hash 8>/<slot>`, where the state hash is the first 8 characters of the runner's per-repository state directory name under `~/.local/state/pi-autowork/`, falling back to `/tmp/aw-<uid>-<hash8>-<slot>`. Create it with mode 0700 and owner checked; reject a pre-existing path owned by anyone else. Set `TMPDIR`, `TMP` and `TEMP` to it. A resumed worker keeps the same directory, and slot retirement removes it. Keep at least 60 bytes of headroom below the socket limit.
- Acceptance: Fixtures show the following. TMPDIR is at most 48 characters, mode 0700 and distinct per slot. Binding an AF_UNIX socket with a 40-character name inside it succeeds. A foreign-owned pre-existing path is refused. The directory survives runner restart and adoption, and is removed on retirement. Existing dispatch and refill tests pass.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 scripts/check.py
- Bootstrap note (planner's call): this task's own worker still inherits the long TMPDIR. Its tests must create the short directory themselves and must not rely on the inherited one. If `scripts/check.py` fails only on AF_UNIX socket fixtures under the inherited long TMPDIR, as TOOLSET-115-bf observed, record that as the pre-existing condition this task removes, not as a regression. Run it once more with `TMPDIR` set to a short private directory and require that run to pass.
- Dependencies: None.
- Ownership: Toolset coordinator. The held a fleet task reruns through the runner's own retry once this is delivered; nobody edits the fleet repository by hand.
- Exclusions: No browser installation and no per-repository Chrome configuration.
- Planner's call (2026-10-17): moved up, next to TOOLSET-188-75: TOOLSET-184-b3's worker is held on it too (`a private physical task TMPDIR with no ancestor containing .git`); today's `<slot data>/tmp` lies inside the repository's `.git`, so no retry can satisfy that. XDG_RUNTIME_DIR first, because it is per-user, 0700 and tmpfs.
- Planner answer (2026-10-17 09:15, monitor pass): its worker asked for `skills/autowork/scripts/parallel_integrate.py`. It and its test are added to Touches. Resume or reverify the existing candidate; do not reimplement.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-190-bf — A landing that needs no merge goes ahead during a review

- [x] TOOLSET-190-bf — A landing that needs no merge goes ahead during a review
- Status: done 2026-10-17 by the owner session (5c3d3aa, merged in 7039f47); pi-autowork/tests/test_landing.py fails on the old code and passes now.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [landing](pi-autowork/pi_autowork/coordinator.py) (`land_planning`, `land`, `merge_main`, `session_busy`); TOOLSET-188-75 (done).
- Evidence (2026-10-17, this repository's runner, after TOOLSET-188-75 was deployed): other runners landed planning commits within a minute (`DOCS-MAINTAINER: merged`, then `Merged ... into main`, `Pushed main`), but this one still held 14 commits off main 40 minutes later. Its reviews run the full offline check (about 25 minutes each) back to back, and every landing waits until no review runs, because `merge_main` first merges the base into the session, which would move the branch the review fast-forwards at its end.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) While a review runs, a due landing (TOOLSET-188-75's triggers) goes ahead when the base is already an ancestor of the session, so no merge is needed: fast-forward the base in the main checkout to the session's current tip and push, without touching the session branch or its worktree. (2) When the base has moved, the landing waits for the review as today. (3) The review's own fast-forward of the session at its end is unaffected; the next landing carries it.
- Acceptance: In a fixture with a slow review running and a questions commit on the session (base not moved), the question reaches main and the fixture upstream before the review ends, and the reviewed task then integrates and lands normally. With the base moved by an outside commit, the landing waits for the review.
- Checks: python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No merge into the session during a review; no change to what lands.
- Planner's call: right after TOOLSET-189-96: a runner whose reviews run long full checks otherwise keeps its planning invisible for hours, as before TOOLSET-188-75.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-191-0a — autowork restart reloads a runner that is re-executing, instead of restarting it

- [x] TOOLSET-191-0a — autowork restart reloads a runner that is re-executing, instead of restarting it
- Status: done 2026-10-17 by the owner session (cc59768); its fixture test fails on the old code and passes now.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [reload](pi-autowork/pi_autowork/service.py) (`reload_in_place`, `runner_record`), [re-execution](pi-autowork/pi_autowork/coordinator.py) (`reexec` unlinks `runner.json`; the new process writes it after taking the lock).
- Evidence (2026-10-17): two `autowork restart` rounds a few minutes apart; in the second, one runner answered `Restarted ...; workers paused and resume on the same attempt` while the others reloaded. Between `reexec` removing `runner.json` and the re-executed process writing it again, `runner_record` finds no record, `reload_in_place` treats the runner as one from before reloads and the command restarts the unit, pausing its worker.
- Touches: pi-autowork/pi_autowork/service.py, tests/test_autowork_command.py
- Scope: (1) With the service active and no `runner.json`, `reload_in_place` waits up to 10 seconds for the record before deciding; a record without `reloads` still means an old runner. (2) A record that appears with a higher `reloads` than before the command (or any record while the unit's main PID is unchanged) counts as reloaded, with no second signal.
- Acceptance: In a fixture with a fake systemctl, `autowork restart` while `runner.json` is missing and reappears with `reloads` after 2 seconds prints `Reloaded`, sends one SIGHUP and no `restart`; with no record after 10 seconds it restarts as today.
- Checks: python3 -m unittest discover -s tests -p test_autowork_command.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to `reexec` or to the record's contents.
- Planner's call: small and near the top: each wrong restart pauses a worker, which is what TOOLSET-174-1d removed.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-193-54 — A test the host's resource gate refuses is skipped, not failed, so a busy host never reads as red

- [x] TOOLSET-193-54 — A test the host's resource gate refuses is skipped, not failed, so a busy host never reads as red
- Status: done 2026-10-17 by the owner session (merged in 45b6320); python3 scripts/check.py passed with no failures at load 17.9; its main-check and check.py tests fail on the old code.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [resource gate](skills/autowork/scripts/parallel_dispatch.py) (`resource_gate`), end-to-end tests that dispatch real workers (`skills/autowork/scripts/test_parallel_e2e.py`, `test_parallel_adversarial.py`), [main check](pi-autowork/pi_autowork/main_check.py), [offline check](scripts/check.py).
- Evidence (2026-10-17, this repository's runner): `Main is red at cc59768: 4 failing`: `test_parallel_adversarial.AdversarialWorkerTests.test_a_report_written_after_a_coordinator_restart_is_adopted` and three `test_parallel_e2e.EndToEndTests` tests. All six gate lines in that log read `resource gate: load average 26.77 >= 24 CPUs`: the tests dispatch through the real gate, the host's load (the fleet's own workers) refused them, and they report it as a failure. The same four failed in every full check started at a high load that day and passed when rerun below the gate. A false red sends the DOCS-MAINTAINER to plan a repair (`changed MAIN`), and a review that runs the full check rejects a sound candidate.
- Touches: skills/autowork/scripts/test_parallel_e2e.py, skills/autowork/scripts/test_parallel_adversarial.py, skills/autowork/scripts/offline_fixtures.py, scripts/check.py, tests/test_check.py, pi-autowork/pi_autowork/main_check.py, pi-autowork/tests/test_main_check.py
- Scope: (1) A test that dispatches through the real gate and gets a `resource gate:` refusal raises `unittest.SkipTest` with that reason (one shared helper), instead of failing. (2) `scripts/check.py` prints the number of tests skipped by the gate in its summary, and exits non-zero only for real failures. (3) The main check records gate-skipped tests and, when any were skipped, runs the check again once the load is below the gate (at most once per main revision) before calling main green; a red from real failures is unaffected.
- Acceptance: In a fixture with the gate forced to refuse (an environment override for the load threshold), the four tests are skipped with the gate reason, `scripts/check.py` exits 0 and reports them, and the main check reports green-pending rather than red; with the override removed they run and pass.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_e2e.py; python3 -m unittest discover -s tests -p test_check.py; python3 -m unittest discover -s pi-autowork/tests -p test_main_check.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the gate's thresholds (TOOLSET-118-68) or to production dispatch; no bypass of the real gate in these tests.
- Planner's call: high in Now: every busy hour turns this repository's main red and wastes a maintainer run, and reviews of toolset tasks fail on a busy host.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-194-46 — An integration under way waits briefly for the writer lock instead of ending BUSY and abandoned

- [x] TOOLSET-194-46 — An integration under way waits briefly for the writer lock instead of ending BUSY and abandoned
- Status: done 2026-10-17 by the owner session (merged in 2e755cb); python3 scripts/check.py passed with no failures; the waiting-lock test fails on the old code with BlockingIOError.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [integration](skills/autowork/scripts/parallel_integrate.py) (`integrate`: the slot becomes `integrating`, then `save_receipt` and the merge take `writer.lock` again), [locks](skills/autowork/scripts/task_execution.py) (`lock` is non-blocking; `BlockingIOError` becomes `BUSY`), [loop](pi-autowork/pi_autowork/coordinator.py) (`start_integration` runs beside dispatch since TOOLSET-183-d6).
- Evidence (2026-10-17, one fleet runner, from its journal and log): a task was `verifying` from 22:03 and its slot `integrating` from 22:03:06; at 22:05 the runner logged `waiting to integrate until another session leaves the main checkout (Repository execution lock is held by a live operation.)` and started the next reported task's review, which integrated at 22:07 and landed. The first task's slot stayed `integrating`; at 22:07:23 the engine held it with `abandoned integration tree changed or ambiguous; preserve for diagnosis` and it ran again from scratch as `-r2`. Since reviews run beside the loop (TOOLSET-183-d6), the loop's own `--apply --parallel` takes `writer.lock` each cycle while the review child also takes it, non-blocking, for every receipt and for the merge; whichever loses gets `BlockingIOError`, which the child reports as BUSY after it already marked the slot `integrating`. Another runner stalled 33 minutes on the same message that evening.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/task_execution.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) Once a slot is `integrating`, every later `writer.lock` (and `integration.lock`) acquisition in that integration waits up to `AUTOWORK_LOCK_WAIT` seconds (default 60), retrying non-blocking every 0.2 s, before giving up; the loop's own holders release within seconds. (2) If it still cannot take the lock, the integration returns the slot to `reported` (removing its integration worktree) before answering BUSY, so it is retried, never abandoned. (3) The coordinator logs the "another session in the main checkout" message only when the holder is not this runner's own process tree (the PIDs holding the lock, as `fuser` shows them, are compared with the runner and its children); for its own contention it says nothing and retries next cycle.
- Acceptance: In a fixture, an integration whose receipt step meets `writer.lock` held by another process for 2 seconds completes INTEGRATED with no BUSY; held for longer than the wait, the slot ends `reported`, not `integrating`, and the next integration of it succeeds with no `abandoned integration` hold. A runner fixture with a slow review and dispatch every second integrates every task once.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to which operations take which lock, and no blocking wait before a slot is `integrating` (dispatch keeps its non-blocking refusal).
- Planner's call: first in Now: since TOOLSET-183-d6 every runner with reviews and dispatch in the same minute can lose a finished task's work this way.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-196-fb — A review that runs out of time is retried with a longer limit, without spending the task's attempt

- [x] TOOLSET-196-fb — A review that runs out of time is retried with a longer limit, without spending the task's attempt
- Status: done 2026-10-17 by the owner session (9af9e76); scope (1) and (2) delivered with tests; (3), the owner question after a timeout at the four-hour cap, is not built: such a task stays held with cause timeout.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [integration](skills/autowork/scripts/parallel_integrate.py) (`passed`, the validation hold), [bounded command](skills/autowork/scripts/task_execution.py) (outcome `TIMED_OUT`), [verify timeout](pi-autowork/pi_autowork/worker.py) (`PI_AUTOWORK_VERIFY_TIMEOUT`, default 1800), [coordinator](pi-autowork/pi_autowork/coordinator.py) (`start_integration`, `count_failure`).
- Evidence (2026-10-17, this repository's runner): TOOLSET-165-f7's reviews ended `TIMED_OUT` at 1829 s and 1925 s against the 1800 s limit, and the task was held with `missing, failed, stale or mismatched integration validation` after its second attempt: two attempts spent on the host's speed, not on the task. The repository's full check alone takes 8 to 9 minutes; the reviewer's model work and the task's own checks take the rest. The owner session raised `PI_AUTOWORK_VERIFY_TIMEOUT` for this runner by hand.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/worker.py, tests/test_pi_autowork.py, docs/cross-host.md
- Scope: (1) A validation that ends `TIMED_OUT` holds with cause `timeout`, kept apart from `validation`, and does not count toward the task's attempts or the runner's failure streak. (2) The runner records each finished review's duration per repository; the next review's limit is the larger of `PI_AUTOWORK_VERIFY_TIMEOUT` and twice the longest of the last five, capped at four hours, and a task held for `timeout` is reverified once with that limit doubled. (3) A second timeout at the cap becomes one owner question naming the durations. Status and the TUI show the limit in use.
- Acceptance: In fixtures, a review that outlasts a 2-second limit holds with cause `timeout`, keeps attempt 1, and is reverified with a 4-second limit, then integrates; the failure streak is unchanged. After reviews of 3 and 5 seconds, the next limit is at least 10 seconds. Two timeouts at the cap give one question and no third run.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to worker timeouts or to what a review checks.
- Planner's call: high in Now: a slow host should cost minutes, not a task's attempts; this repository's own tasks were held by it.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-198-8f — An answered question stays answered: a task entry that names its holder ends the claim question

- [x] TOOLSET-198-8f — An answered question stays answered: a task entry that names its holder ends the claim question
- Status: done 2026-10-17 by the owner session (merged in 8ba53fe): scope (1) without the separate `held by` waiting line (the task still shows under claimed elsewhere), (2), (3) and (4); python3 scripts/check.py passed.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner report (2026-10-17: "contradiction!!!", pasting `/blockers` answering "0 new questions; the T-… and T-… notices remain covered by your earlier answers" beside the TUI showing "2 questions for you" for the same two tasks); [questions](pi-autowork/pi_autowork/questions.py) (`build`, the `claim` question and its Answer text), [Blockers](skills/blockers/SKILL.md) (where answers are saved), [fleet view](pi-autowork/pi_autowork/fleet_view.py) (the questions count and list).
- Evidence (2026-10-17, one fleet runner): its claim question offers two answers: `set Status: open ... otherwise note who holds it and when it will be done`. The owner took the second: both task entries name their holder (an isolated continuation to preserve) and stay `in_progress`. `/blockers` reads that as answered; the runner rebuilds its questions from engine state every cycle, sees the same claim, and keeps both questions open, so the TUI and BLOCKERS.md (since 01:25 that day) ask again for what is answered.
- Touches: pi-autowork/pi_autowork/questions.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/tests/test_questions.py, pi-autowork/tests/test_fleet_view.py, skills/blockers/SKILL.md, skills/docs-sync/SKILL.md
- Scope: (1) A task entry may carry `Held by: <who or what>; until <YYYY-MM-DD>` (the claim's answer, written by `/blockers` or the owner). While that line is present and its date has not passed, the runner writes no claim question for the task; the TUI and status show it under waiting as `held by <who> until <date>`, not as a question. After the date, the question returns once, noting the expired answer. (2) The claim question's Answer text names that field exactly. (3) `/blockers` records a "someone holds it" answer as that field, and treats an entry with a current `Held by:` as answered. (4) An entry without the field keeps today's behavior.
- Acceptance: In fixtures, a claimed task whose entry has `Held by: isolated continuation; until <tomorrow>` yields no claim question and a `held by` waiting line; with yesterday's date the question returns, mentioning the expired answer; without the line the question is as today. The fleet view's questions count excludes such tasks.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_questions.py; python3 -m unittest discover -s pi-autowork/tests -p test_fleet_view.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No automatic adoption of claimed tasks; no model call to read answers.
- Planner's call: first in Now: a runner asking the owner what is already answered breaks the one rule the owner set for questions.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-205-a1 — A fresh attempt is told about its task's earlier work on set-aside branches and may build on it

- [x] TOOLSET-205-a1 — A fresh attempt is told about its task's earlier work on set-aside branches and may build on it
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17/18); [dispatch](skills/autowork/scripts/parallel_dispatch.py) (the worker prompt and worktree), [set-aside](skills/autowork/scripts/parallel_integrate.py) (`entry_changed`: a held task whose entry changed runs fresh, earlier work kept on `autowork/<task>-set-aside-N`), [worker](pi-autowork/pi_autowork/worker.py).
- Evidence (2026-10-17/18, two fleet runners): one task has five `autowork/<task>-set-aside-1..5` branches; its latest fresh attempt stopped with `both authorized candidate files are absent from the current worktree`, as earlier attempts did. The task's plan (rewritten by the owner and the DOCS-MAINTAINER) tells the worker to preserve and continue its earlier candidate, but a fresh attempt starts from a clean worktree at main and its prompt never names the set-aside branches, so the worker cannot find that work and reports a blocker instead. Another runner's workers stopped the same way asking for a "retained prerequisite" commit that was not an ancestor of their baseline.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, skills/autowork/references/parallel-workers.md
- Scope: (1) When a task has earlier work (its `autowork/<task>-set-aside-N` branches, or the previous attempt's branch), the worker prompt lists each with its tip commit, date and changed files, newest first, and says the worker may merge or cherry-pick from them when the task asks to keep earlier work, and must otherwise ignore them. (2) The branches are reachable from the worker's worktree (same repository; no fetch needed). (3) Files changed there count toward the worker's Touches only as the entry's Touches allow; nothing outside them is brought in.
- Acceptance: In a fixture, a task held, set aside once, and run fresh gets a prompt naming `autowork/<task>-set-aside-1` with its commit and files; a fake worker that cherry-picks from it integrates; a task without earlier work gets no such section.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest discover -s pi-autowork/tests -p test_worker_tmp.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No automatic merging of set-aside work; no change to when work is set aside.
- Planner's call: high in Now: tasks whose plans say "keep the earlier candidate" loop on blockers until a person digs the branch out by hand.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-203-7a — A finished main check is recorded even when its process is a zombie the runner never reaped

- [x] TOOLSET-203-7a — A finished main check is recorded even when its process is a zombie the runner never reaped
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [main check](pi-autowork/pi_autowork/main_check.py) (`alive`), [coordinator](pi-autowork/pi_autowork/coordinator.py) (`check_main` starts the check with `Popen` and polls `alive(record['pid'])`; `reexec` drops the `Popen` object).
- Evidence (2026-10-18, this repository's runner): `main_check.json` said `running` on one revision for 31 minutes although its log already ended `Offline result: 4 test directories passed; 1 failed` and `main-check.exit` was written; `ps` showed the check's bash as `<defunct>`, a child of the runner. `alive()` is `os.kill(pid, 0)`, which succeeds on a zombie, and nothing reaps the child: the runner re-executed in place (reload or self-update) after starting it, so no `Popen` object waits on it any more. Main's status stays frozen (still red from the previous revision) until the runner restarts, and no next revision is checked.
- Touches: pi-autowork/pi_autowork/main_check.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/tests/test_main_check.py, tests/test_pi_autowork.py
- Scope: (1) `alive(pid)` is false for a zombie (`/proc/<pid>/stat` state `Z`) and for a pid that is not the recorded check (start time from `/proc/<pid>/stat` stored with it). (2) The coordinator reaps finished children it no longer holds a `Popen` for (`os.waitpid(pid, os.WNOHANG)` on the recorded check's pid, ignoring ECHILD), so no zombie stays. (3) A written `main-check.exit` is enough to finish the record, whatever `alive` says.
- Acceptance: In a fixture, a runner that re-executes while its main check runs records that check's result (green or red) once the check ends, within one cycle, and leaves no defunct child; `alive` is false for a zombie in a unit test.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_main_check.py; python3 -m unittest discover -s tests -p test_pi_autowork.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to what the main check runs or how it reports.
- Planner's call: first in Now: a frozen main check hides both a red and a green main, and every reload can cause it.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-199-2d — A task whose Ownership needs the owner or live authorization is never dispatched unattended

- [x] TOOLSET-199-2d — A task whose Ownership needs the owner or live authorization is never dispatched unattended
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [task contracts](skills/autowork/scripts/parallel_dispatch.py) (`contracts`), [plan](skills/autowork/scripts/parallel_plan.py) (runnability and the `outside` root), [questions](pi-autowork/pi_autowork/questions.py).
- Evidence (2026-10-17, this repository's runner): it logged `TOOLSET-123-a0: runs alone (no Touches proposed: NONE - Purely live migration of installed profiles, host plugins, cron wiring and runner sessions ...)` and queued it, although the entry's Ownership reads `Owner or a coordinator with live authorization` and its scope reinstalls the owner's live profiles, plugins and cron jobs. The owner session moved it to Needs decision by hand.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_questions.py, skills/docs-sync/SKILL.md, skills/autowork/scripts/parallel_status.py
- Touches widened by the runner from worker evidence: skills/autowork/scripts/parallel_status.py
- Touches widened by the owner session (2026-10-18): skills/autowork/scripts/parallel_status.py, which its worker asked for (`pending_tasks`/`_snapshot` must report owner-only tasks as waiting).
- Scope: (1) A task whose `Ownership:` names the owner as the only performer (`Owner`, `owner only`, `Owner or a coordinator with live authorization`) or that declares `Resources: live` without a recorded `Live authorization:` line is not runnable for an unattended runner: it waits as an `outside` root, never dispatched. (2) It becomes one owner question: run it yourself, record live authorization, or move it to Needs decision. (3) Docs Sync writes such tasks under Needs decision from the start.
- Acceptance: In fixtures, a Now task with `Ownership: Owner or a coordinator with live authorization` is listed as waiting (outside) and never dispatched, and BLOCKERS.md gets one question; the same task with `Live authorization: <record>` runs.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_plan.py; python3 -m unittest discover -s pi-autowork/tests -p test_questions.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to tasks with an ordinary coordinator ownership.
- Planner's call: high in Now: an unattended worker must never change the owner's live installation.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-206-0c — A held commit whose entry changed only in Touches is verified again, not set aside and redone

- [x] TOOLSET-206-0c — A held commit whose entry changed only in Touches is verified again, not set aside and redone
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [rescope](skills/autowork/scripts/parallel_state.py) (`rescopable`: once per slot, `rescoped`), [retry order](skills/autowork/scripts/parallel_integrate.py) (`retry_held`: rescope, then reoffer, ..., then `entry_changed` runs fresh and sets the work aside).
- Evidence (2026-10-18, this repository's runner): TOOLSET-189-96's commit was held for one file outside Touches, a test it adjusted while merging main; the runner had already widened its Touches once from evidence, so it asked the owner. The owner session answered by adding that file to the entry's Touches. Because the slot was already `rescoped`, `rescopable` refused, and `entry_changed` ran the task fresh, setting the commit aside as `autowork/TOOLSET-189-96-set-aside-1`: an hour of worker time redone for a one-line answer.
- Touches: skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py
- Scope: (1) When a held commit's entry changed and the only changed field is `Touches:` (or the `Touches widened ...` lines), and the commit's outside files are now covered, the commit is verified again (`RESCOPED`) regardless of an earlier automatic rescope; the once-per-slot limit applies only to the runner's own widening. (2) Any change to Scope, Acceptance, Checks or Dependencies keeps today's fresh run. (3) The journal records which fields changed.
- Acceptance: In a fixture, a commit held for scope after one automatic rescope, whose entry then gains the outside file in Touches and nothing else, is reverified and integrates with the same commit and attempt and no set-aside branch; an entry whose Acceptance changed runs fresh as today.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No more automatic widening than today.
- Planner's call: high in Now: the usual answer to a scope question is exactly this edit, and today it throws the work away.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-207-e4 — Engine status and dispatch parse the task contracts once per call, not once per pending task

- [x] TOOLSET-207-e4 — Engine status and dispatch parse the task contracts once per call, not once per pending task
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [status](skills/autowork/scripts/parallel_status.py) (`_snapshot`, `pending_tasks`), [selection](skills/autowork/scripts/task_execution.py) (`select`, `_contracts`, `archived_done`), [dispatch](skills/autowork/scripts/parallel_dispatch.py) (`contracts`).
- Evidence (2026-10-18, profiled on this repository's session worktree with 69 waiting tasks and a 250 KB TODO.md): one `--parallel-status --json` took 11.6 s. `pending_tasks` called `select` 51 times, each re-parsing every contract through `_contracts` (102 calls); 9.6 s were 10,077 `re.findall` calls and 3.1 s `archived_done`. Another runner with a 236 KB TODO.md took 4.9 s; small queues take under 0.5 s. The runner's `--apply --parallel` holds `dispatch.lock` for 30 to 40 s each cycle for the same reason, so the runner's own status reads fail with `[Errno 11] Resource temporarily unavailable` and `status.json` kept stale data: it said `blocked`, 0 running and `wait for <a task closed minutes earlier>` while three workers ran.
- Touches: skills/autowork/scripts/task_execution.py, skills/autowork/scripts/parallel_status.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_task_execution.py, skills/autowork/scripts/test_parallel_status.py, pi-autowork/pi_autowork/health.py, pi-autowork/tests/test_health.py
- Scope: (1) Within one engine process, parsed contracts, task bodies and the archive's done set are computed once per input file content (keyed by path and bytes digest) and reused by every `select`/`pending_tasks` call; results are unchanged. (2) `pending_tasks` evaluates eligibility in one pass over the parsed queue instead of a `select` per task. (3) When the runner's status read fails, `status.json` says so (`status unavailable since <time>: <reason>`) and keeps the last snapshot's age visible, instead of presenting old rows as current; the TUI shows that age.
- Acceptance: A fixture TODO with 80 open tasks and a 250 KB body gives the same status JSON as before, in under 1.5 s (measured in the test with a generous bound); dispatch on it holds `dispatch.lock` under 3 s; a status failure is shown with its age in `status.json` and the TUI.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_status.py; python3 -m unittest discover -s pi-autowork/tests -p test_health.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to selection rules or priorities.
- Planner's call: high in Now: the largest queues are the slowest and the most wrongly displayed, and every runner pays this every cycle.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-208-54 — A toolset update never mixes two releases in one running engine process

- [x] TOOLSET-208-54 — A toolset update never mixes two releases in one running engine process
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [self-update](pi-autowork/pi_autowork/release.py) and `update_toolset` in [coordinator](pi-autowork/pi_autowork/coordinator.py) (the shared Pi package checkout is updated in place with `git pull`), engine modules imported from `skills/autowork/scripts/` (some lazily, such as `execution.goals_module()`).
- Evidence (2026-10-18): two runners logged `The engine needs attention: no answer from the engine` in the same minute; both engine.err files show `AttributeError: module 'parallel_dispatch' has no attribute 'authorization_contract'` from `parallel_status.py`, with tracebacks quoting source lines that do not match their line numbers. The shared package checkout had just been updated in place while those engine processes were importing: one module came from the old release and one from the new. Both recovered a minute later after re-executing on the new release; a long review or worker that imports a module after such an update could fail the same way mid-run.
- Touches: pi-autowork/pi_autowork/release.py, pi-autowork/pi_autowork/coordinator.py, scripts/pi-autowork.sh, pi-autowork/tests/test_release.py, tests/test_pi_autowork.py, docs/cross-host.md
- Scope: (1) Runners and their engine, worker and review processes run from an immutable release directory (a detached checkout per commit, such as `<state root>/releases/<sha>`), selected once per process start through `PI_AUTOWORK_TOOLSET`; updating the package creates the next release directory and never changes one in use. (2) A runner moves to a new release only by re-executing (self-update or reload); children started earlier keep their release. (3) Release directories no process uses and older than the last two are removed.
- Acceptance: In a fixture, an engine process that imports one module, then has the package updated to a release where a second module changed its API, then imports the second module, still runs on one release and succeeds; a runner re-executes onto the new release; old release directories are pruned when unused.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_release.py; python3 -m unittest discover -s tests -p test_pi_autowork.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to how often the package is updated.
- Recurrence (2026-10-18 05:26): the next package update did it again on this repository's runner, `AttributeError: module 'task_execution' has no attribute 'task_bodies'` from `parallel_status.py` (a function the new release added), one cycle lost. It happens on every update to every runner whose engine is mid-start.
- Planner's call: moved to Now after the recurrence: every release now costs each runner a cycle, and a long review that imports late would lose its answer.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-209-55 — Workers run the runner suite sharded, and a worker timeout names the command it cut off

- [x] TOOLSET-209-55 — Workers run the runner suite sharded, and a worker timeout names the command it cut off
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [offline check](scripts/check.py) (`SPLIT`, `units`), task `Checks:` lines in this TODO.md, [worker timeout](skills/autowork/scripts/parallel_dispatch.py) (`worker timeout after N s`), worker sessions under the runner state's `sessions/`.
- Evidence (2026-10-18): three workers in three repositories ended `worker timeout after 5400 s` within 90 minutes; this repository's TOOLSET-204-f2 attempt 2 is one. Its session shows the work done (the full offline check passed, a reviewer subagent found nothing material) and its last tool call, at 12:57, a `bash` running `python3 -m unittest discover -s tests -p test_pi_autowork.py` among focused suites; it never returned before the kill at 13:12. That module runs serially (about 13 minutes on an idle host, longer under the fleet's load), although `scripts/check.py` already shards it 12 ways; 18 open tasks' `Checks:` lines name it that way. The hold reason says only `worker timeout after 5400 s`, so finding this took reading the session file.
- Touches: scripts/check.py, tests/test_check.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/worker.py
- Scope: (1) `scripts/check.py [PATH ...]` runs only the given test modules (or directories), with the same sharding, environment and summary; with no paths it runs everything as today. (2) Not for the worker: once (1) has landed, the planner rewrites this TODO.md's `Checks:` lines that run a `SPLIT` module serially to `python3 scripts/check.py <module>` (planning files are the coordinator's, and the command must exist first). (3) The worker prompt says to run the full gate once, at the end, and focused modules before. (4) A worker timeout's hold reason names the tool command running at the deadline and its age, read from the worker's session (first 120 characters), for example `worker timeout after 5400 s while running (14 min): python3 -m unittest discover ...`.
- Acceptance: `python3 scripts/check.py tests/test_pi_autowork.py` runs only that module, sharded, and passes in a fraction of the serial time (measured in the test against the shard count, not wall time); a fixture worker killed while a fake tool runs gives a hold reason naming that command.
- Checks: python3 -m unittest discover -s tests -p test_check.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py
- Answer (2026-10-18, owner session, to the worker's blocker): (2) is the planner's, after this lands; the worker does (1), (3) and (4) only.
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the worker timeout value.
- Planner's call: high in Now: a finished task that times out while re-running a serial suite costs an attempt and an hour, and three did so this morning.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-204-f2 — The main check reruns its failures alone before calling main red; tests that pass alone are reported as flaky

- [x] TOOLSET-204-f2 — The main check reruns its failures alone before calling main red; tests that pass alone are reported as flaky
- Status: done 2026-10-18 by the owner session (91a268d), from the second worker attempt that timed out after its own checks passed; python3 scripts/check.py passed (4 tests skipped by the resource gate at load 27).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17/18); [main check](pi-autowork/pi_autowork/main_check.py) (`failures`), [coordinator](pi-autowork/pi_autowork/coordinator.py) (`finish_main_check`, the MAIN maintainer trigger), [offline check](scripts/check.py).
- Evidence (2026-10-17/18, this repository's runner): three consecutive main checks were red, each on different tests: at 151718f `test_an_integration_that_cannot_get_the_lock_gives_its_slot_back` and `test_a_failing_validation_with_a_daemon_still_holds_and_old_daemon_holds_are_offered_again`; at 6c8f9a5 those passed and `test_a_waiting_runner_sees_tasks_committed_to_main_later` failed on a fixture `git commit`. Every one of them passed when run alone on the same revision. Each red sent the DOCS-MAINTAINER to fold "MAIN" failures into a task, and a worker then works on tests that are not broken.
- Touches: pi-autowork/pi_autowork/main_check.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_main_check.py, tests/test_pi_autowork.py
- Scope: (1) After a red main check, the runner reruns each failing test id alone (`python3 -m unittest <id>` in the same scratch checkout, its directory as for the full run), up to 10 ids, each with a 10-minute limit. (2) Ids that pass alone are recorded as `flaky` with the revision and do not make main red; main is red only for ids that fail alone too. (3) A test flaky on three different revisions becomes one MAIN trigger of its own kind (`flaky test`), so the maintainer plans hardening it, not repairing code; status shows `main green at <rev> (N flaky)`.
- Acceptance: In fixtures, a main check whose one failure passes alone records green with that id as flaky and no maintainer run; a failure that also fails alone is red as today; the same flaky id on three revisions gives one `flaky test` trigger.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_main_check.py; python3 -m unittest discover -s tests -p test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: TOOLSET-203-7a (the check's result must be recorded at all).
- Ownership: Toolset coordinator.
- Exclusions: No change to `scripts/check.py`'s own exit status; reviews keep their own judgment.
- Planner's call: right after TOOLSET-203-7a: a false red costs a maintainer run and a worker's attempt each time, and the fleet's load makes these flakes routine.
- Next action: Continue the preserved uncommitted implementation in .worktrees/autowork-TOOLSET-204-f2-r2 after the live TOOLSET-197-4f writer releases overlapping coordinator/maintainer files; verify no surviving owner first. The timeout is a technical continuation, not missing product intent or acceptance. Retain the five modified task files and cumulative attempt/budget history, inspect the last completed commands/results, and reconcile current main without overwriting work. Use the delivered TOOLSET-209-55 supported focused checker, python3 scripts/check.py pi-autowork/tests/test_main_check.py tests/test_pi_autowork.py, to validate the existing candidate before its original full offline gate and independent review. Do not restart discovery, rerun completed identical checks, start a second worker, extend timeouts blindly, reset budgets, weaken flaky/failure classification or change acceptance.
- Blocker reconciliation: Planning-only technical continuation saved after comparing the session question, current canonical contract, candidate and latest retained report. No new owner intent or operation authority is required; no check is waived and no worker/claim is released by this answer. Pick-up and completed delivery still require observation.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-210-53 — A runner keeps the disk from filling: a free-space gate, build caches pruned from idle worktrees, and a restart after it fails

- [x] TOOLSET-210-53 — A runner keeps the disk from filling: a free-space gate, build caches pruned from idle worktrees, and a restart after it fails
- Status: done 2026-10-18 by the owner session (2e771b7): (1) disk gate, (2) clean set-aside worktrees removed, (3) janitor prunes ignored build output of idle worktrees, (4) exit 70 on a crash and Restart=on-failure with RestartPreventExitStatus=1 3 4 (installed unit updated by hand).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [resource gate](skills/autowork/scripts/parallel_dispatch.py) (`resource_gate`: memory and load only), [set-aside](skills/autowork/scripts/parallel_integrate.py) (earlier work kept on `autowork/<task>-set-aside-N`, worktree kept too), [janitor](pi-autowork/pi_autowork/janitor.py) (only `/tmp` entries), [service unit](pi-autowork/pi_autowork/service.py) (`Restart=on-abnormal`).
- Evidence (2026-10-18 ~09:40): the root filesystem reached 100 % (464 KB free of 1.8 TB). One fleet repository's `.worktrees` held 85 GB in 119 worktrees, about 87 GB of it in Rust `target/` build directories, the largest in set-aside worktrees (17 GB, 15 GB, 9 GB) that no attempt would use again. Six of eight runners then exited on `No space left on device` and stayed dead: the unit restarts only on abnormal exits. The owner session freed 121 GB by removing those `target/` directories (with the owner's approval) and restarted the six runners.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/janitor.py, pi-autowork/pi_autowork/service.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/tests/test_janitor.py, tests/test_autowork_command.py, docs/cross-host.md
- Scope: (1) The resource gate also refuses a new worker when the repository's filesystem has less than `PI_AUTOWORK_MIN_FREE_DISK_GB` (default 20) free, with the reason `resource gate: <n> GB free on <mount>, need <m>`; status and the TUI show it. (2) Setting a task aside removes its worktree once its branch holds the work (commits, and uncommitted changes committed first, as today), so set-aside worktrees do not accumulate; the branch stays. (3) The janitor removes regenerable build output (`target/` with `CACHEDIR.TAG` or `.rustc_info.json`, `build/` and `.dart_tool/` under a worktree whose slot is held, released, closed or set aside, and untouched for 2 hours) in this runner's own `.worktrees` only, and logs what it freed; below the disk threshold it does so at once, oldest first. (4) The unit uses `Restart=on-failure` with `RestartSec=60`, so a runner that exits on an OS error comes back; deliberate exits (1 for failures the owner must see, 3 for another runner, 4 for attention) keep `RestartPreventExitStatus=` so they stay down as today.
- Acceptance: In fixtures: with free space reported below the threshold, no worker starts and status shows the disk reason; a set-aside leaves no worktree but its branch; the janitor removes a held slot's cargo `target/` older than its age limit and never one in a running slot or outside `.worktrees`; the installed unit has the restart settings and a fake runner exiting 2 is restarted while one exiting 3 is not.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py; python3 -m unittest discover -s pi-autowork/tests -p test_janitor.py; python3 -m unittest discover -s tests -p test_autowork_command.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No deletion outside the runner's own `.worktrees`; no source, commit or branch removed; no change to memory or load gates.
- Planner's call: first in Now: a full disk stopped the whole host's fleet and the owner's other work.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-213-45 — A Touches value that is not a list of paths is a contract error, not a silent outside-Touches hold

- [x] TOOLSET-213-45 — A Touches value that is not a list of paths is a contract error, not a silent outside-Touches hold
- Status: done 2026-10-18 by the owner session (4994477): (1) and (2), with (3) met by ending a Touches value at a list item, heading or blank line instead of changing the field labels (a general label change would have altered 49 lines in one fleet ledger); python3 scripts/check.py passed.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [field parsing](skills/docs-sync/scripts/goals.py) (`task_fields`: a label is `[A-Za-z][A-Za-z /-]*:`, so a line such as `- Touches widened by the owner session (2026-10-18): ...` is no field and runs into the one before), [paths](skills/autowork/scripts/parallel_plan.py) (`paths`), [contracts](skills/autowork/scripts/task_execution.py).
- Evidence (2026-10-18, this repository's runner): TOOLSET-189-96's entry had `- Touches: ..., pi-autowork/tests/test_status_cache.py` followed by the owner session's note `- Touches widened by the owner session (2026-10-18): pi-autowork/tests/test_status_cache.py, which the worker adjusted ...`. The parenthesised label is not a field, so `paths()` returned `pi-autowork/tests/test_status_cache.py\n- Touches widened by the owner session (2026-10-18): pi-autowork/tests/test_status_cache.py` and `which the worker adjusted ... branch` as two "paths"; the real file was outside, and the worker's attempt was held for `changed files violate Touches` although the entry listed it. The owner session fixed the label (1faf38a).
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py, skills/docs-sync/scripts/goals.py, skills/docs-sync/scripts/test_goals.py
- Scope: (1) `paths()` rejects an entry containing whitespace other than single spaces inside a quoted path, a newline, or a leading `- `, and a Touches value with such an entry makes the task not runnable with the reason `Touches is not a list of paths: <first bad entry, 80 chars>`, which the DOCS-MAINTAINER repairs. (2) `goals.py validate` reports the same for open tasks. (3) The field label pattern also accepts a parenthesised suffix (`Touches widened by X (date):`), so such notes are their own fields.
- Acceptance: In fixtures, the entry above is a contract error with that reason in status and no worker is dispatched; with the label fixed, or with (3), its paths parse to the listed files only; `validate` flags the broken entry.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_plan.py; python3 -m unittest discover -s skills/docs-sync/scripts -p test_goals.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to what Touches may contain beyond rejecting prose.
- Planner's call: high in Now: a mis-parsed Touches costs a worker's attempt and looks like the worker's fault.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-211-71 — A leftover task branch with nothing of its own never stops dispatch

- [x] TOOLSET-211-71 — A leftover task branch with nothing of its own never stops dispatch
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [worktree creation](skills/autowork/scripts/parallel_dispatch.py) (`create_worktree`, `created_by_autowork`: `... already exists and was not created by parallel Autowork; resolve it by hand`), [set-aside](skills/autowork/scripts/parallel_integrate.py) (renames a task's branch to `-set-aside-N`).
- Evidence (2026-10-18 10:16, one fleet runner, after the disk filled and six runners were restarted): every cycle logged `The engine needs attention: <repo>/.worktrees/autowork-<task> or branch autowork/<task> already exists and was not created by parallel Autowork; resolve it by hand` and nothing was dispatched for the whole repository. The branch `autowork/<task>` had no worktree, and its tip was a commit already in main (a questions commit): a name left behind when a set-aside was interrupted mid-way (its `-set-aside-6` was created at the moment of the restarts). It held nothing; the owner session deleted it with `git branch -d` on the owner's approval, and the runner continued.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_dispatch.py
- Scope: (1) When the task's branch exists without a worktree and its tip is an ancestor of the base (no commit of its own), the engine deletes it (`git branch -d`, which refuses anything unmerged) and creates the worktree as usual, journaling `stale_branch_removed`. (2) A branch with commits of its own is set aside to the next free `-set-aside-N` name (its work is kept) and the task proceeds; it is never deleted. (3) Only a leftover worktree directory with uncommitted changes, or a path that is not a worktree, stays a person's question, and then only that task waits: the rest of the queue dispatches.
- Acceptance: In fixtures: a leftover branch at a base commit is removed and the task dispatches; a leftover branch with a commit of its own becomes `-set-aside-N` with that commit and the task dispatches; a foreign directory at the worktree path holds only that task while another task dispatches in the same cycle.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No removal of anything with unique commits or uncommitted changes.
- Planner's call: high in Now: one stale name stopped a whole repository's dispatch until a person acted.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-215-a8 — One stuck command cannot use up a worker's attempt: tool commands get their own time limit

- [x] TOOLSET-215-a8 — One stuck command cannot use up a worker's attempt: tool commands get their own time limit
- Status: done 2026-10-18 by the owner session (4c18c7c); python3 scripts/check.py passed; the stopped command is logged in the worker log. (Its entry was dropped by an unrelated commit and restored here.)
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [worker](pi-autowork/pi_autowork/worker.py) (the Pi worker process and its timeout), [dispatch](skills/autowork/scripts/parallel_dispatch.py) (worker prompt; the timeout reason now names the running command, TOOLSET-209-55).
- Evidence (2026-10-18 11:26, one fleet runner): `NUM-WALL-01: failed — worker timeout after 5400 s while running (89 min): CHROME_EXECUTABLE=/usr/bin/chromium ... flutter test --no-pub --platform chrome ...`. One browser test command hung for 89 of the attempt's 90 minutes; the worker could neither see the hang nor try anything else, and the attempt was spent. Earlier that morning two other workers timed out the same way inside long test runs.
- Touches: pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, skills/autowork/scripts/parallel_dispatch.py, docs/cross-host.md
- Scope: (1) While a worker runs, the runner watches its process tree: a tool command (a descendant of the worker's Pi process other than Pi itself) running longer than `PI_AUTOWORK_COMMAND_TIMEOUT` seconds (default 1800, capped below the worker timeout) gets SIGTERM, then SIGKILL after 30 s, and the event is logged once with the command's first 120 characters. Pi reports the failed tool call to the model, so the worker continues the same attempt and can retry differently. (2) The worker prompt says commands longer than that limit are stopped and suggests `timeout` and narrower test selection for browser or device suites. (3) Build daemons the review already tolerates (Gradle, Kotlin, Flutter) are not counted as stuck commands while idle.
- Acceptance: In a fixture, a fake worker whose tool command sleeps past a 3-second limit has that command killed, the worker then finishes and reports normally on the same attempt, and the runner log names the killed command once.
- Checks: python3 scripts/check.py pi-autowork/tests/test_worker_tmp.py; python3 scripts/check.py tests/test_pi_autowork.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the worker timeout itself or to the review's limits.
- Planner's call: high in Now: a hung command costs a whole attempt and 90 minutes; three did today.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-161-17 — Touches schedules work but never holds it: integrate by merge, rebase on conflict

- [x] TOOLSET-161-17 — Touches schedules work but never holds it: integrate by merge, rebase on conflict
- Status: done 2026-10-18 by the owner session (4ec89d8), on the owner's direction: admission, integration, removal and recovery as scoped; touches_inference.py keeps only its module helpers in use; python3 scripts/check.py passed.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17): "touches mechanic causes many bugs"; [admission](skills/autowork/scripts/parallel_plan.py), [integration scope and ownership checks](skills/autowork/scripts/parallel_integrate.py) (`verify_scope`), [slot state](skills/autowork/scripts/parallel_state.py), [Touches inference](pi-autowork/pi_autowork/touches_inference.py), [coordinator](pi-autowork/pi_autowork/coordinator.py), [question block](pi-autowork/pi_autowork/questions.py).
- Evidence (2026-10-17 runner history for this repository): all but one recent hold are Touches holds. TOOLSET-099-87, TOOLSET-140-f4, TOOLSET-148-88 and TOOLSET-157-cd each had a worker that needed a file outside its declared Touches; TOOLSET-155-e2 needed 20; TOOLSET-147-54 was held `overlap` for files another slot owned and blocked 48 tasks. Five live tasks were inferred `NONE` and could only run alone. Since 2026-10-14, 26 commits on main patch the mechanism (inference, `NONE` retries, worker-requested widening, reverify after widening, typed hold causes, trailing-period tolerance, per-task invalid holds), and TOOLSET-152-d4 and TOOLSET-157-cd were still adding more. The cause is structural: Touches asks the planner to predict a task's files before the code is read, then integration treats that prediction as a hard boundary, so a one-file miss costs a hold, an owner question or a deadlock.
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/task_execution.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/test_parallel_state.py, skills/autowork/references/parallel-workers.md, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/touches_inference.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_touches_inference.py, pi-autowork/tests/test_questions.py, tests/test_pi_autowork.py, scripts/pi_autowork_touches.py, docs/cross-host.md, CHANGELOG.md
- Scope: Optimistic concurrency, as a merge queue does it. (1) Admission: Touches (declared or inferred) is only a hint for picking tasks that are likely independent. Missing, invalid or `NONE` Touches never holds a task; it ranks lower for parallel slots. The `SERIAL_PATHS` and `live`/`exclusive` rules stay as they are (TOOLSET-160-df). (2) Integration: remove the `outside Touches` and other-slot ownership checks from `verify_scope`; keep the protected-file rules (TODO.md, goals.json, BLOCKERS.md, serial files without serial admission). Finished candidates integrate one at a time into the session branch in TODO priority order. A clean merge runs the task's checks on the merged tree and lands. A textual conflict, or checks that fail only after the merge, returns the same candidate to its worker to merge current main and reverify, with the existing Pi merge resolver for the conflict: no fresh attempt and no owner question. A second failure on an unchanged main holds with the real reason (`conflict with <task>: <files>` or the failing check). (3) Held slots own nothing, so holds cannot deadlock admission. (4) Clean cut, no compatibility path: delete the widening, widen-and-reverify, `needs_touches` blocker parsing, `overlap` and `outside` hold causes and their questions, ownership release and the `NONE` retry machinery. Shrink Touches inference to a single cheap pass, or remove it if declared Touches plus file-history overlap rank as well in fixtures. (5) Recover what is held today: on upgrade, every slot held only for an `outside`, `overlap` or `needs_touches` reason is requeued as a finished candidate for (2), keeping its branch and report.
- Acceptance: In fixtures, a candidate that changes a file outside its Touches integrates when it merges cleanly and its checks pass. Two candidates editing the same file integrate in priority order; the second merges main, is reverified once and lands, with no new implementation run and no question. A real conflict the resolver cannot settle holds once with the files named. A task with no Touches runs beside other work. Held slots never block admission. Existing `outside`/`overlap`/`needs_touches` holds requeue and integrate without reimplementation. No model call happens unless a merge conflict needs the resolver. The removed code paths and their tests are gone, and docs describe Touches as a scheduling hint.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p 'test_parallel_*.py'; python3 -m unittest discover -s pi-autowork/tests; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator. Reconcile the owner session's in-progress TOOLSET-157-cd output in the same engine files first; the same applies to TOOLSET-152-d4 (worker-named widening), which the owner session is implementing in these files. Let both land; this task then deletes what they add here that (4) removes, as superseded, not reverted by hand.
- Exclusions: No change to the worker cap, the serial and exclusive rules, the protected-file rules, required checks or review, and no force integration of unverified work.
- Evidence (2026-10-17 11:25 monitor pass, after the 5b240c1 restart): with serial files no longer exclusive, the largest remaining parallelism loss is wide declared Touches. One runner's running task declared 12 whole directories (app, tests, integration tests, docs) and held 42 of 51 waiting tasks with `overlapping paths with` it; most could not have touched the same files. Under (1) they would be admitted and integrate by merge.
- Evidence (2026-10-17 12:41 monitor pass, `waiting_groups` in this repository's status): after serial files stopped being exclusive, the largest admission loss left here is `8 wait behind <task>, which runs alone`. That task is a live follow-up with no Touches; as an exclusive task waiting on running work it drains the pool, so eight lower-priority tasks idle for a task a worker may not even complete offline. Under (1) it ranks lower and nothing waits behind it.
- Owner direction (2026-10-18): "the touches mechanic is too limiting our agents ... if need to reach farther ... allow worker to do it right there? the simpler the better. it's slow progress too." Moved to the top of Now.
- Planner's call (earlier): second in Now, behind TOOLSET-165-f7 (owner, 2026-10-17). Holds from Touches predictions are the main reason runners go idle; making integration decide by merge and checks removes the class instead of patching each shape.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-180-72 — A candidate lands only if the merged tree's full suite has no new failures

- [x] TOOLSET-180-72 — A candidate lands only if the merged tree's full suite has no new failures
- Status: done 2026-10-18 by the owner session (eb51352): (1)-(4) and the folded main-check fallback; the rejection is a validation hold whose reason names the new failures (no separate `regression` cause); python3 scripts/check.py passed.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: feedback from an interactive session in one fleet repository (2026-10-17), pasted by the owner with "please plan these as tasks, folding into existing ones where they overlap" (item 3); [review and validation](pi-autowork/pi_autowork/worker.py) (`verify`, `PI_AUTOWORK_VALIDATE`), [questions](pi-autowork/pi_autowork/questions.py).
- Evidence (one fleet repository, 2026-10-17): a reviewer-approved commit landed while breaking 44 tests. A screen read a connection provider during build and added a listener that never closed; a later fix repaired it. The task's checks covered only its own feature, the reviewer ran those, and the repository had no `PI_AUTOWORK_VALIDATE`, so nothing ran the whole suite on the merged tree. Second instance (another fleet repository, 2026-10-17): a landing changed a shared struct without updating four test fixtures in a file outside its Touches; the test build no longer compiled, and the next two workers each stopped with a blocker naming those fixtures instead of doing their tasks. That repository has no `PI_AUTOWORK_MAIN_CHECK` either, so TOOLSET-176-98's main check never ran.
- Touches: pi-autowork/pi_autowork/worker.py, pi-autowork/pi_autowork/main_check.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_worker_tmp.py, pi-autowork/tests/test_questions.py, tests/test_pi_autowork.py, docs/cross-host.md, AGENTS.md
- Scope: (1) The full check comes from `PI_AUTOWORK_VALIDATE`, else from a `Full check:` line in the repository's AGENTS.md (documented, and added to this repository's AGENTS.md). Without either, the runner asks one owner question per repository and status shows `no full-suite gate`. (2) Verification runs it on the merged tree and compares it with the base revision's result, run once per base revision and cached: a pass that becomes a failure, or failing test names (from unittest, pytest, go test, flutter test and jest output) not failing on the base, reject the candidate. Failures the base already has do not block. (3) A rejection is a `regression` hold naming the newly failing tests, and the retry's prompt includes them. (4) `PI_AUTOWORK_VALIDATE_TIMEOUT` (default 3600 seconds) bounds each run; a timeout is a validation failure, not a pass.
  (Folded 2026-10-17) The main check (`main_check.py`, TOOLSET-176-98) uses the same resolved full check when `PI_AUTOWORK_MAIN_CHECK` is unset, so a red main gets its repair task in every repository that declares a full check either way.
- Acceptance: In fixtures, a candidate that breaks a test outside its own checks is rejected with that test named, and its retry prompt quotes it. A candidate in a repository whose base already fails one test lands when it adds no new failure. The base result is computed once per base revision. A repository with neither setting gets one question and a status note, not a hold on every task.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p 'test_*.py'; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the reviewer's prompt or to how a task's own checks are chosen; no full suite in the worker's own run.
- Planner's call: third in Now since 2026-10-17 (two fleet repositories lost tasks to a landing that broke other tests). compare against the base instead of requiring a green suite, so a repository with a known failing test still lands work; parse test names where the common runners print them and fall back to the exit status otherwise.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-218-d0 — A worker whose task closes on main stops at once, and a task closed on main never starts

- [x] TOOLSET-218-d0 — A worker whose task closes on main stops at once, and a task closed on main never starts
- Status: done 2026-10-18 by the owner session: (1)-(4). The coordinator passes `--base-ref` on dispatch and integration; `retire_closed` stops a live worker of a task closed on either side and sets its slot aside (cause `closed_on_base`, event `closed_on_base`), or on a later cycle while a review holds the integration lock, the stopped slot occupying nothing meanwhile; integration sets a reported commit of such a task aside instead of reviewing it. Closed tasks are also left out of the waiting list. Checks: four dispatch fixtures and one runner journey (`test_a_worker_whose_task_the_owner_closes_on_main_is_stopped`); python3 scripts/check.py passed (5 directories, four resource-gate skips at load 45).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [retired tasks](skills/autowork/scripts/parallel_dispatch.py) (`retired(repo)` reads only the session worktree's goals.json, TODO.md and archive; `dispatch_locked` frees only held or interrupted slots of retired tasks), [session merge](pi-autowork/pi_autowork/coordinator.py) (`merge_main` brings the base into the session only when the session lands, and not while a review runs).
- Evidence (2026-10-18 12:47, this repository's runner): TOOLSET-161-17 and TOOLSET-215-a8 were shipped and archived on main by the owner session at 12:03 and 11:48, yet both still had a live worker 45 minutes later, and TOOLSET-180-72 (closed on main at 12:44) was pending dispatch. The session branch had not taken main since 12:00: its landing was refused because the main checkout had another session's uncommitted TODO.md edits, and while it cannot land it never merges the base either. Two of eight slots spent tokens re-implementing finished work, and their candidates would land as conflicting duplicates.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/owner_cycle.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) `retired()` also counts tasks closed on the base branch: read `goals.json`, `TODO.md` and the archive at the base ref (`git show <base>:<file>`; the coordinator runs the engine on the session worktree, so it passes `--base` through owner_cycle.py), so the session's lag no longer matters. A task closed on either side is retired. (2) Each dispatch cycle, a dispatched or running slot whose task is retired is stopped (`stop(worker, worktree)`), its worktree set aside as any closed task's is (commits kept on a `-set-aside-N` branch, nothing deleted), and its slot closed with cause `closed_on_base`; the log says `<task>: closed on <base>; worker stopped`. (3) A pending or restartable task that is retired never dispatches. (4) An implemented candidate of a retired task is not integrated; it is set aside the same way.
- Acceptance: In fixtures: a task checked off only on the base ref while its worker runs is stopped within one cycle, its slot closes with `closed_on_base`, its commits survive on a set-aside branch, and the freed slot dispatches the next task in the same cycle; a pending task closed only on the base never dispatches; a task open on both sides is unaffected; an unreadable base ref (no such branch) falls back to the session ledger alone.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest tests/test_pi_autowork.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to when the session merges or lands. No reopening, rewriting or deleting of task entries. Nothing with commits of its own is deleted.
- Planner's call: first in Now. It wastes worker slots on every repository where the owner closes tasks on main while the session lags, which happens whenever the main checkout is dirty or a review is long. Reading the base ref is cheaper and safer than merging the base into a session under running workers.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-221-8e — Planning a dispatch takes seconds, not minutes: path overlap is matched once, cheaply

- [x] TOOLSET-221-8e — Planning a dispatch takes seconds, not minutes: path overlap is matched once, cheaply
- Status: done 2026-10-18 by the owner session: (1)-(4). `_intersects` is cached and decides literal sides directly (the product search is now `_search`, run only for two real globs); `plan` memoizes solo, resources, hints and the dependency closure per task, and ranks against a set. On this repository's live session ledger, `admit` went from over 6 minutes to 0.07 s; on 12 and 20 of its real tasks the old planner took 101 s and 250 s, the new one under 0.01 s, with identical dispatch and waiting output. Checks: an agreement test over 3000 random literal/directory/glob pairs and a 150-task timing test in test_parallel_plan.py; python3 scripts/check.py passed (5 directories, four resource-gate skips at load 29).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [admission planning](skills/autowork/scripts/parallel_plan.py) (`plan`: the likely-independent ranking calls `_shared(_hint(task), chosen)` with `chosen` growing by every dispatched task's Touches; `conflict` calls `serial()`/`exclusive()`, each re-running `_solo` and its `_shared(..., SERIAL_PATHS)`, for every pair; `depends` walks the dependency graph again for every pair); `_intersects` (a glob-intersection search that tries every boundary character with `fnmatchcase` at every state pair).
- Evidence (2026-10-18 13:16-13:23, this repository's runner, 58 runnable tasks): one `--apply` engine call ran for over 6 minutes at a full core with no child process. Rerunning `parallel_dispatch.admit` on the same ledger with stack sampling did not finish within 60 s. Every sample was in `_shared` → `_intersects` → `fnmatchcase`: 94 from `plan`'s ranking loop, 26 from `_solo`. Reading the ledger (`contracts`, `retired`, `pending_tasks`) took under 1 s together. The ranking arrived with TOOLSET-161-17 (4ec89d8), which also stopped holding tasks on path overlap, so far more tasks now reach it in one pass. Each runner's loop waits on this call, so dispatch, integration and questions all slowed, and the core it burns counts toward the host load that gates every other runner (see TOOLSET-222-e1).
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py
- Scope: (1) `_intersects` is cached (`functools.lru_cache` on the two pattern strings) and short-cuts the common cases before the search: two literal paths compare equal or by directory prefix (`a/` covers `a/b`), and a literal path against a pattern is one `fnmatchcase`. The search runs only when both sides contain glob metacharacters. (2) In `plan`, each task's hint, resources and solo/serial/exclusive answers are computed once per call (a dict keyed by task ID), not per pair. (3) The dependency closure is computed once per call, so `depends(a, b)` is a set lookup. (4) The ranking keeps `chosen` as a set of distinct patterns. Results stay identical: same dispatch order, same waiting reasons and `blocked_by`.
- Acceptance: In fixtures: a generated queue of 150 tasks with 10 Touches paths each (some directories, some globs, some serial paths) and 8 running tasks plans in under 2 s on an unloaded machine. Assert that it finishes within 10 s, so a busy host cannot flake it. Every existing test_parallel_plan.py and test_parallel_dispatch.py case passes unchanged. A property check over random literal/glob pairs shows the short-cuts agree with the full `_intersects` search.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_plan.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to which tasks dispatch or wait, or to the order. No new dependency.
- Planner's call: first in Now. The minutes-long planning slows every runner with a deep queue, and its CPU feeds the load gate that starves the rest. Caching and literal short-cuts keep exact semantics, unlike dropping the glob search.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-233-ba — The session takes main between reviews, so planning and fixes on main reach dispatch and validation within one review

- [x] TOOLSET-233-ba — The session takes main between reviews, so planning and fixes on main reach dispatch and validation within one review
- Status: done 2026-10-18 by the owner session: (1)-(3). `follow_base` no longer waits for an empty pipeline: it merges main into the session whenever no review runs, under the engine's writer.lock (non-blocking), and also before each integration starts; beside a running review it takes only commits that change planning files or docs/. Integration lands a validated merge onto a session moved only by such commits with a second merge and no second validation (`remerge_planning`, event `integration_head_moved_planning_only`); any other move validates again as before. A conflict with work in flight is left for the landing's resolver. Checks: two test_parallel_integrate.py cases (the planning-only case fails on the old engine), one runner journey (`test_the_session_takes_main_while_a_worker_runs`); two landing-conflict journeys now move main during the review (new fake `verify:move_main`), since a move while the worker runs is now taken at once and surfaces as an integration conflict; python3 scripts/check.py passed (5 directories, no skips), and the affected suites again after rebasing on 10d09c7.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [session merge](pi-autowork/pi_autowork/coordinator.py) (`merge_main` merges the base into the session only on its way to landing, and returns at once while `session_busy`; `land_beside_review` only fast-forwards; the integration loop starts the next review right after it collects one); [integration](skills/autowork/scripts/parallel_integrate.py) (a session that moved during validation is validated again, `integration_head_moved`); TOOLSET-218-d0 in [the archive](TODO.archive.md) (closures alone are read from the base).
- Evidence (2026-10-18 15:04, this repository's runner): the session branch last took main at 12:00 and was 26 commits behind it, including four toolset fixes. At 12:11 the owner changed TOOLSET-172-92 from `Resources: exclusive` to `install-transaction` on main. The session's copy still said `exclusive` three hours later, so every lower task logged `priority waits for TOOLSET-172-92 (draining, waited 895m)` and the runner had 0 of 8 workers. Its reviews ran back to back with no idle gap, and landing (the only path that merges the base in) never found one. Every candidate reviewed meanwhile was validated against a base without main's fixes.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py
- Scope: (1) Before starting each integration, and once per cycle when none runs, the coordinator merges the base into the session when the base has commits the session lacks. It runs only when no review is running and the merge is clean; a conflict goes to the existing Pi resolver path at the next landing, and the log says `took <n> commit(s) from <base> into the session` once per base revision. (2) While a review runs, base commits that change only planning files (`PLANNING_FILES` in parallel_integrate.py, plus `docs/`) are merged into the session at once. When the review ends with the session moved only by such commits, integration re-merges the candidate onto the new session head and fast-forwards without validating again, if the re-merge is clean and leaves every non-planning path identical to the validated tree. Otherwise the existing moved path applies. (3) Dispatch admission reads the session ledger after (1) or (2), so a priority, Resources or Touches change on main applies within one review.
- Acceptance: In fixtures: a commit to main between two reviews is in the session before the second review starts, and the second candidate's validation sees it; a planning-only main commit during a review is in the session before the review ends, and that review's candidate integrates without a second validation run; a code commit to main during a review still triggers revalidation; a conflicting base commit leaves the session unchanged and is logged once.
- Checks: python3 -m unittest tests/test_pi_autowork.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator. It overlaps TOOLSET-179-cf's local-plan refinement (a safe base merge with no outgoing session commits); whichever lands second reuses this merge step. TOOLSET-230-bf (off-tree integration) keeps it if it lands first.
- Planner's call: first in Now. A stale session hid every owner planning change and every toolset fix for three hours and left the runner idle; merging between reviews costs one clean merge and no extra review. The planning-only re-merge skips the revalidation that would otherwise make merging during a review a loss.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-236-4d — A pending reload or toolset update applies when the current review ends: no new review or Pi job starts first

- [x] TOOLSET-236-4d — A pending reload or toolset update applies when the current review ends: no new review or Pi job starts first
- Status: done 2026-10-18 by the owner session: (1)-(3). `reexec_due` names an asked-for reload or a package past the running release; while one is due the integration loop starts no next review and re-executes instead, right after the finished review's answer is handled (Pi jobs run inside the cycle, so none starts across that point). `reexec` logs `Reload pending: waiting for <what> to end` once. `runner.json` records the running `toolset_rev`, and `autowork status` adds `runs <rev> and moves to <rev> at its next reload` when they differ; the TUI is unchanged. Checks: `test_a_reload_applies_between_back_to_back_reviews` (fails on the old coordinator, which reloaded only after every queued review), the existing reload journeys; python3 scripts/check.py passed (5 directories, four resource-gate skips).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [coordinator](pi-autowork/pi_autowork/coordinator.py) (`restart_if_updated` runs at the start of a cycle; `reexec` returns while `self.integration or self.child`; the integration loop collects a finished review and starts the next one in the same cycle; `autowork restart` says `it reloads once its running review or Pi job ends`).
- Evidence (2026-10-18 16:04, this repository's runner): the runner has not re-executed since 13:33 (same PID, `since 13:33`, one `Reloading:` line), though `autowork restart` sent it five SIGHUPs since then, each answered `asked to reload, but it has not within 150s; it reloads once its running review or Pi job ends`. Its reviews run back to back: each cycle begins with a review running, so `reexec` refuses; later in the cycle the loop collects that review and starts the next. So it kept running the 13:33 release, without the fast planner (TOOLSET-221-8e), the integration fix (TOOLSET-223-8e) or the session sync (TOOLSET-233-ba), while `autowork status` showed the new release as its toolset. An automatic toolset update has the same gap.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/tests/test_fleet_view.py
- Scope: (1) While a reload is pending (`self.reload`), or a newer prepared release is waiting, the coordinator starts no new review, maintainer, merge-resolver, provisioning or other Pi job. Workers already running keep running and dispatch continues. When the running review or job ends, its answer is read and the runner re-executes at the end of that same cycle, before starting anything else. (2) The log says `Reload pending: waiting for the review of <task> to end` once. (3) `autowork status` and the TUI show the release the process runs (from `runner.json`) and, when it differs, the release it will move to. They don't show the configured release alone.
- Acceptance: In a runner fixture with two reviews queued (`slow_review`), a SIGHUP during the first review gives `Reloading:` after the first integrates and before the second starts verifying, and the second integrates under the new process; a package update during a review does the same; with no review running, a reload applies at the next cycle as today; status shows the running and pending releases while the reload waits.
- Checks: python3 -m unittest tests/test_pi_autowork.py; python3 -m unittest discover -s pi-autowork/tests -p test_fleet_view.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No interruption of a running review or Pi job. Running workers stay attached as reloads keep them today.
- Planner's call: first in Now. Every toolset fix reaches the runners through a reload, and the runner with the most work never took one, so the fleet could not heal itself where it mattered most. Deferring one review start costs a few seconds.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-237-35 — A check that crashes before reporting test results is a broken check: never a red main with placeholder failures, never a pass

- [x] TOOLSET-237-35 — A check that crashes before reporting test results is a broken check: never a red main with placeholder failures, never a pass
- Status: done 2026-10-18 by the owner session: (1)-(3). `main_check.crash_line` names a crash; failure lists no longer get placeholder strings. A main check that exits non-zero naming no test, or is cut short with only flaky tests named, is checked once more (`recheck` with `crashed`); a second crash records `broken` with `crash`, shown as `main check broken at <rev>: <line>`, and gives the maintainer a `check broken` trigger whose prompt forbids repair tasks for test names. The full-suite gate reruns a crashed merged run once; still crashed, it blames the candidate when the base passes and otherwise writes the review environment marker (the TOOLSET-173-94 provisioning and reverify path) and holds; it never passes for want of evidence. Checks: a main-check unit case on the logged crash text, two runner journeys (crash on base and candidate holds, a fails-on-old-code case; a single crash reruns and lands); python3 scripts/check.py: 4 directories passed, one known flaky failure (`test_release` late-imports pruning race, already in the runner's flaky history, passing 3 of 4 reruns here and untouched by this change).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [main check](pi-autowork/pi_autowork/coordinator.py) (`failures = main_check.failures(...) or [f'the check exited {code}']`, and `the check exited {code} without a complete test result` appended when incomplete); [full-suite gate](pi-autowork/pi_autowork/worker.py) (`full_suite_gate`: `if base['code'] != 0 and not base['failures']: return True, ''`, "the base fails the same unnamed way"); [maintainer triggers](pi-autowork/pi_autowork/maintainer.py) (`MAIN (main red)` adds a repair task naming the failing tests).
- Evidence (2026-10-18 16:34, one fleet runner): main was recorded red at a new revision with `failures: ['the check exited 1', 'the check exited 1 without a complete test result']`. The log shows analysis passing (`No issues found!`) and then the test tool crashing: `Oops; flutter has exited unexpectedly: "Bad state: No element"`, with a crash report and no test result. No test failed. The two placeholder strings sit in the failure list as if they were test IDs, and the maintainer's MAIN rule turns such a list into a repair task. Separately, the TOOLSET-180-72 gate passes a candidate when the merged tree and the base both exit non-zero without named failures. While a tool crashes on every run, candidates land with no test evidence at all.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/main_check.py, pi-autowork/tests/test_main_check.py, pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, tests/test_pi_autowork.py
- Scope: (1) A check that exits non-zero with no parsed test failure, or one cut short (`incomplete`), is a crashed check. `main_check.crash_line(log)` names it: the first line matching an unexpected exit, an uncaught exception, a signal, `Bad state` or `Segmentation fault`, else the last non-blank line. Failure lists never hold placeholder strings. (2) A crashed main check runs once more. If it crashes again, main's state is `broken` (not `red`) with `crash` set to the crash line. Status shows `main check broken: <crash line>`. The maintainer gets a `check broken` trigger, which restates or provisions (the TOOLSET-173-94 environment path) instead of adding a repair task. (3) In the full-suite gate, a crashed merged run is run once more. If it still crashes, the candidate is held with cause `environment` and the crash line (the existing provisioning and reverify path). It is never passed because the base crashes too. A merged run that names failures keeps today's base comparison.
- Acceptance: In fixtures: a main-check log that ends with a tool crash and no test results yields `broken` with that crash line after one rerun, no placeholder in `failures`, and a `check broken` maintainer trigger, not a repair task; a crash that passes on the rerun yields green; a merged-tree gate whose base and candidate both crash holds the candidate as `environment` with the crash line; named failures still compare against the base as before.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_main_check.py; python3 -m unittest discover -s pi-autowork/tests -p test_worker_tmp.py; python3 -m unittest discover -s pi-autowork/tests -p test_maintainer.py; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to how named failures, flaky reruns or the base comparison work. No automatic upgrade of a crashing tool outside `$AUTOWORK_CACHE`.
- Planner's call: Now, right after the two integration-hold tasks. The gate rule I added in TOOLSET-180-72 lets untested candidates land during a tool crash, and the main-check rule sends the maintainer after test names that do not exist. "Could not check" belongs to the environment path, as in reviews.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-227-a8 — A candidate's full check runs once, by the runner, and the worker and reviewer reuse it

- [x] TOOLSET-227-a8 — A candidate's full check runs once, by the runner, and the worker and reviewer reuse it
- Status: done 2026-10-18 by the owner session: (1)-(4). The runner passes its full check to the engine as `AUTOWORK_RUNNER_FULL_CHECK`; with it the worker prompt says not to run the full check and to leave it out of the report's `checks` (any non-pass entry holds a task); without it (other hosts) the old once-at-the-end rule stays. `full_suite_gate` caches its verdict per merged tree id and command (`full-check/tree-<tree>.json`; crashes are never cached); `gate_note` gives the reviewer the command, outcome and log path and says not to rerun it. The TODO work center says a full-check Checks entry is satisfied by the runner's run. Checks: a gate-runs-once and review-note case in test_worker_tmp.py, a prompt case in test_parallel_dispatch.py, a dispatched-prompt assertion in a runner journey; python3 scripts/check.py passed (5 directories, four resource-gate skips).
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [full-suite gate](pi-autowork/pi_autowork/worker.py) (`full_suite_gate`, `base_result`, `run_suite`, `verify`, the `REVIEW` prompt), [main check command](pi-autowork/pi_autowork/main_check.py) (`full_check`), [worker prompt](skills/autowork/scripts/parallel_dispatch.py) (`prompt`).
- Evidence (2026-10-18, this repository, the last 48 hours: worker runs took a median 33 minutes (p75 51); in two logged attempts test commands took 38 of 44 and 26 of 32 minutes; a full `scripts/check.py` took 7 to 10 minutes at a host load average of 24 to 27. One candidate's full check ran 4 to 5 times: 2 or 3 times by its worker, once by the full-suite gate on the merged tree, and again by the model reviewer, which polled its own background run every 90 s. 15 of 26 integrations ended held and 15 of 25 check receipts failed or timed out, many on the environment.)
- Touches: pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, tests/test_pi_autowork.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/shared/TODO-WORKCENTER.md, CHANGELOG.md
- Scope: (1) The worker prompt says the runner runs the repository's full check on the merged tree before review: the worker runs its task's focused checks (every `Checks:` command except the full check) and does not run the full check itself; it may run named tests from it. (2) The gate's result is cached by the merged tree's id and the check command, so a re-review of the same tree (a changed reviewer, a requeue) reuses it instead of running again, as `base_result` already does for the base. (3) The review prompt gives the reviewer the gate's outcome and log path and says not to rerun the full check; it reruns only tests it needs to examine. (4) The TODO work center says a task's `Checks:` line for the full check is satisfied by the runner's gate, not by the worker.
- Acceptance: In fixtures, a review of a tree whose gate result is cached runs no full check; a changed tree runs it once; the worker prompt names the focused checks and states the full check is the runner's; the review prompt carries the gate's outcome and log path. Acceptance of a candidate still requires the gate: a failing merged-tree check still rejects it.
- Checks: python3 scripts/check.py pi-autowork/tests/test_worker_tmp.py tests/test_pi_autowork.py skills/autowork/scripts/test_parallel_dispatch.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No weaker gate: the runner's full check on the merged tree stays required; no reuse of a worker-reported result (a receipt the runner did not produce proves nothing).
- Priority (2026-10-18 17:34): moved up to fourth in Now. On one runner 13 verified candidates waited for reviews that take 17-65 minutes each, one at a time, with the full suite run twice per review.
- Planner's call: the runner's gate is the one trusted full run, so it is the one kept; the worker's and the reviewer's repeat runs add time and host load, not assurance. Expected effect: two to four fewer full checks per candidate, about 15 to 30 minutes at today's load.


<!-- archived from TODO.md -->

Source section: Now

Disposition: Superseded; not completed
Successors: TOOLSET-239-d4
Reason: TOOLSET-239-d4 puts the worker's $TMPDIR itself on disk, which makes a separate disk folder unnecessary (owner, 2026-10-18)
Original task and unchecked acceptance retained below.

### TOOLSET-212-0d — Each worker gets a disk-backed scratch folder that is removed when its task retires

- [ ] TOOLSET-212-0d — Each worker gets a disk-backed scratch folder that is removed when its task retires
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [worker launch and temp allocation](skills/autowork/scripts/parallel_dispatch.py) (`worker_tmpdir`, `launch`, `cleanup_tmpdir`, `drop_attempt_tmp`, `sweep_retired_tmp`, `prompt`), [reviewer temp](pi-autowork/pi_autowork/worker.py) (`verify`, `worker_tmp`, `PROVISIONED`).
- Evidence (2026-10-18, this host): the disk filled to 320 KB free and Hermes stopped saving conversations. A worker's `$TMPDIR` is a short path under `$XDG_RUNTIME_DIR`, a 6.3 GB RAM-backed tmpfs shared by every worker, so workers improvise disk space for builds: one symlinked `$TMPDIR/disk` into its worktree's `build/` folder, another made `/var/tmp/aw165.*` for a full check and left it after its task closed. Nothing the pipeline owns removes such folders. 1f05447 now removes each attempt's `$TMPDIR` at retirement, but large output still has no supported place.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, CHANGELOG.md
- Scope: (1) `launch` creates a per-task disk folder at `<git common dir>/autowork-execution/slot-data/<task>/disk` (mode 0700, refused if it is a link or has a foreign owner, like `_private_tmp_dir`) and exports it as `AUTOWORK_DISK_TMP`; the task keeps it across attempts. (2) The worker prompt says `$TMPDIR` is small and in RAM: build output, target directories, scratch copies and anything large go under `$AUTOWORK_DISK_TMP`; never `/tmp`, `/var/tmp` or a new folder outside the worktree, and reusable downloads still go to `$AUTOWORK_CACHE`. (3) The reviewer is told the worker's disk folder read-only, as it is told the worker's `$TMPDIR` today. (4) `cleanup_tmpdir` removes the disk folder when the task closes or is set aside, a held commit keeps it for its review, and `sweep_retired_tmp` removes it for slots already retired.
- Acceptance: In fixtures, a launched worker's environment has `AUTOWORK_DISK_TMP` at the task's `slot-data/<task>/disk`, private and not under the runtime tmpfs; a second attempt gets the same folder. Closing and setting aside the task remove it; a held slot keeps it; a link or foreign-owned folder at that path is neither followed nor removed. The worker prompt names `$AUTOWORK_DISK_TMP` and forbids `/var/tmp`; the review prompt names the worker's disk folder when it is not empty.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_dispatch.py pi-autowork/tests/test_worker_tmp.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the per-repository cache (`AUTOWORK_CACHE`) or its retention, to the short `$TMPDIR` (socket paths must fit) or to set-aside worktrees; no sweeping of `/tmp` or `/var/tmp` entries the pipeline did not create.
- Planner's call: the folder lives under the slot data in the repository's git directory: on the repository's own disk, private to the task, and removed by the same retirement code that removes the rest of its temp files, so no new allocation record is needed. Placed in Now (owner, 2026-10-18: temp folders must be deleted after each task, "critical").


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-238-11 — Only the candidate the engine will integrate next is started, and only it reads 'verifying'

- [x] TOOLSET-238-11 — Only the candidate the engine will integrate next is started, and only it reads 'verifying'
- Status: done 2026-10-18 by the owner session: (1)-(2) and most of (3). The engine's refusal names the task that goes first (`integrate the highest-priority reported task first: <id>`), honoring the writers-busy skip; `settle` starts the first candidate and, on that refusal, the named one, never walking the list. "Verifying" is logged when an integration is still running after 1.5 s, or just before a quick INTEGRATED or HELD answer, never for a refusal. Not done: the `(<n> ahead)` place in the TUI lanes; waiting candidates show as `implemented`. Watching the slot turn `integrating` instead of the fixed wait was tried and dropped: returning to the loop earlier exposed lock races (dispatch answered "Repository busy" while the engine still held its writer lock). Checks: `test_only_the_candidate_the_engine_takes_next_is_started_and_reads_verifying` (fails on the old code), the review and reload journeys; python3 scripts/check.py passed (5 directories, four resource-gate skips), and the affected suites again after rebasing on 94d4342.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [coordinator](pi-autowork/pi_autowork/coordinator.py) (`settle`: for every reported row it logs `note_state(task, 'integrating')`, starts an engine `--integrate` child and waits up to 5 s for a quick refusal); [integration](skills/autowork/scripts/parallel_integrate.py) (`integrate` raises `integrate the highest-priority reported task first` for any other task, and `integrated` drops that refusal silently).
- Evidence (2026-10-18 17:55-17:56, this repository's runner, right after a reload): with 13 reported candidates, the log printed `<task>: verifying` for all 13 within a minute, and the runner launched 13 engine integration processes in a row. Every one but the first was refused at once for priority order. Only one candidate is ever reviewed at a time, so the log and the TUI lanes said 13 reviews were running, and each wrong guess cost an engine process (a ledger parse and a lock round) on a loaded host.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/tests/test_fleet_view.py
- Scope: (1) The engine's priority refusal names the task that goes first: `integrate the highest-priority reported task first: <id>`. It honors the writers-busy skip from TOOLSET-223-8e. (2) `settle` starts the candidate the status rows put first. On that refusal it starts the named task next, and at most once per cycle; it never walks the whole list. (3) `verifying` is logged when the engine accepted the integration (its child is still running after the quick wait, or it answered INTEGRATED or HELD), never before starting it. The other reported candidates show `implemented — waiting to integrate (<n> ahead)` in status and the TUI lanes. That isn't logged per cycle.
- Acceptance: In a runner fixture with three reported candidates whose reviews are slow, the log has exactly one `verifying` line at a time, and the run starts one engine integration per review (counted from the runs or engine log), not one per candidate; the refusal text names the first task; the TUI lanes show the others as waiting with their place.
- Checks: python3 -m unittest tests/test_pi_autowork.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s pi-autowork/tests -p test_fleet_view.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to integration order or to one review at a time.
- Planner's call: Now, after TOOLSET-222-e1: small, and it removes a false picture (13 reviews "running") that the owner and the fleet monitor read every pass, plus a burst of wasted engine processes after every reload.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-239-d4 — A worker's TMPDIR is a short directory on disk, not the shared RAM disk

- [x] TOOLSET-239-d4 — A worker's TMPDIR is a short directory on disk, not the shared RAM disk
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [temp allocation](skills/autowork/scripts/parallel_dispatch.py) (`worker_root`, `_disk_tmpdir`, `worker_tmpdir`, `_tmp_record`).
- Evidence (2026-10-18, this repository): TOOLSET-139-62 and TOOLSET-147-54 held asking for "a disk-backed task TMPDIR with at least 20 GB free": the runtime directory was a 6.3 GB RAM disk shared by every worker, and the suite's own gate needs that space. TOOLSET-212-0d had added a separate disk folder beside it, which leaves `$TMPDIR` itself too small.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/test_parallel_integrate.py, CHANGELOG.md
- Scope: A worker's `$TMPDIR` is `/var/tmp/aw-<uid>-<repo key>-<slot>` (`PI_AUTOWORK_WORKER_ROOT` moves it), private and socket-safe even when resolved, with the short `/tmp` path as fallback; an allocation on the runtime disk moves there with its files when the task's next worker starts.
- Acceptance: In fixtures the `$TMPDIR` is the disk path (a socket binds under its resolved path), the fallback is used when the disk path cannot be made, a foreign-owned or linked directory is refused, and an old allocation moves with its files.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_dispatch.py skills/autowork/scripts/test_parallel_integrate.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator (implemented in the main checkout, 3d0f2c0).
- Exclusions: No change to the per-repository cache.
- Planner's call: `$TMPDIR` itself on disk replaces TOOLSET-212-0d's separate disk folder (owner, 2026-10-18: "make the change").
- Evidence of completion: 3d0f2c0; python3 scripts/check.py passed (5 test directories, 0 failed); test_parallel_dispatch 44 passed.


<!-- archived from TODO.md -->

Source section: Now

### TOOLSET-165-f7 — A runner's own worker processes never count as an outside session in the main checkout

- [x] TOOLSET-165-f7 — A runner's own worker processes never count as an outside session in the main checkout
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [writer check before integration](skills/autowork/scripts/parallel_integrate.py) (the pool-attribution loop before `WritersBusy('live or unknown external writer/session; preserve canonical checkout: …')`), [worker launch](skills/autowork/scripts/parallel_dispatch.py) (`launch`, `start_new_session=True`), [slot state](skills/autowork/scripts/parallel_state.py), [identity helpers](skills/autowork/scripts/task_execution.py) (`identity`, `argv_of`).; [qualification recovery](docs/plans/2026-10-16-pi-autowork-coordinator.md#worker-attribution-candidate-qualification-recovery).
- Evidence (2026-10-17 11:31-11:43, this repository's runner): a verified TOOLSET-142-85 commit waited 12 minutes with `waiting to integrate until another session leaves the main checkout (… pid 770860 pi in .worktrees/autowork-TOOLSET-154-d3-r2 (no terminal / running commands))`. That process was the runner's own TOOLSET-154-d3 attempt-2 worker. The slot record named leader pid 767411 (state `running`, worktree `…-154-d3-r2`), and 770860 ran only in that worktree, but it was not the leader and not in the leader's process group, so attribution failed. The attempt had resumed across two coordinator restarts (11:05 and the 11:18/11:39 self-updates). Health reported `verified commit(s) wait for another session in the main checkout (runner, holds 49)`.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_state.py, skills/autowork/scripts/test_parallel_adversarial.py, skills/autowork/scripts/fixtures/fake_worker.py
- Scope: (1) Attribute a writer to a pool slot when it is the slot's identity-matched leader, in the leader's process group, or a descendant of the leader through a parent chain whose every link is alive with a matching birth identity, and every workspace it uses is inside that slot's worktree. A pi or shell that a worker starts in its own session or process group is therefore still the worker's. (2) Keep fail-closed for everything else: an unknown agent in a sibling worktree, a process whose chain leaves the slot's leader, a dead or reused leader PID, or a slot not `dispatched`/`running` still blocks. (3) The `WritersBusy` reason names the slot it was compared with when a process sits in a slot worktree but could not be attributed (`unattributed process in <task>'s worktree: <why>`), so a misattribution is visible rather than reported as another session.
- Acceptance: In fixtures, a worker leader that spawns a child in a new session, and that child's own child, both in the slot worktree, do not block integration. A same-worktree process whose parent chain does not reach the leader, a process in a sibling slot's worktree, and a leader PID reused with a different start time each still block, with the new reason naming the slot. A slot resumed after a coordinator restart (new leader recorded) attributes its descendants the same way.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_state.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator. Runs before TOOLSET-161-17, which reconciles this change in parallel_integrate.py.
- Exclusions: No relaxation for processes outside the pool's worktrees or in the canonical checkout itself; no change to the main-checkout session rule from TOOLSET-120-fc.
- Planner's call: first in Now, ahead of TOOLSET-161-17 (owner, 2026-10-17). A misattributed own worker stalls every verified merge (twice in 20 minutes on 2026-10-17, the second a pi process in TOOLSET-124-97's attempt-2 worktree), and the fix is a narrow attribution rule with fail-closed defaults.
- Qualification recovery: An earlier attempt-2 report asked for a new validation window/host because two fixed-duration fixtures also failed targeted retry; the retained ad7bfac candidate now contains their repair. Routine test-only recovery is within this task: replace the two-second A-worker ordering assumption in test_out_of_order_completion_lands_each_commit_once and the sixty-second worker-lifetime assumption in test_two_retries_and_fresh_tasks_fill_eight_worker_slots with test-owned ready/release signals and bounded cleanup. Preserve every original ordering, exactly-once, retry/refill, eight-slot, live-process and negative ownership assertion; no skips, longer-sleep workaround, production test hook or weakened gate. Reconcile the delivered 3bd1d95 checker/environment correction instead of reimplementing it. Original Scope and Acceptance remain binding; see the cited recovery section.
- Additional checks: Planned after the fixture repair: `python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_adversarial.py`, the existing named parallel-integrate/state suites and the complete original offline inventory on the resulting tree. The retained candidate now reports these checks passing with its source-bound serial receipt; earlier failed inventories remain historical failures, and current integration qualification is separate.
- Next action: Resume integration-only recovery of retained clean commit ad7bfac24ad1f934fad3c2d8fe37c0120874c7ce in .worktrees/autowork-TOOLSET-165-f7-r2. The deterministic fixture recovery is already implemented; do not restore a8170f5 or reimplement it. The retained qualification-check-serial-receipt.json reports exit 0 with matching before/after source fingerprints, and the worker reports the focused/full checks passed; preserve those receipts as candidate evidence, not proof of a newer integration tree. The recorded integration revision 8f477962e9063151a9b829cc6c16f1e92275de84 has no terminal receipt at its named path. Once the live integration owner permits, establish the exact current integration tree, collect or rerun only missing/invalidated required verification through that owner, and close only after accepted integration. Preserve cumulative attempts, current candidate and failed/missing historical evidence; no new owner approval, restored old snapshot, manual retry/reset or passing claim from main green.
- Blocker reconciliation: Planning-only technical continuation saved after comparing the session question, current canonical contract, candidate and latest retained report. No new owner intent or operation authority is required; no check is waived and no worker/claim is released by this answer. Pick-up and completed delivery still require observation.
- Review failure cause: The 2026-10-17 22:34 integration review of ad7bfac failed on its environment, not the candidate: socket-path errors from the long review TMPDIR (`review-tmp/<task>-<pid>` under the runner state directory), cleanup failures and runner timeouts at load average about 30. The worker's own run of the same checks with a short TMPDIR passed. 740b48a (TOOLSET-140-f4, landed 23:04) keeps the worker's short TMPDIR for the review. Review ad7bfac again on the current tree; do not reimplement it, and do not count the earlier environmental failure against the candidate's acceptance.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-195-ee"></a>

### TOOLSET-195-ee — The runner's own jobs never count as outside sessions

- [x] TOOLSET-195-ee — The runner's own jobs never count as outside sessions
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17): "yes, plan the task"; [external workers](skills/autowork/scripts/task_execution.py) (`external_workers`, the `AUTOWORK_EXECUTION_COMMON` marker), [runner jobs](pi-autowork/pi_autowork/coordinator.py) (the background main check in `pi-scratch-main-check-*`, the DOCS-MAINTAINER, provisioning, merge resolution and Touches inference in `pi-scratch-*`), [main check](pi-autowork/pi_autowork/main_check.py).
- Evidence (2026-10-17 22:03, this repository's runner): TOOLSET-165-f7's attempt-2 commit waited to integrate on `live or unknown external writer/session; preserve canonical checkout: pid … python3 in <repo>/.worktrees/pi-scratch-main-check-… (no terminal; activity unknown)`. Those were the runner's own background check of main, started at 22:01. `external_workers` recognizes the runner's commands only by the `AUTOWORK_EXECUTION_COMMON` marker, which only engine commands carry; the main check's test processes start fake `pi` agents, so they read as outside agent sessions. Every integration that falls during a main check (2 to 5 minutes, after every landing) waits for it. TOOLSET-165-f7 covers worker processes only.
- Touches: skills/autowork/scripts/task_execution.py, skills/autowork/scripts/test_task_execution.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, skills/autowork/references/parallel-workers.md
- Scope: (1) A process in this runner's own systemd unit (its `/proc/<pid>/cgroup` names `pi-autowork@<name>.service` for this repository), or one carrying the attribution marker, is the runner's own and never an outside writer or session, wherever it runs. (2) Without systemd (a foreground `autowork run`), every job the runner starts (main check, maintainer, provisioning, merge resolution, Touches inference) carries the marker, and test processes it starts keep it. (3) The runner's own jobs in their `pi-scratch-*` worktrees never block integration, closeout or worktree cleanup; a person's session in those worktrees still does. (4) A blocked integration names the process's kind (`runner job: main check` or `session`), so a wrong attribution is visible in the log.
- Acceptance: In fixtures, an integration during a running main check proceeds without waiting, under systemd (a fake cgroup file) and without it (the marker). An agent process started outside the runner in the main checkout, or in a `pi-scratch-*` worktree, still blocks with the `session` reason. Fixture runners started by the test suite are not mistaken for the real runner's jobs (their cgroup is not the real unit's and they carry no real marker).
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator; builds on TOOLSET-165-f7's attribution of worker descendants in the same writer check.
- Exclusions: No change to which outside sessions block, to the main check itself or to how often it runs.
- Planner's call: the service's control group as the primary signal, because it covers every process the runner starts, including detached ones and test fixtures that drop the environment, and cannot be set by an outside process. The marker remains for foreground runs.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-189-96"></a>

### TOOLSET-189-96 — A new runner starts cleanly: a lasting PATH and committed planning files

- [x] TOOLSET-189-96 — A new runner starts cleanly: a lasting PATH and committed planning files
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [service install](pi-autowork/pi_autowork/service.py) (`run` writes `PATH=` from the installing shell), [readiness](pi-autowork/pi_autowork/fleet_view.py) (`readiness`), [session start](pi-autowork/pi_autowork/coordinator.py) (`ensure_session`, the engine-attention loop).
- Evidence (2026-10-17, a runner added to the fleet that evening, in a Git submodule): (1) its service crashed with `FileNotFoundError: ... ~/.cache/uv/builds-v0/.tmp<id>/bin/python3`: it was installed from inside a `uv run` environment, the settings file's `PATH` starts with that temporary build directory and `~/.cache/uv/archive-v0/<id>/bin`, and both were gone by the next start. (2) After a restart it looped on `The engine needs attention: [Errno 2] No such file or directory: <session worktree>/TODO.md` every minute, shown as idle: `TODO.md` and `goals.json` exist in the main checkout but are untracked, so the session worktree, made from the committed main branch, has neither. `autowork start` called the repository ready because both files exist. (The session worktree also landed under `.git/modules/<name>/.worktrees/`; another session is already fixing that in `worktree_paths.canonical_root`.)
- Touches: pi-autowork/pi_autowork/service.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/questions.py, tests/test_autowork_command.py, tests/test_pi_autowork.py, pi-autowork/tests/test_fleet_view.py, pi-autowork/tests/tui_pilot.py, pi-autowork/tests/test_status_cache.py
- Touches widened by the owner session: pi-autowork/tests/test_status_cache.py (2026-10-18), which the worker adjusted while merging main's repository-status cache into its branch.
- Touches widened by the runner from worker evidence: pi-autowork/tests/tui_pilot.py
- Scope: (1) The service's `PATH` keeps only directories that exist and are not under a tool's temporary or cache build area (`~/.cache/uv/builds-v0`, `~/.cache/uv/archive-v0`, and any `.tmp*` component), with duplicates removed in order; the install output names what it dropped. (2) Readiness requires `TODO.md` and `goals.json` committed on the main branch (`git cat-file -e <base>:TODO.md`), and `autowork start` says `commit TODO.md and goals.json on <base> first` when they are only on disk. (3) A running runner whose base lacks them reports one runner blocker and one BLOCKERS.md question (`planning files are not committed on <base>`) instead of the engine-attention loop, and resumes on its own once they are committed. No model call.
  (4) (Folded 2026-10-17) A recorded session whose worktree is not at the canonical location (one made before 4a98845 under `.git/modules/<name>/.worktrees/`) is retired when it has no commits of its own and recreated at the canonical path; with commits of its own it is moved with `git worktree move`. The same runner kept its old session after the fix and still logged `No such file or directory: <old path>/TODO.md` every minute.
- Acceptance: In fixtures: installing with a `PATH` that starts with a missing `.tmp` directory and a uv build directory writes a settings file without either and says so; `autowork start` on a repository whose `TODO.md` and `goals.json` are untracked refuses with that message; a runner started on such a repository logs one blocker line and writes the question, then dispatches after the files are committed, with no `The engine needs attention` line.
- Checks: python3 -m unittest discover -s tests -p test_autowork_command.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 -m unittest discover -s pi-autowork/tests -p test_fleet_view.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No commit of the owner's planning files by the runner at start; the submodule worktree location belongs to the other session's change.
- Planner's call: after TOOLSET-188-75 in Now; every repository added to the fleet goes through this path, and the failure looks like an idle runner.
- Next action: Resume delivery of retained commit d314fad5334069eb8343d3482b07a207d8af8019, not a fresh implementation. Canonical Touches already includes pi-autowork/tests/test_status_cache.py and its widening note; the current scope hold cites the older assigned contract. The existing coordinator must reconcile that accepted contract through its normal held-candidate workflow, verify candidate identity/source-bound checks and perform fresh integration verification after overlapping TOOLSET-197-4f releases the workspace. Keep all nine changed paths, acceptance, review and safety guards; no manual slot rewrite, forced merge or attempt/budget reset.
- Blocker reconciliation: Planning-only technical continuation saved after comparing the session question, current canonical contract, candidate and latest retained report. No new owner intent or operation authority is required; no check is waived and no worker/claim is released by this answer. Pick-up and completed delivery still require observation.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-197-4f"></a>

### TOOLSET-197-4f — An invalid goals.json is a DOCS-MAINTAINER trigger, not an endless engine-attention loop

- [x] TOOLSET-197-4f — An invalid goals.json is a DOCS-MAINTAINER trigger, not an endless engine-attention loop
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-17); [maintainer triggers](pi-autowork/pi_autowork/maintainer.py) (`triggers`), [coordinator](pi-autowork/pi_autowork/coordinator.py) (the `ACTION_REQUIRED` branch logging `The engine needs attention`), [ledger](skills/docs-sync/scripts/goals.py) (`validate`).
- Evidence (2026-10-17, a runner added that evening): after its planning files were committed it ran one task, then logged `The engine needs attention: invalid goals.json: <GOAL>: unverified goal has no open task; checking again in 60s` every minute and showed as blocked. Nothing repairs a ledger the engine refuses: the DOCS-MAINTAINER only reacts to held, not-runnable or review-finding tasks and to a red main, and BLOCKERS.md got no question.
- Touches: pi-autowork/pi_autowork/maintainer.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_maintainer.py, pi-autowork/tests/test_questions.py, tests/test_pi_autowork.py
- Scope: (1) When the engine answers `ACTION_REQUIRED` with a reason starting `invalid goals.json` (or `goals.py validate` fails on the session), the runner adds the item `LEDGER` with the validate errors to the maintainer's triggers, runs the maintainer once per distinct error set, and lets it change only planning files as today (a goal with no open task gets a task for its remaining proof, or its evidence and status corrected). (2) If the maintainer's change does not validate, or it makes no change, the runner writes one BLOCKERS.md question quoting the errors. (3) The log says once per error set what was tried, not every minute.
- Acceptance: In a fixture whose goals.json has an unverified goal with no open task, the runner logs one `DOCS-MAINTAINER: repairing the task docs of LEDGER`, merges the maintainer's planning change, and dispatches afterwards; with a maintainer that changes nothing, one question appears in BLOCKERS.md and the attention line is logged once.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_maintainer.py; python3 -m unittest discover -s pi-autowork/tests -p test_questions.py; python3 scripts/check.py tests/test_pi_autowork.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to goals.py's validation rules.
- Planner's call: next to TOOLSET-196-fb: a refused ledger stops a whole repository and nothing tells the owner.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-184-b3"></a>

### TOOLSET-184-b3 — Restore the full offline check after the red main at 36e2b7c

- [x] TOOLSET-184-b3 — Restore the full offline check after the red main at 36e2b7c
- Status: done
- Goal: PI-RUNNER
- Payoff: Restore the existing offline gate so runner reviews can distinguish new regressions from a broken baseline.
- Sources: [accepted continuous Pi runner](docs/project.md#continuous-pi-runner-2026-10-15); `scripts/check.py`, `tests/test_pi_autowork.py`, `pi-autowork/tests/test_pi_runtime.py`, `pi-autowork/tests/test_publishable.py`, `pi-autowork/tests/test_release.py`, `skills/autowork/scripts/test_parallel_adversarial.py`, `skills/autowork/scripts/test_parallel_e2e.py`, `skills/autowork/scripts/test_parallel_integrate.py`, `skills/autowork/scripts/test_publication_readiness.py`, `skills/autowork/scripts/test_budget_controller.py`, `skills/autowork/scripts/test_native_containment.py`, `skills/autowork/scripts/test_task_execution.py`, `tests/test_worktree_closeout.py`, `tests/test_tx.py`, `pi-autowork/tests/test_janitor.py`, `skills/autowork/scripts/test_audit_profiles.py`, `skills/autowork/scripts/audit_profiles.py`, `skills/docs-sync/scripts/test_docs_stale.py`; [review scratch setup](pi-autowork/pi_autowork/worker.py); [current MAIN and worker evidence](docs/tasks/TOOLSET-184-b3-main-recovery.md).
- Evidence: Current MAIN at `e4faccb8165c770368d1884b38b2ea0249a444c4`, after recorded green `520ddb85da146c5d115754ea1e3fe32e02ba7ad1`, fails `test_pi_autowork.EngineTests.test_a_task_commit_that_conflicts_with_the_session_is_merged_not_reimplemented` and `test_parallel_integrate.IntegrationTests.test_a_build_daemon_left_behind_by_a_passing_validation_does_not_fail_it`. The completed full gate exits 1 (3 directories passed, 2 failed, 8 exclusions; one skip, not a pass). The conflict trace shows a dirty `A.txt` merge abort, later session-dirt commit and a second worker run for A, not the expected resolver/reverify path. The daemon case reaches INTEGRATED, then reports `EXECUTED` instead of `CHILDREN_TERMINATED`; its close assertion is not reached. Capture fixture Git results, slot/command receipts and cleanup evidence before attributing either failure to runtime or fixture ordering. The [current receipt](docs/tasks/TOOLSET-184-b3-main-recovery.md#current-main-receipt-at-e4faccb) retains all eight supplied commits and changed-file evidence, already within Touches. Neither a cause nor a fix is established; TOOLSET-204-f2's planned flaky classification cannot waive this repair's full gate.
- Prior MAIN evidence: MAIN at `d72179ed391684ae6b9c6951ef268a901b75298d`, after recorded green `2e755cb1349c273c5b9885f267da00305bf47514`, fails `test_parallel_integrate.IntegrationTests.test_a_failing_validation_with_a_daemon_still_holds_and_old_daemon_holds_are_offered_again`: `CHECK_FAILED` instead of `CHILDREN_TERMINATED` at `skills/autowork/scripts/test_parallel_integrate.py:1218`. The full gate exits 1 (4 directories passed, 1 failed, 8 exclusions; 4 host-resource skips, not passes). The [prior receipt](docs/tasks/TOOLSET-184-b3-main-recovery.md#current-main-receipt-at-d72179e) retains the supplied ten commits and changed-file evidence, already within Touches. The earlier HELD assertion passed; the failure stops before the exit-1 rejection and historical exit-0 reoffer assertions. Capture the command receipt, descendant cleanup and child log before deciding whether the fixture or runtime needs correction; no cause is established. The preceding `6c8f9a5` receipt's waiting-runner fixture `git commit -qam unblock` exit 128 remains a regression requirement, not this run's failure or a proven dispatch defect. The preceding `151718f` receipt's two integration failures and four resource-gated skips remain historical evidence, not this run's failure inventory or passes. No duplicate task or verified causal attribution follows. The preceding receipt at `cc59768` had four restart-adoption/ABC/serial failures; it is historical, not the current inventory. Historical evidence: the runner's `main_check.json` records red revision `36e2b7c0ea0c6096a7b20197edcacf68dc11dfa4`, no recorded green revision, and 20 failing test identities. Its completed `main-check.log` records 28 distinct failing/error identities below and ends `Offline result: 2 test directories passed; 3 failed; 8 modules excluded.` These are retained runner receipts, not checks repeated by this docs pass. There is no `slot-data/MAIN/` worker report. The [later MAIN receipt and failed review](TODO.archive.md#main-receipt-at-3ca53ce-and-toolset-184-b3-review) record 25 distinct failures at `3ca53ce` (including five budget-evidence cases) and the rejected review of integration candidate `a7d3f9f`, derived from worker commit `2c23b62`. The worker's reported full pass is bound to its older tree, not proof that the reviewed merged tree passed. Completed TOOLSET-176-98 in [the archive](TODO.archive.md) owns detection/repair-task creation, not this repair; open TOOLSET-180-72 owns the future regression gate, not restoring this baseline.
- Failing tests (recorded in both receipts):
  - `test_pi_autowork.EngineTests.test_independent_tasks_run_in_parallel_and_merge_verified_into_main`
  - `test_pi_autowork.EngineTests.test_merged_work_is_pushed_to_main_upstream`
  - `test_pi_autowork.EngineTests.test_a_rejected_push_merges_the_upstream_and_pushes_again`
  - `test_pi_autowork.SetupTests.test_an_idle_runner_updates_its_toolset_and_restarts_on_the_new_code`
  - `test_pi_autowork.EngineTests.test_provider_failure_falls_back_and_resumes_the_same_session`
  - `test_pi_autowork.SetupTests.test_a_release_that_cannot_read_current_state_is_never_installed`
  - `test_pi_autowork.EngineTests.test_missing_credentials_at_run_time_fall_back`
  - `test_pi_autowork.EngineTests.test_questions_for_the_owner_land_in_blockers_md_without_a_model`
  - `test_pi_autowork.SetupTests.test_a_broken_toolset_update_keeps_the_running_code`
  - `test_pi_autowork.EngineTests.test_unauthenticated_primary_and_no_fallback`
  - `test_pi_autowork.EngineTests.test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why`
  - `test_pi_autowork.EngineTests.test_the_docs_maintainer_restates_a_task_that_is_not_runnable_as_written`
  - `test_pi_autowork.EngineTests.test_the_docs_maintainer_may_change_only_planning_files_and_runs_once_per_trigger_set`
  - `test_parallel_adversarial.AdversarialWorkerTests.test_a_report_written_after_a_coordinator_restart_is_adopted`
  - `test_parallel_e2e.EndToEndTests.test_abc_real_cli`
  - `test_parallel_e2e.EndToEndTests.test_abc_with_delayed_initial_observation`
  - `test_parallel_e2e.EndToEndTests.test_serial_control`
  - `test_publication_readiness.PublicationReadinessTests.test_ancestry_conflict_never_becomes_force_push_readiness`
  - `test_publication_readiness.PublicationReadinessTests.test_multiple_remotes_are_resolved_by_bound_authority_not_origin_guess`
  - `test_pi_runtime.RuntimeTests.test_a_provider_failure_cools_the_primary_and_the_fallback_finishes`
- Additional failing tests (full log, omitted from the 20-name summary):
  - `test_pi_runtime.RuntimeTests.test_model_choice_and_the_budget`
  - `test_publishable.PublishableTests.test_a_pointer_to_a_local_only_commit_stays_out_until_it_is_pushed`
  - `test_publishable.PublishableTests.test_an_untracked_nested_repository_is_not_added`
  - `test_publishable.PublishableTests.test_ordinary_files_are_unchanged`
  - `test_release.ReleaseCheckTests.test_a_compatible_release_may_be_installed`
  - `test_release.ReleaseCheckTests.test_a_release_that_cannot_read_this_state_is_refused`
  - `test_release.ReleaseCheckTests.test_another_runner_with_work_in_flight_defers_the_update`
  - `test_release.ReleaseCheckTests.test_fetched_declarations_are_parsed_never_executed`
- Commit evidence: The receipt reports `36e2b7c`, `99813f9`, `ce43743`, `d9e39b4`, `db2e4ba`, `69937f0`, `0749177`, `b40d85f`, `2f27806`, `e22cee9`, `605a302`, `1515af8`, `2e415c4`, `a01e061`, `6aacc26`, `6fee26e`, `d495a6b`, `9ea176b`, `93d1f2a`, `f9fdf43`. With `green: null`, this is the reported history window, not a proven range since green or attribution of fault. Relevant changed files include `scripts/check.py` and `tests/test_check.py` (36e2b7c); coordinator/maintainer and their tests (ce43743, 1515af8, 2f27806); fleet view/health and their tests (db2e4ba); parallel dispatch/plan and their tests (d495a6b).
- Observations: The log shows forbidden `pi-autowork-push-disabled` transport during disposable Git fixture setup; fallback cases retry the primary or say fallback is disabled; otherwise-unrelated fake repositories run an inherited `python3 scripts/check.py` that exits 2 and triggers MAIN maintainer calls. Three end-to-end cases explicitly refuse admission at load 46.54 against 24 CPUs. These observations suggest fixture-environment/load isolation gaps, not permission to weaken production guards or a verified single cause. `Fixture.setUp` clears some inherited settings but not `PI_AUTOWORK_MAIN_CHECK` or `PI_AUTOWORK_NO_FALLBACK`; runtime fixtures overlay the parent environment.
- Touches: scripts/check.py, tests/test_check.py, tests/test_pi_autowork.py, tests/test_autowork_command.py, tests/test_worktree_closeout.py, tests/test_tx.py, pi-autowork/pi_autowork/, pi-autowork/tests/, skills/autowork/scripts/, skills/docs-sync/scripts/test_docs_stale.py, skills/autowork/references/parallel-workers.md, docs/cross-host.md
- Scope: Reproduce and repair this recorded offline failure inventory, starting at the existing fixture/environment seams and the new parallel checker. Keep the full inventory, assertions and production runner contracts intact. Isolate synthetic repos, fake providers and simulated host load at the fixture boundary; any runtime correction must preserve the existing accepted behavior. Coordinate overlapping engine/coordinator edits with their current workers, preserving candidates and pinned inputs.
- Acceptance: Every named failing/error case passes on the repaired tree, and the complete existing offline check passes across all five test directories without dropping tests, weakening assertions, raising timeouts or excluding failures. Fixture-only Git transport remains confined to disposable repositories; production worker push denial, fallback configuration, resource admission and no-model idle behavior retain their existing contracts. Record the tested revision, environment and complete result; fixture passes do not establish live provider, publication or fleet qualification.
- Checks: Required full gate (planned, not run here), only after the coordinator supplies permitted physical task scratch outside repository ancestry: `test -n "${TMPDIR:-}" && tmp=$(mktemp -d "$TMPDIR/aw-XXXXXX") && (trap 'rm -rf "$tmp"' EXIT; export TMPDIR="$tmp"; python3 scripts/check.py)`. The earlier direct `/tmp` sample conflicts with the reviewer's supplied-scratch restriction; this command creates only a child of supplied TMPDIR and is not permission to choose an outside directory. First reproduce the current failures with `python3 scripts/check.py tests/test_pi_autowork.py -k test_a_task_commit_that_conflicts_with_the_session_is_merged_not_reimplemented` (retain fake `move_session` Git add/commit exit codes and stdout/stderr, session status, slot state and worker invocation count; preserve the resolver/reverify messages, exactly one A worker run and A/B/C completion assertions) and `python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py -k test_a_build_daemon_left_behind_by_a_passing_validation_does_not_fail_it` (retain the validation command receipt, child log and descendant cleanup; preserve INTEGRATED, CHILDREN_TERMINATED and CLOSED assertions). These planned checks supplement the unchanged full gate and prior regressions, not an isolated-pass waiver. Then run `python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py -k test_a_failing_validation_with_a_daemon_still_holds_and_old_daemon_holds_are_offered_again` with the validation command receipt (exit code, terminated descendants and input match), child log and slot state retained. Preserve HELD for exit 1, the daemon-cleanup outcome, rejection by `passed`, and the historical exit-0 reoffer assertions; a passing isolated run is diagnostic, not a full-gate pass or proof of a fix. Then run the prior waiting-runner regression `python3 scripts/check.py tests/test_pi_autowork.py -k test_a_waiting_runner_sees_tasks_committed_to_main_later`, retaining Git stdout/stderr and runner state if it fails; keep its later-main-dispatch and stop assertions. Do not substitute retries or longer timeouts for a diagnosed correction. Then run the affected modules with `python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py` (including the prior MAIN failures and their slot-return, daemon cleanup, exit-status and reoffer assertions), `python3 scripts/check.py tests/test_pi_autowork.py`, `python3 -m unittest discover -s tests -p test_check.py`, `python3 -m unittest discover -s pi-autowork/tests`, and `python3 -m unittest discover -s skills/autowork/scripts -p 'test_parallel_*.py'` plus `python3 -m unittest discover -s skills/autowork/scripts -p test_publication_readiness.py`, using a fresh short private TMPDIR. Exercise fixture isolation under the recorded inherited main-check/fallback settings and worker push guard, without changing the outer worker's guard or contacting a remote service. Also run `python3 -m unittest discover -s skills/autowork/scripts -p test_budget_controller.py`, `python3 -m unittest discover -s skills/autowork/scripts -p test_native_containment.py`, `python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py`, `python3 -m unittest discover -s tests -p test_worktree_closeout.py`, `python3 -m unittest discover -s tests -p test_tx.py`, and `python3 -m unittest discover -s pi-autowork/tests -p test_janitor.py` for the newly recorded failure seams. Also require `python3 -m unittest discover -s skills/autowork/scripts -p test_audit_profiles.py` and `python3 -m unittest discover -s skills/docs-sync/scripts -p test_docs_stale.py` under the same permitted non-repository scratch: the continuation's full gate failed those fixtures. These checks are required procedures, not passes from this docs edit. Worker and reviewer must record the actual resolved TMPDIR and exact command: reconcile the short physical scratch requirement with the reviewer's task-owned scratch restriction in the existing setup/fixture seam; do not substitute a `/proc` alias, write outside the reviewer's permitted scratch, or treat a different environment's pass as the required gate. `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator; one repair worker, serialized with overlapping active work.
- Exclusions: No product redesign, live operations, credentials, spending authority, push-guard bypass, automatic revert, or reset of existing worker attempts. This task does not close or replace another task's acceptance.
- Review continuation: The reviewer rejected `a7d3f9f` with `Full offline gate exits 1: only 2/5 directories pass. Required TMPDIR exposes socket-path, worktree-cleanup and tx fixture failures; full-gate acceptance is unmet.` Resolve all three findings without weakening Acceptance: (1) AF_UNIX path overflow in native-containment and janitor fixtures; a short `/proc` alias instead caused canonical-path assertion failures and is not a valid substitute. (2) Disposable merged worktrees were retained as `managed by pi-autowork` under the review-state ancestor, breaking closeout and both task-claim fixtures; isolate the fixture from real runner ownership while preserving production cleanup protection. (3) The tx help assertion matched `autowork` inside the temporary config path, not a new tx command; preserve the no-Autowork-command contract while correcting fixture/path contamination. An interrupted-validation focused failure passed with default SIGINT handling; retain that check, not a claim that its first failure was fixed. Separately reproduce the five newly recorded budget-evidence failures and preserve evidence retention, uncertainty, deadlines and cleanup assertions; timing/load is a hypothesis, not a verified cause.
- Next action: Read the completed current-main receipt at `e4faccb` before changing fixtures; the owner's rerun-first instruction now has that source-bound red result, not a pass. Reproduce the conflict-recovery and passing-validation/daemon cases first with the new focused Checks. Distinguish a failed fake session commit or ordering issue from a runtime merge defect using Git diagnostics and slot state; distinguish daemon receipt classification from surviving descendants using the command receipt, child log and cleanup evidence. Preserve the same-candidate resolver/reverify path, exactly one A worker run, all task completions, passing-validation cleanup and close assertions. Keep the earlier failing-validation/daemon, waiting-runner, lock and every historical named case as required regressions; exit 1 must remain held and rejected by `passed`, with historical exit-0 reoffer preserved. Neither the trace nor an older isolated pass establishes a cause or correction. TOOLSET-204-f2 owns future runner flaky classification, not a waiver of this repair's full-gate acceptance. The latest retained report is still `slot-history/TOOLSET-184-b3/3/slot-data/attempt-1/report.json`: `commit: null`, no changed files, no test run and clean baseline `f428b8f`; its scratch blocker predates the integrated TOOLSET-140-f4 change (`740b48a`, merged by `77843f0`, closed by `1b7d212`). Verify the actual supplied worker/reviewer physical TMPDIR paths are permitted, short and have no ancestor containing `.git`; do not wait for the completed task or assume an old worker's environment changed. Preserve the 19-file continuation in `.worktrees/autowork-TOOLSET-184-b3-set-aside-2` (baseline `0c420d5`, still 17 modified and two untracked files), not the clean set-aside-3 checkout, and reconcile only changes still needed on current main. Then rerun every required focused check and the unchanged full gate and obtain independent review on the resulting merged tree. Retain every review finding above; do not replay old candidates over current main, weaken guards, use aliases, write outside supplied scratch, reset attempts or repin evidence. This documentation releases no slot, grants no new scratch access, closes no task and authorizes no fresh implementation attempt.
- Priority reason: The MAIN-specific repair instruction and completed TOOLSET-176-98 require one repair task first in Now; preserve the relative order and full contracts of every existing task.
- Owner priority and rerun instruction (2026-10-17): set aside so TOOLSET-165-f7 runs first. Its red-main cause is mostly the
  check fixed since: 3bd1d95 sizes parallel tests to idle CPUs and keeps runner settings out of them, and the
  remaining test_parallel_e2e and adversarial failures come from the real host load gate (load >= CPUs).
  Re-run the full check on the current main before changing any fixture.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-172-40"></a>

### TOOLSET-172-40 — A worker paused by a runner restart shows as paused, not failed

- [x] TOOLSET-172-40 — A worker paused by a runner restart shows as paused, not failed
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17): "find out why 165-f7 died", then "yes, plan the task"; [slot reaping and pause](skills/autowork/scripts/parallel_state.py) (`pause`, the reap that sets `EMPTY`, `change`), [status rows](skills/autowork/scripts/parallel_status.py) (`failed` count), [lifecycle words](pi-autowork/pi_autowork/common.py) (`lifecycle`), [coordinator log](pi-autowork/pi_autowork/coordinator.py) (`note_state`), [status listing](pi-autowork/pi_autowork/cli.py), [TUI words](pi-autowork/pi_autowork/fleet_view.py) (`PHASE_WORDS`, `WORD_STYLES`).
- Evidence (2026-10-17 13:43, this repository's runner): a service restart stopped the runner five seconds after TOOLSET-165-f7's worker started. `pause` marked the slot `paused`, Pi exited with no changes, and the reap released it with `dead worker without a commit or changes`. The runner logged `TOOLSET-165-f7: failed — dead worker without a commit or changes`, and status listed it as `failed` with that reason and again as `pending`, and counted it among `4 failed`. The slot was `released`, attempt 1, `paused: true`: it resumes on the same attempt and lost nothing. The owner read it as a crash.
- Touches: skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_state.py, skills/autowork/scripts/parallel_status.py, pi-autowork/pi_autowork/common.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/cli.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/tests/test_fleet_view.py, tests/test_pi_autowork.py
- Scope: (1) A slot that a deliberate stop paused and that ended `interrupted` or `released` gets the lifecycle word `paused`, not `failed`, in the runner log, `autowork status`, `autowork ls` and the TUI. The reap records the reason `stopped by a runner restart; resumes on attempt <n>`, plus `with uncommitted changes` when the worktree had any; the dead-worker reasons stay for unpaused slots. (2) Paused slots do not count toward `failed` in status totals and never toward the failure streak. (3) Status shows each task once: a paused slot that also waits for dispatch shows `paused` with the waiting reason appended (`…; waiting: overlapping paths with <task>`).
- Acceptance: In fixtures, a worker stopped by `pause` and then reaped with no changes shows `paused` with the restart reason in the log line, the status row, the totals and the TUI. The same with uncommitted changes says so. An unpaused worker that dies with nothing still shows `failed — dead worker without a commit or changes`, and a second-attempt unpaused death still holds with cause `empty`. A paused slot that waits on overlap appears in one row. The resume itself is unchanged: same worktree, same attempt.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_state.py; python3 -m unittest discover -s pi-autowork/tests -p test_fleet_view.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to when a stop pauses workers, to resume or retry rules, or to holds.
- Planner's call: placed after TOOLSET-171-35. It changes only words and counts, and a misread failure costs the owner an investigation, not runner time.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-181-02"></a>

### TOOLSET-181-02 — Planning files merge without conflicts: union archive, keyed goals.json, re-rendered coverage

- [x] TOOLSET-181-02 — Planning files merge without conflicts: union archive, keyed goals.json, re-rendered coverage
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: feedback from an interactive session in one fleet repository (2026-10-17), pasted by the owner with "please plan these as tasks, folding into existing ones where they overlap" (item 4); [goals commands](skills/docs-sync/scripts/goals.py) (`render`, `reorder`), [archive](skills/docs-sync/scripts/todo_archive.py), [merge attributes](.gitattributes) (`CHANGELOG.md merge=union`), [session merge](pi-autowork/pi_autowork/coordinator.py) (`merge_main`).
- Evidence (2026-10-17): TODO.md and goals.json conflicted again in one fleet repository, and this repository needed a hand merge that kept both task archive entries. Coverage rows run to hundreds of characters with inline scratch paths, so two closes that touch one goal always collide on the same line. goals.json is keyed by task ID and its `priority_order` follows TODO.md; the coverage table is rendered from goals.json.
- Touches: skills/docs-sync/scripts/goals.py, skills/docs-sync/scripts/test_goals.py, skills/docs-sync/scripts/todo_archive.py, skills/docs-sync/scripts/test_todo_archive.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, .gitattributes, skills/docs-sync/SKILL.md
- Scope: (1) `goals.py merge-driver` merges goals.json by task and goal ID (three-way per record; the same record changed differently on both sides is a real conflict) and rebuilds `priority_order` from the merged TODO.md. (2) For TODO.md it merges the task entries with Git and re-renders the coverage table from the merged goals.json, so the generated region never conflicts. (3) The archive merges as a union of entries, keeping both and never duplicating one. (4) Each runner registers the drivers in its repository's local Git config on start and commits the matching `.gitattributes` lines on its session branch; this repository's `.gitattributes` gets them too. (5) Coverage evidence rows hold a short summary and a link to the archived task, never scratch paths. A conflict the drivers leave goes to the Pi merge resolver as today.
- Acceptance: In fixtures, two branches that each close a different task under one goal merge with no conflict, and the result validates. Two that reprioritize the same task differently conflict only on that entry. Archive entries from both sides are kept once. A runner start registers the drivers and adds the attributes once. New coverage rows stay short.
- Checks: python3 -m unittest discover -s skills/docs-sync/scripts -p 'test_*.py'; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Docs Sync; TOOLSET-150-71 later replaces the coverage format and keeps these drivers.
- Exclusions: Generating goals.json from TODO.md is not part of this; that is the linked-store direction (TOOLSET-149-df, TOOLSET-150-71). No rewrite of existing coverage rows beyond what each close touches.
- Planner's call: merge drivers instead of generating goals.json from TODO.md. They remove the conflicts now without a format change, which TOOLSET-150-71 already plans.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-246-06"></a>

### TOOLSET-246-06 — Budget-controller fixtures bound a hang, not the host's speed: no 2-second wall-clock limits

- [x] TOOLSET-246-06 — Budget-controller fixtures bound a hang, not the host's speed: no 2-second wall-clock limits
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [budget-controller tests](skills/autowork/scripts/test_budget_controller.py) (`assert_final_observation_failure_retains_evidence` and two race cases: `self.assertLess(evidence['elapsed'], 2)` and `self.assertLess(race['elapsed'], 2)` over fixture subprocesses).
- Evidence (2026-10-18 20:32, this repository's runner, load average 21-27): main went red at 539b926 with one failure, `test_budget_controller.BudgetTests.test_final_source_read_error_fails_qualification_without_erasing_evidence`: `AssertionError: 3.0635160729289055 not less than 2`. Its isolated rerun under the same load failed the same way, so it counted as red, not flaky. Reruns of the module from the owner session at that load also failed `test_failed_race_evidence_survives_assertion_and_temp_cleanup` and `test_final_effect_read_error_fails_qualification_without_erasing_evidence`. Earlier the same day a worker reported "the unrelated budget-controller timing failure" as a reason it could not finish (TOOLSET-170-f6). The test logic held in each case; only the elapsed bound failed.
- Evidence (2026-10-18 20:31, this repository's runner): the full-suite gate held TOOLSET-165-f7, first in Now, with `the full check has new failures the base does not: test_budget_controller.BudgetTests.test_duplicate_race_records_deterministic_transaction_coordination, ...`. The base run happened to pass those tests and the isolated reruns under load did not, so a timing failure counted as the candidate's. That commit had been held at each review since 16:10 with "required offline checks are red".
- Touches: skills/autowork/scripts/test_budget_controller.py
- Scope: (1) Each `elapsed < 2` assertion becomes a bound tied to what it guards. A fixture that ends normally must finish well inside the fixture's own deadline (the deadline the test sets, or 30 s if none), which still catches a hang. A deadline-mode fixture must have been stopped by that deadline, which the events and failures already assert. (2) Any timing that remains reads the fixture's own monotonic stamps, not the test's wall clock around process start-up. (3) No skip or retry is added: the tests stay deterministic.
- Acceptance: The three named tests pass with the host loaded (for example with `AUTOWORK_GATE_CPUS=1` and a CPU-burning helper running beside them, or 8 parallel runs of the module), and still fail when the fixture is made to hang past its deadline.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_budget_controller.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator. It is the concrete fix for the current failing inventory of TOOLSET-184-b3 (MAIN recovery), whose evidence the maintainer refreshed at 20:38 for this red main; landing it should let that task record main green.
- Exclusions: No change to the budget controller itself.
- Planner's call: second in Now, after TOOLSET-165-f7 (raised 2026-10-18 20:49): these timing failures hold the top task's own candidate as well as main. A red main hides real regressions and blocks main-green signals for every candidate, and the maintainer would otherwise add a product-code repair task for a test-speed problem.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-247-5a"></a>

### TOOLSET-247-5a — A maintainer repair that leaves a task unrunnable for the same reason is not repeated; the owner gets one question

- [x] TOOLSET-247-5a — A maintainer repair that leaves a task unrunnable for the same reason is not repeated; the owner gets one question
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [maintainer](pi-autowork/pi_autowork/maintainer.py) (`due`: a run is due for any trigger set whose `key` differs from the last run's; `remember` records the set, its outcome and the changed tasks); [questions](pi-autowork/pi_autowork/questions.py).
- Evidence (2026-10-18, one fleet runner): the docs maintainer merged repairs to the same three task entries at 15:01, 15:34 and 21:14, and started a fourth run at 21:18. After each merge the three tasks were still `not runnable: ledger dependency or disposition holds execution`, holding six dependents, and the runner stayed stalled from 15:37 to 21:10. The trigger set alternated between those three tasks and the same three plus two others, so each alternation counted as a new set. Each run is a model call and rewrites the same entries.
- Evidence (2026-10-18 22:34, two more fleet runners): one merged maintainer changes to the same held task at 22:19, 22:21, 22:23 and 22:25 (four model runs in six minutes). That task waits for a live device only the owner can provide, so no doc repair could release it. Another runner merged changes to one task at 20:53, 22:08 and 22:32, with the task still held each time.
- Touches: pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_questions.py, pi-autowork/pi_autowork/coordinator.py
- Scope: (1) Due-ness is decided per trigger item, not per set. A run is due when at least one item was not yet handled, and the prompt carries only those items. (2) Each item the maintainer changed is recorded with its reason class (the waiting reason without IDs or numbers) and the entry's digest after the change. If the task is still waiting for the same reason class with that same entry, the item is not offered again. It is offered again only when someone else changes the entry or the reason changes. (3) An item excluded by (2) raises one BLOCKERS.md question. It names the task, the reason the runner gives, and the fields the maintainer already changed, so the owner decides once instead of the maintainer guessing again.
- Acceptance: In fixtures: a trigger set {A, B, C} handled and merged, followed by {A, B, C, D}, runs the maintainer for D alone; A still waiting with the same reason and the entry the maintainer left is not offered again and yields one question naming its reason; an owner edit to A's entry makes A eligible again; a changed reason does too.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_maintainer.py; python3 -m unittest discover -s pi-autowork/tests -p test_questions.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to what the maintainer may edit or to its validation of its own commits.
- Planner's call: second in Now (raised 2026-10-18 22:34: the loop runs on three runners, once every two minutes on one). A repair that does not change the runner's verdict is not progress, and repeating it spends model calls and hides the fact that the task needs an owner decision.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-243-6d"></a>

### TOOLSET-243-6d — A reviewer change re-reviews a held commit behind fresh candidates, once, and only when the change could alter its verdict

- [x] TOOLSET-243-6d — A reviewer change re-reviews a held commit behind fresh candidates, once, and only when the change could alter its verdict
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [coordinator](pi-autowork/pi_autowork/coordinator.py) (`reviewer_version` hashes all of worker.py plus two settings; `reverify_held` sends every validation-held commit back on each new version); [integration](skills/autowork/scripts/parallel_integrate.py) (`reverify` puts the slot back to `reported` with `reverified=<version>`, and `integrate` takes reported slots in plain priority order).
- Evidence (2026-10-18 19:01, this repository's runner): one candidate integrated between 12:00 and 19:00 while 14 verified candidates waited. TOOLSET-165-f7's commit `7238dc0` was re-reviewed at 16:10, 17:55 and 18:47 after toolset releases that changed worker.py for unrelated reasons (the gate's crash handling and its cache). Each time the reviewer gave the same verdict, `fail — required offline checks are red`, and each re-review took about 50 minutes. Because the task is first in Now, its re-review went ahead of every fresh candidate each time.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/worker.py, tests/test_pi_autowork.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py
- Scope: (1) The fingerprint covers only what decides a verdict: the review, live and gate prompt texts, the source of `review`, `full_suite_gate` and `run_gate`, and the settings already in it. Edits elsewhere in worker.py leave it unchanged. (2) A slot sent back by `reverify` integrates after every reported slot that was not (the priority rule treats `reverified` slots as last). Among reverified slots, the plain priority order holds. (3) A commit held again by a changed reviewer with the same verdict class (the same failure line, ignoring revision IDs) is not reverified again for that commit. It stays held for the maintainer's `review findings` trigger. A different verdict, or a new commit, resets that.
- Acceptance: In fixtures: an edit to a worker.py helper outside those functions leaves `reviewer_version` unchanged, and an edit to the review prompt changes it; a reverified slot of a high-priority task waits while a fresh lower-priority candidate integrates first; a commit held twice with the same verdict is not offered a third review when the fingerprint changes again, and one with a new verdict is.
- Checks: python3 -m unittest tests/test_pi_autowork.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the full-suite gate or to what a review checks.
- Planner's call: second in Now, behind TOOLSET-165-f7. Each toolset release re-reviewed the same failing commit ahead of the whole queue, so the runner that receives the most releases integrated the least. Ordering, scoping the fingerprint and stopping same-verdict repeats keep the benefit (a fixed reviewer gets one more look) without the stall.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-223-8e"></a>

### TOOLSET-223-8e — Integration never waits on the owner's uncommitted planning edits, and one waiting candidate never stops the rest

- [x] TOOLSET-223-8e — Integration never waits on the owner's uncommitted planning edits, and one waiting candidate never stops the rest
- Status: done 2026-10-19, landed by the owner sessions: (1)-(2) in c9243bd (planning files do not block integration; a writer-busy candidate steps aside 10 minutes) and (3) in 10d09c7 (the status line names the waiting candidate and the rest integrating). The runner's own candidate for this task duplicates that work and is set aside as closed on main.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [writer check](skills/autowork/scripts/parallel_integrate.py) (`require_no_writers`, `touches_none_of`: a session in the main checkout blocks integrating elsewhere when the merge changes a file it left uncommitted); `integrate` (`integrate the highest-priority reported task first`); [landing](pi-autowork/pi_autowork/coordinator.py) (`commit_owner_changes` commits quiet owner edits before merging, and `merge_main` keeps the branch when the main checkout cannot take it).
- Evidence (2026-10-18 13:36, this repository's runner): 8 verified candidates were waiting to integrate and status said `1 verified commit(s) wait for another session in the main checkout (runner, holds 56)`. An interactive planning session had kept TODO.md uncommitted in the main checkout for over 90 minutes while running a polling loop, so it counted as active. Three of the candidates change TODO.md and goals.json (their own Status lines), which made the session a blocker for them. Because integration takes reported tasks strictly in priority order, the first blocked candidate also held back the ones that touch no planning file.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) In `touches_none_of`, uncommitted planning files in the main checkout (TODO.md, goals.json, the TODO archive and BLOCKERS.md) do not count: integration merges in the session worktree, and the landing step already reconciles owner planning edits or keeps the branch. A planning file the session holds open for writing still counts. (2) A reported task refused with `WritersBusy` is recorded on its slot (`writers_busy_at` plus the reason). For the next 10 minutes, the highest-priority-first rule skips it, so the next reported task integrates. It goes back in its place once that time passes or the writer is gone. (3) The coordinator's status line names which candidate waits and why, and how many integrate meanwhile.
- Acceptance: In fixtures: a main checkout with an uncommitted TODO.md edit and a live session there does not stop a candidate whose merge changes TODO.md, and the later landing commits the owner's edit first; a session holding a source file the merge changes still blocks that candidate; a higher-priority candidate blocked by a writer lets a lower-priority one integrate in the same cycle, and is integrated itself after the writer leaves.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the landing step's own refusals or to how sessions are detected. A file the session holds open for writing still blocks.
- Planner's call: second in Now, after TOOLSET-221-8e. Interactive planning is the normal way the owner works, and every task's own Status edit made it block the whole integration queue.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-250-49"></a>

### TOOLSET-250-49 — A task closed on main whose set-aside must wait for a review is reported once, as closing, not each cycle

- [x] TOOLSET-250-49 — A task closed on main whose set-aside must wait for a review is reported once, as closing, not each cycle
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); TOOLSET-218-d0 in [the archive](TODO.archive.md); [integration](skills/autowork/scripts/parallel_integrate.py) (`retire_closed`: when the integration lock is held, it returns the stopped tasks as closed and sets them aside on a later cycle); [coordinator](pi-autowork/pi_autowork/coordinator.py) (`closed_on_base` results go to `note_state(task, 'closed', ...)`; `settle` notes each status row's state, so a still-slotted `reported` task reads `implemented` again).
- Evidence (2026-10-18 21:55-22:06, this repository's runner): after the owner hand-merged a verified batch and closed seven tasks on main, the runner logged 270 `<task>: done — closed on main; its worker is stopped and its work set aside` lines in 11 minutes, interleaved with as many `<task>: implemented` lines, about four cycles a minute. Its own review held the integration lock, so each cycle deferred the set-aside and reported the same tasks again, and the next status read showed their slots `reported`. The set-asides completed at 22:06, when the review ended.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, skills/autowork/scripts/parallel_status.py
- Scope: (1) `retire_closed` returns two lists: `closed_on_base` (set aside now) and `closing` (stopped, set aside when the integration lock is free). (2) The coordinator logs `<task>: closing — closed on <base>; set aside once the running review ends` once per task and the `done` line once when it is set aside. (3) A slot whose task is retired shows `closing` in status rows and TUI lanes, so `settle` never flips it back to `implemented`. (4) A cycle whose only news is deferred closings pauses the normal interval instead of cycling again at once.
- Acceptance: In a fixture with a review holding the integration lock and three tasks closed on the base, ten cycles log one `closing` line per task, no `implemented` line for them, and one `done` line each after the lock frees; the loop does not cycle faster than its interval meanwhile.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest tests/test_pi_autowork.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to when a closed task's worker is stopped or its work set aside.
- Planner's call: Now, after TOOLSET-247-5a: a fix to my own TOOLSET-218-d0. The log flood buries every other line exactly when the owner lands work by hand and reads the log to see what happened.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-258-07"></a>

### TOOLSET-258-07 — Verified candidates integrate as a batch: one merged tree, one full check, their reviews side by side

- [x] TOOLSET-258-07 — Verified candidates integrate as a batch: one merged tree, one full check, their reviews side by side
- Status: done 2026-10-19 by the owner session: (1), (3), (4) and part of (5). When two or more reported candidates wait, the runner starts `--verify-batch`: it merges them on the session in the engine's own order (contract order, without a writer-busy task), leaves a conflicting one out, runs the full-suite gate once on the result against the session head, then reviews each candidate side by side (`PI_AUTOWORK_REVIEWS`, default 3) on its own step of the chain and records the verdict per tree (`batch/<task>.json`). The engine then lands each candidate through its usual integration; `verify` reuses a recorded verdict for the same commit on a tree that differs at most in planning files, and anything else verifies as before. The session does not take main while batch verdicts wait. Not done: attributing a failing batch gate to one candidate (2); such a batch falls back to one at a time, and the same set is not batched again. The log carries the batch and its result; the TUI has no batch view yet. Checks: two runner journeys (two candidates checked once and landed from their batch; a review failure held while the other lands), a verdict-reuse case in test_worker_tmp.py; python3 scripts/check.py passed except three journeys that assumed one review at a time (fixtures now default to `PI_AUTOWORK_BATCH=1`) and one load-timed journey that passed 3 of 3 alone.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner report (2026-10-19 05:30, "stuck in implemented": nine candidates in `implemented`, the oldest for 17 h); [integration](skills/autowork/scripts/parallel_integrate.py) (`integrate` merges, validates and fast-forwards one reported task at a time under `integration.lock`); [coordinator](pi-autowork/pi_autowork/coordinator.py) (`settle` runs one review child at a time); [full-suite gate and review](pi-autowork/pi_autowork/worker.py); the owner session's hand-merged batch `5be2640` ("Merge verified batch", seven tasks); TOOLSET-231-49 (the speculative merge queue, which waits for TOOLSET-230-bf and TOOLSET-228-0c).
- Evidence (2026-10-19, this repository's runner): 6 integrations in 24 hours. A real review takes 67-70 minutes (the last two: 4154 s and 4009 s), almost all of it the gate's full suite and base run. Candidates are reviewed one at a time, so nine waiting candidates need about nine hours before holds and re-reviews. On 2026-10-18 the owner session merged a verified batch of seven by hand to clear the backlog. One waiting candidate (TOOLSET-223-8e) had already landed on main by hand and still sat in the queue.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, tests/test_pi_autowork.py
- Scope: (1) When two or more reported candidates wait, integration builds one batch tree in priority order: each candidate is merged on top of the previous one, up to `PI_AUTOWORK_BATCH` (default 6). A candidate whose merge conflicts is left out of the batch and handled as today. (2) The full-suite gate runs once on the batch tree. If it passes, every candidate in the batch has passed the gate. If it fails, the failing tests are attributed to candidates by the files their commits change and the tests' modules. Unattributed failures fall back to integrating the batch's candidates one at a time, today's path. (3) Each candidate's model review runs on the batch tree, judging its own commit's diff, up to `PI_AUTOWORK_REVIEWS` (default 3) at once, within the host's resource gate. (4) Candidates that passed the gate and their review land in order, each as its own merge commit. A candidate that fails its review is held as today, and the candidates after it are re-merged without it, with the gate rerun on the reduced tree (its cache is by tree, TOOLSET-227-a8). (5) Status and the TUI show the batch: which candidates, the gate's progress, each review.
- Acceptance: In fixtures: three reported independent candidates integrate with one full-check run (counted) and three reviews whose runs overlap in time; a candidate whose review fails is held and the other two land; a gate failure in a file only one candidate changed holds that candidate and lands the others after one more gate run; a conflicting candidate is left out of the batch; the runner journey with three slow reviews finishes in about the time of one review plus one gate.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s pi-autowork/tests -p test_worker_tmp.py; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator. A first step towards TOOLSET-231-49: batches need no ref-based integration or host check slots. When the speculative queue lands, it replaces the batch's fallback path.
- Exclusions: No weaker gate or review: every landed candidate passed the full suite on a tree containing it and its own review.
- Planner's call: first in Now (owner report, 2026-10-19). Integration is the fleet's narrowest point: one runner finishes a task in about 30 minutes and lands one about every 4 hours. Batching does what the owner session did by hand, keeps every check, and needs none of the speculative queue's prerequisites.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-251-c4"></a>

### TOOLSET-251-c4 — A conflict-held commit merged again by the resolver is adopted again when the session moved, and the resolver never runs for a merge the engine will refuse

- [x] TOOLSET-251-c4 — A conflict-held commit merged again by the resolver is adopted again when the session moved, and the resolver never runs for a merge the engine will refuse
- Status: done 2026-10-19 by the runner, merged as 69a10ef from its commit 251ae3e: (1)-(3). `merge_adoption` (parallel_state.py) records the revision a merge was adopted against and allows another adoption only once canonical HEAD advanced past it, up to 3 (`merged_count`); the coordinator runs the resolver only when the engine allows it, and a refusal names the conflicting files and the count. It replaced the blanket once-only guard of f38d6bd. Seen working on the fleet: `merged the session into its commit again (2 of 3); verifying again` on another runner at 05:52.
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [integration](skills/autowork/scripts/parallel_integrate.py) (`merged`: refuses with `merged is only for a conflict-held commit, once` when the slot already has `merged_base`); [coordinator](pi-autowork/pi_autowork/coordinator.py) (`resolve_task_conflict`: asks the Pi merge resolver once per session revision, `seen['resolved-<task>']`, then calls `--parallel-merged`); TOOLSET-157-cd and TOOLSET-233-ba in [the archive](TODO.archive.md) (the session now follows main between reviews, so it moves more often under a held commit).
- Evidence (2026-10-18 22:03-22:47, one fleet runner): two tasks on their second attempt, holding 8 dependents between them, were held for `merge conflict`. The resolver merged each, and at 22:33 the engine refused to adopt both (`could not adopt its merged commit: merged is only for a conflict-held commit, once`, logged twice each), because each slot's earlier conflict had already been adopted once. At 22:47 the runner asked the resolver to merge one of them again. The once-per-slot rule and the once-per-revision rule disagree, so each session move costs a resolver run and the tasks never leave the hold.
- Evidence (2026-10-18 23:17, a second fleet runner as well): one task there was refused the same way at 23:06 and 23:17, and one on the first runner again at 23:17: a resolver run about every ten minutes per stuck task.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) `merged_base` records the canonical revision the merge was adopted against, not just `True`. `merged` accepts another adoption when canonical HEAD has moved past that revision, up to 3 adoptions per attempt (`merged_count`). (2) The coordinator asks the engine whether an adoption would be accepted (a read-only `--parallel-merged --check`, or the same rule read from the slot) before it runs the resolver. If not, it runs no resolver and the hold stays a question for the owner, naming the conflicting files and the adoption count. (3) The log says `merged the session into its commit again (<n> of 3)`.
- Acceptance: In fixtures: a conflict-held slot adopted once, then held for conflict again after canonical HEAD moved, is adopted a second time and reaches review; with HEAD unmoved it is refused and no resolver job runs; a fourth adoption is refused with a question naming the files; the runner journey that reproduces back-to-back conflicts lands the task after two resolutions.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to how a conflict is detected or to the resolver's prompt.
- Planner's call: third in Now (raised 2026-10-18 23:19, two runners): the session moves more since TOOLSET-233-ba, so this loop will grow on every runner whose files overlap, and each turn is a model call with no progress.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-232-01"></a>

### TOOLSET-232-01 — A worker never stops for a full-check failure it did not cause: it commits, and the runner's gate judges it

- [x] TOOLSET-232-01 — A worker never stops for a full-check failure it did not cause: it commits, and the runner's gate judges it
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [worker prompt](skills/autowork/scripts/parallel_dispatch.py) (`prompt`: "a listed failure holds the task"; "blockers ... what a person must decide or provide"); [report reading](skills/autowork/scripts/parallel_integrate.py) (`verify`, `live_items`); the full-suite gate from TOOLSET-180-72 in [the archive](TODO.archive.md) (`worker.full_suite_gate` compares the merged tree with the base and reruns new failures alone); [hold handling](pi-autowork/pi_autowork/coordinator.py).
- Evidence (2026-10-18 14:52, this repository's runner, load average 36-46): TOOLSET-170-f6's worker finished the implementation and its focused checks. It left four modified files uncommitted and reported the blocker `Provide a lower-load offline validation host or a quiet validation window to rerun the required full gate without the unrelated budget-controller timing failure and resource-gated skips`. The prompt says a listed failed check holds the task, so the worker had no honest way to commit with an unrelated red test. The finished work now waits for a person, who can only answer "wait for a quieter host", which the runner could do itself.
- Evidence (2026-10-18 17:18, two more fleet runners): three finished tasks in one repository were held with `report.json ... reports failure: a check did not pass`. Two reported that `flutter test` crashed in the tool before running any test (`StateError: Bad state: No element in testCompilerBuildNativeAssets`, the same crash that made that main red); one that the whole suite ran past the 1800 s command limit at about 392 tests; one also that pytest collection stopped on a missing package (`MarkupSafe`). In another repository a review task stopped for "owner disposition" of an unrelated failing Cargo test in the full gate. None of these is the change's failure, and each costs a whole attempt or a question.
- Evidence (2026-10-18 20:10, this repository's runner): TOOLSET-173-94's worker stopped with the blocker `Provide a sufficiently quiescent offline test execution slot to complete python3 scripts/check.py tests/test_pi_autowork.py on these retained changes`.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) The prompt adds a rule. When the full gate fails only in tests the change does not touch, rerun each alone once. If it passes alone, or the same test fails on the baseline (checked in a detached `$TMPDIR` worktree, never by stashing), commit anyway. List such tests under `unrelated_failures` in the report, not as failed checks and never as blockers. Host load, resource-gate skips and flaky tests are never blockers. The same goes for a check that could not run to its results: a tool crash before any test ran, a suite stopped by the command time limit, or a missing third-party package. List these under `environment_failures` (the command and its summary), not as failed checks; the runner's gate (TOOLSET-237-35) and provisioning (TOOLSET-173-94) judge them. (2) `verify` accepts `unrelated_failures` (a list of test IDs) and `environment_failures` (a list of strings), both normalized like `pending_live`; neither holds the task. The full-suite gate still runs on the merged tree and decides; a listed test that newly fails there is held as usual. (3) A worker blocker that names only host load, a quiet window, resource-gate skips or a flaky/unrelated test, on an attempt whose worktree has uncommitted changes, is not a person's question. The runner resumes the same attempt once (as a paused attempt resumes) with a prompt line saying to commit the finished work under rule (1). A second such report holds as `timeout`, which the runner already re-verifies when the host is quieter.
- Acceptance: In fixtures: the prompt contains the rule and the field; a report with `unrelated_failures` and a commit integrates without a hold; the `load` blocker text from the evidence, with uncommitted files, resumes the same attempt once with the commit instruction and raises no BLOCKERS question; a blocker naming a missing dependency still becomes a question.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator. Coordinates with TOOLSET-227-a8: once workers stop running the full check there, rule (1) applies to the failures of the task's own `Checks:` commands, and (2)-(3) are unchanged.
- Exclusions: No skipping of the runner's own full-suite gate. Failures the change causes still fail the check and the task.
- Planner's call: third in Now, after the two integration-hold tasks (raised 2026-10-18 17:18: it held finished work in three repositories in one pass). Under the load this fleet runs at, a full gate is rarely clean, and every finished worker that obeys the current prompt turns into a question only the runner can answer. The runner's gate already separates new failures from old and flaky ones, so the worker needs no veto.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-253-0d"></a>

### TOOLSET-253-0d — The gate reuses a base run whose tree differs only in planning files, instead of running the base suite again

- [x] TOOLSET-253-0d — The gate reuses a base run whose tree differs only in planning files, instead of running the base suite again
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-19); [full-suite gate](pi-autowork/pi_autowork/worker.py) (`base_result` caches `full-check/base-<rev>.json` by exact revision); TOOLSET-233-ba in [the archive](TODO.archive.md) (the session now takes main between reviews, so its head moves often, mostly by planning commits); `PLANNING_FILES` in [integration](skills/autowork/scripts/parallel_integrate.py).
- Evidence (2026-10-19 02:57-03:58, this repository's runner): one candidate's gate took about 60 minutes. The merged-tree suite ran 29 minutes and failed some load-sensitive runner journeys. Isolated reruns took 5 minutes. Then a base suite ran 27 minutes on `c7689a5`, a `docs(blockers): questions for the owner` commit whose only change from the already-cached base `491ef4a` was BLOCKERS.md. Of the 7 consecutive base runs cached on this runner, 3 repeated a cached base whose tree differed only in planning files. Reviews here run one at a time, so each such run delays every waiting candidate by about half an hour.
- Touches: pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py
- Scope: (1) Base results are also indexed by tree, with the planning-file paths' blobs left out of the key: a tree ID computed with `PLANNING_FILES` and `docs/` removed. Two revisions with the same key share a base result. (2) `base_result` looks up that key before running the suite, and records both the exact revision and the key. (3) The same command is still required. A key match under another command runs again.
- Acceptance: In fixtures: a base cached at revision R is reused for a revision that adds only a BLOCKERS.md or TODO.md change, with no suite run (counted by a command that appends to a file); a revision that also changes a source file runs the base suite; a different check command runs it again.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_worker_tmp.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No reuse across revisions that differ in any file outside the planning set, and no change to when the base suite is needed.
- Planner's call: Now, after TOOLSET-252-4c. One review at a time is this runner's bottleneck: five verified candidates waited behind an hour-long gate. Planning-only commits cannot change test results, so their base runs are pure delay, and they are frequent because questions and closures land as planning commits between reviews.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-244-5d"></a>

### TOOLSET-244-5d — The crash line is the tool's own exit message, not an earlier warning that mentions an error

- [x] TOOLSET-244-5d — The crash line is the tool's own exit message, not an earlier warning that mentions an error
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); TOOLSET-237-35 in [the archive](TODO.archive.md); [main check](pi-autowork/pi_autowork/main_check.py) (`CRASH`, `crash_line`: the first line matching any of `exited unexpectedly`, `Segmentation fault`, `core dumped`, `Bad state`, `panic:`, `Fatal error`, `Killed`, `Aborted`, `out of memory`).
- Evidence (2026-10-18 19:05, one fleet runner): the gate held a candidate whose test tool crashed on the base and the candidate alike, as TOOLSET-237-35 intends. But the crash line it recorded was an ordinary app warning printed during the tests, `[warn][wallpaper] Set wallpaper failed {"error":"Bad state: channel unavailable"}`, because it matched `Bad state` before the tool's own `Oops; flutter has exited unexpectedly: "Bad state: No element".` further down. That wrong line went into the hold reason, the provisioning request ("installing it into the toolchain cache") and the maintainer's input. The main check of the same repository picked the right line, because its log had no such warning.
- Touches: pi-autowork/pi_autowork/main_check.py, pi-autowork/tests/test_main_check.py
- Scope: (1) Patterns are ranked. A process-ending message (`exited unexpectedly`, `Segmentation fault`, `core dumped`, `panic:`, `Fatal error`, `Killed`, a line starting with a Python exception after `Traceback`) beats a weak one (`Bad state`, `Aborted`, `out of memory`). (2) Within a rank the last matching line wins, since a crash ends the output. (3) Log-level prefixes such as `[warn]`, `[info]` and `WARNING:` never count as a crash line.
- Acceptance: In fixtures: the logged sequence (an earlier `[warn] ... Bad state: channel unavailable` line, then `Oops; flutter has exited unexpectedly: "Bad state: No element".`) yields the `Oops` line; a Python traceback yields its final exception line; a log with only a warning-level match falls back to the last non-blank line.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_main_check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to when a check counts as crashed.
- Planner's call: Now, right after TOOLSET-243-6d: a small fix to my own TOOLSET-237-35 that otherwise points provisioning and the maintainer at a harmless warning.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-222-e1"></a>

### TOOLSET-222-e1 — A runner with nothing running always gets one worker, whatever the host load

- [x] TOOLSET-222-e1 — A runner with nothing running always gets one worker, whatever the host load
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [resource gate](skills/autowork/scripts/parallel_dispatch.py) (`resource_gate`: refuses any worker while the 1-minute load average is at or above the CPU count, the same for every runner on the host); [health](pi-autowork/pi_autowork/health.py) (`blocked` when work waits and none runs).
- Evidence (2026-10-18 13:19-13:22): a small fleet runner with two runnable tasks and no worker logged `No task can start now: <task>: resource gate: load average 27.75 >= 24 CPUs` every cycle and showed `blocked` in the TUI. The load came from another runner's six workers, its review checks and a minutes-long planning call (TOOLSET-221-8e). In the last 6 hours four runners logged 1 to 10 load-gate refusals each. The first runner to start workers keeps the load high, so the others wait whatever their queues hold.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/health.py, pi-autowork/tests/test_health.py
- Scope: (1) The load-average check applies only when this runner already has a live worker (`running >= 1`). A runner's first worker is refused only by memory or disk, which still apply to every worker. (2) A wait that is only the load gate shows as `waiting for the host (load L on N CPUs)` in status and the TUI, not `blocked`, and never counts toward `stalled`.
- Acceptance: In fixtures with the load average patched above the CPU count: a runner with no live worker dispatches one task and the second waits with the load reason; a runner with one live worker dispatches nothing new; with memory below the floor, even the first worker is refused. Health reports a runner whose only waits are load-gate waits as waiting for the host, and never stalled after the stall threshold.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest discover -s pi-autowork/tests -p test_health.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the memory or disk floors, or to the load threshold for a runner's second and later workers. No cross-runner coordination file.
- Planner's call: third in Now, after the two integration-throughput tasks. One worker per runner means every repository progresses; a Pi worker mostly waits on the model, and the threshold still caps everyone's extra workers. A host-wide fair-share scheduler would need state shared between runners; this rule gets most of the benefit without it.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-224-07"></a>

### TOOLSET-224-07 — A worker's own test processes in its private temp directory are the worker's, not an outside session

- [x] TOOLSET-224-07 — A worker's own test processes in its private temp directory are the worker's, not an outside session
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [writer attribution](skills/autowork/scripts/parallel_integrate.py) (`require_no_writers`: a pool process is exempt only when every workspace it uses is the slot's worktree); [worker launch](skills/autowork/scripts/parallel_dispatch.py) (`launch`: each worker gets a private TMPDIR under `$XDG_RUNTIME_DIR/aw/<state>/<slot>/`); `scripts/check.py` (removes `AUTOWORK_*` from test processes, so the worktree marker does not reach them); TOOLSET-165-f7 (descendant attribution, implemented and waiting to integrate).
- Evidence (2026-10-18, this repository's runner): integration was refused twice with `pid <n> python3 in /var/tmp/aw161/<tmp>/state/releases/<sha> (no terminal; activity unknown)` and `pid <n> python3 in $XDG_RUNTIME_DIR/aw/<state>/16/<tmp>/state/releases/<sha> (running commands)`. Both were fixture runners that a worker's own test suite started: their working directory is a release copy inside the worker's temp directory, not its worktree. TOOLSET-165-f7 attributes descendants only when every workspace is inside the slot's worktree, so these would still block.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py
- Scope: (1) A process that descends from a live slot leader (the chain rule from TOOLSET-165-f7) is the slot's when each workspace it uses is inside the slot's worktree or the slot's private temp directory (`worker_tmpdir` for that slot, from its `meta.json`). (2) A process in a temp directory that is no live slot's own stays fail-closed, as does a non-descendant in any temp directory.
- Acceptance: In fixtures: a leader's grandchild whose cwd is inside that slot's TMPDIR does not block integration; the same process under another slot's TMPDIR, or with a dead link in its parent chain, still blocks; an unrelated process in `/var/tmp` still blocks.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 scripts/check.py
- Dependencies: TOOLSET-165-f7.
- Ownership: Toolset coordinator.
- Exclusions: No exemption by command name or by path pattern alone; descent from a live leader is required.
- Planner's call: right after TOOLSET-165-f7, which owns the descent rule; this widens only where a descendant may stand. Toolset workers run the runner's own fixtures, so without it every integration here waits while any worker tests.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-216-08"></a>

### TOOLSET-216-08 — Landing merges past someone's uncommitted planning edits, and quiet means unchanged content

- [x] TOOLSET-216-08 — Landing merges past someone's uncommitted planning edits, and quiet means unchanged content
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [owner changes and landing](pi-autowork/pi_autowork/coordinator.py) (`commit_owner_changes`, the `recent` mtime test against `PI_AUTOWORK_PLANNING_QUIET`, `merge_main`, the `Merge pending: … Your local changes … would be overwritten by merge` path).
- Evidence (2026-10-18, this repository): for about three hours the main checkout held the same uncommitted 66-line edit to `TODO.md` and a plan document from another session, yet both files were rewritten (same bytes) often enough that the runner always found them `changed in the last 10 min`. It neither committed them nor merged: `Merge pending: main … could not take pi-autowork/…: error: Your local changes to the following files would be overwritten by merge: TODO.md`, retried every cycle. Interactive sessions committed around the edit by hand: commit the merged content to `main` without touching the working file, then 3-way merge the uncommitted edit back into it.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, pi-autowork/tests/test_landing.py, CHANGELOG.md
- Scope: (1) A change counts as recent only while its content changes: the runner records each uncommitted file's content hash with the time it first saw it, and the quiet interval runs from the last content change, not from the file's modification time. (2) When `main` cannot take the session because files it changes hold uncommitted edits, the runner lands without the working tree: it builds the merge commit in the index of a temporary index file (or `git merge-tree`), moves `main` to it with a compare-and-swap on the ref, then for each dirty file 3-way merges the uncommitted edit (base: the old `HEAD` blob, theirs: the working file) onto the new blob and writes the result to the working file only when the merge is clean and the working file is unchanged since it was read. The uncommitted edit stays uncommitted. (3) A conflicting edit, a file open for writing, or a working file that changed meanwhile leaves `main` where it was and keeps today's `Merge pending` wait, naming the file and the reason.
- Acceptance: In fixtures, a main checkout with an uncommitted edit to `TODO.md` in a different section than the session's change lands the session: `main` has the session's change, the working `TODO.md` has both, and `git diff` still shows only the uncommitted edit. An edit rewritten with identical bytes every minute counts as quiet after the interval. A conflicting edit, or a working file changed between read and write, lands nothing and keeps the edit byte for byte.
- Checks: python3 scripts/check.py tests/test_pi_autowork.py pi-autowork/tests/test_landing.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator. Runs after TOOLSET-197-4f, which edits coordinator.py.
- Exclusions: No stash, reset or checkout of someone else's edit; no change to what is auto-committed or to the secret-file rule; no landing while a merge, rebase or cherry-pick is in progress.
- Planner's call: the owner's direction (2026-10-18, "manage this better") is that a parked edit must not hold finished work; landing around it with a clean 3-way merge keeps the edit and its owner undisturbed, while a conflict still waits for a person.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-217-2d"></a>

### TOOLSET-217-2d — /autowork update also refreshes this host's other installs through install.sh

- [x] TOOLSET-217-2d — /autowork update also refreshes this host's other installs through install.sh
- Status: done
- Goal: PORTABLE
- Payoff: Align portable workflow discovery.
- Sources: [updater](update_bundle.py) (`main`, the receipt), [install entry point](install.sh) and [its menu](scripts/install_menu.py) (items `pi`, `autowork`, `tx`, `hermes`, `claude`, `codex`; `--only`, `--skip`, `--dry-run`; tx "keeps your existing ~/.tmux.conf"), [chat summary](bundle.py) (`summarize_update`).
- Evidence (2026-10-18, this host): after `/autowork update` brought every Hermes profile to the latest release, the host's other installs stayed behind (the Claude Code plugin cache still held release 0.3.0 of the workflows); only the runners update themselves. The owner: "autowork update must also update host by running install.sh".
- Touches: update_bundle.py, tests/test_update_bundle.py, bundle.py, tests/test_bundle.py, scripts/install_menu.py, tests/test_install_menu.py, docs/installation.md, CHANGELOG.md
- Scope: (1) After the profiles are updated and activated, a non-check update runs the fetched release's `install.sh --full --skip hermes,pi -q` from the updated plugin checkout: Hermes was just updated by this run, and the runners update the Pi package themselves only while no work is in flight. (2) It is best effort and bounded (a timeout per run): a host item that fails or is unavailable is recorded per item in the receipt (`hosts`: item, status, exit) and in the chat summary as one line, and never fails or rolls back the Hermes update. (3) It never overwrites a user's own dotfiles: before shipping, verify with `--dry-run` and a fixture home that no item replaces an existing `~/.tmux.conf` or other user config, and keep `~/.local/bin` replacements behind the existing `.bak` rule. (4) An update with nothing new (`up_to_date`) skips the host refresh, so a rerun stays a no-op.
- Acceptance: In fixtures with a fake `install.sh`, an update that changed the release runs it once with `--full --skip hermes,pi`, records each item's outcome, and still reports the Hermes update `updated` when an item fails; an `up_to_date` rerun does not run it; `--check` never runs it. A fixture home with an existing `~/.tmux.conf` keeps it byte for byte after a real `install.sh --only tx` run.
- Checks: python3 scripts/check.py tests/test_update_bundle.py tests/test_bundle.py tests/test_install_menu.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to how runners update the Pi package; no `install.sh` run from `--check`, from a scoped profile update or from a pinned profile; no privilege escalation (host prompts that need a person stay skipped and reported).
- Planner's call: the release's own `install.sh` is the one supported way each host installs, so the update reuses it rather than calling host CLIs itself; `hermes` and `pi` are skipped because this run and the runners already own them. Placed in Now (owner, 2026-10-18).


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-219-2c"></a>

### TOOLSET-219-2c — A planning task runs in the maintainer and saves the next batch, until its goal is met

- [x] TOOLSET-219-2c — A planning task runs in the maintainer and saves the next batch, until its goal is met
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [accepted rolling planning design](docs/plans/2026-10-18-rolling-planning.md#rolling-planning-design), [docs maintainer](pi-autowork/pi_autowork/maintainer.py) (`triggers`, `prompt`, `planning_only`, `LIMIT`), [runner](pi-autowork/pi_autowork/coordinator.py) (the maintainer run and its planning landing), [coordinator files](skills/autowork/scripts/parallel_dispatch.py) (`COORDINATOR_FILES`, which a code worker may not change), [plan protocol](skills/plan-for-me/SKILL.md).
- Evidence (2026-10-18, owner): a large request such as porting a project to Flutter should plan, build, then plan the next batch from what the first one found, "like a goal tool". Today a plan saves one batch; once it is done the queue is empty although the goal is not met, and no worker may write `TODO.md` or `goals.json` to plan more.
- Touches: pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, docs/reference.md, CHANGELOG.md
- Scope: (1) The engine never dispatches a task with `Kind: plan` to a code worker; once its dependencies are done it reports it as ready for planning. (2) The runner adds such a task to the maintainer's triggers as `plan` and the maintainer runs Plan For Me on the entry's scope with the finished batch's evidence (reports, code, the goal's remaining proof), saves at most 8 new tasks under the entry's goal, puts owner-only gaps in `Needs decision` with their question, closes the planning task, and lands all of it in one planning commit. (3) While the goal is not met it ends the new batch with the next planning task, `Kind: plan`, `Plan round: N+1 of M`, depending on the new batch. (4) At round M, or when a round adds no building task, it saves no further planning task and writes one `BLOCKERS.md` question naming the goal and what is left. (5) Planning tasks run one at a time per repository.
- Acceptance: In fixtures, a `Kind: plan` task with done dependencies is never given a worktree; the maintainer's planning commit adds the new tasks, closes the planning task and adds `Plan round: 2 of 10` on the next one, which depends on every new building task; at `Plan round: 10 of 10`, and in a round that adds only `Needs decision` items, no planning task is added and one question is written; more than 8 proposed tasks are refused as a planning failure, not truncated. A repository without planning tasks behaves as today.
- Checks: python3 scripts/check.py pi-autowork/tests/test_maintainer.py tests/test_pi_autowork.py skills/autowork/scripts/test_parallel_dispatch.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator. Runs after TOOLSET-197-4f, which edits maintainer.py and coordinator.py.
- Exclusions: No code worker gains write access to coordinator files; no new `goals.json` schema; no planning without a `Kind: plan` entry (the maintainer's existing triggers are unchanged).
- Planner's call: as recorded in the [design](docs/plans/2026-10-18-rolling-planning.md#rolling-planning-design): the maintainer runs planning tasks, the chain is a dependency, and the limits (10 rounds, 8 tasks a round) are defaults.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-226-d3"></a>

### TOOLSET-226-d3 — Dispatch pauses while finished commits wait to merge, and resumes when the queue drains

- [x] TOOLSET-226-d3 — Dispatch pauses while finished commits wait to merge, and resumes when the queue drains
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [admission](skills/autowork/scripts/parallel_dispatch.py) (`admit`, `dispatch_locked`, `OCCUPYING`, `drain_after`), [wait labels](pi-autowork/pi_autowork/health.py) (`WAIT_KINDS`), [integration writer guard](skills/autowork/scripts/parallel_integrate.py) (`WritersBusy`).
- Evidence (2026-10-18, this repository): 8 verified commits waited to merge for over half an hour while the runner kept starting workers. Each integration attempt stopped on `waiting to integrate until another session leaves the main checkout`, the "other session" being a test process of one of the runner's own workers (TOOLSET-165-f7 and TOOLSET-195-ee fix that attribution), and with 4 workers testing at once the quiet windows integration needs were rare. The owner lowered the runner to 1 worker by hand and asked for "a more sustainable future proof solution".
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/health.py, pi-autowork/tests/test_health.py, docs/reference.md, CHANGELOG.md
- Scope: (1) When at least `PI_AUTOWORK_MERGE_BACKLOG` verified commits (slots `reported` or `integrating`, default 3) are waiting and the oldest has waited `PI_AUTOWORK_MERGE_BACKLOG_AFTER` seconds (default 1200), admission starts no fresh task; restartable and interrupted work and running workers continue. (2) It resumes on its own once the waiting commits fall below the threshold; no setting is changed and no person is needed. (3) Waiting tasks show `wait for N finished commits to merge` (a wait, not a question), and the runner logs the pause and the resume once each, naming what holds integration if the integration step reported it.
- Acceptance: In fixtures, 3 commits waiting 21 minutes stop fresh dispatch while a restartable task still resumes; 2 waiting, or 3 waiting 5 minutes, dispatch as today; after one integrates below the threshold, the next cycle dispatches again. The pause appears in the wait summary with that label and in the log once, and `PI_AUTOWORK_MERGE_BACKLOG=0` turns it off.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_dispatch.py pi-autowork/tests/test_health.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to how integration attributes writers (TOOLSET-165-f7, TOOLSET-195-ee) or to the worker count setting; nothing is stopped or killed.
- Planner's call: back-pressure in admission is the general form of the owner's manual fix: work that is finished but unmerged is the costliest to keep waiting, so the pool stops adding more until it merges. The thresholds are defaults; 0 turns the pause off.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-228-0c"></a>

### TOOLSET-228-0c — Full checks from every runner on the host share a few check slots

- [x] TOOLSET-228-0c — Full checks from every runner on the host share a few check slots
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [check runner](scripts/check.py) (`default_jobs`, load-adaptive jobs), [main check](pi-autowork/pi_autowork/main_check.py), [full-suite gate](pi-autowork/pi_autowork/worker.py) (`run_suite`), [resource gate](skills/autowork/scripts/parallel_dispatch.py) (`resource_gate`).
- Evidence (2026-10-18, this repository, the last 48 hours: worker runs took a median 33 minutes (p75 51); in two logged attempts test commands took 38 of 44 and 26 of 32 minutes; a full `scripts/check.py` took 7 to 10 minutes at a host load average of 24 to 27. One candidate's full check ran 4 to 5 times: 2 or 3 times by its worker, once by the full-suite gate on the merged tree, and again by the model reviewer, which polled its own background run every 90 s. 15 of 26 integrations ended held and 15 of 25 check receipts failed or timed out, many on the environment. Eight runners on one host each start main checks, gates and worker checks independently, so several full suites compete for the same cores and each runs slower and times out more.)
- Touches: pi-autowork/pi_autowork/worker.py, pi-autowork/pi_autowork/main_check.py, pi-autowork/tests/test_main_check.py, pi-autowork/tests/test_worker_tmp.py, docs/reference.md, CHANGELOG.md
- Scope: (1) A full check the runner starts (main check, merged-tree gate, base run) first takes one of `PI_AUTOWORK_CHECK_SLOTS` host-wide slots (default: CPU count divided by 8, at least 1), held as an `flock` on a file under the user's runtime directory shared by every runner. (2) Its timeout counts from when it got the slot; time spent waiting is reported (`waiting for a check slot, N ahead`) and is not a failure. (3) A slot is released when the check ends or its process dies (the lock goes with the file descriptor), so a killed check never holds one.
- Acceptance: In fixtures with 1 slot, a second full check waits until the first ends, then runs with its full timeout; a killed holder frees the slot; waiting shows in status. With the setting at 0 the slots are off and checks start at once as today.
- Checks: python3 scripts/check.py pi-autowork/tests/test_main_check.py pi-autowork/tests/test_worker_tmp.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator. Coordinates with TOOLSET-118-68 (worker and test budgets in the resource gate), which it does not replace.
- Exclusions: No slot for a worker's focused checks; no change to `scripts/check.py`'s own job count.
- Planner's call: a few full suites at full speed finish sooner and fail less than many at once on a saturated host; an `flock` slot needs no daemon and frees itself when its holder dies.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-201-5e"></a>

### TOOLSET-201-5e — An idle runner keeps its session instead of recreating it every interval

- [x] TOOLSET-201-5e — An idle runner keeps its session instead of recreating it every interval
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [engine graph review](docs/plans/2026-10-17-engine-graph-review.md#engine-graph-review-findings) (finding 3); [coordinator](pi-autowork/pi_autowork/coordinator.py) (the `IDLE` branch of the cycle calls `merge_main`, `--release` and `end_session`; the next cycle's `ensure_session` creates a new one).
- Evidence (2026-10-17 23:26-23:28, one fleet runner on the current release): `Session pi-autowork/20261017-232646 started from master`, `Queue empty`, then a new session at 23:27:52 and 23:28:54. Each interval adds a worktree, a branch and engine calls for nothing.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) On an empty queue the runner lands what the session has, then keeps the session worktree and branch and follows main in place; it ends the session only on a stop, a session older than a day with nothing ahead, or a session it cannot follow (a conflict the resolver cannot fix). (2) An idle cycle that finds main unchanged makes no git writes; its engine calls are the dispatch check and the `--release` it makes today, which stays, so an interactive `owner_cycle.py` or `worktree_closeout.py` run between intervals still finds the coordinator lease free. (3) `Session … started` is logged only when a session is actually created.
- Acceptance: In a fixture with an empty queue, ten intervals create one session, log one `Session … started` line and leave the same worktree; a task added to main afterwards dispatches from that session; a stop still ends a clean, merged session as today.
- Checks: python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to landing, pushing or what a stop does.
- Planner's call: keep and follow the idle session rather than remove it lazily, because following main is already the session's normal state while nothing runs.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-241-a1"></a>

### TOOLSET-241-a1 — A task that fails the same way within minutes stops and asks, instead of rerunning

- [x] TOOLSET-241-a1 — A task that fails the same way within minutes stops and asks, instead of rerunning
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [set-aside and rerun on an entry change](skills/autowork/scripts/parallel_integrate.py) (`set_aside`, `_retire`, `entry_changed`), [held-task questions](pi-autowork/pi_autowork/questions.py) (`exhausted`, `build`), [docs maintainer](pi-autowork/pi_autowork/maintainer.py) (`triggers`).
- Evidence (2026-10-17 to 2026-10-18, a fleet runner): one task was set aside and run fresh ten times; each attempt held within a minute with the same blocker (a required input that nothing produces), each rerun started by an edit to its entry.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_questions.py, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, CHANGELOG.md
- Scope: (1) The runner records each attempt's held reason and how long it ran. (2) After 3 attempts in a row that held within 10 minutes with the same blocker (the same reason after normalizing paths and identifiers), an entry change no longer reruns the task: it stays held with one question naming the blocker, the attempts and their times. (3) The maintainer gets that task as a trigger once, to restate it so the missing input is produced (a task or dependency for it) or to move it to `Needs decision`; only an entry change that addresses the named blocker reruns it.
- Acceptance: In fixtures, three one-minute holds with the same blocker stop the reruns and write one question; a different blocker, or an attempt that ran longer than the limit, keeps today's behavior; the maintainer is triggered once for it.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py pi-autowork/tests/test_questions.py pi-autowork/tests/test_maintainer.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to attempt budgets for tasks that ran and failed on their work.
- Planner's call: three quick identical holds are evidence the task cannot start as written; rerunning it spends a worker and a review each time and teaches nothing.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-240-f8"></a>

Disposition: Superseded; not completed
Successors: TOOLSET-234-d4
Reason: Duplicate of 234-d4: both hand the main-check evidence to repair workers; 240-f8's update-the-existing-evidence step is folded into 234-d4.
Original task and unchecked acceptance retained below.

### TOOLSET-240-f8 — A repair task for a red main gets the runner's main-check log and its failing tests

- [ ] TOOLSET-240-f8 — A repair task for a red main gets the runner's main-check log and its failing tests
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [main check](pi-autowork/pi_autowork/main_check.py) (the receipt and `main-check.log` in the runner state), [docs maintainer](pi-autowork/pi_autowork/maintainer.py) (the `MAIN` trigger that writes repair tasks), [worker prompt](skills/autowork/scripts/parallel_dispatch.py) (`prompt`).
- Evidence (2026-10-18, a fleet runner): two repair tasks for a red main held at once, asking for "the full log of the red MAIN, with exit code, failing phase/test and attempt classification" and "the original MAIN run report"; the runner keeps both in its state directory, but nothing gives them to the worker or the repair task.
- Touches: pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/main_check.py, pi-autowork/tests/test_main_check.py, CHANGELOG.md
- Scope: (1) When the maintainer writes or updates a task for a red main, the task's Sources name the failing revision, the command, the exit code, the failing tests and the log's path, and the runner copies that log and receipt into the task's evidence folder (`.git/autowork-execution/slot-data/<task>/evidence/`), kept until the task closes. (2) The worker prompt of such a task names that folder. (3) A later red main on the same tests updates the same evidence instead of writing another task.
- Acceptance: In fixtures, a red main produces a repair task whose Sources carry the revision, command, exit code and failing tests; its worker's prompt names the evidence folder holding the log and receipt; a second red main on the same tests updates that folder; the evidence goes when the task closes.
- Checks: python3 scripts/check.py pi-autowork/tests/test_maintainer.py pi-autowork/tests/test_main_check.py skills/autowork/scripts/test_parallel_dispatch.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to when main counts as red.
- Planner's call: the runner owns the main check, so it hands over its own evidence; a worker should never have to ask for a log the runner holds (owner, 2026-10-18: autowork "must be able to fix these issues easily").


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-170-f6"></a>

Disposition: Superseded; not completed
Successors: TOOLSET-230-bf
Reason: 230-bf removes the closeout writer check whose message 170-f6 refines; the session-and-file wording moves to 230-bf's main-checkout landing.
Original task and unchecked acceptance retained below.

### TOOLSET-170-f6 — Closeout waits only for a main-checkout session that holds the files it writes

- [ ] TOOLSET-170-f6 — Closeout waits only for a main-checkout session that holds the files it writes
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: owner direction (2026-10-17): "plan a task so interactive sessions don't block closeout"; [close and writer checks](skills/autowork/scripts/parallel_integrate.py) (`close`, `_close_writes`, `live_followup`, `require_no_writers`, `touches_none_of`), [coordinator closeout](pi-autowork/pi_autowork/coordinator.py) (`close_task`); the main-checkout session rule of TOOLSET-120-fc (6).
- Evidence (2026-10-17 12:46-12:55, this repository's runner): an integrated TOOLSET-124-97 failed every minute with `could not close: live or unknown external writer/session; preserve canonical checkout: pid … claude in <repo> (running commands); pid … claude in <repo>`. Both were interactive sessions in the main checkout, which owner direction says is where interactive work happens. `close`, `_close_writes` and `live_followup` call `require_no_writers(repo)` without `files`, so `touches_none_of` returns False and any main-checkout session blocks, although integration already passes the files a merge changes and lets unrelated sessions proceed. The runner showed `paused` while 31 tasks waited.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/references/parallel-workers.md, tests/test_pi_autowork.py
- Scope: (1) `close`, `_close_writes` and `live_followup` pass the exact files the close writes (`TODO.md`, `goals.json` when indexed, the archive file) to `require_no_writers`, so a session only in the main checkout blocks closeout only when it holds one of them open or has left one uncommitted there, the rule integration already uses. Sessions outside the main checkout, unknown writers and Autowork commands block as today. (2) When a session does block, the reason names the session and the file (`waiting to close until <session> commits or closes <file>`), so the owner knows what to do. (3) The closeout commit and its landing on main keep the existing final-merge rule, which already waits only for files a session touches.
- Acceptance: In fixtures, an integrated task closes and its close commit lands while an idle interactive session is in the main checkout with unrelated uncommitted files. The same session with `TODO.md` uncommitted, or with the archive open for writing, keeps the close waiting with the new reason naming that file. A session in a sibling worktree and an unknown writer still block. No close is retried more than once per cycle.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator; reconcile TOOLSET-165-f7 output in the same writer check first.
- Exclusions: No relaxation for sessions holding a planning file, no closeout in the canonical checkout while it is being written, no change to integration's file rule.
- Done by the owner session (2026-10-17, 14a7d11 and the commit after it): scope (1). `close`, `_close_writes` (both the indexed and the unindexed paths), `live_followup` and worktree cleanup pass the files a close writes, with a fixture that has goals.json; (3) needed no change. Still open: (2), the waiting reason naming the session and file.
- Planner's call: second in Now, behind TOOLSET-165-f7, which changes the same writer check. Interactive sessions belong in the main checkout, so closeout must not depend on their absence.
- Blocker reconciliation: The latest retained four-file implementation reports passing focused integration and runner checks, but the full offline inventory failed a budget-controller less-than-two-second timing assertion at 2.510591 seconds under load 50.91; four host-resource skips and the failed full run remain unqualified evidence, not passes. A quiet host is a technical capacity condition, not a new owner decision or permission to bypass tests. Use existing completion-first/check-slot admission and supported disk-backed short scratch; do not ask the owner to stop other runners or provide another host before using the normal resource gate. Do not stabilize an unrelated budget-controller test inside this task's scope or classify the timing failure as proven flaky from one run.
- Next action: Preserve the existing four modified files and review notes in the held worktree; reconcile current TOOLSET-165-f7/current-baseline writer logic without another implementation. When the existing qualification owner has capacity under the normal guards, rerun only invalidated/missing checks and the mandatory full gate on the actual integrated source, using the current supported disk-backed task scratch and shared check-slot mechanism where delivered. Waiting for capacity is not a failed attempt or a reason to reset cumulative budgets; it must not launch duplicate inventory while another qualification is owned. If the same budget test still fails on a suitable current baseline, retain its actual result and route repair to the existing baseline/test owner, not a longer-sleep workaround, changed expected result or a waived full gate. Close only from accepted integrated verification; no check, retry or service action is launched by this planning answer.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-115-bf"></a>

Disposition: Superseded; not completed
Successors: TOOLSET-230-bf, TOOLSET-254-80, TOOLSET-255-55, TOOLSET-256-4b, TOOLSET-257-bd
Reason: A catch-all redesign written against coordinator code main has since redesigned; its Touches serialized all coordinator work. Its remaining scope is covered by the named tasks.
Original task and unchecked acceptance retained below.

### TOOLSET-115-bf — Redesign pi-autowork around one lifecycle authority

- [ ] TOOLSET-115-bf — Redesign pi-autowork around one lifecycle authority
- Status: open
- Partial delivery: phases 1-5 done offline (report outcomes, Git safety, health, owner decisions, component port); live fleet qualification remains with TOOLSET-096-7e.
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [design](docs/plans/2026-10-16-pi-autowork-coordinator.md), [engine](skills/autowork/references/parallel-workers.md).; [completion-first delivery](docs/plans/2026-10-16-pi-autowork-coordinator.md#completion-first-delivery-and-recoverable-handoffs).
- Touches: scripts/pi-autowork.sh, scripts/pi_autowork_touches.py, pi-autowork/, package.json, scripts/check.py, skills/autowork/scripts/parallel_*.py, skills/autowork/scripts/task_execution.py, skills/autowork/scripts/test_parallel_*.py, skills/autowork/references/parallel-workers.md, tests/test_pi_autowork.py, docs/cross-host.md, docs/plans/2026-10-16-pi-autowork-coordinator.md
- Scope: Owner direction (2026-10-16, after four runners idled seven hours): stop special-casing stalls in Bash. Implement the design's invariants in phases: worker outcomes from reports (`blockers` defer, `pending_live` never holds); Git safety (disposable review and Touches worktrees, exact closure commits); health (`status.json`, one `STALLED` report); owner decisions (safe-checkpoint self-update with a state schema version, adoption of verifiably idle claims, linked ignored dependencies); deferred causes with automatic actions; a tested Python coordinator behind a thin `pi-autowork.sh`.
- Acceptance: The design's twelve scenarios pass with controlled subprocess workers and failure injection; no runner path runs `reset --hard`, `clean` or `stash` on the session or canonical checkout; a runner with no worker while runnable work exists reports `STALLED` with root blockers.
- Checks: python3 scripts/check.py tests/test_pi_autowork.py; python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py skills/autowork/scripts/test_parallel_state.py skills/autowork/scripts/test_parallel_dispatch.py skills/autowork/scripts/test_parallel_integrate.py skills/autowork/scripts/test_parallel_adversarial.py; python3 scripts/check.py; shellcheck scripts/pi-autowork.sh
- Dependencies: None.
- Context: Builds on TOOLSET-099-87 offline work.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No push by the runner; no direct edits in fleet repositories; live fleet qualification stays with TOOLSET-096-7e.
- Added (2026-10-17, [engine graph review](docs/plans/2026-10-17-engine-graph-review.md#engine-graph-review-findings) finding 5): `coordinator.py` is one 1805-line class with about 15 separate engine call sites; `task_execution`, `parallel_dispatch`, `parallel_claims`, `parallel_integrate`, `parallel_state`, `parallel_status` and `worktree_closeout` import each other in one cycle; `git()` is defined in 9 modules. Address them in this redesign, not as separate refactors.
- Completion handoff: Implement the cited finish-line refinements in the existing engine/coordinator, preserving phases already delivered. Use validated terminal/report/attempt/commit and process-birth evidence for one adoption; distinguish report awaiting exit/adoption from active implementation. Reconcile effective contract changes against retained candidates instead of blindly restarting for informational edits. Resume unfinished review/integration/canonical-closeout steps idempotently after interruption; preserve actual failures, attempts, budgets and live ownership. Existing TOOLSET-119-2b retains atomic creation/transition intent; no competing store or lifecycle authority.
- Qualification refinement: Pin exact integrated source, command/inventory, relevant dependency/tool/environment closure and effective review policy at launch. Reuse valid execution evidence only while all those inputs match; rerun invalidated checks and mandatory review, never qualify a new integration from old worker/main-green results. Keep running review identity across polling/restart and record a real invalidation separately from a new invocation. Preserve current worker/reviewer contracts and cumulative retry limits; a relevant changed policy cannot be hidden by a stale digest.
- Completion proof: Extend the existing engine/adversarial/runner journeys with report-before-exit, exit-before-report, missing report, duplicate polls, restart at each boundary, candidate drift, dead/reused identity, note-only versus real contract change, same versus changed qualification inputs, and publication-disabled canonical delivery. Assert one implementation/adoption/delivery for the same proven candidate, no duplicate review while one is owned, and honest failure/incomplete states. New cases are unrun; all original twelve scenarios and full offline/review requirements remain binding.
- Next action: Reconcile the current delivered engine and retained reports first; implement the narrow remaining terminal/report adoption and resumable qualification/closeout boundaries at existing seams, not phases 1-5 again. Make one source-bound snapshot available to 130-15 and completion occupancy to 118-68. Preserve active owners, current ordering and publication exclusions.
- Delivery evidence boundary: Existing engine reported state is candidate discovery, not validated report acceptance; preserve that split and dirty residue. Reuse integration and closeout receipts, retaining reviewed merge/integration/closeout identities and the configured canonical ref/observed head. Require accepted integration and closeout ancestry on that ref plus source-bound qualification before canonical Delivered; remote publication additionally needs authorized remote-ref readback. Keep baseline-equivalent/flaky/full-inventory exceptions explicit under existing policy, never call an exception-accepted run all green or erase its original failed/skipped results.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-128-89"></a>

Disposition: Superseded; not completed
Successors: TOOLSET-158-08
Reason: Duplicate of 158-08 (fetch, merge the upstream, resolver once per revision, never force-push); its no-runner-push evidence is obsolete since the runner pushes (ef85685). The PI_AUTOWORK_PUSH_BATCH log line moves into 158-08.
Original task and unchecked acceptance retained below.

### TOOLSET-128-89 — First push of a long-local or diverged main

- [ ] TOOLSET-128-89 — First push of a long-local or diverged main
- Status: open
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: owner request (2026-10-17: audit runners' .worktrees use and merging after each task, then plan improvements), [plan](docs/plans/2026-10-17-runner-landing-and-worktrees.md), audit finding 5.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, docs/cross-host.md
- Scope: Mains are 39–72 commits ahead of origin and bravo's has diverged (5 ahead, 19 behind); no runner push has run yet. `push` handles a diverged upstream: fetch, merge the upstream into the session (the Pi merge resolver once per upstream revision on a conflict), land, push once more; a push still rejected becomes a runner blocker and a TOOLSET-125-3c landing question, never a force push. A push that would publish more than `PI_AUTOWORK_PUSH_BATCH` commits (default 200) still runs but logs the count once.
- Acceptance: fixtures with a bare upstream: a main many commits ahead pushes in one step; a diverged upstream with a clean merge is merged, landed and pushed; a conflicting upstream asks the resolver once and, if still conflicting, leaves main local with a runner blocker and no force push.
- Checks: `python3 -m unittest discover -s tests -p 'test_pi_autowork.py' -k push`; `python3 scripts/check.py`.
- Dependencies: None.
- Ownership: Toolset coordinator under the owner's request (2026-10-17).
- Exclusions: No edits to the runner log output or the TUI log view (ht2, 2026-10-17), nor to `update_toolset`/`release.py`; no force push; never delete uncommitted or unpushed work.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-214-5b"></a>

### TOOLSET-214-5b — A deferred dependency asks nothing, and only owner questions read as Waiting on you

- [x] TOOLSET-214-5b — A deferred dependency asks nothing, and only owner questions read as Waiting on you
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [runner questions](pi-autowork/pi_autowork/questions.py) (`build`, the `outside` branch), [headline](pi-autowork/pi_autowork/fleet_view.py) (`Waiting on you — …`), [wait summary](pi-autowork/pi_autowork/health.py) (`WAIT_KINDS`, `describe`), [blockers protocol](skills/blockers/SKILL.md) (the runner-recognized resolutions and the owner report).
- Evidence (2026-10-18, a fleet runner): `/blockers` reported 0 owner decisions while the runner's headline said `Waiting on you — 5 questions`. The questions that remained were dependencies on two tasks the owner had already deferred to `Needs decision`; the runner asks about such a dependency every cycle, because nothing an answer records removes the question except dropping the dependency. The same view listed 5 tasks as waiting for another task's files after that task was done. The owner read every hold as theirs.
- Touches: pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_questions.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/tests/test_fleet_view.py, pi-autowork/pi_autowork/health.py, pi-autowork/tests/test_health.py
- Scope: (1) `questions.build` asks nothing for an `outside` root that is a task in TODO.md's `Needs decision` section with a dated `Owner decision:` line: the owner deferred it, and its dependents wait with it. (2) Those dependents show in status and the TUI as waiting on the deferred task (`wait for deferred <ID>`), a wait, not a question. (3) The headline says `Waiting on you` only when the questions block holds a question; with none, a held or waiting queue reads `Waiting — <cause>` (deferred task, overlapping files, dependencies), never "on you". (4) A wait summary never names a task as holding files once that task is done or integrated in the runner's session; find why the stale entry appeared and fix that source.
- Acceptance: In fixtures, an `outside` root on a `Needs decision` task with a dated `Owner decision:` line yields no question, and the same root without that line yields today's question. With an empty questions block and tasks waiting on a deferred task or on overlapping files, the headline does not contain `on you` and names the cause. A task done in the session is not named in any `wait for … (overlapping files)` group. Existing question, claim (`Held by:`) and live-authorization fixtures keep passing unchanged.
- Checks: python3 scripts/check.py pi-autowork/tests/test_questions.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_health.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator. Runs after TOOLSET-197-4f, which edits questions.py.
- Exclusions: No new question kinds and no model call; held, claim, cycle, contract and live-authorization questions keep their rules. No change to the blockers protocol beyond keeping its runner-recognized forms in step with this rule.
- Planner's call: the owner's deferral is the answer, recorded where the queue already reads it (`Needs decision` plus a dated `Owner decision:` line), so no separate answer field is needed. Placed in Now (owner, 2026-10-18: "blockers skill is weak and misleading").


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-268-7a"></a>

### TOOLSET-268-7a — Chat status shows repository runners separately from plugin setup

- [x] TOOLSET-268-7a — Chat status shows repository runners separately from plugin setup
- Status: done
- Goal: PI-RUNNER
- Sources: [accepted continuous runner](docs/project.md#continuous-pi-runner-2026-10-15); [chat status contract](docs/reference.md#chat-autowork-status-list-and-update); owner request (2026-10-19): add repository status instead of only setup health.
- Touches: bundle.py, __init__.py, tests/test_bundle.py, tests/test_bundle_repo_status.py, pi-autowork/pi_autowork/cli.py, pi-autowork/pi_autowork/release.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/pi_autowork/command.py, tests/test_autowork_command.py, pi-autowork/tests/test_release.py, README.md, docs/reference.md, docs/workflows.md, docs/troubleshooting.md, docs/testing.md, CHANGELOG.md
- Scope: Bare /autowork status reads the runner fleet; status NAME or a quoted absolute repository path reads that runner; plugin status retains the former setup overview. No model invocation, guessed gateway repository, lifecycle command or installation. Use literal argv and this bundle's status reader; status cannot initialize or prune release worktrees. Failed discovery, unknown engine reads and empty/failed/timed-out outer reads remain unavailable, never healthy zero-worker results. Preserve workflow prose routing and all update/list/blocker behavior. Bound and fence chat output without enabling file attachments.
- Acceptance: Offline dispatcher/native regression cases cover fleet/named/quoted targets, flags/relative paths/malformed quotes, outer failures, strict native discovery failure versus genuine empty fleet, unknown engine reads, inherited older launcher pins, release-worktree preservation, bounded Unicode/fence-safe output and retained plugin diagnostics. Real read-only source-handler smoke returns host fleet and named runner state. Existing native/workflow command regressions and the required full offline gate pass on the exact candidate. Source implementation is separate from installed gateway activation or Telegram delivery; no such live acceptance is inferred.
- Checks: python3 scripts/check.py tests/test_bundle.py tests/test_bundle_repo_status.py tests/test_autowork_command.py tests/test_workflow_commands.py pi-autowork/tests/test_release.py pi-autowork/tests/test_fleet_view.py; python3 scripts/check.py; git diff --check. Offline fixtures use fake services/providers; a source-handler read uses existing local runner records without changing services/profiles/jobs.
- Dependencies: None.
- Ownership: Interactive Autowork implementation owner; preserve other workers' code and the existing execution lease. No competing worker is launched.
- Qualification: Source implementation is complete. The six-module focused native/bundle/workflow union passed; the complete offline entry point passed on reviewed source snapshot 3667c78722254a0082c69c10d6a09fd445c39035 (five test directories, zero failed, eight excluded modules). The native authentication regression went RED with primary/fallback checks and GREEN with no auth checks. Independent final source review found no remaining issues. A source-handler smoke returned fleet and named runner output with unchanged parent environment. Excluded native/integration modules, installed gateway activation and Telegram delivery are not qualified.
- Next action: No source reimplementation remains. Installed gateway activation and chat qualification stay separate under the existing authorized installation/live follow-up; preserve all pauses, settings and profile boundaries. No push, install or restart is included in this source closeout.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-229-d0"></a>

### TOOLSET-229-d0 — A worker's edit to a ledger file is left out of its candidate and handed to the docs maintainer, not a hold

- [x] TOOLSET-229-d0 — A worker's edit to a ledger file is left out of its candidate and handed to the docs maintainer, not a hold
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [scope check](skills/autowork/scripts/parallel_integrate.py) (`verify_scope`: `changed files the coordinator owns: ...` raises `Hold('scope')`); `integrate` (merges the worker commit with `merge --no-ff` in the integration worktree); `COORDINATOR_FILES` in [dispatch](skills/autowork/scripts/parallel_dispatch.py); [maintainer triggers](pi-autowork/pi_autowork/maintainer.py) (`triggers`, `PLANNING_CAUSES`).
- Evidence (2026-10-18 13:56, a newly added fleet runner's first candidate): the worker changed five files (one new module, its 261-line test, a client doc, a registry line) and one line of TODO.md's introduction. That line repointed a link to a task the runner had archived meanwhile, so the link no longer resolved. The whole candidate was held with `changed files the coordinator owns: TODO.md`. A held scope commit is offered again, so a worker would spend a second attempt removing a one-line link fix, and the stale link stays for someone to notice.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, pi-autowork/pi_autowork/coordinator.py
- Scope: (1) When a candidate's only out-of-reach changes are to `COORDINATOR_FILES`, integration does not hold it. After the merge, those paths take their content from the integration base (`git checkout HEAD^1 -- <paths>`, amended into the merge commit), and the rest is validated and reviewed as usual. (2) The dropped hunks are saved as a patch in the slot's data and recorded on the slot (`ledger_edit_dropped`: the paths and the patch path). The log says `<task>: its edit to <paths> was left out; the docs maintainer will review it`. (3) `maintainer.triggers` raises a `ledger edit` trigger for such a slot once it integrates. Its reason carries the patch (up to 900 characters), so the maintainer applies it through the ledger tools or drops it. (4) Undeclared protected paths still hold as before.
- Acceptance: In fixtures: a candidate changing `src/x.py` and one line of TODO.md integrates, main has the `src/x.py` change and the base's TODO.md, the patch is saved, the log line appears, and the maintainer's triggers include `ledger edit` with the dropped line; a candidate changing only TODO.md integrates as an empty change and still raises the trigger; a candidate changing an undeclared lockfile is still held for scope.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s pi-autowork/tests -p test_maintainer.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No worker write access to ledger files. The worker prompt still says never to edit them. No automatic application of the dropped patch.
- Planner's call: Now, after TOOLSET-222-e1. Holding sound work for a ledger edit wastes an attempt, and the maintainer is the role allowed to edit the ledger. A worker usually touches it to fix a link or a status line, and the maintainer can judge that.
- Planner's call (2026-10-19 audit; where this differs from the Scope above, this wins): This also applies to merges the runner or its resolver makes into a task branch: ledger paths always take the integration base's content. That removes the ledger holds of 252-4c and 200-c1, which came from those merges, not from their Scopes; run it before them.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-220-71"></a>

### TOOLSET-220-71 — Plan For Me and Plan With Me end a large plan's batch with a planning task

- [x] TOOLSET-220-71 — Plan For Me and Plan With Me end a large plan's batch with a planning task
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [accepted rolling planning design](docs/plans/2026-10-18-rolling-planning.md#rolling-planning-design), [Plan For Me](skills/plan-for-me/SKILL.md), [Plan With Me](skills/plan-with-me/SKILL.md), [TODO work center](skills/shared/TODO-WORKCENTER.md) (task fields).
- Evidence (2026-10-18, owner): "plan_for_me porting this <project> to flutter" should start a chain that keeps planning and building.
- Touches: skills/plan-for-me/SKILL.md, skills/plan-with-me/SKILL.md, skills/shared/TODO-WORKCENTER.md, tests/test_workflow_commands.py
- Scope: (1) The TODO work center documents `Kind: plan` and `Plan round: N of M` (default M 10, at most 8 tasks a round). (2) Plan For Me and Plan With Me, for work too large for one batch, save the first batch (the tasks whose content is known now) and end it with a planning task depending on every task of the batch, whose scope names the goal and what the next round must find out. (3) Their report says the chain will continue on its own, its round limit, and how to stop it (move the planning task to `Needs decision`).
- Acceptance: The three skill texts carry the fields and the rule; a fixture prompt for "port this project to Flutter" in the workflow-command tests is answered by the skill text with a first batch plus one `Kind: plan` task (checked as text, no model run). Plan text for a small task adds no planning task.
- Checks: python3 scripts/check.py tests/test_workflow_commands.py tests/test_blockers.py
- Dependencies: TOOLSET-219-2c
- Ownership: Toolset coordinator.
- Exclusions: No change to how a single-batch plan is saved.
- Planner's call: the skills start a chain only after the runner can run planning tasks (the dependency), so no planning task lands where a code worker would take it.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-275-c1"></a>

### TOOLSET-275-c1 — Select and copy terminal TUI text by mouse dragging

- [x] TOOLSET-275-c1 — Select and copy terminal TUI text by mouse dragging
- Status: done
- Goal: PI-RUNNER
- Sources: [accepted continuous runner](docs/project.md#continuous-pi-runner-2026-10-15); owner request and picked clarification (2026-10-19): select and copy TUI text with the mouse.
- Touches: pi-autowork/pi_autowork/tui.py, pi-autowork/pi_autowork/command.py, pi-autowork/pi_autowork/tui_web.py, pi-autowork/tests/test_tui_mouse.py, pi-autowork/tests/test_fleet_view.py, pi-autowork/README.md, CHANGELOG.md, tests/test_tx.py
- Verification repair: A full check exposed the tx-help guard matching the dynamic config path instead of commands. Force an autowork-named fixture directory, exclude only the Current config-path line, preserve source/unknown-command guards and add a negative control for actual tx autowork help. First full run had an intermittent planning/merge failure; isolated reruns on candidate and base passed. Retain both failed full runs; do not describe them as passes.
- Scope: Terminal startup leaves mouse reporting off so the terminal handles drag selection and normal copy shortcuts. Preserve keyboard navigation/actions, view-only restrictions and reload argv. Offer explicit autowork tui --mouse for clickable controls; browser sessions retain mouse capture. Do not change services, profiles, jobs or clipboard contents.
- Acceptance: Pinned Textual startup tests cover default mouse=False and opt-in mouse=True, public CLI forwarding and browser capture. Existing headless pilot retains keyboard/confirmation behavior. A real isolated PTY renders the TUI and quits by keyboard in both modes; capture sequences are absent by default and present with --mouse. Actual client clipboard behavior is not claimed from fixtures. Full offline check and source review pass; source installation remains separate.
- Checks: python3 scripts/check.py pi-autowork/tests/test_tui_mouse.py pi-autowork/tests/test_fleet_view.py tests/test_autowork_command.py; python3 scripts/check.py; isolated PTY protocol probe; git diff --check.
- Dependencies: None.
- Ownership: Interactive Autowork implementation owner; preserve unrelated main-check edits and live workers.
- Qualification: Source implementation is complete. Focused TUI/native-command and headless-pilot tests passed; isolated PTY runs rendered both modes, confirmed default mouse-reporting absence versus explicit capture and keyboard quit, and contacted no services. The final complete python3 scripts/check.py passed on source snapshot 29b6d08459fbfb7dc016c6e20d43f9c139dc30c9 (five test directories, zero failed, eight excluded modules); final source review found no issues. Two earlier full runs failed and are retained, including the planning/merge intermittent failure and the corrected tx config-path guard. Actual client clipboard behavior and installed activation are not qualified.
- Next action: No source reimplementation remains. Load the updated TUI through the existing authorized installation/update path; client clipboard qualification remains a separate observation. No installation, runner restart, job resumption, clipboard access or push is included in this closeout.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-269-f2"></a>

### TOOLSET-269-f2 — A runner never commits or publishes uncommitted changes it did not make (GitHub #3)

- [x] TOOLSET-269-f2 — A runner never commits or publishes uncommitted changes it did not make (GitHub #3)
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [GitHub #3](https://github.com/TrebuchetDynamics/autowork/issues/3) (recurrence of #2); [coordinator](pi-autowork/pi_autowork/coordinator.py) (the main-checkout sweep that commits `chore: uncommitted work in the main checkout (pi-autowork)` and logs `Committed uncommitted changes in <repo> (...) so the session can merge`).
- Evidence (2026-10-19, one fleet runner): within two minutes of start the runner committed the owner's unfinished work on 9 files (one a deletion) that no task's `Touches:` named, merged its session and pushed main. Its own status had just said the final merge stops if it would touch uncommitted changes. The session's only change was one file.
- Touches: pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, docs/reference.md
- Scope: (1) The runner never stages or commits a main-checkout path outside the planning files (`TODO.md`, `TODO.archive.md`, `goals.json`, `BLOCKERS.md`), whatever its age or quietness. (2) When the session merge would touch such a dirty path, the merge waits and the status names the paths, as the status note already promises; when it would not, the merge proceeds and leaves them uncommitted. (3) The owner-planning sweep of quiet planning files stays as it is.
- Acceptance: In fixtures: a dirty, quiet non-planning file the session does not change stays uncommitted while the session merges and pushes; a dirty file the session does change stops the merge with that path named and no commit; a quiet `TODO.md` edit is still committed as owner planning.
- Checks: python3 -m unittest tests.test_pi_autowork; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to worker-worktree commits (`Left uncommitted in the session worktree`): those are the runner's own.
- Planner's call (2026-10-19): Now, first. Publishing unreviewed owner work is the one failure that damages the repository rather than throughput. The issue's expected behaviour decides the policy: only planning files keep the quiet-edit sweep; everything else belongs to whoever wrote it.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-272-1c"></a>

### TOOLSET-272-1c — A Touches-only rescope that adds a protected file integrates against the answered contract, or is refused plainly (GitHub #8)

- [x] TOOLSET-272-1c — A Touches-only rescope that adds a protected file integrates against the answered contract, or is refused plainly (GitHub #8)
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [GitHub #8](https://github.com/TrebuchetDynamics/autowork/issues/8); [state](skills/autowork/scripts/parallel_state.py) (`rescopable`, `rescope`, `rescoped_contract`); [integration](skills/autowork/scripts/parallel_integrate.py) (`verify_scope` reads `dispatched_contract`, the attempt's original `contract.txt`).
- Evidence (2026-10-19, one fleet runner): a task held for changing `package.json` was rescoped by the owner to declare it. The rescope was accepted, then integration checked the original contract, held it again for the same file and never offered it again; the owner had to cherry-pick the commit by hand.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_state.py
- Scope: (1) When a slot was rescoped by a Touches-only answer that names the protected path, protected-file admission reads `rescoped_contract`, and the commit integrates serially (nothing else integrating beside it). (2) A rescoped slot that is held again for a path its rescope did not name becomes one owner question that says a rerun or a contract change is needed; it is never left held silently.
- Acceptance: In fixtures: a commit changing `package.json`, held, then rescoped with `package.json` in `Touches:`, integrates on the next cycle and alone; a rescope that misses the held path gives one question naming that path.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_state.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No admission change for slots that were not rescoped.
- Planner's call (2026-10-19): Now. An answer the runner accepts must take effect; same shape as 271-d6, so whichever lands second reuses the other's re-offer path.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-284-e0"></a>

### TOOLSET-284-e0 — The autowork core SKILL.md has room again: detail moves to references/

- [x] TOOLSET-284-e0 — The autowork core SKILL.md has room again: detail moves to references/
- Touches: skills/autowork/SKILL.md, skills/autowork/references/
- Short: Core SKILL.md back under budget
- Status: done 2026-10-20 (interactive session): core 15994 -> 12595 bytes; three sections moved verbatim to existing references with one-line pointers; picker-policy and text-asserting tests pass.
- Goal: PI-RUNNER
- Scope: skills/autowork/SKILL.md is 15994 of the 16000 bytes test_picker_policy allows, so any task that adds a line to it fails its review (TOOLSET-230-bf: 16421 bytes). Move detailed procedure out of the core into existing or new files under skills/autowork/references/, leaving in the core a one-line pointer per moved section and every phrase other tests assert in it. No behavior or policy change; wording moves, it is not rewritten.
- Acceptance: skills/autowork/SKILL.md is at most 13000 bytes, leaving room for later tasks (test_picker_policy.PickerPolicyTests.test_core_stays_lean_and_points_to_every_reference); every reference file is still linked from the core (same test); every test that asserts core or reference text still passes (python3 scripts/check.py skills/autowork/scripts tests).
- Checks: python3 scripts/check.py skills/autowork/scripts/test_picker_policy.py; python3 scripts/check.py skills/autowork/scripts tests
- Dependencies: None.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-283-15"></a>

### TOOLSET-283-15 — Installed dependencies of a tracked lockfile are linked into worker and review trees without per-runner settings

- [x] TOOLSET-283-15 — Installed dependencies of a tracked lockfile are linked into worker and review trees without per-runner settings
- Short: Lockfile dependencies link into trees
- Status: done 2026-10-20 (interactive session): lockfile dependency directories linked into worker and review trees when the lockfile matches; reason logged when not; (3) covered by linking before review plus the existing provision-and-reverify path.
- Goal: PI-RUNNER
- Evidence: (2026-10-20, one fleet runner): a task was held 45 h after its review failed with 'missing server dependency' for a package that the repository's package.json and package-lock.json declare and its main checkout has installed. The runner's link list named only one unrelated directory, so the review tree had no node_modules and the hold became an owner question.
- Touches: pi-autowork/pi_autowork/workspaces.py, pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, tests/test_pi_autowork.py, docs/reference.md
- Scope: (1) Besides PI_AUTOWORK_LINK_PATHS, link_ignored links, from the canonical checkout, each gitignored dependency directory that sits beside a tracked lockfile and exists there: node_modules beside package-lock.json, pnpm-lock.yaml or yarn.lock; .venv beside uv.lock or poetry.lock. (2) A directory is linked only when the lockfile in the tree is byte-identical to the canonical one; otherwise it is left out and the log says why, so a task that changes dependencies installs its own. (3) A review that fails only because such a dependency is missing is an environment hold the runner retries once after linking, never an owner question.
- Acceptance: In fixtures: a repository with a tracked package-lock.json and an installed, gitignored node_modules gives worker and review trees a link to it with no setting; a tree whose lockfile differs gets none and logs the reason; a review failing for 'missing dependency' with the link now available is retried once and passes. PI_AUTOWORK_LINK_PATHS keeps working unchanged.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_worker_tmp.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No package installs or network access by the runner; no link when lockfiles differ; no change to PI_AUTOWORK_LINK_PATHS semantics.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-282-43"></a>

### TOOLSET-282-43 — A headless worker never stops to ask for approval; an interactive skill's approval step counts as given by the task contract

- [x] TOOLSET-282-43 — A headless worker never stops to ask for approval; an interactive skill's approval step counts as given by the task contract
- Short: Headless worker never waits for approval
- Status: done 2026-10-20 (interactive session): approval rule in the worker prompt; one same-session resume after a question; a second question holds the task quoting it; worker and prompt tests.
- Goal: PI-RUNNER
- Evidence: (2026-10-20, one fleet runner): a task's second attempt loaded an interactive design skill, wrote its plan and ended with 'The brainstorming skill requires explicit approval of this design before implementation. Do you approve?' after 28 s. The runner recorded 'dead worker without a commit or changes', held the task on its last attempt and asked the owner to rescope it.
- Touches: pi-autowork/pi_autowork/worker.py, pi-autowork/pi_autowork/coordinator.py, skills/autowork/scripts/parallel_dispatch.py, tests/test_pi_autowork.py, pi-autowork/tests/test_worker_tmp.py
- Scope: (1) The worker prompt states that the task contract is the approved design: no person is attached, so a skill step that asks for approval (brainstorming, plan review) is treated as approved by the contract, and the worker proceeds to implement. (2) A worker that ends its session with a question to the user and no commit is not 'dead': the runner resumes the same session once with a fixed message ('No person is attached; the task contract is your approval. Implement it now.'), within the same attempt and budget. (3) Only a second ending without a commit holds the task, with the worker's question quoted as the reason.
- Acceptance: In fixtures with a fake Pi: a worker whose first reply ends 'Do you approve?' with no commit is resumed once in the same session and attempt and then commits; one that asks twice is held quoting its question, never as 'dead worker without a commit or changes'; the prompt fixture contains the approval sentence.
- Checks: python3 scripts/check.py tests/test_pi_autowork.py pi-autowork/tests/test_worker_tmp.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to which skills a worker may load, to attempt limits or to the task contract; a worker's genuine blocker still holds the task.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-281-0d"></a>

### TOOLSET-281-0d — A candidate that passed its batch lands before the runner reloads, and after an interrupted landing it lands first

- [x] TOOLSET-281-0d — A candidate that passed its batch lands before the runner reloads, and after an interrupted landing it lands first
- Short: Batch pass lands before reload
- Status: done 2026-10-20 (interactive session): reload and session merge wait for batch-passed candidates to land; `landing` phase in log and TUI; unit and runner tests.
- Goal: PI-RUNNER
- Evidence: (2026-10-20, this repository's runner): at 20:56 a batch passed three candidates and logged 'landing them now'; 4 s later the runner reloaded onto a new toolset. Two landed; the third has sat in 'integrating' for over 15 h behind about 20 queued candidates, each reviewed one at a time.
- Touches: pi-autowork/pi_autowork/coordinator.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, tests/test_pi_autowork.py, pi-autowork/pi_autowork/fleet_view.py
- Scope: (1) The runner's toolset reload waits while any batch-passed candidate is still landing, as it already waits for a running review or merge resolution. (2) A batch pass is recorded per candidate (tree and verdict) so that, after any restart, a slot still 'integrating' with a recorded pass for its current tree goes to the front of the integration queue and lands from that verdict, without a fresh review and without waiting behind priority order. (3) Status and the TUI say 'landing after restart' for such a slot instead of 'verifying'.
- Acceptance: In fixtures: a batch of three passes, the runner is told to reload between the pass and the landings, and all three land before the reload; a restart forced mid-landing leaves one slot integrating, and the next cycle lands it first with no review run; a slot whose tree changed after its pass is reviewed again as today.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to batch formation, gates or review content; a pass is never reused for a different tree.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-280-4f"></a>

### TOOLSET-280-4f — A held commit whose branch the runner itself merged past is recovered by the runner, never asked of the owner as a rescope

- [x] TOOLSET-280-4f — A held commit whose branch the runner itself merged past is recovered by the runner, never asked of the owner as a rescope
- Short: Runner-merged held branch self-recovers
- Status: done 2026-10-20 (interactive session): runner-merged tips adopted within the limit or rerun from the kept tip (`runner_merged`, technical); abandoned clean merges aborted; fixture tests.
- Goal: PI-RUNNER
- Sources: [integration](skills/autowork/scripts/parallel_integrate.py) (`verify`: raises `reported commit/branch/lineage mismatch` when `refs/heads/<branch>` is not `slot['commit']`; `merged`; `retry_held`, `_retire`), [slot state](skills/autowork/scripts/parallel_state.py) (`merge_adoption`, `exhausted`, `readoptable`), [coordinator](pi-autowork/pi_autowork/coordinator.py) (`resolve_task_conflict`, `adopt_merge`); TOOLSET-251-c4 in [the archive](TODO.archive.md#toolset-251-c4) (adoption limit and per-revision rule).
- Evidence: (2026-10-20, one fleet runner, stalled about 20 h, 8 dependents held): two tasks on their second attempt had passed every listed check on their recorded commits. Before TOOLSET-251-c4 reached that runner, its conflict resolver merged later session commits into each branch 13 and 15 times while the engine refused adoption, so the slot kept the old commit. When the hold was later cleared for technical recovery, verify found the branch past the recorded commit and the runner asked the owner to rescope or split both tasks. One worktree also held an uncommitted, conflict-free merge with no live process. The owner answered each by hand with a retry that restores the kept branch.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_state.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) When verify finds the branch tip is not the recorded commit, but the recorded commit is an ancestor of the tip and every first-parent commit after it is a merge whose other parent is a canonical (session or main) revision, the slot is not held for a person: if merge_adoption allows it, the tip is adopted as by --parallel-merged (report commit and changed_files updated, merged_count counted); otherwise the task is requeued as technical recovery with its kept branch named in the new attempt's prompt so the worker restores it and reruns the checks. (2) A worktree whose resolver run has ended and that still holds a merge in progress (MERGE_HEAD present) is cleaned by the runner before verify or adoption: with no unmerged paths and a live owner absent, the merge is aborted (the resolver can merge again later); the event is journaled. (3) The owner question for 'reported commit/branch/lineage mismatch' is raised only when the tip does not descend from the recorded commit, or descends through a non-merge commit nobody recorded; its text names which.
- Acceptance: In fixtures: a conflict-held slot whose branch gained several resolver merges beyond its recorded commit (adoption limit reached, then hold cleared) is requeued as technical recovery with the kept tip named, never a USER_DECISION; one within the limit is adopted and reaches review; a worktree left mid-merge with no conflicts is aborted and journaled before verify; a branch with an unrecorded non-merge commit still raises the owner question, naming that commit. No report or slot is rewritten to claim a pass.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_state.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to the adoption limit, gates, review or how a conflict is detected; no rewritten report or slot that claims a check the merged tree did not run.
- Planner's call: Now (owner blockers pass, 2026-10-20): the runner caused this hold itself, so it must clear it itself; the owner only plans and answers real decisions.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-273-e0"></a>

### TOOLSET-273-e0 — Planning merge drivers survive a toolset self-update (GitHub #5)

- [x] TOOLSET-273-e0 — Planning merge drivers survive a toolset self-update (GitHub #5)
- Short: Merge drivers survive self-update
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [GitHub #5](https://github.com/TrebuchetDynamics/autowork/issues/5); [coordinator](pi-autowork/pi_autowork/coordinator.py) (`setup_planning_merges` writes `merge.docs-sync-*.driver` with the release directory's path); [release](pi-autowork/pi_autowork/release.py) (`prune` removes old releases).
- Evidence (2026-10-19, one fleet runner): after a self-update pruned the old release, the repository's `.git/config` drivers still named its `goals.py`; any planning-file merge until the next registration used a driver that no longer existed.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/release.py, pi-autowork/tests/test_release.py, tests/test_pi_autowork.py
- Scope: (1) The registered driver command names a stable entry point that outlives releases: the installed toolset package's `goals.py`, or a shim that resolves the current release. (2) A runner re-registers on start when the registered command differs. (3) `prune` never removes a release that a registered driver still names.
- Acceptance: In fixtures: drivers registered on release A still run after an update to B prunes A; a stale registration from before this change is rewritten on the next start.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_release.py; python3 -m unittest tests.test_pi_autowork; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No portable `.gitattributes` change; only the local Git config command moves.
- Planner's call (2026-10-19): Now. Small, and it removes a way for an update to break merges done outside the runner.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-234-d4"></a>

### TOOLSET-234-d4 — A main-repair worker gets the runner's main-check evidence: log, exit code, revisions and isolated reruns

- [x] TOOLSET-234-d4 — A main-repair worker gets the runner's main-check evidence: log, exit code, revisions and isolated reruns
- Short: Main repair gets the main-check evidence
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [maintainer prompt](pi-autowork/pi_autowork/maintainer.py) (`PROMPT`: for `MAIN (main red)` and `MAIN (flaky test)` it adds a repair or hardening task with the failing tests and commits as Evidence); [main check](pi-autowork/pi_autowork/main_check.py) (the runner state's `main-check.log`, `main-check.exit`, `main-check-reruns.log`, `main_check.json`: revision, last green, failures, flaky history); [worker launch and prompt](skills/autowork/scripts/parallel_dispatch.py) (`launch` env, `prompt`).
- Evidence (2026-10-18 15:57, one fleet runner): its two maintainer-made main-repair tasks both ended as owner questions. One asked for "the full log of the red MAIN, including exit code, failing phase/test and attempt/retry classification", which it could not find locally (its own full reproduction exited 0). The other asked for "the original MAIN run report, with the exact test, the three revisions, and the outputs and return codes of the full and isolated runs". The runner had all of it in its state directory, but no worker can see that directory or knows it exists, and the owner cannot answer either question better than the runner's files.
- Touches: pi-autowork/pi_autowork/main_check.py, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_main_check.py, pi-autowork/tests/test_maintainer.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/coordinator.py
- Scope: (1) After every main check, the runner writes a read-only evidence bundle at `<git common dir>/autowork-execution/main-evidence/<rev>/`. It holds `main_check.json`, the full `main-check.log`, `main-check.exit`, `main-check-reruns.log` (each isolated rerun's command, exit code and output) and `flaky_history.json`. It keeps the last five revisions. (2) Workers get `AUTOWORK_MAIN_EVIDENCE` (that directory's parent), and the prompt says that a task repairing a red or flaky main finds the runner's main-check runs there, by revision, and never asks a person for them. (3) The maintainer's MAIN prompt has the task entry name the bundle's revision directory in its Evidence. (4) A worker blocker that asks only for main-check logs, exit codes or rerun output, when a bundle exists, is resumed once with the bundle's path instead of becoming a question (the resume path of TOOLSET-232-01; whichever lands second reuses it).
- Acceptance: In fixtures: a red main check writes the bundle with the log, exit code and rerun output, and old revisions beyond five are pruned; a worker's environment has `AUTOWORK_MAIN_EVIDENCE` and its prompt carries the rule; the maintainer's MAIN items name the bundle directory; a blocker asking for "the full log of the red MAIN" with a bundle present resumes the attempt with the path and raises no question.
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_main_check.py; python3 -m unittest discover -s pi-autowork/tests -p test_maintainer.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No copying of the bundle into worktrees or commits. It is runner evidence, not repository content.
- Planner's call: Now, after TOOLSET-232-01. Each maintainer-made repair task ends as an owner question today, so red mains never repair themselves. Handing workers the runner's own receipts closes the loop the maintainer opens.
- Planner's call (2026-10-19 audit; where this differs from the Scope above, this wins): It also takes over the superseded 240-f8: update the existing evidence when main changes, never add a second task. Scope (4) becomes: `TRIAGE_PROMPT` lists `$AUTOWORK_MAIN_EVIDENCE` among what the runner provides; no separate resume path, the blocker triage covers it.
- Planner's call (2026-10-19 builder check): "Never a second task" means the docs maintainer updates the Evidence of the existing repair task for the same failing tests; drop 240-f8's per-task evidence copy under slot-data.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-138-62"></a>

### TOOLSET-138-62 — Reconcile the fleet's unmerged parallel-admission branch into main

- [x] TOOLSET-138-62 — Reconcile the fleet's unmerged parallel-admission branch into main
- Short: Merge the parallel-admission branch
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [monitor findings](docs/plans/2026-10-16-pi-autowork-coordinator.md#fleet-monitor-findings-delivery-environment-and-stall-repair), branch `fix/directory-parallel-admission` (commits 28d38eb, 3848aaa; checkout `.worktrees/autowork-directory-admission`), main's adedf58 "fill independent worker slots and keep task worktrees canonical", [engine](skills/autowork/references/parallel-workers.md).
- Evidence (2026-10-16 23:40 monitor pass): four services (runner D, runner A, runner C, runner B) run from that checkout. `git cherry main fix/directory-parallel-admission` shows both commits unmerged, and main is 19 commits ahead of them.
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/references/parallel-workers.md
- Scope: Verify the current-history directory-admission implementation represented by merge 3504855659952b9a42ea6b6f78310878d0733f42 and directory-admission commit 34d988b7962c7942c97dcf703ff8fc17b3741db2. Confirm the original 3848aaa patch equivalence as provenance, reconcile independent-retry and protected-inventory directory admission into one current implementation, and qualify the union of their tests. Do not merge old history merely to manufacture original ancestry, restore an old snapshot, rewrite history, or remove a retained branch/checkout. Runtime pin safety remains actual ancestry of each installed pin, owned by TOOLSET-139-62.
- Acceptance: The current-history directory-admission commit 34d988b7962c7942c97dcf703ff8fc17b3741db2 and merge 3504855659952b9a42ea6b6f78310878d0733f42 are ancestors of the actual qualification target main. Establish patch provenance to 3848aaa without claiming original ancestry. The independent-retry, protected-inventory directory-scope admission and canonical-worktree tests pass together on current main, with no duplicated admission path. A patch-equivalent but nonancestor old pin remains unchanged and reported; only its actual ancestry can authorize automatic unpinning.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p 'test_parallel_*.py'; python3 scripts/check.py; git diff --check
- Dependencies: None.
- Ownership: Toolset coordinator. It runs before the TOOLSET-099-87 continuation, which edits the same engine files and resumes on top of this merge.
- Exclusions: No service restart, env edit or fleet repository edit. Runtime pin handling belongs to TOOLSET-139-62.
- Planner's call: Apply the owner's current-history verification decision below; withdraw the former requirement to merge original history solely to make the old pin an ancestor. Preserve original commit identities as history, all functional checks, and the strict per-pin ancestry gate.
- Owner decision: 2026-10-18 — Verify current-history equivalents; keep any old pin whose actual ancestry is unproven. This changes the 138-62 acceptance/history contract and corresponding 139-62 interpretation only; no service operation, reset, remote publication or history rewrite is authorized.
- History evidence: Fresh read-only ancestry checks find original 3848aaa5eb07aaec97005360a7827b6401f1dc38, 28d38ebb09f2f73a4108a9216e201d250d800364 and de023264547f9f6e248a8bd28c4175174c307a43 outside both main and the observed origin/main ref, contrary to the former task status. Current 34d988b7962c7942c97dcf703ff8fc17b3741db2 and 3504855659952b9a42ea6b6f78310878d0733f42 are ancestors of both observed refs. Original 3848aaa and current 34d988b have stable patch ID c05c5b1c7932ab86d8d3555ec30202f6f4908aa0. Patch equality is not source qualification or runtime pin ancestry; no engine/full-suite tests were run by this planning pass.
- Next action: Reuse the current implementation and the retained no-change worker report; verify the cited current-history commits against the actual qualification target, inspect one admission path and run the unchanged named engine/full offline checks. Close only from current executed evidence. Do not remerge retained original history, ask the same ancestry question or mark tests passed from patch identity.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-259-ca"></a>

### TOOLSET-259-ca — Plans prefer independent tasks; a long dependency chain needs a reason

- [x] TOOLSET-259-ca — Plans prefer independent tasks; a long dependency chain needs a reason
- Short: Plans prefer independent tasks
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/plans/2026-10-19-more-parallel-workers.md) (decision 7); [planning craft](skills/shared/PLANNING-CRAFT.md) (`Plan for an unattended worker`); [docs maintainer](pi-autowork/pi_autowork/maintainer.py) (`PROMPT`).
- Evidence: across the fleet, dependency waits were the most common reason on every runner but one (2026-10-19 05:30).
- Touches: skills/shared/PLANNING-CRAFT.md, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py
- Scope: (1) The planning craft adds: prefer tasks with disjoint Touches that can run at once; a chain longer than three tasks names why each link depends on the last; split a task that touches unrelated areas. (2) The builder check asks which saved tasks could run in parallel and why the rest cannot. (3) The docs maintainer's re-sort, when it unblocks a chain, prefers splitting off independent parts.
- Acceptance: The craft and the maintainer prompt contain the rules; the maintainer test asserts the prompt line.
- Checks: python3 scripts/check.py pi-autowork/tests/test_maintainer.py
- Dependencies: None.
- Ownership: Toolset skills.
- Exclusions: No automatic rewriting of existing plans.
- Planner's call: the cheapest parallelism is a plan whose tasks do not wait on each other.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-254-80"></a>

### TOOLSET-254-80 — Explain full-check results from their recorded evidence, never from an absent log

- [x] TOOLSET-254-80 — Explain full-check results from their recorded evidence, never from an absent log
- Short: Explain full checks from their evidence
- Status: done
- Goal: PI-RUNNER
- Payoff: Prevent a reviewer from reading all tests passed when the accepted gate used exceptions or its detailed evidence is missing.
- Sources: [accepted continuous runner](docs/project.md#continuous-pi-runner-2026-10-15); [claim-grounded verification research](docs/research/pi-autowork-reference-architectures.md#source-grounded-verification-and-large-agent-claims); pi-autowork/pi_autowork/worker.py (full_suite_gate, run_gate, gate_log, gate_note); completed TOOLSET-227-a8 check reuse.
- Touches: pi-autowork/pi_autowork/worker.py, pi-autowork/tests/test_worker_tmp.py, tests/test_pi_autowork.py
- Scope: Preserve the runner-owned full-check and its existing cache/passing policy, but carry the producing gate outcome, command/tree identity, original inventory result, exception classification and available owned evidence reference into gate_note's reviewer explanation. A cached result reused by a different task must refer to its actual producing evidence, not infer all green from an absent current-task log. Explicitly distinguish all-green, accepted baseline-equivalent failures, accepted isolated-rerun classification and accepted result with unavailable detail. Missing/unreadable/mismatched legacy evidence remains unavailable and cannot be rewritten as all tests passed. Use existing state/records; no historical receipt engine, new reviewer or extra full check to regenerate explanatory text.
- Acceptance: Existing compact fixtures cover first all-green result, baseline/flaky exception acceptance preserving original failures/skips, cached reuse on the same tree/command for a different task, absent/empty/unreadable log, stale/mismatched evidence and legacy aggregate-only cache. Reviewer text states only what that exact gate record establishes, never it passed solely because no names were parsed. Legacy accepted aggregate results disclose missing detail without fabricating a fresh run or changing existing admission policy. Changed tree/command retains existing invalidation; unknown metadata is not claimed to satisfy future stronger environment-bound reuse. Required full-gate/review behavior, task privacy and source ownership protections remain unchanged; explain-only reuse launches no duplicate check. These cases are planned, unrun.
- Checks: Planned after implementation: python3 scripts/check.py pi-autowork/tests/test_worker_tmp.py tests/test_pi_autowork.py; python3 scripts/check.py; git diff --check. Extend the existing fake-runner/gate fixtures rather than add a new broad suite.
- Dependencies: None.
- Ownership: Normal Toolset execution and integration owner; serialize current worker.py/review work and never repin an active candidate or reviewer.
- Exclusions: No new LLM judge, source-truth guarantee, semantic model benchmark, larger swarm, Obsidian export, runtime/service/profile changes, deployment, publication, test waiver, failure-history rewrite or resurrection of modules targeted by TOOLSET-202-9a. Research persistence does not dispatch implementation.
- Planner's call: A narrow producer-evidence fidelity successor to delivered check reuse, not its reimplementation. Keep 130-15 as the read-model consumer and 118-68/228-0c as capacity owners. Diagnose from structured producing evidence before parsing task-local logs; preserve unsupported and unavailable distinctions.
- Next action: Add a table-driven fake gate/record regression showing cached cross-task reuse with a missing current-task log and an exception-qualified producing run. Make the minimal existing gate-record/gate_note correction, then run the focused fixtures and mandatory offline/review gates. Do not run real model calls or increase worker count to verify this behavior.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-285-29"></a>

### TOOLSET-285-29 — A task whose last attempt failed its review is reworked once with the findings, never left silently held

- [x] TOOLSET-285-29 — A task whose last attempt failed its review is reworked once with the findings, never left silently held
- Short: Review-failed last attempt is reworked
- Status: done 2026-10-20 (interactive session): one rework with finding and kept tip after a last-attempt review failure; second failure held as reviewed_twice (owner question, re-reviewable by a changed reviewer); entry edits reset it; fixture and runner tests.
- Goal: PI-RUNNER
- Evidence: (2026-10-20, one fleet runner): a task's second attempt failed its review ('required scheduler and signed-execution acceptance evidence is missing'). The engine offers fresh retries only to first attempts, and the question list classes review failures as technical, so the task was neither retried nor asked about and appeared nowhere among the runner's roots or questions.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_questions.py, tests/test_pi_autowork.py
- Scope: (1) A held slot whose cause is a review failure (validation, not environment) on its last attempt gets one fresh rework attempt of the same task: the previous commit is kept on a -set-aside-N branch, and the new prompt names that tip and quotes the reviewer's findings as what to fix. (2) A second review failure of the rework becomes an owner question quoting both findings. (3) Until then, status, the TUI and BLOCKERS.md show such a task as 'reworking after review' or as the question, never as nothing: no held task may be neither retried nor asked.
- Acceptance: In fixtures: a task whose second attempt fails review with a finding gets exactly one rework attempt whose prompt contains the finding and the kept tip; a rework that passes lands; a rework that fails again yields one owner question quoting both findings; a status snapshot never shows a held task with no retry, no question and no root.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s pi-autowork/tests -p test_questions.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to review content, gates or the attempt limit for other causes; an environment hold keeps its provisioning path.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-289-71"></a>

### TOOLSET-289-71 — Task status shows Active, Mergeable, Waiting or Blocker with a detail

- [x] TOOLSET-289-71 — Task status shows Active, Mergeable, Waiting or Blocker with a detail
- Short: Status reads Active/Mergeable/…
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [accepted vocabulary](docs/project.md#task-status-vocabulary-2026-10-20) (owner, 2026-10-20); [fleet view](pi-autowork/pi_autowork/fleet_view.py) (`task_counts`, `QUEUED`, `PHASES`); [TUI](pi-autowork/pi_autowork/tui.py) (`RUNNER_COLUMNS` Run/Land/Wait/Held and the detail line "working · to land · waiting · held"); [health](pi-autowork/pi_autowork/health.py) (`NEEDS_PERSON`, "held for a person").
- Evidence: the owner asked what Run, Land, Wait and Held mean and whether Held is a blocker. "Land" counts `implemented` commits (`QUEUED`) that have not been checked yet, so it is not "ready to merge"; "Held" covers both agent-repairable causes and real owner questions.
- Touches: pi-autowork/pi_autowork/fleet_view.py, pi-autowork/pi_autowork/tui.py, pi-autowork/pi_autowork/health.py, pi-autowork/tests/test_fleet_view.py, pi-autowork/tests/test_health.py
- Consumes: TOOLSET-129-c4's single Needs action (reason, audience, source) for a Blocker's "who resolves it".
- Scope: (1) One pure function maps a slot and its evidence to (headline, detail, resolver): headline one of Active, Mergeable, Waiting, Blocker; Mergeable only when the recorded checks and review passed and only the merge remains; `held` becomes Blocker with its cause and resolver Agent repair, Needs you or External (Needs you only for causes the engine cannot repair, the `NEEDS_PERSON` set made explicit). (2) The runner table's columns become Active, Mergeable, Waiting, Blocker, Total; the detail line, task rows and `autowork status` use the same words and show `headline · detail`. (3) Every Waiting row names its reason. (4) Engine state names and runner-level states are unchanged; no alias keeps the old column names.
- Acceptance: Given a reported commit without checks, the row reads `Waiting · Implemented`, never Mergeable (`test_fleet_view.py::test_implemented_is_waiting_not_mergeable`). Given checks and review passed, `Mergeable` (`test_mergeable_needs_passed_gates`). A conflict hold reads `Blocker · Conflict · Agent repair`; a blocker the worker reported for credentials reads `… · Needs you` (`test_blocker_names_its_resolver`). The runner table header is exactly Runner, State, Active, Mergeable, Waiting, Blocker, Total, Needs, Now (`test_runner_columns`).
- Checks: python3 -m unittest discover -s pi-autowork/tests -p test_fleet_view.py; python3 -m unittest discover -s pi-autowork/tests -p test_health.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No change to engine slot states, hold causes or retry behaviour; TOOLSET-276-a9 owns the hold-cause table.
- Planner's call: after 129-c4 because both rewrite the Needs cell and the runner table in the same files.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-146-bc"></a>

### TOOLSET-146-bc — Run conditional Docs Sync during verified Autowork closeout

- [x] TOOLSET-146-bc — Run conditional Docs Sync during verified Autowork closeout
- Short: Conditional Docs Sync at closeout
- Status: done
- Goal: DOCS-COMPLETENESS — Make core-document completeness and drift machine-checkable.
- Sources: [accepted recovery and closeout plan](docs/plans/2026-10-16-pi-autowork-coordinator.md#automatic-stall-recovery-and-conditional-docs-sync), [existing closeout guidance](skills/shared/ENGINEERING-CYCLE.md), [Docs Sync](adapters/skills/docs-sync/SKILL.md), [parallel close](skills/autowork/scripts/parallel_integrate.py).
- Touches: skills/autowork/SKILL.md, adapters/skills/autowork/SKILL.md, skills/shared/ENGINEERING-CYCLE.md, skills/autowork/references/parallel-workers.md, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/worker.py, tests/test_pi_autowork.py, tests/fixtures/autowork-closeout/, docs/cross-host.md, docs/workflows.md
- Skills: Required: bundled Docs Sync, resolved in the actual host, for scoped Maintain when a verified change leaves a concrete documentation delta. Expected result is affected docs reconciled with source and readback/checks, or a justified not_needed disposition. Archive-only rendering is not equivalent. Use its existing helper path for deterministic task/index/archive changes; no repository-wide bootstrap.
- Scope: Assess doc impact at each task closeout from verified changes, task acceptance and actual docs. Update component docs inside authorized worker Touches; route shared docs through the coordinator. Add source-bound not_needed/updated/pending evidence with backward-compatible assessment of older reports. Prepare a narrow Docs Sync pass outside atomic-close locks; integrate/validate the actual doc candidate before final closure. Coalesce compatible completions in one settlement pass without waiting for fleet idleness. Preserve current atomic closure, exact evidence binding and history ownership. Align native/portable sequential guidance with the runtime path. Reconcile known newer origin atomic-close changes before editing; no second closeout authority.
- Acceptance: Behavioral fixtures show relevant docs updated for a changed interface; already-correct or metadata-only work produces a justified no-op; two compatible completions share one pass with per-task evidence. Foreign dirty docs and moved source hold/reconcile safely. Failure or interruption preserves integrated code and pending doc closeout without marking done or replaying implementation; restart resumes once. Legacy reports lacking doc fields are assessed instead of rejected. TODO-only and indexed archive history is preserved. Once/until-empty finish needed closeout within scope; stops/pauses/budget limits do not launch new work. Scoped Docs Sync changes no unrelated policy or acceptance and no global manifest is required.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 scripts/check.py skills/autowork/scripts/test_parallel_integrate.py; python3 scripts/check.py tests/test_pi_autowork.py; bounded native/portable closeout behavioral scenarios (new, unrun); python3 scripts/check.py at combined runtime integration; git diff --check. Reuse compact fake-worker/disposable-Git fixtures; no test per wording rule.
- Dependencies: None. Serialize overlapping lifecycle/closeout edits after active TOOLSET-115-bf work; reuse TOOLSET-120-fc/141-c4 recovery facilities where present, without making all stall handlers prerequisites for doc closeout.
- Ownership: Toolset coordinator. Source/offline delivery here; installed fleet qualification remains TOOLSET-096-7e.
- Owner decision (2026-10-17): the conditional Docs Sync pass at closeout runs in the DOCS-MAINTAINER worker (TOOLSET-164-f1, [plan](docs/plans/2026-10-17-docs-maintainer.md#docs-maintainer-worker) decision 5). This task keeps the per-task doc-impact assessment and its not_needed/updated/pending evidence in worker reports, which the maintainer consumes.
- Exclusions: No full-doc bootstrap per task, new product work at closeout, infinite model retries, automatic installation/service restart, paused-job resumption, direct fleet-repository edits, publication or invented live checks. This planning pass dispatches nothing.
- Planner's call: Always assess, run scoped Maintain only when needed; bind disposition to actual source/doc inputs and retain pending status on required doc failure. A code integration is not complete task closeout.
- Planner's call (2026-10-19 audit; where this differs from the Scope above, this wins): Only the `not_needed`, `updated` or `pending` doc-impact fields in worker reports remain. The closeout Docs Sync pass itself belongs to the docs maintainer (266-7a).


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-252-4c"></a>

### TOOLSET-252-4c — A worker blocker that names another open task waits for that task, occupies nothing meanwhile, and resumes when it lands

- [x] TOOLSET-252-4c — A worker blocker that names another open task waits for that task, occupies nothing meanwhile, and resumes when it lands
- Short: Blocker on a task waits for that task
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: fleet monitoring (2026-10-18); [integration](skills/autowork/scripts/parallel_integrate.py) (a worker's `blockers` become a `Hold('blocker')`, a person's question); [dispatch](skills/autowork/scripts/parallel_dispatch.py) (`dispatch_locked`: held slots stay `occupying` unless exhausted or overlap-held); [admission](skills/autowork/scripts/parallel_plan.py) (an exclusive task waits `must run alone (beside <task>)` for every occupying slot).
- Evidence (2026-10-18 21:23-23:34, one fleet runner): an exclusive task waited more than 70 minutes `must run alone (beside <A>)` while A was reviewed, draining all lower dispatch. A's worker then stopped with a blocker naming that exclusive task: "The existing <exclusive task> owner/coordinator must supply the retained parser repair in the combined baseline". A became a held slot that still occupied, so the exclusive task kept waiting beside it while A waited for the exclusive task. The runner sat at 0 workers with 3 tasks behind A; only a person or the docs maintainer could break it.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/parallel_state.py, pi-autowork/pi_autowork/questions.py, pi-autowork/tests/test_questions.py
- Scope: (1) When every blocker of a report names, by ID, an open task other than its own that the ledger does not already make a dependency, the hold records `waits_for: [<ids>]` (a new slot field) and is not a person's question. (2) A slot with `waits_for` occupies nothing. Admission treats it like a dependency of its task: it never starts beside, or ahead of, a task it waits for. (3) Once every task in `waits_for` is closed (here or on the base, TOOLSET-218-d0), the slot resumes on the same attempt, with a prompt line naming the landed tasks. (4) A blocker naming no task, or also asking for something else, stays a question as today. A `waits_for` that has not resolved after 24 h becomes one question too.
- Acceptance: In fixtures: a report whose only blocker names open task B gives a held slot with `waits_for: [B]` and no BLOCKERS question; an exclusive B starts although that slot exists; after B closes, the slot resumes the same attempt and its prompt names B; a blocker naming no task still goes to the blocker triage.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_dispatch.py; python3 -m unittest discover -s pi-autowork/tests -p test_questions.py; python3 scripts/check.py
- Dependencies: TOOLSET-229-d0.
- Ownership: Toolset coordinator.
- Exclusions: No editing of the task's `Dependencies:` line by the engine; the docs maintainer may still record it.
- Planner's call: Now, after TOOLSET-251-c4. A worker that has found the order the plan missed has told the runner exactly what to wait for; turning that into a wait, rather than a question and a slot that still blocks, removes a whole class of deadlocks between exclusive work and its dependents.
- Owner decision (2026-10-19): Preserve the code; separate coordinator-owned queue edits and reverify this retained implementation. Keep candidate 48070c51f0c65ba28d8ad7542670e69444c926bb and its recorded checks/history; no fresh reimplementation or waiver of mandatory checks.
- Next action: Existing execution owner: continue from retained candidate 48070c51f0c65ba28d8ad7542670e69444c926bb, preserving its code and tests. Prepare the smallest descendant/reconciled candidate that excludes only attributable worker changes to protected TODO.md/goals.json; any necessary planning repair goes through the coordinator/Docs Sync, never a worker-file guard bypass or restoration of stale queue snapshots. Reverify the exact integrated code with original required checks and review; reuse only still-valid evidence. Keep the same task and cumulative accounting, preserve unrelated work and do not clear slots/leases manually. A saved answer is not verified delivery.
- Planner's call (2026-10-19 audit; where this differs from the Scope above, this wins): The hold records `waits_for` before the blocker triage runs, and `triage_blocker` skips slots that have one. A blocker naming no task goes to the triage (4a82801), not to a question. Drop the acceptance clause "an exclusive B starts although that slot exists": 1fcf0a3 already lets a must-run-alone task start beside held slots whose worker has ended.
- Planner's call (2026-10-19 builder check): A `waits_for` that has not resolved after 24 h becomes one question for the owner, not a triage: the task it waits for is stuck. Reuse the waits_for code of the retained candidate (now on `autowork/TOOLSET-252-4c-set-aside-1`) where it still fits, and drop its path that sends task-less blockers to the owner, since the triage handles those: that keeps the owner decision's intent of not reimplementing what exists. Depends on 229-d0.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-242-d5"></a>

### TOOLSET-242-d5 — A task archived as done is done in the ledger too, and a not-runnable reason names what blocks it

- [x] TOOLSET-242-d5 — A task archived as done is done in the ledger too, and a not-runnable reason names what blocks it
- Short: Archived done means done in the ledger
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [contract rules](skills/autowork/scripts/task_execution.py) (`contract_reason`, the `ledger dependency or disposition holds execution` reason, `dependency_done`, `archived_done`, `_queue_inputs`), [ledger commands](skills/docs-sync/scripts/goals.py) (`task`, `archive`), [docs maintainer](pi-autowork/pi_autowork/maintainer.py) (the `not runnable` trigger).
- Evidence (2026-10-18, a fleet runner): three tasks and two behind them waited for hours as `not runnable: ledger dependency or disposition holds execution`; their dependencies were checked done in the TODO archive but still `open` in `goals.json` and unchecked in TODO.md. The reason named neither the dependency nor the disagreement, the maintainer made no change, and the runner asked the owner.
- Touches: skills/autowork/scripts/task_execution.py, skills/autowork/scripts/test_parallel_plan.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py
- Scope: (1) The reason names what holds the task and why: `ledger: <ID> is open in goals.json but archived as done` (or the ID missing from the ledger, or a ledger dependency outside Now/Next). (2) The runner repairs the archived-done case itself, without a model, through `goals.py` (the task `done` in the ledger, its open TODO entry archived), in one planning commit that names the IDs; it never marks a task done that the archive does not show as done. (3) Any other ledger disagreement goes to the maintainer with that exact reason, which it can act on.
- Acceptance: In fixtures, a dependency archived done but open in the ledger is repaired in one planning commit and its dependents run; the reason for every other case names the ID and the disagreement; nothing that is not archived as done is ever marked done.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_plan.py tests/test_pi_autowork.py; python3 scripts/check.py with TMPDIR set to a fresh short directory
- Dependencies: None.
- Ownership: Toolset coordinator. Runs after TOOLSET-197-4f, which edits coordinator.py.
- Exclusions: No change to which tasks the engine runs once the files agree.
- Planner's call: the archive records a close; a ledger that lags it is bookkeeping the runner can fix deterministically, so it needs neither a model nor the owner (owner, 2026-10-18: autowork "must be able to fix these issues easily").
- Planner's call (2026-10-19 audit; where this differs from the Scope above, this wins): Scope (2) is a repair inside the docs maintainer's transaction (265-16) that calls no model, not a new coordinator planning commit.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-133-f5"></a>

### TOOLSET-133-f5 — Define minimum-sufficient regression protection and test budgets

- [x] TOOLSET-133-f5 — Define minimum-sufficient regression protection and test budgets
- Short: Define minimum regression protection
- Status: done
- Goal: TEST-SUITE — Keep test execution efficient without losing regression protection.
- Sources: [accepted skill plan](docs/project.md#discoverable-test-optimization-suite-skill), [existing method](skills/engineering/local/test-suite-optimization/PROTOCOL.md), [shared budget](skills/shared/ENGINEERING-CYCLE.md#test-budget), [current suite audit](docs/test-suite-audit.md).
- Touches: skills/engineering/local/test-suite-optimization/PROTOCOL.md, skills/shared/ENGINEERING-CYCLE.md, skills/engineering/SKILL.md, adapters/skills/engineering/SKILL.md
- Scope: Strengthen the one existing protocol: behavior/risk matrix, proportional timing/flake/history/diff-coverage evidence, critical-module mutant detection and uncertainty, removal-to-retained-oracle mapping, consolidation, repository-specific runtime/new-case budgets, bounded quarantine, review rules and sound optional impact selection. Default to audit; explicit apply or existing implementation authority permits bounded verified edits without another ceremony. Preserve legacy selector and upstream pins. Supersede count-driven or blanket one-test/no-config-test rules with minimum sufficient detection and justified unique-risk exceptions; do not weaken safety obligations.
- Acceptance: Canonical guidance covers all accepted method decisions without requiring all tools/history to exist, manufacturing measurements or forcing whole-suite experiments for every audit. It distinguishes mutant outcomes, equal coverage from equal behavior, stable never-failed regressions from valueless tests, and assertless smoke/contractual interactions from meaningless checks. Each deletion retains its risk or documents its retirement; named bug traceability survives consolidation. Quarantines have owner/expiry/risk; CI selection retains a fallback/full gate. Independent fixture review includes missing evidence and read-only scope; failures become narrow corrections, not more prose tests.
- Checks: Existing engineering protocol routing check; review the compact behavior scenarios named in the accepted plan; verify relative references and unchanged upstream hashes; git diff --check. No full runtime suite for instruction-only edits and no new heading/phrase assertions.
- Dependencies: None.
- Ownership: Toolset coordinator; preserve active writers and existing suite-audit IDs.
- Exclusions: No test deletions in consumer repositories, automatic all-repository scan, required mutation/coverage dependency, new scheduler, CI weakening, upstream skill edits, commit or publication from this planning invocation.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-278-91"></a>

### TOOLSET-278-91 — A commit kept without its worker's report resumes that worker, not a batch or the merge resolver

- [x] TOOLSET-278-91 — A commit kept without its worker's report resumes that worker, not a batch or the merge resolver
- Short: Retained commits resume their worker
- Status: done
- Goal: PI-RUNNER
- Priority reason (2026-10-19 monitor pass): a stranded commit of this kind (TOOLSET-120-fc) holds its serial path, so TOOLSET-119-2b, TOOLSET-122-27 and TOOLSET-144-c0 cannot start until it recovers.
- Evidence (2026-10-19 monitor pass): a runner stop marks a dead worker's commit `reported` ("commit retained") although the worker wrote no `report.json`. Batches merge such commits without reading reports, so three were held for a conflict; Pi resolved the conflicts, and `--parallel-merged` then refused each with "merged needs the held commit's report.json" every cycle. Writing a stand-in report is not the fix: `test_a_paused_attempt_resumes_without_its_earlier_report` and `test_a_late_report_from_a_superseded_attempt_never_completes_the_retry` require that a commit without its own worker's report never lands.
- Touches: skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/parallel_dispatch.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/worker.py, skills/autowork/scripts/test_parallel_state.py, skills/autowork/scripts/test_parallel_integrate.py, pi-autowork/tests/
- Scope: A slot whose commit has no report of its current attempt is not a batch candidate and is not sent to the merge resolver; its worker resumes on the same attempt with an instruction to write the report for the commit it already made (no reimplementation), or it is held with cause `report` naming what is missing. Already-stranded conflict holds of that kind recover the same way.
- Acceptance: A focused test shows a retained commit without a report is left out of `batch_order` and conflict resolution and resumes its worker once on the same attempt; after the worker writes a matching report it integrates normally. The two adversarial tests above still pass. No report is ever written by the runner on a worker's behalf.
- Checks: `python3 scripts/check.py skills/autowork/scripts pi-autowork/tests`; `python3 scripts/check.py`.
- Dependencies: None.
- Ownership: Toolset coordinator.
- Next action: Reproduce with a stopped worker that committed without a report, then route it to a same-attempt resume before batching.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-290-12"></a>

### TOOLSET-290-12 — One interactive session writes the main checkout at a time

- [x] TOOLSET-290-12 — One interactive session writes the main checkout at a time
- Short: One interactive writer per checkout
- Status: done
- Goal: CLAUDE-CODE
- Payoff: Install the portable workflows in Claude Code.
- Sources: [owner decision](docs/project.md#interactive-checkout-writer-2026-10-20) (2026-10-20); [reliability research](docs/research/orchestrator-reliability.md) (root cause 1: many writers to main and its checkout, 30 fixes); [worktree hook](skills/autowork/scripts/worktree_paths.py) (`hook`, installed as `~/.claude/hooks/worktree-policy.py`); [placement doc](docs/worktree-placement.md); [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) ("Interactive sessions work directly in the main checkout").
- Evidence: on 2026-10-20 one interactive session parked its own work by taking the file list from `git status`, which swept a second session's uncommitted `fleet_view.py` and `tui.py` into its wip branch and reset them in the checkout; the second session found its edits gone and re-applied them. Both conflict-marker regressions on main (b69b2d2, 34b7f31) also came from several writers to one checkout.
- Touches: skills/autowork/scripts/checkout_lock.py, skills/autowork/scripts/test_checkout_lock.py, docs/worktree-placement.md, AGENTS.md, CLAUDE.md
- Produces: `checkout_lock.py` as a Claude Code hook (PreToolUse for Edit, Write, MultiEdit and NotebookEdit; SessionEnd) and a CLI `python3 checkout_lock.py status|release [REPO]`.
- Scope: (1) A session's first file edit inside a canonical checkout (not under `.worktrees/`) takes the checkout's interactive-writer lock, recorded under the Git common directory with the session id, its transcript path and the files it has edited; later edits add to that list. (2) Another session's edit there is denied with a reason that names the holder, its edited files and the way out: `EnterWorktree`, or wait for the holder to commit. Reads are never blocked. (3) The lock passes to the next session at once when every file the holder edited is clean (committed or reverted), on the holder's SessionEnd, or when the holder's transcript has been idle for 30 minutes and its files are clean; a holder with dirty files is never released automatically. (4) `release` frees a lock by hand and says whose files stay dirty. (5) Edits inside `.worktrees/` and runner worktrees are not locked; Autowork runners keep their own checks. (6) AGENTS.md, CLAUDE.md and docs/worktree-placement.md say: one interactive writer per checkout; a second session works in `.worktrees/` through `EnterWorktree` until the first commits, and how to install the hook.
- Acceptance: Given session S1 edited `a.py` in the main checkout, when S2 edits `b.py` there, then S2 is denied with a reason naming S1 and `a.py` (`test_checkout_lock.py::test_a_second_session_is_denied_and_told_why`). Given S1 commits `a.py`, S2's next edit takes the lock (`test_the_lock_passes_once_the_holder_is_clean`). Given S1's transcript idle 31 minutes with `a.py` still dirty, S2 is still denied (`test_a_dirty_holder_is_never_released_automatically`); `release` frees it (`test_release_names_the_dirty_files`). An edit under `.worktrees/` is never denied (`test_task_worktrees_are_not_locked`).
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_checkout_lock.py; python3 -m unittest discover -s skills/autowork/scripts -p test_worktree_paths.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: Bash commands that write files are not detected (a workflow guard, like the existing Bash worktree guard, not a sandbox). Pi, Codex and Hermes sessions are out of scope. The user's private `~/.claude/CLAUDE.md` and `~/.claude/settings.json` are the owner's to update by hand from docs/worktree-placement.md. No change to how runners write main.
- Planner's call: a separate hook file beside `worktree_paths.py`, not more branches in it, so the worktree policy stays as small as it is; the lock lives under the Git common directory so every linked checkout of one repository sees one lock.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-117-cb"></a>

### TOOLSET-117-cb — Compare the Pi CLI worker adapter with AgwaB pi-subagent runSubagent on identical fixtures

- [x] TOOLSET-117-cb — Compare the Pi CLI worker adapter with AgwaB pi-subagent runSubagent on identical fixtures
- Short: Compare Pi worker adapter with AgwaB
- Status: done
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [research: runtime adapter](docs/research/pi-autowork-reference-architectures.md#runtime-adapter-overstory--agwab), [Kyle Boas live workers](docs/research/pi-autowork-reference-architectures.md#kyle-boas-reusable-live-rpc-workers), [follow-up boundaries](docs/research/pi-autowork-reference-architectures.md#proposed-follow-up-boundaries), [pi-durable](https://github.com/earendil-works/pi/blob/main/packages/durable/README.md).
- Touches: pi-autowork/, docs/research/pi-autowork-reference-architectures.md
- Scope: Define the small worker-runtime boundary the research proposes (after Overstory's `AgentRuntime`): `launch`, `observe`, `stop`, `resume`, a capability record (live-process reuse, persistent transcripts, reload survival, crash/restart adoption) and normalized events. Implement it for the current Pi CLI path and, in a spike, for AgwaB's `runSubagent` headless backend with a Toolset-owned worktree as its CWD. Owner addition (2026-10-16): also spike `@earendil-works/pi-durable`, first-party and built for crash recovery (commit before showing; `Harness.open`/`resume`; idempotent `requestId` submissions); note it is marked experimental and allows one process per storage. Add per-tool replay safety to the capability record, after pi-durable's `replay: "safe"`: a tool or check that is not replay-safe is not rerun after a crash, the worker is told it was interrupted. Run both against the same fixtures: cancellation, restart adoption, stale results, out-of-order completion, combined-tree verification, cleanup retention, process-group TERM-to-KILL. Qualify `agent_end`/`agent_settled` against the pinned Pi version.
- Acceptance: A written comparison with measured results per fixture and a recommendation; compatibility failures are recorded, not worked around by weakening the contract; the CLI path stays the default.
- Checks: `python3 scripts/check.py`; the comparison fixtures.
- Dependencies: None.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No dependency installed into services or the fleet; no change to the default worker; adoption needs an owner decision.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-288-cf"></a>

### TOOLSET-288-cf — Two runner tests fail only under full-check load

- [x] TOOLSET-288-cf — Two runner tests fail only under full-check load
- Short: Two runner tests fail under load
- Status: done
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [check](scripts/check.py); [runner tests](tests/test_pi_autowork.py) (`test_a_killed_coordinator_restarts_at_once_and_adopts_live_workers`); [integration tests](skills/autowork/scripts/test_parallel_integrate.py) (`test_retry_runs_beside_an_overlapping_worker`); [coordinator](pi-autowork/pi_autowork/coordinator.py) (the `BUSY` outcome); [retry](skills/autowork/scripts/parallel_integrate.py) (`retry_held`).
- Evidence: a full `python3 scripts/check.py` on 2147c130, run while a live runner worked the same host, failed both tests: the restart after `kill` exited 4 with "Repository busy: Repository execution lock is held by a live operation." (the killed runner's engine helper still held the execution lock), and `retry_held` returned `IDLE` instead of `RETRIED`. Each passed alone twice; the retry test passed 12 times in parallel and inside its whole module (146 tests).
- Touches: pi-autowork/pi_autowork/coordinator.py, skills/autowork/scripts/parallel_integrate.py, tests/test_pi_autowork.py, skills/autowork/scripts/test_parallel_integrate.py
- Scope: (1) Find why each fails under load: for the restart, whether `until-empty` treats `BUSY` from a dead runner's helper as final before the helper exits; for the retry, which `IDLE` branch of `retry_held` is taken (capacity, an empty held set, or the plan) and why. (2) Fix the product race if there is one (a restart waits for a dead runner's helper within a bound instead of exiting 4); otherwise make the fixture wait on the state it needs instead of on timing. (3) Record the `IDLE` branch taken in the result so the next such failure names it.
- Acceptance: Given a killed runner whose engine helper still holds the execution lock, when the runner restarts with `--until-empty`, then it waits for the helper and exits 0 (`test_a_killed_coordinator_restarts_at_once_and_adopts_live_workers`, also with the helper delayed on purpose). `retry_held` results for `IDLE` name their branch (`test_retry_runs_beside_an_overlapping_worker` asserts it). Both tests pass in three consecutive full checks.
- Checks: python3 -m unittest discover -s tests -p test_pi_autowork.py -k killed_coordinator; python3 -m unittest discover -s skills/autowork/scripts -p test_parallel_integrate.py -k retry; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No retries or longer sleeps added to the tests to hide the failure.
- Planner's call: queued rather than fixed by hand because live runner workers own all four files.
- Outcome (2026-10-20): the restart flake was the one-shot run treating the killed runner's helper's execution lock as final; it now waits up to `PI_AUTOWORK_BUSY_WAIT` (429eb87a, a test that holds the lock fails on the old code). The retry test was superseded the same day by 5ca0bc35, under which an overlapping retry waits by design (the test now expects IDLE); the failing run predated it.


<!-- archived from TODO.md -->

Source section: Now

<a id="toolset-277-52"></a>

### TOOLSET-277-52 — Restore the offline gate for the picker-policy failures at 171b26b

- [x] TOOLSET-277-52 — Restore the offline gate for the picker-policy failures at 171b26b
- Short: Restore the picker-policy offline gate
- Status: done
- Goal: PI-RUNNER
- Payoff: Restore the offline gate without changing accepted execution policy.
- Sources: [accepted runner contract](docs/project.md#continuous-pi-runner-2026-10-15); [repair evidence and boundary](docs/tasks/TOOLSET-277-52-picker-policy-main-red.md#repair-boundary); [picker policy tests](skills/autowork/scripts/test_picker_policy.py); [Autowork core](skills/autowork/SKILL.md).
- Evidence: MAIN red at 171b26b after last green 3a00a05: `test_picker_policy.PickerPolicyTests.test_core_stays_lean_and_points_to_every_reference` and `test_picker_policy.PickerPolicyTests.test_no_early_exit_and_terminal_results_continue`. Supplied commit window: 171b26b, f057d64, 24748e1, 653998e, ce092d9, 5cfb7f8, 1f6364d, a41e3f0, 42f257a, 07b0338 (the trigger truncated the last to `07b03`). The [receipt and focused reproduction](docs/tasks/TOOLSET-277-52-picker-policy-main-red.md#focused-reproduction) record the full window, exact assertions and six-test exit-1 reproduction at 2c4bf2c: core is 16076 bytes against a strict 16000 limit; test expects version 0.28.1 while core declares 0.28.2. All references are currently linked. No flaky classification is reported for these failures.
- Touches: skills/autowork/SKILL.md, skills/autowork/references/, skills/autowork/scripts/test_picker_policy.py
- Scope: Reconcile the lean-core and stale-version assertions with the current accepted policy. Move detail to existing references as needed, retain all reference links, and preserve meaningful continuation, caller-stop, authority and no-busywork regression coverage. Inspect the cited change window; unrelated fleet, coordinator, state-machine and plan-lint changes are evidence context, not permission to rewrite them.
- Acceptance: The two named failures pass, the core remains strictly below 16000 bytes and links every reference, and coverage no longer rejects a valid policy solely for its incidental patch version. Existing continuation, caller-stop, authority and no-busywork semantics remain intact; no size-limit increase or wholesale assertion removal. The full offline check passes with skips and exclusions reported separately, not counted as passes.
- Checks: `python3 -m unittest discover -s skills/autowork/scripts -p test_picker_policy.py -v`; `python3 scripts/check.py`.
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No product/runtime redesign, live qualification, publication or coordinator-owned planning edits by the code worker. Do not reopen TOOLSET-184-b3 or replay its older candidate.
- Next action: Reproduce the two assertions using repository files, make the smallest policy-preserving repair, then run the focused and full checks. The original runner bundle is not a prerequisite; TOOLSET-234-d4 owns its delivery and the failures reproduce locally.
- Priority reason: The current DOCS-MAINTAINER instruction explicitly puts an uncovered main-red repair first in Now. Preserve every pre-existing task's relative order.


## Retired reporting qualification — 2026-10-20

Owner disposition: retire TOOLSET-011 without claiming qualification. The following original unchecked contract is retained verbatim as history, not executable work or a passing result.

### TOOLSET-011 — Qualify the updated reporting workflow on the affected profile

- [ ] TOOLSET-011 — Qualify the updated reporting workflow on the affected profile
- Short: Qualify the updated reporting workflow
- Status: open; original target environment unavailable.
- Goal: CRON-REPORTING — Verify setup confirmation and scheduled Telegram delivery separately.
- Sources: [accepted reporting qualification](docs/workflows.md#telegram-reporting-qualification), [reporting contract](skills/cron-autowork/SKILL.md), [verification boundaries](docs/workflows.md), archived TOOLSET-010 source delivery.
- Scope: On the original host/profile, install the updated bundle through its supported path. Identify the existing job, preserve its state/scope, verify its requested Telegram route, then inspect the next scheduled result.
- Acceptance: A setup request from another surface confirms once in the intended chat/topic; a scheduled occurrence has attributable execution and Telegram message receipts. Report failed, queued or unverified delivery honestly.
- Checks: Read back installed source and saved route/state; verify the actual setup message and scheduled result/delivery. These live checks are not run.
- Exclusions: No duplicate job, implicit resume, immediate development run, budget reset, push/deployment, USB formatting or real-PC changes. Never substitute another profile.
- Dependencies: TOOLSET-010.
- Environment prerequisite: Original host, affected profile/job and authorized Telegram transport.
- Ownership: Coordinator with that access; no active claim.
- Current evidence: Exact original profile directory and original job ID are absent from this host's root and existing-profile job stores. No replacement job, profile or message was created.
- Next action: Restore access to the original host/profile/job and its authorized Telegram route, then inspect the setup and scheduled delivery receipts.


Retirement disposition: cancelled, not completed; original acceptance remains unmet.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-285-47"></a>

### TOOLSET-285-47 — Harden release-retention and pruning test isolation under concurrent checks

- [x] TOOLSET-285-47 — Harden release-retention and pruning test isolation under concurrent checks
- Coordination: TOOLSET-127-b1 owns broader fixture thinning, not this reported pruning flake. This task has no prerequisite on thinning, main-evidence delivery or product changes; preserve existing Now priority.
- Next action: Start with the named focused test and inspect the existing child ready/input handshake, fixture environment and release .git timestamp ordering; reproduce under isolated and normal concurrent-check conditions, then make a test-only change supported by those observations. Use repository source and saved reports without requiring an owner-supplied receipt.
- Exclusions: No runtime/product-code repair, altered release-retention policy, global /proc suppression, weakened full-check classification, live/model run, publication or coordinator-owned planning edits by the worker.
- Ownership: Toolset coordinator; one writer per affected workspace.
- Touches: pi-autowork/tests/test_release.py
- Evidence: DOCS-MAINTAINER MAIN (flaky test): the full check failed but the named test passed alone on 1f054477d18c7f9af6165c269775267ba99b4ca8, fc3e2f7fe9123273c015cdb47e5fb838c38138be and d575046eed5bcffcd73c8420b3e1c068c28cd65c. Saved reports in the Git common directory: autowork-execution/slot-data/TOOLSET-173-94/attempt-1/report.json records the unrelated pruning failure followed by isolated and component passes; TOOLSET-118-68/attempt-1/report.json records a pruning assertion failure under concurrent runs followed by isolated and component passes. These historical reports do not establish a root cause or current stability. Main is not red for this flaky test.
- Sources: [accepted runner contract](docs/project.md#continuous-pi-runner-2026-10-15); [release regression](pi-autowork/tests/test_release.py); [release retention/pruning implementation](pi-autowork/pi_autowork/release.py).
- Short: Stable release-retention fixture
- Status: done
- Goal: PI-RUNNER
- Scope: Investigate isolation, resource load and fixture timing in test_release.ReleaseCheckTests.test_late_imports_keep_the_selected_release_while_unused_releases_are_pruned. Harden only its test-owned setup, child synchronization, release ordering and cleanup as evidence warrants. Keep a real child importing from its selected old release while newer releases are prepared; do not repair product code.
- Acceptance: `test_release.ReleaseCheckTests.test_late_imports_keep_the_selected_release_while_unused_releases_are_pruned` still proves that a live child keeps its selected release, its late import returns the old API, and unused releases are pruned after the child exits while the newest two remain. Diagnose environment leakage, /proc visibility, filesystem timestamp ordering and concurrent process load as hypotheses, not established causes. Repeated isolated runs, the component module and the full offline gate retain these assertions without intermittent fixture failures; report commands, repetitions and outcomes, including any remaining flake. Preserve conservative production behavior when process usage is unknown; do not weaken assertions, skip cases, inflate timeouts or introduce production test hooks. Reap the child and close its pipes on success and failure.
- Checks: `for run in 1 2 3; do python3 scripts/check.py pi-autowork/tests/test_release.py -k test_late_imports_keep_the_selected_release_while_unused_releases_are_pruned || exit; done`; `python3 scripts/check.py pi-autowork/tests/test_release.py`; `python3 scripts/check.py`; `git diff --check`. Use a fresh short TMPDIR for check runs; these are required checks, not executed evidence.
- Dependencies: None.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-172-92"></a>

### TOOLSET-172-92 — Recover verified managed Hermes checkouts when updates cannot fast-forward

- [x] TOOLSET-172-92 — Recover verified managed Hermes checkouts when updates cannot fast-forward
- Short: Recover managed Hermes checkouts
- Status: done
- Goal: PORTABLE
- Sources: Owner's full-suite failure report and selected automatic-safe-recovery policy; [managed checkout recovery](docs/project.md#managed-hermes-checkout-recovery); update_bundle.py prepare/git and scripts/install_menu.py command-result reporting.
- Touches: update_bundle.py, scripts/install_menu.py, tests/test_update_bundle.py, tests/test_install_menu.py, docs/installation.md, docs/cross-host.md
- Resources: install-transaction — source/profile transaction and installer reporting changes; integration already has one owner and lands one task at a time (TOOLSET-161-17), so this need not run alone. Changed from exclusive by the owner session on 2026-10-18: it had drained the pool for over 12 hours with 17 tasks waiting. Tests use disposable homes only.
- Scope: Implement the cited automatic recovery for verified clean managed Hermes plugin checkouts whose ancestry check fails, using the existing updater's native admission, source binding, profile merge, backup, journal and read-back machinery. Distinguish negative ancestry from actual Git failure and incomplete history; retain the complete old checkout and native profile edits. Dirty, locally advanced, unknown/shared-active or unproven sources defer safely. Improve full-suite summaries to show the updater's structured cause/action, not a closing JSON brace, while keeping successful components and aggregate partial-failure behavior.
- Acceptance: Disposable real-Git fixtures exercise equal/fast-forward and verified rewritten history, shallow ancestry, ahead/diverged local work, unrecognized/dirty/untracked sources, shared live consumers, profile customizations and scan denial. Recovery stages exact trusted main, preserves source/base and user data, verifies publication and reuses the same backups on resume; stale or interrupted writes cannot discard foreign edits or manufacture success. No reset/clean, forced merge/push, active-runtime restart, scanner bypass or unselected scope expansion. Mixed component results retain five successes plus an actionable Hermes error; malformed/non-JSON output has a useful bounded fallback. An unchanged retry is a no-op; preview/skip performs no network/recovery mutation.
- Checks: Planned after implementation: `python3 -m unittest discover -s tests -p test_update_bundle.py`; `python3 -m unittest discover -s tests -p test_install_menu.py`; `python3 scripts/check.py`; `git diff --check`. Extend existing focused fixtures with failure-injection and preservation assertions; new recovery cases have not run.
- Dependencies: None.
- Ownership: Assigned Autowork worker and integration coordinator under normal independent review and canonical delivery gates; do not deploy from the implementation task.
- Context: Existing missing-Pi bootstrap and live reinstall tasks retain their scope and dependencies; this is a distinct updater recovery gap, not a repeat of successful installations.
- Exclusions: No live changes to the reported host or any Hermes profile, credentials, jobs, gateways, services, host plugins or remote branches. Actual installation/adoption needs its own authorized invocation. User-provided paths/logs are evidence, not local-target identity.
- Next action: Add the exact non-ancestor/structured-summary regression and preservation fixture, then implement the supported classified recovery path.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-125-e6"></a>

### TOOLSET-125-e6 — Run inherited execution regressions once

- [x] TOOLSET-125-e6 — Run inherited execution regressions once
- Short: Run inherited regressions once
- Status: done
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [accepted thinning plan](docs/test-suite-audit.md#suite-thinning-plan-2026-10-16), [test budget](skills/shared/ENGINEERING-CYCLE.md#test-budget).
- Touches: skills/autowork/scripts/test_task_execution.py, docs/test-suite-audit.md
- Scope: Replace RecoveryTests inheriting a concrete test class with a fixture-only mixin or helper. DirectExecutionTests retains its 11 named cases and RecoveryTests retains its 25 unique cases. Do not rename or weaken original safety regressions; remove only the 11 duplicate inherited executions.
- Acceptance: Collection changes from 11 + 36 = 47 executions to 36 unique executions; every removed child-class ID maps to its identical retained parent method; setup, action, assertions and branch protection remain equivalent; focused tests and normal gate pass. Record before/after focused timing without promising a suite speedup.
- Checks: python3 -m unittest discover -s skills/autowork/scripts -p test_task_execution.py; python3 scripts/check.py; git diff --check
- Dependencies: None.
- Ownership: Toolset coordinator; one writer per affected workspace.
- Exclusions: No live/model runs, new test framework/dependency, publication, hidden test skips, weakened safety cases or changes outside the named batch.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-135-16"></a>

### TOOLSET-135-16 — Keep bulk planning within its artifact and execution boundaries

- [x] TOOLSET-135-16 — Keep bulk planning within its artifact and execution boundaries
- Short: Keep bulk planning within its bounds
- Status: done
- Goal: BACKLOG — Produce a usable repository backlog for Autowork.
- Sources: [accepted planning handoff plan](docs/workflows.md#planning-only-bulk-handoff-and-skill-recommendations), [shared planning method](skills/shared/RESEARCH-PLAN.md), [handoff contract](skills/shared/PLAN-HANDOFF.md).
- Touches: skills/plan-for-me/SKILL.md, skills/plan-with-me/SKILL.md, adapters/skills/plan-for-me/SKILL.md, adapters/skills/plan-with-me/SKILL.md, skills/shared/RESEARCH-PLAN.md, skills/shared/PLAN-HANDOFF.md, skills/shared/PLANNING-CRAFT.md, __init__.py, adapters/pi.mjs, tests/test_workflow_commands.py, tests/test_portable_package.py, tests/portable_pi.test.mjs, tests/fixtures/planning/, docs/workflows.md
- Skills: None beyond the applicable planning/skill-maintenance workflow; do not load unrelated methods.
- Scope: Make all planner routes load one unambiguous planning artifact/authority contract and produce the full requested batch. Explicit standalone planning narrows the current request despite earlier unrelated implementation authority; an Autowork-owned planning substep returns to its same coordinator. Classify writes by artifact role, including executable Markdown skills. Preserve no-write scopes. Keep complete TODO task bodies, real dependencies, bounded Touches and independent ready lanes; do not start execution when the first task becomes clear. Add the scoped Skills convention reference for later handoff without a new required field. Fix wrapper inconsistencies where inspection demonstrates them; do not claim a hard tool sandbox where the host supplies only instructions.
- Acceptance: Native/portable/compatibility routes preserve request and mode. Disposable behavioral runs for easy fix, bulk request, old unrelated implementation authorization, supporting skill urging coding, questions-only and explicit later execution distinguish their allowed actions. Planning modifies only authorized docs/queue artifacts, represents every requested outcome and leaves unresolved choices scoped. Autowork-owned planning returns without competing workers. Evaluate actual loaded source and tool/change traces; command registration alone cannot close behavior acceptance.
- Checks: python3 -m unittest discover -s tests -p test_workflow_commands.py; python3 -m unittest discover -s tests -p test_portable_package.py; node --test tests/portable_pi.test.mjs; bounded planning behavioral scenarios from the source plan (new, unrun); git diff --check. Use existing fixture cases, no rule-per-phrase tests.
- Dependencies: None.
- Ownership: Toolset coordinator; preserve active worker contracts and unrelated planning batches.
- Exclusions: No implementation in consumer repositories during planning, automatic plugin installation, external execution, paid evaluation, CI weakening, scheduler/service changes, publication, or new mandatory task schema. No dispatch from this planning invocation.


<!-- archived from TODO.md -->

Source section: Next

<a id="toolset-096-7e"></a>

### TOOLSET-096-7e — Qualify the worktree runner live on a fleet repository

- [x] TOOLSET-096-7e — Qualify the worktree runner live on a fleet repository
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Blocker resolution: Repository choice is answered. Remaining work is live qualification through the existing authorized execution workflow with exclusive ownership, not another product decision or permission to escape a worker sandbox.
- Target: The canonical checkout of the current Autowork repository; resolve it from git worktree list, not the assigned task worktree.
- Owner decision: 2026-10-20: Owner selected the canonical Autowork repository, with an alternate fleet test repository also permitted in the private owner record. Use this repository first. Preserve no-push and no-Hermes-job-change exclusions; do not launch a competing runner.
- Short: Qualify the worktree runner live
- Status: done
- Goal: PI-RUNNER
- Sources: [usage](docs/cross-host.md#run-autowork-continuously).
- Scope: Run the released runner on a fleet repository alongside its Hermes jobs (owner's choice) until it ends a session, and record what it completed and how the end-of-session merge went.
- Acceptance: `runs.jsonl` and the repository's main branch show completed tasks merged at the end of a session, or a `Merge pending` with the exact reason and the branch kept; no push by the runner; the repository's uncommitted changes untouched.
- Checks: `runs.jsonl`, runner output, `git -C <fleet-repo> log` and `worktree list`.
- Dependencies: TOOLSET-095-48.
- Ownership: Toolset coordinator on the owner's request.
- Exclusions: No push; no change to the repository's Hermes jobs.
- Outcome (2026-10-20, closed by the owner): qualified by this repository's own released runner, which ran continuously for 54 hours, ended sessions and merged them into main (100 session merges in its runner.log; completed tasks in runs.jsonl). A fresh worker found nothing left to change. The "no push" exclusion no longer applies: the runner pushes main by design since then.
