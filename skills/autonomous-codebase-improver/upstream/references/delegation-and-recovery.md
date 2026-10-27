# Delegation and recoverable slices

## Discover, then delegate

This is parent-only guidance. Never pass the campaign controller to ordinary children or enable child delegation to work around a missing parent capability.

Assumption: this repository pins pi-subagents **0.40.0**. The examples below match its installed `src/extension/schemas.ts` and README; the **current exposed tool schema and executable discovery results are authoritative**. Reading installed source is not a live capability check. Before launch inspect available tools, use supported agent listing, and inspect resolved roles/restrictions; use supported read-only diagnostics when availability or waiting is unclear. Listed-but-restricted agents are not executable. Do not create agents, install tools, widen allowlists/depth, change models, or increase budgets merely to keep running.

Required roles:

- **Scout:** read-only, distinct lane/seam, known evidence, and decision to resolve. Use when evidence is missing/stale; reuse valid evidence rather than launch every slice.
- **Worker:** sole writer for one bounded approved slice or synthesized fix. Return actual edits, commands with outcomes, undone work, risks, and decisions needing approval. No child delegation, shipping, scope expansion, or hidden external work.
- **Fresh reviewer:** read-only independent run, explicitly fresh context, actual current-slice delta plus live files and checks. Review intended outcome, correctness/safety, regression protection, and evidence quality. Never rely only on worker reasoning.
- **Parent:** selects, resolves approvals, owns lifecycle/ownership, validates, dispositions findings, and accepts. Parallelism is limited to independent read-only work; tests that write caches/build outputs also need exclusive mutation ownership.

Equivalent discovered roles are usable only with these explicit task contracts and appropriate capabilities. Missing worker/fresh-review capability or exhausted spawn capacity blocks implementation: report what is missing, preserve state, no solo fallback. Do not start another slice when required review cannot be obtained.

## Bounded tool examples

Only use these shapes if exposed. Agent names below must first resolve to executable roles. Absolute cwd and brief paths stand for the actual bounded work, not literal placeholders to run.

```typescript
subagent({ action: "list" })
subagent({ action: "doctor" }) // read-only diagnosis if needed
subagent({
  agent: "worker",
  cwd: "/absolute/repo",
  task: "Implement approved item A from the supplied brief only. Allowed paths, design, baseline location and checks are in that brief. Sole writer; no delegation or shipping. Escalate unapproved decisions. Return changed files, checks/outcomes, risks and undone work.",
  async: true
})
```

Supply the actual brief/design and recoverable baseline before invoking the worker. Keep role defaults unless an authorized override is needed; never apply tight hard tool/turn/usage budgets to mutation-capable workers. Track the returned run ID immediately. Async is useful for independent parent reading or validation preparation, **not concurrent edits**.

```typescript
subagent_wait({ id: "returned-run-id" })
subagent({ action: "status", id: "returned-run-id" })
// Only after the worker is quiescent, its delta reconciled, and checks captured:
subagent({
  agent: "reviewer",
  cwd: "/absolute/repo",
  task: "Read-only review of item A: inspect the supplied pre/post slice delta, live changed files, approved design, checks and baseline results. Look for regressions and unmet acceptance; return severity, location, consequence and required fixes. Do not edit or delegate.",
  context: "fresh",
  output: false,
  async: true
})
```

Use the runtime's supported waiting mechanism when this run-to-completion campaign needs the result; no sleep/status polling loops or final answer merely to wait. A wait timeout leaves the child running. Attention notifications are not terminal state. If waiting is disabled/unavailable, do not spin: use supported completion delivery or make a truthful handoff retaining ownership. Foreground calls can detach too: answer a supervisor question, then wait for that same run; do not resume/relaunch while detached.

## Ownership release: all exits, not just successful completion

Record one writer owner per cwd: slice, run ID, allowed paths, start baseline, known lifecycle, and in-flight mutation status. Retain that owner across **wait/run timeouts, detach, child/tool error, failed startup with uncertain status, cancellation, pause, session interruption, lost response, and handoff**.

Release only after both conditions are evidenced:

1. The run has ended or is demonstrably stopped, and all in-flight tools/processes capable of mutation have finished. A cancellation acknowledgement, failed tool return, or terminal label alone does not prove an already-started shell/background process is quiescent.
2. Capture actual post-run state, inspect changes against the slice baseline, classify unexpected paths, and reconcile the delta/check status. Partial implementation is not automatically accepted.

Until release, **no replacement/competing writer, resume that creates an additional writer, rollback, unrelated new write, or mutating validation**. Unknown or still-running/detached status retains ownership and does not permit resume. Use supported status/transcript/wait/control evidence; if quiescence cannot be established, stop with a blocked handoff carrying run IDs, baseline location, known tools and uncertainty. Do not start a new campaign on the same cwd to escape the lock.

**Paused continuation is not ownership release.** On explicit user resume, a confirmed paused run may continue its same approved slice only after all in-flight mutation-capable tools/processes have finished and its actual delta/check status and any intervening user edits are reconciled. Refresh current files and stale evidence first. Use the supported same-run resume, retaining exclusive ownership throughout; if the runtime returns a continuation run ID, transfer the existing ownership record to that ID without a gap or competing/new writer. A paused label alone is not proof of quiescence, and unresolved overlap blocks continuation.

Pause/stop blocks new launches immediately. Where exposed, `subagent({ action: "interrupt", id: "..." })` soft-interrupts into a resumable paused state; establish quiescence and reconciliation before continuation. Supported `subagent({ action: "stop", id: "..." })` terminally stops current-session async work; stopped runs are **not resumable**. Establish the release conditions before claiming safely stopped or replacing that writer. Campaign continuation after a terminal stop requires explicit user intent and a new bounded run only after ownership release and refreshed evidence. Generic `/goal` controls are not assumed to control this skill or its children.

## Lightweight baseline and compare-before-rollback

Use recoverable copies or a suitable local snapshot already available—**not just hashes, `git status`, or a HEAD diff**. Keep snapshot storage private, outside repository discovery/package roots (for example, a task-specific OS temp directory); record its absolute path and retain it through review/recovery/handoff. Do not build a transaction engine. Do not include secrets in reports or add backups to the package.

Use this sequence for each slice; before a fix-worker launch retain original B and capture an additional pre-fix checkpoint rather than replacing B:

1. With mutation ownership settled, record dirty tracked/untracked paths and inventory the allowed write surface. Preserve **B**, the pre-slice bytes and path state: existing/absent, file/directory/symlink target and executable mode where relevant. Capture existing untracked files, binary contents, and prior accepted uncommitted slices. Enumerate proposed new paths as absent; snapshot any existing directory that a permitted operation might replace. If the surface cannot be bounded/recovered, narrow it or stop before mutation.
2. Worker stays inside that surface. New paths/scope require parent reconciliation and recoverable pre-change state before expansion. Baseline commands that generate outputs must also be accounted for; retain B and capture the worker's starting state after them as well. Preserve their command results separately.
3. After quiescence preserve **W**, the actual post-worker state, including deletions/new paths, and inspect **B → W**. This is the review delta; `git diff HEAD` may combine multiple accepted uncommitted slices and omit untracked files. Give the reviewer the recoverable states/delta and relevant live files. Follow-up fixes retain the original B and capture a new W after each reconciled run. A runtime `failed`/`no-edits` or mutation-missing label does not prove absence of filesystem effects: a safety fixture produced verified shell/Python edits without a recorded native edit tool. Reconcile actual B → W before retrying, even when no native edit tool was recorded; the same quiescence and approval requirements still apply.
4. Account for parent validation output changes separately. If checks mutate reviewed content, refresh W and review the changed delta. Before acceptance confirm live state still matches the reviewed state on slice-owned paths; unexplained changes require reconciliation/re-review, not an acceptance claim.

If checks regress or review rejects the slice (including non-regression rejection or round-cap exhaustion), repair within approved scope or remove **only** its owned delta before new implementation. To remove it:

- First satisfy the ownership-release conditions. Capture current **C** and compare contents/path state of every intended restore/delete target to the last reconciled W. Check path types/ancestors too; do not follow a newly substituted symlink or recursively delete a directory containing new user files.
- If C differs from W on a target, or ownership is uncertain, **stop rollback**. Preserve snapshots and external edits; seek reconciliation. Never infer that all current changes belong to the child. Unrelated user files outside the delta remain untouched.
- Only when targets still match W restore B for those targets; delete only a slice-created path still matching W whose B state was absent. Preserve previous accepted uncommitted slices and pre-existing untracked files. Never use `git reset`, `git checkout --`, blanket `git restore`, or whole-tree cleanup to recover a slice.
- Validate restoration against B and rerun relevant baseline checks; distinguish pre-existing failures. Record rejection/recovery and release ownership before continuing independent work. If safe removal cannot be proved, hand off blocked rather than stack another implementation on an abandoned delta.
