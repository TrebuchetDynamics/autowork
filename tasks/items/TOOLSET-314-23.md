+++
schema = 1
id = "TOOLSET-314-23"
title = "Pass task text to autowork tasks without shell quoting"
short = "Shell-safe task input"
status = "open"
goal = "TASK-STORE"
section = "Next"
rank = 10000
depends_on = []
touches = ["pi-autowork/pi_autowork/task_commands.py", "tests/", "skills/docs-sync/", "adapters/skills/", "skills/shared/TODO-WORKCENTER.md", "pi-autowork/task-store.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Agents write task prose into shell command lines, where backticks and $(...) run as commands (2026-10-21: a backtick span in a --scope argument started an unrequested headless /blockers session). autowork tasks add, field and goal accept their values as one JSON object from a file or stdin (for example --json FILE, or - for stdin), taken literally with no expansion; the docs-sync skill, its adapters and the shared task rules tell agents to use it for any prose containing quotes, backticks, $ or newlines."
acceptance = ["Scope, acceptance and notes containing backticks, $(...), $VAR, quotes and a newline round-trip byte for byte through --json from a file and from stdin, and no subprocess is started.", "A test runs the documented command form with a value that contains a backtick command and asserts the command never runs.", "skills/docs-sync/SKILL.md, adapters/skills/docs-sync/SKILL.md and skills/shared/TODO-WORKCENTER.md name the JSON input for prose."]
checks = ["python3 -m unittest discover -s tests -p test_task_*.py", "python3 scripts/check.py"]
exclusions = ["No shell execution added anywhere; the existing flags keep working."]
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
