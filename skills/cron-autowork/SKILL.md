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
and existing commit/push/live-operation limits from the full saved job, not a list
preview. Compare them with the latest explicit owner decisions and replace superseded
clauses rather than appending a contradictory grant. Bind selection to current
TODO/ledger order; a hardcoded milestone must not override a later reprioritization,
and a reorder alone changes neither cadence nor active work. Reuse existing settings
unless the user changes them. For a new job with no cadence, propose every 30 minutes and
ask for the cadence before creating it. For wall-clock schedules, establish the
timezone and report the scheduler's normalized next occurrence. Never confuse a
one-shot delay with a recurring interval. A bare invocation helps complete missing
settings; a complete create/update request authorizes that operation without another
confirmation round. Preview/read-only/“prompt only” makes no scheduler changes.

## Bind Telegram reporting independently of invocation

For a new Hermes job, default to Telegram reporting even when setup is invoked
from CLI, a web UI, another chat platform or another supported host. An explicit
user destination or no-message request wins. Preserve an existing explicit delivery
restriction (including local-only or another platform) unless the user changes it;
“respond in Telegram from anywhere” authorizes that delivery change for the matched
job. It does not authorize notifying other profiles or broadcasting to all channels.
When the selected route is local-only or a non-Telegram platform, skip the Telegram
resolution and confirmation steps; do not add a Telegram copy.

Resolve one destination in this order: the user's explicit target; the matching
job's explicit Telegram target; the invoking Telegram chat and topic; the matching
job's saved Telegram origin; then the Telegram home destination of the same verified
profile. Validate each selected target with supported destination/config discovery.
Keep the topic ID: use `telegram:CHAT_ID:THREAD_ID`, or `telegram:CHAT_ID` for a
verified non-topic chat. For home resolution, use `TELEGRAM_HOME_CHANNEL` and
`TELEGRAM_CRON_THREAD_ID` (falling back to `TELEGRAM_HOME_CHANNEL_THREAD_ID`). Read
only the selected profile's routing settings; never print bot tokens or borrow the
calling shell's unrelated profile settings. Missing or ambiguous routing needs one
focused question before creating a job that promises Telegram delivery.

Save that concrete destination in the scheduler's `deliver` field. A prose promise,
`local`, an omitted field or `origin` from a CLI/web/other-platform session does not
bind Telegram reporting. Preserve unrelated origin/context fields. Inspect
`failure_deliver` too: new jobs inherit `deliver`; when repairing explicitly requested
Telegram reporting, clear an old silent/wrong-route failure override using the
supported schema, unless the user separately requested that override. Read back
both routes. If the installed scheduler cannot represent the required route,
report the setup limitation instead of silently falling back to local output.

## Prepare one compact instruction

Read [Autowork scheduled policy](../autowork/references/scheduled-policy.md).
When installed separately, load it through the installed Autowork skill (for
example `skill_view`) and resolve helper paths from that skill's directory, not an
assumed sibling. Reuse its behavior rather than copying the entire skill into a
cron prompt. Attach
the verified Autowork skill using the installed scheduler's supported skill field;
also name it in the prompt. Set the real absolute workdir, not merely a prose path.
Keep the prompt operational, not a status diary: beyond the saved scope filter, no
current task IDs, card/run pointers, failure counts or remaining turns as policy. Those belong in
continuation receipts resolved each occurrence; stale snapshots can reopen delivered
work or override newer authority. Keep reusable recovery behavior in skills.
Use this template with resolved values; never save placeholders:

```text
Use hermes-toolset:autowork in REPOSITORY under PROFILE.
Scope: REPOSITORY_DEVELOPMENT_OR_EXACT_TASK_FILTER.
Delivery authority and exclusions: EXPLICIT_LIMITS.
Resume saved continuation and inspect actual process/workspace activity first.
TODO.md and existing goals.json own the queue; execute in the current agent session.
No Kanban lookup, historical card or native continuation/review transition is required.
For managed profile coordination, supply --profile CURRENT_PROFILE and
--state-dir VERIFIED_PROFILE_HOME/autowork to owner_cycle.py with the actual owner PID.
Resolve profile/home from verified occurrence context; never guess those values.
Integrate approved work before new discovery. Reuse checks only while inputs match.
Preserve useful candidates and live writers; delegate only when useful and authorized.
Repair attributable task/docs metadata and retry selection in this occurrence.
Use Plan For Me only for unresolved planning; save findings through Docs Sync.
For broad repository scope, replenish justified tasks when none is ready; for a
task filter, stay within that scope and its authorized prerequisites.
Preserve consumed budgets, partial work, retry history and paused jobs. A cron tick
does not grant a fresh allocation to an exhausted task. Do not edit Hermes Agent.
Follow references/cron-autoheal.md: repair this exact job managed wiring with the
installed scripts/heal-owner-cron.py and verified occurrence identity; read back.
Fix attributable Toolset faults within existing authority before the next occurrence.
Follow saved recovery outcomes; no repeated unchanged audits or planning-only loops.
Report task ID/title, implemented or integrated slice, checks, commit/publication,
next task, and the exact unresolved operation/input. Separate parent-task completion
from delivered slices. Unchanged observations are not new progress.
Return a concise nonempty status every occurrence through automatic cron delivery,
including an unchanged blocker, no eligible work or an already-running worker.
The occurrence status itself is required news: never return [SILENT] or blank output.
Report observed progress honestly; do not invent work to fill the report. Return
the final report once; do not also send it with a messaging tool.
```

This is the default report cadence for new jobs and for an explicit request to
restore reliable Telegram reports. Preserve a user's explicit changes-only/quiet
preference; replace the template's every-occurrence lines with that policy when
applicable. An inherited generic silence default is not a user quiet preference.

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
Prepare one final payload, compare it with captured scope, limits and settings,
write once and read back the exact saved prompt. Avoid cosmetic rewrites of a
healthy job; configuration churn completes no repository work.
Do not run the job immediately unless requested. After a timeout or unclear write
result, list/read back before retrying creation. If outcome remains uncertain,
report it instead of creating another job. Required fields unsupported by this
installation are a concrete setup limitation, not permission to silently omit them.

Read back the saved job: ID, profile, canonical workdir, recurring cadence/timezone,
enabled state, skill/prompt, scope, limits, delivery and next run. Check scheduler
status read-only. Correct attributable mismatches through supported updates; never
claim active scheduling when the scheduler is unavailable. Finish with those concise
settings and what was actually verified. Registration and job readback do not prove
model execution, a completed task or message delivery.

## Confirm setup in Telegram

After successful create/update and readback, send one substantive setup confirmation
to the resolved Telegram destination: profile/repository, job ID, cadence/timezone,
next run, scope/limits, paused or active state, and whether an immediate run occurred.
Invoking this writing workflow authorizes that confirmation. If this conversation
already is that exact Telegram chat/topic, use the normal reply once. From anywhere
else, use the available `send_message` tool or supported profile-scoped messaging
interface with the explicit target, then summarize its result in this conversation.
Verify that the messaging interface uses the selected profile's Telegram transport;
an unrelated host account/bot is not a substitute for an unavailable profile sender.
Inspect the tool schema; do not invent a CLI send command, forge a Telegram origin
or queue another agent turn merely to send text. This confirmation does not run the
development job. Preview/read-only/prompt-only and explicit no-message requests
send nothing. Do not send a separate “test” ping.

Retain the returned delivery receipt (`message_id` when provided). A queued send,
timeout or acceptance without delivery evidence is unverified; do not blindly resend
or claim the user received it. If messaging is unavailable or fails, say **job saved;
Telegram setup confirmation not delivered/verified**, with the exact limitation.
A confirmation receipt proves only that message, not scheduled execution or future
cron delivery. If setup failed before saving, report the failure in the invoking
conversation without sending a success confirmation.

For “it did not run/report”, inspect the existing job's last execution, saved output
and delivery error/receipt separately. Reconcile any active run before an explicitly
requested run-now through the supported scheduler; never duplicate work or resume
a paused job implicitly. Report configured, execution observed and Telegram delivery
verified as separate facts, using actual evidence rather than scheduler health alone.

For an existing Toolset-managed development job, use the bounded
[cron self-repair path](../autowork/references/cron-autoheal.md). Preserve explicit
no-write restrictions. The helper repairs managed prompt/skill wiring only; it does
not infer missing routing or startup settings. When installing a new managed job,
use `scripts/wire-owner-cron.py`'s `owner_prompt` renderer for its managed section.
Do not run the fleet updater from a single-job occurrence.
