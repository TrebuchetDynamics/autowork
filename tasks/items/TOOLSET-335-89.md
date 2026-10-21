+++
schema = 1
id = "TOOLSET-335-89"
title = "A merge never changes a task's status or closes it: conflict resolution keeps each record's status from a parent"
short = "Merges never invent task closures"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 1000
depends_on = []
touches = ["pi-autowork/pi_autowork/coordinator.py", "pi-autowork/engine/parallel_integrate.py", "tests/test_pi_autowork.py", "pi-autowork/engine/test_parallel_integrate.py", "pi-autowork/tests/test_task_reopen.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "On 2026-10-21 at 11:40 the runner's session merge conflicted in tasks/items/TOOLSET-333-34.md (an owner hold note on main and a DOCS-MAINTAINER dependency note in the session) and Pi resolved it (coordinator.py merge prompt, 'main moved and conflicts with this session ... asking Pi to resolve the merge'). The resulting merge commit 22c2effe set status = done although both parents had status = open, with no evidence, receipt or closing commit: an invented closure, which also stops the task from ever being selected. After any merge that touches tasks/ (session follow-main, worker-side conflict resolution, planning remerge), compare every task and goal record against both parents: status, Evidence notes and closure fields must equal one parent's value, and a contract field may differ only as one parent has it; otherwise reject the merge result (abort or redo it with the resolver told which records it may not change) and keep the pre-merge state. TOOLSET-333-34 itself is closed separately, with evidence, when its fix lands."
acceptance = ["Offline test: a resolver stub that sets status done on a task open in both parents makes the merge rejected, with the session and main unchanged and the reason logged naming the task", "A resolver result that keeps each record's status and evidence from a parent and combines notes from both lands as today", "The same guard covers the worker-side merge resolution and the planning remerge paths"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py pi-autowork/engine/test_parallel_integrate.py pi-autowork/tests/test_task_reopen.py"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-335-89.toml"
+++

