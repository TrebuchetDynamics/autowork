# Hermes Toolset

An opinionated toolkit for running repository work across Hermes profiles—from
questions and research to documented tasks, implementation, checks and commits.
Use the same workflows in CLI chat and Telegram without wiring each skill or
profile by hand.

Hermes already supports skills and plugins. This bundle adds a coordinated set of
repository workflows, automatic slash-command registration, shared installation
across profiles, and verification that gateway commands were registered.

## What you can do

| Workflow | Example in CLI chat | Result and possible changes |
| --- | --- | --- |
| Clarify a project | `/repo-interview Design a caching layer` | Asks focused questions and records decisions in existing docs. Use `questions only` to avoid writes. |
| Challenge a plan | `/grill-me Review this cache design` | Questions assumptions before implementation. |
| Maintain docs and tasks | `/repo-docs Record the accepted cache design` | Updates docs and organizes accepted work into tasks with acceptance criteria and dependencies. Does not start implementation. |
| Implement accepted work | `/autogoal Implement the accepted cache specification` | Selects eligible tasks, hands work to a worker, checks results and commits owned changes. Default invocation selects one task; no push/deploy implied. |
| Research and improve | `/autoresearch:plan Reduce cache latency` | Derives measurements and a plan; records accepted follow-ups through repo-docs. Other research commands can execute bounded experiments. |
| Continue approved work | `/lgtm` | Continues the agreed work without asking again; respects changes such as “no push.” |
| Deliver changes | `/git-commit-push only src/cache` | Validates, commits and pushes the specified work. Add `no push` for local commits. |
| Integrate upstream | `/git-pull-merge` | Runs the repository's pull/merge workflow. |
| Set up a profile | `/profile-create` | Guides profile creation and shared-toolset setup. |
| Inspect capabilities | `/toolset list` | Lists registered commands and their owners; `hermes toolset doctor --json` reports missing imports. |

Telegram uses underscores: `/repo_interview`, `/repo_docs`, `/git_commit_push`,
`/autoresearch_plan`. Autoresearch retains all 13 subcommands plus `/autoresearch`.
See [commands and workflows](docs/workflows.md) for the full research command set.

## A typical workflow

```text
/repo-interview Design a caching layer for this repository
/autogoal Implement that accepted specification; commit locally, no push
```

The interview asks questions and uses repo-docs to save accepted decisions and
tasks automatically; a separate docs command is unnecessary. Once that design is
accepted, autogoal implements it and reports task outcomes and delivery status.
A blocked dependency stays blocked; a passing build alone does not complete a task.
Documentation-only requests do not start implementation or recurring jobs.

Illustrative result after an authorized task completes—not a test receipt:

```text
CACHE — COMPLETED; 1 TODO task completed
Task: TODO.md CACHE-01 — Add bounded cache storage.
Changed: cache implementation, tests and docs/cache.md.
Checks: cache acceptance tests passed; required review passed.
Next: CACHE-02 — Verify eviction behavior [eligible, not started].
Delivery: local commit <SHA>; not pushed, as requested.
```

## Read before installing

**The defaults are designed for an autonomous fleet, not a policy-neutral command bridge.**

- Full setup targets **every existing live profile**. There is no general
  `--profile` selector; `--hermes-home` selects a Hermes installation root.
- Loading the plugin sets `approvals.mode: off`, disables destructive slash-command
  and MCP-reload confirmations, and enables gateway injection in its owning profile.
  Explicit deny rules and Hermes hard blocks remain. Setup also clears disabled-skill lists.
- Full setup installs external integrations and selects **OMH memory with auto-safe
  capture** in separate profile stores. Conflicting providers/stores are refused.
- External imports are **not fully locked**. Some are pinned; others follow current
  upstream sources. Scans or missing dependencies can leave setup incomplete.
- There is **no automatic restoration of previous configuration** on uninstall.
  Back up profile configurations first; see [removal and recovery](docs/uninstall.md).

The runtime-policy opt-out prevents changes **during plugin loading only**.
Full setup still applies the bundle’s approval policy. There is currently no
policy-neutral full-installation mode. See [installation](docs/installation.md).
See [memory and retained data](docs/memory.md) before enabling memory capture.

## Installation choices

| Path | Scope | External integrations | Policy effects |
| --- | --- | --- | --- |
| `bash install.sh --bundle-only` | All existing live profiles | Skips external-source setup | Applies bundle defaults; not a single-profile or policy-neutral mode |
| `bash install.sh --yes-deps` | All existing live profiles | OMH, Ponytail, speech, Graphify, external skills | Applies defaults and OMH setup |
| Native Hermes plugin installation | Selected Hermes profile | Manifest declares OMH, Ponytail and speech dependencies | Plugin load applies runtime defaults and provisions missing bundled skills |

The standalone command registration code does not require a memory or speech
service to register commands. The published manifest describes the complete stack;
there is currently no separate minimal, policy-neutral package.

## Quickstart from source

Prerequisites: an existing Hermes installation with a configured model, Git,
Bash and Python 3.12 for setup/tests (Hermes uses its managed interpreter). Use the [verified compatibility record](docs/testing.md#compatibility)
to check your environment. Telegram also needs its normal Hermes bot configuration.

After reviewing the effects above and backing up configuration:

```sh
git clone https://github.com/TrebuchetDynamics/hermes-toolset.git
cd hermes-toolset
bash install.sh --bundle-only --dry-run
bash install.sh --bundle-only
```

This starts with the bundled workflows and skips external-source setup. Keep the
checkout: the installed plugin links to it. Profile `status` is `ready` or
`incomplete`. The separate `gateway` field reports `commands_reloaded`,
`not_running`, `deferred_by_request`, `unreachable` or `reload_incomplete`.

Run `hermes toolset doctor --json` in the terminal. After bundle-only setup it may
report missing external imports: command registration does not prove full workflow
readiness. Reopen CLI chat and try this first, conversation-only scenario:

```text
/toolset list
/repo-interview questions only: help me clarify a caching improvement; ask one question, then stop
```

Expected first success: the agent asks one relevant question and changes no files.
This uses the bundled interview skill and your configured model; it does not need
OMH, speech, Graphify or a worker. It is a live smoke check you perform, not a claim
that automated registration tests exercised the model. Resolve any missing skill
or model error before attempting implementation workflows.

For the full external stack, preview `bash install.sh --yes-deps --dry-run`, then
run `bash install.sh --yes-deps`. Full setup also needs `uv` unless OMH and Graphify
CLIs are already installed. Read the outcome: partial setup is not success.
Workflow dependencies can still be unavailable after a bundle-only installation.

## What verification proves

| Capability | Evidence |
| --- | --- |
| Skill discovery, installer behavior and workflow helpers | Offline automated tests |
| CLI registration, skill loading and gateway origin routing | Native Hermes integration tests with captured calls |
| Live gateway command refresh | Activation receipts checked during setup |
| Actual model behavior or live Telegram delivery | Not established by those checks; requires a configured live session |

`/toolset` reports registrations, not whether every service is connected.
Hermes `/toolsets` reports enabled tool groups, a different inventory.
[Testing and compatibility](docs/testing.md) explains checks, exclusions and limits.

## Documentation

- [Installation, profile scope and policy opt-out](docs/installation.md)
- [Commands, Autoresearch and the engineering workflow](docs/workflows.md)
- [Memory capture, inspection and existing stores](docs/memory.md)
- [Removal and recovery](docs/uninstall.md)
- [Dependencies, reproducibility and licensing](docs/dependencies.md)
- [Adding skills](docs/contributing.md) · [Testing and compatibility](docs/testing.md)

No repository-wide license is currently declared. Individual bundled components
retain their own licenses; those do not license the whole repository.
See [licensing status](docs/dependencies.md#licensing).
