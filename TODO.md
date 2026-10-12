# Work queue

Central queue for Hermes Toolset. Scope and current architecture: [project contract](docs/project.md).
No task below is implemented by this documentation pass. There is no goals.json
execution index yet; native ledger admission must not be inferred from this queue.

## Now

### TOOLSET-001 — Align portable skill discovery with the current public workflows

- Status: open
- Goal: Consistent primary workflow names across Hermes, Codex and Pi.
- Sources: [public workflow mapping](docs/workflows.md), [portable adapters](adapters/skills/COMMON.md), [Pi registration](adapters/pi.mjs).
- Evidence: Hermes folds Grill Me into Plan With Me and publishes Plan For Me;
  the portable package still discovers separate Grill Me and Autoresearch skills.
- Scope: Align portable public discovery and challenge/research routing; update
  host-specific examples and registration tests. Preserve non-planning protocols
  and supported compatibility invocations.
- Exclusions: No Hermes Agent edits, permission changes or removal of user skills.
- Acceptance: Canonical skills are discoverable on each host; challenge mode and
  every research protocol resolve to valid instructions without recursive routing.
  Package references remain valid after installation.
- Checks: `python3 -m unittest discover -s tests -p test_portable_package.py`;
  `node --test tests/portable_pi.test.mjs`; native installation/discovery in temporary homes.
- Dependencies: None.
- Owner: Next authorized Autowork coordinator; no active claim recorded here.

## Next

### TOOLSET-002 — Provide a supported first-time task-index initialization path

- Status: open
- Goal: Let Docs Sync bootstrap a native-consumable backlog without manual JSON edits.
- Sources: [goals helper](skills/repo-docs/scripts/goals.py), [document scaffold](skills/repo-docs/references/document-scaffold.md), [project contract](docs/project.md).
- Evidence: The CLI documents command-only ledger mutation but exposes no init or
  add-goal command. This repository currently has TODO.md and no goals.json.
- Scope: Establish and document a supported bootstrap operation; preserve full task
  bodies and existing IDs, then validate/render a machine index for this queue.
- Exclusions: No invented accepted plans, completion evidence or overwrite of an
  existing ledger; do not launch workers as part of document initialization.
- Acceptance: Empty-repository bootstrap and an existing TODO-only repository have
  reproducible coverage; repeated initialization preserves bytes; existing/conflicting
  state is preserved; generated task/body links pass consumer checks.
- Checks: Extend goals-helper fixture tests; run `python3 scripts/check.py` and the
  supported validator/render idempotency checks on the generated queue.
- Dependencies: None.
- Owner: Next authorized Autowork coordinator; no active claim recorded here.

### TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow

- Status: open
- Goal: Prove that recovery reaches execution instead of stopping at a planning receipt.
- Sources: [recovery contract](skills/autowork/references/backlog-planning.md),
  [planning tests](skills/autowork/scripts/test_backlog_plan.py), [verification limits](docs/testing.md).
- Evidence: Offline tests cover preparation routing and receipt reuse; they do not
  prove a model calls Plan For Me, updates tasks and starts the supported worker.
- Scope: Use a disposable repository and an isolated configured test environment.
  Reproduce missing prerequisites and candidate drift; capture the actual planning,
  TODO update and handoff sequence, or record the specific failing transition.
- Exclusions: No production messaging, deployment, real user repositories, forbidden
  prerequisite commits, concurrent-writer takeover or manufactured completion.
- Acceptance: The workflow invokes planning without another user command, preserves
  no-commit exclusions, retries an eligible in-scope slice, and reports execution
  separately from planning. Unchanged inputs reuse the saved recovery decision.
- Checks: Offline regression suite plus an explicitly recorded model/native smoke
  run; exact task, checks, commit or none, and remaining blocker in its receipt.
- Dependencies: None; requires a configured isolated model/native environment.
- Owner: Next authorized Autowork coordinator; no active claim recorded here.

## Needs decision

None currently identified for the bounded tasks above. Unavailable live test access
must be reported when encountered; it is not evidence that a product task is done.
