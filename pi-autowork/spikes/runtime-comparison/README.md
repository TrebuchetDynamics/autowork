# Worker-runtime comparison spike (TOOLSET-117-cb)

**Experimental, isolated evaluation code, not a supported runner backend.** Nothing
imports this directory from the coordinator. The current `pi_runtime.py` CLI path
remains the default; adoption is a separate owner decision. No dependencies are
installed into Pi profiles, services or the fleet.

## Boundary and ownership

`boundary.Runtime(backend, state_directory, config)` exposes:

- `launch(cwd, fixture)` registers an attempt token before spawning and returns a
  JSON-serializable handle: backend, token, CWD, attempt directory, process birth
  identity. CWD is an already provisioned **Toolset-owned worktree**. One writer
  owns each runtime state directory; concurrent coordinator mutations are not supported.
- `observe(handle)` returns a normalized event with `status` and `token`:
  `running`, `completed`, `failed`, `interrupted`, or `stale`. Terminal receipts
  must match the active token; all marked descendants must have exited first.
- `stop(handle)` uses the existing engine's process-identity and marker discovery
  with birth-checked group/marked-descendant TERM-to-KILL escalation. Birth is
  rechecked at each signal; stale numeric group IDs alone never justify a signal.
  It never removes a worktree.
- `resume(handle)` adopts live work without relaunching. A dead CLI worker returns
  an interruption notice and does **not** rerun unknown tools or checks. Durable
  recovery reopens the same storage with the original idempotent `requestId`.
  New assignments get fresh IDs, distinct from crash resubmissions.

A result is **execution evidence, never acceptance**. Worktree provisioning,
identity fencing, combined-tree verification, integration and cleanup permission
remain Toolset responsibilities. This is not a second scheduler or task store.

The capability record separates live-process reuse, transcript persistence,
coordinator reload survival, crash adoption and per-tool replay safety. Pi extension
`/reload` survival is separately recorded as unqualified. This
one-shot adapter does not retain idle reusable workers (even though Harness can
serve multiple submissions). `fixture_safe` is replay-safe; `fixture_unsafe` and
unknown operations/checks default to unsafe. Only pi-durable enforces per-tool
recovery: interrupted safe calls may rerun; unsafe calls become model-visible
`interrupted` results. Safe is a promise of idempotency, **not exactly-once external
effects**. Execution counters in the probe deliberately count attempts.

## What actually runs

- CLI: unmodified `pi_autowork.pi_runtime.run_pi`, bypassing model/auth selection
  only to supply the deterministic offline provider. Existing timeout, JSON
  analysis, session persistence and raw-stream deletion run normally.
- AgwaB: pinned `runSubagent({backend: "headless", workspace: "shared",
  worktree: false, cwd, ...})`. Toolset does not invoke upstream worktree creation
  or success finalization. AgwaB requires `runsDir` **inside** CWD, so the spike
  uses ignored `.runtime-agwab/`; its session transcript is stored externally.
- pi-durable: `Harness.open`, JSONL storage with `fsync: true`, committed context
  readback, `resume`, and duplicate `requestId` submissions. A supervisor-held
  `flock` supplies the cross-process exclusion that upstream explicitly does not
  supply. There is only one process per storage. It is **experimental**.

`fixture.mjs` supplies the same deterministic model and tool operations to each
backend. `provider.mjs` is a test-only extension, loaded explicitly with ambient
extensions disabled and an isolated agent home. There are no real model calls,
credentials or provider-network requests. `bridge.mjs` loads explicit cached
upstreams, not packages installed in a service. Built-in Pi tools, MCP, resource
pressure, real provider retries, throughput and power-loss recovery are unqualified.

Fixtures create disposable Git repositories under `$TMPDIR`, with owned
`.worktrees/` directories. They measure cancellation, coordinator-process restart,
stale receipts, out-of-order completion, exact combined-tree rejection, dirty and
unmerged retention, an escaped TERM-ignoring descendant, crash replay, and Pi event
settlement. Shared fences, verification and stop results qualify the **composition**,
not those features in upstream alone. Cancellation uses Toolset stop, not upstream
interrupt/abort APIs. Crash replay kills the supervisor process group; AgwaB's
separate child group survives, which is recorded as an incompatibility, not silently
killed as part of the fault. Final fixture cleanup then stops those descendants.

## Reproduce

Linux `/proc`, Git, Python 3 and Node >=22.19 are required (measured on Node 26.7.0).
Use a disposable local cache; do not install into a profile or fleet. The commands
below fetch executable third-party code only for the explicitly authorized spike.
No upstream source patch or compatibility shim is applied.

```sh
CACHE="$AUTOWORK_CACHE/toolset-117-node-1.3.0"
SRC="$AUTOWORK_CACHE/toolset-117-sources/agwab-ab91a74"
# Reuse these directories if already provisioned at the exact versions.
npm install --prefix "$CACHE" --cache "$AUTOWORK_CACHE/npm" --ignore-scripts \
  --no-audit --no-fund --save-exact @earendil-works/pi-coding-agent@1.3.0 \
  @earendil-works/pi-durable@1.3.0 jiti@2.7.0 proper-lockfile@4.1.2 \
  @anthropic-ai/sandbox-runtime@0.0.75
git clone https://github.com/AgwaB/pi-subagent.git "$SRC"
git -C "$SRC" checkout ab91a74fcbd079caa27f9e48932004d1fd9c1e9f
ln -s "$CACHE/node_modules" "$SRC/node_modules"
timeout 180 python3 pi-autowork/spikes/runtime-comparison/compare.py \
  --pi "$CACHE/node_modules/.bin/pi" --modules "$CACHE/node_modules" \
  --agwab "$SRC" --output "$TMPDIR/comparison.json"
```

`--fixture NAME` or `--backend cli|agwab|durable` narrows investigation. Scratch
logs and worktrees are retained under `$TMPDIR` for diagnosis, not committed.
Only the compact, source-hashed measurement record is kept in `results.json`.
`pass` means that fixture's assertions passed; `compatibility_failure` is an
observed failure, **not a passing runtime qualification**. Such results satisfy the
comparison's recording contract, so exit 0 means the probe finished recording;
unexpected assertion failures exit 1. Missing prerequisites do not qualify any
fixture. The dependency manifests/locks remain in the local cache, not this repo;
transitive dependency versions are not promised by these top-level pins.

Read back the retained record against its exact measured source and inventory:

```sh
python3 pi-autowork/spikes/runtime-comparison/compare.py \
  --readback pi-autowork/spikes/runtime-comparison/results.json
python3 scripts/check.py pi-autowork/tests/test_runtime_boundary.py pi-autowork/tests/test_pi_runtime.py
```

The [research comparison](../../../docs/research/pi-autowork-reference-architectures.md#worker-runtime-comparison-toolset-117-cb)
contains measurements, compatibility limits and the recommendation.
