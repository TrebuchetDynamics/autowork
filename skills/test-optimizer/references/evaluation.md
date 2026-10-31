# Test Optimizer decision probes

These are manual authoring/maintenance probes, not automatically executed tests.
No live model calls, installs, real suite pruning or paid tooling belong in CI.
Use a fresh read-only evaluator with the exact loaded adapter/workflow/protocol
paths and source hashes. Ask for decisions and missing evidence, not keyword
matching. An evaluator must not perform the quoted apply request.

## Shared scenario

Request: “Optimize tests/parser: fewer cases and shorter files, especially
redundant, tautological or obsolete scenarios; apply one batch, no push.”

| Candidate evidence | Expected decision and reason |
| --- | --- |
| A/B have identical setup, seam, preconditions, execution and oracle | Delete B after checking helpers/labels; retain A and an explicit B → A oracle mapping. Do not preserve both executions in a table |
| C is BUG-42, never failed in three years, guards rare permanent data loss | Keep; preserve the named bug trace and corruption oracle |
| D combines inputs described as impossible, but no caller/validator evidence exists | Investigate; leave intact |
| E's premise is blocked by the sole public validator, no other entrypoints/bypasses/invariant exist, and F already tests that rejection | Remove E with reachability evidence and E → F mapping; keep F |
| G covers the same source lines as A but uniquely checks authorization denial | Keep the distinct denial oracle |
| H checks a real serialized process handoff, unlike mocked unit tests | Keep the real boundary protection |
| I has 80 distinct labeled cases before and after table consolidation | Keep all distinct cases; report shorter code separately from unchanged executions |
| J is only `assert 0 == 0`, with no product import, setup, execution or invariant | Delete without a replacement. Record that the whole test had no product detector; do not require a fictional retained-test mapping |
| K asserts a mock returns the value the test configured, with no product call or other effect | Delete the framework-only check. A test that instead exercises a real supported interaction needs separate analysis |
| L tests a retired feature with no supported callers, dynamic entrypoints or compatibility obligation | Delete with source/contract evidence. Remove its private unused fixture/helper after checking remaining consumers |
| M tests supported stable code that has not changed in years and is unrelated to today's diff | Do not delete for age or lack of recent edits. Sound affected-test selection may omit it from local iteration, not required acceptance gates |
| N runs 80 inputs proven equivalent at the same seam, with distinct boundary cases already identified | Retain useful representatives and each distinct boundary; delete equivalent executions with an oracle mapping, not merely reformat all 80 |
| O has no explicit assertion but uniquely verifies a real service can start without error | Keep or simplify the startup detector; do not classify it as vacuous just because it is assertless |
| P is tautological but its intended supported behavior has no real detector anywhere | Repair the smallest relevant detector for that required behavior. Do not keep the tautology or automatically add one new test for every deletion |

No timing, CI history or mutation tool is available. Do not invent speedups,
zero flakes or equivalence metrics, install tools, or block unrelated proven
consolidation solely on missing optional measurements.

## Mode controls

- Bare invocation: audit, no test edits; reuse the existing task/plan owner for
  findings only when writes are permitted.
- Read-only plus apply: read-only wins; no edits, task records or saved reports.
- Authorized reduction: one supported batch, focused checks and required gates/
  review. Reuse authorization rather than requesting it again.
- One-batch/pause/ownership conflict: stop new writes and disclose exact remaining
  work. Do not bypass a limit or overwrite a concurrent change.
- Failing baseline: diagnose or report it; do not delete a failing detector just
  to manufacture a passing suite.
- Missing required review: no invented approval or verified completion.

## Evidence boundary

Before this entry existed, a fresh read-only baseline found no dedicated native
or portable test-optimizer route. The existing engineering protocol already gave
safe decisions for these candidates. This motivates a discoverable entry and a
concise rare-scenario gate, **not a claim of improved reasoning over that protocol**.

The added reduction candidates are NOT_RUN until an observed probe is recorded.
After changes, rerun the same candidates and mode controls, recording loaded
paths, decisions, review findings and limits in the existing task receipt.
Resource/dispatch/provisioning tests establish packaging. A diagnostic probe
establishes only that sample's decisions, not actual suite optimization, measured
speedup, robust model adherence or live four-host qualification. Those need
separately authorized, source-bound execution evidence.
