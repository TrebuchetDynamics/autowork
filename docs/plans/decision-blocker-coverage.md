# Decision-task and blocker coverage

## Complete owner-action inventory

Status: Accepted

Owner direction, 2026-10-20: tasks in Needs decision are not being counted or
exposed consistently as blockers; the owner must be able to reach all decisions,
not just the single blocker highlighted by the current view. This records the
requirement, not an implemented fix or permission to start/reconfigure runners.

### Required behavior

- Reconcile the complete supported TODO/index task inventory with current runtime
  holds and owner answers. Include independent unresolved Needs decision tasks,
  including zero-dependent tasks, without requiring a worker to fail first or a
  runnable task to depend on them. Use supported linked storage when enabled.
- Classify each task: unanswered owner decision/input/authority; already answered
  and awaiting consumption; deliberately deferred; cancelled/retired; agent repair;
  or ordinary dependency/resource wait. A section name alone is not proof that a
  fresh owner answer is needed. Preserve prior answers and explicit deferrals.
- Count unique affected task IDs separately from distinct unresolved decisions.
  Shared-question grouping must retain all affected IDs and is valid only for the
  same actual decision. If one shared answer affects twenty tasks, show both
  quantities; do not suggest that there is only one affected task. Do not dedupe
  unrelated tasks merely because they share a section, goal, reason or label.
- Derive summary counts, details, BLOCKERS.md publication and the /blockers intake
  from the same normalized, freshness-qualified inventory. A single recommended
  next action may remain the headline, but cannot truncate the underlying list.
  Expose omitted/deferred/answered categories explicitly instead of hiding tasks.
- Let the owner list and address every unresolved decision through supported
  details or pagination and repeated /blockers use. An answer updates the named
  decision and all proven affected tasks, without silently discarding others.
  Recheck and continue to the next unanswered issue; preserve stop/skip behavior.
- Support read-only inventory on idle, paused or stopped repositories without a
  model call, worker dispatch, service lifecycle change or automatic resumption.
  Stale cached questions must be identified and reconciled, not presented as a
  complete fresh inventory. Unavailable evidence remains explicit.

### Verification

Add composed offline cases with twenty independent Needs decision tasks and zero
worker holds, twenty tasks sharing one real decision, zero-dependent decisions,
mixed answered/deferred/cancelled/agent-repair entries, source/index drift, legacy
and enabled linked storage, stopped runners and stale generations. Assert identity
coverage and agreement among counters, generated questions, CLI/TUI details and
/blockers discovery, not just the displayed headline. Resolve one decision and
prove the others remain reachable; an unchanged repeat is stable and invokes no
model or control action. No duplicate questions for heading/checkbox pairs,
coverage rows, archived history or prose mentions.

TOOLSET-129-c4 retains its active one-next-action display slice; do not rewrite its
running contract. This work extends complete inventory/publication/intake beneath
that headline and must reconcile delivered question normalization and recovery
interfaces, rather than duplicate them. Existing pauses, live qualifications,
mandatory acceptance and cumulative budgets remain unchanged.
