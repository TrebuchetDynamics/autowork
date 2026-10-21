# Scheduled policy and profile exceptions

Maintain reusable behavior in autowork source before changing profile prompts.
Profiles carry only workspace, accepted scope, owner authorization, delivery target
and genuine repository exceptions; do not duplicate this workflow in each job.
Existing authorized cron jobs may invoke autowork; the skill never creates schedules.

Caller scope and saved stop/batch limits govern each occurrence. Preserve a saved
at-most-one-new-batch limit: fixes, recovery and authorized closeout inside that
batch need no new permission, but they grant no second batch. An explicit
multi-batch/whole-spec mandate continues only within its existing bounds. Recurrence
does not widen scope or unpause a job.
Reuse concurrent implementation only after provenance, current ownership,
checks and required review are verified. A pending review or approval holds its
operation and dependent work, not independently authorized non-overlapping work;
fallback never expands worker scope.

Start with `autowork:autowork` for repository-stage preparation, then use the
current session and actual repository state. A missing `tasks/` store alone is setup work (`autowork migrate`, or planning); an
unintegrated owner proposal still requires reconciliation.

Autonomous coordination is the default. The running agent handles local planning,
implementation, review and integration without waiting for another owner or parent.
Historical claims are attribution; check actual running workers and conflicting
writes. Continue/review/adopt idle local candidates while preserving their bytes
and provenance. Delegate only through authorized host-native tools when useful. Old route files
or owner labels never require a native worker or external acknowledgement. Earlier owner-only wording in this workflow is superseded
for authorized local work; scope, pauses and explicit external-action limits remain.

Before a blocked or idle report, execute [the owner recovery cycle](owner-cycle.md).
Use `owner_cycle.py --apply --owner-pid ACTUAL_SESSION_PID --profile CURRENT_PROFILE
--state-dir VERIFIED_PROFILE_HOME/autowork` for a durable current session claim.
Resolve profile/home from verified occurrence context and retain actual process identity; use --scope repository for broad
repository development and --scope tasks for exact named tasks. No Kanban lookup,
old-card import/release or native continuation API is required. Preserve the exact
--plan/--tasks filter. Execute the returned contract in this session and retain
source-bound receipts; selection alone is not implementation.

Before another no-progress report, identify the specific missing preparation using
[bounded Autoresearch Plan fallback](backlog-planning.md). Run plan only when the
task lacks preparation and research is actually needed; a known bounded repair
can use direct evidence. Persist the result against the triggering input fingerprint.
Planning findings must reach canonical docs-sync reconciliation before selection.
If the bound task stays held, run [repository maintenance](repository-maintenance.md)
under broad repository authorization: inspect a distinct component, record justified
tasks with `autowork tasks add` and execute an eligible slice now. Do not confuse a cached task-specific
planning receipt with completed repository-wide discovery.

When no runnable task remains and no live worker owns the affected work, load `autowork:docs-sync`
for narrow task/document reconciliation grounded in existing accepted intent; use
Bootstrap only for applicable missing documentation. Then
rerun selection in the same occurrence. Respect concurrent docs ownership and the task
store's changed-since-read refusals. Unchanged inputs stay byte-identical; never invent tasks, approval,
empty commits or repetitive broad scans to fill a tick. A live worker or ownership
conflict is reconciled, not replaced by a competing docs writer.

A standing explicit owner request to commit and push remains a delivery obligation
across occurrences; autowork invocation alone never implies push permission.
With that authority, load `autowork:git-commit-push`, gate and commit the owned
completed slice, push only its policy-permitted ref to the existing authorized remote,
and read back the exact remote ref and SHA. Carry explicit publication authority
into any delegated contract; never transfer coordinator-only permission implicitly.
Use the actual verified receipt commit SHA, not assumed HEAD. The coordinator may
perform authorized local integration after checks and required review, following
repository policy. No force push, unauthorized remote publication or deployment,
protection bypass, foreign edits or main-only admission bypass.
A local commit is incomplete delivery when an authorized push remains held.

## Scoped offline task isolation

When the user explicitly authorizes isolated task branches/worktrees for named
repositories, retain that exact permission in their existing cron scope and
applicable repository instructions. Use the ordinary supported isolated worktree
path for those offline tasks, not the unsupported canonical main-only
path. Keep main protected, preserve live writers and unrelated work, and carry
no-push, no-deployment and no-live/RF exclusions into every execution contract.
An unchanged main-only admission/canary task does not gate independent authorized
offline isolation; it remains unproved rather than being falsely closed. The
exception grants no PR, protected-main write, history rewrite or Agent modification.
Respect separately recorded pause/resume decisions.

## Progress and decision loop

Before selecting new work, reconcile an already approved candidate: identify its
exact commit, remaining task scope and current canonical ancestry; perform authorized
integration and verified close (status plus receipt) when its checks/review cover that scope. Approval alone
does not close a larger task. Do not repeatedly inspect the same approved commit while
its actionable closeout is untouched. Preserve paused schedules; an interactive or
previously launched worker can still be running while its cron is paused.

For installed helper drift, compare exact source/installed revisions and the helper
actually used by the active process. Update idle installations through the supported
toolset updater; do not replace running workers' pinned helpers or silently migrate
their evidence. Report the affected helper, compatibility finding, update/defer action
and next retry. Drift alone is not a demonstrated runtime defect.

Repeated recovery reporting must name the earliest missing transition, the concrete
repair/closeout attempted, its result, and the same-run retry or precise unavailable
input. A diagnosis-only receipt is not a repair, and a later unrelated worker result
is not proof that recovery succeeded. Take an authorized action rather than repeatedly
emitting the same audit; do not invent busywork when no supported action remains.

On each occurrence account for accepted_goal -> eligible_task -> implementation ->
passing_checks -> required review/local commit -> authorized_publication separately.
Bind evidence to the actual task/session, source and check receipt; changed HEAD,
scheduler success, task creation and documentation churn are not proof of product
progress. A live worker is observed through its actual process identity, not replaced.

A held or blocked selection goes to Plan For Me for a fix-or-skip decision in the
same occurrence (see [ownership and limits](../SKILL.md#ownership-limits-and-continuation)).
When consecutive completed runs repeat the same task/blocker/check/commit evidence,
compare relevant inputs, then diagnose the earliest missing transition. Do not
repeat broad docs passes or ask again for authority already granted. Apply the
existing recovery reference within the profile's own accepted scope. Use
`owner_cycle.py` and the actual workspace/process evidence to resolve the specific
hold. Preserve original candidate/check bytes and failed evidence. No historical
card or missing native API can veto independent local work. Required tests/review,
source freshness, actual writer exclusion and explicit cap enforcement remain.

## Automatic cron recovery

Follow [cron self-repair](cron-autoheal.md) at occurrence entry and after a failure.
Use the exact-job healer for managed wiring, verify its saved readback, and fix an
attributable Toolset cause in the same occurrence within existing authority. Preserve
pauses, scope and original worker accounting. Startup failures before agent execution
need an external authorized maintainer; saved wiring is not future execution proof.

For material choices retain `Decision: <choice>; Evidence: <source>; Reason: <why>;
Check: <proof>` in the existing task evidence. This is not user approval for broader
scope. After 5 consecutive attempts with no new evidence, change the approach or
report the exact unavailable input; do not rerun unchanged failures indefinitely.
