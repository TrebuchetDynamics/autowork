# Task-store branch playbooks

Disclosed reference for [Docs Sync](../SKILL.md) section 5. Load it when the request
matches one of these branches. The task contract in the main skill still governs: these
branches add a disposition, never authority or a new status.

### Put deferred qualification last

When the owner asks to leave real-world checks until the end, identify the exact
checks from the conversation and give their tasks the highest ranks in Next (or
place them in Needs decision when they need an owner); do not merely add a deferred
note. Preserve their relative order, acceptance, dependencies and access gates, and
the relative order of unrelated work. Check selection with `autowork tasks list`:
rank alone does not exclude a task from execution. Keep that deferred tail intact
during later priority changes unless the owner changes it. Do not add dependency
edges from independent implementation or fixture QA to these externally gated
checks, because that would turn an access gap into a development stop. Deferral is
neither a pass nor cancellation, and it grants no device, credential or
live-operation authority.

### Read-only pending-task reports

Read the store with `autowork tasks list` and `show`, enumerate open IDs in
selection order, and calculate section totals from those same IDs. Report
superseded tasks separately as history, not executable work. Within Needs decision,
distinguish unresolved owner choices or live-operation authority from accepted
scope awaiting recovery, qualification or delivery. Describe a `Held by:` note as
recorded, not as checked liveness, and state whether target identity and deployed
readiness were assessed. A listing performs no repair, transition or schedule
change. If an owner stop is not yet reflected in the store, distinguish recorded
totals from pending work after that stop, and expose the stale entry as a risk;
never silently count stopped work as authorized or claim its closeout was applied.

### Owner-stopped closeout

Read the current task and latest retained result before interpreting a close request.
Honor an explicit manual-close decision with `done --by WHO --reason TEXT`; keep
unmet goal acceptance unqualified unless an owner waiver/qualification is recorded.
If acceptance is unmet and the intended disposition is unclear, ask once whether to
stop without completion or retain the task for qualification; reuse an explicit stop
answer without asking again. Do not run additional experiments to justify
cancellation. Keep the original contract, withdraw active continuation notes and
place the task in Needs decision with the stop recorded (`place ID "Needs
decision" --decision TEXT`), or supersede it when an accepted successor exists;
never mark it done or fabricate a successor. Keep unmet goal status unmet. Run
`autowork tasks why ID` and assert it is not selectable before reporting removal
from execution. Queue exclusion does not prove an already-running worker stopped:
assess it separately when in scope and report any unverified liveness.

### Autoresearch intake and task scheduling

For `/autoresearch` findings, plans, experiments or chained handoffs, load
[the autoresearch adapter](../../autoresearch/SKILL.md). Treat run logs, TSV and
`handoff.json` as evidence inputs; this skill still owns canonical documentation
and task reconciliation. Narrow Maintain records accepted findings in existing
owners and schedules bounded work with `autowork tasks add` under the matching
goal, with rank, dependencies, full acceptance/checks and preserved ownership.
Reuse matching task IDs, including held work; repeated evidence creates no
duplicates. Research recommendations do not manufacture accepted product
requirements.

Include baseline/target/units, exact Verify/Guard results, run/source references,
remaining gaps and chosen implementation/verification slices. Run the handoff check
above and report actual Now/Next eligibility. Scheduling here means ordered tasks,
not a new timer or dispatch. Continue through autowork only within existing
implementation authority; explicit audit/read-only and no-implementation limits
carry across all chained research commands.

## Hard-blocker coordination contract

Inspect root BLOCKERS.md during authorized Bootstrap/Maintain. Load `hard-blockers`
before entry changes; reading/respecting needs no load. Create absent canonical
Active/Resolved sections with None during bootstrap, not invented blockers: this
required empty coordination file is the no-empty-scaffold exception. Only USER_INPUT,
SUDO or USER_DECISION belong there after autonomous paths/decisions are checked;
internal engineering/review/tool issues stay in tasks. Preserve entries and
Default if no answer; reference IDs in questionnaires/tasks and continue independent
work. Change Last checked only after reevaluation. Verify resolution before moving
to Resolved; never silently delete. Explicit Audit/read-only changes nothing.
