# Parallel workers

Opt-in mode in which one coordinator session runs several independent TODO tasks at
once, each in a headless host CLI worker in its own Git worktree, then integrates
the results one at a time. Without `--parallel`, `owner_cycle.py` behaves exactly as
before. Linux only (worker identity comes from `/proc`).

The coordinator is the current Autowork session. Workers implement one task and
commit once; they never select tasks, edit coordinator-owned files, push or close
tasks. Reusing earlier task work is the only permitted worker merge (see recovery
below). A worker's commit and `report.json` are evidence, not acceptance:
the coordinator reviews, integrates, validates and closes.

## Coordinator loop

All calls use `python3 <autowork>/scripts/owner_cycle.py REPO` with the
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
   `SEQUENTIAL_FALLBACK`, or `BUSY`, `PRIORITY_DRIFT` and `ACTION_REQUIRED` as in
   sequential Autowork. `IDLE` only means no worker started and none is running.
2. **Wait.** `--wait --timeout S` blocks inside the helper until a worker exits or
   S seconds pass, so the coordinator spends no model turns polling. `CHANGED`
   lists the slots that moved; `TIMEOUT` means none did. A worker past
   `--worker-timeout` (default 3600 s, fixed when it started) has its process group
   stopped and its slot becomes `interrupted`.
3. **Review the report.** Read `report.json` at
   `<git-common-dir>/autowork-execution/slot-data/<TASK>/attempt-N/report.json`
   (commit, changed files, checks, blockers, pending live checks, proposed
   CHANGELOG line) and the commit itself. A report is a claim; integration verifies
   it. `blockers` name offline work the worker could not finish and what a person
   must decide; a worker that reports any is held with `cause: blocker`, with or
   without a commit, and gets neither a resume nor a fresh attempt. `pending_live`
   lists device, production, hardware or human checks the worker could not run;
   they never hold the task.
4. **Integrate.** `--integrate TASK --timeout S --run ARGV...`, where TASK is the
   highest-priority `reported` task (otherwise `ACTION_REQUIRED`). It merges the
   worker commit with `--no-ff` in the detached integration worktree
   `<canonical-repo>/.worktrees/autowork-integration`, runs the validation argv there under a
   bounded process tree, and fast-forwards the canonical checkout only if its HEAD
   has not moved (one re-merge on a moved HEAD, then hold). Result: `INTEGRATED`,
   or `HELD` with a reason when:
   - the commit does not descend from the slot baseline, differs from the branch
     or the report, or the report lists blockers or a check that did not pass;
   - it changes a coordinator-owned file, or a protected file (manifest, lock file,
     schema, migration or CI file) its task did not declare for serial work. Files
     outside `Touches:` and files another slot changed are not held: the merge into the
     base, in priority order, settles them (TOOLSET-161-17);
   - the merge conflicts (aborted; the canonical checkout, its uncommitted files and
     the worker branch stay untouched);
   - validation fails, or the task contract or canonical branch changes meanwhile;
   - (not a hold) another live agent session would be affected: the result is `BUSY`
     and the commit stays reported until that session leaves. Integrating outside
     the main checkout (a runner's session worktree), a session in the main checkout
     counts only when the merge changes a file it holds open for writing or has left
     uncommitted there.

   Validation runs in the engine's own journaled integration worktree. If it leaves
   changes there, the next integration saves them to
   `autowork-execution/integration-residue/*.patch` and resets that worktree only.
5. **Close.** `--parallel-close TASK` refuses unless the slot is `integrated` with a
   passing validation receipt and its TODO contract still matches the validated
   one. It marks the task done, runs the Docs Sync archive (with goals.json this
   archives every verified completed body, not only TASK) and removes the current
   attempt's worktree and branch if they are clean (`cleaned`). When the report
   listed `pending_live`, close also adds `TASK-LIVE` under Needs decision (in
   goals.json too), depending on TASK and listing those checks, exactly once:
   offline completion never qualifies live behavior. Result: `CLOSED`, with
   `live_followup` when one was added and `files`, the exact paths it wrote,
   for the coordinator's commit.
6. **Commit coordinator files.** Close edits TODO.md, the archive and goals.json in
   the canonical checkout without committing. Commit them, plus the CHANGELOG line
   from the report if it is accurate, as one coordinator metadata commit.
7. **Refill.** Call `--apply --parallel [N]` again: freed slots take the next
   eligible tasks, and a task that depended on a closed one becomes eligible.
   Before releasing, integrate or close every `reported` and `integrated` slot,
   handle `held` ones, and check `waiting`. Release with `--parallel --release`
   only after the pool drains: it ends the coordinator lease, not the workers, and
   a sequential Autowork claim does not wait for surviving workers.

`--parallel-status [--json]` is read-only at any point and needs no owner: workers
active out of the maximum, one row per task (state, slot, elapsed, blocked reason and
`blocked_by`: the task IDs or outside condition holding it), `roots` (where each waiting
chain ends: `held`, `claim`, `contract` (a TODO entry the engine will not run, with its
reason), `outside`, `cycle`, or moving work, with how many tasks it holds),
completed/failed/integration-queue counts, and journal metrics (wall, worker,
integration and waiting time, peak workers, conflicts, retries).

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

## Admission: Touches and Resources

`Touches:` schedules work; it never holds it (TOOLSET-161-17):

- `Touches:` is a comma-separated list of repository-relative paths or globs the
  task is expected to change; `*` also matches across `/`, and a trailing `/` covers a
  directory. It is a hint: tasks whose `Touches:` overlap running or earlier-chosen work
  are dispatched after independent tasks, never held. A worker may change whatever else
  its task needs; the merge into the base, one candidate at a time in priority order,
  settles overlap, and a real conflict goes to the merge resolver. A missing or invalid
  `Touches:` is no hint (the task ranks after hinted ones).
- `Resources: live` or `Resources: exclusive` makes a task run alone. Other names
  (for example `Resources: port-8080, test-db`) keep tasks that share a name from
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
- Dependencies and TODO.md priority still apply: a task waits for its
  prerequisites to close. `Dependencies:` counts task-ID-shaped tokens and known task IDs; surrounding
  prose is ignored, a first clause starting with `none` means none, and a line naming
  no task at all stays an unresolved outside condition. A lower-priority task starts past a higher-priority one
  that cannot start yet only when it shares no resource or dependency with it. A task
  that must run alone (a `live`/`exclusive` resource) and waits on running work stops all lower-priority
  dispatch so the pool drains for it, once it has waited that way for
  `PI_AUTOWORK_DRAIN_AFTER` seconds (default 1800, counted from the journal); until then
  independent work backfills and it reserves only what it declares. A serial task never drains.
- Slots that are `reported`, `integrated`, `held` or `interrupted` block only their
  dependents and shared resources until closed. A `held` or `interrupted` slot whose task is now done
  or superseded (in goals.json, or checked off in TODO.md or its archive) blocks
  nothing; its worktree and record stay for inspection. An `in_progress` task with no live slot is a claim:
  it is never dispatched and blocks its dependents and tasks whose `Resources:` overlap
  it (the coordinator holds the repository lease, so no sequential Autowork run is
  executing it). With `--adopt-idle-claims SECONDS` a claim idle that
  long is planned like an open task: no change to its TODO/ledger entry, no commit on
  a branch named for it, no file change in such a worktree and no live agent there,
  and no active agent session in the canonical checkout holding open a file inside
  the task's `Touches:` (a task without `Touches:` waits for every active session
  there, its files being unknown; idle sessions never count).
  A claim a note holds is never adopted: its own entry, or any TODO.md line naming
  it (table rows aside), says to keep it open or in progress, forbids dispatch
  ("do not dispatch", "no worker dispatched"), puts it on hold, or says it requires
  or is missing an authority, authorization, approval or owner decision.
  The worker's prompt names the earlier branches and worktrees to reuse; they are never
  modified. The journal records `claim_adopted` with that evidence and the dispatch
  result lists `adopted`. Only live workers count toward N.

The root files `TODO.md`, `TODO.archive.md`, `goals.json` and `CHANGELOG.md` are
coordinator-owned: workers never edit them, and integration holds a commit that does.

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
  after a hold, and integration repeats every check, judging scope by the `Touches:`
  the worker was dispatched with (from its prompt), not by Touches recorded later. A second failure stays held:
  send it to Plan For Me to fix or skip. Until then it blocks only its dependents:
  it reruns fresh from the code of that time, never merges as is, so overlapping
  work proceeds. A worker-reported blocker holds the same way at once. Closing a
  retried task leaves the first attempt's worktree and branch for manual cleanup.
- **Hold causes:** every held slot records a machine-readable `cause`: `scope` (with
  `outside`, the coordinator-owned or undeclared protected files), `report`, `conflict`,
  `validation`, `contract_changed`, `moved`, `blocker`, `crash` (died twice) or
  `launch`. Integration's `HELD` result carries `cause` and `outside` too.
- **Holds from before TOOLSET-161-17:** a commit held for `overlap`, or for `scope` on
  files that are neither protected nor the coordinator's, is offered again once
  (`REOFFERED`) in priority order and integrates by merge; a worker held with
  `scope_request` (it stopped to ask for files) resumes in its worktree (`RESUMED`).
- **Reverify:** `--integrate ... --reviewer-version V` records which validation held a
  commit (`reviewed_by`). `--parallel-reverify TASK --reviewer-version V` sends a commit held
  by validation back to `reported` once per version V, and only when V differs from the
  one that held it (a hold without the record counts as an older one). The attempt is
  unchanged and integration repeats every check; a coordinator passes a fingerprint of
  its reviewer so a corrected reviewer re-examines what the old one held.
- **Answers re-queue:** each attempt records the contract it was dispatched with
  (`contract.txt`). When a held task's TODO entry no longer matches it (the owner
  answered by editing the entry), the next refill retires the slot as a set-aside
  does and returns `REQUEUED`; the task then dispatches fresh. An entry that was
  removed is retired with `requeued: false`. An unchanged entry stays held. A new
  coordinator claims the lease before these checks, so a one-shot run sees them.
- **Set aside:** `--parallel-set-aside TASK` retires a held slot with no attempt
  left, or an integrated one whose TODO entry was rewritten after validation (its
  merge stays in the main branch; the new entry is new work). Every attempt's
  worktree and branch is kept, renamed with `-set-aside-N`, and the slot record and
  data move to `slot-history/TASK/N`; the next refill dispatches the task fresh.
- **Earlier task work:** [the worker prompt](../scripts/parallel_dispatch.py) lists
  this task's local `autowork/<TASK>-set-aside-N` branches (including retired `-r2`
  attempts) and previous attempt branches, excluding the current branch. Each has
  its tip commit, commit date and changed files, newest tip first. Changed files
  are measured from the merge-base of that tip and the new attempt's baseline.
  All refs are reachable from the worker's worktree without fetching. Only when
  the current task asks to keep or continue earlier work may the worker merge or
  cherry-pick from those tips; otherwise it must ignore them. Nothing is applied
  automatically. Inspect the diff and bring in only paths the current entry's
  `Touches:` allow, never coordinator-owned or unreserved protected files; a
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
- **Name collisions:** a worktree is adopted only when the journal shows Autowork
  created it. A user branch or folder with the target name is left untouched and
  dispatch returns `ACTION_REQUIRED` until it is resolved by hand.
- **Resources:** a worker starts only while MemAvailable is at least twice
  `--min-free-mem-mb` (default 1500): one worker's budget plus as much spare, however
  many already run, since their memory is already out of MemAvailable. The 1-minute
  load average must also be below the CPU count. pi-autowork removes stale agent
  scratch from a RAM-backed `/tmp` (`PI_AUTOWORK_TMP_STALE`) so it cannot hold this.
- **Authority** is unchanged: workers inherit no publication, push or deployment
  authority, and the canonical checkout is only ever fast-forwarded.

Offline tests use deterministic fake workers; they do not qualify real model
workers or measure their speedup.
