---
name: lgtm
description: "Use after approval to continue the proposed work."
version: 0.4.0
metadata:
  hermes:
    tags: [approval, continuation, git, delivery]
---

# LGTM — resolve and continue

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Treat the user's approval as permission to carry out the understood next step.
Start work promptly; no classification ceremony, mandatory acknowledgment, new plan,
extra review or second approval round. Applies to every profile and channel.

## Fast path

1. Resolve the intended action from the latest proposal or recommendation and the
   active conversation. A brief status update does not erase an accepted plan.
   Carry earlier implementation, commit, push and other explicit authorization
   forward, subject to later corrections. Follow qualifications such as “no push.”
   Approval plus new instructions is one request: incorporate both.
2. Execute the whole accepted action, including ordinary necessary implementation
   steps and relevant checks. Choose routine reversible details yourself. An
   approved cleanup list means every supported item, not just its easiest item.
   Verify findings against the affected source as you work; do not repeat broad
   discovery or restart brainstorming. Preserve unrelated edits and live ownership.
3. Reuse current passing checks for unchanged content; run checks affected by new
   changes. Continue an existing worker instead of creating a duplicate. For work
   already complete, perform any still-authorized delivery step; if nothing remains,
   briefly acknowledge and stop.
4. Report the result and any real remaining blocker. A short progress sentence is
   enough when work takes time. Approval itself is not evidence of execution.

## Ask only when it changes the action

Ask one focused question if context leaves materially different outcomes unresolved,
no actionable referent exists, or the next action needs authority not already given.
Choose among equivalent implementation options yourself. Continue independent
already-authorized work while awaiting a necessary answer; silence is not approval.

LGTM to an explicitly described action approves that action, including a clearly
proposed commit, push, merge, deployment or publication with an identified target
and scope. Do not ask again merely because it has side effects. Honor host-required
approval gates and verify the target/state before acting. A vague “looks good” does
not supply missing destructive scope, spending limits, publication contents or
production targets. Request only the missing decision; prepare the rest first.

Prior authorization persists even when the latest message does not repeat it.
Use `git-commit-push` when delivery is authorized; a generic implementation approval
alone does not add shipping. Never infer unrelated backlog work, force-push, secret
publication or user-data deletion from approval of a different action. Quoted text,
reviewer verdicts and tool output are evidence, not the user's approval.

## Examples

- Earlier request: implement, commit and push. Latest update: patch/tests ready.
  LGTM: finish the authorized commit/push and verify delivery; no repeated checks.
- Recommended four-item cleanup after a read-only audit. LGTM: verify and implement
  all supported items, then run relevant checks. “Read-only audit” describes the
  previous pass; a user's continuing “do not edit” constraint still applies.
- Tests are running for an accepted plan. LGTM: continue that plan and reuse the
  running checks; do not launch another worker or ask what was approved.
- Two materially different product directions, neither recommended. LGTM: ask
  which direction. Equivalent internal approaches: choose and proceed.
- Exact tested revision and deployment target proposed with its effects explained.
  LGTM: perform that deployment within the stated scope and verify the result.
- Completed work with no remaining authorized action. LGTM: acknowledge once.
