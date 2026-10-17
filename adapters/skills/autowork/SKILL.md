---
name: autowork
description: "Coordinate repository work: plan missing tasks, implement a useful slice, verify and commit locally."
disable-model-invocation: true
---

# Autowork

Read the [host contract](../COMMON.md). Use this host's native tools for execution.
Do not launch Hermes workers (opt-in parallel workers below use this host's own
CLI), require Hermes profiles, or depend on a native Kanban card. Run in the current session; delegate only when available and appropriate under
the user's instructions. Use a separate worktree when real concurrent writes need
isolation, and preserve all unrelated edits.

At verified closeout and initial reconciliation of completed bodies, automatically
move those bodies from TODO.md to `TODO.archive.md` (or the established archive).
Reconcile the task checkbox/Status and ledger, then run the bundled
[goals helper](../../../skills/docs-sync/scripts/goals.py) with `archive <repo>`.
Without goals.json, inspect completion checks and pass the verified closed IDs as
`archive <repo> --verified-tasks ID1,ID2`. Preserve ledger records/evidence and report
retained conflicts. Follow the [archive contract](../../../skills/docs-sync/references/todo-archive.md);
explicit read-only runs write nothing.

1. Read repo instructions, TODO.md, accepted plans and current changes. Reconcile
   active work and approved candidates before choosing another task. Finish authorized
   closeout after checks/review; local integration and publication are distinct.
2. Choose a dependency-ready accepted task. If none exists, inspect a bounded seam
   for a useful bug, test, UI, documentation or refactoring improvement. Use
   [Plan For Me](../plan-for-me/SKILL.md) only when planning/research is needed;
   an obvious repair needs no extra ceremony. Record a complete TODO task via
   [Docs Sync](../docs-sync/SKILL.md), including `Touches:` for the paths the inspected
   seam may change, then execute within the user's scope.
   For a ready task, compose reconciliation, accepted body, explicit bounded
   code/docs/tests/dependency sources and a short execution contract in one host-native
   preparation step. Retain objective/scope, acceptance/checks, source/base,
   ownership, authority, budget and stop conditions. Do not run a duplicate
   validate-only, planning/docs audit, full suite or optional skill loader first.
   Keep detailed inputs in the existing task receipt and routine status compact.
   Preserve stale/held/incomplete/interrupted/owned refusals and consumed budget;
   prepare only the missing input; preserve existing evidence and explicit allocations.
   No Kanban lookup, historical card, native continuation or review transition is required.
   Inspect actual process identity and workspace activity before adopting idle work.
   Advisory local locks do not coordinate other hosts or manual writers ignoring them.
   Planning owns consequential decisions and executable acceptance; follow the
   [handoff](../../../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
   Once ready, execute without reconfirmation. Choose reversible details yourself;
   adapt a failed approach within accepted behavior, exclusions and checks on the
   same task. Record material deviations; use bounded planning only for a newly
   discovered consequential choice, not routine debugging or a missing fixture.
3. Batch connected consumers, runners and tests into one useful outcome; split
   only for concrete dependency, concurrency, authority or budget boundaries.
   Implement the smallest complete outcome, run discriminating checks, fix failures and
   satisfy required review. Separate offline implementation from live qualification.
   Use installed specialist skills only for concrete gaps, not a mandatory phase chain.
   Run long checks through tracked host background/session execution with a finite
   command timeout; respect execution deadlines and cancellation. Retain candidate,
   command, session identity, log and final exit.
   Reconcile a transport interruption before retrying; never duplicate a live check
   or call partial output a pass. Finish the authorized closeout in this run.
   Apply the [Ponytail method](../../../skills/autowork/references/ponytail.md) to
   material implementation choices: reuse before adding code, complete affected
   consumers, and record the choice and checks in the existing task. Resolve the
   actual host skill or use the bundled fallback; apply review criteria within
   this host's existing review step and reuse unchanged source-bound decisions.
4. Commit attributable verified work locally unless forbidden. Use ordinary Git and
   the repository's conventions; do not manufacture a Hermes card or receipt. Follow
   repository integration policy and existing authority. Push/deploy requires its
   own authorization; never override host approvals or actual live-safety gates.
   Finish [worktree closeout](../../../skills/autowork/references/worktree-closeout.md):
   verify integration on the canonical `main` or `master`, then remove the task's
   worktree with `skills/autowork/scripts/worktree_closeout.py CANONICAL --worktree PATH --apply`. Preserve active, dirty, unmerged and recovery-bearing
   worktrees; report integration/cleanup pending until the remaining steps succeed.
5. Reconcile task status and evidence in TODO.md and any existing goals.json. Do not
   close a whole feature from a partial slice. Report completed task, checks, commit,
   next task and exact remaining blocker. Default is one completed slice; continue
   across tasks when the user's mandate explicitly requests it.

`/autowork blockers [repo|name]` is [`/blockers`](../blockers/SKILL.md): routine planning
repairs first, then genuine owner questions, easiest first; resolutions become
TODO.md planning, never execution. A task may
read runner state (`autowork ls`, `autowork status NAME`); it never starts,
stops or reconfigures runners.

Parallel workers are opt-in: only when the user asks, run the bundled
`owner_cycle.py REPO --apply --parallel [N] --owner-pid PID` and follow
[parallel workers](../../../skills/autowork/references/parallel-workers.md). Codex
and Pi coordinators get Codex or Pi workers from built-in templates. Claude Code has
no template because it chooses its workers' approval mode: pass `--worker-command`
with an explicit worker argv, or the helper returns `SEQUENTIAL_FALLBACK` and the
task runs in this session as usual. Never add approval or sandbox bypass flags.

Caller scope and saved stop/batch limits control continuation.
Default interactive execution completes one slice, including authorized recovery
and closeout. An explicit one-task limit stops new selection after that task;
standing authority cannot override the caller's narrower stop. Explicit continuation or whole-spec scope
permits further eligible batches only within its accepted bounds.
Recurrence authorizes the saved occurrence, not wider scope or extra budgets.
Reconcile consumed history first; unknown usage is not zero, and
exhaustion requires explicit additional allocation, never a new occurrence or session.

When preparation stalls, execute an existing in-scope recovery step first: rebuild
recoverable patches/inputs, verify the actual consumer requirements, then retry.
For scope/attribution, inspect accepted specs and integration receipts as well as
Git refs; a missing ref alone does not negate valid attribution. Separately required
immutable pins/ancestry still apply; restoring pinned bytes requires their original
hash, while new accepted implementation uses its acceptance checks. Preserve foreign
work, no-commit restrictions and active writers. Invoke
[Plan For Me](../plan-for-me/SKILL.md) only for a consequential unresolved choice, not a known
reconstruction. No implementation reconfirmation is needed.

An actual tool `pending_approval` holds the original operation and dependent work
only. Keep its resume step and supplied request ID, and use the host's supported approval
mechanism; never approve it yourself or resubmit it through another channel. Continue
independently authorized work after checking dependencies and resource ownership;
do not mark the held work complete or silently expand an assigned worker's scope.

For repeated blockage, repair the ordinary metadata/environment issue, choose
independent accepted work, or identify one precise missing external input. Do not
repeat the same audit or treat an old ownership label as perpetual denial. Never
claim unattended scheduling, independent review or live qualification without evidence.

For partial delivery, lead with the delivered behavior and commit stage; report the
open parent and remaining acceptance separately. Reuse unchanged, source-bound
checks only when policy allows; changed inputs and mandatory gates need checks.
Finish authorized closeout and continue the requested scope without a new approval
round. Do not manufacture parent completion or silently widen an active task.

Do not invent a universal lifetime-task cap. An unavailable enforcement capability
holds only the operation requiring an explicit cap, not independent inspection or
already-authorized local verification/integration. A prompt cannot enforce spending.
