---
name: autowork
description: "Default coordinator for authorized repository development: select tasks, execute, verify and close out; call supporting skills only for a concrete need."
version: 0.25.0
author: Hermes Agent
platforms: [linux, macos]
metadata:
  hermes:
    tags: [autonomy, planning, backlog, verification]
---

# Autowork

First apply [repository-stage preparation](references/repository-stages.md), then
use the execution and completion rules below.
Local recovery needs no external owner: [recovery](references/owner-cycle.md).
Unresolved planning invokes [Plan For Me](references/backlog-planning.md),
updates TODO.md and retries execution; never wait for the user to invoke it.

## When to use

Default /autowork hands off one bounded native goal worker (100 turns by default; explicit 50 per invocation).
New cards stop automatic failure retries; continuation must preserve cumulative
usage and cannot reset an exhausted allocation. See [handoff budget](references/handoff.md#turn-allocation-across-attempts).
Scope it as a [coherent delivery batch](references/delivery-batches.md), not one card
per file. Decide routine scope/order/check choices and continue authorized closeout.
Give workers the selected task, accepted decisions, scope, checks and completion
rules. A clear task needs no supporting skill. For a concrete method gap or explicit
protocol request, select one technique through [engineering](../engineering/SKILL.md);
consult [the engineering cycle](../shared/ENGINEERING-CYCLE.md) only when routing
is unclear. Autowork owns workflow authority; protocols add no separate planning,
approval or review loop. Preserve explicit user methods and required checks.
Apply [Ponytail's smallest complete change method](references/ponytail.md) to
implementation choices and the existing review step. Reuse concrete decisions
and evidence; load the verified skill for material choices, not another audit loop.
Does not create recurring jobs; existing authorized cron jobs may invoke it.

## Mode precedence

Only explicit whole-spec requests use `references/whole-spec-execution.md` instead of picker selection/stop rules; retain all safety, ownership, admission, budgets and review gates below.

For scheduled runs load [scheduled policy](references/scheduled-policy.md).
Owner consultations: `references/profile-feedback.md`.

Apply [TODO-first planning](../shared/TODO-WORKCENTER.md).

At verified closeout and reconciliation of completed bodies, align TODO and ledger
status, then run `python3 "<skills-root>/docs-sync/scripts/goals.py" archive <repo>`.
This automatically moves closed bodies to `TODO.archive.md` or the existing archive;
do not wait for a Docs Sync job. Keep ledger evidence. Without goals.json, inspect
checks and pass verified closed IDs with `archive <repo> --verified-tasks ID1,ID2`.
Report retained conflicts; read-only runs skip this write. Follow the
[archive contract](../docs-sync/references/todo-archive.md).

## Operating priorities

1. **Step 0 — reconcile, never fingerprint-exit.** Resolve workspace instructions,
   human decisions, journal and live ownership before selecting.
   Reconcile once, select usable backlog, check ownership/source freshness, hand off.
   Run discovery only when no usable task remains: [maintenance](references/repository-maintenance.md).
   Disable change-only fingerprint monitors; only `autowork_gate.py` may skip a tick
   while this profile's own card is running or ready and nothing finished.
   Preserve schedule, model, delivery and enabled state.
   Reconcile new terminal results, then CONTINUE selection in the same occurrence.
   A completed card is not a stop condition. A genuinely live worker wins: reconcile
   its exact run; never enqueue overlapping work or steal its lease.
   Resume the saved continuation before discovery. Finish pending integration,
   review rework or supported recovery first. Inspect a new seam only when no
   actionable continuation or usable task remains; broad repository scope permits
   independent maintenance beyond a genuinely held milestone.
   Empty queues, absent TODO/FIXME markers, green tests and unchanged HEAD do not
   prove work is absent. Implement the accepted next slice or fix an evidenced
   defect with a regression instead of repeating audits or ledger-only receipts. Silence is allowed only AFTER the required work search
   finds no eligible delta. Record `work_search`: milestone/source, checked seam
   and evidence, candidates, eligibility/rejection reasons and next seam. This is
   prompt policy, not a runtime guarantee of autonomous progress.
2. **Use runnable backlog first; otherwise run the docs-sync fallback.**
   Explicit plan slices follow [the shared handoff](../shared/PLAN-HANDOFF.md):
   select within the named IDs, never an unrelated global task.
   Do not run a docs-sync prepass for a usable backlog task, even without a docs cron.
   Record `Repo-docs pass: existing backlog <source/receipt>` or the actual fallback result.
   With no runnable task and no overlapping writer, apply the scheduled fallback
   above and load discovery.md as needed; reuse current docs-owner evidence rather
   than competing with an enabled docs job. Then recheck consumer readiness and selection.
   Missing TODO.md or an old mtime alone does not invalidate a usable goals.json task.
   **Selection order:** reconcile live work, then read `goals.py focus <repo> --json`
   with `<skills-root>` the loaded skill directory’s parent. Select ONE primary milestone; retain it
   until delivered or explicitly reprioritized. Run
   `python3 "<skills-root>/docs-sync/scripts/goals.py" next <repo> --json`
   and choose a dependency-ready, unclaimed slice advancing that focus, not the
   first unrelated task. If focus is absent, record the accepted milestone and
   missing focus explicitly; do not invent CLI syntax. Without goals.json use
   TODO.md Now/Next linked to that milestone. Broad-scope maintenance fallback
   requires evidence that every eligible milestone slice
   cannot safely proceed (ownership, authority or environment), or owner reprioritization.
   Executed passing checks establish only their named scope, not delivery.
   Prove or finish unverified/partial work before reimplementing it.
   Build the worker contract directly from the task's Scope, Acceptance and Sources,
   and quote its task ID and goal ID. Mark it with `goals.py task <repo> <TASK>
   in_progress` at handoff. If the backlog is stale against the code (a task already
   done, a path gone), correct that one entry via `goals.py task`, then pick again;
   docs-sync' next run does the rest.
3–9. Apply [iteration and decisions](references/iteration-and-decisions.md) for
    environment repair, retries, acceptance, review and genuinely missing user input.
10. **Ownership.** Each writing pass uses its own pinned Git worktree, never
    the shared checkout. `start_goal.py` requires `--base`; assemble explicit
    prerequisites and run its manifest-pinned guard before FIRST edits only.
    Use default worker mode and `goals.py`; this agent owns local integration.
    External-owner/proposal roles require an explicit split-role request.
    Follow [handoff safeguards](references/handoff.md#ownership-and-verification-safeguards).
    Gate one frozen candidate; fixtures never establish product/provider execution.
11. **Model refusals.** A provider safety refusal or crash is infrastructure: reword
    the contract neutrally (or set a `hermes kanban set-model` override) and retry
    the same card once. After two failures, record it in the journal and move on.
12. **Board queries.** Use `hermes kanban list/show/runs --json` piped through `jq`
    with `--assignee`/`--status` filters. Never hand-write SQL against kanban.db,
    and never `json.loads` raw terminal output of a whole-board listing.
14. **Local commits required.** Before review/completion, run `scripts/finish_task.py`
    for acceptance checks and owned files; report branch/SHA. Failure is incomplete;
    no_changes means no new commit. Explicit no-commit instructions win.
    See references/handoff.md for commands, ownership and delivery safeguards.
    Never commit foreign work, secrets or build output; never
    push, rebase, amend or bypass protected PR checks without explicit authority.
    Coordinator local integration follows standing repository authority and review;
    worker contracts do not grant workers merge permission.
13. **State hygiene.** Keep `autowork/state.json` under ~20 KB: the last 20 entries
    with a fixed schema; older entries go to `autowork/history/`. Keep picker
    receipts to the last 10. Preserve downstream launch inputs outside disposable
    worker workspaces before terminal completion; retain exact bytes and hash pins.
15. **Recovery must reach execution.** Follow the recovery-continuation procedure
    in `references/handoff.md`: retain original-card launch authority, reconcile
    current runs, and execute the authorized parent continuation after slot release.
    Task creation is not progress; report running only from exact run/process
    identity and observed worker initial-gate success.

## Parallel dispatch and reporting

Load [dispatch and reporting](references/dispatch-and-reporting.md) before an explicit parallel backlog handoff or any user-facing status report, including blocked, failed, unchanged and scheduled occurrences. Always name the current TODO.md task and the next task with its eligibility; its output contract is required.

## Each run (picker)

**Picker budget:** At most about 30 tool calls or 10 minutes per scheduled run.
Reconcile, finish authorized closeout, select and hand off. Delegate deep investigation, source
re-verification and checks to the worker. Over budget: hand off the best candidate,
or reply `[SILENT]` and leave a journal note for the next run.

1. **Reconcile first.** Use `scripts/reconcile.py --profile <profile> [--task-id <id>] --compact`
   once for the prior handoff; reuse its readback instead of repeating show/journal reads.
   Before a waiting report, apply the final readback in [delivery batching](references/delivery-batches.md#continue-delivery).
   Omit `--compact` only when full evidence is needed for the next action.
   Two unchanged blocked observations require a different supported repair,
   independent authorized work, or one precise external input—not another identical retry.
   Use `continuation` and `changed_fields` from its saved report projection to resume
   the phase. Unchanged evidence is not a reason to redo planning or check suites.
   Check relevant working files and ownership before acting; the report cache is
   not an authorization or source-freshness proof. Preserve failed attempts and
   retry only after changed inputs or a concrete different repair.
   Follow its `next_action`: observe an active run without overlapping it; verify
   approved terminal work and integrate under existing authority before selecting
   more work; recover the original blocked card. A hint is not liveness or approval
   evidence. Finish authorized closeout in this occurrence, not a later scheduled tick.
   Apply owner replies and report new terminal results. Preserve the original card and worker session
   after interruption; a new tick never licenses a replacement, budget reset or overlapping worker.
   Check live ownership again at dispatch (the helper does this under its lock).
   Read run/heartbeat liveness per `references/handoff.md#picker-run-liveness`.
   Load `references/state-and-recovery.md` for schema/session/recovery details and
   `references/blockers-and-history.md` for failed/blocked cards. Retry limits still apply.
2. **Select.** Read `goals.py focus <repo> --json`, then run `goals.py next <repo> --json`
   through the docs-sync script path (pass `<repo>` as the absolute repo path — a bare
   directory name fails to resolve); choose an eligible slice of that primary milestone (priority 2). If held, run [recovery](references/owner-cycle.md) and [planning](references/backlog-planning.md). Resolve routine engineering choices first. If it still needs a material
   owner action or decision, run `goals.py section <repo> <TASK> "Needs decision"` and ask (hard-blockers).
   If it bundles excluded scope, register the in-scope slice with `goals.py add-task` and park the rest.
   Then pick again, within the picker budget. If the eligible slice's goal is not the ledger
   focus, use the scoped override in [the plan contract](../shared/PLAN-HANDOFF.md)
   for a one-slice request. Change `goals.py focus <repo> <GOAL>` only for an owner
   priority change, then re-run `next`. Neither path licenses unrelated work.
   Load `references/discovery.md` only if
   no usable milestone task remains (including the TODO fallback); do not double-check
   a usable task with a broad discovery or documentation pass.
3. **Hand off.** Load `references/handoff.md`. Use backlog-check. Compare
   executable inputs against the committed candidate. Use default worker mode;
   proposal context is only for explicitly requested split-role work. Dirty code needs
   attributable prerequisites per [recovery](references/blocker-recovery.md);
   never copy or commit foreign edits. Treat `--validate-only` as structural
   and ledger admission, not proof that isolated candidate assembly will pass.
   Write the contract file with every field:
   `Objective`, `Scope`, `Verification`, `Source`, `Project payoff`, `Current evidence`,
   `Expected change`, `Acceptance`, `Stop conditions`, `Repo-docs pass`. Include the
   vertical-slice contract in references/handoff.md within these fields. Build it from the
   goals.json task (quote its task and goal IDs), run `scripts/start_goal.py … --validate-only`,
   then the real handoff (same selected budget: default 100 or explicit 50/100, automatic failure retries disabled), and — only once the helper
   has actually created or returned a card for it — mark the task with
   `goals.py task <repo> <TASK> in_progress`. If the helper answers `already_owned`, no card was
   created: preserve the live card, avoid duplicate dispatch and revert any premature
   `in_progress`. Explicit parallel requests use bounded file-disjoint children under
   **Explicit parallel backlog requests**; the parent retains ledger/commit ownership.
   The picker never implements the slice itself.
4. **Report** per the Output contract and the user's delivery policy. A request
   for status every occurrence requires a concise nonempty report even when unchanged.
   Otherwise reply exactly `[SILENT]` only after reconciliation and the idle fallback
   find no new reportable event; an idle profile with eligible tasks hands one off.

References (load when steps 1–3 require): `references/discovery.md`,
`references/handoff.md`, `references/blockers-and-history.md`, `references/maintenance.md`
(maintenance only; not scheduled), `references/upstream-goal-selection.md` (background),
`references/native-containment-proof.md` (containment),
`references/budget-controller-proof.md` (synthetic admission), and
`references/controller-bridge-proof.md` (peer-bound fixture composition).
These proofs do not qualify native/provider execution.

Named plan: [accepted-plan-execution.md](references/accepted-plan-execution.md). Explicit whole spec: `references/whole-spec-execution.md`.

## Upstream boundary

Hermes Agent stays unchanged. Missing authenticated runtime capabilities are not
permission to patch upstream, export worker identity, manufacture claims or weaken
admission. A saved handoff can restore registration context only, never authenticate
a worker. Use supported coordinator/plugin controls; if a particular operation is
unavailable, preserve that candidate and continue independent authorized work.
Do not repeatedly request an exception to an explicit no-upstream-edits instruction.
