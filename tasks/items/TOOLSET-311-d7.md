+++
schema = 1
id = "TOOLSET-311-d7"
title = "Collect 30 days of evaluation data on at least two other repositories"
short = "30-day evaluation run"
status = "done"
goal = "EVALUATION"
section = "Needs decision"
rank = 2000
depends_on = ["TOOLSET-310-50"]
touches = ["docs/evaluation.md"]
resources = ["live"]
kind = "implementation"
ownership = "owner"
scope = "Run Autowork for 30 days, mostly building other products, on at least two repositories other than this toolset, preferably on different stacks, with controlled permissions: no production credentials, and only repositories where an automatic push is acceptable. Choose the baseline (for example a week of supervised single-agent sessions on similar tasks) and record it as the --baseline file. Keep weekly autowork scorecard exports private, then record the aggregate verdict against each proposed target in docs/evaluation.md before any major new architectural change."
acceptance = ["docs/evaluation.md records aggregate weekly results per metric for at least two repositories, the baseline used and a verdict against each proposed target, including targets missed."]
checks = ["Live: autowork scorecard --days 30 --json on each evaluated runner, exported weekly"]
exclusions = ["No repository names, paths, identities or raw usage records in this public repository: aggregates only.", "Offline fixture results do not count."]
closure = "manual"
closure_actor = "xel"
closure_timestamp = "2026-10-22T11:50:02.883173+00:00"
closure_reason = "2026-10-22 owner decision: manually closed this live-only qualification to clear the pending queue. Offline acceptance remains; live evidence was not produced and is not claimed. Reopen when an authorized live environment and operator window are available."
+++

- Sources: [30-day evaluation](docs/evaluation.md#30-day-evaluation)
- Owner decision: 2026-10-21: Owner deferred the shared 30-day live evaluation on at least two other repositories. Keep the baseline, controlled-permission, privacy, weekly evidence and aggregate-verdict requirements; no completion or qualification is claimed. Do not create jobs, start runners, widen push authority or change existing pauses. Reuse this same decision for TOOLSET-311-d7 and TOOLSET-310-50-LIVE rather than asking twice.
