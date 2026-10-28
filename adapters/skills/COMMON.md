# Claude Code, Codex and Pi host contract

Use the [ASD-STE100 and project language rules](../../skills/shared/COMMUNICATION.md)
for user-facing text. Read the target project's glossary map and glossary when available.

These adapters run repository workflows in the current Claude Code, Codex or Pi session.
Use this host's actual file, terminal, search, question and delegation tools.
Read repository instructions and user scope first; preserve unrelated work.
Every bundled workflow applies the [shared Ponytail method](../../skills/shared/PONYTAIL.md)
within its own authority. The pinned suite is included on all hosts; no external
Ponytail plugin or persistent activation is required.
Do not require Hermes CLI, profiles, gateways, Kanban cards, native origin injection,
worker manifests, cron jobs, OMH, speech or another agent runtime. Those integrations
belong to the Hermes distribution, not portable prerequisites.

Installation exposes skill metadata, not all instructions in every request. Load
only the selected workflow and relevant references. Resolve links relative to the
loaded skill file. The canonical primary workflows are Plan With Me, Plan For Me,
Docs Sync and Autowork. Autoresearch remains independently discoverable with all
13 research selectors. Grill Me is Plan With Me's challenge mode, not a separate
public skill; Pi retains `/grill_me` as a compatibility command. In native skill
invocation (`/autowork:plan-with-me` in Claude Code), select `plan-with-me`
and request challenge mode.
Shared source files are reference material; this contract takes
precedence over Hermes-specific execution procedures in linked upstream material.
Never change host permissions, memory configuration, model credentials or approval
policy to make a workflow run. A skill cannot promise unattended execution after
the current host session ends.

Follow [task holds](../../skills/shared/TODO-WORKCENTER.md#task-holds-require-an-explicit-user-request):
leave tasks active by default. Only an explicit user request permits a skill to add
or renew a task hold. Planning-only session scope does not pause the queue.
Preserve existing user pauses, live claims, dependencies and safety gates.

Explicit invocation authorizes the documented default action within user scope.
Questions-only/read-only/no-write/no-commit/no-push restrictions propagate through
all handoffs. Product intent is distinct from proposals and current behavior.
The repository's `tasks/` store is the one work queue: task and goal records edited
through `autowork tasks`, never by a worker's commit. Do not fabricate completion,
review, attribution or live qualification there. Python 3 is needed only when
using bundled Python helpers, not for a questions-only interview.

Use available independent review when required; if unavailable, state the missing
check rather than invent approval. A local commit, local integration, remote push,
release and deployment are separate outcomes. Preserve active work and paused jobs.
Report task, actual changes, checks, commit, next action and precise unresolved input.
