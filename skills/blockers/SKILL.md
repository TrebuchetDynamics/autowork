---
name: blockers
description: "Use to answer queue blockers by picking options."
license: MIT
metadata:
  version: 0.1.0
  hermes:
    tags: [blockers, interview, planning, autowork]
---

# Blockers

The owner plans and answers questions; runners do the rest (owner direction,
2026-10-16). `/blockers [repo|runner name]` starts a questionnaire at once: one
question per blocked task, easiest first, each answered by picking an option, and
each answer saved as planning before the next question. `/autowork blockers` and
`/plan_with_me blockers` are the same command. It runs only when the owner starts it;
no runner or schedule invokes it, so an idle queue still costs no tokens.

It changes plans, not runners: it never starts, stops, restarts or reconfigures a
runner or service, never launches an execution or repair session, never kills a
session, and never pushes. Fixing a blocker yourself is not answering it; the runner
does the work once the plan says what to do.

## 1. Gather, read-only, then ask

Do not announce a plan or ask whether to begin: gather, then put the first question
in the same turn. Resolve the target: a path, `.` (default), or a runner name, whose
repository is the `Repository:` line of `autowork status NAME`. Then collect, without
a model call:

- The runner's questions block in `BLOCKERS.md`, between
  `<!-- pi-autowork:questions:start -->` and `<!-- pi-autowork:questions:end -->`,
  when present (TOOLSET-120-fc). Each entry already carries its type, effort,
  `unblocks` count, `Needs:` and `Answer:`.
- Without that block, the engine's view:
  `python3 <autowork>/scripts/owner_cycle.py REPO --parallel-status --json`. Use
  `roots` whose `kind` is `held`, `claim`, `outside`, `cycle` or `runner` (`blocks` is
  how many waiting tasks depend on it) and the `tasks` rows for each held task's
  `reason`, plus its worker's `report.json` blockers under
  `.git/autowork-execution/slot-data/TASK/attempt-N/`.
- Owner-maintained entries under `## Active` in `BLOCKERS.md` and tasks in TODO.md's
  `Needs decision` section.

Merge duplicates by task ID. A task the owner is already editing, or one a live
worker is running, is not a question. A technical blocker (missing input, trust
gap, failed checks) is still a question: what should the plan say the runner does
about it? With nothing blocked, say so in one line and stop.

## 2. Order: easiest first

Effort is deterministic from the kind, never guessed:

| Effort | Kinds | Typical answer |
|---|---|---|
| quick | a claim no live session holds; a dependency cycle | reopen the task or name its owner; cut one dependency |
| decision | an outside condition, a dependency not in Now/Next, `Needs decision` | decide; move the task into Now/Next, or mark it done or superseded |
| input | a worker's blocker asking for files, inputs or authorization | widen `Touches:`, supply the input, or narrow the acceptance |
| investigate | attempts exhausted on validation, report or crash | read the evidence, then rescope or split the task |

Within an effort, a larger `unblocks` count comes first, then the oldest. Open with
one line of totals (for example `7 questions: 2 quick, 2 decision, 3 input`).

## 3. One picked question per blocked task

Ask one question at a time with the host's option picker: Hermes `clarify`
(`questions=[{question, choices}]`), Claude Code `AskUserQuestion`, Codex
`request_user_input`. Without one, number the options in chat and accept a number.

- The question names the task and how many tasks wait on it, quotes the worker's or
  engine's words whole when short, and gives the one piece of evidence that matters.
- Two to four choices, each a concrete plan change in a few words (for example
  `Widen Touches: add src/feed.py`, `Split: offline part now, device check later`,
  `Supersede T-12`). The recommended choice comes first. Typed answers, `skip`
  (leave it open) and `stop` (end now) are always accepted; the picker's free-text
  row carries them.
- Do not batch questions, and do not ask what the repository already answers; the
  [grill-me](../grill-me/SKILL.md) rules apply: verify before asking, decide only
  what the owner must.

When the pick means replanning (split or rescope the task, add a task or dependency,
change acceptance), plan that one task with
[Plan With Me](../plan-with-me/SKILL.md)'s planning craft: a short round of further
picked questions about that task only, then save it. Then go to the next blocker.

## 4. Record the answer as planning

Write each answer where the queue reads it, right away:

- Edit that task's TODO.md entry: scope, `Touches:`, acceptance, `Dependencies:`,
  `Status:`, or a short dated `Owner decision:` line. Keep the entry's shape; use
  Docs Sync `goals.py` (`section`, `task`, `supersede`, `reorder`) for ledger moves.
- A claim the owner calls abandoned: set `Status: open`. A claim the owner says is
  live: leave it and note who holds it.
- An outside condition: record the decision, or the task that now owns it.
- Remove resolved owner entries from `BLOCKERS.md` `## Active`; never edit inside the
  runner's marked block, which the runner rewrites itself.

A held task re-queues itself once its entry changes (TOOLSET-120-fc); a runner
sees the plan change within seconds. Where it does not, request it after the edit
with `pi-autowork.sh --repo REPO --set-aside TASK`; the runner keeps the earlier work
on `-set-aside-N` branches.

## 5. Close out

Commit only the planning files the answers changed (TODO.md, goals.json,
TODO.archive.md, `BLOCKERS.md`) in the repository's checkout as
`docs(tasks): owner answers to blockers`, so the runner's merge is not held by
uncommitted edits. Never commit unrelated changes; do not push unless the owner asks.
Report what was answered, skipped and still open, and what each answer unblocks.
