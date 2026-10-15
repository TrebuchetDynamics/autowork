# Verification and compatibility

## Verify

```sh
uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py
python3 scripts/check.py --list
python -m py_compile __init__.py bundle.py install-omh.py install-graphify.py
node --test tests/portable_pi.test.mjs
```

The checker runs top-level and maintained bundled workflow tests in separate
Python processes, with a 600-second timeout per directory (the Autowork suite
alone takes about 150 seconds on an idle machine). `--list` prints the
inventory without importing tests. Model, installed native backend and optional
integration suites are explicitly excluded with reasons; live opt-in flags are
removed from test subprocesses. Passing this gate does not qualify model/native
execution. Tests use temporary Git fixtures and may write offline scratch receipts.

Autowork check receipts fingerprint the command executable using the check's
working directory and execution environment, including relative or empty `PATH`
entries. Receipts created before the `execution-cwd-v1` resolution policy cannot
be reused; preserve them and run the check with a new receipt path. An unresolved
executable also prevents reuse.

Current Autowork executes repository tasks in the current session without Kanban
setup or native-card transitions. Its direct-execution, recovery and isolated
no-agent qualification are described in the
[project verification contract](project.md#todo-first-delivery-qualification).
Model-driven recovery and useful-action timing remain the separate TOOLSET-003/013
checks; no-agent execution is not a substitute.

The following native-handoff coverage is historical/compatibility verification,
not a startup requirement for the distributed TODO-first path. Legacy native
Autowork handoffs snapshot their helper runtime and pin its manifest.
Offline regressions execute startup, completion and goal entry points from that
snapshot, change the original installation, and verify that changed bundled
dependencies refuse execution. Reconciliation tests cover terminal runs behind
`todo`/`ready` cards and repeated-blocker escalation. Registration drift tests keep
admission closed while distinguishing matching, missing, mismatched, ambiguous and
malformed current evidence. None of these checks releases an existing native claim
or migrates historical cards, installed profiles or saved schedules.

Backlog dependency validation parses each Dependencies field once and intersects
its tokens with the known task/goal IDs. It preserves exact word/hyphen boundaries,
including Unicode adjacency and explicit None declarations. Legacy goal IDs with
spaces or punctuation retain their original matching through precompiled patterns.
The selection-cost regression bounds regex operations rather than relying on a wall-clock timeout;
fresh source, contract, dependency, ordering and ownership checks still run.

Local Python 3.12 measurement on October 13, 2026: a 600-task selection fell from
10.080 seconds at `7df64e4` to 0.312 seconds (about 32× faster). A 100-task selection
fell from 0.034 to 0.026 seconds. Each result is the median of three unprofiled
`retry_selection.select` calls on a temporary Git fixture with open tasks, one
accepted plan, no dependencies and a cleared regex cache before each call. Both
versions selected the same first task. These measure the selection helper only,
not model execution, native dispatch or total cron duration.

Offline Autowork regressions cover missing-ledger recovery receipts, TODO/ledger
dependency and completion mismatches, and goal/task dependency deadlocks. A `met`
goal with unfinished tasks fails validation; `goals.py fmt` reopens it as `partial`
when executed passing evidence exists, preserving that evidence. Plan-status
recovery compares the complete heading subtree, including nested sections and
fenced examples, while preserving unrelated sibling sections.

`tests/integration_plugin.py` additionally checks the actual Hermes manifest
reader, native install security scan, loader, bundled skill reader, Telegram menu, CLI queue, gateway routing,
and unload behavior. Run it using Hermes' Python environment with the Hermes
source root on `PYTHONPATH`. It uses a temporary profile and a capture callback
instead of sending Telegram messages or calling a model.

`tests/integration_bundle.py` checks an existing isolated `HERMES_HOME`: all
loaded skill content, CLI queues and captured gateway routing for every generated
alias, plus the expected-import inventory. Run it with the same Hermes Python
environment and source `PYTHONPATH`. It exits nonzero for missing plugins, missing,
blocked or ambiguous skills, and skill sources not yet set up. Native command registration is inspected; upstream actions, external
services, and live Telegram delivery are not invoked.

From this repository's root, use the installed Hermes interpreter and source
checkout (adjust `HERMES_SOURCE` if Hermes is installed elsewhere):

```sh
HERMES_PYTHON="$(hermes --print-runtime-command --module runpy | python -c 'import json, sys; print(json.load(sys.stdin)[0])')"
HERMES_SOURCE="$HOME/.hermes/hermes-agent"
PYTHONPATH="$HERMES_SOURCE" "$HERMES_PYTHON" -c 'import hermes_bootstrap, runpy, sys; runpy.run_path(sys.argv[1], run_name="__main__")' tests/integration_plugin.py
```

For the full bundle check, first provide an existing isolated profile where the
bundle and its declared imports have already been installed. Do not point this
check at your live profile; plugin loading may write runtime records.

```sh
HERMES_HOME="/path/to/isolated-installed-profile" PYTHONPATH="$HERMES_SOURCE" "$HERMES_PYTHON" -c 'import hermes_bootstrap, runpy, sys; runpy.run_path(sys.argv[1], run_name="__main__")' tests/integration_bundle.py
```

The offline suite runs in GitHub Actions; CI byte-compiles only `__init__.py`, not
the four files above. Live Telegram delivery and model
execution require your configured Hermes installation.

## Compatibility

Verified locally on October 11, 2026; this is a tested baseline, not a discovered
minimum-version guarantee:

| Layer | Evidence / boundary |
| --- | --- |
| Host | Ubuntu 24.04.4, x86_64 |
| Hermes | `v0.21.6+556.g6a2662a`, source `6a2662a4aaad68e1b75f6e7ac789409aa653abf7` |
| Native integration interpreter | Hermes-managed Python 3.14.7 |
| Offline tests | Python 3.12; the suite also requires PyYAML (profile audit, portable package and Telegram menu tests) |
| CI declaration | Ubuntu runner and Python 3.12 in [.github/workflows/test.yml](../.github/workflows/test.yml); a declaration is not a current passing CI result |
| Required Hermes APIs | `register_skill`, `register_command`, origin-aware `inject_message`, profile-scoped loader and native gateway control socket |
| Other Hermes revisions / macOS / Windows | Not qualified by these receipts; shell setup requires Bash |

The manifest does not declare `requires_hermes`, although current Hermes loaders
enforce it when present. Do not interpret
“current Hermes” as compatibility evidence. Check `hermes --version`, then use the
native integration tests against that interpreter. There is no supported claim
that an earlier version has all required APIs.

`tests/integration_autoresearch.py` checks all research aliases, CLI queues,
the Telegram menu (current workflows advertised, Autoresearch compatibility aliases
not advertised) and captured gateway origin routing. Like the main plugin
integration test, it runs without a live model or message delivery.

## Core versus full-stack diagnostics

`python3 -m unittest discover -s tests -p test_doctor_modes.py` covers core success
with external gaps, strict full-stack failure, command ownership, missing skill
registration, plugin load failure and readable/JSON output. The native plugin
integration fixture additionally loads a real bundle-only profile and requires
core success plus full-stack failure from the same installed state.
These checks do not call a model or send a Telegram message. Use the separate
[operator-run onboarding checks](onboarding.md) for those outcomes.

## Installer preflight

`test_preflight.py` covers admission failure before any installer call, unchanged
profile snapshots, incomplete destination conflicts, source timeouts and the core
policy/memory preview. Run it with Hermes's managed Python as well to exercise
strict YAML rejection, memory conflicts and secret-safe errors (those parser
cases skip when ruamel.yaml is unavailable). `test_complete_setup.py` separately
checks orchestration after admission, including no installation calls on dry-run.
No passing preview is evidence of a live model or Telegram workflow.

## Update self-healing and Telegram menu checks

The implemented update/menu changes in `b021c54` have focused offline contracts:

```sh
python3 -m unittest discover -s tests -p test_telegram_menu_policy.py
python3 -m unittest discover -s tests -p test_setup_runtime.py
python3 -m unittest discover -s tests -p test_update_bundle.py
```

Menu fixtures check that only current workflow names receive priority, stale
compatibility entries are removed without deleting user choices, reconciliation
is idempotent, and typed compatibility registrations remain available with required
text hints. Finalization fixtures reject settings that remain unhealed after load.
Local-Git updater fixtures check `settings_healed`, one requested restart after
change, `not_running` for an absent gateway, no restart on an unchanged retry, and
`pending` with no second restart while a requested one is still draining.

These use temporary profiles and mocked activation/restart calls. Passing them
proves the local contracts, not that a real gateway drained, reconnected, refreshed
Telegram menus, delivered a message or executed a model. Inspect the actual update
receipt and activation/transport evidence before making those live claims.

## First-index initialization checks

From `skills/docs-sync/scripts`, run:

```sh
python3 -m unittest test_goals test_goal_concurrency test_handoff_reconciliation
python3 goals.py init --help
```

Initialization fixtures use real disposable Git consumers. They exercise empty
and TODO-only repositories, accepted-source and full-body binding, preserved
continuations/history/focus/ownership, byte-stable repeats, conflicting/incompatible
input refusal, unsafe paths, replacement failure rollback, concurrent locking,
stale revisions and linked-worktree canonical targeting. Consumer checks bind the
actual initialized repository, including a plan inside TODO; readiness is not a
live lease, model execution or Telegram delivery. Execute the
[documented initialization example](../skills/docs-sync/references/document-scaffold.md#first-task-index-initialization)
against a disposable consumer and run `fmt`, `validate`, `render`, then
`backlog-check` with its exact source and task IDs. `init` does not infer acceptance
or automatically render/archive bodies.

The safe root gate remains:

```sh
uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py
```

These offline helper checks do not qualify installed model behavior, native task
execution, publication or Telegram reporting. Keep those live gates separate.

## Archive and ownership regression checks

From `skills/docs-sync/scripts`, run:

```sh
python3 -m unittest test_todo_archive test_archive_policy test_render_safety
```

These fixtures exercise automatic/archive-only moves, whole-body preservation,
custom archive paths, CRLF bytes, stale-write refusal and unchanged second passes.
The source regression added in `586337f` keeps a sibling group heading in TODO
when the preceding done task is archived; deeper evidence subsections remain with
that task. This source contract does not prove an installed helper was refreshed.
They preserve open bodies and ledger history and reject ambiguous completion
metadata. The selected archive and the live TODO must both be inspected after
rendering; a passing fixture does not prove a real task's acceptance or model
follow-through. See the [archive contract](../skills/docs-sync/references/todo-archive.md).

From `skills/autowork/scripts`, run:

```sh
python3 -m unittest test_retry_selection
```

Ownership fixtures check partial claim updates, exact historical-workspace
resolution, retained metadata and rejection of conflicting identities. They do
not establish a live worker's availability or grant a new lease. At the repository
root, `python3 -m unittest discover -s tests -p test_owner_cron.py` checks prompt
generation, repair-mode opt-in and preserved job settings without scheduling or
executing a live repair.

## Portable package checks

Codex/Pi packaging and adapter-reference checks run in `tests/test_portable_package.py`.
The Pi Node tests cover command registration, literal arguments, queued messages
and packaged support files. CI uses Node 22 for those tests. See
[cross-host installation and verification](cross-host.md) for tested client versions
and disposable-home installation checks. Package discovery does not prove model
execution or completion of an Autowork task; the outstanding qualification is
tracked in [TODO.md](../TODO.md#toolset-003--qualify-automatic-planning-recovery-with-a-real-bounded-workflow).
