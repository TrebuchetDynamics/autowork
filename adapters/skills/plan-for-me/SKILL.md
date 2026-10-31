---
name: plan-for-me
description: "Research and save a plan without an interview."
disable-model-invocation: true
---

# Plan For Me

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host-neutral Plan For Me workflow](../../../skills/plan-for-me/SKILL.md) first.

First read the [planning artifact and authority contract](../../../skills/shared/RESEARCH-PLAN.md),
then the [host contract](../COMMON.md) and
[planning craft](../../../skills/shared/PLANNING-CRAFT.md). Size the work first;
a clear task still needs a complete saved record. Finish the full requested batch,
with real dependencies, independent ready lanes and scoped unresolved choices.
Investigate relevant source, tests and existing decisions. Compare practical options, choose a supported approach and
record material reasoning. Ask only after investigating for consequential missing
intent or authority; continue independent planning. Do not reopen settled choices
or invent requirements.

Route from the request's meaning, not a short phrase list:

| Request | Route |
| --- | --- |
| No concrete objective; "plan this project"; "make it better"; a broad direction such as reliability or performance | Read [autonomous project discovery](../../../skills/plan-for-me/references/discovery.md), investigate the project, derive accepted and engineering goals, then save one executable frontier. Do not ask for a goal first. |
| A named outcome, feature, defect or accepted slice | Focused planning for that outcome and its authorized prerequisites; do not audit unrelated work. |
| Read-only, chat-only, no-write or dry-run | Match the route above but save nothing, including queue metadata. |
| An Autowork-owned substep | Stay inside the named task and authorized prerequisites; return to that same coordinator. |

A vague adjective is a direction for discovery, not an accepted outcome. Keep new
product directions as proposals until the owner accepts them; a project with no
accepted objective or meaningful source gets the missing decision reported, not an
invented roadmap.

For held or blocked work, read the existing task, latest runs and retained candidate
evidence; classify the observed source and phase:

- Resolve engineering planning choices within delegated scope, recording the
  supported approach and checks as the planner's call, not an owner question.
- If an existing task or candidate has a runtime, transport, gate or continuation
  failure without new product uncertainty, return the exact failed operation,
  task ID, attempt evidence and source-bound candidate evidence to the same
  coordinator for supported recovery. Report missing evidence as unassessed, never
  invented. Reuse the existing task and candidate: no new interview, replacement
  task or acceptance split just to get moving. Save new findings in the existing
  task; do not implement recovery or redispatch inside planning.
- Keep genuinely unavailable external, owner or physical-access inputs pending
  only on affected tasks, with the exact missing input and resume condition;
  continue independent authorized planning. Do not invent access or authority.

Split only when authorized scope and evidence justify decomposition, not merely
because runtime failed; preserve existing task IDs, contracts, acceptance and
history, and never silently waive acceptance.

Read the pinned [Autoresearch plan protocol](../../../skills/autoresearch/upstream/plan.md)
and apply the [planning adaptations](../../../skills/shared/RESEARCH-PLAN.md).
Use that protocol directly; do not route back through the Autoresearch adapter.
Research relevant code and evidence; routine planning needs no experiment.
Use [Docs Sync](../docs-sync/SKILL.md)'s existing capability/prepare flow on the
actual consumer before reconciling tasks; reuse its result while inputs are unchanged.
Do not call deferred conversion or activation-pending consumers ready; do not install
updates or interrupt workers to complete planning, or duplicate the conversion matrix.
Save accepted plans in their document owners and
complete task records with `autowork tasks add`/`goal`
([work center](../../../skills/shared/TODO-WORKCENTER.md)), including acceptance,
checks, dependencies, `touches` and Now/Next placement. A planning task the runner
handed you closes with `autowork tasks done ID --by WHO --reason TEXT [--evidence REF]`.
That is manual, not verified: it writes no receipt and does not by itself qualify a
goal or a verified prerequisite; use only an actual recorded owner waiver/qualification.
Its successor notes
`Plan round: N of M` with `autowork tasks field`. Planning does not implement or dispatch workers.
Explicit read-only/chat-only/no-write/dry-run requests save nothing. Record goals, non-goals,
anti-goals and every default as the planner's call. For focused tasks and discovered
frontiers, apply shared [decision closure](../../../skills/shared/PLANNING-CRAFT.md#decision-closure):
record planner calls and keep only genuinely owner/external-blocked affected tasks
pending. Run the builder check and persist each material finding's disposition in
the saved contract, then run `autowork tasks validate --worktree .` and commit the
batch once before reporting it ready. Report saved paths, task IDs, the
planner's calls and the next executable task, distinguishing proposals from ready work.

Use the [single-pass handoff](../../../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff):
resume accepted decisions and existing task IDs, investigate only missing evidence,
persist one affected batch, and reuse input-bound checks. Unchanged findings need
no new docs pass. After the commit, `autowork tasks why ID` reports committed-store
selection eligibility and position only, not resource/ownership admission, capacity
or dispatch. Report the actual selection result, or say selection was not assessed.
Distinguish a branch-local commit from delivery to the actual canonical consumer:
disclose whether that consumer includes the commit and whether selection was checked
there. Report runtime and ownership unassessed unless observed.
A saved plan is not dispatch, delivery or completed work.

Standalone planning stops here despite earlier unrelated
implementation permission. An Autowork-owned substep returns to that same
coordinator; no competing worker or execution inside planning. A later explicit
implementation instruction enters the execution workflow. The shared contract
does not require Hermes-native tooling or promise a hard sandbox on this host.
