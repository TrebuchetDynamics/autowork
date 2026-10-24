# Fleet TUI responsiveness and task freshness

## Scope and diagnosis

Status: Accepted

Owner request: improve slow input through SSH and unreliable task-count updates, including the last saved task not being picked up. This standalone planning pass saves an implementation batch; it does not implement it, run UI/model/SSH experiments, change services or schedules, or operate the other host shown earlier.

Three distinct observations must not be conflated:

1. Source at `911d1b2855c94eaedfa07102434d95d139f0ab13` performs blocking service/Git/filesystem/journal/model reads on Textual callbacks. That is an input-blocking mechanism, not an executed reproduction of SSH transport lag.
2. Fleet counts mix health/slot observations with separately refreshed Needs-decision totals; they are not a census of one current committed TaskStore. Tasks and health can refer to different worktrees/revisions, and several read errors look empty.
3. `TOOLSET-377-199b6bb6` was genuinely absent from canonical HEAD: commit `614bdf8e` existed only on its planning branch. The runner had no open tasks. After fresh clean-checkout/no-interactive-writer/no-in-flight checks, that exact two-file planning commit was fast-forwarded into canonical main. Consumer show/why succeeded and a subsequent native prepare reported the task in_flight on the existing runner. No start/restart or explicit dispatch occurred. This repairs planning delivery, not UI latency or product completion.

Reuse the existing RELIABILITY-2026-10 goal, priorities/focus and prior task IDs. Keep the active hotkey task's admitted contract unchanged. Existing task-count classification/drilldown work is not recreated, and an unintegrated Src migration is not a prerequisite. At execution retain any newly landed hotkey/other fixes and adapt to actual source owners rather than restore this baseline.

## Source evidence and boundaries

- `FleetApp.on_mount/action_refresh/on_resize` synchronously calls fleet_view.collect on a three-second refresh and resize. Collection includes per-repository `task_prepare.prepare(mode='check')`: it is read-only but scans source/history. The per-service is-enabled call lacks a timeout; discovery/journal/model listing have existing finite bounds.
- Full-screen/fleet logs, task rows/detail/goals, directory readiness/render-label cache misses and default model discovery also perform synchronous reads. Model listing can wait up to its sixty-second timeout. Existing off-thread mutation execution still recollects synchronously on completion.
- `task_counts` combines lanes, held/stopped/waiting health and separately prepared Decision counts. `task_rows` separately rereads HEAD/status/pending paths; stale slots are joined by ID, and stopped waits differ between list/fleet classification.
- Health loses explicit source/age at the fleet adapter. Coordinator directory-only status caching and health write-time stamping can make reused observations appear newer. Engine status identifies workspace but not the store revision/contract identity needed for safe joins.
- TaskStore itself sanitizes inherited GIT_* and replacement refs, but task_queue.commit's SHA discovery does not. Missing/invalid/unreadable stores and pending-read errors must not become verified empty/clean inventory.
- Existing headless pilot checks slow mutation actions, not slow readers. Existing health tests retain failed-read timestamps; retain those assertions and extend actual producer-to-view coverage. No product test, benchmark or remote SSH reproduction ran during this planning pass.

## Chosen contracts

Planner calls: three cohesive slices: producer provenance → one committed task snapshot → nonblocking UI consumption. No schema migration, second queue, new permission gate, lower verification bar or unbounded polling/thread creation. Source-reading and fixture regressions are future task-owned inputs, not absent external prerequisites.

### Producer provenance

Status: Accepted

Add diagnostic observation metadata to engine status and health only; task/attempt/receipt schemas and authority are unchanged. At engine status entry capture one immutable TaskStore/revision and use it for all task membership/current-record reads in that answer, not a final HEAD lookup after rendering. Expose `task_source = {workspace, repository_identity, revision, observed_at}`; each task row carries its current source contract_hash and, where a live attempt exists, its admitted_contract_hash separately. Never substitute today's hash for the attempt's hash. Missing legacy metadata stays unknown, not inferred fresh.

Use the existing sanitized TaskStore Git path for revision discovery in task_queue.commit, preserving unborn/unknown revision handling while distinguishing real read failure. No process-global environment mutation. A hostile inherited GIT_DIR/WORK_TREE/INDEX_FILE or replace ref must not redirect the selected repository.

Coordinator status cache is keyed by resolved workspace and source revision as well as its existing lifetime; engine mutation invalidation remains. Cached data retains its original observed_at. Health carries that observation through successful/cached writes and retains its age on failed reads; write time is separate. Preserve existing failed-read escalation and status/lock lifecycle. No live process restart is required or implied by source qualification.

Produces: the additive task_source/row identity envelope and truthful observation time for the next slice. Planned checks: `python3 scripts/check.py pi-autowork/engine/test_parallel_status.py pi-autowork/engine/test_task_queue.py pi-autowork/tests/test_health.py pi-autowork/tests/test_status_provenance.py`. New test_status_provenance.py owns coordinator cache/revision and health propagation cases; existing runtime assertions remain.

### One committed task snapshot

Status: Accepted

Add `pi_autowork/task_snapshot.py` with `capture(repo, *, engine_observation, generation) -> TaskSnapshot`. Its immutable result includes selected repository identity/worktree, one resolved committed revision/TaskStore, generation and capture times, rows, counts, goals/questions, independently captured pending paths, engine source identity and explicit freshness/errors. Pending/working detail and runtime observations keep their own timestamps/provenance; a generation is not a claim that every source was observed at one physical instant.

Inventory membership is **exactly current committed open task IDs**, with each present once. Join execution evidence only for the same repository identity and compatible contract hash; different session/canonical revisions are disclosed, and hash-compatible observations may still describe the same task. Incompatible/legacy-unknown/orphan slot data remains visible as separate execution annotations, never extra inventory. Decisions come from current Needs-decision records; stopped dependency waits remain Blocker, overlap/transient waits remain Waiting, Mergeable still requires compatible evidence, and ordinary ready work is Waiting with explicit “ready; awaiting dispatch”, not omitted from Total. Preserve existing five-bucket sum and queue/goal order; questions without matching inventory are annotations.

Derive fleet counts, task rows, Waiting/Blocker detail parts and the visible task list from this same result. Reuse the revision-keyed TaskStore cache, not a whole live snapshot keyed only by HEAD. A newly committed task appears at the next completed capture even for stopped/no-health runners; closes/section changes remove/reclassify it. Staged/unstaged/untracked records remain pending, not committed membership. Do not scan or union arbitrary planning branches into counts.

Valid empty is six zeros. Unavailable/invalid/missing data is not empty: `task_counts` returns no valid vector when no verified snapshot/last-good exists, and consumers render unknown/unavailable; if last-good exists, show it with its original revision/age and stale/error state. Read failures never mean clean pending paths. Extend current synthetic count fixtures with explicit inventory inputs rather than deleting bucket/mergeability assertions. Preserve service lifecycle labels independently of task-data freshness.

`fleet_view.collect` attaches/uses these snapshots. Define `collect_for_tui(..., generation, cached_preparation=None) -> FleetSnapshot` carrying runners, per-repository TaskSnapshots, capture time and explicit acquisition errors; existing CLI collection keeps its contract. Service/env/store/pending errors must survive the adapter instead of being swallowed as empty values. The TUI read path separates current cheap state/inventory capture from expensive preparation audit. Bound the formerly unbounded service-enabled query with the existing ten-second discovery bound in this reader-owning slice. CLI/full readiness retains existing semantics. TUI preparation diagnostics may reuse a labelled result for at most 30 seconds (planner default), invalidated by relevant observed repo/environment changes, action/preparation return or explicit refresh; mark diagnostics age separately. They never supply inventory counts or authorize Start. Confirmed Start always forces a fresh readiness read. No cache of pending/status/environment/readiness solely by HEAD.

This slice owns synchronous TUI rendering adapters for the new snapshot/unknown/freshness fields; the next slice moves their readers off-loop. Legacy health metadata remains displayable as unknown/stale with canonical inventory available. Planned checks: `python3 scripts/check.py pi-autowork/tests/test_task_snapshot.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_health.py`; existing rendered pilot and selected affected tests must run, with skips disclosed.

### Nonblocking read coordination

Status: Accepted

Add `pi_autowork/tui_reads.py` with a read-only coordinator: `request(kind, identity, epoch, loader) -> token`, subscribing only active app/screen resources. Token contains owner lifetime, kind/resource identity, request generation and invalidation epoch. Workers receive plain immutable inputs; the UI thread alone publishes results/queries widgets. Use a bounded executor (four concurrent reads, planner default), at most one physically active read plus one replaceable pending request per resource, and retire queued subscriptions when the owner/selection changes. No recurring thread per timer.

Fleet/discovery/task snapshots, journal/log/action detail, goals, readiness/directory labels, model catalog and code-stamp reads use this boundary. Separate log/catalog/readiness keys so one blocked reader does not serialize the entire UI. Resize/filter/wrap/selection renders cached snapshots immediately and schedules only missing reads; it must not recollect the fleet synchronously. File discovery stays on DirectoryTree's existing loader where applicable; no I/O from render_label. Consume the preceding slice's bounded service readers and preserve other established timeout/error semantics.

Publish each repo snapshot atomically for the current owner/identity/epoch, applying only completion sequences newer than the last applied result. Repeated timer polls of the same identity/epoch coalesce without invalidating the active read merely because another request is pending: otherwise a collector slower than the timer would never publish. Semantic invalidation/selection changes reject the old result; a newer already-published completion cannot be overwritten. Resolve runner/repository/task by identity, never a stale table index. Keep current selection, filter, scroll/follow state; a failed read releases busy state and retains visibly stale last-good data. An empty successful discovery differs from a failed discovery. Model results stay service/provider-context-specific; preserve default fresh discovery per opening and Portal invalidation, not a fleet-global catalog.

Unmount cancels queued work/subscriptions. Cancelling an async wrapper does not stop a running thread: keep its resource slot occupied until physical completion, discard its late result, and do not admit an overlapping replacement. Invalidate epochs after action/preparation/planning return and interactive resume; completion callbacks request new reads instead of doing synchronous recollection. Preserve fresh pre-Start readiness in a worker, duplicate-start prevention, confirmation/view-only/authorization and existing interactive suspension. Mutation commands are not cancellable disposable reads. Do not restore removed fleet shortcuts.

Proposed `test_tui_reads.py` and existing tui_pilot use threading.Event entered/released/completed handshakes: while each provider is blocked, acknowledge navigation/filter/key/close before release; prove coalescing, no overlapping cancelled-thread replacement, stale-generation rejection, close/reopen and action invalidation, error recovery and selection stability. Use a watchdog only to terminate deadlocks, not invented millisecond SSH performance claims. Planned checks: `python3 scripts/check.py pi-autowork/tests/test_tui_reads.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_tui_mouse.py`.

## Batch and completion

Independent builder review: “nothing important left.” The reader confirmed the source/identity/error contracts, non-starving read coordination, test ownership and real producer-to-consumer dependencies. This was read-only review, not executed product tests or SSH qualification.

Saved tasks: `TOOLSET-378-faaf7ed8` (producer provenance) →
`TOOLSET-379-cf40090d` (committed task snapshots) →
`TOOLSET-380-f265bb27` (nonblocking UI reads). The earlier hotkey task
`TOOLSET-377-199b6bb6` is retained unchanged and has a separate consumer receipt.

Each slice consumes the preceding concrete API, with producer/consumer notes on the task records. These are real data/interface dependencies, not sequencing invented for shared paths. Each owns code, its focused tests and compatibility; no separate giant qualification task or rolling successor is needed for known scope. Existing active hotkey work can proceed; respect current source/ownership at implementation and retain its eventual outcome.

Every slice runs its focused checks plus `python3 scripts/affected_tests.py --run` on the actual implementation base (`--base` when needed). Keep required review and main's full gate. Task-provided tests are planned/unrun; this plan does not install dependencies or produce test/model results. The Textual pilot must actually run for rendered coverage; a skipped dependency is NOT_CHECKED, never a visual pass.

Completion means responsive local event handling under deterministically stalled readers and accurate revision-bound counts/error states, not universal low SSH latency. Actual SSH terminal/transport qualification remains unrun; if later observations still lag after local blocking is removed, investigate that specific host/network separately. Keep canonical delivery, selection, admission, execution and acceptance distinct. Saving planning branch records does not make them visible to a runner; verify canonical inclusion and a real consumer receipt, preserving active contracts and all existing jobs/pauses/publication limits.

## Immediate task deletion feedback

Status: Accepted

Owner request: “deleting task must refresh tui inmediately”, through standalone Plan For Me. Save this bounded correction under RELIABILITY-2026-10; do not implement it, delete a real task, dispatch workers, install anything or change schedules in this occurrence.

### Diagnosis and chosen approach

Source baseline: `6ee8f67a528b1b370a355aa0d9df39754351e8c3`. In `tui.py`, `finish_action` posts `action_completed` without action/result context; `action_completed` schedules `action_refresh` and immediately redraws the still-current task snapshot. `publish_fleet` eventually redraws the current screen, but `task_commands.cmd_delete` only removes the working-tree record. `task_snapshot.capture` intentionally reads committed HEAD and records pending paths independently. A successful delete can therefore remain in inventory even after recollection, until another actor commits it. These are source observations, not an executed UI reproduction.

**Planner's calls:** handle TUI-initiated deletions as explicit, app-owned pending display mutations. “Immediately” means the next UI-loop update after the successful command result is posted, without a timer tick, completed fleet read or runner commit. Preserve the immutable committed snapshot and admission/eligibility authority. Show the display adjustment as “deletion pending commit”, not as a new committed revision. This is not a working-tree replacement for TaskStore.

- Carry explicit delete identity/result through the action completion path: captured runner, resolved workspace/repository identity and task ID, never the currently selected row, a mutable runner name lookup or parsed notification text. Invoke the existing delete CLI against the captured repository path, not a runner-name binding that could be retargeted between confirmation and execution. A zero return code with warnings is still success under the existing CLI contract. Failure, exception, denied access and cancellation of confirmation do not remove anything.
- Apply an idempotent success-only display overlay before starting expensive refresh. Derive visible task rows, per-view counts and fleet inventory counters from the same effective projection; remove a deleted closed-history record without decrementing open totals. Keep filters/scroll and choose the nearest surviving row, or an explicit empty state. Refresh the selected detail and menus; a deleted detail must become unavailable or return safely rather than retain actionable stale data. Repaint cached parent/task screens on resume, not unmounted widgets.
- Keep the overlay scoped to the captured repository/workspace and record identity so another runner/repository with the same task ID is untouched. Old reads and stale/last-good snapshots cannot resurrect the deleted record. Request a fresh off-loop observation through existing epochs/physical-slot scheduling; do not cancel a thread and pretend its slot is free. Slow or failed recollection must not undo acknowledged feedback or freeze input.
- Reconcile using off-loop working-tree/pending observation as well as committed membership. A fresh successful observation that the record is absent in committed inventory retires the overlay; a fresh observation that the record has been recreated/restored also retires it and restores any row that belongs to the current committed snapshot. A recreated record absent from HEAD is disclosed as a pending record, not inserted into committed inventory. HEAD absence alone must not conceal that pending recreation indefinitely. Unknown/read-error state retains the pending overlay with visible provenance rather than claiming a clean or committed deletion. Reject pre-action observations for reconciliation. Repeated success notifications are idempotent.
- Independent worker/slot/question observations remain diagnostics, not resurrected inventory; deleting a record does not erase actual worker activity or owner questions. Genuine independent questions can remain in Questions with that provenance. Dependent records remain present and blocked/warned under the existing semantics; the display overlay must not grant admission, satisfy dependencies or close anything.

Rejected alternatives: another timer/manual refresh does not address uncommitted deletion; silently filtering every pending path confuses edits/additions with deletions; committing from the TUI changes ownership/transaction authority; removing rows before command success falsely acknowledges failure. No filesystem watcher or new background service is needed. Planner's default scope is completion feedback for deletion initiated in this TUI; external CLI edits retain normal observation cadence.

### Single implementation slice and verification

Task `TOOLSET-383-7a5b0363` owns this complete vertical correction. Use current `pi-autowork/pi_autowork/{tui,fleet_view}.py` and existing fleet/read/pilot test seams; if the accepted Src relocation lands first, use their real `Src/pi_autowork/` owners instead of adding behavior to compatibility shims. It is not dependent on the unrelated source migration. Shared production writes with that migration require reconciliation/serialized integration, not fake product prerequisites or changing active contracts.

Planned checks: `python3 scripts/check.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_tui_reads.py pi-autowork/tests/test_task_history.py tests/test_task_commands.py`; the existing fleet test wrapper must actually execute its pinned Textual pilot, not count a skipped dependency as rendered coverage. Also run `python3 scripts/affected_tests.py --run` against the actual implementation base (`--base` when required). Proposed regressions are task-owned to add to existing seams, not written or run during this planning occurrence.

Acceptance/oracles: extend `tui_pilot.py` with a deterministic post-delete case with timer refresh disabled and a blocked fleet reader. After releasing command success, assert row/detail/menu removal and matching displayed counts before releasing the reader, including last-row/closed-history deletion. Then release a pre-delete snapshot and assert no resurrection. Use the real native CLI in a private Git fixture to demonstrate successful working-tree deletion while HEAD still contains the record, plus warning-success, failed/cancelled deletion, duplicate completion, another repository with the same ID, close/reopen or selection change, and later commit or restore/recreation. Existing fleet/snapshot/reader/history/command guards remain intact; tests must not delete a real repository task or invoke live services/models.

Pre-mortem guards: (1) a stale reader restores a deleted row — barrier-controlled old-result and unchanged-HEAD tests; (2) optimistic feedback hides a failed delete or another repository's row — failure/cancel/warning and captured-identity cases; (3) counters/detail disagree or a restored task stays hidden — shared projection, last-row/history and fresh restore/recreation tests. Keep no-write/view-only guards, confirmation, worker warnings, task-store format, receipts, locks and live authority unchanged. No arbitrary millisecond latency or SSH-delivery claim.
