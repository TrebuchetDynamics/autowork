# Installed Pi RPC delivery pilot — proposed 2026-10-24

Owner: [TOOLSET-389](../../tasks/items/TOOLSET-389-6dedfd8c.md).
This is preparation, **not pilot authorization, an executed result or fleet
qualification**. Keep the task owner-owned, Needs decision and `live = "denied"`
until the target, bounded model use and interruption window are explicitly accepted.
[TOOLSET-390](../../tasks/items/TOOLSET-390-e1c2afa6.md) now depends on this gate;
source integration alone must not release coordinator steering work.

## Current evidence boundary

The installed Autowork coordinator was observed selecting release
`8b99850e52dc55f2fc63d41b46afde2c43630845`, whose default transport is RPC.
The existing private SDK interpreter reports `pi-agent-python-sdk` 0.2.6 and
installed Pi reports 1.4.0. Read-only process/metadata inspection did not yet find
an RPC invocation attributable to that coordinator; retained workers and the most
recent completed run still lacked RPC transport/version/cleanup evidence.
**Selected release and configured next-invocation transport are not execution
proof.** Existing workers may retain their older release across coordinator reload.
These are a dated observation, not a claim about later fleet state.

TOOLSET-388 already has a documentation-only reconciliation candidate
`965ed8f00db0077df849dd4ac47c2062d753af20`, tested against unchanged runtime source
at `8b99850e`. Its worker report records 166 focused tests, 138 legacy engine tests
(two expected failures), 167 integration tests and five direct native offline
protocol tests. It is still subject to independent engine verification,
serialized integration and merged-tree checks. Do not duplicate its implementation,
edit its live checkout, manually close its task or treat its report as acceptance.
The historical [qualification report](pi-rpc-qualification-2026-10-24.md) preserves
the distinction between fake-peer, native-offline and real-model smoke evidence.

## Proposed target and authorization

Prefer **one new disposable standalone repository**, with no Git remotes,
production configuration or existing task state, using the installed release's
supported foreground `--until-empty --workers 1` runner. Its task worktrees belong
under that repository's own canonical `.worktrees/`. Use an isolated private state
root and explicitly select the existing pinned SDK interpreter; do not install,
modify or restart any of the seven existing services. This qualifies the installed
CLI/engine path, not systemd rollout or fleet acceptance.

The owner decision must name the exact private target/state paths, executor,
window, maximum model-run/time budget and permission for the controlled
interruptions below. Proposed ceiling: four worker/reviewer case pairs (normal
RPC, recovery RPC and matched JSON controls), with no extra fallback/model runs
without a recorded budget decision. If the owner instead chooses an existing
service, obtain its actual writer handoff and preserve all work/attempts first;
the disposable-target proposal does not authorize interrupting that service.

## Preconditions and frozen manifest

1. TOOLSET-388 has genuine coordinator-verified closure and its exact integrated
   revision passes the required offline gate. Preserve the raw full-check result,
   command, exit code, revision/tree, skips and expected failures. An in-progress
   check or pass on an earlier revision is not a substitute. Reuse an already
   running matching check rather than launching a competing duplicate.
2. Pin the installed release selected for the pilot. Record resolved entrypoints,
   source tree, effective transport, Pi executable/version, SDK executable/version,
   model and relevant safe settings. Recheck readiness without a model call.
3. For this target only, require `PI_AUTOWORK_PUSH=0`,
   `PI_AUTOWORK_STEERING=0`, review/validation enabled, optimistic integration off,
   bounded runtime/retries and updates disabled through the supported
   `PI_AUTOWORK_UPDATE_INTERVAL=0` setting. Verify effective settings after saved
   repository configuration is applied. Do not change global/fleet settings.
4. Freeze a small deterministic engineering task, checks and exclusions, including
   observable work markers and an independent reviewer. Record baseline, contract
   hash and expected files before admission; a prompt-only echo is insufficient.
   Model transport is the only intended remote use; no deployment, data services,
   publication, protected corpus or credential modification.

## Required cases

### Normal installed-engine closure

Use the real installed launcher, engine, worker and independent reviewer. Capture
admission, slot/attempt ID, worker report/candidate, reviewer identity and session,
checks, integration commit and native closure receipt. Correlate the actual RPC
process/progress and completed run metadata to that attempt. Require SDK/Pi pins,
settlement and complete cleanup evidence; task/model prose is not a receipt.
The task must reach verified closure through the engine, not manual `tasks done`.

### Interrupted-attempt recovery

First establish exact ownership and process birth identities for this disposable
coordinator and its accepted worker. At an observable bounded checkpoint, record
the slot, session, task/contract hash, worker identity, partial work and descendant
ownership. Interrupt only the authorized pilot coordinator through the supported
lifecycle; a crash case requires separate explicit permission for the precise
owned process and failure window. Never kill an unrelated worker or guard.

Restart only the same pilot against the same state. Verify engine reconciliation
adopts the existing live worker where applicable, preserves the accepted attempt,
partial work and session, and creates no competing worker or duplicate task
execution. Correlate receipts rather than merely counting process starts. If the
worker was aborted, acceptance is uncertain or cleanup unproven, the correct
result is a retained technical hold—not forced retry or a switch to JSON.
Record that limit honestly; do not call a held run recovered completion.

### Matched JSON comparison

Only after RPC processes are settled and cleanup proven, use fresh equivalent
baseline/contract/session cases with explicit JSON selection. Never replay the
RPC accepted session in JSON. Keep model, task complexity, checks, reviewer and
budget comparable. If a safe matching recovery case cannot be run, mark that
comparison missing rather than altering the failure scenario to get a pass.

## Evidence, abort and exit criteria

Keep raw histories, prompts, process identities and private state outside Git.
Publish only sanitized revision-bound evidence: complete engine chain, independent
review, exact checks, recovery/duplicate-dispatch observations, cleanup, wall time,
startup/tool/recovery latency, retry/intervention counts and quality coverage.
Separate partial token subtotals from complete totals; unknown billed spend stays
unknown. Four small cases cannot establish fleet reliability or performance gains.

On contract drift, unexpected side effect, budget exhaustion, duplicate ownership,
uncertain acceptance or missing cleanup proof, stop new admissions, retain all
artifacts and report the exact failure. Do not erase attempts, clear holds, weaken
checks or enable JSON automatically. Explicit rollback is for a future invocation
only after reconciliation and proven cleanup.

Close TOOLSET-389 only when its acceptance is actually covered, with missing
measurements or live evidence explicitly remaining open. Then, and only then,
admit TOOLSET-390's control-channel implementation. Automatic steering remains
off until its separate bounded policy/channel qualification succeeds.
