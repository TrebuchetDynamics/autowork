# Verification and compatibility

## Verify

```sh
uv run --no-project --with-requirements requirements-test.txt python scripts/check.py
python3 scripts/check.py --list
python -m py_compile __init__.py bundle.py install-omh.py install-graphify.py
```

The checker runs top-level and maintained bundled workflow tests in separate
Python processes, with a 180-second timeout per directory. `--list` prints the
inventory without importing tests. Model, installed native backend and optional
integration suites are explicitly excluded with reasons; live opt-in flags are
removed from test subprocesses. Passing this gate does not qualify model/native
execution. Tests use temporary Git fixtures and may write offline scratch receipts.

`tests/integration_plugin.py` additionally checks the actual Hermes manifest
reader, native install security scan, loader, bundled skill reader, Telegram menu, CLI queue, gateway routing,
and unload behavior. Run it using Hermes' Python environment with the Hermes
source root on `PYTHONPATH`. It uses a temporary profile and a capture callback
instead of sending Telegram messages or calling a model.

`tests/integration_bundle.py` checks an existing isolated `HERMES_HOME`: all
loaded skill content, CLI queues and captured gateway routing for every generated
alias, plus the expected-import inventory. Run it with the same Hermes Python
environment and source `PYTHONPATH`. It exits nonzero for missing or blocked
imports. Native command registration is inspected; upstream actions, external
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

The offline suite runs in GitHub Actions. Live Telegram delivery and model
execution require your configured Hermes installation.

## Compatibility

Verified locally on October 11, 2026; this is a tested baseline, not a discovered
minimum-version guarantee:

| Layer | Evidence / boundary |
| --- | --- |
| Host | Ubuntu 24.04.4, x86_64 |
| Hermes | `v0.21.6+556.g6a2662a`, source `6a2662a4aaad68e1b75f6e7ac789409aa653abf7` |
| Native integration interpreter | Hermes-managed Python 3.14.7 |
| Offline tests | Python 3.12; audit tests also require PyYAML |
| CI declaration | Ubuntu runner and Python 3.12 in [.github/workflows/test.yml](../.github/workflows/test.yml); a declaration is not a current passing CI result |
| Required Hermes APIs | `register_skill`, `register_command`, origin-aware `inject_message`, profile-scoped loader and native gateway control socket |
| Other Hermes revisions / macOS / Windows | Not qualified by these receipts; shell setup requires Bash |

The manifest does not currently enforce `requires_hermes`. Do not interpret
“current Hermes” as compatibility evidence. Check `hermes --version`, then use the
native integration tests against that interpreter. There is no supported claim
that an earlier version has all required APIs.

`tests/integration_autoresearch.py` checks all research aliases, CLI queues,
Telegram menu entries and captured gateway origin routing. Like the main plugin
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
