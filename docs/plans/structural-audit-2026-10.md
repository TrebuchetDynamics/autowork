# Structural audit of the runner, 2026-10-21

A measurement pass over every production Python module (AST metrics plus 60 days of Git
history), the ranking it produced, what was refactored on the spot, and the bounded
follow-up slices queued in the task store under the `CODE-HEALTH-2026-10` goal.

Method: for each module, lines and logical lines; functions over 50 and 80 lines; classes
over 300 lines; a McCabe-style complexity per function (`cc`); nesting depth; broad
`except` handlers; commits and fix/revert commits touching the file in the last 60 days
(`cmt`, `fix`); intra-package import fan-in/out; and which offline test modules name
the module. The script lives outside the repository (nothing permanent was added for
the audit); `scripts/affected_tests.py` and `scripts/check.py` ran the verification.

## Hotspots

Ranked by complexity × change frequency × defect history × operational criticality.
Line count alone was not a criterion: `update_bundle.py` (2051 lines) is a cohesive
installer with low churn and ranks below far smaller runner modules.

| # | File | LOC | Max cc / fns > 10 | Commits / fixes (60 d) | Responsibilities | Risk | Expected ROI |
|---|------|----:|------------------:|-----------------------:|------------------|------|--------------|
| 1 | `pi_autowork/coordinator.py` | 3522 | 128 / 40 | 152 / 106 | loop, dispatch, landing, Git integration, batches, reviews, maintainer, main check, questions, reload | very high | very high: every fix lands here |
| 2 | `pi_autowork/worker.py` | 1198 | 41 / 10 | 52 / 36 | worker process, full-check gate, reruns, review prompt | high | high: gate verdicts decide what lands |
| 3 | `pi_autowork/fleet_view.py` | 1323 | 49 / 14 | 49 / 23 | runner rows, verdicts, questions, readiness, actions, log parsing | high | medium: display, but shared by CLI, TUI and JSON |
| 4 | `pi_autowork/cli.py` | 523 | 63 / 4 | 36 / 17 | argument parsing, startup validation, status view | high | medium: owned by TOOLSET-325-d4 right now |
| 5 | `pi_autowork/main_check.py` | 566 | 33 / 8 | 18 / 14 | main's full check, process liveness, rerun receipts | medium | medium |
| 6 | `pi_autowork/health.py` | 360 | 48 / 5 | 22 / 12 | status files, fleet rows, PID liveness | medium | medium: liveness decides "running" |
| 7 | `pi_autowork/questions.py` | 292 | 51 / 1 | 24 / 19 | BLOCKERS.md questions block | medium | low-medium |
| 8 | `engine/parallel_integrate.py` | 1928 | 118 / 21 | 18 / 9 | integration engine | medium | medium: large, but stable and tested in `engine/` |
| 9 | `pi_autowork/task_commands.py` | 835 | 40 / 9 | 13 / 4 | task-store CLI | low-medium | low: three open tasks already own it |
| 10 | `pi_autowork/tui.py` | 1167 | 20 / 7 | 33 / 12 | Textual screens | low | low: fourteen small classes, low complexity |

Coupling: the package has one import cycle, `command → task_prepare → (command, fleet_view)`,
closed through function-level imports in `task_prepare.prepare` and `task_commands`.
The `engine/` package has none. Shell execution uses argument lists everywhere
(`shell=True` does not occur in production code).

Process liveness is implemented three times with different strength: `health._alive`
(`os.kill(pid, 0)`, no identity), `main_check.alive(pid, started)` (procfs start ticks)
and `coordinator.own_process` (procfs parent chain). `runner.json` records no start
identity, so a reused PID after an unclean exit reads as a running runner in `autowork
status` and the fleet view.

## Refactored on the spot

Both changes are behaviour-preserving extractions inside the coordinator, verified by the
existing characterization suites (`pi-autowork/tests/test_landing.py`, the end-to-end
`tests/test_pi_autowork.py` runner tests) with no assertion weakened.

| Target | Before | After |
|--------|--------|-------|
| `coordinator.py` lines | 3522 | 3341 |
| `Coordinator.cycle` | 238 lines, cc 128 | 23 lines, cc 9, plus nine named phases (largest `finish_cycle`: 47 lines, cc 31) |
| `land_around_edits` | coordinator method, raised the runner's `Finish` | `pi_autowork.landing` module function (267-line module with `recent_owner_paths` and `checkout_operation`), raises `LandingBroken` |
| Functions over 80 lines in `coordinator.py` | 5 | 3 (`settle`, `check_main`, `finish_main_check`) |
| Highest cc in `coordinator.py` | 128 | 68 (`settle`) |

The landing module takes the repository, base branch and state directory explicitly, so the
Git mechanics no longer need a `Coordinator` instance to be exercised.

## Queued follow-ups (goal `CODE-HEALTH-2026-10`)

Each is an independent slice with its own Touches, ordered behind the open tasks that own
the same files today so no two writers meet in one module.

1. One process-liveness helper with start identity, used by health, status and the fleet
   view; `runner.json` carries the start ticks (bug: PID reuse reads as running).
2. `settle`, `check_main` and `finish_main_check` decomposed into named phases, as `cycle`
   was.
3. `worker._run_gate`, `gate_note` and `verify_batch` split into verdict, evidence and
   prompt builders with table-driven tests on recorded receipts.
4. `fleet_view.collect`, `verdict` and `task_rows` split by concern (runner record, main
   check, questions, task rows).
5. The `command → task_prepare → command/fleet_view` import cycle removed by moving the
   readiness-and-service lookup `prepare` needs below both.

## SDD maintainability refactor

Status: Accepted

### Requested scope and authority

The owner clarified that SDD targets **Autowork's codebase**, then explicitly added **`Src/`** to the maintainability/folder/file-structure request. Preserve that capitalization. This amendment supersedes the earlier planner call in commit `e52a6c8b` that excluded a source-root migration; it does not reopen completed TOOLSET-355–359 or discard their fixes. Standalone planning saves this specification and task batch only: no product code, tests, fixtures, skills, installations, live jobs or service changes are authorized in this occurrence.

Reuse `CODE-HEALTH-2026-10` and the existing foundation/supervision/closure task IDs. Preserve goal priority/focus/status, completed receipts and unrelated user ordering. Current source inspection is pinned to `34aca3f6487eda7d0c45589cdd4c1b33cbe2d3fa`; this refresh uses that canonical baseline in an isolated planning checkout. The owner selected both this refresh and the planning-instruction corrections, with instruction fixes first. Those fixes are specified in [the existing planning owner](planning-skills-current-autowork.md#batch-verification-and-delivery). Earlier audit measurements above remain historical, not current complexity scores.

Use the existing engineering SDD protocol at `1be8e34187e34647bb83adc3a1323b26ae6f6abe`, verified SHA-256 `c4b97ce3d7f24be0e67fd612c7595f65504872e3a9f8d338d098b2363fdb66ef`. Its application is this explicit ownership/interface/migration specification with behavior-to-oracle contracts before movement. It adds no repeated human phase gate, framework, spec registry, second queue or permission ceremony. `tasks/` remains the work store; do not recreate TODO.md/goals.json.

### Target ownership and alternatives

**Planner's call:** real core Python implementations move under root `Src/`; existing entry files become compatibility boundaries, not duplicate implementations. Retain host-specific adapters, shell/tooling scripts, tests/fixtures, skills, manifests, docs, assets, tasks and runtime data in their established owners. Do not rename every test or reorganize every small module merely to populate folders.

```text
Src/
  autowork_bootstrap.py                 # stdlib-only layout/loading compatibility
  autowork_runtime/
    __init__.py                        # inert
    plugin.py                          # implementation formerly root __init__.py
    bundle.py, autoresearch_commands.py, workflow_commands.py
    runtime_defaults.py, telegram_menu_policy.py
    install_skills.py, setup_bundle.py, setup_preflight.py, setup_runtime.py
    install_omh.py, install_graphify.py
    update_bundle.py, update_bundle_native.py
  pi_autowork/
    __init__.py, layout.py              # canonical package; explicit path ownership
    coordinator.py, command.py, cli.py, worker.py, ...
    legacy/                            # existing conversion support, not a second queue
    supervision/
      __init__.py, main_checks.py
    engine/
      __init__.py, task_store.py, parallel_state.py, parallel_integrate.py, ...
      integration/
        __init__.py, closure_documents.py

autowork_bootstrap.py                   # tiny release-local bootstrap shim
__init__.py, bundle.py, setup_*.py, ...   # stable native entry namespace loaders
pi-autowork/
  bin/autowork                         # stable public command
  pi_autowork/                         # package bridge + old executable adapters
  engine/                              # old flat-name/CLI adapters + existing tests/support
```

Two **standalone distributable hooks** remain implementation owners at `pi-autowork/engine/worktree_paths.py` and `checkout_lock.py`: docs/worktree-placement.md explicitly supports copying each single file to a user's hooks directory. Do not turn them into non-standalone source-dependent shims. Canonical engine use of worktree_paths is loaded once from that exact selected-root file under its canonical name, with the flat alias pointing to the same object. These two explicit origin exceptions are not a general legacy-source fallback. `store_fixture.py`, `offline_fixtures.py`, test files and fixtures stay test support outside Src. `agent_commit.sh` retains its public path. `adapters/pi.mjs` remains the existing host integration adapter, not a duplicate Python runtime; its package entry contract is unchanged.

Rejected: an empty/cosmetic Src folder, only the two helper extractions, wholesale deletion of old entry paths, detached `from ... import *` facades, and a new wheel/editable-install prerequisite. A conventional re-export for native plugin functions would break their module-global patch seams and path-based host loads. A generic eval-based loader for the runner would instead duplicate canonical module identity. Use the narrowly distinct native namespace and runner package strategies below; do not combine their rules implicitly.

### Layout and source-loading contract

The root bootstrap shim loads only its own `Src/autowork_bootstrap.py`, preserving one bootstrap identity for that selected root. No cwd/Git-root search, site-packages borrowing, persistent engine-directory sys.path insertion or installed-code fallback after selection.

`activate(root: Path) -> Layout`, `load(root: Path, module: str) -> ModuleType`, `run(root: Path, module: str, argv: list[str]) -> int` form the runner boundary. `root` is the resolved selected toolset, never the target repository. Layout exposes the toolset root, `Src/`, canonical runtime/engine roots, the compatibility component `<root>/pi-autowork`, exact public Python entrypoints, resource paths and actual implementation paths. `Layout.python_sources(root) -> tuple[Path, ...]` is sorted bounded Python discovery, excluding test/fixture/bytecode paths and escaping symlinks while supporting a linked selected root. No writes or process/model calls.

Runner rules:

- Canonical names are `pi_autowork.*` and `pi_autowork.engine.*`. The old package bridge has **only** the canonical package search path. Relative/qualified internal imports replace engine-directory sys.path insertion. Old flat engine imports alias the canonical module object, preserving exception, class, mutable-global and monkeypatch identity in both import orders.
- Resolve/import from the selected tree only, validate origins, and reject an already-bound runner package from another root. Supported release switches still exec the target release before import; never silently return release A's cached dispatch when asked for B. Preserve selected-release lock/pruning/child inheritance and the environment meanings of PI_AUTOWORK_TOOLSET/COMPONENT/PACKAGE/SCRIPT.
- `run` uses explicit internal adapters for the existing terminal CLI blocks, not runpy/exec of the canonical body again. Retain public main signatures. An internal `_compat_main(argv) -> int` may preserve each original terminal block's argv/stdin/KeyboardInterrupt/exception/exit behavior. Cover every currently executable old Python path, not just command/cli. Copied standalone hooks keep their current terminal blocks instead.
- Do not spoof canonical implementation `__file__`. Replace path arithmetic in moved callers with Layout: selected-root pi_runtime/main_check/autowork_run/TUI/agent_commit entrypaths, resources, subprocess commands and worker source fingerprints. Main-check launch uses its **public Layout entrypoint**, not the relocated `main_check.__file__`. Dispatch/workspaces must stop loading the same engine body under alternate spec names.
- Keep literal `STATE_SCHEMA` and `STATE_SCHEMA_READS` compatibility metadata in the old parallel_state.py path: older releases inspect it as text. Match the canonical literals without changing values or receipt/state schemas.

Native plugin/root-file rules:

- `_compat` responsibilities live in the shared Src bootstrap: `execute(namespace, source_relative)` compiles the owning source with its actual filename and executes it **in the existing caller module dictionary**. Preserve caller name/package/spec/package path and the original root-entry `__file__` deliberately. Inject `_AUTOWORK_LAYOUT` and `_AUTOWORK_COMPAT` for the selected root; native peer calls use `_AUTOWORK_COMPAT.peer(globals(), name)`, not a globally cached unqualified bootstrap import. Root shims load that bootstrap by exact tree-local path and native bootstrap instances are root-keyed; the runner alone binds its one-root bootstrap name. Root files contain loading only, not copied fallback bodies.
- This native-only execution strategy preserves plugin package names, `handler.func.__module__ + '.bundle'`, path-based exec_module callers, and patches to bundle.start_update, setup/update collaborators, ROOT and SKILLS_DIR. Do not detach functions, replace sys.modules alone, or import the same native body under an additional public implementation namespace.
- `peer(namespace, name)` binds unqualified native sibling dependencies to the captured release root/current plugin package (or a root-keyed private standalone package), not a cached top-level module from another release. It resolves the same-root public peer entry, which may still be its legacy implementation until that independent slice migrates; a migrated shim missing its declared Src payload **fails**, never falls back to old/installed code.
- Required-file/copy validation follows migrated shims' literal source paths and bootstrap closure. Each native migration carries its own copied fixtures; callers are never expected to obtain a missing handoff or arbitrary manifest from someone else. Existing shell-wrapper-only discovery fixtures remain standalone shell cases.

### Compatibility foundation — existing TOOLSET-368-24bdb225

Status: Accepted

Replace the earlier proposed source_layout-only foundation with the common bootstrap/Layout, source ownership/import mapping and packaging/test support needed by all moves. It may create inert source package initializers and private fixture examples, but must not redirect production entrypoints to incomplete canonical packages. Existing production loading remains intact until its owning migration cut lands.

Own `autowork_bootstrap.py`, `Src/autowork_bootstrap.py`, inert `Src/autowork_runtime/__init__.py` and `Src/pi_autowork/__init__.py`; `package.json`; scripts/affected_tests.py and scripts/check.py; focused bootstrap/selection/packaged-fixture tests and one reusable private test-copy helper. Foundation also owns tests/test_install_plugins.py: its shell fixture actually imports copied runtime_defaults.py, so copy the selected bootstrap/Src closure through that helper before root modules become loaders; this is not a standalone shell-discovery exception. This shared foundation intentionally exceeds a five-file heuristic: it is one source/import/selection contract, not an invitation to move all product code in one task.

npm includes `autowork_bootstrap.py`, `Src/autowork_bootstrap.py` and `Src/pi_autowork/` along with existing adapters/legacy entrypaths/resources; it must **exclude** Hermes-only `Src/autowork_runtime/` payloads as it excludes current native root installers. No hooks, install, publication or dependency change. Offline `npm pack --ignore-scripts --offline` in private source fixtures and extracted-package checks prove closure. Archive help/read commands without Git are distinct from immutable runner launch, which still requires a committed Git release.

Keep test locations and shard/discovery keys. Make affected-test selection package/relative-import aware, with explicit old-entry to owning-source edges, initializer/deletion/rename and duplicate-stem cases. An unresolved mapping selects the conservative full inventory; never silently drop tests. Source-reading/AST checks must inspect actual owners, not just thin shims. Shared fixture support copies a complete selected release or an explicitly verified entry/source closure; it does not synthesize product results.

Produces: the loading/Layout interfaces above, real source-selection mappings, source-closure fixture support and passing offline compatibility oracles. All migration tasks consume them. New tests are task-owned deliverables, not missing external prerequisites.

Planned checks: `python3 scripts/check.py tests/test_src_bootstrap.py tests/test_affected_tests.py tests/test_check.py tests/test_portable_package.py tests/test_install_plugins.py`; `node --test tests/portable_pi.test.mjs`.

### Runner and engine relocation

Status: Accepted

After the foundation, one coherent mechanical cut moves the selected-release runner package (including legacy/) and production engine bodies to Src/pi_autowork and its engine subpackage. Its source set is the existing pi_autowork package and engine non-test Python modules, excluding the two standalone hooks and the two named fixture-support helpers. Enumerate that fixed mapping in implementation evidence; no unrelated module redesign. Old component/bin/script/service entry paths remain compatible.

This cut is necessarily larger than the following feature extractions: package bridging, qualified engine imports and process-launch paths must agree atomically to avoid mixed source roots. It does not also move native root modules. Hooks remain standalone; bootstrap origin exceptions/aliases are explicit. Test both old/canonical import orders and old/new release transitions with poisoned cwd/PYTHONPATH, late imports and children pinned to the same release.

Own its old/new runtime source trees, scripts/pi-autowork.sh only if bootstrap plumbing requires it, affected copied-runner fixtures, release/main-check/worker/TUI/source-fingerprint and entrypoint tests, and pi-autowork/README.md. Runner also owns tests/test_task_prepare.py: its AST/import-graph discovery must inspect canonical Src/pi_autowork bodies after relocation rather than pass on compatibility adapters; retain the cycle/refusal/side-effect assertions. Preserve shell discovery preference, target repository identity, inherited ports, birth identity, stop/reload and exception/exit behavior. Compile/probe nested selected source via Layout; invalid nested candidate source refuses without changing the running release. Preserve updater raw tracked-blob hashing/modes: archive validation does not replace source_tree().

Planned checks: `python3 scripts/check.py tests/test_src_entrypoints.py tests/test_pi_autowork.py tests/test_task_prepare.py pi-autowork/tests/test_release.py pi-autowork/tests/test_main_check.py pi-autowork/tests/test_worker_tmp.py pi-autowork/tests/test_tui_mouse.py pi-autowork/tests/test_nested_layout.py pi-autowork/engine/test_worktree_paths.py pi-autowork/engine/test_checkout_lock.py`; repeat packaged-file tests against the **actual migrated modules**, not just foundation sentinels.

### Native plugin and policy relocation

Status: Accepted

After the foundation, move exactly root __init__.py, bundle.py, autoresearch_commands.py, workflow_commands.py, runtime_defaults.py and telegram_menu_policy.py implementations to Src/autowork_runtime (root __init__ maps to plugin.py). Keep original root files as namespace-preserving execute loaders. Characterize registration, policy opt-out, command arguments, namespaced bundle access, menu/config behavior and collaborator patches; preserve root/resource resolution.

Own those explicit source/destination pairs and their existing plugin/bundle/workflow/policy tests. Use the common fixture-copy helper rather than edit another migration's shared fixture implementation. This can migrate beside setup/updater: same-root unchanged peer entries remain reachable, and no caller receives an extra execution authority. No actual plugin load into a live profile is part of verification.

Planned checks: `python3 scripts/check.py tests/test_src_native.py tests/test_plugin.py tests/test_bundle.py tests/test_workflow_commands.py tests/test_telegram_menu_policy.py`.

### Native setup and installer relocation

Status: Accepted

After the foundation, move exactly install_skills.py, setup_bundle.py, setup_preflight.py, setup_runtime.py, install-omh.py and install-graphify.py implementations to their Src/autowork_runtime counterparts (hyphenated public files keep their names; source owners use install_omh.py/install_graphify.py). Keep entry arguments, native paths, installer exception/exit behavior, privacy and full source closure; no actual profile installation.

Update required-file contracts for the migrated bootstrap/source payload and copied-setup/provisioner fixtures. Negative tests show missing source refuses before writes; it must not borrow another checkout. Tests that formerly copied only install_skills.py now copy its actual same-release closure. Own tests/test_complete_setup.py, test_install_skills.py, test_native_provisioning.py, test_setup_runtime.py, test_install_omh.py, test_install_graphify.py and the existing engine integration single-installer-copy fixture. Do not redesign setup stages or broaden installed targets.

Planned checks: `python3 scripts/check.py tests/test_complete_setup.py tests/test_install_skills.py tests/test_native_provisioning.py tests/test_setup_runtime.py tests/test_install_omh.py tests/test_install_graphify.py pi-autowork/engine/test_parallel_integrate.py`.

### Native updater relocation

Status: Accepted

After the foundation, move only update_bundle.py and update_bundle_native.py implementations under Src/autowork_runtime with stable root loaders. Preserve same-root peer loading, raw tracked source closure, native subprocess interpreter/path selection, restart waiter and rollback/lock/transaction behavior. Two native releases may load independently without sharing cached peers/resources; this is distinct from the runner's one-active-root-per-process rule.

Own the two source/destination pairs and tests/test_update_bundle.py and test_update_quiet_restart.py. Installed-profile integration (tests/integration_bundle.py) is not silently executed: offline checks use isolated fixture/mocked host boundaries; installed-host qualification remains NOT_CHECKED. Registration, archive or text guards are not a deployed update acceptance.

Planned checks: `python3 scripts/check.py tests/test_update_bundle.py tests/test_update_quiet_restart.py`; inspect the native integration test's prerequisites before any execution and do not expand into live profile operations.

### Main-check supervision — existing TOOLSET-369-b5db2d3a

Status: Accepted

After runner relocation, move only implementations of remember_reused_main_green, check_main, check_main_reap, check_main_revert_pending, check_main_reuse_result, check_main_wait, check_main_start, passed_on_tree, finish_main_check, finish_main_check_failures and finish_main_check_result into Src/pi_autowork/supervision/main_checks.py (empty initializer). Retain original Coordinator methods/signatures in Src/pi_autowork/coordinator.py.

Each helper receives owner plus its original arguments and keyword-only current git, passed late-bound by the facade. Only check_main_reuse_result also receives keyword-only current coordinator.planning_path; planning_path/PLANNING_FILES remain coordinator policy. Internal phase calls go through owner methods, preserving overrides. No helper object, mixin or copied state. Owner callbacks remain repo/base/state/stop/MAIN_CHECK_WAIT, session_busy, revert_regression, batch_running, tasks, scratch_checkout, job_environment, main_check_port_lease, maintain and push. Keep port leasing, batch ownership, regression mutation and task recovery in Coordinator.

Allowed dependencies are main_check, optimistic, common.LOG and stdlib, never the Coordinator facade. Preserve shared module patch seams, process birth/waitpid/reaping, inherited port-lock FD, receipts, cleanup and result publication order. Use Layout's public main_check entrypoint after relocation; **the previous main_check.__file__ rule is superseded by the explicit Src path contract**. Update the existing AST bound test to inspect extracted bodies and retain behavior assertions.

Planned checks: `python3 scripts/check.py pi-autowork/tests/test_supervision_main_checks.py pi-autowork/tests/test_main_check.py tests/test_src_entrypoints.py`. New focused tests cover facade signatures, late-bound git/planning_path/phase overrides, fresh-import no side effects and local/relative reverse-import rejection.

### Closure preparation — existing TOOLSET-370-02928e38

Status: Accepted

After runner relocation, move receipt_path, receipt_text, live_backlog_id, followup_text, existing_backlog, backlog_target, task_store_rank and the task/receipt/live preparation part of close_writes into Src/pi_autowork/engine/integration/closure_documents.py (empty initializer). Keep original-signature functions on canonical parallel_integrate; old flat public aliases still expose that same module object. Current close_writes also composes changelog_entry: leave changelog_entry and UNRELEASED in parallel_integrate. Its original-signature close_writes facade first calls the leaf preparation, then applies the existing changelog_entry result to that map. Do not introduce a fifth ClosurePorts field or reverse import. Preserve exact changelog placement, replay deduplication and dirty-owner-edit refusal; preparation still performs no writes.

Frozen ClosurePorts has exactly git, passed, task_path, live_items. Construct it per facade call from current parallel_integrate.git/passed, execution.task_path and live_items. Dependency-using helper functions receive keyword-only ports and forward it; pure helpers retain arguments. Read-only preparation returns dict[path,text]. Retain task_store._Document use, exact TOML bytes/order/redaction/contract/tree, committed task reads, working-backlog-first/HEAD fallback, dedup/order/reuse/suffix and notes/backlog/none/unknown follow-up modes.

Allowed leaf imports are stdlib, canonical engine task_store and lazy check_receipt. No host/coordinator, parallel_integrate/dispatch/state or task_execution reverse import. Do not move display_free, pending_writes, close, validated_receipt, integration/recovery/exceptions/retries/cleanup or identity-preserving close_files re-export. Dispatch → integration → writer lock order, second writer check and transaction authority remain unchanged.

Planned checks: `python3 scripts/check.py pi-autowork/engine/test_closure_documents.py pi-autowork/engine/test_parallel_integrate.py pi-autowork/engine/test_close_files.py tests/test_src_entrypoints.py`. This slice also owns edits to pi-autowork/engine/test_parallel_integrate.py. Characterize exact repeat-preparation maps, changelog facade composition and late-bound ports; retain real-Git replay/partial commit/changed contract/writer arrival/rollback/no premature cleanup assertions. Update source-reading tests to real owners, never thin-wrapper-only proof.

### Current-source preservation amendment

Status: Accepted

This is a planning refresh, not implementation or historical receipt maintenance. The earlier seven-slice architecture and API contracts remain the planner's chosen approach. Imports and test oracles are refreshed against the pinned current source, not candidate-era bodies. No graph artifact was available; direct source inspection and independent read-only reviews provide this evidence, not a graph rebuild.

- Foundation source/package discovery includes the actual nested runner bodies, including task_snapshot.py, task_status.py, tui_reads.py, blockers_report.py and review_policy.py. Its import/closure fixtures must not import Textual, start an executor or require native-only payloads merely for portable help/read checks. Src/autowork_runtime remains excluded from the npm payload.
- Runner relocation owns those five modules and the task_snapshot/fleet_view/blockers_report/coordinator flat engine import seams. Remove their engine-directory path insertions while preserving same-object TaskStore/StoreError/task_queue aliases and fleet_view.TaskRow identity with task_snapshot.TaskRow. Preserve capture's pinned committed membership, repository/contract/attempt joins, independent pending/question provenance and stale-versus-empty states. Preserve Coordinator.status caching by resolved workspace/revision and its engine-reported revision. command.runner_json must continue omitting display-only snapshot/preparation/provenance/error fields from legacy JSON.
- TUI code_stamp observes actual selected implementation files; TUI reload exec uses Layout's public TUI entrypoint, not relocated __file__. Coordinator review_fingerprint retains all current helper bytes; review_policy.version continues hashing itself and worker.py. Source-reading fingerprint fixtures inspect real implementation owners.
- Preserve four physical reader slots, replaceable pending tokens, cancellation not freeing a physical thread, epoch/generation admission and UI-loop-only publication. Retain Open versus Closed/history, unknown versus explicit manual closure, full copyable diagnostics, Blockers read-only behavior and existing question/failure-policy semantics. Preserve task-delete warnings with proceed, after=None journal recovery, externally recreated-record protection, technical incident/rework-budget retention and Git-read failure isolation. These are regression invariants, not new feature work.
- Runner owns current task_snapshot/status_provenance/status_cache/task_history/tui_reads/blockers_report/fleet_view/review_policy/questions/maintainer/task_transactions suites, task command/migration suites, and engine task_queue/parallel_status/parallel_integrate suites. Keep tui_pilot.py, task_history_pilot.py and blockers_pilot.py in their current test directory. Existing wrappers own their pinned Textual setup; stdlib scheduler tests must not inherit that dependency.
- Native plugin relocation consumes TOOLSET-375-da53c314's corrected queue injection and preserves the already-landed bare Plan For Me discovery marker, workflow-command assertions and test_plan_for_me_discovery.py. Setup/updater contracts and supervision's eleven-method late-bound ports remain unchanged.
- Shared test_parallel_integrate.py edits among runner/setup/closure require serialized writers. They do not create extra product dependency edges. Narrow each edit to the fixture or actual-owner assertions required by its own move.

Pre-mortem guards: (1) source-only shims falsely pass ownership/fingerprint checks — foundation/runner actual-owner AST, nested syntax and source-byte fixtures; (2) relocation restores pre-freshness UI or task mutation semantics — runner's current snapshot/reader/history/Blockers/transaction suites; (3) closure extraction loses changelog composition or moves write authority — closure's exact-map/changelog/dirty-writer and reverse-import guards. Existing mandatory review, tests and ownership protections stay intact.

All future implementation checks remain planned/unrun in this occurrence. Planning validation does not qualify source relocation, installed profiles, model adherence or live operations. The advisory SDD pilot remains separate and is not a prerequisite or runtime-adoption authority.

### Batch, verification and completion

Saved graph (full IDs): foundation `TOOLSET-368-24bdb225`; runner `TOOLSET-375-8e02693d`; native plugin `TOOLSET-376-49034161`; native setup `TOOLSET-377-689cb14e`; native updater `TOOLSET-378-07c50be2`; supervision `TOOLSET-369-b5db2d3a`; closure preparation `TOOLSET-370-02928e38`. All seven IDs are retained from the earlier saved candidate; none is present in the current consumer. Restore them through the task CLI, without reopening completed work. Preserve their relative ranks and all unrelated ranks and goal fields; update only this goal's source to the accepted SDD heading. The four instruction tasks lead selection. Native plugin relocation additionally consumes the corrected injected-request contract from TOOLSET-375-da53c314, so it depends on that real producer as well as the foundation.

The common foundation precedes runner and three native relocation cuts; the two feature extractions depend on runner relocation and can then run independently. Native plugin/setup/updater have disjoint production writes; shared check/read inputs alone do not make product dependencies. Shared engine integration tests can constrain scheduling but do not justify fake product edges. The atomic runner cut's size is justified above; no giant all-host move, test relocation or rolling-planning successor is needed for these known outcomes.

All future tests and package checks are **planned/unrun and task-owned to create**, not missing external inputs. Every slice adds its fixture characterization before the move, preserves public/failure assertions, runs its named checks and `python3 scripts/affected_tests.py --run` against the actual implementation base (`--base` when needed), and keeps required review. Mapping/inventory changes require conservative verification, not dropping affected suites. Main's independent post-landing full check remains separate; no model/service experiment is authorized.

Import/ownership guards include function-local and relative imports, empty initializers, old-to-owner closure and deliberate forbidden-import/missing-payload/duplicate-stem negative cases. Do not count moved lines/files as a maintainability result; success is real core implementation ownership under Src, preserved legacy compatibility, cohesive feature boundaries, correct source selection and unchanged behavior backed by offline oracles.

Attempts, task schema/IDs/order, state/receipts/locks, leases/budgets/resources, user decisions, pauses/live exclusions and lifecycle authority are invariant. The snapshot/async-reader/history/Blockers changes are now landed: preserve them at execution, never restore old source over a fix or add a missing-ID dependency on an unintegrated candidate. Preserve worker verdict fingerprint semantics while changing where canonical source bytes live.

Builder review found two missing test owners, now resolved in the saved contracts: foundation owns the install-plugins native-copy fixture and its check; runner owns the task-prepare actual-source AST guard and its check. No other consequential interface choice or unreachable external input was reported. Setup's engine integration fixture overlaps the runner scope for scheduling, not as a new product dependency. No product tests or models were executed by that review.

Source evidence: pinned source/AST/path/entrypoint inventory and two independent read-only architecture reviews; no graph artifact existed and no graph rebuild/model extraction is claimed. Planning validation covers exact accepted anchors, final store/docs/link checks, candidate closure, privacy/whitespace, preserved unrelated records/order and repeat stability. Local plan commit, canonical integration, consumer receipt, execution and live acceptance remain distinct.
