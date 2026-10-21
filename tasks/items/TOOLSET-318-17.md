+++
schema = 1
id = "TOOLSET-318-17"
title = "Report what still reads TODO.md before a conversion"
short = "Warn of TODO.md consumers"
status = "open"
goal = "TASK-STORE"
section = "Next"
rank = 14000
depends_on = []
touches = ["pi-autowork/pi_autowork/task_migrate.py", "pi-autowork/pi_autowork/task_prepare.py", "tests/", "pi-autowork/task-store.md", "skills/docs-sync/", "adapters/skills/docs-sync/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: a repository converted cleanly, then its main went red, because its own make check and 14 of its tests read TODO.md, which the conversion removes. Before converting, autowork migrate --dry-run and tasks prepare --check list tracked files outside documentation that name TODO.md or goals.json (build files, CI workflows, hooks, source and tests), and the conversion refuses while any remain unless --accept-consumers is given; prepare reports them as diagnostics after a conversion. Documentation mentions are reported separately, not refused."
acceptance = ["On a fixture repository whose Makefile and one test read TODO.md, the dry run lists both, the conversion refuses naming them, and --accept-consumers converts and reports them.", "Markdown mentions of TODO.md are reported as documentation drift and never refuse."]
checks = ["python3 -m unittest discover -s tests -p test_task_*.py", "python3 scripts/check.py"]
exclusions = ["No edits to any consumer repository; the converter reports, it does not rewrite their code."]
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
