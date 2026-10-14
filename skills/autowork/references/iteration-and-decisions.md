# Worker iteration and autonomous decisions

These operating priorities apply to every Autowork run.

3. **Fix your own environment.** Install missing non-privileged tooling in user
   space/project; record installs, PATH changes and fixtures. Only sudo/system
   packages, credentials and paid resources become owner questions (priority 9).
   For offline fixtures, populate an omitted, already-qualified dependency from
   genuine local source at a verified revision (source-only; copied binaries can
   defeat negative tests), and unset only a demonstrated contaminating selector for
   the test process (`env -u NAME …`). Never fabricate markers, spoof identity
   variables or relax containment. A wrapper refusal before execution is an unrun
   gate, not a product failure. Prefer existing supported gates over new bespoke
   prerequisites.
4. **Workers iterate.** In the current session, a failing check means fix → rerun until
   acceptance, or until 5 consecutive attempts produce no new evidence. Never block
   on a first failure, and never write "one execution/one rerun/no source edit"
   limits into contracts for work inside their scope. Give workers the scope
   they need; a harness or fixture correction needed to reach acceptance is in
   scope by default, subject to explicit exclusions and live ownership. Routine
   isolated patch reconstruction and local input recovery use existing authority:
   execute the saved next step, verify it and continue on the same task. Use
   [direct recovery](owner-cycle.md#limits-and-recovery)
   when evidence lookup or reconstruction is being mistaken for missing authority.
   If an approach fails, choose another reversible implementation on this task
   while preserving accepted behavior, exclusions and checks; record material
   deviations in existing evidence. Neither debugging nor a hard implementation
   is a reason to ask permission or repeat planning. Resolve only newly exposed
   consequential choices through the coordinator's bounded planning pass.
5. **Retry and backoff across runs.** Use no automatic failure retry after an
   unknown launch; reconcile actual process/workspace evidence first. Preserve
   consumed usage and never reset an exhausted allocation. Two unchanged holds
   require a different supported repair, independent authorized work or one exact
   external input. A failed task holds only its actual dependencies and resources.
   Finish pending required review, commit and local integration before selecting
   new work. Preserve paused jobs and useful candidates. No card transitions or
   native continuation API are required for current-session recovery.
6. **Vague acceptance.** If criteria are vague, the worker rewrites them in its
   first turn as 1–3 observable checks under `Interpreted acceptance:` and proceeds.
   Ask an owner question (priority 9) only when the possible readings lead to
   materially different product outcomes; continue only independent authorized work
   until that input arrives. Honor explicit task/caller limits and real host
   enforcement. Stop at acceptance; unused allocation is not work to spend.
7. **Done means scoped done.** Finish after checks pass and owned changes are committed; never rerun an unchanged
   passing gate merely to refresh status metadata. NOT_CHECKED is not qualification.
   For checks likely to exceed the terminal window, use the host's tracked
   background/session execution from the start, with a finite command timeout
   appropriate to the gate; respect execution deadlines and cancellation.
   Save command, candidate identity, session/process
   identity and log/exit receipt; observe that same run through completion.
   A transport timeout is not a test verdict: reconcile the original process
   before retrying, never launch a duplicate live check. Missing final exit/results
   remains unchecked. Reuse source-bound passing receipts when policy allows; required checks still run.
   Separate implemented, exact-source/platform qualification and verified main delivery.
   Explain progress in user outcomes: overall goal, current slice, what is still unproved.
   Keep unrelated recovery work separate; IDs and test counts must not obscure that map.
   Follow the complete outcome standard in references/delivery-batches.md.
8. **Required review.** Use the project's ordinary independent review mechanism
   when required. Bind approval to the actual candidate and checks. Review-requested
   changes run in the current authorized session, followed by affected checks and
   fresh review for changed bytes. No Kanban reassignment or card becoming done is
   required. Review approval alone does not prove all task acceptance. When explicit
   authority requires review before commit, state that ordering consistently in the
   contract and keep the post-approval commit step; review entry never requires the
   deferred commit. Scoped commit helpers may leave HEAD unchanged: use the commit
   they return, not worktree HEAD, for review and integration.
9. **Ask, don't block independent work.** Decide routine engineering choices
   (approach, internal design, tests, ordering within focus) under existing authority
   without a questionnaire. Ask only for material missing USER_INPUT, SUDO or
   USER_DECISION, using `grill-me`/`clarify` when available. Record the exact held
   action and recommendation in BLOCKERS.md and the handoff. Silence never grants
   authority or required review acceptance. Prepare authorized work up to that
   boundary and continue independent work; if nothing can proceed, report the real
   dependency honestly. Do not relabel incomplete work as done to avoid a pause.
   Existing explicit authority carries forward. Failing tests, missing user-space
   tooling, routine debugging and agent-invented restrictions are not owner decisions.
   A real tool `pending_approval` holds its original operation and dependent work
   only. Preserve its resume step and supplied request ID; do not resubmit through another tool
   or invent approval. The coordinator may select independently authorized,
   dependency-ready, non-overlapping work; workers stay within their assigned scope.
   Read owner replies (chat / `session_search`) at each run and apply them; do not
   repeatedly return `[SILENT]` for an unanswered material question.

## Mode precedence

Caller scope and saved stop/batch limits control continuation.
Default interactive execution completes one slice, including authorized recovery
and closeout. An explicit one-task limit stops new selection after that task;
standing authority cannot override the caller's narrower stop. Explicit continuation or whole-spec scope
permits further eligible batches only within its accepted bounds.
Recurrence authorizes the saved occurrence, not wider scope or extra budgets.
Reconcile consumed history first; unknown usage is not zero, and
exhaustion requires explicit additional allocation, never a new occurrence or session.
Count usage in the controller's actual unit (API calls, tool calls and tool-calling
iterations differ) and record spent and unspent amounts; early stop does not consume
the whole grant. Reopening a closed remainder reuses its actual remaining amount
and scope, not a fresh default.

## Archive verified completion

At verified closeout and reconciliation of completed bodies, align TODO and ledger
status, then run `python3 "<skills-root>/docs-sync/scripts/goals.py" archive <repo>`.
This automatically moves closed bodies to `TODO.archive.md` or the existing archive;
do not wait for a Docs Sync job. Keep ledger evidence. Without goals.json, inspect
checks and pass verified closed IDs with `archive <repo> --verified-tasks ID1,ID2`.
Report retained conflicts; read-only runs skip this write. Follow the
[archive contract](../../docs-sync/references/todo-archive.md).
