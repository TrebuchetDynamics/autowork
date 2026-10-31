---
name: autowork
description: "Implement and verify ready repository tasks."
version: 0.28.2
author: Hermes Agent
platforms: [linux, macos]
metadata:
  hermes:
    tags: [autonomy, planning, backlog, verification]
---

# Autowork

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Execute a bounded useful slice in the current agent session. `tasks/` is the one
task store: `tasks/items/<ID>.md` owns each task's intent, scope, acceptance,
dependencies, section, rank and status; `tasks/goals/<ID>.md` owns goals; and
`tasks/evidence/<ID>.toml` holds the receipt of a verified close. Every edit goes
through `autowork tasks`. A repository needs no Hermes setup or extra public
tracking file. No Kanban lookup, card, board, assignee, native
continuation API or native review transition is a prerequisite, including recovery
of old work. Historical cards are not leases. Preserve their evidence without
querying, importing, releasing, resetting or deleting them.

Read repository instructions and accepted decisions first. A ready task needs no
planning prepass. Decide reversible details, implement, test, repair and close out
without reconfirmation. Delegate through host-native tools only when useful and
authorized; no mandatory worker launch. Select a supporting skill only for a
concrete method gap; use [engineering guidance](../shared/ENGINEERING-CYCLE.md)
only for that gap. Planning resolves consequential missing choices through
[Plan For Me](references/backlog-planning.md); it does not become a second approval
loop. Apply [Ponytail](references/ponytail.md) within the existing implementation and
review step. Keep Hermes Agent unchanged.

## Select and execute

1. **Step 0 — reconcile, never fingerprint-exit.** Reconcile once: inspect current
   workspace/Git changes, actual process identity and activity, existing candidates,
   checks and required reviews. Resume the saved continuation before discovery;
   finish authorized integration and review rework first. Historical cards cannot
   veto execution. Do not overlap a live writer or assume a stale PID proves release.
   Disable change-only fingerprint monitors. CONTINUE selection after closeout when
   caller limits permit. A completed slice is not itself a stop condition under continuation authority;
   default and explicit caller stops still apply.
2. **Use runnable backlog first; otherwise run the docs-sync fallback.** Selection
   reads `tasks/` at the base commit: section (Now before Next), then rank, gated by
   goal focus, priority and dependencies. `autowork tasks list` shows the order and
   `autowork tasks why ID` explains a pick or a skip. A record missing contract fields
   is a visible draft, never selected. Reconcile inconsistent source evidence
   without inventing acceptance or ownership.
   Do not run a docs-sync prepass for a usable backlog task.
   Named --tasks/--plan scope stays exact. A task Autowork records or
   repairs carries `touches` from the inspected seam
   ([task rules](../shared/TODO-WORKCENTER.md)), so parallel workers can run it beside
   others. Do not create a second board. A repository without `tasks/` selects nothing;
   `autowork tasks prepare` (Docs Sync) converts it, or records the request so the
   runner drains in-flight work and converts it itself.
3. **Prepare only missing inputs, then implement.** Derive a short contract from
   the task's objective, scope/exclusions, acceptance/checks, dependencies and sources.
   Keep source/candidate identity, actual owner/session and explicit limits in
   private evidence. One coherent delivery batch may include
   connected code, tests and docs; do not split it merely by file.
   The engine is not part of this skill: it ships with pi-autowork, in
   `<toolset>/pi-autowork/engine/`, where `<toolset>` is the installed Autowork toolset
   (the Pi package `~/.pi/agent/git/github.com/TrebuchetDynamics/autowork`, or a clone).
   The default is one composed command for selection and coordination:

   ```sh
   python3 <toolset>/pi-autowork/engine/owner_cycle.py /absolute/repo \
     --apply --owner-pid ACTUAL_SESSION_PID
   ```

   Resolve ACTUAL_SESSION_PID from the real persistent current coordinator process;
   never use a guessed PID or a transient shell that exits before work starts.
   The process must be task-scoped: verify its role and birth identity before
   invoking `--apply`. A shared gateway/server ancestor is not the owner; a common
   parent does not identify the current conversation. Keep inspection and mutation in
   separate calls or a conditional branch that refuses an invalid owner; printing
   an invalid role before an unconditional mutation is not a guard.
   `EXECUTE` returns a contract for this session to implement; it is not proof of
   implementation or a background launch. Moving a task is editing its rank
   (`autowork tasks move ID up|down` or `autowork tasks field ID rank N`); there is
   no separate recorded order. See [the exact interface](references/owner-cycle.md)
   for claims, bounded argv execution, release and source-bound receipts.
4. **Implement and verify.** Repair routine non-privileged environment failures,
   iterate on failing tests, and retain failure evidence. Required acceptance tests,
   independent review where required and source freshness still apply. Reuse checks
   only for matching inputs when policy allows; rerun changed-input and mandatory
   gates. A missing required review holds completion, not unrelated authorized work.
   Follow
   [partial delivery and the critical path](references/iteration-and-decisions.md#partial-delivery-and-the-critical-path).
5. **Close out.** Assess doc impact from the verified diff, Acceptance and actual docs:
   record `not_needed` with reason, `updated` with paths/readback/checks, or `pending`
   with the gap and resume action. Follow the shared [scoped documentation closeout](../shared/ENGINEERING-CYCLE.md#one-canonical-backlog-one-executor-one-closure-owner):
   resolve bundled Docs Sync in this host and run Maintain only for a concrete delta.
   Workers update in-scope component docs and report shared-doc gaps for the
   coordinator/DOCS-MAINTAINER. Preserve
   implementation and pending evidence on interruption; never replay implementation
   or launch work after a stop or pause to finish docs.
   Commit attributable verified paths locally unless forbidden.
   Use ordinary Git, repository review and integration policy. Inspect fresh target
   state and serialize canonical writes; preserve unrelated dirty work. Never push,
   deploy, publish, spend money, place trades or broaden live authority without its
   explicit scoped authorization. Report actual commit/review/integration separately.
   For worktree-backed work, finish [worktree closeout](references/worktree-closeout.md):
   verify integration on the canonical `main` or `master`, then remove the task's
   worktree with `<toolset>/pi-autowork/engine/worktree_closeout.py CANONICAL --worktree PATH --apply`.
   Every `--apply` task claim also removes earlier integrated, clean, unused
   worktrees and reports the rest under `worktree_cleanup`. Preserve active, dirty,
   unmerged or recovery-bearing worktrees; report integration/cleanup pending.
   Close a task only after verified acceptance: the engine's verified close writes
   `status = "done"` plus the receipt in `tasks/evidence/<ID>.toml` in one commit, and
   replay is a no-op. A close without the engine uses `autowork tasks done ID
   --evidence TEXT`. An existing `TODO.archive.md` is frozen history, never written.
   Read-only runs do not write.

## Ownership, limits and continuation

Use local repository locks and isolated worktrees where concurrent writers need
isolation; one writer per workspace. Before adopting idle work, inspect actual
process liveness, workspace changes, source/candidate provenance and check receipts.
Advisory locks cannot exclude manual writers who ignore them or coordinate different
hosts; an enabled same-repository cron run may also be writing. Preserve useful
candidates; do not kill workers or delete worktrees. A `Held by:` note prevents
selection. Under the [task-hold policy](../shared/TODO-WORKCENTER.md#task-holds-require-an-explicit-user-request),
only an explicit user request permits adding or renewing that note with
`autowork tasks hold`. Use supported execution leases and workspace locks for
ordinary ownership instead. Preserve existing holds; `autowork tasks release ID`
lifts only a reconciled hold. An open session or a bare PID is not
live ownership: verify the executor's identity and recent activity before releasing
an abandoned claim, keeping its work and any explicit pause. Only typed fields
(`live`, `resources`, `ownership`) grant authority; a note never does. Workers never
edit `tasks/`: a worker commit that does is held and never merged. Before requeueing, check the executor can work where the task's
files live. Never end a turn on a bare claim: leave the task open with its Next
action, a current `Held by:` note, or the explicit pause, so no claim outlives the
session that made it. A live writer does not freeze priority: an owner's rank or
section edit applies to the next selection without interrupting current work or
faking a dependency; report it only after `autowork tasks list` agrees.

Work in the canonical checkout by default; for live sessions, `BUSY`/`isolate`, integration
and execution leases follow [canonical checkout and leases](references/owner-cycle.md#canonical-checkout-sessions-and-leases).

Caller scope and saved stop/batch limits control continuation. Default: one useful
slice including recovery and closeout. Explicit stops win. Apply
[mode precedence](references/iteration-and-decisions.md#mode-precedence).
Autowork has no token, cost or time budgets: model usage and cost are measured
(`runs.jsonl`), never a reason to stop, and timeouts only bound single runs. A task
that still declares a budget, allowance or ceiling is not held for it: record its
usage as evidence and keep working to its acceptance. Spending money (paid services,
purchases) remains an authority only the owner grants.

A held or blocked task goes to [Plan For Me](../plan-for-me/SKILL.md) in the same
run, before reporting, and Plan For Me must **fix or skip** it. Fix: choose a
reversible change within the delegated scope, record it as the planner's call and
implement it now. Skip: split the blocked acceptance into its own open task naming
the exact missing input (never waived), then continue with the next ready task in
scope. Report a blocker again only when it is a genuinely unavailable external input
or authority (credentials, money, deployment, legal or owner approval), and only
once; never repeat an unchanged held report. Ask only for
material missing decisions or authority; never repeat a permission question already
answered. Preserve actual pending-approval requests; do not bypass them through a
new tool, session or credential.

Run discovery only when no usable task remains. Under broad repository authority,
[repository maintenance](references/repository-maintenance.md) inspects a bounded
seam, records a justified task with `autowork tasks add` and executes it in the same occurrence.
Named-only jobs cannot widen scope. Empty queues, green tests or unchanged HEAD
are not proof of exhaustion; record `work_search` evidence and rejected candidates.
This policy is not a runtime guarantee of progress. No fabricated busywork.

## Parallel workers (opt-in)

Only when the caller asks for it, run `owner_cycle.py REPO --apply
--parallel [N] --owner-pid PID`: it starts headless workers, one task each in
its own worktree. `touches` only orders tasks, never holding one; `resources` and
dependencies keep tasks apart.
Loop `--wait --timeout S`, review each `report.json`, `--integrate TASK
--timeout S --run CHECK...` (`--run` last), `--parallel-close TASK`, commit the
coordinator files, and refill with `--apply --parallel`; release only after no slot
is left to integrate or close. Workers never select, merge, close or push. On
`SEQUENTIAL_FALLBACK`, run the returned contract normally. Follow [parallel workers](references/parallel-workers.md).

## Owner blockers

`/autowork blockers [repo|name]` is [`/blockers`](../blockers/SKILL.md): routine planning
repairs and genuine owner answers become planning, never execution.
Tasks may read runners (`autowork ls|status`), never start, stop or reconfigure them.

## Scheduled work and reporting

Autowork does not create schedules. Existing jobs use [scheduled policy](references/scheduled-policy.md)
and [exact-job self-repair](references/cron-autoheal.md). Preserve pauses, IDs, cadence,
model, delivery, task filters and publication limits. A paused job cannot resume
itself. Managed profile invocations must pass `--profile CURRENT_PROFILE` and
`--state-dir VERIFIED_PROFILE_HOME/autowork` to owner_cycle.py alongside the actual
owner identity. Resolve both from verified occurrence context so scoped helper
updates can detect and preserve the active coordinator. Do not guess a profile home.
Scope retained in an old prompt survives migration; obsolete card-only
prerequisites do not.

Report per [dispatch and reporting](references/dispatch-and-reporting.md): task ID
and title, concrete change, actual checks/review, local commit/integration/publication,
next task and precise blocker. A selected contract, completed session or checkbox is
not product acceptance. Never claim live qualification or Telegram delivery from
offline fixtures. Honor every-occurrence reporting; otherwise exactly `[SILENT]`
is allowed only after reconciliation and required work search find no reportable delta.
Interactive updates follow
[dispatch and reporting](references/dispatch-and-reporting.md#interactive-updates).

## Reference map

Active guidance: references/repository-stages.md, references/iteration-and-decisions.md,
references/owner-cycle.md, references/scheduled-policy.md, references/cron-autoheal.md,
references/repository-maintenance.md, references/dispatch-and-reporting.md,
references/delivery-batches.md, references/accepted-plan-execution.md,
references/whole-spec-execution.md, references/backlog-planning.md,
references/parallel-workers.md, references/ponytail.md, references/discovery.md,
references/profile-feedback.md.

Historical native-card evidence, not instructions or prerequisites:
references/blocker-recovery.md
references/blockers-and-history.md
references/budget-controller-proof.md
references/controller-bridge-proof.md
references/handoff.md
references/maintenance.md
references/native-containment-proof.md
references/state-and-recovery.md
references/upstream-goal-selection.md
references/historical-owner-cycle.md
## Boundaries

- Not planning; use `/plan-with-me` or `/plan-for-me`.
- Not open-ended improvement; use `/autonomous-codebase-improver`.
- Not an architecture review; use `/improve-codebase-architecture`.
- Not publication by default; use `/git-commit-push` when the request includes push.

**Done when:** one ready task's acceptance is met, its checks ran, and it is closed or reported with the exact blocker.
