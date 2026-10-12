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
| `/toolset` | `/toolset` | Inspect registered capabilities and setup gaps |

Use `/plan_with_me` when you want questions before planning. It asks one at a
time, reuses existing answers, and saves decisions through repo-docs. Add
`questions only` for an interview without file changes.

For example, type `/docs_sync update the architecture documentation` in Hermes
CLI chat, or `/git_commit_push only src/; no push` in Telegram. Arguments are
passed as text to the skill, never executed as a shell command by the plugin.
These are conversational slash commands, not new `hermes <skill>` shell
subcommands. The agent loads the skill through `skill_view` and performs its
instructions using the current conversation and tools.

Bundled skills also remain available by their qualified names, such as
`hermes-toolset:repo-docs`. Supporting files stay next to their `SKILL.md`. Shared contracts live in
[`skills/shared`](../skills/shared/COMMON-CONTRACT.md), alongside the skill folders;
the legacy skill copier preserves that support directory too. Resolve helper
commands from the loaded bundle rather than assuming `~/.hermes/shared-skills`.
Generated autowork ledger commands use quoted paths to the bundled helper.
An existing built-in or previously registered plugin command wins a name
collision; the skipped alias produces a warning and the qualified skill remains
available. Choose distinctive names to avoid collisions with other plugins,
local skills, and configured quick commands.

Repo-docs and autowork decide routine engineering choices autonomously within the
accepted scope. They carry decisions into worker contracts and apply relevant
[Addy agent-skills](https://github.com/addyosmani/agent-skills) throughout planning,
implementation and verification, including API, UI, migration, CI and operational
work. Handoffs identify the skill used, the artifact or decision it informed, and
its check result. Missing owner intent or authority remains an explicit question;
loading a skill alone is not proof of applying it.

The [engineering cycle](../skills/shared/ENGINEERING-CYCLE.md) connects accepted
specs and existing `goals.json`/`TODO.md` tasks to targeted installed engineering
skills, implementation, checks, native review and owner-ledger reconciliation.
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

The [Hermes adapter](../skills/autoresearch/SKILL.md) connects research to repo-docs:
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

`/engineering` (the same spelling in Telegram) selects Addy engineering methods for
the current phase. Autowork, Repo Docs and Autoresearch load this adapter through the
shared engineering cycle; no separate command is normally needed. Examples:

```text
/engineering plan the accepted cache change into TODO.md; do not implement
/engineering review the current cache task against its acceptance checks
```

The [adapter](../skills/engineering/SKILL.md) loads a small relevant selection from
25 pinned protocols and their shared references. It translates upstream plan/task
paths into existing TODO.md/goals.json entries and preserves prior authorization,
explicit restrictions and actual review requirements. Its protocols are not extra
workers or independently registered slash commands. See [provenance and updates](dependencies.md#refresh-the-pinned-engineering-pack).
