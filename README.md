# Autowork

### Plan in Git. Build with agents. Verify each change.

Autowork connects your project's decisions, work queue and coding agents.
Plan together, save accepted tasks in `tasks/`, and execute the next eligible task
with checks and a clear delivery report.

**Use the workflows in Hermes, Claude Code, Codex or Pi.**
Start the Linux Pi runner separately when you want it to continue through the queue.

[Get started](#install) · [Choose a workflow](#what-you-can-do) ·
[Run continuously](#pi-autowork-pipeline) · [Safety](#read-before-installing) ·
[Evidence and limits](#what-verification-proves) · [Docs](#documentation)

| Your host | Install | Start planning |
| --- | --- | --- |
| **Hermes** | [Native plugin](#try-the-native-plugin-in-one-profile) | `/plan-with-me` |
| **Claude Code** | [Marketplace plugin](#claude-code) | `/autowork:plan-with-me` |
| **Codex** | [Marketplace plugin](#codex) | `$autowork:plan-with-me` |
| **Pi** | [Git package](#pi) | `/plan-with-me` |

For example, in **Hermes CLI** after installation (illustrative, not a run receipt):

```text
/plan-with-me questions only: help me clarify a caching improvement; ask one question, then stop
/autowork Implement the next ready task; commit locally, no push
```

<p align="center">
  <img src="assets/readme/workflow.svg" width="100%" alt="Plan accepted work, queue it in tasks/, execute an eligible task, and report checks and delivery. Further work requires the caller's authority; this diagram does not promise a background scheduler.">
</p>

**A skill invocation is not a background service.** Hermes profile management and
Hermes scheduler integration are native-only. Portable adapters use their host's
scheduling facilities and do not guarantee execution after a session ends.

---

## Why Autowork

**The plan, the queue and the result belong in the same repository.**

| You need to… | Autowork provides… |
| --- | --- |
| Turn an idea into accepted work | Guided planning, documented decisions and task records |
| Keep agents working from the same plan | A Git-versioned `tasks/` store with scope, dependencies and checks |
| Implement without losing the boundaries | Scope and resource gates, verification and separate delivery authority |
| Continue through the queue | Explicitly started runners with parallel workers and recovery controls |

Hermes, Claude Code, Codex and Pi share the planning, documentation and execution
skills. The Linux Pi runner adds a persistent execution loop. It admits independent
tasks in parallel, requires checked evidence before closure, and adopts live workers
after a restart instead of starting duplicates. An empty runner queue waits without
a model call. Only typed fields grant authority. Dependency, file-scope and resource
gates decide what runs in parallel.

Docs Sync keeps requirements and tasks in step. It can convert an old `TODO.md`
queue, prepare a new store from accepted plans, and report what needs repair.

How Autowork compares with established orchestrators is not yet benchmarked.
Sustained live reliability is not yet proven. See [project status](#project-status).

## Read before installing

These defaults apply to Hermes; the [Claude Code, Codex and Pi adapters](docs/cross-host.md)
keep their hosts' settings. **They are designed for an autonomous fleet, not a
policy-neutral command bridge.**

- Full setup targets **every existing live profile**. There is no general
  `--profile` selector; `--hermes-home` selects a Hermes installation root.
- Loading the plugin sets `approvals.mode: off`, disables destructive slash-command
  and MCP-reload confirmations, removes the per-turn iteration cap
  (`agent.max_turns: unlimited`) and enables gateway injection in its owning profile.
  Explicit deny rules and Hermes hard blocks remain. In profiles with OMH it disables the
  OMH skills outside a measured keep list (your own disabled skills stay).
- Full setup installs external integrations and selects **OMH memory with auto-safe
  capture** in separate profile stores. Conflicting stores are refused; another
  selected memory provider is left in place, and OMH memory stays off until you clear it.
- External imports are **not fully locked**. Some are pinned; others follow current
  upstream sources. Scans or missing dependencies can leave setup incomplete.
- There is **no automatic restoration of previous configuration** on uninstall.
  Back up profile configurations first; see [removal and recovery](docs/uninstall.md).
- With approvals off and unattended runners, **give agents no production
  credentials** and start with repositories where an automatic local commit and
  push is acceptable.

The runtime-policy opt-out prevents policy changes **during plugin loading and
setup**. Full setup still applies OMH memory defaults and external integrations;
there is currently no policy-neutral full-installation mode. See
[installation](docs/installation.md), and [memory and retained data](docs/memory.md)
before enabling memory capture.

## Install

Choose one host below and configure its model. Portable adapters need no
Hermes installation. For all available hosts at once, use the
[full-suite installer](#everything-at-once) after reviewing the warnings above.

### Try the native plugin in one profile

Default-profile commands below; add `-p work` after `hermes` for a named profile.
Advisory dependencies are not installed; missing ones warn rather than block loading.
Native security scanning still applies. A successful download is not scan approval;
CAUTION requires review and acceptance, and a dangerous verdict blocks installation.

**Keep your approval settings?** Before enabling, run
`hermes config set plugins.entries.autowork.settings.apply_runtime_defaults false`
([opt-out details](docs/installation.md#install)). Otherwise, accept the defaults with:

```sh
hermes plugins install TrebuchetDynamics/autowork
hermes plugins enable autowork
hermes autowork doctor --core
```

The opt-out does not undo prior changes or prevent full setup from configuring
memory and external integrations. Without it, loading applies the policy above.
Native install stays in one profile; full setup expands to **every live profile**.

### Claude Code

Install the marketplace and plugin:

```sh
claude plugin marketplace add TrebuchetDynamics/autowork
claude plugin install autowork@autowork
```

### Codex

Requires a CLI with plugin support:

```sh
codex plugin marketplace add TrebuchetDynamics/autowork --ref main
codex plugin add autowork@autowork-marketplace
```

### Pi

Requires Node 22 or later:

```sh
pi install git:github.com/TrebuchetDynamics/autowork
```

Restart your host session to discover the installed skills. See the
[cross-host guide](docs/cross-host.md) for reload commands, updates and removal.

## First use in your project

Open **your project**, not the Autowork checkout. Start your configured host there
(`hermes`, `claude`, `codex` or `pi`); keep `-p PROFILE` for a named Hermes profile.
Use the planning invocation in the host table at the top with this request:

```text
questions only: help me clarify a caching improvement; ask one question, then stop
```

For example, in **Hermes CLI**:

```text
/plan-with-me questions only: help me clarify a caching improvement; ask one question, then stop
```

Expected first success: one relevant question and no file changes. This is a live
smoke check **you perform**, not an outcome established by automated tests. Hermes'
`doctor --core` checks registrations, not a model or live messaging. Continue with the
[core-only interview](docs/onboarding.md#core-only-requirements-interview) or
[full-workflow exercise](docs/onboarding.md#optional-see-decisions-become-a-task).
See [onboarding](docs/onboarding.md) for Telegram and project binding; a profile is
not a filesystem sandbox.

<details>
<summary><strong>Install every available host and CLI component</strong></summary>

### Everything at once

From a checkout, `install.sh` installs every available component with verbose output:
the Pi package, the `autowork` command and TUI, the `tx` tmux launcher, the Hermes
plugin (every live profile), the Claude Code plugin and the Codex plugin, including
their complete portable skill suites. These include pinned Ponytail skills and an optional
read-only codebase-map script. Every Autowork skill applies the shared smallest-complete-change
method within its existing scope; no separate Ponytail plugin or startup hooks are installed.
A host whose CLI is missing is skipped and explained. Each item runs that host's own install
command, listed above; `tx` keeps an existing `~/.tmux.conf`.

```sh
git clone https://github.com/TrebuchetDynamics/autowork && cd autowork
./install.sh                    # full suite, live output and exact commands
./install.sh --menu             # arrows, Space toggles, Enter installs
./install.sh --dry-run          # preview the full suite without installing
./install.sh --only pi,autowork,tx --dry-run   # print what it would run
```

`--full` (`--all`) and `--verbose` (`-v`) are already the defaults.
Install steps stream output as they run,
with component/step progress, elapsed times and a final result for every component.
Use `--quiet` (`-q`) for summaries and
failure diagnostics (native output stays visible when input is a terminal).
Colors are automatic on terminals; `--color always|never|auto` overrides that
choice, and `NO_COLOR=1` disables automatic color.

The full suite targets hosts already on `PATH`; it does not bootstrap host CLIs.
Missing hosts are listed as skipped. An explicitly requested missing host, such as
`--only codex`, fails. Failed components return a nonzero status while independent
components continue. Preview mode installs nothing. Hermes still uses its complete
fleet setup and its normal dependency/security prompts; use `--yes-deps` only when
you intend to consent to its declared dependencies.


</details>

<details>
<summary><strong>Compare installation paths and profile scope</strong></summary>

| Path | Scope | External integrations | Policy effects |
| --- | --- | --- | --- |
| Native Hermes plugin | Selected profile | Advisory only | Runtime defaults unless opted out |
| `bash install-plugins.sh --bundle-only` | Every live profile | Skips external-source setup | Bundle defaults unless opted out |
| `bash install-plugins.sh --yes-deps` | Every live profile | OMH, speech, Graphify | Bundle defaults and OMH setup |

### Fleet setup from source

Requires Hermes with a configured model, Git, Bash and Python 3.12; external setup
also needs `uv` unless the OMH and Graphify CLIs are installed. After backing up
configuration and reviewing the policy above:

```sh
git clone https://github.com/TrebuchetDynamics/autowork.git
cd autowork
bash install-plugins.sh --bundle-only --dry-run
bash install-plugins.sh --bundle-only
```

Keep the checkout: the installed plugin links to it. This targets every live
profile, even from a named-profile invocation. Add external integrations later
with `bash install-plugins.sh --yes-deps`. **Hermes CLI startup can apply defaults even
with `--dry-run`;** the shell preview above does not boot Hermes. See
[preflight and activation details](docs/installation.md#preflight-before-fleet-writes).

</details>

## How it works

1. **Plan and queue.** Planning saves decisions to the docs and tasks to `tasks/`
   with `autowork tasks`; Docs Sync keeps the documents consistent and prepares the
   store (`autowork tasks prepare`) before it reconciles tasks. Planning alone
   never starts implementation or schedules work. `read-only`, `chat-only`,
   `no-write` and `--dry-run` requests write nothing.
2. **Execute and report.** Autowork prioritizes accepted runnable tasks, implements
   a useful slice, runs required checks and commits locally. It never pushes or
   deploys without explicit authorization. Another authorized invocation continues
   from the recorded state; a diagram or installed skill does not create a timer.

**When the queue is empty:** with broad repository-development authority, Autowork
may discover useful work, record a justified task **and implement it in the same
invocation**. With task-limited authority, it must stay in that scope. It does not
invent busywork or treat an empty queue as permission to expand its authority.

## What you can do

Examples use **Hermes CLI**. Portable workflows use the host-specific prefixes above.

### Plan and document

- **Plan together:** `/plan-with-me Design a caching layer` asks focused questions,
  then saves decisions and tasks. Add `questions only` to write nothing.
- **Challenge assumptions:** `/plan-with-me Challenge this cache design` tests the
  plan before implementation.
- **Delegate planning:** `/plan-for-me Reduce cache latency` investigates, chooses
  an approach and saves tasks; it does not implement. Bare `/plan-for-me` (or a
  vague direction such as *make it better*) first discovers the project's
  evidence-backed gaps, then saves the highest-value executable frontier without
  asking you for a goal. `read-only` saves nothing.
- **Answer blockers:** `/blockers [repo|runner]` (also `/autowork blockers`,
  `/plan-with-me blockers`) reconciles routine planning issues first, then asks
  only for missing owner decisions or inputs, easiest first. Resolutions become
  task-record edits for the runners; an idle reviewed candidate needs no new
  ownership choice when local integration is already authorized.
- **Keep the repository coherent:** `/docs-sync Record the accepted cache design`
  maintains docs and tasks with acceptance criteria and dependencies.

### Execute and deliver

- **Develop:** `/autowork Implement the accepted cache spec` executes and verifies
  one useful slice. No push or deployment is implied.
- **Run in parallel:** `/autowork --parallel 2` runs independent tasks in separate
  worker sessions and worktrees, then merges and checks them one at a time. It is
  opt-in; tasks declare the files they change so overlapping work never runs
  together. See [parallel workers](skills/autowork/references/parallel-workers.md).
- **Continue:** `/lgtm` proceeds with the agreed next step under existing limits,
  including `no push`.
- **Deliver:** `/git-commit-push only src/cache` validates, commits, pulls and merges
  upstream, then pushes. Add `no push` or `no pull` to narrow it.
- **Integrate only:** `/git-commit-push pull` or `merge <branch>` integrates without
  rebasing or discarding local work.

<details>
<summary><strong>Specialist skills: bug hunting, refactoring and test optimization</strong></summary>

### Hunt bugs and refactor

The [pi-toolset specialists](docs/cross-host.md#pi-toolset-specialists) are bundled
for all four hosts, with Ponytail guidance and Autowork's existing scope/review rules:

- `/bug-harvest one bug in the parser; no push` — discover and verify unknown defects.
- `/autonomous-codebase-improver one improvement; no push` — select an evidenced
  improvement across applicable work lanes, then implement and review it.
- `/skill-folder-refactor src/parser; one move-only slice` — reorganize one folder
  without mixing moves with behavioral changes.
- `/unused-code src/parser; read-only` — inspect liveness before proposing deletion.

The locally authored [Test Optimizer](docs/workflows.md#test-optimizer) adds
`/test-optimizer tests/parser; apply one batch; no push`: reduce duplicate tests,
repeated setup and unsupported scenarios while retaining distinct regression and
safety protection. Bare invocation audits; `read-only` writes nothing.

[APK Get](skills/apk-get/SKILL.md) adds `/apk-get [app-path]`: find an existing
Flutter or React Native Android app and build an ARM64-only release APK. It reports
the verified artifact path and signing status; it does not upload or install the APK.

These are current-session skills, not new services. Pi uses hyphens; Claude
Code and Codex use the same namespaced prefixes as other skills. No upstream
controllers, installers or global activation are imported.

</details>

<details>
<summary><strong>Hermes scheduling, profiles and command aliases</strong></summary>

### Operate

Hermes-only scheduler, profiles and fleet management:

- **Schedule:** `/cron-autowork every 30 minutes for this repo; no push` creates or
  updates a matching job and verifies it. **With a cadence, a paused job resumes.**
- **Set up a profile:** `/profile-create` guides repository-bound profile setup.
- **Update:** `/autowork update` updates every live profile; see [updating](#updating).
- **Inspect:** `/autowork list` lists registered commands and their owners.

| Interface | Plan | Docs Sync | Schedule |
| --- | --- | --- | --- |
| Hermes CLI | `/plan-with-me` | `/docs-sync` | `/cron-autowork 15m` |
| Hermes Telegram | `/plan_with_me` | `/docs_sync` | `/cron_autowork 15m` |

See [commands and workflows](docs/workflows.md) for the full reference, aliases and
[portable invocations](docs/cross-host.md). Supporting design skills and engineering
protocols load only when needed; registration is not proof a technique was applied.

</details>

## Pi Autowork pipeline

**Keep Pi working through the accepted queue, with parallel workers and checked integration.**
The Linux runner is separate from a one-shot skill invocation: you start it explicitly;
installing the Pi package does not start workers, a service or a Hermes cron job.

```text
tasks/ (one file per task and goal)
                 ↓
Dependency / scope / resource gates
                 ↓
Pi workers in isolated worktrees
                 ↓
Verify + integrate into session
                 ↓
main/master or Merge pending
```

- **Parallel where safe.** Independent tasks run together; overlapping file scopes,
  shared resources and dependencies constrain admission. An empty queue waits
  without a model call rather than inventing tasks.
- **Evidence before closure.** Worker commits and reports are claims. Project checks
  and, by default, a separate Pi review gate integration and task closure.
- **Local delivery is automatic; push is opt-in.** After each closed task the runner
  merges its session into `main`/`master` (Pi resolves a conflict with the owner's
  newer plan) and fast-forwards the main checkout. Main stays local unless an explicit
  `PI_AUTOWORK_PUSH=1` grant enables upstream publication: fast-forward only, never
  forced; a rejected push merges the upstream and tries once more. What cannot land
  is reported as `Merge pending` and shown as the runner's blocker; the session is
  retained. Workers never push. Saved per-repository grants are reused; existing
  saved on/off settings are preserved. See the [grant and status commands](pi-autowork/README.md#the-autowork-command).

The runner defaults to SDK-backed **Pi RPC** (Pi 1.4.0 / Python SDK 0.2.6).
The `autowork` installer component installs its isolated Python dependency; for a
manual Pi-package installation, first follow [RPC setup](docs/pi-rpc.md).
JSON is explicit temporary rollback, never an automatic replay path.

From your project's main-branch checkout, after the Pi installation and RPC setup:

```sh
# Preview only: no workers or repository changes.
~/.pi/agent/git/github.com/TrebuchetDynamics/autowork/scripts/pi-autowork.sh --dry-run
# Run until no task can start, with up to two workers.
~/.pi/agent/git/github.com/TrebuchetDynamics/autowork/scripts/pi-autowork.sh --until-empty --workers 2
```

Starting the second command makes model calls and local commits. Configure project
checks and cost/runtime limits before unattended use. See the
[runner guide](docs/cross-host.md#run-autowork-continuously) for Linux prerequisites,
continuous/service mode, model fallback, status, stop and recovery controls, and the
[Pi component](pi-autowork/README.md) for code ownership and migration status.

<details>
<summary><strong>Runner commands, TUI and service controls</strong></summary>

### Run and watch runners

Each repository's runner is a **systemd user service**, managed with the `autowork`
command. Bare `autowork` opens the live TUI: every runner with what it needs from
you (its open questions), its workers in flight, blockers and log, with keys to
start, stop, pause, restart and set the model; `d` browses directories and starts a
service for any repository with a `tasks/` store committed on its main branch.

```sh
autowork                      # the live TUI
autowork start                # this repository: install (if needed) and start its service
autowork ls                   # one colored line per runner; --long: workers, blockers, model
autowork status india          # tasks, workers and what blocks them
autowork pause india           # stop it and keep it off; autowork resume india starts it again
autowork model india openai-codex/gpt-6-luna   # per-service model, from: autowork models
autowork web                  # the TUI in a browser, http://127.0.0.1:8765
autowork blockers india        # answer what blocks the queue, picking options (/blockers)
autowork plan ~/git/project --interactive  # embedded planning/chat; explicit review/apply, no runner start
autowork scorecard            # per runner, last 7 days: closed, held share, start to merge, questions
```

A target is a runner name, a repository path or `.`. Workers pause and resume on
the same attempt whenever a runner stops. See the
[pi-autowork component](pi-autowork/README.md#the-autowork-command) for every command
and the [service setup](docs/cross-host.md#run-autowork-continuously) for logout
behavior and settings.

</details>

## Your work queue

`tasks/` holds accepted scope, task priority, checks and progress: one file per task
(`tasks/items/<ID>.md`) and per goal (`tasks/goals/<ID>.md`). Edit them with
`autowork tasks` (`list`, `show`, `add`, `field`, `move`, `place`, `done`, ...).


<details>
<summary><strong>Task-store lifecycle and illustrative records</strong></summary>

Task-editing verbs validate the whole store and never commit; commit their result
like any change. The `prepare` conversion lifecycle is the exception described below.
You never set the store up by hand: `/docs-sync` runs `autowork tasks prepare` first,
which converts a repository that still has `TODO.md` and `goals.json` (one proven local
commit; it refuses while work is in flight), finishes an interrupted conversion, and in
a new repository lists the accepted plan headings that goals may come from. `autowork
tasks prepare --check` writes nothing: it diagnoses the committed store at HEAD
and reports pending paths without validating their uncommitted contents. Use
`autowork tasks validate --worktree .` to validate working-tree edits. For a
conversion, `prepare --no-commit` stages the result without moving HEAD.
Contributors can use ordinary Git and project tools; see
[working on a task](docs/contributing.md#work-on-a-repository-task).

An illustrative completion report—not a recorded test result:

```text
CACHE — COMPLETED; 1 task completed
Task: tasks/items/CACHE-01.md — Add bounded cache storage.
Changed: cache implementation, tests and docs/cache.md.
Checks: cache acceptance tests passed; required review passed.
Next: CACHE-02 — Verify eviction behavior [eligible, not started].
Delivery: local commit <SHA>; not pushed, as requested.
```

### Complete illustrative task record

This is a consumer-project example, not a task to run in Toolset. Replace the goal,
accepted source, paths and check with your project's actual values. The fields are the
[task store schema](pi-autowork/task-store.md#file-schema); `autowork tasks add` writes
them for you:

```markdown
+++
schema = 1
id = "CACHE-01"
title = "Add bounded cache storage"
short = "Bounded cache storage"
status = "open"
goal = "CACHE"
section = "Now"
rank = 1000
depends_on = []
touches = ["src/cache/", "tests/test_cache.py", "docs/cache.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Bound cache memory by evicting the oldest entry; no new dependencies."
acceptance = ["entries beyond the limit are evicted oldest-first"]
checks = ["pytest tests/test_cache.py"]
exclusions = []
+++
- Sources: [Accepted cache design](docs/cache.md#accepted-cache-design)
```

Helper paths belong in the
[task-management reference](docs/reference.md#repository-helpers-used-by-workflows),
not the quickstart. See the [task-record rules](skills/shared/TODO-WORKCENTER.md)
and [reporting contract](skills/autowork/references/dispatch-and-reporting.md):
`COMPLETED` means verified acceptance and closure, not merely a passing build.

</details>

## Updating

**Hermes:** `/autowork update` in chat updates every live profile; the terminal form
is `hermes autowork update`. Use `/autowork update --check` in chat to preview. Updates
normally fast-forward clean plugin checkouts. Verified managed checkouts can recover
from rewritten upstream history through a backed-up native transaction that preserves
compatible installed-skill edits and requests no runtime restart. Dirty or unproven
sources defer. Ordinary updates reapply runtime/menu defaults except where opted out;
recovery does not. Conflicts stop preflight.

**Files updated does not mean the gateway is running updated code.** A busy root
gateway can defer its restart for up to six hours, then expire without restarting.
Check `/autowork update status` in chat for pending/deferred activation and the final
result. Profile-dedicated gateways need their own restart. See
[update behavior and recovery](docs/installation.md#update-all-profiles);
portable hosts use their [own package update commands](docs/cross-host.md).

<details>
<summary><strong>Migrating from hermes-toolset</strong></summary>

### Renamed from hermes-toolset

This project was called hermes-toolset before 0.3.0. The rename has no compatibility
layer: the plugin, command namespace, settings key (`plugins.entries.autowork`) and
chat/terminal maintenance commands (`/autowork update|status|list`,
`hermes autowork …`) exist only under the new name. Remove an older installation and
[install](#install) `autowork` again in each host; in Hermes, move any settings you set
under `plugins.entries.hermes-toolset` and rewire existing cron jobs with
`scripts/wire-owner-cron.py --apply`.

</details>

## What verification proves

| Host | Evidence and limits |
| --- | --- |
| Hermes | Offline tests, native registration/integration checks and gateway activation receipts. Live model behavior and Telegram delivery require separate live checks. |
| Claude Code | Plugin validation and an earlier isolated install are recorded; no live model workflow is demonstrated in that record. |
| Codex | Earlier isolated installation and skill discovery, plus portable-package checks; the current package still needs renewed native/live qualification. |
| Pi | Earlier isolated installation and resource discovery, plus package/command tests; the current package still needs renewed native/live qualification. |

Package contents have changed since some isolated-install runs. The
[cross-host verification record](docs/cross-host.md#behavior-and-verification) names
the tested versions and gaps; [testing and compatibility](docs/testing.md) covers
Hermes. `/autowork status` reads the runner fleet; `/autowork status NAME` reads one
repository's workers, holds and waiting reasons. `/autowork plugin status` reports
registrations and setup gaps; Hermes' `/toolsets` is a different tool-group inventory. No registration or package test proves model
output quality, Git delivery or live Telegram execution.

## Project status

The design is ambitious and the offline evidence is broad, but **sustained live
reliability is not yet proven**. An outside assessment (2026-10-21) rated the concept
and potential value highly and proven reliability at 5/10. Its main warnings are to
avoid spending more effort improving Autowork than building products with it, and to
take the permissive defaults seriously. The next step is a 30-day evaluation on
real repositories with controlled permissions: tasks completed without intervention,
regressions, owner attention and cost per verified task, time to merge, and crash
recovery. `autowork scorecard` measures part of this today. See
[Is Autowork worth it?](docs/evaluation.md) for the assessment, targets and the gaps
still to instrument.

## Documentation

| Start here | Go deeper |
| --- | --- |
| [Installation and policy opt-out](docs/installation.md) | [Command and configuration reference](docs/reference.md) |
| [Onboarding and first-use checks](docs/onboarding.md) | [Architecture and product scope](docs/project.md) |
| [Commands and workflows](docs/workflows.md) | [Cross-host behavior and verification](docs/cross-host.md) |
| [Troubleshooting](docs/troubleshooting.md) | [Testing and compatibility](docs/testing.md) |
| [Removal and recovery](docs/uninstall.md) | [Dependencies, reproducibility and licensing](docs/dependencies.md) |

**Run and inspect:** [`autowork` runner controls](pi-autowork/README.md#the-autowork-command) ·
[`tx` tmux sessions](tmux/README.md) · [Work queue](tasks/) · [Changelog](CHANGELOG.md)

**Configure and contribute:** [Memory and retained data](docs/memory.md) ·
[Speech-to-text setup](docs/FASTER-WHISPER-MEDIUM-SETUP.md) ·
[Adding skills and contributing](docs/contributing.md) ·
[Assessment and 30-day evaluation](docs/evaluation.md)

All skills use the [shared writing rules](skills/shared/COMMUNICATION.md).
They use ASD-STE100 as the writing standard and the target project's glossary for
technical terms. Reports must state what changed, what passed, and what is still
pending. These instructions are not proof of full ASD-STE100 compliance.

Licensed under the [MIT License](LICENSE). Bundled third-party components keep their
own licenses and attribution. See [licensing details](docs/dependencies.md#licensing).
