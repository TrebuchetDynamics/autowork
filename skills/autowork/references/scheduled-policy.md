# Scheduled policy and profile exceptions

Maintain reusable behavior in hermes-toolset source before changing profile prompts.
Profiles carry only workspace, accepted scope, owner authorization, delivery target
and genuine repository exceptions; do not duplicate this workflow in each job.
Existing authorized cron jobs may invoke autowork; the skill never creates schedules.

Start with `hermes-toolset:autowork` for repository-stage preparation, then use the
existing worker engine and state. Missing task files alone are bootstrap work; an
unintegrated owner proposal still requires reconciliation.

Autonomous coordination is the default. The running agent handles local planning,
implementation, review and integration without waiting for another owner or parent.
Historical claims are attribution; check actual running workers and conflicting
writes. Continue/review/adopt idle local candidates while preserving their bytes
and provenance. Use the default worker role. External-owner requests and proposal
roles are opt-in through `--require-owner`, never implied by old route files or
owner fields in receipts. Earlier owner-only wording in this workflow is superseded
for authorized local work; scope, pauses and explicit external-action limits remain.

Before a blocked or idle report, execute [the owner recovery cycle](owner-cycle.md).
Use owner_cycle.py --apply --allow-ready-fallback --scope repository for broad repository development;
use --scope tasks for a job limited to its named tasks and omit fallback for literal
task-only scope. Process inbox replies, reuse existing
exact authority and task-bound handoff payloads, replenish useful accepted offline
tasks, and reconcile worker completions per the unattended continuation contract.
Never summarize the readiness helper's zero count as the whole occurrence result.
Keep an actual owner pipeline receipt and bounded disjoint work search; a maintenance
"evaluation" without an authorized repair attempt is not completed recovery.

Before another no-progress report, follow the owner-cycle `planning.action` and
[bounded Autoresearch Plan fallback](backlog-planning.md). Run plan only when the
gate requests preparation and research is actually needed; a known bounded repair
can use direct evidence. Persist the result against the triggering input fingerprint.
Planning findings must reach canonical docs-sync reconciliation before selection.
If the bound task stays held, run [repository maintenance](repository-maintenance.md)
under broad repository authorization: inspect a distinct component, record justified
TODO tasks and execute an eligible slice now. Do not confuse a cached task-specific
planning receipt with completed repository-wide discovery.

When no runnable task remains and no live worker owns the affected work, load `hermes-toolset:docs-sync`
for narrow task/document reconciliation grounded in existing accepted intent; use
Bootstrap only for applicable missing documentation. Then
rerun selection in the same occurrence. Respect concurrent docs ownership and ledger
revision guards. Unchanged inputs stay byte-identical; never invent tasks, approval,
empty commits or repetitive broad scans to fill a tick. A live worker or ownership
conflict is reconciled, not replaced by a competing docs writer.

A standing explicit owner request to commit and push remains a delivery obligation
across occurrences; autowork invocation alone never implies push permission.
With that authority, load `hermes-toolset:git-commit-push`, gate and commit the owned
completed slice, push only its policy-permitted ref to the existing authorized remote,
and read back the exact remote ref and SHA. Forward scoped worker publication through
`start_goal.py --publication-authority` per `references/handoff.md`; do not rely on a
parent prompt to override the worker's no-push contract. Otherwise the authorized
integration owner delivers the completed candidate. Use the receipt commit SHA,
not assumed HEAD: `agent_commit.sh` can leave HEAD unchanged. The coordinator may
perform authorized local integration after checks and required review, following
repository policy. No force push, unauthorized remote publication or deployment,
protection bypass, foreign edits or main-only admission bypass.
A local commit is incomplete delivery when an authorized push remains held.

## Scoped offline task isolation

When the user explicitly authorizes isolated task branches/worktrees for named
repositories, retain that exact permission in their existing cron scope and
applicable repository instructions. Use the ordinary supported isolated native
worker path for those offline tasks, not the unsupported canonical main-only
path. Keep main protected, preserve live writers and unrelated work, and carry
no-push, no-deployment and no-live/RF exclusions into every worker contract.
An unchanged main-only admission/canary task does not gate independent authorized
offline isolation; it remains unproved rather than being falsely closed. The
exception grants no PR, protected-main write, history rewrite or Agent modification.
Respect separately recorded pause/resume decisions.

## Progress and decision loop

Before selecting new work, reconcile an already approved candidate: identify its
exact commit, remaining task scope and current canonical ancestry; perform authorized
integration and ledger closure when its checks/review cover that scope. Approval alone
does not close a larger task. Do not repeatedly inspect the same approved commit while
its actionable closeout is untouched. Preserve paused schedules; an interactive or
previously launched worker can still be running while its cron is paused.

For installed helper drift, compare exact source/installed revisions and the helper
actually pinned by the active card. Update idle installations through the supported
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
Bind evidence to the actual task/card/run, source and check receipt; changed HEAD,
scheduler success, task creation and documentation churn are not proof of product
progress. A live worker is observed through its same card/run, not replaced.

When consecutive completed runs repeat the same task/blocker/check/commit evidence,
compare relevant inputs, then diagnose the earliest missing transition. Do not
repeat broad docs passes or ask again for authority already granted. Apply the
existing recovery reference within the profile's own accepted scope. Use
`owner_unblock.py <actual-consumer> --plan <accepted-path#heading> --tasks <IDs>`
first; diagnosis is non-mutating. Only the explicit integration owner uses
`--apply --authority <existing-owner.json>` after current ownership reconciliation.
This composed CLI reuses recover_backlog.py and retry_selection.py and retries
selection in the same occurrence after attributable repair. Supply
`--prerequisite-request <existing-inputs.json>` only for already explicit
snapshot/attribution/base/check inputs; candidate_target/required_paths enable
real candidate validation, never native dispatch. See handoff.md's executable
owner unblock pipeline for exact schemas and native/authentication limits. Missing
inputs produce required inputs/next action argv; do not invent attribution, run
hidden docs generation, unpause jobs or replace an in_progress task.
The individual existing helpers remain available for separately authorized steps:
- Missing/malformed accepted task bodies: source-bound recover_backlog.py under
  canonical revision/ownership guards, then retry the exact consumer gate.
- Uncommitted planning files in an explicitly requested proposal workflow: use its
  automatic frozen planning context; no planning-files prerequisite commit is needed.
  Otherwise retain worker mode and reconcile attributable planning changes through
  the normal authorized candidate preparation; dirt alone does not select proposal mode.
- Dirty executable prerequisites excluded from the candidate: prepare_prerequisites.py
  only with existing explicit attribution; never adopt foreign dirty work.
- No eligible selection after maintenance: retry_selection.py against the actual
  canonical consumer in the same occurrence, not the docs scratch checkout.
- Completed owned slice not published: publication.py with its existing exact
  publication-authority receipt, then the scoped delivery procedure above.

A tool or test failure is a bounded engineering investigation, not user approval
needed. Follow existing limits: 5 consecutive attempts with no new evidence stop
worker iteration; parked cards remain governed by their original retry/fingerprint
rules. Preserve review/ownership/admission and continue independent eligible work.
Record the attempted recovery, discriminator/result and next safe action. Do not
loop unchanged failures or weaken acceptance to make a transition appear complete.

Decide reversible implementation choices under accepted intent using existing
conventions and a discriminating check. Retain `Decision:`, evidence, reason and
check in the existing task/contract; avoid new ADRs for routine choices. Ask only
when outcome/priority/ownership conflicts, credentials, spending or destructive/
external actions require missing authority. Missing evidence is not permission.

This decision discipline adapts the installed addyosmani/agent-skills practices:
observability-and-instrumentation (questions, correlated outcome signals, privacy),
code-review-and-quality (correctness/security and verification), with the verified
systematic-debugging fallback (reproduce -> diagnose -> minimal fix -> check).
This attribution requires no protocol load. For a concrete method gap or explicit
protocol request, select one verified technique through
[engineering](../../engineering/SKILL.md); consult
[the engineering cycle](../../shared/ENGINEERING-CYCLE.md) only if routing is unclear.
Record material application in the existing receipt; loading a skill is not applying
it, and policy tests are not live decision proof.

Honor explicit status-every-occurrence requests over silence defaults. Report
profile, fallback outcome, observed worker/checks, actual commit/push or none,
blocker and next safe action; never fabricate implementation or delivery progress.
