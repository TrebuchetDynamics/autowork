+++
schema = 1
id = "TOOLSET-338-82"
title = "A batch check runs only the test modules its changes affect; main gets the full suite after landing"
short = "Affected-tests batch checks"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 29000
depends_on = ["TOOLSET-336-3c", "TOOLSET-335-89", "TOOLSET-334-f9", "TOOLSET-337-e0"]
touches = ["scripts/check.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/worker.py", "pi-autowork/pi_autowork/main_check.py", "pi-autowork/tests/test_main_check.py", "tests/test_pi_autowork.py", "tests/test_check.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Owner decision 2026-10-21: batch and landing checks are too slow (8-25 min). Select, for a batch's merged tree, the test modules its changed files can affect: a module is selected when it imports a changed Python module (transitively, within this repository) or names a changed path, plus every changed test module, plus a small always-run core (tree_guard, docs.py check, task-store validate). Run scripts/check.py on that selection (a new --affected BASE..HEAD mode that prints the selection and why each module is in it). Changes outside known code (scripts/check.py itself, SPLIT, CI or packaging files, shared fixtures, anything the map cannot resolve) select the full suite. After landing, the background main check runs the full suite as today; a failure there goes through the existing regression attribution (TOOLSET-308-f9) to the landed task and its repair task. Receipts record which selection was checked. A batch check that ran only the affected selection no longer stands in for the main check of its base (TOOLSET-336-3c records the base green from a passing batch check): only a batch check that ran the full suite records the base green; after an affected-only batch the base is checked in full on main as before, so main never reads green from a subset."
acceptance = ["check.py --affected prints the selected modules with the reason for each; a change to an unresolvable path selects the full suite", "A batch touching only pi-autowork/pi_autowork/fleet_view.py runs fleet_view's tests and their importers and not the whole suite (offline test on a fixture repository)", "Landing receipts name the selection; main's full check after landing still runs and a new failure there is attributed to the landed task as today", "An affected-only batch check that passes does not record its base green; the full main check of that base still runs, and a full-suite batch check still records it green (TOOLSET-336-3c)"]
checks = ["python3 scripts/check.py tests/test_check.py pi-autowork/tests/test_main_check.py tests/test_pi_autowork.py"]
exclusions = []
+++

- Owner decision: 2026-10-21 (owner): batch and landing checks run only the affected test modules; the full suite runs on main after landing, with regressions attributed to the landed task
- Dependencies: TOOLSET-336-3c, TOOLSET-335-89, TOOLSET-334-f9, TOOLSET-337-e0
- Scheduling: Overlap repair: retain TOOLSET-336-3c and its full-suite-only base-green rule; wait for TOOLSET-335-89 and then TOOLSET-334-f9 before changing their shared coordinator.py, worker.py and tests/test_pi_autowork.py paths. TOOLSET-334-f9 declared TOOLSET-337-e0 as a prerequisite but closed in be7f56d7 under optimistic landing before it, so no landed change owns scripts/check.py now; TOOLSET-337-e0 is open again after its revert and still reshapes scripts/check.py's SPLIT and tests/test_pi_autowork.py. This task therefore depends on it: both edit those two files and must not write them at the same time (337-e0 is earlier-ranked and its timing changes alter the same test module this task extends). Splitting off the affected-test selector would still collide with TOOLSET-337-e0 in scripts/check.py, not produce a runnable disjoint slice. Preserve the owner decision in 3d4efc9a and the affected-only/main-green reconciliation in d07af414, including every existing Acceptance item; no scope, Touches, Checks or queue-rank change.
