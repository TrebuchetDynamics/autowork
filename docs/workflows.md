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
| `/cron-autowork` | `/cron_autowork` | Create or update a recurring Autowork job; preserve existing scope. Giving a cadence for a paused job resumes it unless you say to keep it paused |
| `/impeccable` | `/impeccable` | Design and front-end quality workflow |
| `/ui-taste` | `/ui_taste` | Uizze's UI Taste playbooks for building, polishing and reviewing web and iOS interfaces |
| `/beautify-github-readme` | `/beautify_github_readme` | Redesign or audit a GitHub README with project-native SVG assets |
| `/engineering` | `/engineering` | Select one engineering protocol for a concrete method gap |
| `/toolset` | `/toolset` | Inspect registered capabilities and setup gaps; `/toolset update [--check\|status]` updates all profiles |

Both planners use the pinned Autoresearch planning method and save evidence,
decisions and actionable tasks through Docs Sync, following the shared
[planning craft](../skills/shared/PLANNING-CRAFT.md). Both size the work first (a
clear task gets no interview), say every default they chose as the planner's call,
record goals, non-goals and anti-goals, and run a builder check: a fresh reader in
Autowork's place lists what it would still have to guess, and only the answers that
change what gets built come back to you, in one message.

`/plan_with_me` opens by offering to skip the questions (reply *plan it for me*),
then gets you describing before offering options. It asks in short rounds: one open
question, or a few ready decisions numbered with recommendations, worded so a plain
"yes" accepts them. It plays each understood part back with its guesses marked,
researches facts itself, flags terms and claims that contradict the code, and can
challenge assumptions using Grill Me. `/plan_for_me` investigates and chooses
within your delegated scope. Both reuse existing answers and plans. Add
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
| `/plan_for_me` | `plan-for-me` | `/autoresearch:plan` (CLI), `/autoresearch_plan` (Telegram); runs the Autoresearch skill's plan protocol with the same planning adaptations |
| `/docs_sync` | `docs-sync` | None |
| `/autowork` | `autowork` | None; Autogoal is retired |

Grill Me is the challenge mode of Plan With Me; its old command still works but
is not advertised as a separate plugin skill. Autoresearch protocols remain
accessible through their commands and the Plan For Me adapter. Autoresearch compatibility command
spellings remain typeable but are deliberately omitted from Telegram menu
advertising, not merely displaced by capacity. Plan With Me and Docs Sync do not
register the old repo-interview or repo-docs aliases. The Telegram menu prioritizes
the five current workflow commands, then `/ui_taste`, `/beautify_github_readme`,
`/impeccable`, `/lgtm`, `/engineering`, `/git_commit_push` and `/git_pull_merge`.
Hermes' default menu holds 60 entries and its built-ins alone exceed that, so each
prioritized command displaces the lowest-ranked built-in (currently `/yolo`,
`/approvals`, `/fast`, `/voice`, `/busy`, `/memory` and `/bundles`), which stays
typeable. Do not rename helper paths or saved receipt keys for presentation. Autogoal references in migration code preserve old state;
they do not register a live command. Hindsight is not a bundle integration; its
negative tests prevent accidental reintroduction. Updating source does not refresh
an already-running gateway's command registry: use supported plugin reload and
verify activation before claiming the new names work in messaging.

Docs Sync and autowork decide routine engineering choices autonomously within the
accepted scope. The executing session (or an optional authorized delegate) works
from the selected task, accepted decisions, scope, checks
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
its stated scope. Default `/autowork` completes one useful slice in the current
session, including recovery and closeout. Review acceptance and
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
`/autoresearch plan ...` also works. Autoresearch compatibility commands, including
the base and underscore spellings, are intentionally not advertised in Telegram's
menu; type the desired command with its request text. This is separate from the
menu capacity limit and does not remove the typed handlers. Existing command
owners keep precedence.

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

Planning resolves consequential design, dependency and product choices and saves
an executable task with scope, decisions, acceptance and checks. Autowork executes
that task without another permission round: choose reversible details, implement,
test, repair and finish authorized closeout. It can adapt a failed implementation
on the same task while preserving accepted behavior and checks.

Only a newly discovered consequential choice or missing decomposition invokes
bounded Plan For Me, automatically and within existing authority. Save the decision
in TODO.md/goals.json and resume execution in the same run. Known recovery steps,
ordinary candidate changes and debugging stay in execution. Named task-family
scope, no-commit restrictions and live ownership remain. A planning receipt is not
proof that a worker ran or a task completed.

### Direct repository execution

TODO.md is the work board; goals.json, when present, is its synchronized index.
`owner_cycle.py` selects and coordinates a bounded task for the current session.
Its `EXECUTE` result is a contract to implement, not completed implementation or a
worker launch. Use its [current interface](../skills/autowork/references/owner-cycle.md)
for actual owner identity, source-bound receipts and bounded command execution.

No Kanban lookup, historical card, native continuation API or card review transition
is required for selection, recovery or local integration. Preserve actual writers,
useful candidates, explicit allocations, required checks/review and publication limits.
Host-native delegation remains optional and needs existing authorization.

Autowork works in the canonical checkout unless something is actually writing
there. A running Autowork command for the repository blocks every worktree. Any
other agent session (such as `pi`, `claude`, `codex`, `hermes` or `aider`) blocks
only the checkouts it touches (its working directory, path arguments or open writable
files), and only while it is active (terminal input or output in the last 30
minutes, running commands, or an open writable repository file) or its activity
cannot be determined, for example without a readable terminal. A launcher whose
only child is the agent itself does not count as running commands. An idle
session left open is listed under `idle_sessions` (an active or unknown-activity
session in another checkout under `other_checkout_sessions`) and never blocks, killed or
messaged. For an active one the helper returns `BUSY` with an `isolate` branch and
`git worktree add` command; the task runs there, and `owner_cycle.py REPO
--writers` (read-only; `CLEAR`, `BUSY` or `ACTION_REQUIRED`, exit 1 unless `CLEAR`)
gates merging the branch back.

### Delivery batches and partial completion

Autowork executes one coherent outcome in the current session: connected consumers,
runners and tests share a batch when their dependencies and authority permit it.
One useful slice is not a one-file limit. The coordinator chooses routine batch
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
source and actual process/workspace ownership before implementation. No changes means no repeat documentation
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

## Telegram reporting qualification

Status: Accepted

The existing reporting requirement and TOOLSET-011 retain the requested Telegram
destination and separate setup confirmation, actual execution and scheduled
message delivery. Verify one setup confirmation in the intended chat/topic and
attributable scheduled execution/delivery on the original host/profile/job.
Setup or command registration alone cannot close that qualification. Preserve the
owner's stop-all instruction: this scope creates no replacement job, immediate run
or permission to resume a schedule.

## Scheduling behavior

Use `/cron-autowork` (`/cron_autowork` in Telegram) for schedule setup; `/autowork` performs the work. The scheduling
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

Each run of a Telegram-routed Autowork job with the start-notice script attached
sends a start message before the agent begins, and the run's report when it finishes. The start message comes from the
bundle's `autowork-start-notice.py` pre-run script, which the plugin copies into
every profile's `scripts/` folder (Hermes runs cron scripts only from there) and
`/cron_autowork` attaches to the job unless the job already has a different script
(it keeps that one and reports the notice as not attached). A same-named script without the bundle
marker is treated as the user's and never replaced. The script never fails a run;
a missing token, ambiguous job match or unreachable Bot API is reported in the
run's own prompt instead.
