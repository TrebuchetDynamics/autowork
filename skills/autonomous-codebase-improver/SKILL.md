---
name: autonomous-codebase-improver
description: "Use when improving a repository across multiple work lanes."
license: MIT
---

# Autonomous Codebase Improver

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Use for open-ended improvement across correctness, security, performance, design,
UI/accessibility, reliability, tests, delivery and docs. Not a second runner,
scheduler or replacement for Autowork. A known defect, fixed plan or audit-only
request keeps its narrower workflow.

Read the [host and authority adaptations](../shared/PI-TOOLSET.md), then the pinned
[campaign protocol](upstream/PROTOCOL.md) and relevant selection/recovery references.
This adapter overrides their Pi-only worker requirement, repeated approval
ceremonies and separate conversation-only task-state convention. Autowork owns
the task store, execution, review and acceptance.

## Current-session campaign

1. Orient on repository tasks, actual source, ownership and checks. Establish scope,
   non-goals, explicit limits and prior authorization. Default to continuous work
   **within this session**; an explicit one-improvement request stops after one.
2. Rank at most three evidenced candidates by consequence, confidence, reversibility
   and validation cost across applicable lanes. Record coverage and deferred leads
   in existing task receipts. Refresh an underexplored lane after at most two
   accepted slices or investigation-only steps; do not manufacture edits for coverage.
3. Choose one bounded task with acceptance and checks. Reuse accepted decisions and
   routine local implementation authority. Park genuinely gated work with an exact
   missing decision; continue independent authorized work rather than retrying a hold.
4. Establish recoverable baseline and sole-writer ownership. Use the host's supported
   execution path. Discover real capabilities, not assumed Pi agent names. If
   independent review required by this campaign cannot be obtained, do read-only
   discovery and report that blocker before starting a slice.
5. Validate the actual slice delta, obtain fresh independent review, resolve findings
   and verify acceptance. Worker success is not acceptance. Unknown active writer
   status retains ownership; stop rather than launch a replacement or reset files.
6. Emit a progress receipt, refresh candidates/coverage and continue within limits.
   An empty shortlist triggers a fresh bounded discovery pass. No further actionable
   candidates after that pass, all useful work genuinely gated, pause/stop or an
   explicit limit produces a truthful terminal receipt, not invented completion.

Ordinary child workers never inherit this controller or delegate. Tools that write
caches or test outputs also need exclusive ownership. Missing delegation alone is
not a requirement to install pi-subagents: follow the shared host translation.

**Receipt:** task/title and selection reason; baseline → actual result; paths,
checks and review disposition; accepted/rejected slices; ownership/run status;
coverage and blocked leads with revisit conditions; next action or stop reason;
commit/integration/push/live evidence separately.

**Example:** after accepted A, continue authorized independent B. If the user said
“one improvement,” checkpoint after A with B pending. A pause prevents new launches.
Upstream evaluation results are not evidence that this adapted campaign ran.

[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).
