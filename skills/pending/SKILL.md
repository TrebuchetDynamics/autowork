---
name: pending
description: "Use to see what is pending or done in a task ledger."
license: MIT
metadata:
  version: 0.2.0
  hermes:
    tags: [tasks, pending, done, query, read-only]
---

# Pending

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Answer "what is left, what is next, what was done" from the repository's task store
(`tasks/`) without changing it. Use the read-only `autowork tasks` queries, which read
the store at a commit (HEAD by default), and report the outcome in the user's language,
leading with what matters and keeping task IDs:

```sh
autowork tasks list [repo]                 # every task: status, section, rank, next-eligible position
autowork tasks show <TASK-ID> [repo]       # one task: its contract, notes and record revision
autowork tasks why <TASK-ID> [repo]        # why it is or is not the next eligible task
git -C <repo> log --since=<date> --format='%ad %s' --date=short -- tasks/evidence/   # closes, dated
```

Open work is `status: open` in Now and Next, in `position` order; Needs decision items
wait for a person. A verified close has a receipt in `tasks/evidence/<ID>.toml`. The
queries write nothing and run nothing; eligibility is recorded dependency and priority
evidence, not worker admission or liveness. A repository without `tasks/` is not
converted yet: say so and name `/docs_sync` (its `autowork tasks prepare` converts it,
or defers to the runner while work is in flight); do not read TODO.md instead.
