---
name: autowork
description: "Use to implement and verify ready repository tasks."
version: 0.28.1
author: Hermes Agent
platforms: [linux, macos]
metadata:
  hermes:
    tags: [autonomy, planning, backlog, verification]
---

# Autowork

Execute a bounded useful slice in the current agent session. TODO.md owns task IDs,
intent, scope, acceptance, dependencies and visible progress; goals.json, when
present, is its synchronized index. A TODO-only repository needs no Hermes setup
or extra public tracking file. No Kanban lookup, card, board, assignee, native
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
2. **Use runnable backlog first; otherwise run the docs-sync fallback.** Read
   TODO.md Now/Next and accepted milestone priorities. With an existing index use
   `goals.py next <repo> --json` and `goals.py focus <repo> --json` from Docs Sync;
   reconcile inconsistent source evidence without inventing acceptance or ownership.
   Do not run a docs-sync prepass for a usable backlog task. Named --tasks/--plan
   scope stays exact. A task Autowork records or repairs includes `Touches:` from the
   inspected seam ([TODO rules](../shared/TODO-WORKCENTER.md)), so parallel workers can
   run it beside others. Do not create a second board or require goals.json for a
   TODO-only contributor.
3. **Prepare only missing inputs, then implement.** Derive a short contract from
   the task's objective, scope/exclusions, acceptance/checks, dependencies and sources.
   Keep source/candidate identity, actual owner/session, explicit limits and known
   consumed budget in private evidence. One coherent delivery batch may include
   connected code, tests and docs; do not split it merely by file.
   The default is one composed command for selection and coordination:

   ```sh
   python3 <autowork>/scripts/owner_cycle.py /absolute/repo \
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
   implementation or a background launch. `PRIORITY_DRIFT` means a human changed
   TODO.md order since it was recorded: run `goals.py reorder <repo> --expected-revision
   <revision>` (scheduled runs do this automatically), then select again; never
   execute the stale order. If reorder refuses, report its conflict. An `UNMIGRATED`
   priority flag is reported as-is; selection does not migrate the repository. See [the exact interface](references/owner-cycle.md)
   for claims, bounded argv execution, release and source-bound receipts.
4. **Implement and verify.** Repair routine non-privileged environment failures,
   iterate on failing tests, and retain failure evidence. Required acceptance tests,
   independent review where required and source freshness still apply. Reuse checks
   only for matching inputs when policy allows; rerun changed-input and mandatory
   gates. A missing required review holds completion, not unrelated authorized work.
   Before another partial delivery, compare it with the exact acceptance criterion
   still preventing closure: name the positive capability it delivers or the required
   gate it removes. Do not keep selecting adjacent parser, cancellation or refusal
   controls while the same missing trust input or runtime capability stays untouched;
   growing commit/test counts can conceal an unchanged critical path. Repair genuine
   security or data-loss defects, but do not use incidental hardening as a substitute
   for finishing the selected outcome. If the remaining capability is unavailable,
   make the existing fix-or-skip disposition and advance dependency-ready independent
   work within scope; never imply that refusal-only tests supply the positive path.
   Recover independently useful fixes from an idle candidate only after verifying
   provenance and current writer inactivity; compare adopted bytes, rerun affected
   checks and obtain required review. Prefer one coherent final candidate and the
   union of mandatory affected checks over a full rebuild/review for each tiny guard.
   Reuse a sanitized cache/target and check receipts only when their bound inputs
   match; retain required mutations, independent review and integration checks.
   Integrate a partial slice only when repository policy permits it; record its
   commit and exact remaining gates under the original TODO ID. Never call focused
   passes a full-suite pass, waive a gate, close the parent, or infer dependency,
   publication or upstream authority from partial delivery.
5. **Close out.** Commit attributable verified paths locally unless forbidden.
   Use ordinary Git, repository review and integration policy. Inspect fresh target
   state and serialize canonical writes; preserve unrelated dirty work. Never push,
   deploy, publish, spend money, place trades or broaden live authority without its
   explicit scoped authorization. Report actual commit/review/integration separately.
   For worktree-backed work, finish [worktree closeout](references/worktree-closeout.md):
   verify integration on the canonical `main` or `master`, then remove the task's
   worktree with `scripts/worktree_closeout.py CANONICAL --worktree PATH --apply`.
   Every `--apply` task claim also removes earlier integrated, clean, unused
   worktrees and reports the rest under `worktree_cleanup`. Preserve active, dirty,
   unmerged or recovery-bearing worktrees; report integration/cleanup pending.
   Reconcile TODO and any existing goals.json only after verified acceptance, then
   archive completed bodies to `TODO.archive.md` (or the established archive) with
   `goals.py archive <repo>` (without an index use `--verified-tasks ID1,ID2`).
   Follow the [archive contract](../docs-sync/references/todo-archive.md). Preserve
   history; read-only runs do not write.

## Ownership, limits and continuation

Use local repository locks and isolated worktrees where concurrent writers need
isolation; one writer per workspace. Before adopting idle work, inspect actual
process liveness, workspace changes, source/candidate provenance and check receipts.
Advisory locks cannot exclude manual writers who ignore them or coordinate different
hosts; an enabled same-repository cron run may also be writing. Preserve useful
candidates; do not kill workers or delete worktrees to migrate. A live writer does
not freeze priority: apply an owner's reorder to the next selection through Docs
Sync, without interrupting current work or faking a dependency, and report it only
after `goals.py next` agrees.

Work in the canonical checkout by default; it needs no merge step. The task helper
separates two kinds of live process. An Autowork command for the repository blocks
every worktree. Any other agent session (`pi`, `claude`, `codex`, `hermes`) blocks
only the checkout it touches, and only while active: recent terminal use, running
commands or an open writable repository file. A session idle past 30 minutes is
reported under `idle_sessions` and does not block; never kill or message it. An
active (or unknown-activity) session in another checkout is reported under
`other_checkout_sessions`: it does not block this one, but it is not idle. When the
helper returns `BUSY` with `isolate`, create that worktree and branch (reuse it if it
already exists), rerun the helper with that worktree as the consumer, and do the
task there. Integrate the verified branch into the canonical checkout only when
`owner_cycle.py CANONICAL --writers` returns `CLEAR` and the merge touches no file the session
has changed or holds open; otherwise keep the committed branch, report it as
awaiting integration and continue with independent work next occurrence. Shared-tooling fixes follow
[cross-profile recovery](references/owner-cycle.md#cross-profile-recovery-and-deployment).

Distinguish a `BUSY` response from an existing live Autowork execution lease: a
`--writers` result of `CLEAR` does not release or override that lease. Compare the
recorded owner with this session's verified dedicated runtime identity before
calling it another worker; inspect actual activity without taking over, removing
the lease or opening a competing worktree to bypass it. Report a preserved live
owner separately from verified implementation progress.

Caller scope and saved stop/batch limits control continuation. Default: one useful
slice including recovery and closeout. Explicit stops win. Apply
[mode precedence](references/iteration-and-decisions.md#mode-precedence).
Honor explicit task/caller allocations and the host's real controls; unknown usage
is not zero. A cron tick never renews an exhausted allocation. Do not invent a
universal lifetime-task budget. Missing enforcement holds only an operation requiring
that explicit cap; independently authorized inspection, checks and local integration
remain separate. A prompt or receipt cannot enforce spending.

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
seam, records a justified TODO task and executes it in the same occurrence.
Named-only jobs cannot widen scope. Empty queues, green tests or unchanged HEAD
are not proof of exhaustion; record `work_search` evidence and rejected candidates.
This policy is not a runtime guarantee of progress. No fabricated busywork.

## Parallel workers (opt-in)

Only when the caller asks for parallel work, run `owner_cycle.py REPO --apply
--parallel [N] --owner-pid PID`: it starts headless host workers, one task each in
its own worktree, for tasks whose `Touches:` and `Resources:` prove independence.
Then loop `--wait --timeout S`, review each `report.json`, `--integrate TASK
--timeout S --run CHECK...` (`--run` last), `--parallel-close TASK`, commit the
coordinator files, and refill with `--apply --parallel`; release only after no slot
is left to integrate or close. Workers never select, merge, close or push. `SEQUENTIAL_FALLBACK` means run the returned contract the
ordinary way. Follow [parallel workers](references/parallel-workers.md).

## Owner blockers

`/autowork blockers [repo|name]` walks the owner through queue blockers, easiest
first; answers become planning: [owner blockers](references/owner-blockers.md).
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
For interactive updates, lead with the concrete artifact or result and say plainly
whether work is executing, waiting or idle; keep unchanged implementation details out
of repeated messages. After a user asks to continue tool work, return a visible result
or precise remaining blocker, never an empty response. Coalesce delayed completion
notices into the current task report: a late failure from an already-repaired attempt
is not a fresh regression, and an already-reported pass is not another completed task.
Keep run/source bindings in receipts, not in user-facing narration.

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
