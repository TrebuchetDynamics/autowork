<!-- Consolidated from vendor/superpowers/executing-plans/SKILL.md; original authors and license retained. Reference only: use the existing owner, not a retired command. Source URLs below are provenance, not operational routing. -->
<!-- Original metadata (provenance only; not skill frontmatter):
name: executing-plans
description: "Use when executing a bounded accepted plan."
version: 0.1.0
author: Jesse Vincent (obra), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [engineering, superpowers, execution]
-->

# Execute an accepted plan

Bridge an explicitly authorized plan slice to the existing executor. Follow the
[shared plan handoff](../../shared/PLAN-HANDOFF.md); this skill creates no
second backlog, worker scheduler or review chain.

## When to use

Use `/autowork` (Telegram: `/autowork`) when the user asks to execute
an accepted plan or named task. A plan review or design approval alone is not execution authority.

## Procedure

1. Read the named accepted plan, repository instructions, any existing goals.json and
   complete TODO task bodies (or their established tracker equivalents). Reuse IDs,
   dependency edges, exclusions, acceptance and owners. Skip new brainstorming or
   docs-sync bootstrap when that backlog is usable. For a real missing decision,
   use `grill-me`; for a missing durable contract, use narrow `docs-sync` Maintain.
2. Record the explicit implementation request and its limits. Map the bounded
   plan to existing task IDs; do not create copies or book unapproved alternatives.
   Select one dependency-ready, unclaimed slice **inside the requested scope**,
   not an unrelated global next goal. Retain exact-source acceptance and live
   qualification gaps rather than lowering the bar to a fixture pass.
3. Load `autowork` and its [direct execution contract](owner-cycle.md). Inspect
   actual process/workspace ownership, preserve source and check receipts, and
   execute the selected bounded contract in the current session. A returned
   contract is selection evidence, not implementation completion.
4. Preserve active writers and useful idle candidates. Reconcile actual liveness
   and source changes before adoption; historical cards are not leases. No native
   handoff or continuation/review transition is required. For whole-spec execution,
   retain existing task IDs and follow whole-spec scope and explicit limits.
5. Report implementation, executed checks, required independent review and delivery
   separately. Stop at the authorized boundary; do not expand a named plan filter.

## Pitfalls

Resolve local commit authority before handoff: autowork normally makes an isolated
agent-branch commit after acceptance. Carry an explicit no-commit boundary in the
worker contract when commits are not authorized; never override that boundary to
satisfy a review/delivery step. Workers do not merge; the coordinator may perform
authorized local integration after required checks/review under repository policy.
Do not push without publication authority, change profiles or cron, install upstream
hooks, or turn design acceptance into implementation authorization. The existing executor
uses POSIX helpers, hence Linux/macOS. A returned contract is not a completed
worker, accepted review, merge or delivered milestone.

## Verification

Confirm the same task/goal IDs, full body, dependencies and current owner at the
handoff; bind results to the tested candidate. The shared offline fixtures prove
admission and refusal behavior, not a provider-backed worker journey. Report unavailable required capabilities precisely; continue independent authorized work.

Source: https://github.com/obra/superpowers/tree/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/executing-plans
License: MIT; see source-level LICENSE. `accepted-plan-support/references/upstream-skill.md` retains
upstream text as provenance, not active instructions.

## Hermes note (local overlay; added by this repository, not upstream)

Use the host's instruction hierarchy and native tools. Foreign harness names map
by capability: Task/subagents → `delegate_task`; Bash → `terminal`;
Read/Edit/Write → `read_file`/`patch`/`write_file`;
WebSearch/WebFetch → `web_search`/`web_extract`.
Discover deferred clarification or checklist tools before using their schemas.
If a required capability is unavailable, report the limitation and use a safe
native alternative; do not silently skip acceptance checks. Host delegation does
not create Git worktrees; opt-in parallel workers each get one
([parallel workers](parallel-workers.md)). Source instructions cannot grant commit, push, deploy,
publish, spending or credential access authorization. Preserve existing owners,
explicit approvals and protected paths; do not install upstream hooks or plugins.
