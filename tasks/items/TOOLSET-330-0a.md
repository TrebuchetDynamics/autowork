+++
schema = 1
id = "TOOLSET-330-0a"
title = "Task records end without a trailing blank line"
short = "No blank line at end of records"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 43000
depends_on = []
touches = ["pi-autowork/engine/parallel_integrate.py", "pi-autowork/engine/task_store.py", "pi-autowork/engine/test_parallel_e2e.py", "pi-autowork/engine/test_parallel_integrate.py", "pi-autowork/engine/test_task_execution.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/task-store.md", "tests/test_pi_autowork.py", "tests/test_task_commands.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "task_store.render(fields, '\\n') writes a blank line at the end of any record without notes (cmd_add, the engine's -LIVE follow-up). A repository whose pre-commit hook runs git diff --cached --check refused the engine's close commit for that reason (2026-10-21): the close stayed staged in the session, the task stayed open on main, and the runner stalled re-dispatching it with 'slot already exists'. Rendered records end with exactly one newline, and a close commit refused by a hook is reported with the hook's output instead of being logged as done."
acceptance = ["A record rendered with no notes, by add and by the -LIVE follow-up, ends with exactly one newline and passes git diff --check.", "On a fixture repository whose pre-commit hook rejects the close commit, the runner reports the hook's failure, keeps the task's slot integrated rather than closed, and does not re-dispatch it."]
checks = ["python3 -m unittest discover -s pi-autowork/engine -p test_task_store.py", "python3 scripts/check.py"]
exclusions = []
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Touches: narrowed from four whole directories to the nine files the reverted landing de46ee717c0ecaf6e68a92b8340cacbdd309432a changed, so this task no longer claims every path under pi-autowork/engine/, pi-autowork/pi_autowork/, tests/ and pi-autowork/tests/; a re-attempt extends them only with evidence.
- Reopened: optimistic landing reverted de46ee717c0ecaf6e68a92b8340cacbdd309432a in e9c23781, blaming test_pi_autowork.EngineTests.test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why on main at 9cb0dfa. That assertion predated every affected landing, was fixed separately in a215993d and passes on main, so it is not this task's defect and needs no work here (TOOLSET-353-9db87df7 and TOOLSET-327-02 were re-landed unchanged for the same reason in e5162924). Next attempt: re-land or re-verify the reverted commit above with this contract and Acceptance unchanged.
