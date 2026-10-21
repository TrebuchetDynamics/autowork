# Offline gate repair at 868ae564

## Accepted repair

Status: Accepted

Authority: the DOCS-MAINTAINER request explicitly requires one first-in-Now repair
task for the three failing tests in the saved main evidence. This is a new bounded
regression repair under the existing reliability goal, not permission to restore
the queue the owner deleted in `0cc75087`. Historical passing harvest evidence is
unchanged; this new repair remains open until its own checks pass.

### Evidence

Read in place, without copying runtime artifacts into Git:

`<git-common-dir>/autowork-execution/main-evidence/868ae56442381e511bb83532883b2c9be466f9f5/`

Resolve `<git-common-dir>` with `git rev-parse --path-format=absolute --git-common-dir`
from this repository, including linked worktrees. This portable
reference identifies the same original bundle without publishing a private home
path.

- `main_check.json`: state `red`, checked revision
  `868ae56442381e511bb83532883b2c9be466f9f5`, last green
  `616cb7f335056db1a7a31e281d22c80d3e418d62`, red since
  `5729fd496cdf71d9eff5dda58eaacb6b4d0c9db0`, no current flaky tests.
- `main-check.exit`: 1. `main-check.log` ends with three test directories passed,
  two failed, four modules excluded. The check reached test results; it did not
  crash before tests.
- `main-check-reruns.log`: each of the three tests below failed when run alone
  with `python3 -m unittest <test>` from its owning directory, using the absolute
  interpreter path recorded in the bundle.
  These are retained results, not checks performed by this documentation pass.
- `flaky_history.json`: none of these three tests has a recorded isolated-pass
  history. Historical flakes in unrelated tests do not qualify these failures.

| Failing test | Full-run and isolated result |
| --- | --- |
| `test_project_status.ProjectStatusTests.test_live_qualification_stays_open_and_separate` | `KeyError: 'TOOLSET-003'` |
| `test_project_status.ProjectStatusTests.test_reviewed_delivery_is_current_not_pending` | `KeyError: 'TOOLSET-002'` and `KeyError: 'TOOLSET-012'` |
| `test_task_execution.RecoveryTests.test_runner_jobs_do_not_block_integration_but_outside_scratch_sessions_do` | marker case expects `(session:` but gets the file-specific `fixture.py` uncommitted-change refusal; cgroup case raises `ValueError: integrate the highest-priority reported task first: None` |

Commits reported since last green (not a claim that each caused a failure):

- `868ae564`: stalled plugin fetch timeout and retry; changes `update_bundle.py`
  and `tests/test_update_bundle.py`.
- `0cc75087`: owner-directed removal of every open task and unfinished goal;
  changes `TODO.md` and `goals.json`, retaining completed bodies in the archive.
- `5729fd49`: uncommitted landing refusals name files instead of every session;
  changes `skills/autowork/scripts/parallel_integrate.py`, its regression tests,
  `pi-autowork/pi_autowork/coordinator.py` and `CHANGELOG.md`.
- `09d65eaa`: merge main into the runner session.
- `6ab2c115`: order overlap-held tasks behind their existing writers;
  changes `TODO.md` and `goals.json` before the reset.
- `892d4311`: question/blocker count relationship; changes fleet-view/TUI code,
  fleet-view tests and changelog.
- `e92b490f`: retain drain clock across wait reasons; changes parallel-dispatch
  code, its tests and changelog.

### Repair contract

Start with the named focused tests and inspect the current source. Reconcile
`tests/test_project_status.py` with the explicit queue reset: preserve assertions
that historical reviewed delivery is historical and that unperformed live checks
are not passing evidence, without requiring deleted tasks to remain executable.
Correct stale current-task claims in `docs/project.md` without erasing historical
results or implying that deleted qualification work passed.

Reconcile the integration fixture with the file-specific refusal introduced in
`5729fd49`. Keep coverage that conflicting outside sessions are refused, while
same-repository runner marker/cgroup jobs do not falsely block integration. Check
fixture cleanup and the cgroup follow-on error independently; the logs do not
prove that the latter is a separate product defect. Repair a local implementation
defect only if the focused regression demonstrates it. Do not weaken actual writer
protection or restore session-list wording merely to satisfy a stale assertion.

Acceptance: all three named regressions and `python3 scripts/check.py` pass;
regressions retain the queue-reset, historical-versus-live evidence and real
outside-writer protections above. No production/model/Telegram execution, new
credentials, restored deleted tasks, or fabricated live acceptance is included.

Required checks (planned, not passing results):

```sh
python3 scripts/check.py tests/test_project_status.py skills/autowork/scripts/test_task_execution.py skills/autowork/scripts/test_parallel_integrate.py
python3 scripts/check.py
```

Keep the full-check failure evidence until the repair's exact candidate has passed
its required checks and review. This documentation pass schedules the repair only.
