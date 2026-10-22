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
