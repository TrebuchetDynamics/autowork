---
name: plan-for-me
description: "Investigate a repository, choose a supported approach, and save a plan and tasks without an interview."
disable-model-invocation: true
---

# Plan For Me

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

Read the pinned [Autoresearch plan protocol](../../../skills/autoresearch/upstream/plan.md)
and apply the [planning adaptations](../../../skills/shared/RESEARCH-PLAN.md).
Use that protocol directly; do not route back through the Autoresearch adapter.
Research relevant code and evidence; routine planning needs no experiment. Save accepted plans in their document owners and
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
no new docs pass. Standalone planning stops here despite earlier unrelated
implementation permission. An Autowork-owned substep returns to that same
coordinator; no competing worker or execution inside planning. A later explicit
implementation instruction enters the execution workflow. The shared contract
does not require Hermes-native tooling or promise a hard sandbox on this host.
