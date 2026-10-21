# Owner-cycle retirement evidence — TOOLSET-202-9a

Source baseline: `f9c49c20cb822442f9f85d767eff67e03081d67b`.
Authority: [accepted graph review, finding 4](2026-10-17-engine-graph-review.md#engine-graph-review-findings).
This is implementation evidence, not a replacement task contract or full-gate receipt.

## Procedure and checklist

- [x] Inspect live imports, dynamic loaders, command paths, skill reference maps,
  adapters, benchmark intermediaries and current hook installation instructions.
- [x] Verify the unchanged baseline with source-bound offline checks.
- [x] Compute the retirement set rather than copying the old candidate list.
- [x] Delete that set, its exclusive tests and the legacy fixture; preserve mixed
  suites' live cases and remove four now-unused native-suite exclusions.
- [x] Run surviving engine and affected installation/workflow tests; check links,
  source closure and historical-prose preservation.
- [x] Measure complete baseline / candidate offline checks under comparable host
  load; retain every sample, including unrelated baseline failures and reruns.
- [ ] Coordinator: integrate and run the authoritative merged-tree gate.

Reproduce the rule (no code imports or checkout changes):

```sh
python3 docs/plans/owner-cycle-reachability.py --verify
```

The script reads baseline files with `git archive`, starts from the stipulated
CLI/package/skill/adapter entry points, and follows Python imports (including
function-local imports), literal Python paths, shell helper paths and current
skill-reference links. Tests are not roots: `scripts/bench_parallel.py` explicitly
imports `test_parallel_e2e`, so its test helpers are reached indirectly. Test
inventory/exclusion strings are not invocations. Python comments, docstrings and
bare dictionary keys are not import/path edges. Historical references are excluded
using the live skill's explicit history map and historical notices, not their age.
Current host-hook installation in `docs/worktree-placement.md`, linked by repository
instructions, is also a root. Consumer-project example links do not turn this
repository's TODO/archive/plans into executable instructions.

This conservative lexical/AST closure is task evidence, not a general Python
reflection analyzer. Independent source tracing corroborates it; the hook consumer
prevents deleting `checkout_lock`. `--verify` checks every retired file is absent
and reintroduces baseline names only in its in-memory graph to detect surviving
edges to missing modules. It also checks exact original historical-body bytes
after undoing only this pass's links, and verifies the linked removal commit
actually deletes every retired module. Verification includes newly tracked live
files, not just paths present in the baseline.

## Removed inventory

All paths below were direct children of `skills/autowork/scripts/`. Lines are
physical source lines (`splitlines()`), including comments and blanks, at baseline.

| Module | Lines |
| --- | ---: |
| budget_controller.py | 215 |
| continuation_capability.py | 106 |
| controller_bridge.py | 185 |
| delivery_state.py | 313 |
| disjoint_fallback.py | 73 |
| native_containment.py | 443 |
| native_lifecycle.py | 755 |
| owner_unblock.py | 237 |
| pass_workspace.py | 498 |
| prepare_prerequisites.py | 115 |
| publication.py | 78 |
| ready_preflight.py | 197 |
| reconcile.py | 264 |
| registration_admission.py | 172 |
| runtime_bundle.py | 113 |
| start_goal.py | 828 |
| writer_registration.py | 313 |
| **17 modules** | **4,905** |

Also removed: 30 engine test files (9,343 lines before moving retained coverage)
and `tests/fixtures/legacy_owner_cycle.py` (525 lines). The pinned-parent refusal
case from `test_prerequisite_recovery` still tests live `agent_commit.sh`, so it is
preserved in `test_finish_task` using that suite's existing disposable Git fixture.
All other cases in those 30 files exercise only retired helpers or the legacy
fixture. Mixed suites retain their live cases: `test_finish_task`,
`test_response_tail`, `test_native_provisioning`, `test_workflow_contract` and
`test_workflow_cycle` lose only obsolete native-body / fixture cases. The existing
engineering installation case now verifies live engine dependencies instead of
deleted admission helpers. No runtime behavior was changed. Static test-method
inventory falls from 1,025 to 609 in the engine directory and from 778 to 774 in
root tests; these counts include excluded native tests, not just executed cases.

The four removed exclusions are `test_native_lifecycle_controls`,
`test_native_handoff`, `test_native_containment_linux` and
`test_controller_bridge_linux`. The offline inventory changes from 148 runnable
modules / 8 exclusions to 122 runnable modules / 4 exclusions. The offline runner's
live-flag scrubbing remains a defense-in-depth boundary.

### Retained, despite the old candidate list

- `check_receipt` is named by current `owner-cycle.md` and `delivery-batches.md`;
  its imports retain `source_freshness` and `candidate_identity`.
- Current `backlog-planning.md` invokes `backlog_plan`, which imports
  `progress_runtime` and reaches `retry_selection`.
- The profile-audit wrapper reaches `audit_profiles`, whose imports independently
  retain `retry_selection` and `cron_output`; current discovery guidance retains
  `discover_sources` and `engineering_signals`.
- Autoresearch retains `finish_task` and its `agent_commit.sh` helper.
- The benchmark reaches `gate_skip` and `offline_fixtures` through its imported
  workload; deleting these would break a live script and surviving tests.
- `checkout_lock` is a currently documented, installable Claude hook, not part of
  the historical native owner-cycle engine. Its eight tests remain.
- `analyze_audit_logs` is explicitly protected by this task's contract. Its only
  located command reference is historical; the script reports this retention
  exception rather than inventing an independent live path.

## Offline verification

The current baseline passed two complete offline timing runs (2,208 tests in
162 process units, one pre-existing skip per run). All three candidate timing
runs passed (1,860 tests in 136 process units, no skips). The baseline and candidate
workspaces each retained identical tracked input bytes throughout all their runs.
Fresh short scratch directories were children of the supplied `TMPDIR`.

Final focused checks and readbacks are recorded in the worker report:

```sh
python3 scripts/check.py --list
python3 docs/plans/owner-cycle-reachability.py --verify
python3 docs/plans/owner-cycle-timing-readback.py --artifacts "$TMPDIR/timings"
python3 skills/docs-sync/scripts/docs.py check "$PWD"
```

Scoped Docs Sync Maintain uses the bundled `skills/docs-sync/SKILL.md` and
`skills/docs-sync/scripts/docs.py`: architecture, testing, dependency instructions
and historical source links are the affected owners. The coordinator-owned TODO,
archive, goals and changelog were not changed. No archive render or repository-wide
docs bootstrap was run. Historical bodies are unchanged except source-link repairs.
The roles checker reports `ok`; its `stale` command separately reports existing
non-ancestor verification pins, which this task does not repin.

## Measured complete-check timing

The review rework specifically required the missing full-check measurement. This
retry interpreted that later specific instruction as a narrow exception to the
generic worker no-full-gate instruction, for offline timing only. It restored
`b466f80d06a3fc7acf3975b3051f0f2e91dc7248` without reimplementing the deletion and
compared it with this attempt's unchanged baseline, not unrelated runner revisions.
The coordinator still owns the authoritative merged-tree gate.

Every timing executes the real complete checker (no selected paths) as
`python3 scripts/check.py --jobs 4 --timeout 600`. A task-private stdlib collector
measures `time.monotonic()` immediately around the subprocess; it records UTC
start/end, exit, exact source/index tree and input hashes, inventory/log hashes,
Python executable hash, affinity, child CPU time and host-load/CPU samples every
two seconds. Inventory capture and isolated reruns are outside the timed interval.
The same Linux x86_64 host, Python 3.12.14 executable, installed dependencies,
22-CPU affinity, fixed four-process concurrency and scratch filesystem are used
throughout. There is no queue-slot wait in these direct measurements.

[Machine-readable receipts](owner-cycle-full-check-timings.json) retain every run,
source and log hash, skip/failure classification and load summary. Raw collector,
input maps, two-second observations, inventories and complete logs are retained
under the task-private `TMPDIR` named in the worker report, not copied from or
written over the runner's main evidence.

| Run order | Wall seconds | Exit | Mean 1-minute load | CPU busy |
| --- | ---: | ---: | ---: | ---: |
| before-1 | 533.062 | 0 | 11.28 | 45.1% |
| after-1 | 494.243 | 0 | 10.58 | 43.3% |
| before-2 | 547.054 | 0 | 12.94 | 44.3% |
| after-2 | 494.639 | 0 | 10.65 | 35.9% |
| before-3 | 485.736 | 1 | 8.28 | 28.7% |
| after-3 | 530.709 | 0 | 12.96 | 47.0% |
| before-4 (replacement baseline) | 553.967 | 1 | 15.97 | 51.1% |

The two passing baseline gates have median **540.058 s**; all three passing
candidate gates have median **494.639 s**, **8.41% lower**. No passing sample was
excluded. Including the failed baseline attempts happens to leave the baseline
median unchanged, but failed gates do not count as qualification. The comparison
has two passing baselines rather than the planned three; both failed replacement
attempts and their raw data are disclosed instead of silently discarded.

The closest observed mean-load match is `before-2` / `after-3`: **12.94 / 12.96**,
with CPU busy **44.3% / 47.0%** (the candidate is not on an idler host). Their
complete-check wall time falls **547.054 → 530.709 s**, **2.99% lower**. These are
measured wall times, not sums of unittest process durations. The shared host is
not exclusively scheduled: load ranges and CPU pressure vary, so this establishes
an observed fixed-concurrency improvement under comparable load, not an identical-
instantaneous-load claim or a universal/default-concurrency throughput guarantee.

Both failed baseline gates report the same unchanged flaky test:
`test_pi_autowork.EngineTests.test_a_conflicting_owner_plan_is_landed_after_each_task`.
Its one required isolated rerun on the unchanged baseline passed (one test,
45.736 s). All 162 units still ran in each baseline attempt; no timeout or resource
gate skip occurred. The candidate's three complete gates all passed without skips.
This failure is reported as unrelated baseline evidence, not a change-caused check
failure or an owner blocker. No flaky-test behavior was altered to obtain timings.

Measured candidate tree: `127151e274bdc99b2c42f60b6018e5e1b36d0b78`; baseline tree:
`ec0140fedbd541eda116bf778151fb018d15d970`. The candidate measurements precede this
evidence readback: only four documentation/evidence paths are subsequently changed.
The collector's explicit hash map covers Python, shell, MJS and JSON files;
readback also compares the entire measured Git tree, including YAML, JavaScript
and extensionless files, allowing only those four evidence-document edits.
Independent review verified all seven logs/inventories, both failure classifications,
timing/load calculations and absence of runtime drift. These measurements are not
the final merged-tree gate receipt.

DOCS-MAINTAINER resume: reconcile the coordinator-owned task/test-thinning records
and changelog with this measured evidence after the normal integration gate.

## Historical source and deletion commit

The first attempt's [removal commit](https://github.com/TrebuchetDynamics/autowork/commit/026e23baf4c226aac2c672e3d0e984a77996b9da)
is immutable evidence of the same 17 module deletions. This retry reuses that
scoped change after reviewing its diff, recomputes closure against the new baseline,
and repairs historical links to that existing deletion commit instead of trying
to embed its own not-yet-created hash. The task report supplies this retry's exact
commit. Historical commands remain evidence, not current instructions; their
pre-deletion source is available from the linked deletion diff and its parent.

TOOLSET-125-e6, TOOLSET-126-6b and TOOLSET-127-b1 should reconcile against this
inventory before thinning tests; do not recreate the deleted suites. No model,
native backend, production or Telegram qualification is implied.
