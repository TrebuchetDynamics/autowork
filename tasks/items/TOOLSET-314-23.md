+++
schema = 1
id = "TOOLSET-314-23"
title = "Pass task text to autowork tasks without shell quoting"
short = "Shell-safe task input"
status = "done"
goal = "TASK-STORE-HARDENING"
section = "Next"
rank = 38000
depends_on = ["TOOLSET-304-2c", "TOOLSET-305-7b"]
touches = ["pi-autowork/pi_autowork/task_commands.py", "tests/", "skills/docs-sync/", "adapters/skills/", "skills/shared/TODO-WORKCENTER.md", "pi-autowork/task-store.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Agents write task prose into shell command lines, where backticks and $(...) run as commands (2026-10-21: a backtick span in a --scope argument started an unrequested headless /blockers session). autowork tasks add, field and goal accept their values as one JSON object from a file or stdin (for example --json FILE, or - for stdin), taken literally with no expansion; the docs-sync skill, its adapters and the shared task rules tell agents to use it for any prose containing quotes, backticks, $ or newlines."
acceptance = ["Scope, acceptance and notes containing backticks, $(...), $VAR, quotes and a newline round-trip byte for byte through --json from a file and from stdin, and no subprocess is started.", "A test runs the documented command form with a value that contains a backtick command and asserts the command never runs.", "skills/docs-sync/SKILL.md, adapters/skills/docs-sync/SKILL.md and skills/shared/TODO-WORKCENTER.md name the JSON input for prose."]
checks = ["python3 -m unittest discover -s tests -p test_task_*.py", "python3 scripts/check.py"]
exclusions = ["No shell execution added anywhere; the existing flags keep working."]
closure = "manual"
closure_actor = "owner interactive session (Claude)"
closure_timestamp = "2026-10-22T10:17:00.304708+00:00"
closure_reason = "Re-landed in 9f6bf604 after a misattributed revert (main's red check was the stalled-service assertion fixed in a215993d)"
closure_evidence = "re-landed unchanged in 9f6bf604 as the inverse of its optimistic-landing revert; the blamed test predated it and was fixed in a215993d; its own review and batch check had passed before the revert"
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Coordination: Overlap repair: wait for TOOLSET-304-2c atomic writes in task_commands.py, then the earlier-ranked TOOLSET-305-7b closure CLI and skill changes. Task Store v2 uses this one CLI for add, field and goal; literal JSON input must be implemented there before its documented commands and round-trip tests can be verified. A docs-only split would depend on the same unfinished input contract, not run independently. Preserve all Acceptance and existing priority.
- Next action: 2026-10-21 blocker repair: preserve candidate eae7bd1917410f8e7c95da331fe73302ac2a8b9c and reuse its descendant 4d534ece41dbf7ce97b9151de557b0b73ec0b873 from autowork/TOOLSET-314-23. The one-file repair replaces obsolete newline/tab refusal assertions with exact field/body round-trip checks; CLI/store/writer/transaction modules pass (18,10,4,3 tests). Existing runner must adopt this repair in the same task rework and run the required integration gate/review, including the prior interruption-test failures. Do not reverify the unchanged old commit, reimplement JSON input, rewrite the old report or mark this delivered from the focused pass.
- Reopened: optimistic landing reverted b632bd586d3f4a1825beb2cbf0d5cf71298a0b3c in 6e1ed307, blaming test_pi_autowork.EngineTests.test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why on main at 9cb0dfa. That assertion predated every affected landing, was fixed separately in a215993d and passes on main, so it is not this task's defect and needs no work here (TOOLSET-353-9db87df7 and TOOLSET-327-02 were re-landed unchanged for the same reason in e5162924). Next attempt: re-land or re-verify the reverted commit above with this contract and Acceptance unchanged.
