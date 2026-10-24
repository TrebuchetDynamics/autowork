# Pi RPC qualification — 2026-10-24

This is evidence for TOOLSET-387-132efe18's **bounded implementation slice**, not
an installed-fleet acceptance receipt. Architecture, setup and rollback are in
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

## Remaining delivery gates

1. Reconcile canonical source ownership with TOOLSET-375 relocation and TOOLSET-369
   extraction, preserving their candidates and serializing canonical writes.
2. Review/rebase and integrate through the supported path. Local source default
   and local commits do not update an installed release or authorize publication.
3. Qualify a single explicitly owned installed runner, including interrupted-attempt
   recovery and real engine closure. Preserve paused jobs; do not restart a fleet.
4. Measure matched real engineering tasks and quality/check coverage before claiming
   throughput or token improvements. Keep automatic steering off until a production
   control channel and intervention policy are separately qualified.
5. Retain the guard's documented SIGKILL/kernel/hostile-process limitations. Stronger
   containment needs a delegated-cgroup qualification, not a claim from these tests.

TOOLSET-385 remains the canonical recovery reconciliation follow-up. TOOLSET-386
still covers the legacy JSON accounting path; RPC's new projector does not prove
that old analyzer was repaired.
