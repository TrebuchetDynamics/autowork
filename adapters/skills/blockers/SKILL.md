---
name: blockers
description: "Answer what blocks a repository's Autowork queue: one picked option per blocked task, easiest first, saved as planning."
disable-model-invocation: true
---

# Blockers

Read the [host contract](../COMMON.md), then follow the
[blockers protocol](../../../skills/blockers/SKILL.md) in this session. Start at
once: gather read-only, then ask the first question in the same turn. Ask each
question with this host's option picker (Claude Code `AskUserQuestion`, Codex
`request_user_input`; in Pi, numbered options in chat), two to four concrete plan
changes with the recommended one first. Plan a task that needs replanning with
[Plan With Me](../plan-with-me/SKILL.md) before the next question.

It changes plans, not runners: it never starts, stops, restarts or reconfigures a
runner or service, never launches an execution session and never pushes. Hermes
CLI and profiles are not required; read the runner's `BLOCKERS.md` block or the
engine status the protocol names.
