# Pi Autowork coordinator redesign

Status: accepted, 2026-10-16; owner decisions recorded at the end.

## Why

On 2026-10-15/16 four `pi-autowork@` runners sat idle for seven hours with
"active (running)" services. Each stall was fixed as a special case in Bash or the
engine (backfill, readopt, close retries, exhausted holds, prose dependencies). The
failures share causes that patches do not remove:

- **Lifecycle authority is split.** The engine owns slot states, but the runner
  keeps its own lifecycle (`SEEN`, `FAILURES`, `DRAINING`, close retries, Touches
  edits, session merges) in about 1,000 lines of Bash. Neither side can state which
  transitions are possible from a stuck state.
- **Worker outcomes are guessed from process state.** A worker that stopped on
  purpose and wrote `report.json` with blockers (runner A a fleet task) was classified "dead
  worker with uncommitted changes" and resumed, burning its last attempt. A worker
  whose report listed pending device checks (a fleet task) was held as a
  failure twice although its offline slice passed.
- **No state means "waiting for a person".** Holds, contract changes and
  unbounded scope all became generic blocks, and nothing surfaced them.
- **Destructive Git recovery runs on shared checkouts.** The reviewer and Touches
  passes may `reset --hard`/`clean` the session checkout; closure stages
  `git add -u -- '*.md'`.
- **Silence.** A stalled runner logs one line and polls forever.

## Invariants

1. **One lifecycle authority.** Every task state transition is made by the engine
   (`owner_cycle.py`) and journaled. The runner never infers or stores task state;
   it reads `--parallel-status --json` and calls engine operations.
2. **Every state has an exit.** Each non-terminal state names the event that leaves
   it: a worker, the coordinator, time, or a person. A state whose exit is "a
   person" is `deferred` and blocks only its dependents and declared overlap.
3. **Worker outcomes come from the report, not the process.** Exit with a valid
   report decides the transition; process death without a report is the only
   "crash". A runner stop or restart never consumes an attempt.
4. **Offline completion is separate from live qualification.** A report has
   `blockers` (work not done) and `pending_live` (device, production or human
   checks for a separate task). Only blockers hold a task.
5. **Nothing unauthorized reaches main.** Scope, coordinator-file ownership and
   validation are checked on the exact merge candidate; deferral keeps the commit
   and receipt and never counts as completion.
6. **Exactly-once closure.** Integration, TODO closure, archive and the closure
   commit form one recoverable transaction keyed by the integration commit; a crash
   at any point resumes or completes it, never repeats it.
7. **Git operations are scoped.** Destructive cleanup (`reset --hard`, `clean`,
   `worktree remove`) runs only on a worktree the journal shows Autowork created,
   that is not the session or canonical checkout, with no live writer. No `stash`.
   Commits stage an explicit file list.
8. **Progress whenever independent work exists.** If no worker runs while runnable
   work exists, that is a bug surfaced as `STALLED` with the root blockers, not a
   quiet poll.
9. **Ambiguity blocks.** A dependency that names no known task is an outside
   condition and blocks; it is never read as "none".

## Task states (engine)

| State | Meaning | Leaves by |
| --- | --- | --- |
| `queued` | runnable contract, no slot | dispatch |
| `running` | live worker | worker report or crash |
| `reported` | commit + report, awaiting integration | integration |
| `verifying` | candidate merged in isolation, checks running | pass → `integrated`, fail → `retry`/`deferred` |
| `integrated` | landed on the session branch | closure transaction |
| `closed` | TODO closed, archived, committed | terminal |
| `retry` | failed, an attempt left | fresh attempt when its scope is free |
| `deferred` | needs a person or an outside condition; keeps commit, report, worktree | person, contract change, or `set-aside` |
| `blocked` | dependency or overlap with running/claimed work | the blocker clears |

`deferred` carries a machine-readable `cause`: `scope` (needs more paths),
`contract_changed`, `blocker` (report text), `validation`, `conflict`,
`attempts_exhausted`. Each cause has one automatic action where safe:

- `scope` with runner-inferred Touches: widen Touches with the paths the report
  names, record them, and resume the same worktree once. Authored Touches defer.
- `contract_changed` after integration: set aside (merge stays), re-queue.
- `conflict` with another task: revalidate against the new baseline after that
  task closes, once.
- others: wait for a person; shown in `--status` and the stall report.

## Components

```text
pi-autowork.sh            thin CLI/systemd entry: options, lock, service install, signals
  └── pi_autowork/ (Python, tested)
       coordinator.py     loop: reconcile → dispatch → integrate → close → report health
       pi_adapter.py      Pi invocation, model fallback, sessions, cost records
       worktrees.py       provisioning (linked ignored paths), scoped cleanup
       health.py          status.json, STALLED detection, needs-attention list
  └── skills/autowork/scripts (engine; single lifecycle authority, extended states)
```

The engine keeps its contracts; the redesign adds the `deferred` cause model,
report-based worker outcomes, `pending_live`, and the closure transaction. The
runner's Bash shrinks to the entry point.

## Required scenarios (controlled subprocess workers, failure injection)

1. Two tasks overlap: one integrates, the other defers and later integrates after
   revalidation.
2. Crash between integration and closure: restart closes exactly once.
3. Worker changes files outside scope: nothing reaches main; inferred scope widens
   once, authored scope defers.
4. Dependency names an outside condition: blocked, never runnable.
5. A person reorders TODO.md while workers run: running work is kept; new dispatch
   follows the reconciled order.
6. Reviewer writes unexpectedly: candidate rejected; unrelated changes kept.
7. Independent tasks finish out of order: no duplicate commits, no lost changes.
8. Worker stops with blockers in its report: deferred with that cause, no resume.
9. Report with only `pending_live`: integrates; a live follow-up stays open.
10. Runner restart mid-task: worker adopted or resumed without using an attempt.
11. Exhausted hold: blocks only dependents and overlap; the rest progresses.
12. No worker running while runnable work exists: `STALLED` is reported once with
    root causes.

## Owner decisions (2026-10-16)

1. **Self-update at a safe checkpoint only:** no live, reported or integrating
   slot, and the new release must read the current state schema version; otherwise
   keep running the current release and say why.
2. **Adopt verifiably idle claims:** an `in_progress` claim whose claiming session
   is gone and whose branch or worktree has had no writes for a set time may be
   taken over, keeping any existing work (AGENTS.md "adopt an idle candidate").
3. **Linked ignored dependencies:** the service environment file (toolset state,
   not the repository) may list gitignored paths to link read-only from the main
   checkout into each task worktree.
4. Local main's 56 unpushed commits were merged with origin and pushed (ee82575).

## Phases

1. Done (59a44cf). Worker outcomes from reports: a report with blockers defers with that cause
   instead of resuming; `pending_live` never holds; the worker prompt says which.
2. Done (50768e2). Git safety: reviewer and Touches passes in disposable worktrees; closure commits
   only the files closure changed.
3. Done. Health: `status.json`, one `STALLED` report with root blockers, `--status`
   and `--fleet`; the first module of the `pi-autowork/` component
   ([layout](pi-autowork-component-layout.md)).
4. Done. Owner decisions 1-3: safe-checkpoint self-update (fleet idle, state
   schema check before install), adoption of verifiably idle claims, linked ignored
   dependencies; plus guarded priority-drift recording and no service exit on engine
   errors.
5. Done offline. Typed hold causes with re-verification after widening inferred
   Touches; the whole runner (CLI, coordinator loop, worker modes, service, Pi job
   runtime, Touches inference) moved into the component, with `pi-autowork.sh` as a
   thin entry point. Deferred causes and their automatic actions; extract the coordinator into the
   `pi-autowork/` component per the [layout proposal](pi-autowork-component-layout.md)
   and reduce `pi-autowork.sh` to a compatibility entry point.

## Useful progress and independent workers

Status: Accepted

Owner direction (2026-10-16): run many independent tasks in each repository;
make the existing Needs column and selected-runner detail the first improvement.
One terminal should explain what agents are doing, what needs the owner, and what
has reached main. Keep the existing layout and dependencies. This is an accepted
implementation plan, not a claim that its behavior is already delivered.

### Evidence and limits

Source inspected at `1a955e5`, with existing test-thinning planning edits retained:

- `parallel_plan.py:plan` admits four disjoint task contracts together in a pure
  replay. Its existing 15 planner tests pass. Eight-worker dispatch and refill
  fixture cases already exist in `test_parallel_dispatch.py`; they were inspected,
  not executed in this planning pass. No live throughput has been measured.
- Pi's configured default is eight workers, with a 3000 MB memory gate per worker
  and a load gate (`cli.py`, `coordinator.py`, `parallel_dispatch.py`). Raising the
  default cannot fix a lack of compatible admitted work.
- A replay with one Go task running, a waiting `server/package.json` task and a
  third disjoint task dispatches nothing: `serial path` followed by `priority
  waits`. This is the explicit anti-starvation rule, not a hidden one-worker cap.
  The owner's supplied session shows this same barrier. Broad directory scopes,
  real dependencies, unknown scopes and shared resources also reduce concurrency.
- A literal route directory containing `[id]` fails `overlap` against an
  actual file inside that directory: fnmatch interprets the brackets as a class.
  This reproduces a false scope hold independently of any live repository changes.
- `Coordinator.infer_touches` checks its process-lifetime `touches_tried` set before
  the persisted expiry. A successful NONE answer can therefore remain solo beyond
  24 hours in a long-running process. The current TOOLSET-099-87 held report names
  this defect and requests the migrated coordinator path missing from its Touches.
- `parallel_integrate.retry` preserves old attempts but retires a held slot on a
  generic TODO contract change, then dispatches fresh work. The supplied session
  shows both a missing candidate on resume and reimplementation after a report
  formatting hold. Retention alone is not candidate adoption.
- `fleet_view.needs` displays question count and easiest task ID. `read_questions`
  retains ID, effort, count and Needs, discarding Answer, Since and question type.
  `health.update` stores `updated_at`, but that observation age does not reach the
  selected-runner display. A recent tool action can relabel a runner working;
  it is not evidence of integrated work.
- `tui.LogScreen.refresh_log` and the embedded log clear and rewrite each refresh.
  `collect` reads configured models, not proof of the effective model of each
  active attempt. Current state/log phases do not establish independent review
  or publication. `command.py` supports `autowork tui --view-only`.

Read-only local fleet observations corroborated one active worker per working
repository, with different roots: dependencies, malformed contracts, held work,
and broad scopes. These are changing snapshots, not a permanent fleet inventory.
The source named in the supplied logs is an older development checkout; qualify
the actual running version before claiming a fix reached a service. No services,
fleet queues, candidate branches or reports were changed during planning.

The quoted `a fleet source file` / `a fleet source file` limitation belongs to a fleet
feature's evidence contract. A read-only check found `uptime_seconds` from
`/proc/uptime`; it does not establish durable boot identity or service provenance.
Preserve that existing feature's prerequisite task and acceptance. Do not invent
boot evidence, reduce acceptance, or create a duplicate feature in Toolset to
increase the worker count. Private paths, reports and profile identities stay
outside public documentation; the fixtures below use generic task names.

### Decision and implementation order

1. **TOOLSET-129-c4 — one next action.** Add a deterministic presentation model in
   `fleet_view.py`, reused by the Needs cell and selected detail: audience (owner,
   agent, waiting, unknown), plain-language action, reason, source, evidence age,
   task reference and affected count. Parse existing Answer, Since and type when
   present; retain compatibility with old blocks. Prefer a verified owner action,
   then an agent repair or wait reason. Use a conservative "Inspect blocker
   evidence" when the source cannot establish responsibility. Do not infer an
   owner decision from every held slot or from the generated USER_DECISION label.
   Missing contract fields and report formatting are agent repair work; product
   choices remain owner decisions. A merge conflict is an agent repair unless
   evidence names an owner choice. IDs are secondary in detail, not the headline.
   Show "Nothing needed—verifying" only with current verification evidence and no
   unresolved owner action. With stale or missing evidence, say so instead.
   Separate "observed 2m ago" from "waiting since …"; file mtime or state duration
   alone does not prove when a blocker was checked. View-only shows evidence and
   action descriptions but cannot execute controls. Preserve intentional pauses.
2. **TOOLSET-099-87 — independent admission.** Resume the held scope-inference fix
   with its migrated implementation/test paths. Bound inferred scopes to the
   actual change; avoid whole-repository declarations. Repair literal-route path
   handling consistently in scope generation, intersection and final validation.
   Keep intentional globs conservative, including paths not created yet. Use the
   existing fnmatch literal escape (`[[]id]`) for emitted concrete bracketed
   segments; reconcile existing authored ambiguity explicitly rather than silently
   treating every bracket class as literal or widening it. Split an independently
   verifiable manifest/schema/CI change from implementation only where source and
   acceptance prove independence; preserve necessary dependency edges. Keep the
   global drain rule for genuinely exclusive work and bounded unknown scope. Fill
   every compatible available slot and refill when work completes. No fake task
   splitting, dependency removal, scope guessing or forced eight-worker target.
3. **TOOLSET-120-fc — resume the candidate and repair the cause.** A metadata answer
   must first reconcile the existing candidate, report and new contract. Pin its
   branch/commit or preserved patch, baseline and checks; verify no live writer.
   Correct report shape or scope within delegated authority and resume/reverify
   that candidate when compatible. Never fabricate a passing check or silently
   coerce ambiguous report values. If the artifact is missing, name the missing
   artifact and search preserved history before asking a person. Semantic scope
   changes still invalidate affected checks; integration verifies the resulting
   tree. Fresh work is appropriate only when no reusable candidate exists or the
   accepted new scope requires it, with an explicit disposition of preserved work.
   This supersedes the generic "any TODO edit means fresh implementation" rule
   for held candidates. Keep unchanged holds bounded and avoid repeat interviews.
4. **TOOLSET-130-15 — activity, delivery and capacity facts.** Extend existing
   status and selected detail, with backward-compatible missing-data handling.
   Show active/configured workers, compatible ready work and exact spare-slot
   limits (dependency, conflicting scope, exclusive drain, resource gate, hold,
   unavailable evidence). Derive counts and limits from the engine's admission
   result, not a second UI scheduler. Keep last tool activity, review waiting and
   unique main integrations today separate. Define “today” in the displayed local
   timezone; restarts/replayed events must not double-count integrations. Expose
   Implementing → Testing → Reviewed → Integrated → Published as evidence-backed
   milestones, including failed, skipped, pending and unverified checks. A report
   saying done proves none of the later stages. Distinguish session integration
   from canonical main, and local main from publication; publication is unknown
   without an attributable remote receipt. Show configured and effective attempt
   model separately, fallback policy, push policy and running version. Unknown
   versions/models/policies stay unknown; checkout HEAD is not process version.
5. **TOOLSET-131-ac — actionable blocker detail.** Select a blocker in the existing
   detail and inspect full reason, affected tasks, source/evidence age, available
   candidate/check evidence and appropriate next action. Read evidence lazily and
   bound its size. In normal mode use the existing action/agent entry points;
   explain restart, pause, model and other side effects before execution. In
   view-only allow inspection but no control action. Distinguish an owner answer
   from a repair the coordinator should perform, without an LLM call on refresh.
6. **TOOLSET-132-af — logs that retain context.** Add explicit follow/pause, search
   and copy with clear unsupported-clipboard feedback using existing facilities.
   Preserve selection and scroll anchor across refresh, resize and returning from
   raw logs. Keep task changes/errors in the compact feed; raw logs remain one
   Enter away. Bound retained data and handle journal rotation and restart replay
   without hiding distinct errors. No new panels or dependencies.

TOOLSET-115-bf is active in the observed runner: leave its assigned task body
unchanged. Reconcile its result before executing overlapping continuations above;
this plan does not start a competing worker. Retain TOOLSET-096-7e for installed
fleet qualification, with overlapping worker intervals and actual integrations
as evidence, not merely configured capacity or a screenshot of “working”.

### Alternatives and boundaries

- Raising the worker cap was rejected: eight is already configured and gates
  explain empty slots. Removing serial/resource/ownership checks was rejected:
  it would increase unsafe activity rather than independent progress.
- A new scheduler, task tracker or dashboard was rejected: existing admission,
  slot journals and views are the supported owners. Fix their missing evidence
  and broad contracts instead of duplicating lifecycle authority.
- Fresh retries for report-only failures were rejected when a valid candidate can
  be retained. Existing paused jobs, active writers, private credentials and
  per-profile job state remain protected.
- Themes, animations, new dependencies, automatic publication and direct fleet
  feature edits are excluded. UI labels must not imply a recovery action actually
  ran. Existing permission and publication policy is displayed, not changed.

### Verification and handoff

First-slice acceptance: a fresh owner decision, an agent-repairable malformed
contract/report, current verification, intentional pause and stale/missing records
each render one accurate action with reason and source age. Refresh preserves the
selected runner; 80-column detail remains usable; every control remains disabled
in view-only. Existing headless pilot plus pure fleet-view tests cover these cases;
no screenshot or visual verdict was obtained during this planning pass.

Parallel acceptance: controlled subprocess fixtures demonstrate simultaneous
worker lifetimes for at least three independent tasks, the existing eight-task
case, and refill after an out-of-order completion. Guard cases keep real
dependencies, overlapping/nonexistent paths, exclusive drain, low resources and
live claims blocked. A bracketed-route candidate validates only its authorized
scope; a metadata-only repair reuses the same candidate instead of reimplementing.

Metric: occupied slots versus currently compatible resource-admissible work, plus
unique validated integrations. Higher utilization is desirable only within those
guards; no performance percentage or always-eight-worker promise is accepted.
Use bounded fixtures, not an optimization loop or LLM activity count.

Executed now: 15 planner tests passed; pure replays admitted four independent
contracts and reproduced the serial drain and bracketed-route failure. These are
baseline observations, not regression fixes. Proposed per-task Verify commands
are in TODO.md; new assertions and live qualification remain unrun. The normal
offline gate remains a guard for combined runtime implementation, with the prior
600-second timeout retained as nonpassing evidence. Do not rerun it for this
documentation-only planning batch.

Planning handoff: TOOLSET-129-c4 is first in Now; continue the existing 099/120
contracts after overlapping active work settles. Follow-up UI tasks are Next and
depend on 129. Ledger readiness does not inspect live ownership or authorize
dispatch, restart, commit or push. Use the source-bound backlog consumer on this
section and the named task IDs; refresh execution evidence at admission time.

Handoff checks: goals validation, task-body readback and whitespace checks passed.
The six-task consumer returned `backlog_reconciled_not_eligible` (exit 2) only
because 130/131/132 depend on 129; the 129-only consumer returned
`ready_for_autowork` (exit 0), with synchronized priority and live ownership
unknown to that checker. The separately observed active 115 writer still requires
normal ownership admission. Receipts are local `/tmp/autowork-monitoring-backlog.json`
and `/tmp/autowork-monitoring-frontier.json`, not committed runtime evidence.

## Fleet monitor findings: delivery, environment and stall repair

Status: Accepted

Owner direction (2026-10-16): monitor the autowork fleet every 15 minutes, plan
bugs, optimizations and TUI improvements as toolset tasks, and never fix a
repository by hand: autowork must heal itself. Reordering Now/Next is delegated.
Each item below is the planner's call within that delegation.

Evidence from the 23:40 read-only pass (no service, queue or fleet file changed):

- **Delivery gap.** Four of five services set `PI_AUTOWORK_TOOLSET` to the
  development checkout `.worktrees/autowork-directory-admission`. That checkout is
  at 3848aaa on `fix/directory-parallel-admission`: two commits not in main, 19
  commits behind. Self-update follows only the Pi package or that checkout's own
  HEAD, so fixes on main never reach those runners. TOOLSET-138-62 merges the
  branch, so its ancestry is provable. TOOLSET-139-62 then removes a merged, clean
  pin automatically and reports an unmerged one as agent work. Both go first in
  Now, because every other delivery depends on them reaching the fleet.
- **Environment.** Worker `TMPDIR` lives under the deep state path, and Chromium
  fails there because of the 108-byte Unix socket limit (runner C
  a fleet task). TOOLSET-140-f4 gives each slot a short private directory.
- **Stall repair.** runner B has been stalled for seven hours on ledger tasks
  without full bodies, a cause TOOLSET-129-c4 only labels. TOOLSET-141-c4 adds a
  bounded docs-sync repair worker. It runs only when a stall's root is a
  repairable contract, so idle cycles still spend no tokens.
- **Display.** `autowork ls` shows a fallback for a runner configured with
  `PI_AUTOWORK_NO_FALLBACK=1`. This is recorded as additional acceptance on
  TOOLSET-130-15.

Observed but not tasked, because the evidence is insufficient or the work is
already owned: frequent external restarts (10 in 3 hours for runner B) issued by
systemctl rather than the runner; children reported as remaining after a unit
stop, gone by the next check; a fleet task's missing held candidate and the runner D
`pending_live` report hold (TOOLSET-120-fc); runner A's `Merge pending` caused by
uncommitted planning (TOOLSET-120-fc part 4); a fleet task's bracketed-route scope
conflicts (TOOLSET-099-87). Fleet owner decisions (runner D a fleet task/003/022, runner A
a fleet task claims) stay with each repository's BLOCKERS.md.

## Automatic stall recovery and conditional Docs Sync

Status: Accepted

Owner direction (2026-10-16): stalled runners must heal themselves, and Autowork
must run Docs Sync at task closeout when needed. The supplied fleet snapshot shows
runner B stalled for 7h31m with 27 questions, alongside four working runners.
This is supplied evidence, not a new live inspection or permission to restart
services. The outcome is resumed useful work and accurate documentation, not a
lower question count, a reset uptime counter or repeated model activity.

### Evidence and implementation ownership

At local de02326, `coordinator.cycle` settles tasks and then pauses/rechecks blocked
work. `health.update` detects and labels stalls; `update_questions` emits owner
questions. These observations alone do not execute a repair. There are already
specific recoveries for priority drift, inferred Touches and held verification.
Extend this same lifecycle authority; do not add a watchdog or a second scheduler.
TOOLSET-120-fc owns candidate-preserving recovery and repair-versus-owner routing;
TOOLSET-141-c4 owns missing/incomplete task-body repair. Retain both IDs and the
active TOOLSET-115-bf contract. TOOLSET-099-87, 139-62 and 140-f4 retain directory
admission, release delivery and short-temp-path fixes respectively.

`ENGINEERING-CYCLE.md` already calls for narrow Docs Sync Maintain at closeout,
but native/portable Autowork closeout largely names task metadata and archival.
`parallel_integrate.close` updates task/index/archive and pending live follow-ups;
this does not reconcile README, runbooks or architectural descriptions. Workers
cannot write coordinator-owned files. TOOLSET-146-bc closes this behavior gap
without treating archive rendering as a full Docs Sync pass. The known remote
contains newer atomic-close/report-hold changes; implementers must reconcile them
before editing overlapping code, preserving their crash-recovery guarantees.

### Recovery policy — extend TOOLSET-120-fc and TOOLSET-141-c4

Planner's call: evaluate an observed blocked root on the next normal coordinator
cycle, without waiting for the display's stall threshold. Continue compatible
independent tasks while recovering a held lane. Recheck source, candidate, lease
and live-writer evidence before each action. Classify by cause and actual missing
input, not the worker's use of the word “blocker”.

| Root evidence | Automatic action | Remaining limit |
| --- | --- | --- |
| Missing/duplicate task fields with accepted source material | One scoped Docs Sync repair under TOOLSET-141-c4, then admission again | Never invent product intent or erase conflicting requirements |
| Malformed report, stale claim or scope hold with a preserved candidate | Reconcile attributable report/claim/scope, resume or reverify existing work under TOOLSET-120-fc | No fresh implementation for a clerical change; no adoption of a live writer |
| Failed validation or merge conflict within accepted scope | Bounded repair on the retained candidate with normal isolation, checks and review | Do not discard competing work, waive checks or broaden Touches silently |
| Capacity, live lock/writer or genuinely running prerequisite | Refill compatible slots; back off the affected lane until evidence changes | No lock deletion, timeout-based ownership theft or killing healthy workers |
| Runner/toolset/environment failure with a supported recovery | Reuse the owning recovery handler and its version/health evidence | Restart only when that handler needs it; restarting is not proof of recovery |
| Missing owner decision, credential, external artifact or live qualification | One deduplicated question per root naming the exact missing input and affected tasks | No fabricated answers, acceptance reduction, automatic unpause or publication |

Run deterministic reconciliation first. If an actual repair needs reasoning, use
one scoped worker through the existing coordinator/worker path, with concrete
inputs, allowed paths, acceptance, timeout and the existing resource/cost limits.
It is not a generic “fix everything” prompt. Keep one repair writer per overlapping
resource; a repair does not bypass normal admission or consume extra unbudgeted
slots. Read-only idle/blocked polling and repeated unchanged causes spend no model
tokens. A reasoned repair may spend tokens once on supported work; this supersedes
the historical blanket “all stalled cycles make zero model calls” wording only
for that bounded repair.

Persist the repair attempt and disposition in existing private runner state,
keyed by task/root, relevant task/source hashes, candidate/report identity and
recovery-handler revision. Cosmetic wording, timestamps, restart or unrelated
commits do not reset the allowance. Recheck relevant external availability without
spending model tokens. A changed accepted source/candidate or relevant fixed
handler can justify a new attempt; record why. Default one reasoned attempt per
unchanged evidence set, with existing deterministic retry limits retained. Save
the attempt before launch and reconcile surviving processes on restart so a crash
does not duplicate repair workers. Treat unknown attribution as a hold.

After an unsuccessful attempt, retain the candidate and precise failed operation.
Continue independent work; expose exhausted internal repair as agent work, not an
owner decision with no answerable question. Existing accepted repair tasks are
reused, not duplicated each cycle. Only genuinely unavailable external input goes
to BLOCKERS.md. Many dependent tasks sharing one cause produce one root question.
The Needs view uses TOOLSET-129-c4's agent/owner distinction; status records repair
action, result, next retry condition and last useful progress. A launched worker
or service restart alone never advances the useful-progress timestamp.

For TOOLSET-141-c4 this refines “task-body fingerprint”: include the accepted source
evidence, and distinguish missing information from conflicting acceptance. Apply
repair when that root is observed even if another worker is active. The repair is
exclusive on its planning paths, not automatically exclusive over the whole repo.
Validate complete task bodies and rerun actual admission, not just ledger shape.
Missing source content becomes one precise external question only if it cannot be
recovered from local accepted evidence. Same-input repair exhaustion stays visible
as internal failure without another model loop or redundant owner question.

### Conditional closeout — TOOLSET-146-bc

Planner's call: every completed task assesses documentation impact; invoke scoped
Docs Sync Maintain only for a concrete delta. Use the verified diff, accepted task,
actual check results, existing document owners/role manifest when present, and
already-written documentation. Changes to user behavior, commands/configuration,
interfaces, architecture, operating procedures or verification requirements call
for a source-backed check of their affected docs. Metadata-only closure still
uses the existing supported task/index/archive helpers. No manifest is required,
and no blanket repository bootstrap or unrelated documentation audit is allowed.

Record one of `not_needed` (with reason), `updated` (paths and checks), or `pending`
(specific gap and resume action) in the existing task/closeout evidence, bound to
the relevant code and doc inputs. Workers update allowed component docs before
their final commit and report documentation impact/proposals for shared files.
Absence of a new report field in older reports means assess, not fail validation
or silently assume no docs are needed. A worker's assertion alone is not evidence.

The coordinator owns shared README/CHANGELOG/task metadata edits and runs the
narrow Maintain step at settlement of verified work, before final closure. Reuse
the existing Docs Sync skill, the runner's worker facility and serialized
integration path with explicit doc paths. Never invoke a model inside the atomic
close transaction or give a worker unrestricted coordinator-file access. Prepare
and verify documentation outside the short integration/write locks, then recheck
the source and expected doc bytes before applying. A stale candidate is reconciled,
not forced into place or made current by repinning receipts. Validate affected
docs/links and run the required integration checks on the actual final candidate;
reuse earlier checks only where unchanged inputs and repository policy permit.

Coalesce compatible completions in the same settlement pass into one Maintain run
for shared documents, retaining a disposition for each task. Do not wait for an
entire continuous fleet to become idle. Bound attempts to one per source/doc input
set and persist pending work so restart/interruption cannot lose it or repeat a
successful no-op. Finalize task/archive changes through the existing atomic-close
mechanism only after documentation acceptance is met. A required doc failure leaves
the code's real stage visible (for example integrated, closeout pending); preserve
it and repair documentation without rerunning implementation. Do not close or
remove its recovery evidence prematurely. Independent nonoverlapping work proceeds.

For sequential native/portable Autowork, the same session performs this scoped
step before final task closure under existing authority. Once/until-empty modes
include needed closeout within the original task limit; closeout does not select
new product work. Stops, pauses, budget exhaustion and explicit no-write/no-commit
constraints still apply: save permitted pending evidence and resume later rather
than claiming done or launching a new model after a stop. No new commit/push,
installation or live authority is conferred by running Docs Sync.

### Verification and handoff

Extend compact existing coordinator/integration fixtures: repair a supported root
and dispatch its dependent work; do so while an unrelated worker stays running;
repeat unchanged roots/restarts without duplicate workers or questions; preserve
a live claim, paused runner, exhausted budget, retained candidate and true owner
decision. Assert restored admission/verified integration, not just “repair started”.

Closeout fixtures cover a behavioral change needing docs, already-correct docs
with a recorded no-op, metadata-only closure, concurrent completions sharing one
doc update, foreign dirty docs, source movement, repair failure and restart between
doc preparation/application/closure. Both indexed and TODO-only repositories retain
their history owners. A failed docs gate cannot archive/close a task; retry updates
only docs and does not replay implementation. Use existing test seams with fake
workers and disposable Git repositories. Native/portable instruction compliance
needs a bounded behavioral scenario; unit forwarding tests alone do not prove it.

All new scenarios are proposed and unrun. Keep real fleet recovery under existing
TOOLSET-096-7e qualification, including resumed useful work and affected-doc readback
on the installed version. This planning pass edits only this plan, existing task
contracts and the ledger; it starts no worker, service, installation or publication.

Update (23:47, same pass, under the owner's added "reinstall autowork and restart
it as needed"): the pinned commits had meanwhile reached origin/main (de02326), so
the planner removed the four obsolete `PI_AUTOWORK_TOOLSET` pins (env files backed
up) and restarted runner D, runner A, runner C and runner B onto the Pi
package at 4192b13. All four reported `(Pi package)` and adopted their workers.
TOOLSET-138-62 is now verify-and-close; TOOLSET-139-62 automates the same repair.
New: runner A's session merge reports `conflicts with main in: .` because a stray
uncommitted file in the integration worktree blocks `git merge` before any
conflict exists. That is TOOLSET-147-54.

Update (23:50 pass): runner B's engine refuses its entire plan because two
session-branch task bodies end `Touches: …, docs/notes/.`, and the sentence-final
period parses as a dot-segment path. That one task-level error stops all 55
waiting tasks: TOOLSET-148-88 (first in Now). runner B was also stopped by an
external `systemctl stop` at 23:49 (no pause marker). The planner left it stopped:
restarting would only hit the same engine error, and its session merge is
separately blocked by uncommitted non-planning files in its canonical checkout
(README.md, docs/spec.md and others), which belong to whoever is editing there.
Elsewhere, runner C's held a fleet task and a fleet task
were rerun from scratch after a TODO change, with their earlier work kept on
set-aside branches. That is the generic-rerun behavior TOOLSET-120-fc's
continuation replaces; no new task.

Update (00:00, 2026-10-17 pass): TOOLSET-115-bf is now held because its offline
inventory cannot create AF_UNIX socket fixtures under the long task TMPDIR, so
TOOLSET-140-f4 moves to Now: it blocks the toolset's own redesign. New
TOOLSET-152-d4: the most frequent hold kind across the fleet is a worker naming
one or two exact files outside its Touches (a fleet task, a fleet task, TOOLSET-099-87,
a fleet task), and each currently becomes an owner question. A bounded
automatic widening (exact, non-protected, unowned files, once per task, then
reverify the same candidate) turns those into agent repair. On restart, the owner
asked for runner B to run. Its repository Hermes agent had been stopping the
service while it repaired the dot-segment Touches; it exited, its fix is in both
TODO.md copies, and the runner restarted at 23:58 with a fleet task
running. The agent left an uncommitted TODO.md edit in the integration worktree,
the TOOLSET-147-54 case.

Update (2026-10-17 pass): the owner saw runner A's TUI listing nine questions that
the repository's own agent showed were stale (a fleet task and a fleet task are open with
saved answers). Root cause: `update_questions` silently skips while the
integration worktree is dirty, and runner A's has a stray `tasks/plan.md`, the same
file behind its `Merge pending … in: .`. Folded into TOOLSET-147-54 (refresh
whenever BLOCKERS.md itself is clean; record and show staleness) and
TOOLSET-129-c4 (show question age, never stale questions as current).

Update (00:06, 2026-10-17 pass): runner B's repeated external stops came from
its own Hermes agent (owner-approved "stop the stalled service and repair
locally"). It stopped the service to take the queue locks while this monitor,
on the owner's "restart runner B", started it, and each saw the other as an
unexplained restarter or stopper. Its repair is complete ; the
runner was restarted at 00:06 and a fleet task is running. New
TOOLSET-153-64 (Next): an expiring planning hold, visible in `ls` and the TUI,
that keeps workers running and releases the writer lock, so repository agents
need not stop the service. Also observed and not tasked: stopping a runner kills
the leftover processes of a paused worker's test run by design (workers live in the
unit cgroup and resume on the same attempt).

Update (00:08, 2026-10-17 pass): owner direction "all 5 runners must work, use autowork cli or tui to manage services/runners". All five were working at 00:08. TOOLSET-153-64 moves to Now and gains a watchdog timer: a runner stopped without `autowork pause` or a live hold is restarted within 5 minutes, so an unexplained stop cannot leave a repository idle.

## Blockers repairs for malformed task contracts

Status: Accepted

Owner requirement: `/blockers` must fix routine duplicate-field contract problems
rather than merely report that no worker can start. This is a refinement of
TOOLSET-141-c4, not a second repair engine or authorization to expand product scope.
Implementation is future work; this planning pass changes no installed skill or
runner and does not edit the example repository.

**Observed evidence:** `task_execution._contracts` rejects repeated labels and also
rejects the simultaneous presence of `Checks` and `Verification`. The existing
recovery helper removes identical whole duplicate bodies, not repeated fields.
The current example a fleet task is already indexed done and archived; its archived
contract has one Checks procedure and one Verification paragraph of execution
claims. This is a concrete alias-collision shape, not evidence that it is still
blocked or that these are the exact bytes from the quoted failure. Do not reopen
or rewrite it, reproduce profile-private evidence paths, or infer a live PID/model
state from the user's earlier notification.

**Decided repair contract:**
- Teach `skills/blockers/SKILL.md` and portable blocker routes to classify malformed
  metadata as an internal planning repair. An invoked target-repository agent may
  repair its own queue within documentation-only scope; that is not authority to
  code, change acceptance, start an attempt, restart a runner or touch another
  profile. Toolset fleet monitoring still routes writes through the repository's
  existing runner/integration owner rather than editing foreign repositories.
- Use a shared Docs Sync repair operation from manual `/blockers` and the existing
  automatic repair path. Preview/apply use the same parser, exact target IDs,
  source-bound fingerprints, canonical lock, expected revision and writer-ownership
  guards. Remove byte-identical repeated fields once, retaining continuation bytes;
  do not silently normalize quoted commands/values or drop one of two alternatives.
- When a unique Checks procedure coexists with a Verification paragraph containing
  historical execution claims, retain Checks and relabel that paragraph Evidence
  (or append it to an existing evidence field losslessly), without turning a claim
  into a new pass. When both contain complementary required future checks, preserve
  every command in one canonical Checks field only after confirming the accepted
  source supports the combined procedure. Never choose the first/last value blindly.
- Differing Scope, Acceptance, Dependencies, Status, Sources, Touches or check values
  require reconciliation from the task's existing accepted source/current ledger,
  not guessing, weakening tests or unioning permissions. If those sources resolve
  the difference, apply the minimal supported repair; only genuinely unavailable
  product intent/authority creates an owner question. Missing/stale ownership or an
  exhausted internal repair stays an internal hold with its evidence/retry condition.
- Preserve ID/title, relative queue order, state/dependencies, budgets, live gates
  and accepted product/documentation-only scope. Fences, quoted examples, unrelated
  fields and other task bodies remain untouched. Never edit an active assigned
  contract or repin a worker. Use the supported planning handoff/hold if available;
  no raw service stop/restart or invented hold command to obtain a lock.
- Revalidate through Docs Sync and the actual task admission parser. A successful
  ledger validate alone is insufficient. Keep duplicate/conflict rejection intact
  for unresolved contracts; this is safe repair before admission, not permissive
  first/last-wins parsing. Dry-run writes nothing; a repeat is byte-stable.
- Classify repaired internal errors separately from real USER_INPUT/USER_DECISION
  questions. Preserve owner-maintained BLOCKERS entries and the runner-generated
  block's ownership; the runner refreshes its own notice. Report separately: repair
  saved, admission reason cleared, runner observed the update, and worker started.
  No service status or worker pickup is claimed without observation.

**Planned behavioral checks:** fixtures for identical repeated fields, conflicting
accepted intent, unsupported conflict, Checks plus historical Verification evidence,
two complementary/conflicting check aliases, multiline continuations, fenced examples,
stale revisions, live claims, unchanged retry fingerprints, idempotence and dry-run.
A composed fake-runner test must take a documentation-only blocked contract through
manual repair and actual admission with unchanged scope, no owner question, no model
execution, and no systemctl/runner configuration changes. Negative cases remain held
and independent eligible work continues. Reuse the existing recovery/admission/repair
fixtures, adding focused selectors instead of duplicating a whole workflow suite.

## Owned worktree healing and fresh task/question views

Status: Accepted

Owner requirement: Autowork detects and self-heals recoverable worktree problems,
and must not present stale tasks/questions as current. This refines existing
TOOLSET-119-2b and TOOLSET-130-15, coordinating their existing producer/display
owners TOOLSET-147-54 and TOOLSET-129-c4. No duplicate implementation task, new
watchdog, live repair, service operation or scheduling is authorized by saving it.

**Evidence:** `parallel_dispatch.create_worktree` currently adds a worktree before
journaling its creation, and says resolve by hand when an existing path/branch lacks
that event. `Coordinator.merge_main` can call a dirty integration checkout a conflict
with an empty file list. `update_questions` is covered by the existing dirty-session
refresh repair in TOOLSET-147-54. `fleet_view.read_questions` takes the first session
question block before canonical data without proving its generation is current;
`needs` counts it as open owner questions. These are source observations, not a
new live diagnosis of an unspecified runner, worktree path or prior incident.

**Worktree detection and healing (TOOLSET-119-2b):** On startup, recovery and the
next relevant failed transition, compare Git's registered worktrees, canonical
common-directory identity, intent/journal/slot records, path/branch/HEAD and actual
lease/process-birth ownership. Classify partial creation, missing path/registration,
occupied path/branch, dirty integration tree and unfinished merge separately, with
actual nonempty path/branch/reason evidence. Never equate directory existence or an
old ACTIVE label with ownership; never treat an unknown Git failure as a content
conflict. Existing dirty-tree preservation/delivery remains TOOLSET-147-54's handler.

Persist intent before any add/repair/slot transition. Resume an interrupted creation
only when exact recorded identities match and no live writer is displaced. Recreate
only a provably unstarted checkout or an exactly recoverable recorded clean candidate;
missing unsaved work is not reconstructed or declared recovered. For a foreign
path/name collision, preserve it: after exclusive task ownership and candidate
reconciliation, allocate a fresh uniquely journaled owned path/branch when safe rather
than require manual deletion. Unknown task ownership still holds that task, not all
independent lanes. No blanket worktree prune/remove, forced checkout, reset/clean,
stash or adoption based only on matching names. Preserve candidate checks, accounting,
pauses, ignored/untracked data, locked worktrees, branches and canonical-main delivery
requirements; do not place new task checkouts outside canonical `.worktrees/`.

Use existing recovery dispatch and write locks. Attempt a deterministic action once
per relevant identity/evidence/handler revision, journal outcome, and reconcile after
restart; corrected evidence allows a justified retry, unchanged polling does not.
Unsupported or exhausted internal repair is agent work with an exact resume condition,
not a fabricated owner question. Only unavailable authority/input is a human gate.
Do not weaken the matching-intent adoption restriction or modify another writer's
contract to make recovery succeed.

**Task/question freshness (TOOLSET-130-15):** Give status/question observations a
repository and session generation, queue revision, source path/ref, observation time,
last successful reconciliation and any refresh error. Keep question first-seen Since
separate from last refreshed: an old persistent question may still be current.
A healthy heartbeat alone does not prove its queue/questions were reconciled.

Build task state and generated questions from one reconciled engine/ledger view;
publish the snapshot atomically. Before listing a generated question as current,
validate its session identity and relevant task/cause against that view. A completed,
superseded, answered-and-reconciled or changed-cause task must not retain the old
question. An answer merely saved is not yet proof of resolution or worker pickup.
Question counts and Needs headlines use only validated current questions; retained
unverified entries are explicitly last-known/stale/unknown, not zero blockers or
healthy. Preserve historical failure evidence without replaying it as current state.

The producer retries question reconciliation after recovery on the next cycle.
Unrelated dirty files must not freeze a clean runner-owned BLOCKERS block; preserve
human edits and never commit a dirty/foreign-owned block as part of this repair.
If publication is blocked, record the reason and the affected last-successful revision,
not a freshly reset success timestamp. Keep internal repair state distinct from
USER_INPUT/USER_DECISION. This uses TOOLSET-147-54's producer rather than adding a
second question writer; TOOLSET-129-c4 owns the compact headline.

CLI, TUI and `/blockers` use the same read-only freshness-aware view. The first
available session file is not automatically the newest valid authority; do not mix
counts from one generation with labels from another. Missing/replaced sessions,
old schemas, incomplete snapshots and unavailable status yield explicit unknown or
stale source/age. UI polling neither mutates planning files nor launches a model or
repair; recovery stays in the coordinator. Preserve view-only controls and the
selected runner/task across refresh.

**Planned proof:** Real disposable Git/fake-process fixtures inject each creation/
journal/slot crash point, exact owned recovery, foreign collision, live/uncertain
owner, missing data, locked/ignored/untracked work and repeated restart. A safe
recoverable case advances in the same or next eligible cycle; protected cases stay
untouched while independent work continues. Include canonical `.worktrees/` placement
and exact branch/HEAD/candidate/evidence preservation assertions. Compose the dirty
integration repair with question/status publication: old resolved questions leave
the current view; a dirty BLOCKERS file retains bytes and shows a refresh failure;
a missing session cannot revive old canonical questions as fresh. Replayed/older
snapshots cannot overwrite a newer generation. An unchanged old Since with a fresh
reconciliation stays current. No model calls for detection/display, service changes,
forced cleanup, budget reset or invented acceptance. Existing focused suites are
extended, not multiplied into duplicate end-to-end suites; these new cases are unrun.

Update (00:19, 2026-10-17 pass): runner B commits BLOCKERS.md every ~2 minutes with only `Since:` changes, because question IDs from wrapped prose dependencies contain newlines and break `previous_since`: TOOLSET-154-d3 (second in Now, small). Two new runners joined the fleet (runner E, runner F). runner E is blocked on `a fleet task: not runnable`, the TOOLSET-141-c4 contract-repair case. runner D integrated and pushed a fleet task. The package self-update to c00a110 is still deferred while runners have work in flight; it proceeds after the 30-minute wait.

## Runner usage, delivery counts and real uptime

Status: Accepted

Owner requirement: runner statistics include tokens spent, tasks done and better
real uptime. Extend TOOLSET-130-15; reuse its existing CLI/TUI detail and health
pipeline rather than create another dashboard, scheduler or monitoring agent.
This is planning only: no source implementation, telemetry migration, provider call,
service restart or live statistics collection is authorized in this pass.

**Observed baseline:** `worker.worker` and `worker.verify` use `pi_runtime.job`;
`pi_runtime.analyse` sums assistant message-end totalTokens/cost and `record` appends
role/task/model/outcome/session/tokens to runs.jsonl. Records do not yet have a stable
invocation/event identity or explicit missing-usage coverage. `health.update.since`
is the start of the current health state, and fleet_view exposes it as minutes.
It is not process/service uptime. Coordinator.started is reset by initialization,
so it alone cannot measure uptime across re-exec. No live token/cost/uptime totals
were measured here, and no existing record was rewritten.

**Planner's calls — token accounting:**
- Show provider-reported tokens for Today and Recorded total, with an explicit
  timezone and collection-start/coverage label. The current invocation is available
  separately in detail. Use all attributable runner roles: implementation, review,
  merge resolution and authorized planning/repair/inference; include failed,
  interrupted and fallback/retry calls when actual usage was reported.
- Preserve native totals and supported input/output/cache-read/cache-write breakdowns
  with provider/model/role attribution. Do not add a cache count again to a native
  total that already includes it. Missing fields remain unknown; deriving a total
  requires a documented complete component contract. Tokens are not money or an
  invoice; subscription usage does not imply a USD cost. No pricing-service feature
  or budget-policy change is included.
- Give new invocations a durable run identity before launch, and account for each
  new assistant usage event once under that invocation. Use stable event identity
  from the supported stream where available; never hash response text to deduplicate
  legitimately identical calls. Resume/fallback is real additional consumption, not
  a repeated transcript to sum again. Replayed imports/snapshots and rollup rebuilds
  must not double count. Ambiguous legacy/replayed events yield partial coverage,
  not an invented exact total. A no-model launch can be known zero; a crashed call
  with missing usage cannot. Do not erase or reinterpret historical zero records as
  complete billing evidence.
- Prefer existing compact run/journal records; collect only new numeric/identity
  metadata at the supported runtime boundary. No prompt/response transcript,
  credential, browser URL or message content is added to telemetry. Do not scan
  unrelated Hermes profiles or provider accounts. Persist in private runner state,
  not TODO.md/goals.json or Git.

**Tasks done:** Primary metric is unique tasks delivered to canonical main/master
with matching integration/closure evidence attributable to this runner, for Today
and Recorded total. Count each task ID once per displayed window, not each attempt,
review, commit, restart, report or replay. Session-integrated/awaiting-main tasks are
separate, never called delivered. A reopened task's prior delivery remains a dated
historical event but is not a claim that it is currently closed; current pending
state remains visible. Do not credit a manual/external closeout to this runner merely
because its ledger changed. Legacy outcomes lacking attributable canonical evidence
are unverified/partial, not inferred deliveries. Preserve the existing distinction
between reviewed, session integrated, canonically delivered and published; no push
or publication is implied. Time filtering uses completion-event provenance, not log
file mtime; day boundaries follow the displayed timezone.

**Real uptime:** Display three explicitly different durations:
1. Current service/process uptime: the actual current systemd invocation's activation/
   start identity and matching monotonic time, or a verified foreground process birth
   on the current boot. Preserve it across a coordinator re-exec when the service/
   process identity did not restart; a real process restart starts a new uptime.
   Never use health-state Since or the first retained session timestamp as uptime.
2. Observed cumulative running time: persist proven service/process running intervals
   across restarts, excluding known downtime. Label collection coverage; do not fill
   an unobserved crash/reboot gap by subtracting the oldest wall-clock timestamp.
3. Observed useful-work time: union of intervals in which workers, verification or
   integration actually progress; simultaneous workers do not multiply elapsed time.
   Idle, blocked, intentionally paused and unknown gaps stay separately classified.

Use boot/invocation/process-birth identities; never mix monotonic clock domains or
compare old-boot ticks to current ticks. Wall-clock corrections must not produce
negative/huge uptime. Stopped or paused services do not have a ticking current uptime;
retain their proven historical durations. If identity/timestamps are unavailable,
show unknown/last-known age rather than reuse a recycled PID or stale heartbeat.
Do not publish an availability/SLA percentage without a defined observation window
and enough monitoring coverage.

**Publication and display:** One versioned reducer projects run/delivery/lifecycle
records into an atomic compact statistics snapshot, carrying source revision, last
successful observation, window bounds and coverage. Checkpoint incrementally outside
Git; do not rescan all retained history on every UI tick. Serialise concurrent append/
checkpoint writers, handle partial tails and rotation, and allow a replay-safe rebuild
from retained evidence. The cache is not a second lifecycle or billing authority.
Existing CLI status/long listing and TUI detail use that same snapshot; keep the
80-column list compact, expose breakdowns in selected detail, and preserve selection
and view-only controls. Readers do not write caches, call a provider/model or trigger
repairs. Stale/missing/legacy telemetry is labelled explicitly under the existing
freshness plan, not presented as a precise current zero. Any running-job usage that
has not yet been reported is described as in-flight/not yet included.

**Planned checks:** Extend the existing Pi runtime/health/fleet and composed worker
fixtures. Cover primary+fallback and failed calls, review/repair roles, missing/zero
usage, cache decomposition, replay/resume and concurrent append, malformed partial
records, rollup rebuild/rotation, timezone rollover, repeated canonical closure,
session-only/externally closed/reopened tasks, and incomplete history. Controlled
process/clock fixtures prove same-process re-exec versus real restart, boot changes,
wall-clock jumps, stopped/paused intervals, stale/PID-reuse refusal and union-of-work
intervals. CLI/TUI agree and readers leave files/refs unchanged with zero model calls.
Use small table-driven cases and the existing headless pilot; no real provider/model
benchmark or claimed historic backfill. These new acceptance cases have not run.

## Canonical plan and session reconciliation

Status: Accepted

Owner request: fix the stale runner/session state identified by the blocker check.
During this planning inspection, canonical main had both TOOLSET-164-f1 and
TOOLSET-173-94 open, while the session was three commits behind and still indexed
both in_progress. The engine retained TOOLSET-165-f7 as integrating with no live
implementation worker. These are observations, not proof that its review finished
or that its candidate can be adopted. Preserve that candidate, all real leases,
assigned contracts, attempt budgets, pauses and pending verification.

Source: Coordinator.follow_base defers all base merging while in_flight is true;
cycle calls it before settling, but settling/integration can block synchronously.
Coordinator.update_questions then combines an engine snapshot with session TODO;
questions.build emits a claim question without checking the current canonical
plan. More frequent question-file rewrites alone cannot repair that stale input.

Planner's call: extend TOOLSET-179-cf's existing reconciliation path to include
local canonical main, not create a watchdog, scheduler or second recovery engine.
Check committed canonical main every cycle/startup and immediately before admission
and question publication, independently of the rate-limited remote fetch. Remote
sync disabled or no upstream must not disable local plan following. In a clean,
unowned mutable session, merge canonical main through the existing path before new
dispatch, even when there are no outgoing session commits. Follow existing push
policy; local plan ingestion never requires publishing or enabling automatic push.

When a worker/review/integration owns mutable inputs, do not merge under it, repin
it, cancel it or move its worktree. Instead compare one read-only, revision-pinned
canonical plan with the engine/session snapshot. Publish provenance and a concrete
sync-pending cause in existing status: canonical revision, session revision, snapshot
observation time and sync reason. Never treat this informational comparison as
execution admission, ownership release or an instruction to edit a running task.
After the phase releases its inputs, reconcile and recompute before refill.

Use the same comparison for question validity. A cached claim whose only cause is
an old in_progress token, now open in the canonical plan, becomes internal plan-sync
waiting, not a new owner question. A real live lease remains a hold regardless of
that token. A genuinely new decision, unresolved external input or failed lease
inspection is never silently suppressed. Missing/changing source bytes, replaced
session, dirty inputs and old legacy snapshots remain stale/unknown with a reason,
not a healthy zero-blocker result. Keep stable question IDs and first-seen Since;
show last successful reconciliation separately. Preserve owner text outside generated
markers and dirty BLOCKERS.md; a skipped write must leave explicit stale provenance.

Ownership split: TOOLSET-179-cf supplies the producer reconciliation/provenance and
question-validity seam; TOOLSET-130-15 consumes it in CLI/TUI/blocker read views using
its already accepted freshness contract. Its machine dependency now includes 179-cf,
while retaining 129-c4. TOOLSET-147-54 still owns safe dirty-session preservation;
TOOLSET-158-08 owns rejected-push recovery and TOOLSET-181-02 owns semantic planning
merges. Reuse those outputs when present; no competing merge implementation here.

Planned proof, not executed: existing fake-engine/coordinator/question fixtures
exercise an owner-open commit while a separate integration is held; during the hold,
current owner-question counts exclude the obsolete claim but explicitly show sync
waiting; lease and assigned-input hashes stay unchanged. Release the fake phase and
observe canonical answers, recomputed admission and removal of obsolete questions
on the next cycle. Also cover no outgoing commits, no upstream, fetch disabled,
push disabled, dirty BLOCKERS preservation, a live claim, one unresolved real owner
question, missing/changing canonical data and restart/old-generation rejection.
Check the composed producer-to-CLI/TUI path, not just freshness timestamps or mtimes.
Use disposable repositories and fake commands only; no live restart, claim release,
provider call, service edit, network repair or delivery is authorized by this plan.

Rejected: clearing claims merely because main says open loses real ownership;
merging main during a pinned review invalidates evidence; auto-restarting runners
hides the coordination defect; repeatedly rebuilding BLOCKERS from stale session
inputs recreates the same question. Runtime implementation and tests remain pending.

### Review frontier observation (2026-10-17)

The owner's supplied 16:18–16:50 log is historical evidence, not a request to
restart or bypass a hold. At 23:11 UTC the retained TOOLSET-165-f7 slot was still
integrating and the coordinator had live verifier/check descendants; zero active
implementation workers therefore did not establish an idle runner. The original
candidate a8170f5 has an actual retained offline log ending in five passing test
directories (one skipped test, eight excluded modules). Its current integration
revision 9c399d4 differs in parallel_integrate.py and test_parallel_integrate.py;
that earlier passing log does not qualify these changed bytes. The terminal
integration receipt was not yet present. Candidate implementation, integrated-tree
verification, session inclusion and canonical delivery remain separate.

Keep the live assigned task body and all attempts/pins unchanged. The existing
integration owner collects the current check's terminal result, reconciles any
findings against that exact revision, then follows the normal integration and
closeout path. No replacement implementation, duplicate full gate, lease release,
restart or claim that the visible overlaps were cleared follows from this docs
pass. If the process later disappears without an exit/aggregate receipt, record
incomplete verification and resume through that owner with retained evidence.
The already-open canonical answers to 164-f1/173-94 remain the separate plan-sync
case above; they need no repeated owner decision. TOOLSET-130-15 carries this
current presentation evidence without changing TOOLSET-165-f7's pinned contract.

## Pipeline-first queue priority (2026-10-17)

Status: Accepted

Owner instruction: reorder all tasks; Autowork pipeline bugs are most important
now. This priority replaces older positional comments such as "second in Now"
inside individual bodies, not their scope, acceptance, dependency or ownership
requirements. Move whole task bodies without rewriting contracts or resetting
claims, attempts, review evidence, pauses or budgets. Done/superseded history and
external/live qualification gates remain unchanged.

Planner's call: prioritize the retained 165-f7 integration blocker, file-scoped
closeout 170-f6, restart survival 174-1d, nonblocking review 183-d6 and optimistic
integration 161-17. Keep 174 before 183 as the latter's ownership note requires.
Then repair the short-temp environment, integrate the retained release branch
before pin healing (138-62 before 139-62 and 099-87), and repair canonical/upstream
following, rejected pushes and merged-tree verification. Preserve confidentiality
checks alongside that delivery path; never trade them for speed.

Continue Now with lifecycle reconciliation, missing-toolchain handling, maintainer
and dirty-merge recovery, stable/meaningful questions, planning handoff, safe
worktree/landing recovery, resource scheduling and evidence-backed status. Promote
those existing runtime-fix successors from Next where required. Dependencies stay
as recorded; ordering is not evidence that a prerequisite passed or a lease is free.

Next starts with managed-updater and UI rendering bugs, then diagnostic navigation,
test feedback-loop thinning, planning/skill quality, compact ledger storage and
feature work. Move the exclusive linked-ledger implementation 149-df out of Now:
it must not drain the pool ahead of urgent runtime repairs. Its exclusivity and
149→150→151 dependency chain stay intact, and later authorized conversion is not
canceled. Leave native command packaging, model/accounts and the all-task browser
behind runtime fixes; do not cancel their accepted scope.

Keep the existing relative order of the late Next live/install/migration tasks
(123-a0, 066, 003, 098-5d, 019, 096-7e, 029, 011), including 019's recorded
in_progress state. All three Needs decision entries remain at the tail in their
existing order. No scan bypass, live login, deployment, profile update, cross-repo
migration, scheduler change, job resumption, implementation, commit or push follows
from this priority change. No active worker is stopped or redirected.

Verification is queue-level: preserve every pending ID and body byte-for-byte,
allow only intended section/order changes to the index, retain goal evidence and
dependencies, check full archive identity, run Docs Sync reorder/fmt/validate/render
and repeat stability, then report the actual next selection and consumer result.
The read-only engine probe returned ACTION_REQUIRED with resource-unavailable
(errno 11) during preparation; that is unknown runtime availability, not an empty
pool. Existing held candidates remain with their recovery owner; this pass does
not mark a failed or incomplete integration green.

## Worker-attribution candidate qualification recovery

Status: Accepted

The original accepted TOOLSET-165-f7 attribution scope and safety acceptance stay
unchanged. This is an evidence-backed planning repair under the owner's pipeline-bug
priority, not approval to skip a failing inventory, use a new host or restart a runner.

At the current blocker inspection, the session's only generated question is 165-f7's
attempt-2 report: it asks for a validation window/host or fixture timing repair.
The task is held, and the recorded attempt-2 implementation process is absent.
Its four-file implementation is retained uncommitted in the recorded -r2 worktree;
attempt-1 candidate a8170f5 and both failed reports remain historical evidence.
Focused task regressions passed, but the complete attempt-2 inventory failed; this
plan neither upgrades that result nor restores an older candidate over newer work.

Source inspection confirms `test_out_of_order_completion_lands_each_commit_once`
uses a two-second A sleep to require B to finish first, while
`test_two_retries_and_fresh_tasks_fill_eight_worker_slots` uses sixty-second fake
workers to require all eight slots remain occupied. Both assumptions can expire
before the observation under load. Replace only these ordering/lifetime assumptions
with deterministic test-owned ready/release signals, observable milestones, bounded
failure deadlines and guaranteed child cleanup. Preserve the original exactly-once,
no-lost-change, retry/refill, eight-distinct-slots and live-worker assertions. Do not
just inflate sleeps, skip tests, reduce the inventory or add production test hooks.
The existing fake-worker fixture may gain optional test-only signal handling with
unchanged default behavior; keep the change limited to the two named scenarios.

The existing checker correction 3bd1d95 isolates runner settings and caps/shapes
parallel test scheduling, but does not itself change these two fixtures. Reconcile
its delivered setup rather than duplicate it. The existing main check was running
on 3ca53ce at inspection: collect that check's terminal, source-bound result through
its owner rather than launch a duplicate run. Its outcome is not yet a pass here.

Next: the existing runner preserves the -r2 dirty work and reconciles current main
through its normal candidate workflow; carry forward the reviewed attribution fix,
apply only the named fixture repair if still needed, run the focused affected union,
then the complete offline inventory on the exact resulting tree. Reuse earlier
results only when their full relevant inputs still match. Keep cumulative attempts,
budgets, evidence, real claims, push guards and external/canonical writer protections.
No reset of consumed attempts, manual lease release, new worker, service restart,
installation, model call, deployment or push is performed by this planning pass.
A failed aggregate or missing terminal receipt stays unqualified. Broader test
thinning remains TOOLSET-127-b1, not a prerequisite or substitute for this repair.

## Runner activity versus partial task holds

Status: Accepted

Owner report: the fleet table shows `blocked 0m` and the detail `Stuck 0m` with no
Needs reason, even though other work/main verification continues; a later log shows
one task held for an omitted test file. Treat the supplied fleet values as historical
observations, not authorization to restart, widen a worker's scope or clear a hold.
A fresh read-only engine observation during planning reported two running workers
and a separate held TOOLSET-210-53. The missing test-scope hold is real task-level
work; it does not establish that the entire runner cannot progress.

Source inspection: health.classify already gives active workers/integration priority
over queue waits. fleet_view.collect starts from the persisted health state and
only overrides blocked/stalled/not-cycling when a lane has recent transcript activity;
fleet_view.verdict then selects its headline chiefly from runner.state. A quiet live
worker or mixed/stale generations can therefore be misrepresented. This is a
source-backed risk, not a claimed exact reproduction of the owner's terminal.

Planner call: refine existing TOOLSET-129-c4's display classification, with producer
provenance/shared CLI projection retained under TOOLSET-130-15. Keep the task's
recorded hold, admission gates, owner questions and background-job results distinct
from overall observed activity. From one coherent source-bound snapshot, running,
testing, reviewing or integrating work yields a Working headline plus the partial
hold count/reason; queue overlap/dependency/exclusive waits describe unused capacity,
not global Stuck while independent work progresses. Use existing identity/generation
validation; do not count an unvalidated old `running` slot or arbitrary process as
proof of life. Quiet validated work does not stop being active solely because no
transcript text arrived recently. Process existence alone is not proof of progress;
a real stale/stall indication remains visible as such.

With no task work but a validated main check/maintainer currently active, name that
activity and separately show why task admission is waiting. A previous failed
maintainer run is historical status, not itself a current global block. Blocked/Stuck
requires current evidence that task execution cannot progress, and a nonempty cause
or an explicit unavailable/stale reason; never `Stuck 0m` and Needs `-`. Intentional
pause, stopped service, failed current safety gate, real owner input and unknown or
contradictory freshness remain visible; no optimistic green fallback from missing
counts or a background heartbeat. Preserve first observation times separately from
new refresh time and do not reset the displayed age on each poll.

Apply the same derived classification to runner-row state/color, header totals,
Needs and selected detail; a single frame cannot say blocked and Working for the
same snapshot. The existing 130-15 freshness/provenance work owns eventual CLI and
producer parity; its fallback-policy correction also covers the pasted disabled-
fallback mismatch without creating another account/model task.

Planned proof (unrun): extend existing fleet/health/pilot fixtures for two active
workers plus one scope-held task; a quiet but identity-validated worker; review-only
and main-check-only activity; a historical maintainer failure plus current progress;
zero-progress dependency/exclusive/disk waits; real owner input; stale/contradictory
counts, dead/reused worker identity and pause/stop. Assert row/header/detail/Needs
agreement, accurate counts and nonempty wait causes across transitions as workers
finish, and no false pass/completion. Use fake clocks/data/process observations;
retain view-only and zero model/service/slot-mutation assertions. No new dashboard,
scheduler, repair loop, threshold-tuning campaign or implementation in this plan.

## Completion-first delivery and recoverable handoffs

Status: Accepted

### Outcome and owner decision

Improve efficiency and accuracy from worker completion through required verification,
session integration and canonical delivery. The owner chose completion-first admission:
when verification/integration capacity is saturated, defer NEW implementation starts,
while current workers continue. This is a planned admission policy, not a request to
pause/restart current runners, change their settings or execute this plan. Existing
checks, review, ownership, privacy, publication and live-qualification boundaries stay.

Planner's call: make incremental changes in the current shared lifecycle engine and
Pi wrapper, not a new harness, scheduler, state database or rewrite. Reuse existing
slots, journal, reports, check records, integration state and health projections.
Keep planning IDs/order and every active assigned contract. Existing partial phases
of TOOLSET-115-bf are not instructions to reimplement delivered code. Canonical local
delivery and remote publication are distinct; no new push/deploy authority is granted.

### Evidence and limits

The owner's historical worker view mixed running, reviewer-changed and verifying
labels with transcripts saying committed. These messages do not establish process
exit, report acceptance, passing review or canonical delivery. A read-only observation
during planning found two running workers, seven awaiting integration and ten session
commits not yet merged into main; this is queue evidence, not a proven defect or a
measured latency baseline. Current coordinator.cycle calls dispatch before settle;
settle already collects asynchronous integration, serializes review and closes
integrated tasks. reviewer_version fingerprints worker.py and validation/review
settings; reverify_held already bounds reoffers per version. Preserve these existing
mechanisms and tighten their boundaries rather than add another implementation.

### One authoritative completion lifecycle — TOOLSET-115-bf

Distinguish worker executing, terminal result/report available, report adopted,
verification queued/running/failed, qualified integration and canonical delivery.
Expose these through existing records; no new mandatory names or parallel tracker.
A transcript, heartbeat, git commit, old green main or PID alone cannot advance a
completion boundary. Validate task/attempt, commit, terminal execution evidence,
process-birth ownership, candidate/worktree and current effective contract. A valid
report written while an owned worker is still exiting is visible as awaiting that
terminal boundary, not silently closed or counted as a new implementation.

Use a stable task/attempt/candidate identity and the existing journal/receipts for
idempotent adoption, check collection, integration and closeout. Reconcile Git and
recorded intent after interruption; do not replay an already proven side effect.
TOOLSET-119-2b continues to own atomic intent/worktree creation, not a second journal
inside this change. A missing terminal result remains incomplete; preserve failures,
missing reports, dirty/untracked changes, real claims and cumulative attempt/budget
history. Unknown ownership is not permission to steal or kill a process.

A changed planning entry does not automatically justify fresh implementation. Compare
effective scope/acceptance/Touches/gates with the retained candidate: informational
notes alone do not invalidate it; a widened allowed path can permit qualification
of the same candidate; an actual changed requirement needs bounded reconciliation
against current code. Closed/cancelled tasks do not resume. Never restore an old
snapshot over newer source or repin a running worker/review to make evidence match.
Retained work is not a passing result and mandatory review is never skipped.

Bind each verification to the actual integrated source, check command/inventory,
relevant code/dependency/tool/environment inputs and effective review policy captured
at launch. Reuse executed results only when that full input closure is demonstrably
unchanged; otherwise rerun invalidated checks and required review. Different merged
code is not qualified by worker checks on its old base. No semantic-equivalence guess,
changed policy hidden by a stale fingerprint, skipped failure, stale receipt rewrite
or main-green substitution. Keep the launch fingerprint with active work across
polls/restarts; UI/config refresh must not fabricate a new review or imply one is
running. A genuine validation-policy or relevant environment change remains visible
and requires its affected qualification; budgeted reoffers do not replenish on restart.

### Completion-first capacity — TOOLSET-118-68

Use the existing engine gate, with coordinator settlement/collection before new
implementation admission. Count implementation and expensive test/review capacity
separately using current process-bound observations and cgroup/host limits. Unknown
resource usage stays unknown/conservative, not zero. Reconcile the current single
integration/review lane; this plan does not add parallel reviews on a shared tree.

Initial deterministic policy: an occupied completion lane plus at least one ready,
actionable candidate waiting for it is saturation. Reserve the resource headroom
needed by that lane, deny new implementation admission with a named completion wait,
and reconsider after every terminal collection. Continue existing workers and drain
eligible completion work in existing engine priority order. No arbitrary time limit,
new model-cost budget or constant threshold-tuning project. If no actionable
completion work remains and budgets permit, resume normal compatible starts.

An owner/external/foreign-writer hold alone is not an executable drain queue and must
not deadlock all unrelated work. Permit only the existing bounded prerequisite repair
needed to unblock completion, with its normal ownership, budget and safety checks;
this is not a backdoor to unlimited implementation. Persist sufficient policy state
for restart continuity, but derive actual occupancy from validated current evidence.
Do not relax load/disk/memory gates, clear leases, kill workers to free a slot or count
reported/held tasks as free resources without checking their remaining processes.

### Reliable checks and truthful views — existing owners

TOOLSET-127-b1 retains deterministic event-based fixtures and deduplication with every
unique assertion preserved; do not create another suite or infer speedup from fewer
cases. TOOLSET-212-0d owns disk-backed per-task scratch; TOOLSET-173-94 owns missing-
toolchain provisioning and bounded environment requalification. Use those outcomes,
not competing scratch/provisioning fixes or a second full-gate recovery task.

TOOLSET-130-15 consumes the engine's stage/evidence and the capacity gate reason in
one generation-bound CLI/TUI snapshot, reusing TOOLSET-129-c4's headline. Show report
awaiting adoption/exit, queued review, active check, integration/session-only changes,
canonical delivery and remote publication separately. Show quiet/last activity apart
from phase duration, pending policy invalidation apart from an active reviewer, and
real owner input apart from technical recovery. Missing/stale counts never mean zero.
Preserve the existing source-freshness prerequisites and all view-only restrictions.

### Source-audit refinements and concrete boundaries

Further source inspection confirms that parallel_state.reconcile already retains a
dead worker's descendant commit as reported, including preserved dirty residue;
parallel_integrate subsequently validates the report and candidate. Keep this split:
candidate discovery is not report acceptance, and neither is completed delivery.
The engine already checks an isolated merged tree and its closeout receipt; the
coordinator's target is its session, so that receipt alone is not canonical delivery.

Planner's calls: aged session commits alone do not trigger saturation. Attempt a
safe actionable closeout/landing before new admission; if a real external writer or
owner gate prevents it, expose that gate without globally freezing independent work.
Continuing an already live, validated worker is not a new start. Launching a new
implementation process, including retry/resume of an old attempt after its process
exited, is new admission and obeys completion backpressure, except the bounded
normally guarded prerequisite repair described above. Never resume an explicit pause.

Use existing records, not a new receipt format, to retain task/attempt/candidate,
review input signature and reviewed merge, integration and closeout commit identities,
and configured canonical ref/observed head. Canonical delivery requires the accepted
integration and closeout in that ref's ancestry with matching source-bound evidence;
missing ancestry/provenance is session-only or unknown, never Delivered. A remote
publication claim additionally needs authorized remote-ref readback.

TOOLSET-173-94's environment marker includes a commit, but environment_hold currently
reads only its missing-tool text; provisioning suppression also uses process-local
seen state. Bind the marker to the actual reviewed merge/task/attempt before acting.
Keep the existing one-provision/one-reverify policy durable by repository, task/attempt,
candidate, relevant review-input signature and normalized missing item; restart does
not grant another attempt or reset cumulative limits. Old mismatched markers are
historical, not a request to install tools for a different candidate. Record attempted
setup and failure evidence in the existing recovery owner, preserving cache-only scope.

Current worker.full_suite_gate already distinguishes baseline-equivalent and isolated-
rerun/flaky failures. This plan does not broaden or silently remove that policy.
Record the original full inventory's exit, baseline comparisons, rerun classifications,
skips and accepted exceptions explicitly. An accepted integration with those exceptions
is not an all-green run, and a rerun passing does not rewrite the original failure.
Preserve required execution/review and expose any unqualified or unavailable proof.

### Proof and efficiency observations

Extend existing controlled-process/Git fixtures, not live Pi/model calls. Cover:
report-before-exit and terminal-before-report; missing/malformed report; duplicate
polls; restart after each adoption/qualification/integration/closeout boundary; dirty
candidate and live/reused/unknown identities; planning-note-only changes versus real
scope changes; unchanged full inputs versus altered integration code/tool/review
policy; saturated completion lane, current workers continuing, capacity release and
resume; genuine external hold with independent useful work; and canonical closeout
with publication disabled. Assert one implementation and one adoption/delivery per
unchanged candidate, no duplicate check/review launch while valid evidence exists,
and affected requalification rather than false completion when inputs change.

Read existing events to report worker-terminal-to-adoption, report-to-review-start,
review duration and qualified-to-canonical-delivery separately, plus duplicate check
launches for identical input bindings and peak expensive-check occupancy. Unknown
historical timestamps stay unknown. Establish a source-bound baseline during
implementation; no latency/speedup percentage or fixed minutes target is claimed by
this planning pass. Acceptance is correct bounded transitions, no unbounded rerun
loop, and retained normal offline/review gates. The new scenarios are planned, unrun.

Implementation owners remain 115-bf (completion handoff), 118-68 (admission budgets),
127-b1 (existing fixture efficiency), 130-15 (projection) and 173-94 (existing environment
escalation). 118-68 already follows 115-bf; no reciprocal dependency is introduced.
Preserve unrelated queue ordering and live-work exclusions; planning does not promote
this chain above the current frontier or supersede the compact-ledger tasks.
