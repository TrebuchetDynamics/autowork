# Pi RPC qualification — 2026-10-24

This records TOOLSET-387-132efe18's **bounded implementation slice** and
TOOLSET-388-b422fa9e's [canonical recheck](#canonical-recheck-after-the-import-cycle-repair),
not an installed-fleet acceptance receipt. Architecture, setup and rollback are in
[the runtime guide](../pi-rpc.md). The earlier [harness audit](pi-harness-audit-2026-10-24.md)
remains historical evidence; its JSON-baseline recommendation was superseded by
the owner's explicit request to implement RPC by default.

## Implemented

- Default `AsyncPiClient` transport, immutable expanded input, SDK/Pi pins, isolated
  installation, explicit JSON rollback, existing model/cooldown/retry policy.
- Linux guard with explicit parent birth identity, pidfd-based ownership,
  descendant cleanup and receipts; ancestry-safe command watchdog.
- Bounded live progress, independent reviewer sessions, settlement-aware outcomes,
  typed terminal uncertainty, partial-usage provenance and fixed opt-in controls.
- Durable auxiliary recovery reservations before dispatch; failed triage is not an
  owner verdict, missing scratch is not completed provisioning, and ambiguous
  accepted work is replay-blocked. Per-scratch cleanup disposition also covers
  background maintainer finish/stop, without borrowing a foreground result.
- Existing engine/Git integration remains authoritative. No upstream Hermes edits,
  custom Pi protocol, second scheduler, task database, publication grant or service
  restart.

## Offline evidence

Qualified environment: Linux, Python 3.12.14, Node 24.19.0, Pi 1.4.0 and SDK 0.2.6.
Qualification used disposable isolated environments and actual offline hash-pinned
wheel installation. The final-path venv's `bin/pip --version` also passed (a relocated
venv would leave broken shebangs). The same pinned wheel was then installed into
the default private versioned runtime environment. This installed the dependency,
not a new runner release: no global Python/Pi edits or service restart occurred.

A final focused `scripts/check.py` invocation covered **13 modules / 197 tests**,
all passing, with the SDK available (no SDK-class skips):

| Module | Tests |
|---|---:|
| `pi-autowork/tests/test_pi_process.py` | 15 |
| `pi-autowork/tests/test_pi_events.py` | 16 |
| `pi-autowork/tests/test_pi_rpc.py` | 17 |
| `pi-autowork/tests/test_pi_rpc_install.py` | 4 |
| `pi-autowork/tests/test_recovery_runtime_failures.py` | 12 |
| `pi-autowork/tests/test_pi_runtime.py` | 6 |
| `pi-autowork/tests/test_blocker_triage.py` | 1 |
| `pi-autowork/tests/test_maintainer.py` | 20 |
| `pi-autowork/tests/test_fleet_view.py` | 47 |
| `pi-autowork/tests/test_main_check.py` | 28 |
| `tests/test_cli_startup.py` | 1 |
| `tests/test_install_menu.py` | 28 |
| `tests/test_pi_rpc_engine.py` | 2 |

The engine tests use a real Git engine and real SDK with a **fake Pi peer**. They
prove worker/report/reviewer wiring, verified fixture closure and provider fallback
without changing the engine attempt. They are not real-model engineering evidence.

The separate legacy JSON engine/service module ran **138 tests**, including two
pre-existing expected failures (reused Yarn tool mutation isolation and saved versus
consumed blocker answers). Its first pass had one ordinary failure: the old test
expected incomplete provisioning to announce that it needed a person. The test was
updated to require a technical hold, no invented owner need, continued independent
work, and no completion of blocked/dependent tasks. That single integration test
then passed. The entire 138-test module was not rerun after the assertion update;
no whole-module clean-pass claim is substituted for that evidence.

Affected selection conservatively selected the whole inventory because the new
requirements file/docs have no narrower mapping. Per repository instructions,
named affected modules were run instead. **No full-repository or full affected-suite
pass is claimed.** Registration/native fixture success does not establish delivery.

Independent review reproduced and drove regressions for parent-adoption identity,
PID-reuse ancestry, aborted-provider fallback, pre-dispatch recovery reservations,
late control after settlement, background scratch cleanup and STOP masking cleanup
uncertainty. The final narrow review approved the bounded implementation with no
remaining P0/P1 findings and independently reran 35 tests. It did not revalidate
live smokes, documentation, fleet activation or all repository tests.

## Installed Pi, offline provider

Direct opt-in `test_installed_pi_rpc.py` passed **3 tests** with the real SDK and
installed Pi: live events before settlement, session resume with independent
review history/tool restrictions, and deterministic JSON/RPC comparison. HOME,
resources and provider are isolated; this uses no real credentials or model calls.

Measured external monotonic elapsed time (seconds), three identical cold fixture
invocations per transport:

| Transport | Samples | Median |
|---|---|---:|
| JSON | 0.488, 0.458, 0.487 | 0.487 |
| RPC | 1.577, 1.657, 1.552 | 1.577 |

RPC was about **1.09 seconds slower** at cold startup here. A repeat using the
finally installed private SDK environment measured JSON 0.413/0.375/0.392 seconds
and RPC 1.190/1.278/1.133 seconds: medians 0.392 versus 1.190, or 0.80 seconds
additional RPC startup. All four typed task checks passed with that installed
environment, including the direct native tests. The guard, SDK-host and version
checks add overhead. These three-sample results do not establish production
latency distributions or token/throughput improvements. RPC currently adds usable
lifecycle control and observation—not demonstrated startup speed savings.

## Bounded real-model smokes

Two independent disposable repositories used the current `openai-codex/gpt-6.1-sol`
configuration, with no deliberate credential or global-configuration edits. Ambient extensions, skills,
context files, templates, themes and MCP were disabled. No network tools,
publication, service updates or unrelated repository changes were requested.
Each worker used the real `worker.worker` entrypoint, made a scoped local commit
and wrote its report. A fresh `verify` job independently inspected the accepted
contract/diff and ran the check. The harness checked actual file bytes, commit,
clean tree, unchanged contract and reviewer verdict; model claims alone did not
establish success.

| Scenario | Worker elapsed | Review elapsed | Observed result |
|---|---:|---:|---|
| Exact readiness marker | 28.22 s | 13.62 s | Scoped commit/report and independent review pass |
| Intentional blocked `sleep` tool | 34.71 s | 11.68 s | One watchdog interruption; same worker invocation continued, committed and passed independent review |

Both cases reported cleanup complete. The recovery run had exactly one worker
run and one review run, with one worker command interruption and zero reviewer
interruptions; it was not a fallback or re-dispatched engine attempt.

Assistant token subtotals below were extracted afterwards from the saved private
session usage surfaces; they are **not complete invocation totals**. Input excludes
cache-read tokens; total includes the provider's reported cache contribution.

| Scenario / role | Input | Output | Cache read | Reported assistant total |
|---|---:|---:|---:|---:|
| Marker worker | 5,884 | 873 | 10,496 | 17,253 |
| Marker reviewer | 3,335 | 122 | 1,152 | 4,609 |
| Recovery worker | 5,425 | 884 | 13,312 | 19,621 |
| Recovery reviewer | 2,018 | 146 | 2,560 | 4,724 |

Complete token totals and billed spend remained **unknown**: optional tool usage
was absent, and ordinary Pi catalog cost fields are not billing provenance. The
new `known_usage` field retains partial reported subtotals without pretending that
they are complete. No dollar savings or comparable real-model JSON/RPC A/B result
was measured.

These smokes preceded the last offline failure-window corrections. They establish
bounded real-model worker/review and command-interruption behavior, **not** live
engine closure, coordinator-crash recovery, hostile-process containment, complex
coding quality, automatic steering or installed-fleet acceptance. Raw session
histories, credentials, private state and disposable repositories stay out of Git.

## Canonical recheck after the import-cycle repair

TOOLSET-388-b422fa9e was reopened after the import-isolation gate failed at
`7e29570686f3482e654a6ad8a8730437f4856454`. Its earlier documentation-only landing
was reverted. These results instead bind to the new source baseline
`60eb9b36977505baf797226ffec2e9640fe3ade2`; the current follow-up changes documentation
only and does not alter tested runtime or test bytes.

Historical source inspection reproduces both `pi_rpc` ↔ `pi_runtime` and
`planning_ui` ↔ `tui` import cycles, including deferred imports. Repair
`aeca6caf1f2e730ef5d445b37fc69b4fc5d4c9cf` is already an ancestor of the new baseline:
it extracted shared run helpers into `Src/pi_autowork/pi_run_support.py` and
confirmation UI into `tui_dialogs.py`. RPC now depends on the helper leaf rather
than importing `pi_runtime` back; caller-owned cancellation is an explicit live
`stop_requested` callback. The unchanged cycle guard passes on all 55 runner
modules. No duplicate fix or weakened test is needed.

The baseline also retains canonical RPC merge
`37f830ce245d8fdea65022690af12c7249777c13`, TOOLSET-375 relocation and TOOLSET-369
main-check extraction. RPC, guard, projection and job-runtime bodies have one
owner each in `Src/pi_autowork`; old public paths are compatibility adapters.
Guard/SDK-host children use the selected release's `LAYOUT.entrypoint` paths.
Main-check supervision remains behind the Coordinator facades in
`Src/pi_autowork/supervision/main_checks.py`. Public imports, bootstrap loads and
source inventory confirm one selected-release owner, including the helper leaf.

Fresh checks used Linux, Python 3.12.14, SDK 0.2.6 and Pi 1.4.0:

| Check | Result on the new baseline |
|---|---|
| Named import-isolation/acyclicity guard in `tests/test_task_prepare.py` | 1 test: OK, no optional-renderer skip |
| Focused RPC/process/events/runtime/recovery/install, release, supervision, maintainer, public-entrypoint, CLI and installer checks | 14 modules / 180 tests: OK, no SDK skips |
| Direct `test_installed_pi_rpc.py -v` | 3 tests: OK |
| Direct `test_installed_pi_contract.py -v` | 2 tests: OK |

The focused group used the existing SDK interpreter through `autowork-run` and
`scripts/check.py`. Native tests explicitly selected installed Pi, isolated HOME
and ambient resources, and used the deterministic offline provider. No credentials,
real-model calls, installation, service restart or activation were performed.
The three optional Hermes integration modules were excluded, not RPC SDK cases.

A broader 16-module run also exercised `tests/test_pi_rpc_engine.py` and all of
`tests/test_task_prepare.py`. Three cases failed before any file was edited and
failed again individually on that pristine baseline:

- `test_pi_rpc_engine.RpcEngineTests.test_default_rpc_worker_independent_reviewer_and_verified_engine_close`
- `test_pi_rpc_engine.RpcEngineTests.test_rpc_provider_fallback_preserves_existing_engine_attempt`
- `test_task_prepare.ForceTests.test_force_stops_the_service_and_a_live_worker_and_converts_keeping_the_work`

The two engine fixtures timed out after worker startup (120 seconds each); the
force fixture reported that its worker survived SIGKILL. These are retained as
baseline failures, not passing engine-closure or conversion evidence. The named
import guard passed both alone and in the broader run. The worker report records
exact commands, logs and classifications; no full-repository pass is claimed.

The supported delivery remains a scoped local commit/report followed by the
coordinator's serialized integration, independent review and merged-tree gate.
This follow-up does not merge, alter another checkout, bypass ownership guards,
repin failed evidence, close tasks, publish or restart services. A source commit
is not an installed release.

## Remaining delivery gates

1. Integrate this evidence follow-up through the supported coordinator path, with
   independent review and merged-tree checks, including the named import guard.
   Canonical relocation and the cycle repair are already present in the tested
   baseline; the baseline fixture failures above are not silently qualified.
2. Qualify a single explicitly owned installed runner, including interrupted-attempt
   recovery and real engine closure. Preserve paused jobs; do not restart a fleet.
3. Measure matched real engineering tasks and quality/check coverage before claiming
   throughput or token improvements. Keep automatic steering off until a production
   control channel and intervention policy are separately qualified.
4. Retain the guard's documented SIGKILL/kernel/hostile-process limitations. Stronger
   containment needs a delegated-cgroup qualification, not a claim from these tests.

TOOLSET-385 remains the canonical recovery reconciliation follow-up. TOOLSET-386
still covers the legacy JSON accounting path; RPC's new projector does not prove
that old analyzer was repaired.
