# Plan With Me: special cases

Load the section that matches the request. The core interview in
[SKILL.md](../SKILL.md) and the [planning craft](../../shared/PLANNING-CRAFT.md) still
apply; these add the lessons learned for specific kinds of planning.

## Cancelled tasks

When the matching task was cancelled, separate permission to revisit its plan,
to reactivate it and to execute it; ask which boundary changes rather than reviving an
old execution grant. On reactivation reuse its ID and keep the cancellation in
history. If the owner instead requests a new replacement, add its successor with
`autowork tasks add`, then supersede the old task with `autowork tasks supersede ID
--by NEW --reason TEXT`;
preserve original acceptance/results without importing withdrawn scope. Report queue eligibility separately from execution authority.

## Validation-performance plans

First distinguish measured performance work from qualitative test-value cleanup.
For measured work, reuse existing phase receipts; ask once whether the goal is
release latency or developer feedback, restore correctness before optimizing,
keep an active frozen candidate untouched, then use one-variable experiments and
repeated passing full-gate times under matched conditions. A failing run is not a
performance baseline. Never invent an SLA or claim speedup without repeatable
evidence. For explicitly qualitative cleanup, follow
[simpler test cleanup](#simpler-test-cleanup-and-scope-reductions) instead of
carrying forward timing experiments. Preserve required behavioral coverage, not
necessarily redundant test identities. Planning launches nothing.

## Companion frontends and platform scope

1. Establish the product boundary before discussing implementation: distinguish an existing website, a native companion app, an embedded website and an additional browser build of the companion. A second frontend for the same backend is not automatically a WebView or a second web application.
2. Use concrete product names when asking about platforms. If a reply mentions keeping the existing website and adding the companion, clarify whether a separate Flutter browser build is also required; do not treat the word "web" as proof of that requirement or silently discard an earlier explicit platform choice.
3. Inspect existing page loaders, public APIs, role gates and shared UI patterns before proposing parity. A generic list endpoint may omit the page's filters, summaries, history, position provenance or privacy projection. Prefer shared server read models over duplicating queries or scraping framework-internal page data.
4. Settle frontend/platform scope before asking about hosting or designing cross-origin authentication. First-party cookie reuse, native session handling and cross-site browser access have different constraints; an unresolved deployment choice does not authorize a new token protocol, relaxed cookies or broad CORS access.
5. Once native versus embedded and feature depth are settled, save those answers in the existing planning owner before another consequential round when continuity would otherwise be lost. Mark only unresolved choices Open; do not restart discovery or make understood product scope look undecided. Keep cloud session/state independent of local-device connection state when the requested module must work without that connection.

## Simpler test cleanup and scope reductions

When the user chooses a simpler qualitative task, remove timing, benchmark,
repeated-run and speed-target requirements from its active contract; retain
correctness checks instead of the retired measurement campaign. Prefer one bounded
test-value cleanup over new measurement infrastructure in that scope. Inspect
unchanged test verdicts before edits. Require each deletion or consolidation to
identify duplicated behavior/assertions and the retained test protecting them;
low priority, similar names, coverage overlap or fewer tests alone never justify
losing unique regression, security, boundary or configuration protection. Keep
uncertain cases and report recommendations instead.

State whether low-priority items means test cases or repository tasks; do not
silently turn a test-cleanup request into unrelated backlog cancellation. If the
user requests a new simpler replacement, save the successor and supersede the old
task without marking its unproven outcome passed. Creating that replacement does
not implement it or dispatch a worker.

## Blockers and recovery

`/plan_with_me blockers [repo|runner name]`, or a request to work through what blocks
the queue, is [`/blockers`](../../blockers/SKILL.md): routine planning repairs first, then
genuine owner decisions, easiest first, one question at a time. An
answer that needs replanning is planned here, with the planning craft, and saved
with `autowork tasks` before the next question. The rest of this section applies to a
broader blockers question.

For a broad "blockers" request, separate owner-input blockers from everything
preventing delivery; an empty BLOCKERS.md does not prove execution is unblocked.
If scope is unclear, ask whether it means the current task, repository-wide
delivery or only owner decisions. Inspect the full task record, implementation and
execution evidence first; do not ask the user to decide facts or routine repairs.
For recovery planning, refresh the original task, review, target and delivery
state before decomposing: observed delivery can supersede a reported pending
integration, leaving only the remaining receipt or qualification gap.

## Pending-task lists

For a pending-task list, separate unresolved product
choices, recovery scope and live-operation gates; do not interview every task
or reopen settled deferrals and cancellations. Group tasks only when one shared
choice governs them, retaining each task's acceptance and separate operation gates.
Ask that shared choice once, record which tasks its answer governs and reuse it
throughout the batch. Do not turn a bare "yes" into approval of separate task
recommendations; clarify only affected unanswered choices. One pending task does
not hold independent accepted work.

## Landing pages, READMEs and onboarding

Settle audience, primary action and
first useful outcome before visual references; screenshots prove appearance, not
availability or conversion.

## Planning while teaching

When the user wants to learn a domain while planning (for example to present a
roadmap), confirm that audience and decision purpose. Teach one short concept the
next decision needs, its practical consequence, then ask the highest-impact open
question; neither an interview alone nor a full course up front. Shape roadmaps as
stages with deliverables, dependencies, roles, evidence gates and cost categories;
keep a stakeholder roadmap separate from deep lessons. Learning objectives are not
product acceptance. Revalidate inherited legal/regulatory or vendor claims against
primary sources with retrieval dates, labeling partial reads; API access is not a
usage right. A no-code instruction also covers docs-site scaffolding, config,
dependencies and UI; a suggested framework stays a candidate. Ask about public vs
private audience before choosing a publication layout; hidden URLs or robots rules
do not protect confidential content.

## Investor briefs

For an investor anteproject, separate the learning library, conceptual architecture
and executive presentation from a full implementation specification, binding quote
or investment plan. Capture the meeting horizon without inventing an exact date;
ask for the date only when it changes the delivery sequence. Plan a concise deck
with sourced findings, proposed capabilities, alternatives, dependencies, accountable
roles, cost categories and the next due-diligence decisions. Never present proposed
team capabilities, investor resources or expected permission access as verified facts.
Keep exhaustive source reconciliation as supporting work rather than silently making
it a prerequisite for every preliminary presentation; retain explicit research gaps
and do not weaken the later production acceptance gates.

## Jurisdiction and geography changes

When incorporation or operating geography changes, distinguish the incorporation
country, target player markets, physical-venue locations and hosting/data locations
before choosing legal research. Ask first about the unresolved player/venue market;
forming a company in one country does not establish gaming rights elsewhere. Keep
prior jurisdiction-specific PRDs as attributed references, not the new applicability
baseline. Leave unclear dictated company/regime names unresolved rather than
inventing a legal structure from transcription. Record a possible physical venue as
a scenario until selected, not as an automatic expansion of launch scope.

## Saving across a long interview

Keep the compact uncertainty map with the existing brief: resolved decisions,
planner calls, assumptions, and consequential open issues with their affected
tasks. After each answer, continue to the next issue that still changes intent or
acceptance, not an arbitrary interview length. On "stop/finish", end questioning
and save the resolved portion (chat only in no-write mode), with unresolved choices
explicitly open. On resume, read that state rather than repeating the interview;
corrections supersede prior proposals without erasing history. A skipped question
is not delegated or answered, and a delegated choice is not user acceptance.

Put accepted amendments before preserved historical
scope and reconcile affected Scope, Sources, Next action and recovery summaries;
otherwise a worker can obey a superseded prohibition or repeat a settled question.
Keep older anchors attached to their original content, not an empty heading above
a newly accepted sibling subsection.

After each successful interim integration, retain its exact bytes/hashes as the next
baseline. Extend that baseline with the next answer rather than re-merging the whole
accumulated proposal against the initial interview base; earlier accepted edits can
otherwise appear as competing changes. Refuse unexpected drift, preserve other
writers through targeted reconciliation and batch final checks once.

When an answer settles broad scope, mark it
settled in its decision owner and reconcile affected conditional tasks and summary
wording; leave only unresolved subchoices Open. Put the current scope and an
explicit supersession notice before preserved obsolete guidance. Reconcile an
investor-brief, jurisdiction or deadline change into the existing affected task and
goal records, not only the narrative plan. If a scheduled research job
still names the old scope, inspect its full saved instruction and disclose the
mismatch; update it only under existing scheduling authority, preserving cadence,
paused state, history and no-code/publication limits. A one-time commit/push request
does not create standing publication permission for future research runs.

## Continuations and live gates

Permission to plan a continuation does not launch it; Autowork has no token, cost or
time budgets to grant or extend. A shared live-campaign sequence
likewise grants no target access or mutation approval; retain per-operation gates.

When the user
splits offline implementation from live qualification, keep the implementation
task's ID, ownership and evidence, reuse or add the live follow-up with the original
operational acceptance, and keep the parent goal unverified; a split is not a waiver.

If an answer
authorizes a bounded continuation after another worker exits, record scope and wait
condition, then recheck that worker's terminal state: if satisfied, return the ready
continuation to the existing authorized coordinator for execution outside standalone
planning under existing scope and limits; otherwise keep one pending request for that
coordinator. Do not ask again for settled authorization or erase an explicit current
no-execution limit. A scope expansion to a shared runtime or upgrade stays conditional
on a supported candidate proving the required operations; planning acceptance permits neither the
upgrade nor job resumption, and preserves existing pauses. No new
scheduler, parallel backlog, automatic deployment or invented acceptance.
