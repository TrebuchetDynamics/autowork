# Pi RPC default runtime implementation

## Accepted intent

The owner explicitly requests RPC now and by default, using pi-agent-python-sdk,
not another design-only experiment. Preserve task/attempt/contract authority,
independent review, checks, Git integration, receipts and publication policy.
Automatic steering remains off until qualified; do not restart other runners.
The full mission includes live-model qualification and measurement, which must not
be inferred from deterministic fixture execution.

## Source and ownership baseline

Base: 1ac75c1f (audit on canonical 24df62b9). See
[the source audit](../research/pi-harness-audit-2026-10-24.md).
Pi 1.4.0, Node 24.19.0, Python 3.12.14. SDK 0.2.6 installed only in a disposable
qualification venv; no global installs/configuration. SDK source and cancellation
contract rechecked. Context7 unavailable; pinned upstream docs/source used.
TOOLSET-375 relocation remains live in its own checkout. Implementation proceeds
in isolated feat/pi-rpc-default, never modifying that worker's checkout or merging
across its active work. Reconcile actual Src paths before landing. Existing
TOOLSET-385/386 track recovery classification and complete accounting; preserve
those contracts rather than fabricate their completion.

## Architecture decision

Keep `pi_runtime.job` as the sole model-selection/retry/accounting policy seam.
All worker, reviewer and auxiliary invocations pass through it. `run_pi` defaults
to RPC; `PI_AUTOWORK_TRANSPORT=json` is explicit rollback only, never automatic
replay after uncertain acceptance. Read-only CLI imports remain stdlib-only.

A synchronous engine caller invokes a bounded SDK-host subprocess using the pinned
Python environment. The host runs AsyncPiClient with one process/session for that
attempt invocation. This avoids introducing an event loop into the synchronous
coordinator or depending on its interpreter having the SDK. The OS guard wraps the
SDK host and owns/reaps Pi and tool descendants; it uses Linux process identities,
subreaping and parent-death handling. No SDK private fields or custom JSONL protocol.

`RunSpec` pins session, role, working directory, prompt contents/digest, model,
timeout and allowed arguments/environment. Startup @file prompts are explicitly
expanded before RPC submission, with bounded file sizes. Worker sessions retain
existing engine-derived IDs; reviewers retain separate IDs and exclude MCP.
A per-session file lock prevents simultaneous owners. Compact progress files in
private runtime state are projections, not a new execution journal or scheduler.

`EventProjection` consumes events as they arrive with bounded memory, preserving
settlement, tool lifecycle, retries/compaction, final assistant text and known usage.
No raw text/thinking/tool arguments enter progress. Unknown metadata is not authority.
Slow progress persistence is coalesced outside SDK delivery; critical event overflow
fails closed. The SDK retains its native queue bounds and run ownership rules.

Uncertain acceptance, protocol/overflow failures and missing cleanup evidence are
terminal technical outcomes for this invocation, not automatic job retries.
Confirmed settled provider failures may use existing bounded fallback only after
the process guard proves cleanup. No runtime event closes an engineering task.
Control methods query state, clear/abort and accept only engine-pinned, bounded
technical steering; no arbitrary LLM-generated authorization. Reviewer steering
is forbidden. Intervention records belong to the attempt and require freshness.

## Implementation sequence and verification

- [x] P0 process guard: real nested/escaped subprocess cancellation, parent death,
  PID identity protection, unrelated sentinel, exit/deadline/cleanup receipt.
- [x] Pure event projection: settlement vs agent_end, 7+5+11 usage, missing billing,
  bounded text/state, no raw progress leakage, phase transitions.
- [x] SDK adapter: immutable spec, exact prompt expansion, per-session lock,
  typed failures, cleanup proof, SDK/Pi pins, fake RPC subprocess tests.
- [x] Default runtime seam and install: lazy dependency readiness, hash-pinned
  isolated environment, explicit JSON rollback, existing bounded provider fallback,
  worker/reviewer parity, no changed publication authority.
- [x] Live metadata-only observation and SDK-host bounded controls; automatic steering off.
- [x] Native Pi 1.4.0 fixture worker/reviewer, live state and settlement qualification;
  comparable JSON/RPC deterministic timing, honestly not model/throughput evidence.
- [x] Independent bounded-slice review and proportional checks; local task evidence.
- [x] Disposable real-model worker/reviewer pilot and same-invocation stalled-command recovery.
- [ ] Canonical Src reconciliation/integration (TOOLSET-388-b422fa9e).
- [ ] Installed-runner/interrupted-engine-attempt qualification and matched real-task
  measurements (TOOLSET-389-6dedfd8c); no blanket fleet restart.
- [ ] Production coordinator control channel/policy qualification remains gated on installed-pilot qualification.

Tests precede behavioral changes. Named focused suites are used if affected selection
falls back to the entire suite because of unmapped docs. No production token savings,
model quality or fleet activation claim follows from offline test passes.
