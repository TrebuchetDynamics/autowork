---
name: blockers
description: "Use to resolve blocked tasks: ask only what the owner must."
license: MIT
metadata:
  version: 0.2.0
  hermes:
    tags: [blockers, interview, planning, autowork]
---

# Blockers

`/blockers [repo|runner name]` resolves held tasks and owner questions together.
Apply established answers, repair authorized technical causes and verify progress,
then ask only for unresolved owner
decisions or unavailable inputs, easiest first. Save each resolution before moving
on. `/autowork blockers` and `/plan_with_me blockers` are the same command.
It runs only when the owner starts it; no runner or schedule invokes it, so an idle
queue still costs no tokens.

It never starts, stops, restarts or reconfigures a runner or service, never launches
a competing execution or repair session, never kills a session, and never pushes.
Execute authorized local recovery through the existing task's supported execution
workflow when exclusive ownership is established; do not edit a live worker or
duplicate its checks. An invocation authorizes bounded local blocker repair, not
unrelated implementation, live operations, credentials or publication. Explicit
questions-only, planning-only and read-only requests execute nothing; read-only also
writes nothing. Updating an already authorized plan needs no new owner decision.

## 1. Gather and filter

Do not announce a plan or ask whether to begin: gather and filter, then put the
first genuine question in the same turn if one remains. Otherwise report the
planning repairs and remaining execution work without inventing a question.

Resolve the target: a path, `.` (default), or a runner name, whose repository is the
`Repository:` line of `autowork status NAME`. The runner's questions live in its
session worktree, which can be ahead of the main checkout; read them there, and save
answers in the main checkout, which the runner merges into its session. Always inspect
both the questions and engine task states: an empty questions block does not mean no
held work. Initial discovery is without a model call:

- The runner's questions block in `BLOCKERS.md`, between
  `<!-- pi-autowork:questions:start -->` and `<!-- pi-autowork:questions:end -->`,
  when present (TOOLSET-120-fc). Each entry already carries its type, effort,
  `unblocks` count, `Needs:` and `Answer:`.
- The engine's view even when the questions block exists:
  `python3 <autowork>/scripts/owner_cycle.py REPO --parallel-status --json`. Use
  `roots` whose `kind` is `held`, `claim`, `outside`, `cycle`, `runner` or `contract`
  (a TODO/index mismatch: without it a metadata-blocked queue seems to have no
  questions) and the `tasks` rows for each affected task's `reason`, plus its
  worker's `report.json` blockers under
  `.git/autowork-execution/slot-data/TASK/attempt-N/`. `blocks` counts waiting tasks
  that depend on the root; check which IDs it counts, since it can include the root.
  Inspect every held task row, including holds with zero dependents and no root entry.
  A failed status read is unavailable evidence, not an empty queue; fall back to
  current slot identities and latest attempt reports without inventing live counts.
- Owner-maintained entries under `## Active` in `BLOCKERS.md` and tasks in TODO.md's
  `Needs decision` section. `Q-ACCEPT-GOALS`, between `<!-- docs-sync:accept-goals:start -->`
  and its end marker, asks to accept a first drafted backlog: on the owner's yes run
  `python3 <docs-sync>/scripts/goals.py accept REPO`; for a change, edit
  `docs/tasks/proposed-goals.json` or the goal's section and run `goals.py propose` again.

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
  repair the cause and verify the supported continuation, not merely another Next
  action in the task. A failed check, missing
  receipt or pending local integration does not by itself need a user choice.
- **Idle candidate awaiting delivery:** verify actual writer/session activity and
  candidate identity. When no live writer owns it and local integration is already
  authorized, perform the supported integration-only continuation with the existing
  execution owner, reusing the candidate. Keep valid candidate checks, require verification
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
recommended option only, never every alternative or permission to deploy. A task
that only waits on unfinished dependencies is not a question: a release task waiting
for features is not a request to approve publication. Waiting for overlapping files
or a running dependency is scheduling, never a blocker.

Resolve each runner question in the form the runner recognizes, so it leaves the
block on the next cycle; a question you only filtered out keeps showing as "Waiting
on you". A changed entry ends a held-task question, `Held by:` a claim question. A
task in `Needs decision` with a dated `Owner decision:` line is an answered
outside dependency: the runner stops asking about it, and its dependents wait with
it (`wait for deferred <ID>`). Dependents may stay in Now/Next; no dependency needs
to be dropped and no separate answer field is required.

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

When the owner defers a physical or live check, keep its criteria and access limits.
If that check still stops independent offline work, ask separately whether offline
development may go ahead before the final human acceptance. The answer can change
admission dependencies; it never supplies a test result, product acceptance or
publication authority, and never turns an unobserved check into a pass.

## 4. Resolve and verify each item

For each technical hold, keep the same task, candidate and cumulative budgets.
Inspect its latest attempt, actual writer/session activity and exact qualification
inputs; fix the smallest in-scope local cause using the existing Autowork execution
workflow. Reuse retained code and valid checks, repair local metadata/scope omissions
within accepted intent, and rerun only missing or invalidated required checks. Keep
required full-gate/review evidence, source bindings and negative safety assertions.
Never patch a report or directly clear a slot/lease to manufacture progress.

Read back the exact task state and question after the repair. A saved answer is not
a removed hold; missing terminal evidence stays unqualified. If a live owner must
consume the change, observe its acknowledgement or name the precise pending
operation and owner. Do not repeatedly append the same advice or edit metadata just
to trigger fresh implementation. An unavailable owner, real resource wait or external
prerequisite can remain held: retain its evidence and continue independent repairs.
Escalate only unavailable input, consequential intent or ungranted authority—not
routine implementation choices. Do not promise every hold can be removed safely.

Write each answer or supported planning repair where the queue reads it, right away.
An approved clerical index correction is planning: apply it through Docs Sync and
record it in the task. An answer supplies only the selected intent or authority;
execute its local repair only within the invocation's scope and ownership rules.
It never implicitly authorizes service migration or broader live operations.

- Edit that task's TODO.md entry: scope, `Touches:`, acceptance, `Dependencies:`,
  `Status:`, or a short dated `Owner decision:` line. Keep the entry's shape; use
  Docs Sync `goals.py` (`section`, `task`, `supersede`, `reorder`) for ledger moves.
- An abandoned claim established by fresh activity checks or an explicit owner
  release: set `Status: open` only within existing task authority and clear the
  ownership prose, keeping acceptance, dependencies, candidate references, partial
  delivery evidence and pending checks; check the TODO body and the index agree.
  Successors are not unlocked by this: they still need the task's acceptance. A live
  claim stays with its current worker; record that answer as one line in the entry,
  `Held by: <who or what>; until <YYYY-MM-DD>`, which ends the runner's claim question
  until that date. An entry with a current `Held by:` line is answered, not open.
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
and never start a paused runner to consume an answer.
Retries, restarts and `pi-autowork.sh --set-aside TASK` belong to the runner's own workflow;
use its supported handoff rather than manual state mutation. When it cannot consume
the repair safely, report the precise remaining execution condition instead. A kept branch
does not prove a fresh worker received that candidate: name it in the task's
`Next action:` so the next attempt restores it instead of reimplementing. Never
rewrite a running worker's contract.

## 5. Close out

Commit only attributable, verified planning or local repair files, including their
tests and affected docs, through the repository's scoped local-commit workflow.
Use `docs(tasks): owner answers to blockers` for planning-only changes, so the
runner's merge is not held by uncommitted edits. Where those files hold other uncommitted planning, stage only the
answered tasks' hunks and their ledger rows, check the staged diff, and leave the
rest as it was. Never commit unrelated changes. This workflow never pushes; route
separately requested publication through Git Commit Push with its existing authority.
Validate a changed index and read the engine status before reporting. Keep apart:
answer saved, blocker removed, picked up by the runner, worker running, and work
done; a successor can still wait on the same unfinished prerequisite. Planning
readiness is not completed integration.

## 6. Report to the owner

The owner reads this on a phone. Write for them, not for the runner:

- **First line, the verdict:** how many questions need them now, and what the runner
  shows them, read fresh (`autowork status NAME`, with its time). The two agree: when
  the runner still lists a question this pass resolved, say it leaves on the runner's
  next cycle; when one stays because nothing you may record removes it, say so and why.
- **Then three groups, one plain line per task:** needs you (the question), the runner
  handles it (technical recovery, a retry, a review), and waits on other work
  (dependencies, overlapping files, a deferred task). Leave out empty groups.
- Plain words: what the task is for and what happens next. No commit hashes, slot or
  receipt terms, or internal roles (candidate, coordinator, combined source) unless
  the owner asks; a repair is one line saying what changed.
- When the runner's view is older than the checkout (a dependency it waits on is
  already done), that is the runner's to catch up, not a question; say it in one line.
