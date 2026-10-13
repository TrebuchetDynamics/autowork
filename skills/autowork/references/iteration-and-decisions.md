# Worker iteration and autonomous decisions

These operating priorities apply to every Autowork run.

3. **Fix your own environment.** Install missing non-privileged tooling in user
   space/project; record installs, PATH changes and fixtures. Only sudo/system
   packages, credentials and paid resources become owner questions (priority 9).
4. **Workers iterate.** Inside a goal worker, a failing check means fix → rerun until
   acceptance, or until 5 consecutive attempts produce no new evidence. Never block
   on a first failure, and never write "one execution/one rerun/no source edit"
   limits into contracts for work inside their scope. Give workers the scope
   they need; a harness or fixture correction needed to reach acceptance is in
   scope by default.
5. **Retry and backoff across runs.** New cards use `--max-retries 1`: no automatic failure retry.
   Supported same-card recovery must preserve cumulative usage; never reset an exhausted allocation.
   A card that blocks twice with no new evidence is parked
   (`hermes kanban schedule <id> "retry_exhausted: …"`) and is not reselected until
   its source, prerequisite or contract fingerprint changes. Pick disjoint work
   instead. A parked or triage card blocks only its own slice.
   Reconcile `retry_selection.py`'s `reconciliation_task_ids` before dispatch:
   observe an active worker, resume an idle candidate, or finish verified review,
   commit and integration under existing authority. A review-approved candidate
   awaiting closeout needs a closeout action, not another inspection of its tests.
   The selector keeps in-progress work out of the new-task frontier, so an
   independent open task can be considered without changing the original task's
   status. Dependency and native admission checks still apply. If closeout cannot
   proceed, check overlap and execute an independent candidate in the same run.
   Preserve paused jobs; do not call a paused schedule stalled. Report the concrete
   action and remaining step, not merely the same task ID and unchanged evidence.
6. **Vague acceptance.** If criteria are vague, the worker rewrites them in its
   first turn as 1–3 observable checks under `Interpreted acceptance:` and proceeds.
   Ask an owner question (priority 9) only when the possible readings lead to
   materially different product outcomes; continue only independent authorized work
   until that input arrives. Use 100 turns by default, or an explicit 50-turn override;
   explicit 100 still requires `Goal budget rationale:` for one coherent outcome. Stop at acceptance, not budget exhaustion; never spend turns
   merely because available. If acceptance cannot fit, narrow it before dispatch.
7. **Done means scoped done.** Finish after checks pass and owned changes are committed; never rerun an unchanged
   passing gate merely to refresh status metadata. NOT_CHECKED is not qualification.
   Separate implemented, exact-source/platform qualification and verified main delivery.
   Explain progress in user outcomes: overall goal, current slice, what is still unproved.
   Keep unrelated recovery work separate; IDs and test counts must not obscure that map.
   Follow the vertical-slice standard in references/handoff.md.
8. **One review.** When the card goes through the native review lane, that lane is
   the independent review. Every card body starts with a *Definition of done* that makes
   the review handoff the card's last step, NOT milestone completion. If a worker reports "review entry rejected
   because review is pending" (circular gate), do not route it to the governor and do not
   block. Have the review requested again with a summary that cites the Definition of
   done and lists only deliverables and executed checks (see SOUL "Review handoff"). Do not also launch pre-write or final reviewer subagents
   unless the contract explicitly names them. Do not load `requesting-code-review`
   in workers.
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
   Read owner replies (chat / `session_search`) at each run and apply them; do not
   repeatedly return `[SILENT]` for an unanswered material question.
