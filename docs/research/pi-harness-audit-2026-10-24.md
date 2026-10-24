# Autowork / installed Pi integration audit

2026-10-24 UTC. Scope: canonical Autowork `24df62b93b4164184e0a7346218580b95a69b88d`,
installed **Pi 1.4.0**, and the supplied architecture/SDK reviews. Start here for
verified corrections and the next repair, not a new harness design. This supplements
[the older runtime comparison](pi-autowork-reference-architectures.md#worker-runtime-comparison-toolset-117-cb);
its Pi 1.3.0 measurements and receipts are unchanged.

## Executive finding

**Keep Pi JSON as the production baseline.** Source and offline fault probes support
fixing recovery classification before changing transport. RPC provides control,
not demonstrated reductions in failed attempts, model tokens or time to verified
merge. The installed runtime already resumes JSON sessions by ID and compacts
context; a persistent process is not required for either.

The highest-value production repair is **incomplete auxiliary recovery being
recorded as completed triage/provisioning**. It is currently ownership-blocked:
live TOOLSET-375-8e02693d is relocating the entire runner/engine package. Its
process birth identity and worktree changes were checked, not inferred from an
old ACTIVE note. No migration-owned source was edited. The implemented safe slice
is opt-in native adapter regression coverage, not a claim to have fixed recovery.

## Scope and existing strengths

- `pi_runtime.py:281-322`: GNU `timeout`, same caller process group, private scratch
  stdout/stderr, final analysis and scratch deletion. File redirection avoids a
  blocked stdout pipe; it is not an existing incremental parser.
- `worker.py:124-174`: engine attempt-derived worker session ID; same-session
  approval recovery once, only without a report/commit. The engine retains report,
  worktree and attempt authority. `parallel_dispatch.py:757-785` also captures
  unfinished tool calls before timeout.
- `worker.py:1295-1351`: independent review session, tool selection, checkout/HEAD
  integrity check, explicit verdict and structured runtime failure explanation.
  Full/affected gate reuse and conservative selective review are already present
  (`worker.py:1241-1292`, `review_policy.py`). Do not duplicate expensive gates.
- `coordinator.py:771-796`: auxiliary job subprocess boundary; `2510-2625`:
  foreground/background docs maintainer and validated scratch changes;
  `2663-2755`: provisioning and blocker triage; `2815-2932`: merge resolution,
  clean-ancestry adoption and owned scratch cleanup. `maintainer.py` supplies
  planning policy/prompt helpers, not another execution engine.
- `pi_runtime.py:90-135,355-390`: auth readiness, primary cooldown, bounded retry,
  fallback and same-session partial-work reconciliation already exist.
- `fleet_view.py:222-310`: bounded persistent-session tails plus gate stages already
  expose recent actions. `pi_runtime.py:186-278` has a worker command watchdog,
  including check-queue wait subtraction and daemon exclusions.
- `pi_runtime.py:138-177,329-351`: attempt/role attribution, redaction and honest
  unknown billing. Catalog-derived cost is not a bill; preserve that distinction.

Paths above are under `pi-autowork/pi_autowork/` unless explicitly engine paths.
Line references describe the audited revision, not the forthcoming Src relocation.

## Claims confirmed, corrected and unsupported

| Proposal / claim | Finding | Consequence / simpler approach |
|---|---|---|
| Events are parsed only after process exit | **Confirmed** in `run_pi`; native events were observed on disk before exit | Tail the existing JSON output incrementally if live lifecycle diagnostics are needed; no RPC prerequisite |
| There is no useful live progress | **Disproved**: fleet session tails, gate stages and command watchdog exist | Add retry/compaction/tool-start/end freshness rather than a second activity system |
| `agent_settled` is the completion boundary | **Confirmed**, already used by `analyse` | Preserve it; neither settlement nor process exit proves task acceptance |
| Role tool policy is absent | **Partly wrong**: reviewer already selects read/bash/grep/find/ls | Triage/maintainer still inherit broader defaults; reviewer bash and retained MCP are not read-only containment |
| Same-session retry / crash recovery needs RPC | **Disproved as a blanket claim**: same ID resumes JSON history; engine has retained-work/report-only recovery | Preserve current recovery; neither JSON nor RPC guarantees exactly-once tool side effects |
| Question-shaped output controls recovery | **Confirmed**, but guarded and bounded, not an unconditional approval mechanism | Improve existing report/outcome contract; do not replace it with a parallel task status authority |
| Long context is unmanaged | **Wrong as stated**: installed Pi auto-compacts in all modes | Measure complete usage and compaction frequency before changing handoffs |
| Raw transcripts are not retained | **Only transport scratch is deleted** | Persistent private Pi session files remain for resume and fleet display; do not claim transcript-free operation |
| RPC / SDK is faster or cheaper | **Unverified** | Same model context can cost the same in either transport; steering adds input and may add turns |
| Codemode is unavailable without an extension project | **Wrong**: built-in extension/tool in Pi 1.4.0 | Pilot selectively; filtered results can omit evidence and nested model work must be accounted for |
| Pi Durable should become recovery authority | **Not justified** | Existing isolated spike already records limits; no second durability/scheduler authority |

`--no-approve` means **decline project-resource trust**, not “disable per-tool
permission prompts.” It does not disable user resources or context files. Plain
`--tools` lists retain MCP unless an `mcp__` entry filters it; use explicit MCP
exclusion/`--no-mcp` as appropriate. Neither flag is an OS sandbox.

## Actual installed Pi capabilities

Evidence: `pi --version` and `pi --help`, the managed launcher's selected 1.4.0
package, its shipped docs and compiled implementation. The launcher follows its
managed current-version file; Autowork does not pin this executable version in
`runs.jsonl`. This audit does not claim every already-running fleet process uses
1.4.0 or the current checkout.

Within `@earendil-works/pi-coding-agent` version 1.4.0:

| Capability | Status / matching implementation |
|---|---|
| JSONL mode, LF-only framing, incremental events | Supported; `docs/json.md`, `dist/modes/print-mode.js:84-108`, `dist/modes/json-event.js` |
| RPC prompt/state/steer/follow-up/abort/clear-queue | Supported; `docs/rpc.md`, `docs/rpc-commands.md`, `dist/modes/rpc/rpc-mode.js:298-361` |
| Prompt ACK versus settlement | Distinct; `handled` need not start a run; `agent_end` can precede automatic continuation |
| Session ID, explicit directory, resume/fork/no-session | Supported; `docs/sessions.md`, `docs/session-format.md`, `dist/main.js:344-351` |
| Automatic/manual compaction and retries | Supported in JSON and RPC; `docs/compaction.md`, `dist/core/agent-session.js:2323,2609` |
| Tool/resource restrictions | Supported, with MCP/trust caveats; `docs/cli.md`, `docs/security.md` |
| TypeScript SDK and RpcClient | Supported; `docs/sdk.md`, checked `examples/sdk/01-minimal.ts` and `examples/rpc-client.ts` |
| Codemode | Supported built-in extension, selectively enabled; `docs/codemode.md`; not an OS sandbox |
| Built-in arbitrary-process attachment or exactly-once recovery | Not established by these APIs; session reopen is not process attachment |
| Pi Durable as Autowork backend | Experimental existing spike only, not production adopted |

Native, isolated offline probes on the actual executable passed:

1. JSON emitted tool events while the process remained blocked before settlement;
   two `agent_end` events preceded one `agent_settled`.
2. Same session ID appended to the same history file; raw transport files were deleted.
3. Explicit allowlist plus denylist exposed only the fixture's allowed tool.
4. RPC prompt ACK preceded completion; steering queued while a tool was blocked.
   `clear_queue` followed by `abort` settled the run; a second prompt used the same
   process and a fresh process reopened its saved session.

These use the existing deterministic provider, an isolated HOME/config and an
allowlisted environment, not real credentials or provider calls. They do **not**
qualify real model behavior, nested-process cancellation, power-loss replay,
compaction under real context pressure, or savings.

## Ranked repairs

Ranking is engineering judgment from reproduced control flow, not fleet throughput
measurement. All production changes require fresh ownership checks after relocation.

| Rank | Verified weakness / evidence | Bounded repair and acceptance | Risk / effort |
|---|---|---|---|
| 1, high | `coordinator.py:2733-2743` discards job success/why, writes triage reason hash and calls missing verdict owner-needed; `2674-2681` spends provisioning marker before scratch exists | Preserve incomplete technical outcomes; bounded durable retry/backoff, genuine owner verdict still held, successful work deduplicated | Medium / M; avoid unbounded retry and duplicate provisioning |
| 2, medium | Live retry/compaction state absent from current activity projection; final analysis retains the whole stream in memory (`pi_runtime.py:138-177,307-310`) | Bounded incremental reads from existing scratch file; phase/time/counters only, attempt/session identity, terminal drain and malformed/partial-record tests; no new authority | Medium / M; avoid stale progress, log leakage, callback blockage or “quiet means stuck” kills |
| 3, medium | Reviewer still has bash; plain tool allowlist retains MCP; triage uses ordinary defaults | Explicit role loadout and executable/version metadata; read-only diagnosis excludes mutation-capable tools/resources, verification uses controlled execution | Medium / M; avoid breaking checks or confusing filtering with sandboxing |
| 4, medium | `analyse` counts only assistant usage, omitting tool/compaction usage | Account known independent usage once; disclose incomplete coverage and preserve billing provenance | Low–medium / S–M; prerequisite for credible token comparison |
| 5, medium | Broad provider/error/crash categories; final status does not fully describe truncated or late-failing execution | Preserve structured outcomes and concise terminal diagnostics using existing report/record seams | Medium / S–M; never infer authorization or successful acceptance from runtime completion |
| 6, experimental | Need for mid-run control is plausible, savings unmeasured | Isolated RPC/client fault-injection pilot only after parity gates; compare with JSON resume | High / M–L; no default switch |

Fault probes reproduced rank 1 without a model: two unchanged triage cycles with
`pi_job -> (False, '')` made **one call**, persisted `triage.json`, and printed
“needs the owner.” Two provisioning cycles with unavailable scratch attempted
scratch creation **once** and retained the reviewer-version marker. These show
lost retry eligibility, not a measured count of production stalls.

Accounting fixture: 7 assistant tokens + 5 tool-result tokens + 11 compaction
summary tokens yielded **7**, not **23**. Installed Pi's own
`dist/core/agent-session.js:3445-3484` includes those categories in session totals.
Cumulative session totals cannot simply be added per retry. Usage entries and
other surfaces also need a completeness inventory; unknown spend stays unknown.

Lower-priority source findings: provisioning uses substring completion matching
(`coordinator.py:2690`), unlike terminal verdict parsing elsewhere; asynchronous
maintainer/resolver launch failures can leave allocated output files before normal
cleanup registration (`2536-2545`, `2823-2833`). No live incident was attributed.

## Alternatives and the community Python SDK

Public sources were searched and inspected; Context7/codebase-memory tools were
unavailable. Alternatives were **not installed or benchmarked**. API availability
is not a quality ranking.

| Interface | Verified capability | Autowork trade-off |
|---|---|---|
| Pi JSON | Native events, durable session history, same-ID resume | Smallest production boundary; live control requires another invocation |
| Pi RPC | Same events/context engine, bidirectional commands | Potential startup reuse/control; requires framing, backpressure, command/run correlation and process recovery |
| Pi TS SDK | In-process AgentSession, explicit resources/tools/models | Rich native surface but Python needs a Node-side boundary; no demonstrated throughput gain |
| Community Python RPC SDK | Sync/async clients, streaming, session options, steering and version checks | Avoids hand-writing much protocol handling; Alpha dependency, lifecycle differences still need qualification |
| Codex Python SDK | Official sync/async API, typed notifications, thread/turn handles, steer/interrupt, sandbox presets | Credible A/B candidate; different runtime/provider ecosystem and platform sandbox qualification |
| Claude Agent SDK Python | Async streaming, bidirectional client, Python PreToolUse hooks, permission policies, bundled CLI | Claude-centered runtime; hooks can enforce policy but do not prove complete isolation |
| OpenCode | Headless HTTP/OpenAPI, session/status/abort/prompt_async, SSE and optional HTTP basic auth | Useful network control boundary; service lifecycle, authentication and reconnect reconciliation add work locally |

Primary sources: [Codex Python README](https://github.com/openai/codex/blob/main/sdk/python/README.md),
[Codex API](https://raw.githubusercontent.com/openai/codex/main/sdk/python/docs/api-reference.md),
[Claude Python README](https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/README.md),
[OpenCode server](https://opencode.ai/docs/server/),
[Pi RPC](https://pi.dev/docs/latest/rpc). Pi conclusions above use the installed
version, not latest online documentation. Claude `allowed_tools` auto-approves
named tools; it is not a tool-removal allowlist. Compare actual permission semantics.

### Python SDK correction and pilot gates

The supplied **0.2.3** version is stale: inspected [PyPI](https://pypi.org/project/pi-agent-python-sdk/)
served **0.2.6**, uploaded October 23; search excerpts still said 0.2.5.
[Metadata](https://raw.githubusercontent.com/cheenulabs/pi-agent-python-sdk/v0.2.6/pyproject.toml)
labels it Alpha, Python >=3.11, with no Python runtime dependencies. Pi/Node remain
external requirements. Its [compatibility record](https://raw.githubusercontent.com/cheenulabs/pi-agent-python-sdk/v0.2.6/docs/compatibility.md)
records Pi 1.4.0 as tested; other accepted versions are not thereby qualified here.

Pinned [transport source](https://raw.githubusercontent.com/cheenulabs/pi-agent-python-sdk/v0.2.6/src/pi_agent/_transport.py)
confirms `asyncio.create_subprocess_exec` without a new process group, followed by
stdin close and direct child terminate/kill/reap. It bounds draining inherited
pipes; that is **not** descendant termination. Pi itself has cleanup, so this is
a missing composition guarantee, not proof every SDK cancellation orphans tools.
Autowork's current watchdog assumes `timeout -> Pi -> command`; substituting the
SDK would also change that ancestry. Test both ordinary and escaped descendants.

Pinned [run source](https://raw.githubusercontent.com/cheenulabs/pi-agent-python-sdk/v0.2.6/src/pi_agent/_runs.py)
waits for ACK/start/settlement and cleans owned runs with clear-queue/abort;
low-level settlement-helper timeouts only cancel observation. Choose one ownership
style per client. Raw `request()` is needed for disposition because the Python
prompt/steer wrappers return None. Callbacks run synchronously on its event loop;
slow callbacks and bounded subscriber overflow remain integration concerns.
[Usage accumulation](https://raw.githubusercontent.com/cheenulabs/pi-agent-python-sdk/v0.2.6/src/pi_agent/_usage.py)
is assistant-only and sums Pi catalog costs: adopting `RunResult.usage` unchanged
would neither solve our omitted usage nor preserve billed-cost provenance.

An approved opt-in experiment is reasonable, **not yet implemented or qualified**.
Pin SDK and Pi; retain engine attempt fencing, timeout/process ownership and fresh
review sessions. Require nested/escaped descendant termination, crash/no-double-
dispatch, partial-result accounting, ACK-before/after-events, retries/compaction
before settlement, bounded queues, and scope-preserving steering. Do not enable
new operator resources or credentials. Compare repeated identical tasks/model/
verification on the same snapshot: verified delivery, failed attempts, complete
input/output/cache/summary/tool tokens, idle time and owner intervention. Subscription
usage is not billed spend. Only then decide whether RPC beats streaming JSON.

## Delivered slice and verification

Task **TOOLSET-384-f3e1e7f5** adds
[`test_installed_pi_contract.py`](../../pi-autowork/tests/test_installed_pi_contract.py),
reusing the existing offline provider rather than another harness/transport.
Explicit opt-in tests exercise the real production `run_pi` and installed Pi:
settlement/partial output, raw cleanup, same-ID context, distinct review-session
history and tool allowlist/denylist. IDs are supplied by the test: this does not
qualify production ID generation, reviewer prompt construction or semantic recall.
Tool checks inspect loaded capabilities, not an attempted unsafe call or OS isolation.
Ordinary offline discovery invokes no Pi.

```sh
AUTOWORK_TEST_PI=/absolute/path/to/pi \
  python3 pi-autowork/tests/test_installed_pi_contract.py -v
```

Run directly: `scripts/check.py` intentionally strips `AUTOWORK_*`; passing that
variable to the checker still skips these native tests. This was observed and the
instructions corrected. Two direct native tests passed on Pi 1.4.0. Two injected
mutations (premature `agent_end` settlement and worker/reviewer session reuse)
each produced the expected assertion failure without modifying runtime source.
Baseline focused runtime/triage checks passed **7 tests**. Standard offline native-
test discovery correctly reported **2 skips**, not native qualification. Affected-test
selection against the audited base conservatively selected all 138 modules because
this new human audit document has no resolved test mapping. Per repository focused-
change instructions that full fallback was not run; named checks and working-tree
task validation are the scope, not a claimed full/affected-suite pass.

Follow-up tasks created, not marked implemented:
- **TOOLSET-385-6021ba81**: rank-1 technical recovery, dependent on live relocation
  **TOOLSET-375-8e02693d**; recheck coordinator ownership against subsequent
  **TOOLSET-369-b5db2d3a** extraction before writing.
- **TOOLSET-386-4288b2e0**: omitted usage, also dependent on relocation.

No production parser, recovery, policy, installed package or service changed.
The production-repair blocker is current overlapping ownership, not an owner
approval question. Native tests are a verification improvement only; fewer stalls,
more verified merges, model-token savings, SDK cancellation and real crash recovery
remain unmeasured. Revisit this report when relocation, Pi version, SDK pin or the
recovery/accounting repairs change.
