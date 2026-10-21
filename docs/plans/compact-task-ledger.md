# Compact task ledger

Status: Superseded by [Task Store v2](../project.md#task-store-v2-2026-10-20) (2026-10-20)

The owner requests a plan for smaller `TODO.md`, `TODO.archive.md` and `goals.json`,
with detailed per-task files as a candidate, and authorizes auditing this repository.
TODO remains the central human work queue; planning saves findings/tasks but does not
implement or migrate the storage format. The original clarification asked
for planning/Docs Sync support before conversion. The owner has since prioritized
this chain, delegated implementation details and authorized this repository as the
first guarded adoption target after its support/review gates. No manual rewrite
or premature migration is authorized. Choices below are the
planner's calls.

## Measured problem

A point-in-time dirty-checkout audit found 42 live task bodies in a 143,022-byte,
725-line TODO; task bodies occupy 123,802 bytes and generated coverage 16,904 bytes.
The longest task is 10,110 bytes; the longest line has 4,053 characters. This is
mostly required contracts and repeated coverage, not an archive-cleanup failure.
The archive is 283,831 bytes/2,373 lines. The 62,199-byte goals index has 142 task
records: 41 open, one in progress, 97 done and three superseded, across 21 goals.
Compact-serialized terminal records occupy 17,333 bytes; per-goal evidence 14,845
bytes and repeated goal task membership 2,227 bytes. Whitespace-only minification
would still leave a 47,016-byte goals file. All are source-size measurements, not
LLM token counts, latency measurements or evidence that execution gets faster.

A synthetic projection retaining the ordered 42 live rows is 4,975 bytes of TODO;
active tasks plus short goal summaries are 16,624 bytes of pretty JSON before new
reference/digest overhead. These are design estimates (96.5%/73.3% smaller than
the measured roots), not migrated artifacts or promised final sizes. Full private
input hashes and the projection method are in the planning audit receipt.

## Chosen layout and authority

Default task storage is `docs/tasks/`, beside `docs/plans/`; root TODO/index/history
entrypoints remain unchanged. This keeps task documentation out of application task
code namespaces. These records remain coordinator-owned metadata despite living
under docs/: broad documentation write scope does not authorize contract changes.

- `TODO.md`: short navigation and one linked row per live task in the existing
  Now/Next/Needs decision order. Keep ID, outcome/title and an optional short gate;
  no full acceptance/check logs and no coverage table enumerating every task again.
  A short goal-count summary replaces that table. Explicit human ordering remains
  authoritative; alphabetical folder order never chooses work.
- `docs/tasks/<ID>.md`: one stable detail path for the lifetime of a task, including after
  closure. It owns the full executable contract and structured versioned metadata:
  ID, title, goal, status, dependencies and retained extra ledger fields. Preserve
  Sources, Touches/Resources, scope, acceptance, checks, exclusions, ownership,
  budgets and live gates. Use a strict JSON metadata envelope, not executable YAML.
  Task field conflicts are diagnosed, not silently resolved by last-key-wins.
- `docs/tasks/goals/<GOAL>.json`: full goal definition, membership and evidence, retaining
  existing meaning and executed-versus-inspected distinctions. Hot goal summaries
  refer to these records instead of embedding long receipts. Membership is checked
  against task records, never inferred from absent active rows.
- `goals.json` version 2: synchronized machine index of live tasks and short goal
  summaries, ordered IDs, schema/source references and content digests. It is not a
  competing editable product backlog. Derive it through Docs Sync from TODO order,
  task records and goal records; refuse drift rather than overwrite human edits.
- `TODO.archive.md`: small history catalogue, not all historical prose. Closed task
  details stay at their stable paths; append-only year/month catalogues under
  `docs/tasks/history/` link those records. Root links the year catalogues, not every
  completed task. Never prune evidence to meet a size budget.

Only linked live TODO rows enter the execution queue. Orphan files are reported by
validation and never silently dispatched. Terminal task lookup uses the exact task
path, not a giant root tombstone list or an assumption that a missing active row
means done. Superseded remains distinct from done and cannot satisfy a dependency.
Goal met still requires all member tasks done plus executed passing evidence.
Metadata mirrors in rendered rows/index must agree; edits and reconciliation run
through one owner/CLI, with no independently writable state databases.

## History and compatibility

Current v1 rules require complete live bodies in TODO, retained completed records
in goals.json and an append-only root archive. A tasks directory alone is therefore
not compatible today. This plan prospectively replaces those location requirements
only after producer/consumer and migration support land; it does not weaken content,
review, dependency, ownership or evidence requirements.

Support v1 inline and v2 linked repositories explicitly through one shared reader
and version-aware writers. Legacy repositories stay byte-stable on read and do not
migrate automatically during render, startup or an update. TODO-only repositories
remain supported without creating goals.json; an explicit format marker selects
linked-task mode there. Unknown versions fail clearly, never look like an empty
queue. Before switching a repository, all its selected adapters/installed helpers
must support v2; old already-running workers retain their original contract/format.

The migration first saves the entire original archive and goals bytes as immutable,
checksummed legacy snapshots under `docs/tasks/history/legacy/`; the original archive
must survive byte-for-byte before its root becomes a catalogue. This is a one-time
explicit relocation, not permission to truncate history or rewrite old receipts.
Archive narratives outside task blocks and duplicate historical versions survive.
Terminal legacy task metadata can refer to exact checksummed byte spans in that
snapshot rather than duplicate all old prose. Ambiguous/missing historical bodies
retain their source records and a provenance-gap flag, never invented acceptance.
Future closed task files retain their full bodies at their original task paths.

## Reader, freshness and transaction contract

Introduce a common resolver for queue rows, full contracts, active/terminal state,
goals and historical evidence. Route Docs Sync validation/render/reorder/closeout,
Autowork selection/admission/Touches checks, worker packet construction, integration,
recovery, Pi UI/readiness, task queries and portable adapters through it. Package
that helper wherever standalone copied launchers currently need local dependencies.
Workers receive just their selected contract and necessary dependency/evidence
closure; ordinary queue display does not expand every task, goal or archive.
Full validation can inspect all records; dependency resolution loads referenced
terminal records and goal proof, not an unconditional full-history scan.

Revision/receipt fingerprints must cover consumed task and goal records as well as
the index/queue, so changing only `docs/tasks/ID.md` invalidates affected evidence. Keep
queue revision distinct from assigned-contract/lease identity: unrelated history
appends must not cancel a running worker, while real contract changes, ownership
loss, unsafe Touches, stale sources and unknown dependencies still hold/cancel it.
Validate canonical relative paths/ID agreement, duplicate links, symlinks, path
traversal, untrusted arbitrary references and missing/truncated files before use.

Keep the existing canonical cooperative Git-common lock, clean Git identity and
expected-revision guards. A multi-file mutation stages and verifies all outputs,
records a durable recovery journal, installs detail/history records before publishing
index/queue references, and clears the journal only after coherent read-back. Readers
and writers refuse a pending/inconsistent transaction and report supported recovery;
no mixed snapshot is admissible. Resume an interrupted migration idempotently.
Rollback restores only verified migration-owned outputs under fresh guards, never
another writer's newer edit. Refuse cutover while incompatible active leases/workers
hold the old contracts; do not pause, kill, repin or restart them automatically.

## Delivery slices and checks

1. **Linked task storage and skill adoption:** preserve v1 full ledger/history while
   adding an explicit linked-body storage version, shared reader/guarded writer,
   consumer and packaging adaptations. Update `skills/shared/TODO-WORKCENTER.md`,
   planning skills, Docs Sync/archive contracts and portable instructions together:
   new tasks get one detailed record plus a short queue row in opted-in repositories;
   legacy repositories retain inline bodies. Teach agents to load only a selected
   contract, not expand the whole task directory. Exercise planner save through
   selection, worker packet, verification, canonical closeout and history query.
2. **Active-only index and history catalogue:** depend on linked-storage support.
   Add goals.json v2, per-goal evidence and terminal-record resolution, retained-ID
   allocation, compact coverage and catalogue rendering. Preserve dependency,
   supersession, focus and met-proof semantics. Test both a full-history index with
   linked bodies and the compact index, so these changes can ship independently.
3. **Opt-in conversion tools and offline qualification:** depend on both support
   slices. Implement separately selectable linked-body and compact-history migrations,
   write-free previews, resume and guarded rollback. Use disposable exact copies of
   this repository's audited inputs and a large synthetic history, with interrupted
   commits, stale revisions, concurrent edits and incompatible consumers. Verify
   skill adoption and packaged host behavior. After support, independent review and conservation/recovery checks, perform the
   owner-authorized guarded cutover in this repository. No other profile/fleet
   repository is a conversion target.

Use independent format versions for body storage and machine-index history; changing
body location does not itself prune ledger history. Old TODO anchors need stable
compatibility links during an actual conversion. Protect resolved task/goal/history
metadata as coordinator-owned in scope checks, integration and commits: a worker
cannot widen its own Touches or rewrite acceptance by editing its new task file.
Keep a pure legacy text parser; a repository-aware resolver returns the real owner
path and exact closure, never a fabricated concatenated TODO for writers. Include
record paths in claim age/hold attribution, Pi wakeup detection, planning adoption,
closeout staging and rollback inventories. Planning auto-commit accepts only
schema-validated record identities, not arbitrary `docs/tasks/**` code. Coexisting
application files are not ledger metadata; colliding destination files hold the
migration rather than get overwritten.

Preserve existing whole-queue stale-write/selection guards during the first support
slice. Separating queue revision from running-task invalidation is permitted only
with the composed ownership/contract-change negative tests; it is not permission
to repin a live attempt or relax unchanged guards in this planning pass.

Required tests are behavioral: v1 byte stability; v1/v2 selector/dependency/goal parity;
unchanged statuses, order, gates and full acceptance; task-only tamper invalidation;
closure-bound receipts; unrelated-history non-cancellation versus true ownership-loss
cancellation; traversal/symlink rejection; missing/duplicate details; pending-journal
reader refusal; interrupted migration resume/rollback; history/query compatibility;
portable copied-package operation. Focus new cases in a compact-ledger regression
module and reuse existing concurrency/archive/worker suites. No model, provider,
service or scheduled-job execution is required. Independent review remains mandatory.

Planner's initial size budget on the measured 42-live-task fixture: TODO <=12 KiB,
goals <=28 KiB, root archive catalogue <=4 KiB, with all historic data conserved.
These are acceptance targets to exercise after implementation, not current results
or global hard limits: legitimate growth in live docs/tasks/goals may exceed them with
an explained proportional budget. Closed-history growth must not grow the root
queue or active task index. Test a large synthetic history for that invariant,
not a wall-clock speedup claim or thousands of redundant tests.

## Alternatives and boundaries

Rejected: JSON minification alone (does not remove hot history); stronger prose
trimming (risks dropping contracts); simply deleting done ledger rows (breaks proof
and dependencies); hiding a second complete monolithic ledger behind a tiny root
(does not give task-local loading); SQLite or a hosted board (unnecessary database,
merge and authority replacement). The per-task format adds file/transaction overhead;
the explicit resolver and recovery protocol are the cost of smaller hot documents.

Saving or reprioritizing this plan does not itself execute migration. The latest
owner instruction separately authorizes local implementation, verification and
scoped local commits for this chain, followed by its guarded local cutover. No
publication, installation, schedule change or new worker dispatch is authorized
by saving the plan. Existing task IDs/order and historical completion evidence remain.
The read-only task-query work retains its IDs; the storage implementation must adapt
that consumer if it has landed, not create a competing query feature.

## Source-backed impact

Direct inspection located inline coupling in `skills/docs-sync/scripts/{goals,todo_archive,recover_backlog}.py`, `skills/autowork/scripts/{task_execution,ready_preflight,start_goal,parallel_claims,parallel_integrate,parallel_dispatch,parallel_status}.py`, `pi-autowork/pi_autowork/{coordinator,touches_inference,fleet_view,questions,worker}.py` and `adapters/skills/`. Reader-only changes omit closeout writes, scope protection and Pi planning adoption. Retain the pure legacy parser and introduce a repository-aware shared reader/writer; separate body relocation from terminal-index pruning. Source review only; no runtime tests or migration were executed during planning.

## Immediate local adoption mandate

Status: Accepted

The owner delegated the priority choice and implementation details after requesting
compact TODO.md and goals.json now. Planner call: 149-df, 150-71 and 151-01 lead
the queue in that dependency order, ahead of the older pipeline-first ordering;
all unrelated task order and paused/external gates remain intact. The existing
archive is not the urgent problem: keep its content and receipts; do not spend
time shrinking old history or erase it to meet an active-file target. The visible
queue must contain only concise pending rows, and completed records must leave
the hot index while remaining resolvable. Preserve the chosen docs/tasks/ layout.

First deliver the shared reader/guarded writer and consumer/package compatibility,
then active-only indexing, then run the supported local migration with conservation,
recovery and exact-tree checks. No unreviewed manual file move is a substitute.
The live coordinator and its current worker have matching process-birth identities;
the current worker keeps running. Exclusive implementation/cutover waits for its
normal safe handoff, never a competing owner, new worktree to bypass the lease,
worker kill, restart or repin. Existing local implementation authority does not
extend to publishing, deployment, credentials, fleet migration or scheduling.
