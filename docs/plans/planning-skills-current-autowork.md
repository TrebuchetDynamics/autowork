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
