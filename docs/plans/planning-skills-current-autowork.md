# Planning skills for current Autowork

## Scope and decisions

Status: Accepted

Owner request: “improve plan skills to work better with new autowork”, through standalone Plan For Me. This accepts investigation and a saved improvement batch, not executable-skill/code/fixture edits, implementation dispatch or schedules. The bounded fixes below are delegated planner calls, not separately selected owner options.

Use the existing `TASK-STORE-HARDENING` goal, preserving its source, priority, focus, status and existing IDs/order. Completed TOOLSET-301-32 (store cutover), TOOLSET-306-3a (allocator), TOOLSET-304-9e (concurrency), TOOLSET-305-7b (closure) and TOOLSET-314-23 (literal inputs) are not reopened. The invocation's obsolete TODO/goals paragraph is itself a source defect to fix, not authority to restore a retired queue.

**Chosen approach:** correct observable entrypoint/shared-contract drift and modernize the existing evaluation specimens. Keep Plan For Me decisive and Plan With Me interactive only for consequential unresolved intent. Do not rewrite every skill, install another framework, create a second queue/registry/approval system, or make every plan execute an experiment. No new task fields, receipts or mandatory continuation artifacts.

Success is coherent task-store guidance, feasible unattended tasks, and an honest way to test those instructions. It is not a measured productivity improvement or model-adherence claim. Existing public names, aliases, argument bytes, privacy, origin routing, authority boundaries, review/checks and owner stops stay intact. Preserve the now-landed bare-command autonomous-discovery marker and its tests; a queue-paragraph correction must not restore missing-goal interviews for bare invocations.

## Source evidence

Refreshed source baseline: `34aca3f6487eda7d0c45589cdd4c1b33cbe2d3fa` (earlier saved baseline `3f6a971a244550e750d27997c6e9c695d213f306`). Read-only source reviews corroborated these gaps; no product tests/model evaluations ran in this planning pass.

- `__init__.py::_invoke` currently still injects “TODO.md is the central work queue” and goals.json writes for native Plan For Me/Autoresearch. `skills/plan-for-me`, Plan With Me and Docs Sync already use `tasks/`. The actual invocation reproduced the stale paragraph.
- `skills/plan-for-me/SKILL.md` lines 105–107 and `skills/shared/TODO-WORKCENTER.md` lines 129 and 173–175 omit required manual-close flags. `task_commands.py::add_parser/cmd_done` requires `--by` and `--reason`; the portable Plan For Me and maintainer prompt already have the correct command and manual/not-verified meaning.
- The work center lines 79–82 specifies two hex characters and an absolute collision guarantee; `task_commands.py::new_id` and `tests/test_task_commands.py` implement eight hex characters for new IDs while preserving legacy IDs.
- `PLAN-HANDOFF.md` lines 88–95 overstates protection of an earlier agent read. The CLI's operation-local conflict check is not a replacement for `show ID --worktree` → `record_revision` → `--expect REV` across separate calls. Literal JSON preserves prose, not freshness.
- `PLANNING-CRAFT.md` lines 156–170 and work-center overlap wording overstate file serialization and demand extraction for long/hot files. `parallel_plan.py::plan` gates shared hot production files at `HOT_TASKS = 3`; cold files/directories/globs rank, and `test_module` excludes test modules from that gate. Dependencies remain product prerequisites, not write-set scheduling hints.
- Craft's new-test-file requirement conflicts with `parallel_dispatch.py::prompt`, which prefers an existing public test seam and at most one focused test per changed behavior. Its check wording also conflates affected landing checks (`main_check.landing_check`) with main's separate full gate.
- `task_select.why` reports committed-store selection eligibility/position, not running capacity, resource/ownership admission or dispatch. `task_queue.selectable(requested=...)` filters supplied IDs in supplied order; it does not derive a per-goal frontier. The coordinator reconciles a named slice with current dependencies/ownership.
- `tests/fixtures/planning/scenarios.py`, `interviews.py` and their README still seed/allow only TODO-era owners. Correct `tasks/items`/`tasks/goals` writes would be classified outside planning owners. These are manual evaluation aids, not offline behavior proof.

Host capability discovery returned prepare API 4. Native `tasks prepare` reported READY, a running task-store-aware consumer, no drafts and unchanged checkout bytes. Existing unrelated goal-without-work and legacy-audit diagnostics remain outside this batch. Unrelated archive deletions are preserved; no installation, live profile copy or runtime recovery is included. Source gaps were rechecked on the pinned current baseline.

## Task A: correct the injected planning request

Status: Accepted

Replace only the stale native queue paragraph in `__init__.py::_invoke` with `tasks/` persistence through Docs Sync and `autowork tasks`, preserving IDs/order, explicit no-write scopes and the no-implementation/no-timer boundary. Preserve its namespace/command applicability; do not force the paragraph onto foreign plugins or change routing, arguments, challenge mode or destinations.

Own `__init__.py`, `tests/test_plugin.py` and `tests/test_workflow_commands.py`; preserve and verify existing `tests/test_plan_for_me_discovery.py` assertions without redesigning its route. Extend existing public command-injection cases, rather than introducing a new router: actual injected messages must use the native store and reject imperative legacy-ledger writes; literal user arguments mentioning old filenames must still survive unchanged. Keep foreign namespaces untouched and retain boundary/alias/origin assertions.

Planned check: `python3 scripts/check.py tests/test_plugin.py tests/test_workflow_commands.py tests/test_plan_for_me_discovery.py`.

## Task B: make the task handoff match the CLI

Status: Accepted

One owner updates `skills/plan-for-me/SKILL.md`, `skills/shared/TODO-WORKCENTER.md` and `skills/shared/PLAN-HANDOFF.md`, with proposed focused `tests/test_planning_cli_contract.py`.

- Use `autowork tasks done ID --by WHO --reason TEXT [--evidence REF]` for manual planning closeout; it writes no verification receipt. Explain ordinary dependency satisfaction versus `verified_depends_on`/goal qualification; never manufacture a waiver or owner qualification. Do not manually close implementation acceptance to make the queue green.
- Describe the existing eight-hex allocation without an impossible zero-collision promise; preserve full existing identifiers rather than normalize them or reopen allocator work.
- Use literal JSON for prose. After a material earlier read, carry its `record_revision` into the supported `--expect` update; on refusal reread/reapply the attributable delta, not a stale full snapshot or blind retry. Keep operation-local checking distinct from this cross-call protection.
- Correct shared work-center scheduling/check wording to the actual hot-production/test exemption and focused/affected versus full-main distinction. Task C owns the corresponding craft guidance, so do not promise that shared paths always serialize.
- Say `why` proves committed-store selection eligibility/order only. Admission, ownership, capacity and actual dispatch are separate observations; an isolated branch passing checks is not consumer delivery. Correct the named-slice frontier claim: reconciliation is coordinator work, not a new CLI guarantee. Preserve same-coordinator return and no extra acceptance ceremonies.

Use current Docs Sync capability/prepare handling, including its API-4 minimum, without copying its conversion matrix into every planner or repeatedly preparing unchanged inputs. Force conversion, runtime activation, live workers and package refresh remain under their existing authorities/owners.

The new offline test should exercise corrected documented command forms against the real CLI in private native-store Git fixtures, not merely assert desirable words. Cover required close flags/manual provenance, literal prose and stale revision refusal, ID compatibility, and selection-not-dispatch wording. Existing `test_task_commands.py` cases are the runtime oracles; do not duplicate every CLI test. The portable Plan For Me already has valid closure syntax; parity inspection should retain it, not churn it.

Planned checks: `python3 scripts/check.py tests/test_planning_cli_contract.py tests/test_task_commands.py tests/test_task_touches_contract.py`.

## Task C: remove unnecessary decomposition and check work

Status: Accepted

Update only `skills/shared/PLANNING-CRAFT.md` and proposed `tests/test_planning_decomposition_contract.py`. Replace blanket extraction at approximately 1,500 lines/three tasks with evidence-based cohesion, conflict-cost and testability guidance. A bounded fix may stay in a large file; report overlapping writes honestly. Preserve accurate hot-production scheduling, test-file exemption, real resources, protected paths, shared-registry ownership and true prerequisite edges. Shared tests and cold file overlap do not create fake product dependencies.

Prefer extending the existing public test seam; a new focused file is an option when it improves ownership/discovery, not a universal prerequisite. Keep the worker's at-most-one-focused-test-per-changed-behavior budget and the exception for instruction-contract guards: here the guard is the behavior being changed, not a demand for tests on every prose edit. No broad test renames, source extraction or invented preflight task is authorized by this instruction change.

Describe focused task checks, affected landing qualification and main's separate full check accurately. Preserve task-required commands and independent review; do not waive required checks or run the full repository gate repeatedly because a file is large.

Pin narrow positive/negative instruction-contract examples against the current scheduler/worker prompt: a small large-file fix without unrelated extraction, cold/test overlap without fabricated dependencies, a genuinely hot production conflict, and public-seam focused verification. These are source-contract regression tests, not simulated model output or proof of faster workers.

Planned checks: `python3 scripts/check.py tests/test_planning_decomposition_contract.py tests/test_task_touches_contract.py pi-autowork/engine/test_parallel_plan.py pi-autowork/engine/test_parallel_plan_hot.py`.

## Task D: make the evaluation specimens use the current store

Status: Accepted

Own `tests/fixtures/planning/scenarios.py`, `interviews.py`, their `README.md` and proposed `tests/test_planning_specimens.py`. Build a disposable real Git specimen with valid `tasks/goals/FORMAT.md` and existing task ID `FMT-01`, using the current task CLI. Retain FMT-01 scope/history and preserve the existing easy/bulk, all-nine-known-outcomes, no-write, tempting-skill, old-authority, coordinator-return, challenge, stop/resume and later-explicit-execution cases. Use current bytes from the actual chosen native/portable entrypoint.

Seed/commit the builder's baseline before evaluation; the evaluated model still has the existing no-commit/no-network/no-install/no-dispatch restrictions. Treat read/write planning owners as `docs/plan.md` and native item/goal records; disallow hand-written receipts, code/test/skill edits, unknown artifacts and blanket `.git/**` exemptions. No-write cases allow zero changes, including metadata/scratch. Distinguish task-command coordination effects from dependency lockfiles; retain index/ref/object/inventory observations so side effects are disclosed rather than silently ignored. Later execution is checked against its separate phase-one baseline.

Keep legacy migration separate and explicitly labelled only if a deliberate migration case is retained; do not make it the default specimen or hand-convert records. The offline regression prepares/inspects private specimens, validates the native seed, preserves FMT-01 and demonstrates that a valid item/goal edit is not flagged while receipt/implementation/no-write violations are. It runs no model. README separates specimen mechanics/registration/source guards from actual host/model evaluation and installed-copy freshness.

Planned check: `python3 scripts/check.py tests/test_planning_specimens.py`. The existing manual model-evaluation commands remain optional and unrun; this plan does not authorize installing providers or paid/live runs.

## Batch, verification and delivery

Owner selection in this occurrence: **both planning-instruction fixes and the existing Src refactor refresh, with instruction fixes first**. Save the complete known batch: these four records plus the seven existing Src IDs, not another discovery or rolling-planning task. The instruction records retain their relative order and now lead selection at ranks 1000–4000, before Src foundation rank 6000. All pre-existing consumer tasks, goals, history and unrelated ordering are preserved.

All four outcomes are known now: save one batch without a rolling planning successor. No dependency is needed among these four instruction slices. The later native-plugin relocation consumes Task A's corrected injected-request contract; record that producer edge there, not fake edges between the instruction slices. The four slices have disjoint production/fixture/test writes; shared existing check modules do not make them dependent. Current active owners can still constrain actual integration, especially the plugin's shared top-level file; respect fresh source and live ownership rather than promise immediate dispatch.

Saved tasks (full IDs; all retain the existing goal and append after existing order):

- Task A — `TOOLSET-375-da53c314`: correct injected queue instructions.
- Task B — `TOOLSET-376-79c94947`: CLI-aligned task handoff.
- Task C — `TOOLSET-377-e8117892`: evidence-based decomposition and check budget.
- Task D — `TOOLSET-378-9bb8d577`: native-store evaluation specimens.

Every implementation slice runs `python3 scripts/affected_tests.py --run` on its actual change base (use supported `--base` when needed) plus its focused checks. Proposed new tests are in-scope to create and unrun, not unavailable external prerequisites. Retain negative guard cases and original public assertions. Do not run full directories/full check for these focused changes; main owns its separate full check.

Pre-mortem: (1) fixing prose while the live command still injects legacy writes → Task A actual-message guard; (2) a shortened handoff loses freshness/closure/authority → Task B real-CLI examples and preserved boundaries; (3) relaxation becomes absent checks or permissive fixtures → Task C scheduler/worker guards and Task D negative inventories. No task changes runtime task schemas, scheduling algorithms, dependency/closure semantics, installation or live state.

Planning handoff validation covers native task/doc checks, exact accepted anchors, unchanged old records/order/goal fields, clean candidate closure, privacy/whitespace and repeat-pass stability. Planning checks do not claim the future skill changes or tests passed. A scoped local commit awaiting canonical writer protection is not queued in the consumer; verify current canonical inclusion and exact records before claiming receipt or execution. Installed copies/reload and actual model behavior remain NOT_CHECKED, not presumed from source edits.

Prior builder check: an independent read-only reviewer found “nothing important left” against the saved four-task batch and pinned source. It confirmed disjoint write lanes and no missing prerequisite; actual dispatch/integration still needs current ownership checks, especially for Task A's `__init__.py`. This review executed no tests or models and grants no implementation authority.

## Refresh decisions and limits

The current occurrence saves both document owners and all 11 retained records. Planner's call: correct the source-proved instruction contradictions before relocating their owners; use rank/section priority rather than a blanket phase gate. Src foundation remains technically independent, while native plugin relocation has the real injection-contract prerequisite. Keep current goal priorities/focus/status; no new goal, schema or workflow is introduced. Rejected importing old candidates wholesale because it could restore pre-snapshot/async/history/question behavior; rejected implementing during this pass because this is standalone planning. All proposed implementation/fixture/model checks remain unrun. New tests are task-owned deliverables, not an external input or approval hold. No profile installation, executable instruction edit, code change, worker dispatch, timer, push or historical receipt backfill is part of this occurrence.

See [the refreshed Src owner](structural-audit-2026-10.md#sdd-maintainability-refactor) for its seven-slice graph, current regression owners and changelog-composition decision.

## Decision-complete Plan For Me

Status: Accepted

Request: “improve plan_for_me skills to plan and leave no decisions on the table.
It causes stallness later”, explicitly through standalone Plan For Me. This section
accepts the requested planning scope; the design below is delegated planner judgment,
not evidence of separately approved implementation. Save this batch and stop.

Goal: every ready task contains the consequential choices needed to finish without
another design interview. No guarantee against unknown failures or unavailable
external inputs. Non-goals: runtime scheduler/schema changes, removing owner gates,
new planning frameworks, mandatory experiments, exhaustive code prescriptions,
installation, publication, worker dispatch or rewriting unrelated skills.
Anti-goals: invented approval, silently relaxed acceptance, tests represented as
model-behavior evidence, and a new bureaucratic gate that itself stalls execution.

### Evidence and chosen approach

Planning baseline: `4462f2fae2c8ed359fb1456e24ffe23b9e71a825`. Earlier sections retain
historical baselines and completed records; they are not reopened by this request.

- `skills/shared/RESEARCH-PLAN.md` and `PLAN-HANDOFF.md` already require resolving
  consequential choices. Add the missing closure procedure there rather than
  another workflow. No new CLI, receipt, registry or required task field.
- `PLANNING-CRAFT.md` says “Facts are yours, decisions are theirs” and sends
  consequential trade-offs to the user, while its unattended-worker section calls
  non-owner choices planner decisions. Its builder triage has answered/minor/theirs
  but no explicit evidence-resolvable consequential engineering category. Clarify
  mode/authority, not merely add a stronger adjective to the entrypoints.
- That builder check asks for unavailable inputs/checks, but readiness also needs
  a disposition for each finding. `PLAN-HANDOFF.md` already separates metadata
  validation from admission; neither proves that a worker can reach inputs.
- `skills/plan-for-me/references/special-cases.md` already rejects unidentified
  positive mechanisms and distinguishes retained candidates from duplicate work.
  Preserve and generalize those safeguards, not another recovery task generator.
- `tests/fixtures/planning/scenarios.py` supplies native/portable and discovery
  cases; its README explicitly says the inspector is not a decision-quality
  validator. Extend these aids, not a keyword grader pretending to run a model.

Planner calls: use one compact decision map in the existing plan/task body when
material choices exist: choice, selected approach and evidence/reason, rejected
alternative when meaningful, affected task IDs and acceptance/check. This is prose,
not a mandatory template for every small task. Resolve consequential technical
choices within delegated constraints now; leave only reversible coding details to
workers. Missing facts get bounded research; owner-only intent/authority and truly
unavailable inputs remain explicit on affected tasks. Do not infer authorization
from an engineering preference, silence or an Accepted heading.

A ready-task closure pass walks from starting inputs through implementation and
verification to handoff: selected interfaces/data/error/compatibility/migration
behavior where relevant; reachable inputs and setup; bounded prerequisite repairs;
exact checks and success evidence. For every material builder finding, persist a
resolution or mark the affected task pending with the exact missing input and
resume condition. Recheck changed findings, not the whole unchanged planning pass.
New tests/fixtures the task can create are deliverables, not external blockers.
Real live qualification stays separate and unmet; no offline substitute or waiver.

Rejected alternatives: “always ask the owner” preserves the stall; “decide absolutely
everything” invents intent/authority; a scheduler-enforced completeness schema adds
an unreliable gate; mandatory prototypes implement during planning. Existing
conventions and evidence suffice for this instruction improvement.

### Closure contract

Status: Accepted

Task `TOOLSET-398-debf452f` owns `skills/shared/RESEARCH-PLAN.md`,
`PLANNING-CRAFT.md`, `PLAN-HANDOFF.md` and new
`tests/test_planning_decision_closure.py`. Add the decision classification and
closure pass above. Plan For Me chooses evidence-supported engineering trade-offs
within delegated scope; Plan With Me retains consequential intent interviews.
Builder findings have four dispositions: already answered, planner-resolvable,
worker-reversible, genuinely owner/external-blocked. Nothing material remains
unclassified in a ready task. Keep real gates, full-batch persistence, clear-task
lightweight handling and all standalone/no-write/coordinator boundaries.

Begin with failing focused source-contract tests at the new seam, covering the
four dispositions, readiness versus metadata validity, unreachable-input treatment,
no new authority and preserved interactive mode. Implement the shared guidance;
run `python3 scripts/check.py tests/test_planning_decision_closure.py tests/test_planning_cli_contract.py tests/test_planning_decomposition_contract.py`.
These tests guard instructions, not model compliance or reduced stall rates.

### Entrypoint parity

Status: Accepted

Task `TOOLSET-398-472870c6` consumes the closure contract from
`TOOLSET-398-debf452f`. Own native `skills/plan-for-me/SKILL.md`, portable
`adapters/skills/plan-for-me/SKILL.md`, native references `discovery.md` and
`special-cases.md`, and `tests/test_plan_for_me_discovery.py`.
Link/use the same shared closure procedure without duplicating it. Apply it to
focused and discovered frontiers; record planner calls and only affected pending
choices. Do not turn bare discovery into an interview or turn known runtime
continuation failures into new product decisions. Keep existing task reuse and
source-bound recovery, planner-only persistence and stop behavior.

Begin with an entrypoint-parity regression at the existing discovery test seam;
update entrypoints/references to consume the shared rule. Run
`python3 scripts/check.py tests/test_plan_for_me_discovery.py tests/test_workflow_commands.py tests/test_portable_package.py`.
No installed copies, plugin routing, aliases or runtime prompts change.

### Stall-focused evaluation specimens

Status: Accepted

Task `TOOLSET-398-2d05d7ae` independently owns
`tests/fixtures/planning/scenarios.py`, its `README.md`, and
`tests/test_planning_specimens.py`. Add native and portable variants for: (1) a
consequential technical choice settled by repository conventions; (2) a missing
local fixture/setup repair that the saved task may implement; (3) an unavailable
external qualification input affecting only one of two independent outcomes;
(4) unresolved owner-only destructive scope despite technical feasibility; and
(5) a builder finding resolved into the saved contract rather than left as advice.
Use synthetic public examples, explicit seed evidence and expected task outcomes;
no private fleet identities, credentials or fabricated historical failures.

Extend existing specimen mechanics tests first, then seed the cases and document
manual scoring. Offline tests prove valid seeds, native/portable coverage and the
existing forbidden-write protections; they do not judge a model's decisions.
Manual scoring checks saved choices/evidence, scoped holds, exact verification,
independent lanes and zero unauthorized implementation/approval. Require traces and
source hashes for any actual evaluation; proposed model runs remain unrun and
subject to separate host/provider authority. No model provider is needed to finish
this offline slice. Run
`python3 scripts/check.py tests/test_planning_specimens.py`.

### Batch readiness and delivery limits

All three records use existing goal `TASK-STORE-HARDENING`; retain its priority,
focus and status and all existing tasks/history. No rolling planning successor.
The closure and specimen slices are independent disjoint write lanes. Entrypoint
parity depends on the shared closure contract, not on specimen work. Checks may
read common files; that is not a dependency or exclusive-resource requirement.
No live/shared named resource is needed. Observe current writers at execution.

Each implementation task also runs `python3 scripts/affected_tests.py --run`
against its actual change base (`--base REV` when needed). New regressions and all
implementation commands above are proposed/unrun in this planning pass. A future
composed check runs the three focused seams after all slices land; passing static
checks still does not demonstrate fewer stalls in actual model sessions.

Planning checklist: [x] inspect current owners and preserve previous decisions;
[x] choose the bounded design and map every requested outcome; [x] save/read back
all three records; [x] fresh builder check (read-only reviewer: “nothing important
left”, with the dependency/parallelism and offline-proof boundaries confirmed).
Task validation returned `ok: true`, 166 tasks, 18 goals and no drafts. Final
whitespace/source-anchor checks and one scoped planning commit complete persistence.

Check limitation: affected-test selection falls back to the full 156-module
inventory because this existing plan document has no resolved test mapping. Two
attempted runs timed out (120 seconds and 30 seconds); neither is a passing check.
The first also included this review's generated scratch, subsequently preserved
outside the worktree. No further full-suite retry is appropriate for a planning-only
change. Use task validation, source-anchor/structure and whitespace checks for this
batch; no implementation or model-behavior test is claimed passed.
Next executable slice is the shared closure contract; specimens may run alongside
it under later execution authority. This planning branch is not integrated or
published and must not be described as delivered to the live runner.

### Explicit execution and checked implementation

The later owner instruction, “Well autowork has to solve this. Even implementation.
All up to production releases”, transitions this saved batch into execution and
its authorized delivery. It does not retroactively turn standalone planning into
implementation authority or waive genuine live/owner safety gates.

All three slices are implemented. Shared guidance now resolves consequential
engineering choices and every material builder finding; native/portable and
discovery paths consume that same procedure. Ten synthetic stall specimens cover
the five planned cases on both entrypoints, preserving forbidden-write controls.
The prior planning-only delivery statements above are historical, not current
execution holds.

Verification: baseline 37 focused tests passed; new closure, entrypoint and fixture
regressions failed before their changes and passed afterwards. Final composed
seven-module run passed 45 tests. Parent independently reran closure/discovery:
13 tests passed. Fresh independent review found no blockers in the bounded 12-file
implementation. Whitespace checks passed. Affected selection expands to the full
inventory for the fixture README, so no additional full suite was run here; main
owns its fresh full check. Actual model-adherence evaluations remain unrun.

The three records are manually closed with this evidence, not assigned fabricated
coordinator-verification receipts or used to mark the broader goal met. Local
integration, upstream publication and installed-runtime adoption are separately
verified delivery stages; these offline results alone claim none of them.

## PLANNING-INTERACTIVE-01: checked source correction

Implemented against clean source `c7873c8f`, under the later bounded implementation
request, not the historical standalone-planning authority above. Native Plan With
Me's “Save answers and finish the plan” overstated `tasks why` as “can run”; shared
`PLAN-HANDOFF.md` already limits it to committed-store selection. Shared
`RESEARCH-PLAN.md` already returns execution failures to the same coordinator.
The native continuation reference also said “execute the continuation now” without
locating execution outside standalone planning.

Both entrypoints now separate selection from admission/dispatch, disclose branch-local
versus actual canonical-consumer delivery and unassessed runtime/ownership, and return
existing task/attempt/failed-operation evidence for same-coordinator recovery rather
than duplicate tasks or another product interview. The continuation reference returns
ready work to the existing authorized coordinator outside standalone planning,
preserving settled authorization, current no-execution limits and live gates. Existing
interview, stop/resume, delegation, read-only, builder and single-pass rules remain.

Three focused instruction-contract tests extend the existing CLI seam. Before skill
edits, RED ran 7 tests with 9 expected failures/subtest failures, captured in
`/tmp/autowork-plan-with-me-red.log`. The final four-module GREEN ran 22 tests
(7 CLI, 6 closure, 4 decomposition, 5 specimen mechanics), all passing, captured in
`/tmp/autowork-plan-with-me-green.log`. The first composed attempt exceeded the
120-second tool limit after three modules passed; it is not a passing check. Its
remaining specimen process exited before cleanup; the complete rerun passed.
Affected selection preview against `c7873c8f` selects all 159 modules because this
plan has no resolved test mapping; no full suite was run. Main retains its separate
full gate. Task validation passed (172 tasks, 18 goals, no drafts or pending paths).
Changed-link inspection found zero added/changed targets; existing targets are
unchanged. Final `git diff --check` passed and the index has no staged files.

The supplied five baseline and five no-guidance fresh micro-samples already made safe
no-execution/branch-selection handoffs (run IDs remain in the task record). No new
samples/model calls were run. Static RED/GREEN proves source correction only: no
measured model improvement, compliance qualification, installed adoption or consumer
delivery is claimed by those checks. At worker handoff the changes were uncommitted
and unintegrated. Subsequent independent review found no blockers and reran 17 CLI,
closure and decomposition tests successfully; the parent then reran all seven CLI
contract tests successfully. The reviewer confirmed that all five archived baseline
files match `c7873c8f` and link targets are unchanged. Exact-wording guards are source
contracts, not model-behavior proof. Source delivery and installation remain separate;
no runtime, service, installer or publication operation is part of this correction.

## PLANNING-AUTONOMOUS-01: checked source correction

Implemented only the bounded Plan For Me alignment against clean `cf2aefe6`;
Plan With Me, shared contracts and task metadata remain unchanged. Native and
portable entrypoints now classify the observed source/phase: resolve in-scope
engineering choices, return existing failed-operation/task/attempt/candidate
source evidence to the same coordinator for supported recovery, or retain genuinely
unavailable owner/external/physical-access inputs on affected tasks. Runtime failure
alone does not justify acceptance splitting; evidence-backed authorized decomposition
remains available without losing original contracts, acceptance or history.

Both entrypoints limit `tasks why` to committed selection, distinguish branch-local
commits from canonical-consumer inclusion/selection, and disclose runtime/ownership
as unassessed unless observed. Portable preparation reuses Docs Sync's existing flow
without updates, installation or worker interruption. Existing discovery, decision
closure, full-batch, JSON/CAS, live and standalone/no-execution boundaries remain.

Focused source-contract TDD extended the existing CLI seam and retained Plan With Me
coverage: RED ran 8 tests with 30 expected assertion/subtest failures before skill
edits (`/tmp/autowork-plan-for-me-red.log`). The requested five-module GREEN ran
30 tests (8 CLI, 6 closure, 4 decomposition, 7 discovery, 5 specimen mechanics), all
passing (`/tmp/autowork-plan-for-me-green.log`); no attempt timed out. These checks
prove instruction-source and existing fixture mechanics only. No new model samples,
measured adherence/performance, runtime recovery, installation, delivery or live
qualification is claimed. At worker handoff no commit, push, service or
canonical-checkout operation had been performed. Subsequent fresh independent
review found no blockers, verified all 31 local links/anchors, reproduced the
30 baseline assertion/subtest failures versus zero on corrected instructions,
and reran 25 CLI/closure/decomposition/discovery tests successfully.

Task validation passed (176 tasks, 18 goals, no drafts/pending paths). All four
handoff archive files match `cf2aefe6`. Changed-link inspection validated the sole
new target, portable Docs Sync; other link targets are unchanged. Affected-selector
preview against `cf2aefe6` selects all 159 modules because this plan owner has no
resolved mapping (`/tmp/autowork-plan-for-me-affected.json`); no full-suite fallback
was executed. Main retains its separate full gate. Final whitespace/scope checks
passed, with no staged files at worker handoff. The reviewed source is prepared
in the isolated branch; canonical integration must preserve the concurrent writer's
staged and in-progress changes. Source completion is not publication or installation.

## Verified local integration of both planning modes

Both reviewed slices reached canonical `main` at `ae4db256` after the other writer
committed its changes and the canonical checkout/index became clean. The supported
writer lock, fresh ancestor/cleanliness checks, nine-path allowlist and fast-forward
preserved that writer's history rather than incorporating unrelated staged work.
Exact merged-tree CLI/discovery checks passed 15 tests; task validation passed with
177 tasks, 18 goals and no drafts or pending records. Whitespace checks passed and
the canonical checkout was clean. Together with the 30-test source/fixture run and
fresh independent reviews, this completes the local instruction-correction scope.
No full-main qualification, model-adherence improvement, publication, installation,
runtime recovery or live adoption is claimed by this work.
