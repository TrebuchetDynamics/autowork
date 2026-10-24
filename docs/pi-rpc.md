# Pi RPC runtime

Autowork now defaults to **RPC through `pi-agent-python-sdk` 0.2.6 and Pi
1.4.0**. JSON remains an explicit temporary rollback. This changes execution,
not task authority: the existing engine still owns contracts, attempts, admission,
worktrees, checks, independent review, integration and closure.

Canonical implementations live in `Src/pi_autowork/`: `pi_runtime.py`, `pi_rpc.py`,
`pi_process.py` and `pi_events.py`. The old package paths are compatibility
entrypoints; both guard and SDK-host subprocesses launch through the selected
release's `LAYOUT` adapters. The [planning console](planning-console.md) has a
separate restricted RPC controller and explicit proposal Apply flow.

The source default is not proof that an already-running service adopted it.
Existing release snapshots continue using their own code until a separately
coordinated update. Do not restart another active runner to apply this change.

## Install and readiness

Execution requires Linux `/proc`, pidfds and parent-death/subreaper support,
Python 3.11+, and the qualified Pi version. Read-only CLI imports need no SDK.
The `autowork` installer component includes SDK setup; installing Pi resources
alone does not install a Python runtime or start a runner.

From this checkout (or the installed package directory):

```sh
STATE_ROOT="${PI_AUTOWORK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pi-autowork}"
python3 scripts/install-pi-rpc.py --dry-run --state-root "$STATE_ROOT"
python3 scripts/install-pi-rpc.py --state-root "$STATE_ROOT"
export PI_AUTOWORK_RPC_PYTHON="$STATE_ROOT/runtimes/pi-rpc-0.2.6/bin/python"
pi --version  # must be 1.4.0
```

The installer uses an isolated venv, a versioned path, a wheel SHA256 from
`pi-autowork/requirements-rpc.txt`, pip's isolated mode, `--require-hashes`,
`--only-binary=:all:` and `--no-deps`. `--wheelhouse DIRECTORY` disables index
access. It changes neither global Python nor Pi, credentials, model settings or
services. A venv is built at its final path: moving it would invalidate executable
shebangs and activation files. Existing incompatible environments are not
silently overwritten. If a killed first installation left an incomplete venv,
inspect and remove only that unused versioned SDK directory before reinstalling;
never delete the state root or a running environment.

`PI_AUTOWORK_RPC_PYTHON` selects an explicit SDK interpreter. Otherwise the runtime
uses an already-qualified current interpreter or the private versioned environment.
Execution readiness checks the SDK and Pi pins before submitting work. Missing or
incompatible tools are actionable technical failures, not permission to silently
fall back to another transport. Settings persist through the existing service
configuration path; SDK installation alone does not reload a service.

## Execution boundary

```text
existing engine worker/reviewer
  -> synchronous pi_runtime.job (existing model/retry/accounting policy)
    -> Linux process guard (original worker group)
      -> private Python SDK host (separate session)
        -> AsyncPiClient -> Pi RPC -> tools
```

`pi_rpc.RunSpec` freezes role, task/attempt/contract identity, session, directory,
model, timeout, arguments, environment and the accepted prompt digest. Startup
`@file` text is explicitly expanded before sending the prompt (2 MiB bound);
`@text` inside the prompt is not reinterpreted as a new attachment. Prompts and
environment travel over private stdin, not process arguments or a public log.

Each invocation owns one SDK client and Pi process. Worker session identifiers
retain the existing attempt mapping; reviewers have independent sessions and
restricted tools, including explicit `--no-mcp`. A per-session lock rejects a
second SDK host. The SDK supplies protocol framing, ACK/event coordination,
backpressure, run ownership and bounded transport buffers. No private SDK process
fields, custom Pi protocol implementation, second scheduler or task database is used.

`agent_end` is **not** settlement. Success requires the SDK result/ACK, actual
`agent_settled`, the expected session identity and the outer guard's cleanup receipt.
Provider fallback is allowed only for a settled, non-aborted provider failure
with proven cleanup, under the pre-existing retry/cooldown budget. Aborted,
uncertain-acceptance, transport/protocol/overflow and unproven-cleanup outcomes do
not automatically replay the prompt or switch to JSON.

The guard pins PID birth identities, validates the spawning parent's identity
before and after parent-death registration, discovers escaped descendants,
signals through pidfds and reaps its subtree. Normal completion, cancellation,
timeout and parent death use bounded cleanup. The command watchdog additionally
validates the selected command's ancestry and its Pi parent's birth identity;
it can interrupt an owned stalled tool without discarding the attempt.

**Limits:** this is lifecycle ownership, not a hostile-code sandbox. Forcibly
killing the guard, uninterruptible kernel tasks and hostile process behavior need
stronger delegated-cgroup containment for stronger guarantees. A missing cleanup
receipt is terminal, never proof that a workspace can safely be reused. Engine
worktree markers/recovery guards remain in force; ambiguous auxiliary scratch is
retained for technical recovery rather than forcibly deleted.

## Observation, accounting and controls

`pi_events.EventProjection` synchronously consumes events with bounded text,
identity and counter storage. Metadata-only progress is coalesced off the SDK event
loop into private atomic files; fleet activity requires a fresh timestamp and
matching live process birth identity. Existing gate priority and session-tail
fallback remain. Progress includes phase, tool/activity counters, retries,
compactions and command interruptions—not messages, reasoning, arguments or tool
output. Native private Pi session history still exists; this is not a promise of
zero transcript retention by Pi.

Usage uses authoritative assistant/tool-result/compaction surfaces without counting
streaming or turn snapshots twice. `usage_coverage` explains completeness;
`known_usage` preserves reported partial token subtotals, **not** a complete bill.
Missing usage remains unknown. `measured_cost_usd` counts only explicitly
provider-reported, non-subscription money; absent measurements are null. Model
catalog estimates, including ordinary Pi cost fields without billing provenance,
are not billed spend. SDK assistant-only totals do not substitute for complete
coverage.

Automatic steering is **off**. The SDK-host API exposes live state/abort and
opt-in fixed `reconcile` / `avoid_repeat` corrective templates. It rejects arbitrary
messages, reviewer steering, stale generation/attempt/contract identity and changed
canonical task records (including uncommitted changes). Reads run off the SDK event
loop. A durable pre-send fingerprint, three-intervention ceiling and 60-second
cooldown prevent duplicate replay; ACK means accepted/queued, never consumed.
`PI_AUTOWORK_STEERING=1` permits these checks; it does not install an automatic
LLM supervisor or expose a remote control endpoint. A production cross-process
control channel and automatic intervention policy are not activated by this slice.

Auxiliary triage/provisioning now distinguish completed results from technical
failures. Safe pre-acceptance/confirmed-provider failures and unavailable scratch
use the existing per-profile marker files with a three-attempt recovery budget and
backoff. Ambiguous transport/cleanup/abort outcomes are replay-blocked. A failed
triage is not an owner verdict; successful owner decisions remain deduplicated.
An unapplied engine answer and a missing provisioning scratch are not successful
completion markers. These records do not authorize or close engineering tasks.

## Verification and rollback

```sh
# Safe focused tests. SDK-dependent classes require the interpreter above.
"$PI_AUTOWORK_RPC_PYTHON" scripts/check.py \
  pi-autowork/tests/test_pi_rpc.py pi-autowork/tests/test_pi_process.py \
  pi-autowork/tests/test_pi_events.py pi-autowork/tests/test_pi_rpc_install.py \
  pi-autowork/tests/test_recovery_runtime_failures.py tests/test_pi_rpc_engine.py

# Native Pi, deterministic offline provider, no real-model/auth qualification.
# Invoke directly: scripts/check.py intentionally removes AUTOWORK_* variables.
PI_EXECUTABLE="$(command -v pi)"
AUTOWORK_TEST_PI="$PI_EXECUTABLE" "$PI_AUTOWORK_RPC_PYTHON" \
  pi-autowork/tests/test_installed_pi_rpc.py -v
```

The existing engine/Git fixture checks worker implementation, independent review,
verified closure and same-attempt provider fallback through the real SDK against a
fake Pi peer. The native fixture separately checks installed Pi settlement,
streaming, session resume, reviewer separation and JSON/RPC cold-start timing.
Neither fixture proves a real model's engineering judgment or fleet delivery.
See [qualification evidence](research/pi-rpc-qualification-2026-10-24.md) for the
bounded real-model smokes and current limitations.

For rollback, first settle/stop the owned attempt and verify cleanup through the
existing engine controls. Then select `PI_AUTOWORK_TRANSPORT=json` for the **next**
invocation using the existing configuration/install path. Never switch a still-live
or uncertain attempt to JSON or run two transports against its session. Preserve
accepted contracts, partial commits, histories, pending checks, review and
publication permissions. An active service update/restart remains a separate,
serialized operation with fresh ownership and migration checks.
