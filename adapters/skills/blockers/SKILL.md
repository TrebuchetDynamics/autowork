---
name: blockers
description: "Use when reviewing blocked Autowork tasks and resolving missing owner decisions or inputs."
disable-model-invocation: true
---

# Blockers

Read the [host contract](../COMMON.md), then follow the
[blockers protocol](../../../skills/blockers/SKILL.md) in this session. Start at
once: gather read-only, apply its filter and existing authorization, then ask only
about genuinely missing owner decisions or inputs. Record routine planning repairs
without asking who should integrate an idle reviewed candidate; retain all candidate,
verification, privacy and publication constraints. If no question remains, report
the repairs and pending execution. Use this host's available picker (Claude Code
`AskUserQuestion`, Codex `request_user_input` in a mode that permits it or
`request_user_input_async`; otherwise numbered options in chat), two to four concrete plan
changes with the recommended one first. Plan a task that needs replanning with
[Plan With Me](../plan-with-me/SKILL.md) before the next question.

It changes plans, not runners: it never starts, stops, restarts or reconfigures a
runner or service, never launches an execution session and never pushes. Hermes
CLI and profiles are not required; read the runner's `BLOCKERS.md` block or the
engine status the protocol names.
