# Accepted plan handoff

First load the [planning artifact and authority contract](RESEARCH-PLAN.md#planning-artifact-and-authority-contract).
It owns write classification, no-write scopes, standalone versus coordinator-owned
planning and the full requested batch. This handoff does not widen that authority.

Keep ideas and unanswered decisions in their existing documentation owner until
accepted. An accepted plan section names its status (`Status: Accepted`), scope,
acceptance and sources. Preserve existing task/goal IDs and completed history.
Planning saves accepted work as complete records in `tasks/` through `autowork tasks`
([work center](TODO-WORKCENTER.md)); a goal without tasks is not an executable task.

## One planning pass, one handoff

Plan With Me investigates and resolves consequential choices with the user. Plan
For Me investigates and chooses within delegated scope. Both share the Autoresearch
planning method; neither starts a second planner for the same question. Docs Sync owns document persistence and `autowork tasks` the task records. Autowork owns execution and
closeout. These are responsibilities within the same conversation, not mandatory
separate agents or repeated startup passes. Do not chain all four for a ready task.

Planning owns consequential complexity: investigate dependencies and compatibility,
choose an approach within delegated scope, and resolve material product questions
before marking their dependent implementation ready. A task that still says
“choose the storage model/API/migration behavior” is not ready for implementation
when that choice changes the accepted outcome. Resolve it in planning or keep only
the affected slice pending; independent accepted slices remain executable.

Use the existing task record for the execution handoff: outcome and exclusions,
decisions and relevant evidence, real dependencies, observable acceptance whose
criteria each name the test that proves them, exact checks, and the next executable
action, which starts with the failing test named in Acceptance (see the
[planning craft](PLANNING-CRAFT.md#executable-acceptance)). Include known setup/recovery steps
and separate live qualification when applicable. This is a content standard, not
a new schema, receipt or approval gate; fill only actual gaps in existing tasks.
Do not prescribe every edit or require unknown implementation details up front.

Autowork executes that handoff: inspect the relevant source, implement, test,
repair, submit required review and finish authorized closeout. Choose routine
reversible details and adapt a failed local approach on the same task without
asking permission or reopening planning. Preserve accepted behavior, exclusions,
real dependencies and mandatory checks. Record material deviations in the existing
task evidence. Return only a newly discovered consequential decision to bounded
planning; neither a failing test nor a missing fixture is itself such a decision.

Resume from the current task record, accepted section and saved findings. Read only
relevant changes since that evidence: scope/decisions, source and tests, dependencies,
repository instructions and task state. A new invocation alone invalidates nothing.
Do not ask settled questions, regenerate accepted plans or run a broad docs/graph
pass to rediscover the same facts. If freshness cannot be established, inspect the
specific uncertain inputs; do not assume unchanged HEAD covers dirty files.

Use the existing task record or planning receipt for a compact continuation:
- task IDs and canonical plan section;
- decided scope/exclusions, remaining material questions and their affected tasks;
- evidence paths and source revision/file fingerprints where available;
- changed documents, exact checks/results and their input bindings;
- next executable action and any genuine retry condition.
No new mandatory file, duplicate tracker or ceremonial approval form. Explicit
answers and delegated engineering choices carry forward. Proposals remain proposed;
never infer acceptance from silence or label an entire draft accepted from one answer.

Investigate only the uncertainty preventing the next action. Stop when evidence
supports a choice within authorized scope and observable acceptance/checks can be
written. Do not run experiments, interview the user or compare more alternatives
when conventions and current evidence already answer the question. Preserve a
material unknown only on its dependent tasks; independent accepted work stays ready.

Persist one coherent batch, not a pass per finding or skill transition. During a
long interview, save meaningful decisions for continuity without validating and
committing after each answer. If no findings, intent, implementation or task inputs
changed, reuse the saved handoff; do not rewrite dates, duplicate tasks or create an
empty planning commit.

After actual doc/task changes, run the applicable formatter, validator and links
check once on the final batch. Carry their exact results into
the next stage. Repeat only checks invalidated by changed inputs, failed evidence
or repository-required fresh checks. A cached readiness result is not execution evidence: Autowork still checks current
source, actual process/workspace ownership and candidate before implementation. Report stale receipts honestly rather than repinning them.

Standalone planning stops after the requested batch even if earlier unrelated work
had implementation permission. A later explicit instruction to implement starts the
execution workflow. When Autowork invoked this planning substep, return the resolved
decision and batch to that same coordinator in the same occurrence; do not execute
inside the substep, ask “implement now?”, restart planning or spawn a competing
worker. Genuine product decisions or external authority remain explicit; choose
routine reversible planning details yourself.

Write the batch with `autowork tasks add`, `field`, `place` and `goal`; each write
refuses a file changed since it was read, so a concurrent edit is never overwritten.
Then run `autowork tasks validate --worktree .` before reporting it saved: fix every
error. It lists drafts: a record missing contract fields is never selected. After
the commit, `autowork tasks why ID` shows whether each task can run and what it
waits for. Report each task
as ready, waiting (and on what) or draft. Readiness is not execution authorization
or a live ownership check. Commit the batch once.

Diagnose every validation error and draft before closing the handoff. When existing
owner acceptance unambiguously covers the section, repair its exact status metadata
and other clerical contract defects in the same pass, then validate again. Preserve approval evidence, scope exclusions and Proposed
decisions. Missing approval stays draft. See
[decisive planning](../docs-sync/references/decisive-planning.md); never stop at a
repairable draft or substitute queue size for an ordered implementation plan.

For an explicit plan slice, select only its named IDs. Reconcile existing workers,
dependencies, current source and primary milestone before handoff. A usable
backlog does not require a fresh documentation prepass. The consumer checks the
ordered frontier within the named tasks' goals, never an unrelated global goal.
Preserve the focus goal unless the user reprioritizes it, but an explicitly authorized named
slice may execute within that scope after current dependency, source and ownership
checks. No start_goal admission, fallback file or Kanban card is required.

Under execution authority, the current coordinator executes the selected contract, retaining task IDs, scope,
sources, expected change, acceptance, verification and stop conditions. There is
no in-progress status; work held outside the runner carries a `Held by:` note
(`autowork tasks hold`), lifted with `autowork tasks release`.
Optional delegated workers return source-bound results to the integration owner;
required review and canonical closure stay with that owner under existing authority.
No historical card lookup, release, native continuation or review transition is a
prerequisite. Reconcile affected docs/tasks against verified outcomes and preserve
remaining milestone gaps. Do not mark unverified work complete.

## Scoped Skills convention

An optional `Skills:` note stays in the existing task record, not a new required
field or registry. Follow the
[scoped recommendation convention](https://github.com/TrebuchetDynamics/autowork/blob/main/docs/workflows.md#recommendations-autowork-can-use--toolset-137-cd)
when recommending a method: resolvable source, phase/purpose, expected artifact or
check and fallback; distinguish recommendations from actual requirements. A skill
adds no write, execution, installation or publication authority. Preserve this
note with the rest of the record for the later execution handoff; resolving and
applying recommendations belongs to that scoped workflow.
