---
name: pending
description: "Use to see what is pending or done in a repository's task ledger, read-only."
license: MIT
metadata:
  version: 0.1.0
  hermes:
    tags: [tasks, pending, done, query, read-only]
---

# Pending

Answer "what is left, what is next, what was done" from the repository's own task
records without changing them. Run the bundled read-only query helper and report its
outcome in the user's language, leading with what matters and keeping task IDs:

```sh
python3 scripts/task_query.py pending                       # open work, next eligible first
python3 scripts/task_query.py detail --id <TASK-ID>         # one task with its sources
python3 scripts/task_query.py search --text <words>         # open and closed tasks matching
python3 scripts/task_query.py history --since <date>        # what was closed, with dates
```

The helper writes nothing, runs nothing and claims nothing it cannot read from
`TODO.md`, `goals.json`, the archive and Git history. Its eligibility is recorded
dependency and priority evidence, not worker admission or liveness. The full
contract, including `--repo`, time zones and limits, is in
[the query contract](references/query-contract.md).
