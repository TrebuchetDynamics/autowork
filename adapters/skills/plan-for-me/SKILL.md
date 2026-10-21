---
name: plan-for-me
description: "Investigate a repository, choose a supported approach, and save a plan and TODO tasks without an interview."
disable-model-invocation: true
---

# Plan For Me

First read the [planning artifact and authority contract](../../../skills/shared/RESEARCH-PLAN.md),
then the [host contract](../COMMON.md) and
[planning craft](../../../skills/shared/PLANNING-CRAFT.md). Size the work first;
a clear task still needs a complete saved body. Finish the full requested batch,
with real dependencies, independent ready lanes and scoped unresolved choices.
Investigate relevant source, tests and existing decisions. Compare practical options, choose a supported approach and
record material reasoning. Ask only for consequential missing intent or authority;
continue independent planning. Do not reopen settled choices or invent requirements.

Read the pinned [Autoresearch plan protocol](../../../skills/autoresearch/upstream/plan.md)
and apply the [planning adaptations](../../../skills/shared/RESEARCH-PLAN.md).
Use that protocol directly; do not route back through the Autoresearch adapter.
Research relevant code and evidence; routine planning needs no experiment. Save accepted plans and complete
TODO.md tasks through [Docs Sync](../docs-sync/SKILL.md), including acceptance,
dependencies, `Touches:` and Now/Next ordering. Planning does not implement or dispatch workers.
Explicit read-only/chat-only/no-write/dry-run requests save nothing. Record goals, non-goals,
anti-goals and every default as the planner's call, and run the builder check on
the saved tasks and lint them with `goals.py plan-lint <repo> --tasks IDS` before reporting them ready. Report saved paths, task IDs, the
planner's calls and the next executable task, distinguishing proposals from ready work.

Use the [single-pass handoff](../../../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff):
resume accepted decisions and existing task IDs, investigate only missing evidence,
persist one affected batch, and reuse input-bound checks. Unchanged findings need
no new docs pass. Standalone planning stops here despite earlier unrelated
implementation permission. An Autowork-owned substep returns to that same
coordinator; no competing worker or execution inside planning. A later explicit
implementation instruction enters the execution workflow. The shared contract
does not require Hermes-native tooling or promise a hard sandbox on this host.
