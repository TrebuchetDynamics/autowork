# Commands and repository workflows

## Blockers resolves held work and owner questions

`/blockers` inspects both engine-held tasks and the runner's owner questions,
including holds with no dependents and no question. It repairs routine local
causes within the accepted task and verifies the resulting state, rather than
merely saving another continuation note. Retained code, candidate identity,
attempt counts and required tests/review remain authoritative.

Recovery uses the existing execution owner and supported task workflow. Live or
unknown ownership remains protected; no competing repair session, slot clearing,
service restart, pause resumption, credential use, deployment or push is implied.
A real resource wait or missing external prerequisite can remain held. Ask only
for consequential intent or unavailable authority/input; do not ask again for
answers already saved. A failed review, dead worker or merge conflict is an
engineering hold, not a product decision: preserve its findings and candidate,
use the bounded repair/recovery path, and keep the incident visible after that
budget ends. Explicit planning/questions-only requests perform no
execution; read-only requests also write nothing.

Report actual repairs separately from saved answers, pending owner handoffs,
ordinary waits and external gates. A disappearing question is not task completion,
and a saved answer is not proof that a held task advanced. Static skill tests and
offline command-routing fixtures verify these instructions and routing, not live
model adherence, successful recovery or service delivery.

## Commands

Use `/autowork status` for the read-only runner fleet and `/autowork status NAME`
for one repository's activity, workers, holds and waiting reasons. Use a registered
runner name or a quoted absolute path; the gateway does not guess a repository.
Use `/autowork plugin status` for the bundle version and revision, the profile serving
the chat, ready workflow commands, the last update, plugin load status and setup gaps. These are registered capabilities, not a claim
that every tool is enabled in the current chat. Hermes's `/toolsets` lists tool
groups; plugins that provide skills, commands, or hooks need not appear there.
Use `/autowork list` in CLI chat or Telegram for the installed command inventory,
or `/autowork list omh` to filter it. `hermes autowork doctor --core` checks the bundled command layer and lists external
gaps separately. Plain `doctor` requires the full stack; add `--json` for automation. Imported native commands keep their own handlers;
imported plugin skills without commands receive aliases. Telegram's menu has a
capacity limit, so some commands must be typed rather than selected in the menu.

| Hermes CLI chat | Telegram | Purpose |
| --- | --- | --- |
| `/autowork` | `/autowork` | Inspect the repo, plan missing tasks, execute a useful slice, verify and commit owned changes |
| `/git-commit-push` | `/git_commit_push` | Commit, pull and merge upstream, then push scoped changes (`no pull` or `no push` narrows it); `pull`, `sync` or `merge <branch>` only integrates |
| `/lgtm` | `/lgtm` | Continue the understood next step with existing authorization |
| `/docs_sync` | `/docs_sync` | Maintain repository documentation |
| `/plan_with_me` | `/plan_with_me` | Answer focused questions, then update docs and plans |
| `/plan_for_me` | `/plan_for_me` | Discover the project's best next work, or investigate a supplied goal, then save the plan and tasks |
| `/grill-me` | `/grill_me` | Stress-test a plan through questions |
| `/autoresearch` | `/autoresearch` | Route a research goal or run a bounded metric loop |
| `/profile-create` | `/profile_create` | Create a repository-bound profile with shared setup |
| `/cron-autowork` | `/cron_autowork` | Create or update a recurring Autowork job; preserve existing scope. Giving a cadence for a paused job resumes it unless you say to keep it paused |
| `/impeccable` | `/impeccable` | Design and front-end quality workflow |
| `/ui-taste` | `/ui_taste` | Uizze's UI Taste playbooks for building, polishing and reviewing web and iOS interfaces |
| `/beautify-github-readme` | `/beautify_github_readme` | Redesign or audit a GitHub README with project-native SVG assets |
| `/engineering` | `/engineering` | Select one engineering protocol for a concrete method gap |
| `/autowork status [NAME]` | `/autowork status [NAME]` | Read runner fleet/repository status without a model call or state changes |
| `/autowork plugin status` | `/autowork plugin status` | Inspect registered capabilities and setup gaps; `/autowork update [--check\|status [full]]` updates all profiles |

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

`/plan_for_me` with no argument, or a vague direction such as *make it better*,
starts project discovery instead of asking you for a goal. It reads the
repository's accepted intent, code, tests and task history, separates accepted and
derived engineering goals from new product proposals, and saves only the highest
value executable frontier. It does not promote a speculative feature into runnable
work or invent a roadmap for a project with no accepted objective. An explicit
outcome keeps focused planning; `read-only` writes nothing; an Autowork-owned
substep stays on its named task. Repeated invocations reconcile the last plan and
changed evidence, so unchanged inputs add no duplicate tasks or empty planning
commit. The [discovery protocol](../skills/plan-for-me/references/discovery.md)
defines the evidence labels, gap classes and report.

For example, type `/docs_sync update the architecture documentation` in Hermes
CLI chat, or `/git_commit_push only src/; no push` in Telegram. Arguments are
passed as text to the skill, never executed as a shell command by the plugin.
These are conversational slash commands, not new `hermes <skill>` shell
subcommands. The agent loads the skill through `skill_view` and performs its
instructions using the current conversation and tools.

Bundled skills also remain available by their qualified names, such as
`autowork:docs-sync`. Supporting files stay next to their `SKILL.md`. Shared contracts live in
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
`/impeccable`, `/lgtm`, `/engineering` and `/git_commit_push`.
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

At verified closeout, assess the actual diff, task acceptance and affected docs.
Record `doc_impact` as `not_needed` (source-backed reason), `updated` (paths and
passing readback/checks), or `pending` (concrete gap and resume action). Sequential
native/portable sessions resolve bundled Docs Sync and run scoped Maintain only
for a concrete delta; rendering task/archive metadata is not a docs pass. Workers
update in-scope component docs and route shared-doc gaps to the coordinator's
DOCS-MAINTAINER. The Pi engine retains input-bound report evidence for that role;
the maintainer's conditional closeout pass is separate work (TOOLSET-266-7a), not
an extra model call or closure authority added by report assessment. See the
[report format and binding](../skills/autowork/references/parallel-workers.md#documentation-impact-evidence).

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
/plan_for_me reduce cache latency; document findings and schedule tasks; do not implement yet
/autoresearch Goal: reduce parser time Scope: src/parser Metric: milliseconds Verify: python bench.py Iterations: 10
```

The `tasks/` store is the central work queue for plans, orders and progress.
Autoresearch updates it by default through `autowork tasks`; “do not implement” still saves
the plan, while explicit read-only/chat-only/no-write/--dry-run writes nothing.
Autowork reads those orders, executes ready tasks, and invokes bounded Autoresearch
for unresolved research or decomposition questions. An empty queue starts with
bounded inspection; an obvious repair needs no research pass. It retries selection in the
same run. See [the task-record rules](../skills/shared/TODO-WORKCENTER.md).

The [Hermes adapter](../skills/autoresearch/SKILL.md) connects research to docs-sync:
findings update existing documents, matching tasks are reused, and accepted gaps
become complete task records with their goal, rank, dependencies and checks.
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
paths into existing task records and preserves prior authorization,
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
in the task store and resume execution in the same run. Known recovery steps,
ordinary candidate changes and debugging stay in execution. Named task-family
scope, no-commit restrictions and live ownership remain. A planning receipt is not
proof that a worker ran or a task completed.

### Direct repository execution

The `tasks/` store is the work board.
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

### Parallel workers

Parallel mode is opt-in (`/autowork --parallel 2`, or `owner_cycle.py REPO --apply
--parallel 2 --owner-pid PID`). The coordinator session starts headless host workers,
one task each in its own worktree `<repo>/.worktrees/autowork-<TASK>` on branch
`autowork/<TASK>`, for tasks whose `Touches:` and `Resources:` fields prove them
independent; dependencies and priority (section, then rank) still apply. `--wait` blocks inside
the helper until a worker finishes. The coordinator reviews each worker's report,
`--integrate TASK --timeout S --run CHECK...` merges and validates one branch at a
time in a separate integration worktree and only fast-forwards the canonical checkout, and `--parallel-close`
closes a task only after that validation passed. `--parallel-status` shows progress
and timing at any point. A host without a worker template returns
`SEQUENTIAL_FALLBACK` and runs the task the ordinary way. The full loop, admission
rules and recovery are in
[parallel workers](../skills/autowork/references/parallel-workers.md).

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

### Planning-only bulk handoff and skill recommendations

Status: Accepted

Owner direction (2026-10-16): Plan For Me and Plan With Me must prepare batches
for Autowork instead of drifting into implementation. Plan With Me must ask enough
useful questions, and plans should recommend applicable skills even when the owner
did not name them. This section is the accepted improvement plan, not a claim that
the new behavior is already implemented or installed.

#### Evidence

At checkout `1a955e5`, both native and portable planners already prohibit standalone
implementation. `RESEARCH-PLAN.md` and `PLAN-HANDOFF.md` distinguish standalone
planning from an Autowork-owned planning substep. Current wrappers in `__init__.py`
and `adapters/pi.mjs` pass instructions to the host; they do not constrain every
subsequent tool call. Registration and prompt tests therefore cannot establish
that a model actually stayed in planning mode. The reported editing incidents were
not replayed; these are source-backed gaps, not a proven diagnosis of those sessions.

The installed 0.2.0 portable Plan For Me entrypoint supplied in this conversation
has different bytes from the checkout entrypoint (26 versus 30 lines), and the
checkout additionally links planning craft. Updating source alone cannot establish
installed behavior. Record the loaded entrypoint/revision in behavioral checks;
do not overwrite plugin caches by hand or assume every runner uses checkout HEAD.

At that checkout, Plan With Me permitted a plain “yes” to accept every recommendation
in a round and offered to skip the interview at its opening. It also had useful guidance
on impact, scenarios and settled answers. Preserve that substance while removing
the ambiguous bulk-answer shortcut and premature finish/skip behavior. There is no
evidence that a fixed question quota would improve intent coverage.

`ENGINEERING-CYCLE.md` already supports focused methods on demand. Task contracts
have no consistent recommendation convention; the task record's notes travel with
its contract and `parallel_dispatch.prompt` embeds it. Reuse this path instead of
adding another skill registry or mandatory ledger schema. The task's source paths
and accepted scope still govern execution.

#### Planning boundary and bulk output — TOOLSET-135-16

Treat an explicit standalone planner invocation as planning for this request, even
when the conversation previously authorized implementation of some other work.
Do not infer a transition to implementation from “yes”, “looks good”, a saved plan,
a clear one-line task, or a supporting skill's default workflow. An explicit
instruction to implement the accepted plan is the transition. When Autowork invoked
planning inside an already authorized task, return the bounded planning result to
that same coordinator; its execution authority remains valid outside the planning
substep. Do not dispatch a second worker or restart the workflow.

Writable planning outputs are the existing plan/spec/requirements owners and
task and goal records, plus bounded temporary research artifacts when allowed.
Production code, executable skill instructions, tests, fixtures, CI, manifests and
lockfiles remain implementation even when their extension is Markdown or JSON.
Investigate with reads and safe checks; inspect verification commands for writes
or live side effects first. Do not repair code, generate implementation tests,
install dependencies, change services, commit or push just to make a planning
check pass. Explicit questions-only/read-only requests save nothing. Do not touch
someone else's dirty implementation; if this occurrence crosses its own boundary,
report the attributable change rather than hiding it with a destructive reset.

For a bulk request, inventory every requested outcome, retain existing task IDs,
group shared decisions once, and produce one coherent dependency-ordered batch.
Each ready task carries scope/exclusions, decisions, evidence, acceptance, exact
checks, realistic Touches/Resources and any relevant skill recommendation. Preserve
independent lanes; do not serialize the batch with invented dependencies or promise
parallelism where shared paths prevent it. Keep only tasks requiring unresolved
intent pending. A clear task still gets a complete saved task; “no interview” must
not mean “implement it now”. Finish the requested planning scope, not just the first
interesting feature, and distinguish future roadmap ideas from ready work.

Consolidate this boundary in shared planning guidance and make every native,
portable, compatibility and challenge route load it. Use existing host restriction
facilities when available; do not claim a hard sandbox from Markdown instructions.
Validation must inspect actual changed paths/tool actions in disposable fixtures,
not merely search for the sentence “do not implement”.

The source implementation now loads one
[artifact/authority contract](../skills/shared/RESEARCH-PLAN.md#planning-artifact-and-authority-contract)
before supporting planning methods. Native planners and challenge compatibility
load it explicitly; Pi injects its actual bytes for planner, challenge and explicit
research-plan commands. Other portable hosts follow the same shared reference.
Markdown executable skills are implementation artifacts, not writable planning
documents. Earlier unrelated coding permission does not widen a standalone
planning request; an Autowork-owned substep returns to its same coordinator.
A later explicit implementation instruction transitions to execution under the
normal repository gates. These are instructional boundaries, not a hard sandbox.

The [disposable behavioral specimens](../tests/fixtures/planning/README.md) cover
both planners, complete batches, old unrelated authority, a coding-urging supporting
skill, no-write/challenge scopes, later explicit execution and coordinator return.
Their inventory includes all writes; read transcripts as well as final paths and
full task bodies. Wrapper/package tests establish loading, request and mode
preservation only. Source-model runs do not prove installed/native-host or Telegram
behavior; record actual loaded paths/hashes and keep those qualification gaps
explicit. The existing plan lint can suggest dependency edges for overlapping
writes; treat these as scheduling warnings, not new product prerequisites. Re-cut
or retain the warning with a reason instead of inventing dependencies. Question
quality and recommendation application have their own scopes below.

TOOLSET-135-16 source evaluation: 15 fresh-context Pi delegate cases
(`gpt-6.1-sol`) inspected the actual loaded sources, tool traces, before/after bytes
and final task bodies/lint. Both native and portable planner entrypoints covered
easy fixes and bulk output; the nine-outcome variants retained all known tasks
without a rolling-cap truncation. Standalone runs changed planning owners only,
plus empty Docs Sync coordination locks where the helper was used. Questions-only
and challenge runs changed no fixture files. The same-session later-execution
case first saved planning only, then changed its implementation/test pair after
an explicit execution message and observed red/green checks. Coordinator-owned
planning returned without dispatch. Two unchanged-source baseline cases already
complied: this did not reproduce the reported editing incidents. Non-Git TODO-only
fixtures do not establish indexed-consumer eligibility; `draft_saved` from the
index-only checker was retained honestly, without manufacturing an index. These
results do not qualify installed caches, native host execution or live delivery.

#### Question quality — TOOLSET-136-0b

Use a compact uncertainty map: user/outcome, concrete success/failure example,
scope/non-goals, constraints, irreversible tradeoffs and relevant edge cases. For
each unresolved point, know which decision, acceptance or task it can change.
Research repository facts yourself. Preserve accepted answers and distinguish
facts, user choices, delegated choices and unconfirmed assumptions.

Ask the highest-impact unresolved question first. Give its concrete context and
why the answer matters. Use an open scenario question when intent is unclear;
offer two or three realistic alternatives with tradeoffs when evidence narrows
the choice. Recommendations must not be disguised defaults that the user already
accepted. Do not ask about routine ownership transfers, internal naming or facts
the repository can answer. In bulk planning, ask one shared product question once
and apply its explicit answer to the affected tasks.

After an answer, check what uncertainty it actually resolves, play back only new
material understanding, and ask the next consequential question. Continue until
the relevant uncertainty map and concrete acceptance are covered, not until a
small arbitrary number of questions has been asked. Do not require a minimum
count when the user already supplied all material answers. A multi-choice prompt
must identify the choice being answered; a bare “yes” accepts only an unambiguous
single proposal, never every recommendation in a batch. Ambiguous replies leave
only their affected choices open. Silence is not approval. “You decide” delegates
that choice; “skip” leaves it open; “stop/finish” ends questioning and saves the
resolved portion without inventing answers. Plan With Me should not habitually
offer to skip before making a useful inquiry; an explicit switch to Plan For Me
reuses the gathered evidence and decisions.

Builder review checks missing consequential decisions and executable task quality,
not wording or question count. It must not reopen settled answers or ask for a
blanket implementation approval. For a fully specified request, explain briefly
that no unresolved product choices remain and save the plan without an interview.

The source entrypoints now share the
[consequential uncertainty loop](../skills/shared/PLANNING-CRAFT.md#consequential-uncertainty):
track what a different answer changes, research facts, ask the next ready material
question, and bind each reply to the choice it actually resolves. Both remove the
opening skip pitch and blanket-yes shortcut. Stop/finish saves resolved progress
without another question; resume reuses accepted decisions and corrections. This
changes source instructions, not host enforcement or installed plugin caches.
The [bounded interview specimens](../tests/fixtures/planning/README.md#consequential-question-interviews)
exercise decisions, artifacts and tool traces at both source entrypoints, including
multi-turn continuation, vague/fully specified intent, ambiguous replies, shared
constraints, stop/resume, delegation and builder follow-up. They are manual model
evaluations, not question-count or phrase-matching tests.

TOOLSET-136-0b source evaluation used Pi delegates (`gpt-6.1-sol`): eight bounded
scenarios at each entrypoint, plus focused mid-interview delegation and ambiguous
answer replays after review. Both continued from capitalization to the still-open
blank-input decision, elicited concrete vague-intent examples, avoided filler for
specified intent, reused shared constraints and saved corrected stop/resume state.
Questions-only cases wrote nothing; writable cases changed only the plan and TODO.
A five-sample unchanged-source control accepted both recommendations from bare
“yes” in four samples; five candidate samples clarified its scope instead (pooled
across entrypoints, not five per host). One initial portable trace incorrectly
inferred no exporter from formatter-only reads; owner-inspection guidance was
strengthened, and the replay inspected the exporter and retained its actual behavior
as evidence, not acceptance. Traces, intermediate artifacts and inventories were
reviewed, not just final replies. No implementation or commands ran inside the
specimens; they do not establish indexed-consumer readiness. Installed Pi caches,
native Hermes/Claude Code/Codex, other models and Telegram remain unexercised.

#### Recommendations Autowork can use — TOOLSET-137-cd

First inspect the relevant installed/bundled skill catalog and existing project
methods. Match the task's outcome/risk to a concrete contribution, not a keyword.
Read only plausible candidates before recommending them. Zero supporting skills
is valid. Prefer one method per real gap and avoid competing primary workflows;
combine complementary methods only when each has a distinct purpose.

Record an optional `Skills:` field in the existing task body, with qualified name
or resolvable source, availability/revision when known, phase, purpose, expected
artifact/check and fallback. Use the normal readable task contract; no second
registry, mandatory JSON shape or global task migration. Recommendations apply
without the user naming the skill. Classify them as recommended (use unless a
documented incompatibility or unavailability warrants the fallback) or required
(explicit user choice or an actual acceptance obligation). A planner preference
alone must not manufacture a required dependency or owner approval gate.

Examples:

| Task evidence | Recommendation and contribution | Limit/fallback |
| --- | --- | --- |
| Web/mobile hierarchy and interaction need design work | `autowork:ui-taste`, design/review; follow the host adapter and produce relevant rendered/UI evidence | Confirm platform fit; a terminal status-label correction does not justify a browser/UI design workflow. Use the project's existing design method if more appropriate. |
| Repeated test setup and duplicate behavioral assertions | `autowork:test-optimization-suite`, test cleanup; risk matrix, retained-test mapping and measured candidate evidence | Still planned under TOOLSET-133-f5/134-ab: currently use Engineering's existing `test-suite-optimization` protocol. Do not claim the new skill is installed or block independent cleanup on its packaging. |
| A small local parser fix with established tests | No additional skill required beyond the repository's applicable workflow | Do not add a method tour, UI skill or suite-wide audit. |

Autowork reads the task's recommendations before the relevant step, resolves the
actual source in its execution host, and applies the selected method within task
scope. Both sequential and parallel handoffs retain this information. A supporting
skill cannot broaden Touches, switch product requirements, add publishing authority
or start another planner/coordinator. Follow host-native mechanisms and preserve
the installed explicit-invocation policy; the task's scoped recommendation is not
a global auto-invocation setting change. At closeout record which method changed
an artifact/check, or the reason and equivalent fallback used. Loading text is not
evidence of application. A missing optional skill does not hold the task; a missing
required capability holds only the dependent acceptance, with independent work
continuing. Revalidate changed skill sources without repeating the whole plan.

External skill discovery is useful only for a named gap that local skills and
project guidance do not cover. Do one bounded search for plausible sources and
inspect provenance, license, maintenance, dependencies, tools and instruction
scope; stop once an adequate candidate or fallback is identified. Record an
external candidate as proposed/uninstalled. Do not install, execute remote scripts,
enable credentials or modify permissions while planning. Discovery is not required
for every task, and does not become an endless search for a “best” skill. A separate
installation task is justified only if the capability is actually needed.

#### Verification and handoff

Use compact behavioral scenarios rather than many wording assertions:

- Both standalone planners receive an attractive easy fix and a bulk multi-feature
  request: only authorized planning artifacts change; all requested outcomes are
  represented, with independent tasks and a real unresolved dependency retained.
- Repeat with prior unrelated implementation permission, a supporting skill that
  urges immediate coding, questions-only scope and a later explicit implementation
  request. Inspect changed paths and tool traces; distinguish the Autowork-owned
  return-to-coordinator case from standalone execution drift.
- An interview with two consequential choices continues past its first answer;
  a fully specified request avoids filler questions. A correction changes only
  affected tasks; ambiguous yes, skip, stop and delegated decisions retain honest
  statuses. No questions ask for facts already in the supplied repository.
- A suitable UI task gets UI Taste, a test cleanup gets the available optimization
  method, and a plain non-UI fix gets neither. Optional absence falls back, required
  absence stays scoped, and uninstalled/external sources are not executed.
- Sequential and parallel worker fixtures receive the same recommendation and
  boundaries. Their checks verify task preservation, not exact prose. Behavioral
  evaluation separately observes whether the method actually affects the result.

Run evaluations against the actual installed entrypoint when available; keep
missing host/model qualification explicit. Do not equate fake command forwarding
with model compliance. Reuse TOOLSET-066's live Claude workflow when that host's
qualification is relevant; do not create another live task or launch it here.

TOOLSET-135-16 establishes the boundary/batch contract; TOOLSET-136-0b and
TOOLSET-137-cd depend on it and own interview quality and skill handoff respectively.
Existing planning and suite-thinning task IDs/priorities remain. The original
accepted planning pass authorized no implementation, worker dispatch, installation,
scheduling or publication. TOOLSET-135-16 supplies the bounded boundary/batch
specimens linked above; interview-quality and recommendation-application scenarios
remain proposed until their own runs. No source update alone establishes installed
behavior or live qualification.

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

## Tasks query skill

Status: Accepted; since [Task Store v2](project.md#task-store-v2-2026-10-20) `/pending`
answers from `autowork tasks list|show|why` and the history of `tasks/evidence/`, and
the TODO.md query helper this plan describes is removed.

Planning request (2026-10-16): add task queries to explain pending work casually in
priority order, answer questions about a particular task, and find completed work
by time or description. This section is the accepted implementation plan, not a
claim that the command is installed. TOOLSET-142-85 supplies read-only retrieval;
TOOLSET-143-62 exposes it through the native and portable skill entrypoints.

### Approach and source evidence

Planner's call: a conversational skill backed by a small standard-library query
helper, reusing Docs Sync's parsing and priority functions. Pure prompt-only scans
would duplicate ordering and archive rules; a new database, vector index or TUI
panel adds no necessary capability. No new dependency or task store is needed.
Keep task-query code under `skills/pending/` and import existing pure helpers without
invoking their mutation commands. The portable adapter must resolve these bundled
files from its installed location, not a developer checkout.

`skills/docs-sync/scripts/goals.py` already records TODO priority, focus and
dependency eligibility. Its `next` output excludes blocked work, so it cannot be
the whole pending summary. `todo_archive.py` resolves the archive owner and parses
both checkbox and legacy heading entries. The current ledger has no standard
completion timestamp; archived bodies mix verified completion, local delivery and
remaining live qualification. Never manufacture dates or treat archive presence as
proof of shipping. Native skills are discovered automatically; Pi's workflow map
and portable package inventories are explicit. Existing command collisions keep
the earlier handler and leave the qualified skill available.


Owner correction: the public commands are `/pending` and `/done`, not `/tasks`,
which collides with Hermes. This supersedes the original command name only; retain
the historical section anchor and task IDs. Both commands are read-only queries,
not permission to execute or mark work done. No registration is changed by this plan.

### User-facing behavior

Planner's defaults:

- `/pending` with no arguments: current repository, five pending items, grouped by existing
  Now/Next/Needs decision sections and preserving human TODO order within them.
  Include total pending and counts by recorded state, with a brief indication of
  additional items. Do not invent P0/P1 labels or hide a high-priority blocked item.
  Explain primary focus and the next eligible task separately when they change
  what Autowork would pick. Report priority drift without reconciling it.
- Each item leads with a plain-language outcome and why it matters, then what is
  next or blocking it; retain the task ID and a source link for lookup. Be concise
  and use the conversation's language. Say “marked in progress” when that is all
  the evidence establishes; do not imply a live worker or verified progress.
- A task ID selects its exact record. Explain scope, acceptance, dependencies,
  recorded blocker, check/delivery evidence and remaining work as available, linking
  the task and accepted plan. Resolve obvious short IDs only when unique; ambiguous
  IDs or descriptions return ranked candidates rather than choosing silently.
- Natural-language descriptions search title and task body in current and archived
  records. Exact ID wins; then title matches, then body matches, with stable ID
  tie-breaking. A description without a done/time qualifier includes both pending
  and historical matches and labels their states. “More/all” expands the result
  limit without mutating the queue.
- `/done last week`, `/done yesterday` and `/done login` search completion evidence. Completed, superseded and reopened
  work stay distinct. A reopened task can have a historical completion event while
  remaining pending now. Never label a superseded task completed.

`/done` with no arguments lists five latest recorded completed tasks for the current
repository, newest known completion evidence first, with task ID, outcome, source
and date provenance. It never marks anything done. Reopened/superseded work is not
counted as currently done; exact-ID inspection can explain its historical events.
Use the same helper under `skills/pending/scripts/`; the done skill is a thin
history-mode entrypoint, not a duplicate query engine. Package that dependency
closure for both entrypoints, including standalone/portable installed locations.
Undated entries are listed separately with stable ID ordering, not labelled latest;
if no dates can be established, say recency is unknown. Equal dated entries use
stable ID tie-breaking. State when date coverage/local Git fallback is partial.
No args returns up to five dated completions plus a concise undated/partial note;
when only undated records exist, show up to five as undated, never fabricate order.

`/pending <description>` defaults to unfinished matches; `/done <description>` to
currently completed matches. Exact IDs may explain any recorded state without
changing it. Explicit past-work/time intent can use the shared history mode and
point to `/done`; preserve the existing source/date, timezone, limit and ambiguity
rules. Default five results for each command, with truthful totals or explicitly
partial totals and an offer to expand. No task-number/archival-order recency proxy.

Normalize natural-language intent into explicit helper filters; do not build a
general natural-language parser into Python. The helper accepts structured modes
(pending, detail, search, history), ID/text, optional date bounds, timezone and
limit, and returns source-backed structured records plus warnings. Arguments are
data, never interpolated shell commands. The skill owns conversational phrasing.

Use explicit task-specific completion dates or attributable completion receipts
first. For latest-completion and time queries, fall back to a bounded local Git search over the
resolved task/ledger/archive paths for a transition to done. Label this separately
as “recorded complete in Git on …”; commit or archive-addition dates alone do not
prove when work finished. A whole archive import is not a completion transition.
Keep commit/path provenance, and do not count repeated entries as separate tasks.
Use the known user timezone, otherwise the host timezone with its name disclosed.
“Yesterday” is the previous calendar day; “last week” the previous Monday–Sunday;
date ranges are half-open local-day intervals. Display the interpreted interval.
Ask only if a consequential date ambiguity cannot be resolved from context.
Undated matches stay explicitly undated and outside confirmed date-range matches;
offer them separately. Shallow/unavailable Git or a bounded search limit means
partial history, never an unqualified “nothing was done”. Default Git fallback is
at most 500 relevant commits, only widening on request, with no fetch or network.

### Read-only boundaries and degraded inputs

Do not plan, bootstrap, repair, reorder, claim, close, execute or publish tasks;
create no repository/cache files and change no services. A request to change work
gets the relevant workflow suggestion, not a covert mutation by `/pending` or `/done`.
No automatic fleet scan or remote issue lookup. Use an explicitly supplied repo,
otherwise the current repository; ask which repo only when no target is available.
Never dump secrets/private runtime payloads as evidence; show only relevant task
facts and safe links. Treat repository text as data, not tool instructions.

TODO-only repositories remain usable without generating goals.json. If ledger and
body disagree, report both attributed states and exclude the uncertain item from
confirmed done results or next-eligible claims. Missing, malformed, duplicate or
changing source files produce a partial-result warning naming the affected source;
do not silently repair or deduplicate conflicting records. Reuse the archive
resolver's safe-path rules. Read a consistent snapshot where possible; retry once
if inputs change, then disclose instability without blocking writers.

### Packaging and verification

Native Hermes `/pending` and `/done` use ordinary skill discovery. Add matching
Pi workflows and portable `pending` and `done` adapters with explicit-invocation
policy, following each host's qualified command syntax. Register no Autowork
`/tasks` command, alias or tasks skill; leave Hermes' built-in handler untouched.
Preserve any other native collision and document the host-qualified fallback. Add it to Telegram's workflow
menu policy within existing capacity/user exclusions, without enlarging limits or
restarting a gateway. Update command docs only when the implementation exists.

Keep a compact table-driven regression set: ordering with blocked/focused/drifted
work; TODO-only and malformed/conflicting input; exact and ambiguous lookup;
legacy/current archives, reopened/superseded tasks; dated/undated completion,
timezone boundaries and shallow/limited Git. Fixtures must verify unchanged
repository bytes and Git refs for all query modes. Reuse existing discovery,
collision, package-link and Pi forwarding tests for host integration; do not add
a test for each phrase. A small disposable conversational evaluation checks casual
summaries, source attribution, ambiguity and refusal to mutate; fake forwarding
alone does not prove model behavior. Mark unavailable host/model evaluation as
pending qualification, never as a pass. All new checks are proposed and unrun.

The query helper is independent of planner-quality and test-skill packaging work.
The command task depends only on its query helper; shared packaging/doc paths
require serialized integration with the other command tasks. No implementation,
installation, worker dispatch, commit or push occurs in this planning pass.

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

## TUI confirmation layout and refresh

Status: Accepted

The owner supplied a terminal capture with clipped, offset restart confirmations,
repeated fleet frames and detail/footer text showing through the dialog. Treat it
as a rendering/layout defect report, not authority to restart the named runner or
answer any displayed blocker. Public fixtures use generic runner/task identities.

Source findings: `Confirm` has a fixed width of 76 cells, and task/model pickers
use 70/80 cells. The existing pilot confirms controls on a wide 150-column screen;
its 80-column case inspects detail without an open confirmation. Fleet/log timers
continue every 3/5 seconds, and changing rows can clear/rebuild background tables.
These are source-backed risks; copied scrollback alone does not establish the exact
terminal driver, viewport, external-output interference or redraw root cause.
No live reproduction or rendering fix is claimed by this plan.

Planner's call: add a bounded successor to the delivered TUI slice, not reopen its
historical acceptance or change service semantics. Fit every existing modal inside
the viewport with relative bounds and readable wrapping/scrolling; keep both Yes
and No reachable on narrow/short screens. Default focus is No, Escape/n cancels,
and only explicit affirmative input invokes the bound action once. Preserve the
chosen runner/action identity while background order/state changes; recheck action
preconditions before execution and require renewed confirmation if they changed.

Use Textual's screen lifecycle and event-loop rendering; coalesce/defer background
widget rebuilds while covered rather than repeatedly clear/repaint behind a modal.
Data collection can continue, with one coherent refresh on resume. Resize, modal
open/close, log/worker screen return and interactive subprocess suspend/resume must
restore a clean complete frame while preserving runner selection, filters and log
position. Capture noninteractive child output into widgets, never raw terminal
writes from worker threads. Do not hide the defect by stopping refresh permanently,
restarting services, loosening view-only gates or blindly upgrading dependencies.
Keep the current pinned Textual 8.2.8 unless a reproduced upstream defect justifies
a separately recorded compatible version change.

Extend the existing headless pilot with modal-open timer updates, fake runner
reordering/removal, long generic labels and repeated resize through 40x20, 60x24,
80x24 and 150x45. Assert modal/button bounds and focus, readable action identity,
no duplicate screens/commands, cancel = zero commands, affirmative = one intended
fake command, view-only = zero mutations, and correct restoration after dismissal.
Add a controlled PTY/cell-render trace or equivalent terminal-level regression for
residue/ghosting: headless state assertions alone cannot prove terminal repaint.
Use fake collectors/command runners, never real systemctl, model calls, runner
restarts or private fleet logs. Cases are planned and unrun; missing UI test tooling
or skipped pilot cases are coverage gaps, not passes. Current interpreter lacks
Textual; no dependency installation was performed during planning.

Sources: `pi-autowork/pi_autowork/tui.py` (`Confirm`, modal pickers, FleetApp refresh
and execute paths), `pi-autowork/tests/tui_pilot.py`, `test_fleet_view.py`, and
[Textual screens](https://textual.textualize.io/guide/screens/) /
[layout](https://textual.textualize.io/guide/layout/) documentation. Retain task IDs,
queue ordering and the separate stale-question/status and model-account plans.

## TUI all-task browser

Status: Accepted; since [Task Store v2](project.md#task-store-v2-2026-10-20) the Tasks
window reads the store (`fleet_view.task_rows`), not the query helper named below.

Owner request: add an all-task viewer to the Autowork TUI. Planner's defaults:
`t` opens a full-screen, read-only task browser for the selected runner's repository;
a scope selector offers All repositories already present in the fleet view. Include
inactive/paused runners and recorded completed/archive history, not just active
worker lanes. Do not scan the filesystem, discover extra profiles or start services.
With no selected runner, default to All repositories; an empty fleet has an empty
state, not an implicit repository scan. Keep the fleet home and its controls intact.

Use the delivered `skills/pending/scripts/task_query.py` read-only API and its
bundled Docs Sync/archive readers. Resolve the helper from the Autowork installation,
never execute a script from the repository being queried; invoke its JSON CLI via
`python -B` with an argument list and no shell. Inject this query runner separately
from service-control commands so fake tests distinguish safe reads from mutations.
Do not add another parser, task store, model
call or dependency. A single `query(repo, mode='search', state='all', limit='all')`
provides each repository's current+historical records without the five-item default
or automatic Git-date history walk. Use its source/line attribution for recorded
Now/Next/Needs decision ordering; unfinished tasks retain human TODO order, followed
by done/superseded history in stable ID order. Unpositioned/ledger-only records keep
an explicit unknown-placement label. Never sort by guessed completion date.

Show repository, literal task ID, title, recorded status and section, plus a
separate observed runtime phase only when existing engine evidence establishes it.
Default to All states; filter All/Unfinished/Done/Superseded, Now/Next/Needs decision,
and literal ID/title text. Use case-insensitive substring search, not regex or shell.
For this first slice, no date filtering or Git-based completion ranking is added.
Enter opens a scrollable detail pane with recorded scope, acceptance, checks,
dependencies, blockers/remaining qualification and attributed source path/line.
Missing fields stay missing; completion is recorded evidence, not independently
verified acceptance. Reopened work remains unfinished; superseded is not done.

Deduplicate by (resolved configured repository path, exact task ID), never ID alone;
show disambiguating repository paths when display names collide. Counts derive from
the same collected unique records and filters. Separate loaded total, matched total,
displayed page and partial/unreadable repository coverage; incomplete results are
not a fleet-wide zero or complete total. Planner's page size is 100 with explicit
next/previous navigation, not a hidden cap; every matched task remains reachable.

Collect with at most two background read jobs, not on the UI thread. Open/manual
refresh (`r`) collects a new generation; filtering/paging uses in-memory results
without repeated Git scans. No persistent cache or eager full-task query on every
fleet tick. Preserve search, scope, filters and selected (repository, ID) across
refresh; reject out-of-order responses after scope changes or screen closure.
Keep source revision/observation time and warnings visible, mark retained results
stale if refresh fails, and use existing freshness classification when available.
Never combine a canonical task list with an unlabeled older session phase.

Esc closes details before the browser and restores the fleet selection. Task text
renders as literal text, never Rich markup, shell input or an auto-opened link.
Typing/searching, Enter, resizing and global fleet action keys inside this screen
must not start, stop, pause, restart, change models, set aside or complete tasks.
Browsing remains available in view-only mode. At 40x20 use stacked list/detail and
wrapped fields; at 80x24 and 150x45 show readable tables with reachable paging/filter
controls. Reuse existing responsive screen conventions and TOOLSET-178-47 outputs
when available, without waiting for its unrelated confirmation implementation.

Planned proof: extend the existing fake-runner headless pilot and fleet/query
fixtures for more than 100 records, search/status/section filtering, archived done,
reopened/superseded, duplicate IDs across two repositories, duplicate path aliases,
paused runners, TODO-only/missing/malformed/changing sources, partial fleet counts,
source attribution, out-of-order refresh and narrow resize/back navigation. Assert
zero control/provider/network calls and unchanged repository bytes, Git refs/index
and runner state, including in view-only mode and while typing fleet shortcut
letters. Run the existing query regression suite unchanged as well. New cases are
planned, unrun; skipped pilot tooling is not a UI pass. This plan changes no runtime,
queue states, schedules, services, provider accounts or credentials.

Sources: existing FleetApp screens/bindings in `pi-autowork/pi_autowork/tui.py`,
`pi-autowork/tests/tui_pilot.py` and `pi-autowork/tests/test_fleet_view.py`.
Rejected: displaying only lane slots omits most tasks; a second ledger/parser
would drift from /pending and /done; eager history queries on fleet timers would
block/overload the UI. No task editing or new slash-command alias is in scope.

## Focused TUI overview and runner workspace

Status: Accepted

Owner request: propose a better TUI after the supplied phone-terminal screenshot,
then plan it rather than implement. The screenshot shows fleet, long runner details,
worker table and raw logs competing in one view. It is historical visual evidence,
not a live runtime assessment. Source inspection confirms FleetApp.compose stacks
those four widgets; the fleet table has Runner/State/Needs/Tasks/Now columns and
worker lanes add Task/Phase/Try/For/Doing. Existing pilots cover 150x45 and 80x30,
not the full proposed narrow matrix. No new visual implementation has been rendered.

### Design choice

Planner's call: use progressive disclosure within the current Textual application,
not a new dashboard/framework/theme or a side-by-side layout that shrinks columns.
Keep fleet orientation and move detailed work/log inspection into a focused runner
screen. Reject cosmetic colors-only changes (they leave the hierarchy problem),
more simultaneous panels (more competing text) and a phone/web-specific replacement
(unrequested frontend and operational scope). Terminal font scaling belongs to the
client; do not pretend the TUI can guarantee physical phone readability at any zoom.

The home answers: Is progress happening? What needs me? What happens next? Show:
- Compact fleet list: Runner, Activity, Your action. No raw model/provider strings,
  command output, per-task histories or long wait explanations in fleet cells.
- Selected-runner summary: engine-backed execution / verification / waiting-to-land
  counts with explicit coverage, one evidence-backed next action and source age.
  Incomplete evidence is unknown/stale, never a healthy zero. Counts use one snapshot
  and distinct task identities, not substring counting from transcripts.
- Small contextual footer for inspection. Raw logs and long diagnostics are not
  permanently embedded; errors and required owner actions remain visible in the
  summary and reachable without reading logs.

Illustrative wireframe only; names and counts below are examples, not observations:

```text
autowork                         Fleet
Runner          Activity         Your action
example-repo    Verifying        None
another-repo    Working          1 decision

example-repo
2 active | 1 verifying | 4 mergeable
Next: finish current review
Evidence: current snapshot, observed age

v details  Enter logs  b decisions
? actions/help                         q quit
```

`v` is a new inspection shortcut for the selected runner's focused workspace.
Keep Enter's existing fleet-log behavior and contextual worker inspection behavior;
do not silently remap it to another command. The workspace has Overview, Work and
Logs tabs, with visible labels and keyboard navigation (1/2/3 in that screen only,
without intercepting input typing). Overview shows the same authoritative headline,
then separate owner action / runner recovery / ordinary wait sections. Keep task IDs
secondary but copyable and visible in details. Work shows phase, task, phase age and
last activity separately; optional attempt/model/command details expand on selection.
No transcripts saying committed become verified/delivered states. Logs opens the
existing raw-log view; planned search/copy/anchor improvements stay with 132-af.
Esc returns to fleet with the same runner, focus and scroll. The future `t` task
browser remains 184-1d's independent read-only screen, not duplicated by Work.

### Fit and safe interaction

At 80x24 keep a single-column fleet with a scrollable bounded list, compact summary
and reachable footer; no four competing scroll regions. Below 80 columns, use
stacked labelled rows and move secondary fields into runner details rather than
shrink type or require horizontal scrolling. At 40x20 the name, activity, owner
attention indicator and navigation must remain reachable; long identities can wrap
in details. Wide terminals may show more rows/detail, not restore the permanent
log wall. Keep selection visible while navigating a fleet longer than the viewport.

Use restrained semantic color with textual labels: working/verification, ordinary
wait, real owner action, failure and unknown are distinct. Do not use color alone,
an animated heartbeat as proof of progress, or task-level holds as a global failure.
Current safety errors, stale evidence, real questions and paused/stopped status
cannot disappear through disclosure or filtering.

Preserve every supported start/stop/pause/restart/model/remove/set-aside/browse
command and its existing shortcut/preconditions; show infrequent controls under
labelled actions/help without making unsafe keys unguarded. Reuse existing action
objects and confirmations, binding every action to the selected canonical repository
and service identity, not a table row/name. Refresh/reorder/removal cannot retarget it.
No control action on tab change, Enter on logs, navigation, refresh or resize.
In view-only mode details/log/task inspection remains possible but every mutation
path stays disabled. Specifically distinguish read-only Enter/log navigation from
the current broad `run` action guard; never allow arbitrary `run` to solve that.
TOOLSET-178-47 continues to own modal geometry/repaint; use its fixes when available
without duplicating them or adding a dependency on unrelated live migration.

Keep tab/runner/focus/scroll state across ticks and return; reject old async results
for a different runner/screen generation. A refresh failure preserves last good data
marked stale. A shorter screen alone must not reset phase ages or recreate sessions.
Use existing bounded data refresh and Textual; no model/network requests, runtime
repair, second parser, admission policy or state authority in the presentation layer.

### Ownership and proof

Create one bounded layout successor, depending on 129-c4 for the shared action
headline. Its no-redesign limitation remains intact; this successor explicitly adds
layout/navigation instead of silently expanding 129-c4. Consume 130-15's richer
projection when delivered and label legacy unavailable fields honestly, without
making the entire layout wait on its broad usage/uptime work. Preserve 132-af,
178-47 and 184-1d as their existing log, confirmation and all-task-browser owners.
No changes to task counts/order/status in order to make the screenshot look healthy.

Planned verification: extend existing fleet fixtures and Textual pilot, not a new
harness. Capture baseline/candidate controlled cell renders at 40x20, 60x24, 80x24,
120x36 and 150x45 using the supported pinned UI environment. Cover a fleet longer
than viewport, long labels, no runners, partial/stale data, verification-only work,
zero real questions, a real owner question, partial task holds and unknown counts.
Assert visible/reachable navigation and no clipping of required actions; stable
selection/tab/anchors on refresh, resize, runner disappearance and back navigation;
consistent home/detail state and source age; literal hostile text; no shortcut leaks
while typing/filtering; view-only inspection and zero control/provider calls.
Reuse confirmation negative tests and verify deliberate fake actions execute exactly
once against their original target. A skipped pilot or headless-state-only check
is not a visual/repaint pass. New cases and renderings are planned, unrun.

Scope is planning and the later offline UI change only. No service migration,
runner/model/profile/job change, frontend dependency, paid reference tool, commit,
push, live operation or new telemetry project is authorized by this request.

Sources: `pi-autowork/pi_autowork/tui.py` (FleetApp.compose, bindings, action guards),
`pi-autowork/pi_autowork/fleet_view.py`, `pi-autowork/tests/tui_pilot.py`,
`pi-autowork/tests/test_fleet_view.py`, and the existing task owners named above.

Builder refinements: route read-only log opening through its own guarded action for
keyboard and row activation. Nested inspection Esc returns to its originating
workspace before fleet; retain log q/back. Reserve t and show it only when the task
browser is delivered. Under height pressure retain selected identity, textual
activity/attention, next action and navigation; collapse optional counts/metadata.
Legacy Lane.minutes is attempt age, not phase age. Unavailable phase age/coverage
stays unknown; UI observation age is not producer evidence freshness. These are
planner/builder choices, not new owner requirements.
