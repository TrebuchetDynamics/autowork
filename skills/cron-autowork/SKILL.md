---
name: cron-autowork
description: "Create or update a recurring Autowork job for a repository, with explicit scope, continuation, delivery and budget settings. Use for scheduling, not for executing a development task now."
license: MIT
---

# Cron Autowork

`/cron_autowork` (CLI also `/cron-autowork`) sets up recurring Autowork execution.
Use the current scheduler's supported tools; this skill is not a second scheduler.
Creating this skill or installing the plugin never creates a job automatically.

## Repair command discovery before scheduling

An unknown-command reply occurs before scheduler work; do not recreate a job to
repair it. Verify the receiving profile's native skill and plugin registration.
When supported by the installed toolset, run
`hermes -p PROFILE toolset finalize --hermes-home ROOT --bundle-only` to refresh
that profile's live gateway command wiring without restarting the shared gateway.
Require a profile-matched `ready` / `commands_reloaded` receipt. Finalization does
not update native skill copies or prove the original Telegram invocation succeeded;
keep installation, live registration and message retry separate. If this route is
unavailable, request `/reload-skills` in the receiving bot. A fresh subprocess
resolution alone is not live-cache proof. Preserve schedules, workers and budgets.

## Resolve the job

Read existing user instructions and the current profile/workspace. Resolve the
canonical repository and list this profile's jobs, including paused jobs. Inspect
job details before writing. Match profile + canonical repository + overlapping
Autowork scope, not name alone; accept an explicit job ID only after checking its
profile and repository. If multiple matches or the target is unclear, ask one
focused question. Do not guess another profile, cwd or chat destination.

Extract cadence, task filter versus broad repository development, delivery target,
and existing commit/push/live-operation limits. Reuse existing settings unless the
user changes them. For a new job with no cadence, propose every 30 minutes and
ask for the cadence before creating it. For wall-clock schedules, establish the
timezone and report the scheduler's normalized next occurrence. Never confuse a
one-shot delay with a recurring interval. A bare invocation helps complete missing
settings; a complete create/update request authorizes that operation without another
confirmation round. Preview/read-only/“prompt only” makes no scheduler changes.

## Prepare one compact instruction

Read [Autowork scheduled policy](../autowork/references/scheduled-policy.md).
Reuse its behavior rather than copying the entire skill into a cron prompt. Attach
the verified Autowork skill using the installed scheduler's supported skill field;
also name it in the prompt. Set the real absolute workdir, not merely a prose path.
Use this template with resolved values; never save placeholders:

```text
Use hermes-toolset:autowork in REPOSITORY under PROFILE.
Scope: REPOSITORY_DEVELOPMENT_OR_EXACT_TASK_FILTER.
Delivery authority and exclusions: EXPLICIT_LIMITS.
Resume saved continuation and read current original-card/run state first.
Integrate approved work before new discovery. Reuse checks only while inputs match.
Continue an existing worker/card; do not launch overlapping or replacement work.
Repair attributable task/docs metadata and retry selection in this occurrence.
Use Plan For Me only for unresolved planning; save findings through Docs Sync.
For broad repository scope, replenish justified tasks when none is ready; for a
task filter, stay within that scope and its authorized prerequisites.
Preserve consumed budgets, partial work, retry history and paused jobs. A cron tick
does not grant a fresh allocation to an exhausted card. Do not edit Hermes Agent.
Follow saved recovery outcomes; no repeated unchanged audits or planning-only loops.
Report task ID/title, implemented or integrated slice, checks, commit/publication,
next task, and the exact unresolved operation/input. Separate parent-task completion
from delivered slices. Unchanged observations are not new progress.
```

Do not invent model overrides, spend limits, worker turn increases, push permission,
deployment authority or live-device access. Cron cadence is not a task budget.
The scheduler's execution window may end before a worker: the next occurrence
reconciles that worker rather than duplicating it. Do not promise overlap prevention
or cumulative enforcement the installed scheduler/runtime does not provide.

## Apply and verify

Use `cronjob` list/create/update when available, inspecting its current schema.
Otherwise inspect the installed profile-scoped Hermes cron CLI help and use its
supported create/edit interface. Pass prompts as structured arguments or safely
quoted file content; do not interpolate raw user text as shell code. Never edit
jobs.json, scheduler databases, system crontab or Hermes Agent source directly.

Use scheduler idempotency or serialization when supported. Otherwise recheck for
a match immediately before creation and disclose that concurrent setup requests
cannot be guaranteed unique; do not invent a supported idempotency flag.
Update a single matching job instead of creating a duplicate. Preserve its ID,
history, unrelated settings and paused/enabled state; resume only when requested.
Do not run the job immediately unless requested. After a timeout or unclear write
result, list/read back before retrying creation. If outcome remains uncertain,
report it instead of creating another job. Required fields unsupported by this
installation are a concrete setup limitation, not permission to silently omit them.

Read back the saved job: ID, profile, canonical workdir, recurring cadence/timezone,
enabled state, skill/prompt, scope, limits, delivery and next run. Check scheduler
status read-only. Correct attributable mismatches through supported updates; never
claim active scheduling when the scheduler is unavailable. Finish with those concise
settings and what was actually verified. Registration and job readback do not prove
model execution, a completed task or message delivery. Do not send a test message.
