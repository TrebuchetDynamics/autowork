+++
schema = 1
id = "TOOLSET-341-eb82856d"
title = "Shared test modules never make tasks wait for each other as hot files; they only rank"
short = "Test files are not hot files"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 3000
depends_on = []
touches = ["pi-autowork/engine/parallel_plan.py", "pi-autowork/engine/test_parallel_plan.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "parallel_plan.py makes a path named by HOT_TASKS (3) or more unfinished contracts a hot file, and two tasks naming it wait for each other ('waits for X (shares hot file ...)'). Nearly every engine task adds tests to tests/test_pi_autowork.py, so on 2026-10-21 five tasks (335-89, 334-f9, 337-e0, 338-82 and more) waited for 328-2e only for that file and the runner had 1 of 8 workers busy. Test modules (paths under tests/ or named test_*.py) receive appended test methods that merge cleanly or are resolved by the existing merge step and are re-checked by the full check, so treat them like cold files: they rank and never serialize. Production files keep today's hot-file rule. Declared serial paths and resources are unchanged."
acceptance = ["Offline test: three runnable tasks that share only tests/test_pi_autowork.py among their touches start together; three that share a production module still serialize as today", "A merge conflict confined to a test module is resolved by the existing merge step and the result is still checked before landing"]
checks = ["python3 scripts/check.py pi-autowork/engine/test_parallel_plan.py pi-autowork/engine/test_parallel_dispatch.py"]
exclusions = []
closure = "manual"
closure_actor = "owner's interactive session (supervisor)"
closure_timestamp = "2026-10-21T18:57:44.277388+00:00"
closure_reason = "implemented and landed outside the runner by the owner's session"
closure_evidence = "Landed in bfe49549: parallel_plan.test_module() keeps test modules (tests/, test_*.py, *_test.py) out of hot_files, so they rank only; production files keep the hot-file rule. Checks: pi-autowork/engine/test_parallel_plan.py (new test: three tasks sharing tests/test_pi_autowork.py start together, three sharing a production module still serialize), test_parallel_dispatch.py, test_parallel_plan_hot.py, test_maintainer.py, test_parallel_status.py all pass."
+++

