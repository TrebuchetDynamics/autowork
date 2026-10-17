---
name: blockers
description: "Use to resolve blocked tasks: ask only what the owner must."
license: MIT
metadata:
  version: 0.1.3
  hermes:
    tags: [blockers, interview, planning, autowork]
---

# Blockers

`/blockers [repo|runner name]` reviews the blocked queue at once. Apply established
answers and evidence-backed planning repairs, then ask only for unresolved owner
decisions or unavailable inputs, easiest first. Save each resolution before moving
on. `/autowork blockers` and `/plan_with_me blockers` are the same command.
It runs only when the owner starts it; no runner or schedule invokes it, so an idle
queue still costs no tokens.

It changes plans, not runners: it never starts, stops, restarts or reconfigures a
runner or service, never launches an execution or repair session, never kills a
session, and never pushes. The owner supplies product intent and genuinely missing
authority; the existing runner performs technical recovery and integration.
Updating an already authorized plan needs no new owner decision.

## 1. Gather and filter

Do not announce a plan or ask whether to begin: gather and filter, then put the
first genuine question in the same turn if one remains. Otherwise report the
planning repairs and remaining execution work without inventing a question.

Resolve the target: a path, `.` (default), or a runner name, whose repository is the
`Repository:` line of `autowork status NAME`. The runner's questions live in its
session worktree, which can be ahead of the main checkout; read them there, and save
answers in the main checkout, which the runner merges into its session. Then collect,
without a model call:

- The runner's questions block in `BLOCKERS.md`, between
  `<!-- pi-autowork:questions:start -->` and `<!-- pi-autowork:questions:end -->`,
  when present (TOOLSET-120-fc). Each entry already carries its type, effort,
  `unblocks` count, `Needs:` and `Answer:`.
- Without that block, the engine's view:
  `python3 <autowork>/scripts/owner_cycle.py REPO --parallel-status --json`. Use
  `roots` whose `kind` is `held`, `claim`, `outside`, `cycle`, `runner` or `contract`
  (a TODO/index mismatch: without it a metadata-blocked queue seems to have no
  questions) and the `tasks` rows for each affected task's `reason`, plus its
  worker's `report.json` blockers under
  `.git/autowork-execution/slot-data/TASK/attempt-N/`. `blocks` counts waiting tasks
  that depend on the root; check which IDs it counts, since it can include the root.
- Owner-maintained entries under `## Active` in `BLOCKERS.md` and tasks in TODO.md's
  `Needs decision` section.

### Filter before asking

Merge duplicates by literal task ID and read the current task, decisions, repository
policy and candidate evidence. A generated `USER_DECISION` label or a worker's request
for approval is evidence to examine, not proof that a human decision is needed. A
question can outlive its cause: compare it with the current task state and the latest
attempt's report (a newer scope-validation failure supersedes an older missing-input
report). Exclude retired tasks, released claims and settled deferrals: a cached
worker reason can describe an older checkout. When live status cannot be read, use
retained reports with current queue evidence and say how fresh they are. Count and
sort what remains programmatically, and treat an `unblocks` count as the notice's
figure, not measured impact.

- **Established answer or routine recovery:** use existing authorization. Inspect
  repository/session facts yourself. Preserve the agreed scope and acceptance;
  record the remaining technical work for the runner. A failed check, missing
  receipt or pending local integration does not by itself need a user choice.
- **Idle candidate awaiting delivery:** verify actual writer/session activity and
  candidate identity. When no live writer owns it and local integration is already
  authorized, record an integration-only continuation for the current eligible
  runner, reusing the candidate. Keep valid candidate checks, require verification
  against the integrated code, preserve saved settings and private data, and retain
  no-push/deploy/package-delivery exclusions. Do not ask “Pi or this session?” or
  ask permission to reuse the reviewed fix. Do not label this an owner decision or
  mark delivery complete. Separate genuine live qualification still pending.
- **Live or uncertain ownership:** leave live work and claims alone. A historical
  ACTIVE/in_progress label alone proves neither activity nor abandonment. If activity
  cannot be established, retain the hold, identify the missing evidence, and continue
  with independent entries. Ask only for information unavailable through inspection;
  never offer an uninformed ownership transfer as the recommended answer.
- **Real owner decision/input:** ask when missing product intent, a scope/acceptance
  change, unavailable external input or ungranted operation authority changes what
  can proceed. State that specific gap. Preserve explicit pauses, cancellations and
  task-specific restrictions; routine local authority does not revoke them.
  Conditional recovery permission ("retry if it crashed") does not establish that the
  condition holds; keep the task held until it is verified.

Reuse the owner's latest answers, from this conversation and the queue. An item
the owner deferred is still open work but not an unanswered question; do not ask to
reconfirm it because it remains under `Needs decision`. A brief approval accepts the
recommended option only, never every alternative or permission to deploy.

A questions-only/read-only invocation records proposed repairs in chat rather than
editing files. With no genuine questions left, report what was reconciled and what
still awaits execution. Do not turn “reuse, verify, preserve privacy, no push” into
separate approvals: those are constraints to carry into the plan.

## 2. Order: easiest first

Order only the questions that survive filtering. A generated effort/kind label
does not override that filter:

| Effort | Kinds | Typical answer |
|---|---|---|
| quick | a narrow unresolved choice after inspecting dependencies | choose between two valid dependency plans |
| decision | an outside condition, a dependency not in Now/Next, an unanswered `Needs decision`, a contract mismatch | decide placement or disposition; reconcile the plan without starting work |
| input | a worker's blocker asking for files, inputs or authorization | widen `Touches:`, supply the input, or narrow the acceptance |
| investigate | evidence shows recovery needs a new scope or acceptance decision | choose the supported scope change |

Within an effort, a larger `unblocks` count comes first, then the oldest. Open with
one line of totals (for example `7 questions: 2 quick, 2 decision, 3 input`).

## 3. One picked question per unresolved decision

Ask one question at a time with the host's option picker: Hermes `clarify`
(`questions=[{question, choices}]`), Claude Code `AskUserQuestion`, Codex
`request_user_input` when available in the current mode, or
`request_user_input_async` during active work. Use only tools exposed by the host.
Without an available picker, number the options in chat and accept a number.

- The question names the task and how many tasks wait on it, quotes the worker's or
  engine's words whole when short, and gives the one piece of evidence that matters.
- Two to four choices, each a concrete plan change in a few words (for example
  `Widen Touches: add src/feed.py`, `Split: offline part now, device check later`,
  `Supersede T-12`). The recommended choice comes first. Typed answers, `skip`
  (leave it open) and `stop` (end now) are always accepted; the picker's free-text
  row carries them.
- One shared decision can cover several named tasks; apply its answer to each
  within that scope instead of asking again. Preserve earlier answers across turns.
  Do not batch unrelated questions, and do not ask what the repository already answers; the
  [grill-me](../grill-me/SKILL.md) rules apply: verify before asking, decide only
  what the owner must.

When the pick means replanning (split or rescope the task, add a task or dependency,
change acceptance), plan that one task with
[Plan With Me](../plan-with-me/SKILL.md)'s planning craft: a short round of further
picked questions about that task only, then save it. Then go to the next blocker.

## 4. Record the answer as planning

Write each answer or supported planning repair where the queue reads it, right away.
An approved clerical index correction is planning: apply it through Docs Sync and
record it in the task. No answer is permission to start the task, migrate a service
or launch a repair during the interview.

- Edit that task's TODO.md entry: scope, `Touches:`, acceptance, `Dependencies:`,
  `Status:`, or a short dated `Owner decision:` line. Keep the entry's shape; use
  Docs Sync `goals.py` (`section`, `task`, `supersede`, `reorder`) for ledger moves.
- An abandoned claim established by fresh activity checks or an explicit owner
  release: set `Status: open` only within existing task authority and clear the
  ownership prose, keeping acceptance, dependencies, candidate references, partial
  delivery evidence and pending checks; check the TODO body and the index agree.
  Successors are not unlocked by this: they still need the task's acceptance. A live
  claim stays with its current worker.
- Retirement without completion: keep the original contract in append-only history
  and use the repository's non-executable cancellation form. With no cancelled state
  in the index, use open/`Needs decision` with an explicit CANCELLED gate, never
  done, and check `goals.py next REPO --json` excludes it.
- Rework within the same task keeps its ID, acceptance and the old candidate and
  report as history; the runner works from current sources, never restores the old
  snapshot or rewrites a failed report into a pass.
- An outside condition: record the decision, or the task that now owns it.
- Remove resolved owner entries from `BLOCKERS.md` `## Active`; never edit inside the
  runner's marked block, which the runner rewrites itself.

A running runner reconsiders a held task once its entry changes (TOOLSET-120-fc),
usually within seconds. Observe that in `autowork status NAME`; do not promise it,
and never start a paused runner to consume an answer. Retries, restarts and
`pi-autowork.sh --set-aside TASK` belong to the runner's own workflow, not to this
questionnaire; when a change was not picked up, report that instead. A kept branch
does not prove a fresh worker received that candidate: name it in the task's
`Next action:` so the next attempt restores it instead of reimplementing. Never
rewrite a running worker's contract.

## 5. Close out

Commit only the planning files the answers or supported repairs changed (TODO.md, goals.json,
TODO.archive.md, `BLOCKERS.md`) in the repository's checkout as
`docs(tasks): owner answers to blockers`, so the runner's merge is not held by
uncommitted edits. Where those files hold other uncommitted planning, stage only the
answered tasks' hunks and their ledger rows, check the staged diff, and leave the
rest as it was. Never commit unrelated changes. This workflow never pushes; route
separately requested publication through Git Commit Push with its existing authority.
Report what was reconciled without questions, answered, skipped and still open,
and what each resolution unblocks. Validate a changed index and read the engine
status before reporting. Keep apart: answer saved, blocker removed, picked up by the
runner, worker running, and work done; a successor can still wait on the same
unfinished prerequisite. Planning readiness is not completed integration.
