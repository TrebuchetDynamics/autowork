---
name: blockers
description: "Use when reviewing blocked Autowork tasks and resolving missing owner decisions or inputs."
disable-model-invocation: true
---

# Blockers

Read the [host contract](../COMMON.md), then follow the
[blockers protocol](../../../skills/blockers/SKILL.md) in this session. Start at
once: gather held tasks and owner questions, apply the protocol's filter, execute
bounded authorized local recovery and verify the exact outcome. Do not stop at a
planning note when a safe repair is available. Reuse retained work, preserve live
owners, attempts, checks, privacy and publication constraints, and ask only about
genuinely missing owner decisions or inputs. Report repaired, still held, waiting
on an active owner and externally gated tasks separately. Use this host's available picker (Claude Code
`AskUserQuestion`, Codex `request_user_input` in a mode that permits it or
`request_user_input_async`; otherwise numbered options in chat), two to four concrete plan
changes with the recommended one first. Plan a task that needs replanning with
[Plan With Me](../plan-with-me/SKILL.md) before the next question.

It never starts, stops, restarts or reconfigures a runner or service, never launches
a competing execution session and never pushes. Use the existing task's supported
execution workflow only after exclusive ownership is established; preserve explicit
pauses and never mutate a slot or report to manufacture success. Questions-only and
planning-only requests do not execute; read-only requests neither execute nor write.
Hermes CLI and profiles are not required; always inspect both the runner's questions
and engine held-task rows, including tasks with no question or dependent.
