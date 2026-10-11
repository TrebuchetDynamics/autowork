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
| Maintain docs and tasks | `/repo-docs Record the accepted cache design` | Updates relevant docs and reconciles full TODO.md tasks with goals.json. Does not launch workers. |
| Implement accepted work | `/autogoal Implement the accepted cache specification` | Selects eligible tasks, hands work to a worker, checks results and commits owned changes. Default invocation selects one task; no push/deploy implied. |
| Research and improve | `/autoresearch:plan Reduce cache latency` | Derives measurements and a plan; records accepted follow-ups through repo-docs. Other research commands can execute bounded experiments. |
| Continue approved work | `/lgtm` | Resumes the understood next step, retaining prior authorization and later restrictions. |
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
/repo-docs Record our accepted design and order implementation tasks in TODO.md
/autogoal Implement that accepted specification; commit locally, no push
```

The interview establishes the decisions. Repo-docs turns accepted work into tasks
with dependencies and checks. Autogoal executes authorized work and reports the
current TODO task, actual outcome, next eligible task, and commit/push status.
A blocked dependency stays blocked; a passing build alone does not complete a task.
Documentation-only requests do not start implementation or recurring jobs.

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

The runtime-policy opt-out and exact configuration effects are documented in
[installation](docs/installation.md). It does not make full setup policy-neutral.
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
checkout: the installed plugin links to it. Setup reports each profile as ready,
stopped, deferred or incomplete and refreshes running gateway command handlers.
Reopen existing CLI chats to load the new commands. In chat, try:

```text
/toolset list
/repo-interview questions only: help me clarify a small repository improvement
```

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
