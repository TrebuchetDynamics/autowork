---
name: autowork
description: "Coordinate repository work: plan missing tasks, implement a useful slice, verify and commit locally."
---

# Autowork

Read the [host contract](../COMMON.md). Use this host's native tools for execution.
Do not launch Hermes workers, require Hermes profiles, or depend on a native Kanban
card. Run in the current session; delegate only when available and appropriate under
the user's instructions. Use a separate worktree when real concurrent writes need
isolation, and preserve all unrelated edits.

1. Read repo instructions, TODO.md, accepted plans and current changes. Reconcile
   active work and approved candidates before choosing another task. Finish authorized
   closeout after checks/review; local integration and publication are distinct.
2. Choose a dependency-ready accepted task. If none exists, inspect a bounded seam
   for a useful bug, test, UI, documentation or refactoring improvement. Use
   [Plan For Me](../plan-for-me/SKILL.md) only when planning/research is needed;
   an obvious repair needs no extra ceremony. Record a complete TODO task via
   [Docs Sync](../docs-sync/SKILL.md), then execute within the user's scope.
3. Implement the smallest useful slice, run discriminating checks, fix failures and
   satisfy required review. Separate offline implementation from live qualification.
   Use installed specialist skills only for concrete gaps, not a mandatory phase chain.
4. Commit attributable verified work locally unless forbidden. Use ordinary Git and
   the repository's conventions; do not manufacture a Hermes card or receipt. Follow
   repository integration policy and existing authority. Push/deploy requires its
   own authorization; never override host approvals or actual live-safety gates.
5. Reconcile task status and evidence in TODO.md and any existing goals.json. Do not
   close a whole feature from a partial slice. Report completed task, checks, commit,
   next task and exact remaining blocker. Default is one completed slice; continue
   across tasks when the user's mandate explicitly requests it.

If preparation stalls on unclear prerequisites or changing local dependencies,
invoke [Plan For Me](../plan-for-me/SKILL.md) yourself in this session. Classify the
inputs, choose a supported in-scope route, update TODO.md through Docs Sync and
retry execution. Preserve no-commit restrictions and active writers; never import
foreign edits. Reuse an unchanged recovery plan's next action instead of replanning.
No separate user planner command or implementation reconfirmation is needed.

For repeated blockage, repair the ordinary metadata/environment issue, choose
independent accepted work, or identify one precise missing external input. Do not
repeat the same audit or treat an old ownership label as perpetual denial. Never
claim unattended scheduling, independent review or live qualification without evidence.
