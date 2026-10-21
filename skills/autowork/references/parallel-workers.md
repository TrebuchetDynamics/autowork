# Parallel workers

Opt-in mode in which one coordinator session runs several independent tasks at
once, each in a headless host CLI worker in its own Git worktree, then integrates
the results one at a time. Without `--parallel`, `owner_cycle.py` behaves exactly as
before. Linux only (worker identity comes from `/proc`).

The coordinator is the current Autowork session. Workers implement one task and
commit once; they never select tasks, edit coordinator-owned files, push or close
tasks. Reusing earlier task work is the only permitted worker merge (see recovery
below). A worker's commit and `report.json` are evidence, not acceptance:
the coordinator reviews, integrates, validates and closes.

## Coordinator loop

All calls use `python3 <toolset>/pi-autowork/engine/owner_cycle.py REPO` with the
coordinator's verified `--owner-pid` (the same persistent session identity as
sequential Autowork). `--run` takes every argument after it, so put it last.

1. **Claim and dispatch.** `--apply --parallel [N]` claims the parallel coordinator
   lease, reconciles existing slots, plans the queue and starts up to N workers
   (default 2; at most 4 unless `--max-workers`, hard limit 8). Each worker gets
   worktree `<canonical-repo>/.worktrees/autowork-<TASK>` on branch `autowork/<TASK>` at the
   current canonical HEAD, its own process group, `TMPDIR`, `AUTOWORK_SLOT` and a
   100-port range from `AUTOWORK_PORT_BASE`. Results: `DISPATCHED` (started slots,
   each with its worker command and log), `WAITING` (each held-back task with its
   reason), `RETRIED` (a held task's fresh attempt, below), `READOPTED` (below), `IDLE`,
   `SEQUENTIAL_FALLBACK`, or `BUSY` and `ACTION_REQUIRED` as in
   sequential Autowork. `IDLE` only means no worker started and none is running.
2. **Wait.** `--wait --timeout S` blocks inside the helper until a worker exits or
   S seconds pass, so the coordinator spends no model turns polling. `CHANGED`
   lists the slots that moved; `TIMEOUT` means none did. A worker past
   `--worker-timeout` (default 3600 s, fixed when it started) has its process group
   stopped and its slot becomes `interrupted`.
3. **Review the report.** Read `report.json` at
   `<git-common-dir>/autowork-execution/slot-data/<TASK>/attempt-N/report.json`
   (commit, changed files, checks, blockers, pending live checks, proposed
   CHANGELOG line and [doc-impact evidence](#documentation-impact-evidence)) and
   the commit itself. A report is a claim; integration verifies
   it. `blockers` name what only a person can provide (credentials, devices, spending,
   third-party changes, open product or security decisions); a worker that reports any
   is held with `cause: blocker`, with or without a commit, and gets no fresh attempt.
   `--parallel-answer TASK --answer-file F` answers it instead: the attempt resumes in
   its own worktree with the answer in its prompt, at most twice per task. The Pi
   runner triages each new blocker this way and leaves only a person's part as a
   question. Exception: when every blocker is solely a wait for other open tasks, use
   `Needs TASK-ID to land.` (multiple IDs may be joined with commas or `and`). The
   [report classifier](../../../pi-autowork/engine/parallel_state.py) records `cause: task_wait`, `waits_for`
   and `wait_since` before triage; the runner never triages a slot with `waits_for`.
   Unknown wording, additional requests, self references and existing `depends_on` entries
   remain ordinary blockers for triage, not automatic owner questions. A task wait reserves
   no files or resources, but still holds its dependents. Once every named task closes
   locally or on the base, it resumes in place on the same attempt; the prompt names the
   prerequisites and pins reachable landed source revisions for scoped reconciliation,
   preserving retained work. An unresolved wait becomes one owner question after 24 hours,
   never a triage. The engine never edits `depends_on` for this wait. `pending_live`
   lists device, production, hardware or human checks the worker could not run;
   they never hold the task. `unrelated_failures` lists test IDs that passed a single isolated
   rerun or also failed on the baseline; `environment_failures` lists command/summary strings
   for checks that could not reach results (tool crashes before tests, command time limits,
   missing third-party packages). Both are normalized like `pending_live`, never hold a
   finished commit, and never bypass the runner's merged-tree validation gate.
4. **Integrate.** `--integrate TASK --timeout S --run ARGV...`, where TASK is the
   highest-priority `reported` task (otherwise `ACTION_REQUIRED`). It merges the
   worker commit with `--no-ff` in the detached integration worktree
   `<canonical-repo>/.worktrees/autowork-integration`, runs the validation argv there under a
   bounded process tree, and fast-forwards the canonical checkout only if its HEAD
   has not moved (one re-merge on a moved HEAD, then hold). Result: `INTEGRATED`,
   or `HELD` with a reason when:
   - the commit does not descend from the slot baseline, differs from the branch
     or the report, or the report lists blockers or a check that did not pass;
   - it edits a file under `tasks/`: only the coordinator writes the task store, so
     the commit is held and never merged;
   - it changes a protected file (manifest, lock file, schema, migration or CI file)
     its task did not declare for serial work. Files
     outside `touches` and files another slot changed are not held: the merge into the
     base, in priority order, settles them (TOOLSET-161-17);
   - the merge conflicts (aborted; the canonical checkout, its uncommitted files and
     the worker branch stay untouched);
   - validation fails, or the task contract or canonical branch changes meanwhile. A
     rank, title, short or note edit is bookkeeping; an acceptance, checks, dependency,
     touches, authority or section change is a contract change;
   - (not a hold) another live agent session would be affected: the result is `BUSY`
     and the commit stays reported until that session leaves. A session in the main
     checkout counts only when the merge changes a file it holds open for writing or
     has left uncommitted there, wherever the integration runs. A person's session
     never waits a merge by existing, being busy or having another checkout open.

   Other coordinator-owned edits (`CHANGELOG.md`, a frozen `TODO.archive.md`) are left
   out before validation, including conflicts only in those files and edits the runner
   or resolver introduced by merging into the task branch. Those paths always keep the
   current integration base's content. The
   [integrator](../../../pi-autowork/engine/parallel_integrate.py) saves the omitted proposal as
   `slot-data/<TASK>/attempt-N/ledger-edit.patch` and records `ledger_edit_dropped`
   (paths and patch path) on the slot. Candidates with only such edits integrate as
   empty changes; undeclared protected files still hold. Batch checks and reviews use
   the same stripped merge tree, not the omitted proposal.

   Once integrated, the [docs maintainer](../../../pi-autowork/pi_autowork/maintainer.py)
   gets a one-time `ledger edit` trigger with a bounded patch preview. It judges the
   proposal against current planning, then applies justified changes itself (task
   changes through `autowork tasks`) or drops it; the patch is never applied
   automatically. Draining
   runs, including `--once`, service all pending proposal batches before exiting.

   Validation runs in the engine's own journaled integration worktree. If it leaves
   changes there, the next integration saves them to
   `autowork-execution/integration-residue/*.patch` and resets that worktree only.
5. **Close.** `--parallel-close TASK` refuses unless the slot is `integrated` with a
   passing validation receipt and its task record's contract hash still matches the
   validated one. It writes `status = "done"` into `tasks/items/TASK.md` and the
   receipt `tasks/evidence/TASK.toml` (candidate, integration commit, tree, contract
   hash, checks, result, review; no paths or secrets), and removes the current
   attempt's worktree and branch if they are clean (`cleaned`). A replay writes
   nothing twice and returns only what is still uncommitted. When the report listed
   `pending_live`, close also adds the task `TASK-LIVE` under Needs decision,
   depending on TASK and listing those checks, exactly once: offline completion
   never qualifies live behavior. Result: `CLOSED`, with `live_followup` when one was
   added and `files`, the exact paths it wrote, for the coordinator's commit.
6. **Commit coordinator files.** Close writes the task files in the canonical
   checkout without committing. Commit them, plus the CHANGELOG line from the report
   if it is accurate, as one closure commit.
7. **Refill.** Call `--apply --parallel [N]` again: freed slots take the next
   eligible tasks, and a task that depended on a closed one becomes eligible.
   Before releasing, integrate or close every `reported` and `integrated` slot,
   handle `held` ones, and check `waiting`. Release with `--parallel --release`
   only after the pool drains: it ends the coordinator lease, not the workers, and
   a sequential Autowork claim does not wait for surviving workers.

`--parallel-status [--json]` is read-only at any point and needs no owner: workers
active out of the maximum, one row per task (state, slot, elapsed, blocked reason and
`blocked_by`: the task IDs or outside condition holding it), `roots` (where each waiting
chain ends: `held`, `claim`, `contract` (a task record the engine will not run, with its
reason), `outside`, `cycle`, or moving work, with how many tasks it holds),
completed/failed/integration-queue counts, and journal metrics (wall, worker,
integration and waiting time, peak workers, conflicts, retries). A `claim` root
carries `held_by`, the task's current `Held by:` note; it holds until the note is
released (`autowork tasks release ID`) or its `until` date passes.

## Documentation impact evidence

Every worker assesses the final diff against task Acceptance and existing docs.
Use `doc_impact` in `report.json`, for example (illustrative, not a receipt):

```json
{"status": "updated", "reason": "Guide now describes the changed command",
 "paths": ["docs/guide.md"],
 "checks": [{"command": "git diff --check", "result": "pass", "summary": "guide read back; diff whitespace checked"}]}
```

- `not_needed`: explain why inspected docs already cover the change or why
  metadata-only work affects none. `paths` lists inspected docs (may be empty).
- `updated`: name changed component docs and copy their passing readback/check
  records from the report's top-level `checks`. Resolve bundled Docs Sync in the
  actual host for scoped Maintain; no full bootstrap or global manifest.
- `pending`: put the concrete gap in `reason`, inspected docs in `paths` (may be
  empty), and the specific DOCS-MAINTAINER action in `resume`. Shared documents
  remain with the coordinator; do not edit their policy, Acceptance or history.

Integration retains the assessment in the slot's verified `report.doc_impact` and
exposes it as `doc_impact` in the task snapshot, including after closure/restart.
It adds `inputs` with exact `baseline`, worker `commit`, `task_contract_sha256` and
`documents` mapping inspected paths to committed blob IDs (null for deletion).
These are worker-source inputs, not a claim that merged/current docs are identical.
Consumers must compare current source/docs and preserve foreign dirty work before
reconciling; never make stale evidence current by repinning it. An existing
mismatched `inputs` binding, missing/invalid assessment, missing path or unsupported
update/check claim becomes `pending`, not an implementation retry or silent no-op.
Older reports remain valid and need assessment. Raw reports remain available
beside normalized slot evidence.

DOCS-MAINTAINER owns the conditional closeout Maintain pass (TOOLSET-266-7a).
These fields introduce no new trigger, model call, closure gate or second atomic-close
authority. A worker assertion is not documentation acceptance; task-store
bookkeeping alone is not Maintain. Sequential native/portable closeout uses the same
[scoped assessment](../../shared/ENGINEERING-CYCLE.md#one-canonical-backlog-one-executor-one-closure-owner)
in its authorized session. Required doc failure/interruption preserves code and
pending evidence without replaying implementation. Stops and pauses
launch no new work; once/until-empty limits include needed closeout.

## Runner jobs versus outside sessions

The [writer scan](../../../pi-autowork/engine/task_execution.py) excludes this repository's own
runner jobs before integration, closeout and slot worktree cleanup check for outside
sessions. The primary attribution is the process's `/proc/<pid>/cgroup`: an exact
`pi-autowork@<canonical-repository-name>.service` component, including its child
cgroups. A different repository's unit does not qualify.

For foreground runs, the [coordinator](../../../pi-autowork/pi_autowork/coordinator.py)
sets `AUTOWORK_EXECUTION_COMMON` to the repository's absolute Git common directory
on every main check and Pi auxiliary job (DOCS-MAINTAINER, provisioning, merge
resolution and Touches inference). Children inherit it. If a test harness sanitizes
its child's environment, a still-live marked ancestor retains attribution; under
systemd the cgroup also covers detached jobs that drop the environment. Fixture
repositories do not match the real runner's marker or repository-specific unit.

A `pi-scratch-*` name alone grants no exemption: an outside person's agent there
still blocks, as does an otherwise blocking session in the main checkout. A blocked
integration's process evidence explicitly says `session`, so mistaken attribution
is visible instead of looking like an unidentified check process. These rules do
not change which outside sessions block or how often the main check runs.

## Worker temporary directories

`TMPDIR`, `TMP` and `TEMP` all point to the same private, owner-checked directory
(mode `0700`), outside the checkout. Prefer
`$XDG_RUNTIME_DIR/aw/<hash8>/<temp-slot>`; if runtime storage is unset, unavailable,
inside a checkout or too long, use `/tmp/aw-<uid>-<hash8>-<temp-slot>` instead.
`hash8` is the first eight characters of the runner's repository state-directory
name: SHA-256 of the absolute Git common-directory path (the same namespace for
standalone dispatch). Paths are limited to **47 encoded bytes**, leaving at least
60 bytes below Linux's 108-byte Unix-socket pathname limit, including its NUL.
Foreign-owned existing directories and symlinks are refused, not adopted.

The compact numeric temp slot is reserved in
`slot-data/<TASK>/tmp.json`. It is independent of the worker lane/port number:
refill can reuse a lane while the previous task still retains temporary files.
Resume, retry and coordinator adoption preserve the allocation and contents,
even if `XDG_RUNTIME_DIR` changes. Close and set-aside/requeue remove the temp
directory and release its reservation only after the worker has stopped; ordinary
holds, pauses and coordinator release keep it. Older workers already running with
a long `TMPDIR` keep their environment until relaunched. Logs, reports and other
attempt evidence remain in Git-common execution state, not in the temp directory.
Reviewers find the worker's retained files through this reservation; slots from
older releases without one still use their attempt-local `tmp` directory. Shared
SDKs and package caches remain in `AUTOWORK_CACHE`, independently of temp cleanup.

## Admission: touches and resources

`touches` schedules work, and a shared hot file holds it:

- `touches` is the task record's list of repository-relative paths or globs the
  task is expected to change; `*` also matches across `/`, and a trailing `/` covers a
  directory. A literal file is **hot** when at least three unfinished tasks name it
  explicitly, counting each task once across the whole queue, including tasks not yet
  runnable. A long file is not serial for its length alone. A task naming the same hot file as
  running work or a commit awaiting integration waits with
  `waits for <task> (shares hot file <path>)` until that task lands. Newly selected work
  also reserves its hot files, so free slots cannot start two owners at once. A waiting
  task or idle claim holds no files; a free hot file goes to the higher-priority task
  first. Cold-file, directory and glob overlap only ranks work after independent tasks
  (TOOLSET-161-17). A worker may change
  whatever else its task needs; the merge into the base, in priority order, settles the
  rest, and a real conflict goes to the merge resolver. A missing or invalid `touches`
  is no hint (the task ranks after hinted ones).
- While worker slots idle and tasks wait on a shared hot file, the DOCS-MAINTAINER re-cuts
  those tasks before they run (`overlap` trigger): it may merge one into a task that has
  not started, split off the shared-file part as a dependent follow-up, supersede a
  duplicate or make the order explicit, without touching running tasks.
- `resources = ["live"]` or `["exclusive"]` makes a task run alone. Other names
  (for example `resources = ["port-8080", "test-db"]`) keep tasks that share a name from
  running together.
- A task touching a serial path (dependency manifests and lock files, `migration(s)/`
  and `schema(s)/` directories, CI files such as `.github/workflows/`) never runs beside
  another task that touches a serial path (`serial path shared with <task>`), but runs
  beside independent work: each worker has its own worktree, so its manifest change
  cannot break a neighbour's build.
  Directory scopes use the repository's tracked and nonignored untracked protected
  files: `test/shaders/` is not exclusive merely because a manifest could be created
  there. Explicit manifest paths and schema/migration/CI directories remain serial
  even before they exist. A worker introducing a new protected file through an ordinary
  directory scope is held at verification until its task explicitly reserves serial work.
- Dependencies and store priority (section, then rank) still apply: a task waits
  for its `depends_on` tasks to close. A `depends_on` entry naming no task stays an
  unresolved outside condition. A lower-priority task starts past a higher-priority one
  that cannot start yet only when it shares no resource or dependency with it. A task
  that must run alone (a `live`/`exclusive` resource) and waits on running work stops all lower-priority
  dispatch so the pool drains for it, once it has waited that way for
  `PI_AUTOWORK_DRAIN_AFTER` seconds (default 1800, counted from the journal); until then
  independent work backfills and it reserves only what it declares. A serial task never drains.
- Slots that are `reported`, `integrating`, `integrated` or `interrupted` retain their
  shared-hot-file and resource reservations until closed, even after their worker ends;
  exhausted held slots block only their dependents. A `held` or `interrupted` slot whose task is now done
  or superseded in `tasks/` blocks nothing; its worktree and record stay for
  inspection. A task with a current `Held by:` note is a claim: it is never
  dispatched and blocks its dependents and tasks whose `resources` or serial work
  overlap it, but its files hold nothing. `autowork tasks release ID` lifts it; the
  engine never adopts a held task.
  The worker's prompt names the earlier branches and worktrees to reuse; they are never
  modified. Only live workers count toward N.

`tasks/`, `TODO.archive.md` and `CHANGELOG.md` are coordinator-owned: workers must
never edit them. A worker commit that edits `tasks/` is held and never merged;
integration leaves out the other files' edits and hands their patch to the docs
maintainer. Nothing grants a worker write authority over task files.

### Shared admission path and history

Fresh/resumed dispatch (`admit`) and held retries (`retry_plan`) in
[`parallel_dispatch.py`](../../../pi-autowork/engine/parallel_dispatch.py#L1028) both use
[`parallel_plan.plan`](../../../pi-autowork/engine/parallel_plan.py#L271). They supply the same
tracked/nonignored-untracked protected-file inventory to the planner's directory
classification and the full unfinished task context (including dependency- and
decision-held tasks) for hot-file counts; these are callers of one policy, not
alternative admission rules. Only runnable contracts are dispatch candidates.
The [retry lifecycle guard](../../../pi-autowork/engine/parallel_state.py#L348-L355) also calls
`retry_plan`. [Integration](../../../pi-autowork/engine/parallel_integrate.py#L220-L234) checks the
original dispatched contract against the protected inventory at the slot baseline,
so later files or contract edits cannot retroactively authorize serial work.
Fresh, retry and integration worktrees all use
[`worktree_path`](../../../pi-autowork/engine/worktree_paths.py#L38) under the canonical checkout.

TOOLSET-138-62 provenance: current-history directory-admission commit
`34d988b7962c7942c97dcf703ff8fc17b3741db2` landed through merge
`3504855659952b9a42ea6b6f78310878d0733f42`. Its stable patch ID matches original
`3848aaa5eb07aaec97005360a7827b6401f1dc38`:
`c05c5b1c7932ab86d8d3555ec30202f6f4908aa0`. Patch equality does **not** establish
original ancestry or qualify an installed runtime pin. Keep a retained old pin
unchanged unless its actual commit passes `git merge-base --is-ancestor PIN main`;
service pin handling belongs to TOOLSET-139-62, not admission verification.

Requalify after admission-policy, worktree-placement or history changes: check both
current-history commits against the actual target `main`, compare provenance with
`git show COMMIT --format= | git patch-id --stable`, and run the existing
`test_parallel_*.py` engine tests plus `test_worktree_paths.py`. These cover
independent retries beside workers, protected directory inventory and undeclared
new protected files, and canonical placement from linked checkouts. Offline engine
tests do not qualify live services; the runner's merged-tree gate remains required.

## Hosts

`--worker-host auto` (the default) uses the coordinator's own host, found from its
process ancestry. Shipped templates add no approval or sandbox bypass:

| Host | Worker command | Live qualification (TOOLSET-091-00) |
| --- | --- | --- |
| Hermes | `hermes chat --query-file PROMPT --oneshot --in WORKTREE --run-budget TIMEOUT -Q`, with `-p PROFILE` from `--worker-profile` | Not run, not required (owner decision 2026-10-15: Hermes plans tasks, Pi workers execute them); `/autowork --parallel` from Hermes remains unqualified |
| Codex | `codex exec -C WORKTREE --sandbox workspace-write --add-dir GIT_COMMON_DIR -` (prompt on stdin) | Fails: Codex 0.162.1 workers edit and check but cannot commit, because the workspace-write sandbox keeps Git metadata read-only. Dispatch therefore returns `SEQUENTIAL_FALLBACK` for Codex unless you pass `--worker-command` |
| Pi | `pi -p @PROMPT` | Qualified through [`pi-autowork.sh`](../../../docs/cross-host.md#run-autowork-continuously), whose `--worker` mode is passed as `--worker-command` (Pi 1.2.0, GPT-6.1 Sol): two workers overlapped, integration was sequential, a dependent task waited for its prerequisite, and a killed coordinator's restart adopted live workers without duplicates. The bare template has not been run live |
| Claude Code | none: it chooses its workers' approval mode, so pass `--worker-command` | Not applicable |

`--worker-command` takes a JSON argv list with `{worktree}`, `{prompt_file}`,
`{report_file}`, `{git_common_dir}` and `{timeout}` placeholders, for any host. The
result is `SEQUENTIAL_FALLBACK` with the ordinary single-task contract when there
is no usable template: a Claude Code coordinator without `--worker-command`, a host
not detected in the process ancestry (pass `--worker-host`), a missing worker CLI,
or a non-Linux system. Run that contract with plain `owner_cycle.py --apply`;
nothing parallel was claimed or started.

## Conflicts, recovery and limits

- **Held tasks** keep their worktree and branch for inspection. The next
  `--apply --parallel` gives an eligible held task one fresh attempt (`RETRIED`)
  on `autowork/<TASK>-r2` in `<repo>/.worktrees/autowork-<TASK>-r2`, from the current
  canonical HEAD, keeping the first branch. Retries use the same dependency,
  Touches, resource and capacity checks as fresh tasks, and receive a free worker
  slot. Independent retries and fresh tasks can run together; a retry with unknown
  scope or exclusive resources still runs alone, and one with serial paths never runs
  beside other serial work. When the first commit
  was held only for scope
  (`changed files violate Touches`) and the retry made no commit, refill returns
  `READOPTED` and sets the first commit back to `reported`, once: scope can change
  after a hold, and integration repeats every check, judging scope by the `touches`
  the worker was dispatched with (from its prompt), not by `touches` recorded later. A second failure stays held:
  send it to Plan For Me to fix or skip. Until then it blocks only its dependents:
  it reruns fresh from the code of that time, never merges as is, so overlapping
  work proceeds. A worker-reported blocker holds the same way at once, except a host/check-only
  blocker with uncommitted work: it resumes the same attempt once with an instruction to
  commit finished work using the advisory failure fields. A repeated such report becomes
  `timeout`, not an owner question; the coordinator resumes it when the resource gate allows.
  Task waits described above resume without spending a retry; other inputs go through
  blocker triage, which leaves only a person's part as a question. Closing a
  retried task leaves the first attempt's worktree and branch for manual cleanup.
- **Hold causes:** [`parallel_state.HOLD_CAUSES`](../../../pi-autowork/engine/parallel_state.py) owns
  the supported machine-readable causes and their recovery policies:
  `reoffer_once`, `resolve_conflict`, `ask_owner`, `rerun` or `wait_for_task`.
  `next_action(slot)` selects the refill policy; evidence, liveness and attempt
  limits still apply. Reoffers require repaired evidence before the same commit is
  checked again; a report or validation failure can otherwise use its ordinary fresh
  retry. Scope holds retain protected-file admission and answered-rescope checks;
  timeouts wait for coordinator reverify, never a fresh worker.
  A transition to `held` rejects an explicit unknown cause without changing the
  slot or journal. An omitted new cause defaults to `crash`; old missing or unknown
  causes read as `crash` without rewriting their files. Historical non-verdict holds
  retain their compatibility recovery through the state helper, not refill's display
  text parsing. `scope` carries `outside` (undeclared protected files), and `task_wait`
  carries `waits_for`. Integration's `HELD` result carries its cause and details too.
  Offline coverage: `test_hold_causes.py` exercises rejection, legacy reads and every
  cause's refill action; `test_parallel_state_model.py` checks that held slots always
  have a known cause during its random walk.
- **Holds from before TOOLSET-161-17:** a commit held for `overlap`, or for `scope` on
  files that are not protected (including coordinator-owned files), is offered again once
  (`REOFFERED`) in priority order and integrates by merge; a worker held with
  `scope_request` (it stopped to ask for files) resumes in its worktree (`RESUMED`).
- **Reverify:** `--integrate ... --reviewer-version V` records which validation held a
  commit (`reviewed_by`). `--parallel-reverify TASK --reviewer-version V` sends a commit held
  by validation back to `reported` once per version V, and only when V differs from the
  one that held it (a hold without the record counts as an older one). The attempt is
  unchanged and integration repeats every check; a coordinator passes a fingerprint of
  its verdict code, prompts and validation settings, not unrelated worker helpers.
  Reverified slots integrate behind fresh reported slots, with task priority kept
  within each group. If a changed reviewer repeats the same failure line (ignoring
  revision IDs), that commit stays held for the maintainer's `review findings` trigger;
  a different verdict or new commit resets this limit. Timeouts are not verdicts and
  may still be retried with a longer limit. See
  [`reverify` and `reverifiable`](../../../pi-autowork/engine/parallel_integrate.py).
- **Answers re-queue:** each attempt records the contract it was dispatched with
  (`contract.txt`). When a held task's record no longer matches it (the owner
  answered by editing the record), the next refill retires the slot as a set-aside
  does and returns `REQUEUED`; the task then dispatches fresh. An entry that was
  removed is retired with `requeued: false`. An unchanged entry stays held. A new
  coordinator claims the lease before these checks, so a one-shot run sees them.
- **Set aside:** `--parallel-set-aside TASK` retires a finished commit waiting to
  merge (also one whose review a restart interrupted, unless that merge already
  landed), a held slot with no attempt left, or an integrated one whose task
  contract changed after validation (its merge stays in the main branch; the new
  contract is new work). The runner sets aside a commit at the merge adoption limit itself,
  so its task runs fresh on current main. Every attempt's
  worktree and branch is kept, renamed with `-set-aside-N`, and the slot record and
  data move to `slot-history/TASK/N`; the next refill dispatches the task fresh.
- **Earlier task work:** [the worker prompt](../../../pi-autowork/engine/parallel_dispatch.py) lists
  this task's local `autowork/<TASK>-set-aside-N` branches (including retired `-r2`
  attempts) and previous attempt branches, excluding the current branch. Each has
  its tip commit, commit date and changed files, newest tip first. Changed files
  are measured from the merge-base of that tip and the new attempt's baseline;
  unrelated histories retain their tips with the changed-file list marked unknown.
  All refs are reachable from the worker's worktree without fetching. Only when
  the current task asks to keep or continue earlier work may the worker merge or
  cherry-pick from those tips; otherwise it must ignore them. Nothing is applied
  automatically. Inspect the diff and bring in only paths the current record's
  `touches` allow, never coordinator-owned or unreserved protected files; a
  mixed-scope commit requires selecting allowed paths instead of importing the
  whole commit. Keep one final task commit (`cherry-pick --no-commit` or
  `merge --squash`, for example), and leave earlier branches and worktrees intact.
  Discovery changes neither set-aside decisions nor integration's scope checks.
- **Interrupted or released workers** (timed out, or dead with uncommitted changes
  or with nothing) restart once in the same worktree with a resume note; a second
  interruption is held. A deliberate coordinator stop first runs `--parallel-pause`
  (with `--owner-pid`), which marks live workers `paused`; a paused
  worker that dies resumes in its worktree on the same attempt, spending no retry
  and never holding a second attempt. The flag clears when it is dispatched again. A failed first launch holds the task, which can still get
  the `-r2` attempt; a failed restart launch uses up its retry.
- **A restarted coordinator** reclaims the lease and reconciles the slot records
  under `<git-common-dir>/autowork-execution/slots/`: live workers are adopted; a
  dead worker with a commit becomes `reported` (keeping any uncommitted changes),
  one with only uncommitted changes `interrupted`, one with neither `released`, and
  one whose HEAD left the baseline `held`. No task gets a second worker.
- **Name collisions:** [dispatch](../../../pi-autowork/engine/parallel_dispatch.py) adopts a clean, idle
  journaled task worktree after verifying its identity. An orphan task branch without commits
  beyond the dispatch baseline is removed with `git branch -d` and journaled as
  `stale_branch_removed`; otherwise its work is kept under the next free
  `-set-aside-N` name. A clean, idle task worktree can be removed without force before
  this recovery. Dirty worktrees (including ignored files), unrelated paths and
  branches checked out elsewhere are preserved: only that task waits, while
  independent tasks dispatch. [Slot retirement](../../../pi-autowork/engine/parallel_integrate.py)
  also skips existing set-aside names, preserving earlier attempts.
- **Resources:** a worker starts only while MemAvailable is at least twice
  `--min-free-mem-mb` (default 1500): one worker's budget plus as much spare, however
  many already run, since their memory is already out of MemAvailable. In
  [dispatch](../../../pi-autowork/engine/parallel_dispatch.py), the 1-minute load average must be below
  the CPU count only when this runner already has a live worker; its first worker
  still obeys the memory and disk floors. [Runner health](../../../pi-autowork/pi_autowork/health.py)
  shows load-only waits as `waiting for the host (load L on N CPUs)`, never stalled.
  pi-autowork removes stale agent scratch from a RAM-backed `/tmp`
  (`PI_AUTOWORK_TMP_STALE`) so it cannot hold this.
- **Authority** is unchanged: workers inherit no publication, push or deployment
  authority, and the canonical checkout is only ever fast-forwarded.

Offline tests use deterministic fake workers; they do not qualify real model
workers or measure their speedup.
