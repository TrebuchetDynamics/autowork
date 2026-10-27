---
name: cron-autowork
description: "Create or update recurring Autowork execution with an available scheduler, or prepare a schedule specification when the host cannot schedule."
disable-model-invocation: true
---

# Cron Autowork

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md) and the shared
[scheduling workflow](../../../skills/cron-autowork/SKILL.md).
Apply its repository/scope binding, duplicate detection, paused-state preservation,
prompt template and readback rules using this host's actual
scheduler. Use this host's Autowork skill ID in the prompt; do not require a Hermes
profile, CLI, Kanban or gateway on Codex/Pi. Omit inapplicable Hermes identity
wording from the template and bind the native workspace and skill settings instead.
Never emulate those identities. Unsupported execution binding is a setup limitation.

Honor the shared Telegram delivery and setup confirmation contract when Telegram
reporting is requested or the selected Hermes backend supplies that default. Bind
the explicit destination independently of this host's invocation channel. Use an
available authorized messaging integration for the confirmation, and retain its
receipt. If that integration is unavailable, report **setup confirmation not delivered**;
do not substitute a local reply as proof of Telegram delivery. If the scheduler
cannot support the required Telegram route, report **not scheduled** for a new job
and preserve an existing job instead of silently changing its destination.

If no scheduler is exposed, prepare the concrete prompt, repository, cadence,
timezone, scope and delivery specification and report **not scheduled**. Do not
install another agent, write a system crontab, create a background loop or claim
the current session will continue unattended. If Hermes scheduling is explicitly
requested and available, verify its selected profile and use that supported backend.
Preview/read-only requests make no changes. Creating a job is not permission to
run it immediately.
