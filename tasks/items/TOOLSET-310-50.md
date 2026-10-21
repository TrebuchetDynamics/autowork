+++
schema = 1
id = "TOOLSET-310-50"
title = "Extend autowork scorecard into the evaluation report"
short = "Evaluation scorecard"
status = "open"
goal = "EVALUATION"
section = "Next"
rank = 7000
depends_on = ["TOOLSET-307-5a", "TOOLSET-309-05", "TOOLSET-308-f9"]
touches = ["pi-autowork/pi_autowork/scorecard.py", "pi-autowork/pi_autowork/command.py", "pi-autowork/tests/", "pi-autowork/README.md", "docs/evaluation.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "autowork scorecard reports, per runner and overall, over --days up to 30 with a weekly breakdown: verified tasks per day, unattended completion percentage, median and p95 lifecycle duration (accepted to delivered, dispatch to integrated), cost per verified task, owner minutes per verified task, recovery success rate, regression rate, and the change in each from the first week to the last. Export --json and --csv. Every value is labelled measured, estimate or missing; an optional --baseline FILE (owner-supplied minutes and cost per task) is reported as an estimate beside the measured values. Retries never double-count completions or cost."
acceptance = ["On fixture data spanning 30 days, --json and --csv carry the same values per metric and week, each labelled measured, estimate or missing.", "A window with no verified task reports rates as missing, not 0; a task retried twice counts once as verified, with every attempt's cost.", "--baseline compares measured cost and owner minutes per task with the file's values, labelled estimate; without it the comparison reads 'no baseline'.", "Manual closures are reported separately and excluded from verified tasks and the unattended completion rate; each counts as an owner intervention."]
checks = ["python3 -m unittest discover -s pi-autowork/tests", "python3 scripts/check.py"]
exclusions = ["No dashboard or web view; no new dependency."]
+++

- Sources: [30-day evaluation](docs/evaluation.md#30-day-evaluation)
