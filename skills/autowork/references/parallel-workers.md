# Parallel workers

Opt-in mode in which one coordinator session runs several independent TODO tasks at
once, each in a headless host CLI worker in its own Git worktree, then integrates
the results one at a time. Without `--parallel`, `owner_cycle.py` behaves exactly as
before. Linux only (worker identity comes from `/proc`).

The coordinator is the current Autowork session. Workers implement one task and
commit once; they never select tasks, edit coordinator-owned files, merge, push or
close tasks. A worker's commit and `report.json` are evidence, not acceptance:
the coordinator reviews, integrates, validates and closes.

## Coordinator loop

All calls use `python3 <autowork>/scripts/owner_cycle.py REPO` with the
coordinator's verified `--owner-pid` (the same persistent session identity as
sequential Autowork). `--run` takes every argument after it, so put it last.

1. **Claim and dispatch.** `--apply --parallel [N]` claims the parallel coordinator
   lease, reconciles existing slots, plans the queue and starts up to N workers
   (default 2; at most 4 unless `--max-workers`, hard limit 8). Each worker gets
   worktree `<parent>/<repo>-autowork-<TASK>` on branch `autowork/<TASK>` at the
   current canonical HEAD, its own process group, `TMPDIR`, `AUTOWORK_SLOT` and a
   100-port range from `AUTOWORK_PORT_BASE`. Results: `DISPATCHED` (started slots,
   each with its worker command and log), `WAITING` (each held-back task with its
   reason), `RETRIED` (a held task's fresh attempt, below), `IDLE`,
   `SEQUENTIAL_FALLBACK`, or `BUSY`, `PRIORITY_DRIFT` and `ACTION_REQUIRED` as in
   sequential Autowork. `IDLE` only means no worker started and none is running.
2. **Wait.** `--wait --timeout S` blocks inside the helper until a worker exits or
   S seconds pass, so the coordinator spends no model turns polling. `CHANGED`
   lists the slots that moved; `TIMEOUT` means none did. A worker past
   `--worker-timeout` (default 3600 s, fixed when it started) has its process group
   stopped and its slot becomes `interrupted`.
3. **Review the report.** Read `report.json` at
   `<git-common-dir>/autowork-execution/slot-data/<TASK>/attempt-N/report.json`
   (commit, changed files, checks, blockers, proposed CHANGELOG line) and the
   commit itself. A report is a claim; integration verifies it.
4. **Integrate.** `--integrate TASK --timeout S --run ARGV...`, where TASK is the
   highest-priority `reported` task (otherwise `ACTION_REQUIRED`). It merges the
   worker commit with `--no-ff` in the detached integration worktree
   `<parent>/<repo>-autowork-integration`, runs the validation argv there under a
   bounded process tree, and fast-forwards the canonical checkout only if its HEAD
   has not moved (one re-merge on a moved HEAD, then hold). Result: `INTEGRATED`,
   or `HELD` with a reason when:
   - the commit does not descend from the slot baseline, differs from the branch
     or the report, or the report lists blockers or a check that did not pass;
   - it changes a file outside the task's `Touches:`, a coordinator-owned file, or
     a file another slot changed;
   - the merge conflicts (aborted; the canonical checkout, its uncommitted files and
     the worker branch stay untouched);
   - validation fails, or the task contract or canonical branch changes meanwhile;
   - another live agent session is active in the canonical checkout.
5. **Close.** `--parallel-close TASK` refuses unless the slot is `integrated` with a
   passing validation receipt and its TODO contract still matches the validated
   one. It marks the task done, runs the Docs Sync archive (with goals.json this
   archives every verified completed body, not only TASK) and removes the current
   attempt's worktree and branch if they are clean (`cleaned`). Result: `CLOSED`.
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
active out of the maximum, one row per task (state, slot, elapsed, blocked reason),
completed/failed/integration-queue counts, and journal metrics (wall, worker,
integration and waiting time, peak workers, conflicts, retries).

## Admission: Touches and Resources

A task runs beside others only when the planner can prove it is independent:

- `Touches:` is a comma-separated list of repository-relative paths or globs the
  task may change; `*` also matches across `/`, and a trailing `/` covers a
  directory. Tasks whose `Touches:` intersect never run together, including for
  files that do not exist yet. An absolute path or a `.`/`..` segment makes
  dispatch return `ACTION_REQUIRED`.
- `Resources: live` or `Resources: exclusive` makes a task run alone. Other names
  (for example `Resources: port-8080, test-db`) keep tasks that share a name from
  running together.
- A task without `Touches:`, or one touching a serial path (dependency manifests
  and lock files, `migration(s)/` and `schema(s)/` directories, CI files such as
  `.github/workflows/`), runs alone.
- Dependencies and TODO.md priority still apply: a task waits for its
  prerequisites to close, and a higher-priority task that cannot start yet, or
  must run alone, stops lower-priority dispatch until it can run.
- Slots that are `reported`, `integrated`, `held` or `interrupted` keep blocking
  overlapping tasks until closed. An `in_progress` task with no live slot is a claim:
  it is never dispatched and blocks its dependents and tasks whose declared `Touches:`
  or `Resources:` overlap it, but its own missing `Touches:` does not hold back
  unrelated tasks (the coordinator holds the repository lease, so no sequential
  Autowork run is executing it). Only live workers count toward N.

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
  `--apply --parallel` after no worker is running gives one held task a fresh
  attempt alone (`RETRIED`) on `autowork/<TASK>-r2` in `<repo>-autowork-<TASK>-r2`
  from the current canonical HEAD, keeping the first branch; until the pool
  drains, refill returns `WAITING`. A second failure stays held: send it to Plan For
  Me to fix or skip. Closing a retried task leaves the first attempt's worktree
  and branch for manual cleanup.
- **Interrupted or released workers** (timed out, or dead with uncommitted changes
  or with nothing) restart once in the same worktree with a resume note; a second
  interruption is held. A failed first launch holds the task, which can still get
  the `-r2` attempt; a failed restart launch uses up its retry.
- **A restarted coordinator** reclaims the lease and reconciles the slot records
  under `<git-common-dir>/autowork-execution/slots/`: live workers are adopted; a
  dead worker with a commit becomes `reported` (keeping any uncommitted changes),
  one with only uncommitted changes `interrupted`, one with neither `released`, and
  one whose HEAD left the baseline `held`. No task gets a second worker.
- **Name collisions:** a worktree is adopted only when the journal shows Autowork
  created it. A user branch or folder with the target name is left untouched and
  dispatch returns `ACTION_REQUIRED` until it is resolved by hand.
- **Resources:** a worker starts only while MemAvailable is at least
  `--min-free-mem-mb` (default 1500) times running workers plus one, and the
  1-minute load average is below the CPU count.
- **Authority** is unchanged: workers inherit no publication, push or deployment
  authority, and the canonical checkout is only ever fast-forwarded.

Offline tests use deterministic fake workers; they do not qualify real model
workers or measure their speedup.
