# Commands and repository workflows

## Commands

Use `/toolset` for plugin versions, load status, registered tool/command/skill/hook
counts, and unavailable imports. These are registered capabilities, not a claim
that every tool is enabled in the current chat. Hermes's `/toolsets` lists tool
groups; plugins that provide skills, commands, or hooks need not appear there.
Use `/toolset list` in CLI chat or Telegram for the installed command inventory,
or `/toolset omh` to filter it. `hermes toolset doctor --core` checks the bundled command layer and lists external
gaps separately. Plain `doctor` requires the full stack; add `--json` for automation. Imported native commands keep their own handlers;
imported plugin skills without commands receive aliases. Telegram's menu has a
capacity limit, so some commands must be typed rather than selected in the menu.

| Hermes CLI chat | Telegram | Purpose |
| --- | --- | --- |
| `/autowork` | `/autowork` | Inspect the repo, plan missing tasks, execute a useful slice, verify and commit owned changes |
| `/git-commit-push` | `/git_commit_push` | Commit and push scoped changes |
| `/git-pull-merge` | `/git_pull_merge` | Pull and merge changes |
| `/lgtm` | `/lgtm` | Continue the understood next step with existing authorization |
| `/docs_sync` | `/docs_sync` | Maintain repository documentation |
| `/plan_with_me` | `/plan_with_me` | Answer focused questions, then update docs and plans |
| `/plan_for_me` | `/plan_for_me` | Investigate, choose an approach, and save the plan and tasks |
| `/grill-me` | `/grill_me` | Stress-test a plan through questions |
| `/autoresearch` | `/autoresearch` | Route a research goal or run a bounded metric loop |
| `/profile-create` | `/profile_create` | Create a repository-bound profile with shared setup |
| `/cron-autowork` | `/cron_autowork` | Create or update a recurring Autowork job; preserve existing scope and paused state |
| `/toolset` | `/toolset` | Inspect registered capabilities and setup gaps |

Both planners use the pinned Autoresearch planning method and save evidence,
decisions and actionable tasks through Docs Sync. `/plan_with_me` improves your
initial request with one focused question at a time about ambiguities and important
choices; it researches facts itself and can challenge assumptions using Grill Me.
`/plan_for_me` investigates and chooses within your delegated scope. Both reuse
existing answers and plans. Add
`questions only` for an interview without file changes.

For example, type `/docs_sync update the architecture documentation` in Hermes
CLI chat, or `/git_commit_push only src/; no push` in Telegram. Arguments are
passed as text to the skill, never executed as a shell command by the plugin.
These are conversational slash commands, not new `hermes <skill>` shell
subcommands. The agent loads the skill through `skill_view` and performs its
instructions using the current conversation and tools.

Bundled skills also remain available by their qualified names, such as
`hermes-toolset:docs-sync`. Supporting files stay next to their `SKILL.md`. Shared contracts live in
[`skills/shared`](../skills/shared/COMMON-CONTRACT.md), alongside the skill folders;
the legacy skill copier preserves that support directory too. Resolve helper
commands from the loaded bundle rather than assuming `~/.hermes/shared-skills`.
Generated autowork ledger commands use quoted paths to the bundled helper.
An existing built-in or previously registered plugin command wins a name
collision; the skipped alias produces a warning and the qualified skill remains
available. Choose distinctive names to avoid collisions with other plugins,
local skills, and configured quick commands.

Public skill names match the workflow names. Source directories stay stable for helper links:

| Primary command | Public skill ID | Compatibility command |
| --- | --- | --- |
| `/plan_with_me` | `plan-with-me` | None |
| `/plan_for_me` | `plan-for-me` | `/autoresearch_plan` |
| `/docs_sync` | `docs-sync` | None |
| `/autowork` | `autowork` | None; Autogoal is retired |

Grill Me is the challenge mode of Plan With Me; its old command still works but
is not advertised as a separate plugin skill. Autoresearch protocols remain
accessible through their commands and the Plan For Me adapter. Autoresearch compatibility command
spellings remain available; Plan With Me and Docs Sync do not register the old
repo-interview or repo-docs aliases. The Telegram menu shows the current workflow
names. Do not rename helper paths or saved receipt keys for presentation. Autogoal references in migration code preserve old state;
they do not register a live command. Hindsight is not a bundle integration; its
negative tests prevent accidental reintroduction. Updating source does not refresh
an already-running gateway's command registry: use supported plugin reload and
verify activation before claiming the new names work in messaging.

Docs Sync and autowork decide routine engineering choices autonomously within the
accepted scope. Workers receive the selected task, accepted decisions, scope, checks
and completion rules. For a concrete method gap or explicit request, they select one
[Addy protocol](../skills/engineering/SKILL.md). Autowork retains workflow authority;
protocols supply techniques within its contract. Handoffs record methods that
materially changed a decision or artifact, with their check results.
Missing owner intent or authority remains an explicit question;
loading a skill alone is not proof of applying it.

The [engineering cycle](../skills/shared/ENGINEERING-CYCLE.md) is an optional routing
reference when method selection is unclear. A ready task needs no routing prepass.
A documentation-only `/docs_sync` request does not launch workers. To continue
through a spec, explicitly ask `/autowork` to implement that accepted spec within
its stated scope. Default `/autowork` hands off one slice. Review acceptance and
executed evidence precede canonical closure; no push or deployment is implied.
Skill availability and support files are checked at use time; a missing skill is
reported with its safe fallback, not silently treated as loaded.

## Autoresearch

The bundle vendors [uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch)
v2.2.2 at the revision in [UPSTREAM.json](../skills/autoresearch/UPSTREAM.json), with
its MIT license and runtime scripts. Installing the bundle makes it available in
every configured profile; no separate Claude/Codex installation is required.

Use `/autoresearch` for goal routing or a metric-driven loop. All 13 upstream
subcommands are available:

`plan`, `debug`, `fix`, `security`, `ship`, `probe`, `scenario`, `predict`,
`reason`, `learn`, `improve`, `evals`, `regression`.

Use `/plan_for_me` in CLI or Telegram for planning. Legacy `/autoresearch:plan`
and `/autoresearch_plan` remain available. Other subcommands retain their names:
for example, `/autoresearch:debug` in CLI and `/autoresearch_debug` in Telegram.
`/autoresearch plan ...` also works. Colon commands are omitted
from Telegram's menu; use the underscore spelling there. Menu capacity can hide
entries without disabling typed commands. Existing command owners keep precedence.

```text
/plan_for_me reduce cache latency; document findings and schedule TODO tasks; do not implement yet
/autoresearch Goal: reduce parser time Scope: src/parser Metric: milliseconds Verify: python bench.py Iterations: 10
```

TODO.md is the central work queue for plans, orders and progress. Autoresearch
updates it by default and synchronizes goals.json; “do not implement” still saves
the plan, while explicit read-only/chat-only/no-write/--dry-run writes nothing.
Autowork reads those orders, executes ready tasks, and invokes bounded Autoresearch
for unresolved research or decomposition questions. An empty queue starts with
bounded inspection; an obvious repair needs no research pass. It retries selection in the
same run. See [the work-center contract](../skills/shared/TODO-WORKCENTER.md).

The [Hermes adapter](../skills/autoresearch/SKILL.md) connects research to docs-sync:
findings update existing documents, matching tasks are reused, and accepted gaps
become full TODO.md bodies with goals.json priorities, dependencies and checks.
This schedules the backlog; it does not create a timer. Autowork can execute
eligible tasks when implementation is authorized, preserving its ownership,
verification and commit gates. Read-only and planning-only requests remain scoped.
Upstream flags and analytical methods are retained; host-specific tools, generic
confirmation prompts, experimental Git handling and documentation handoffs follow
the adapter. Claude-only hooks are not installed.

`/autowork` is the repository development command. Its helpers and profile-local
state live under `autowork/`; upgrades preserve existing work through migration.

## Pinned engineering protocols

`/engineering` (the same spelling in Telegram) selects a technique for a specific
method gap. Autowork, Docs Sync and Autoresearch can consult this adapter on demand;
ready tasks need no separate command. Examples:

```text
/engineering use performance-optimization to diagnose this cache bottleneck
/engineering use code-review-and-quality for the current task's existing review
```

The [adapter](../skills/engineering/SKILL.md) provides 25 pinned protocols and their
shared references. Its router's `--protocol NAME` selects exactly one method;
explicit phase commands remain available as optional bundles. Both modes verify
selected protocol and shared reference hashes. It translates upstream plan/task
paths into existing TODO.md/goals.json entries and preserves prior authorization,
explicit restrictions and actual review requirements. Its protocols are not extra
workers or independently registered slash commands. See [provenance and updates](dependencies.md#refresh-the-pinned-engineering-pack).

### Automatic planning during execution

Autowork calls Plan For Me itself when preparation is stuck on unclear prerequisites
or candidate changes. It records a bounded recovery plan through Docs Sync in
TODO.md/goals.json and retries execution in the same run. No separate planner
command is required. Named task-family requests stay within that scope; explicit
no-commit restrictions and live writers still apply. Unchanged inputs resume the
saved plan rather than generating repeated planning reports. A planning receipt
is not proof that a worker ran or a task completed.

### Delivery batches and partial completion

Autowork prepares one coherent outcome per admitted worker: connected consumers,
runners and tests share a batch when their dependencies and authority permit it.
One-card concurrency is not a one-file limit. The coordinator chooses routine batch
boundaries and reuses valid exact-source evidence where repository policy allows;
required review and changed-input checks still run. See
[delivery batching](../skills/autowork/references/delivery-batches.md).

A delivered slice is reported by its behavior and commit/integration stage, with
parent status and remaining acceptance separately. An open parent is not evidence
of zero progress. These rules do not promise a completion rate or eliminate real
worker, live-environment or runtime constraints.

### Planning without repeated setup

Plan With Me asks only unresolved user choices; Plan For Me resolves the specific
engineering uncertainty; Docs Sync persists the affected batch. They share the
[single-pass handoff](../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
Autowork consumes the saved decisions and check results, then verifies current
source and ownership before dispatch. No changes means no repeat documentation
pass. An optional unanswered question holds its dependent tasks only. Standalone
planning still does not authorize implementation.

### Source names and compatibility

Docs Sync lives in `skills/docs-sync/`; Plan With Me lives in
`skills/plan-with-me/`. Neither workflow registers legacy command aliases.
Retired host-local worker snapshots are not installed, packaged or registered as skills.

Plan For Me lives in `skills/plan-for-me/` and is registered as its own skill.
It applies the pinned planning protocol from `skills/autoresearch/`, which remains
the separate Autoresearch skill and protocol suite. `/plan_for_me` selects planning;
`/autoresearch` selects the research router. Non-planning protocols remain available.
The legacy worker-contract field `Repo-docs pass` and receipt key `repo_docs_pass`
remain internal compatibility fields, not additional skills or commands.

Use `/cron_autowork` for schedule setup; `/autowork` performs the work. The scheduling
skill lists existing jobs first, binds the actual repository/workdir and profile,
updates a matching job, and verifies the saved cadence, prompt and execution limits.
A new job without a cadence asks for one. `prompt only` creates no job. Portable
hosts without a scheduler return a specification explicitly marked not scheduled.
New Hermes jobs default to a resolved Telegram chat/topic, independent of whether
setup starts in CLI, Telegram or another surface. Explicit delivery/quiet preferences
remain authoritative. After saving, setup confirms in that Telegram destination;
recurring jobs report every occurrence by default, including unchanged blockers.
Setup confirmation, job execution and scheduled message delivery have separate
receipts. Scheduling alone does not trigger an immediate development run.
