# Delivery-pipeline audit and local baseline — 2026-10-24

Planning only. Accepted design, metric definitions and experiment protocol live in
[the evaluation owner](../evaluation.md#delivery-pipeline-optimization); `tasks/`
remains the only executable backlog. This report is not proof of implementation,
live qualification or a productivity improvement.

## Scope and evidence

Audit source: `4955a2bf79eb69983d4b5dc7f09b64388653e01a`. A subsequent coordinator
merge `1f833b43` has the same tree. Numeric cutoff: **2026-10-24 18:05:49.816 UTC**
(epoch `1792865149.8163736`), requested rolling 30 days. Runtime snapshots were read
shortly afterward, nonatomically. Source citations below refer to this revision.
Three read-only investigations covered planning/execution/recovery, verification/
landing, and existing scorecard/journal/accounting. No external library contract
change is proposed; no external API research was needed. No codebase-memory tool
or existing codebase map was available; direct source, tests and Git history supplied
the evidence. No generated graph or new observability system was created.

### System map

| Stage / owner | Inputs → outputs | Gates, waits and possible repeated work |
| --- | --- | --- |
| Intent / Plan For Me / SDD | Accepted goal, sources, prior findings → complete native task contracts | Existing handoff/builder check; do not rediscover settled decisions or add another approval loop. `skills/shared/PLAN-HANDOFF.md:18-49`, `skills/engineering/SKILL.md:95-113`. |
| Selection / admission | Pinned TaskStore, dependencies, priority, ownership → admitted task/attempt | `engine/task_select.py:35-63`; `engine/parallel_plan.py:328-387` (under `Src/pi_autowork/`). Hot literal production-file waits differ from cold overlap ranking; resources/protected paths remain real gates. |
| Worker / Pi | Pinned contract/revision, expected writes, checks, retained candidate/findings → report and commit | `engine/parallel_dispatch.py:257-403,1152-1164`; default RPC `pi_runtime.py:59`, frozen run identity/context `pi_rpc.py:30-95`. Retained work and same-attempt recovery already exist. |
| Verification / reviewer | Complete candidate, accepted contract, producing check evidence → independent verdict | `worker.py:28-53,674-682,1249-1256,1303-1319`. Affected checks, batching, conservative selective review and no-repeat guidance already exist. No worker attestation replaces review. |
| Batch/train | Ordered immutable merge steps → checked/reviewed prefixes and per-task verdicts | `worker.py:1075-1186`; default three concurrent reviews. Whole-batch completion still gates consumption; failed halves/singles and next-car overlap already exist. |
| Integration / closure | Verdict, current ownership/contract/tree → serial integration and receipt-backed close | `engine/parallel_integrate.py:763-764,832-921,1120-1183`. Integration lock still covers review in the single gated path; broader redesign deferred. |
| Canonical main / publication | Landed commits → background full-check qualification → separately authorized publication | `supervision/main_checks.py:90-132,172-187`; `coordinator.py:1306-1338`. Full evidence can be reused only under existing binding rules; affected evidence cannot qualify main. Last-green push boundary is preserved. |
| DOCS-MAINTAINER / recovery | Bounded task/main/ledger/overlap triggers and retained reports → source-backed repair or durable outcome | `maintainer.py:56-106,162-171,438-548`; `coordinator.py:204-230,2246-2467`. Background/throttled maintenance and bounded triage/provisioning recovery already exist. |
| Evaluation | Git closures/receipts, lifecycle journal, private usage/attention → scorecard | `scorecard.py:223-439`; `accounting.py:1-210`. Completion counts are not accepted-backlog success; unknown billing/time is not zero. |

All abbreviated Python paths in the table are beneath `Src/pi_autowork/`. Public
compatibility entrypoints remain under `pi-autowork/`; no source relocation is proposed.

## Quantitative baseline

### Cohorts and coverage

| Quantity | Observed result | Interpretation |
| --- | ---: | --- |
| Current committed store | 155 tasks, 18 goals; 147 done, 6 open, 2 superseded | Inventory, not a delivery cohort. |
| Distinct closure cohort within 30-day window | 100 | 54 verified, 46 manual/legacy-manual by current scorecard classification; zero invalid coordinator-verified closures. |
| Verified closures per requested window day | 1.8 | 54 / 30; instrumentation does not cover 30 full days. Not deliveries per runner-hour. |
| Integration decisions | 121 integrated, 123 held (244 transitions) | 50.4% held; repeated transitions, not unique task failure rate. |
| Explicitly attributed regressions in verified cohort | 0 / 54 | Unreported/misattributed defects remain unknown; not a zero-defect claim. |
| Recorded intervention lower bound | 46 manual closures | May be one bulk owner action; not 46 distinct conversations or minutes. |
| Unattended share, owner minutes, billed cost/task | Unknown | No attention ledger; every retained usage row has unknown cost. |
| Verified deliveries / runner-hour | Unknown | Missing delivery facts and reliable uptime denominator. |

Journal reader observed **25,387 deduplicated envelopes**, no torn/duplicate records
through cutoff. Retained envelopes start October 17 04:58:33 UTC, but non-acceptance
lifecycle facts start October 21 16:47:02 UTC. Git-derived acceptance may be backdated.
There are 73 lifecycle task IDs, 113 task-attempt keys and 103 dispatched keys;
42 dispatched keys have no same-key integration. These include retries, superseded
and still-active work: do not call them 42 terminal failures.

For the 54 verified tasks, endpoint coverage is accepted 52/54, dispatched 53/54,
reviewed/integrated/closed 54/54, **delivered 0/54**. `execution_journal.py:227-237`
co-emits reviewed and integrated; their near-zero difference is not measured review
duration. `engine/lifecycle_history.py:109-118` has delivery observation logic, but
no delivered facts were observed: this audit does not establish its failure cause.

### Partial latency distributions

Minutes; median and nearest-rank p95; missing/reversed pairs excluded, never imputed.
All rows below are restricted to verified completion IDs, with retry attempts retained
where specified. Rows have different samples and cannot be added.

| Endpoint pair | n | Median | p95 |
| --- | ---: | ---: | ---: |
| First acceptance → first dispatch | 52/54 tasks | 73.57 | 563.93 |
| First dispatch → first integration, including retries | 53/54 tasks | 52.76 | 656.75 |
| Acceptance → lifecycle closure | 52/54 tasks | 158.38 | 1022.80 |
| Dispatch → integration, matched successful attempt | 53 | 32.56 | 97.99 |
| Running → reported, including retry attempts | 75 | 20.15 | 57.34 |
| Reported → first integrating | 75 | 0.33 | 72.71 |
| First integrating → integrated | 54 | 7.82 | 22.87 |
| Integrated → lifecycle closed | 54 | 0.27 | 0.54 |

Acceptance→dispatch includes dependency, authority and scheduling waits. Run→report
is wall time, not model compute. First-integrating may include holds. Main landing,
full qualification and closure are distinct; acceptance→main-delivery is unknown.
The current scorecard correctly returns missing full-cohort timing when any endpoint
is absent; partial distributions above do not replace those conservative metrics.

Across **all** observed attempts (not just verified tasks), 95 first-running→reported
pairs sum to **36.4232 attempt-hours**; 8 running keys lack reports. Parallel spans
overlap and may include suspension. Do not divide 54 by this number and label it
runner-hour productivity: the cohort, coverage and concurrency semantics differ.

### Rework, resources and cost

- Lifecycle holds: 48 events / 25 tasks / 44 attempts. Verification failures:
  35 events / 19 tasks / 34 attempts. Retries: 19 events / 16 tasks. Within the
  verified cohort, 18 tasks have held history, 14 verification failures and 13 retries.
- Legacy hold-cause occurrences: unknown 100, conflict 81, validation 74, blocker 22,
  scope request 9, scope 7, timeout 5, reviewed-twice 5, overlap 4, crash 4. These
  are not a disjoint failure cohort. Nine review-rework and five failed-review-rework
  envelopes indicate recovery work, without proving its net cost.
- Existing recovery metric: 10 matched adoption/resume episodes among 79 observed
  restart/interruption episodes (12.66%). Unmatched/censored episodes prevent treating
  this as eventual recovery success or no-lost-work qualification.
- Usage ledger: 713 unique window runs, 83 unattributed overhead runs; every cost
  unknown. Reported total tokens sum to 1,998,895,405, including 113,685,914 overhead
  tokens. This unreconciled ledger sum is not provider billing, a verified input/output
  split, or complete cross-role usage. Existing task 386 owns accounting repair.
- Only five retained main evidence receipts are available, green/PASS, with finish
  times but no starts. They cannot supply check duration, pass rate or queue p95.
  The sampled current check targeted `8b99850e`, not audit HEAD. No fresh main pass
  for audit HEAD is claimed. Retention is bounded in `main_check.py:337-374`.
- Host check-slot admission and aging already exist (`main_check.py:131-205`), as do
  port leases and wait accounting (`engine/parallel_integrate.py:872-876`). Host CPU,
  memory saturation and check-cache hit rate were not measured. More concurrency
  cannot be justified from this baseline.

### Reproduction and privacy

Use the existing `autowork scorecard --days 30 --json <repository>` into private
storage. For this fixed-cutoff analysis, call `scorecard._collect(repo, 30, cutoff)`,
then `observations(data, cutoff)` and `evaluation([observations], cutoff-30*86400,
cutoff, None)`. Filter journal envelopes at cutoff with the existing deduplicating
reader; group sorted lifecycle facts by task and attempt, and slot-state envelopes
by `(task_id, slot.attempt_id)`. Keep first endpoints, reject missing/reversed pairs,
restrict timing samples to receipt-valid verified completion IDs, then use
`statistics.median` and `sorted(samples)[ceil(.95*n)-1]`. Preserve counts of excluded
and censored pairs. Legacy accounting rows without IDs remain distinct.

Inputs: `<git-common>/autowork-execution/journal.jsonl`, slot metadata and retained
main-evidence receipts; repository-specific `<state-root>/<repo-hash>/runs.jsonl`
and main-check metadata; committed task records/receipts and Git history. The
attention file was absent. No raw prompts, credentials, profile identities or other
projects' state were inspected or copied. Only sanitized aggregates are saved here.
The analysis-only import needed the existing `pi-autowork/engine` compatibility
path for `worktree_paths`; this is not a claim the installed CLI is broken. Later
reproduction can differ because runtime files rotate and Git/receipt validation
advances; the observations were not a transactionally frozen historical archive.

## Top five findings and strategy

1. **High, fact — unsupported rollback attribution creates rework.**
   `optimistic.py:62-95` returns every candidate if one failure lacks a matching
   traceback owner; `coordinator.py:2203-2220` reverts/reopens that list.
   `test_optimistic.py:72-78` explicitly tests this fallback. A source-function probe
   returned both A and B for an unknown failure. Historical tasks 327-02, 330-0a,
   331-be, 332-6c, 339-54, 349-d4d37513 and 353-9db87df7 record misattributed
   revert/re-land incidents. **Chosen:** unknown means no automatic culprit, red-main
   repair stays active. Benefit magnitude unknown; narrow correctness repair first.
2. **Medium, fact — completed review waits for its batch tail.**
   `worker.py:1112-1186` reviews concurrently but emits the batch result only at the
   end; `coordinator.py:1720-1724,1795-1799` waits for process exit. **Chosen:** serial
   eligible-prefix consumption, not more reviewers or a general lock redesign.
   Potential saved time is the eligible tail interval; current causal share of the
   72.71-minute reported→integrating p95 is unknown.
3. **High, fact — the optimization denominator and outcome endpoint are missing.**
   No delivery events, trustworthy uptime, billing or owner-time coverage. Existing
   `scorecard.py:332-397` correctly preserves unknowns. **Chosen:** expose bounded
   phase/coverage diagnostics in that report; use explicit observation windows in
   the already-gated pilot, not a new telemetry daemon. No current ROI claim.
4. **Medium, fact — a safe failed maintainer call can spend its only opportunity.**
   `coordinator.py:2334-2339,2443-2467` drops failure class into generic `failed`;
   `maintainer.py:354-355,459-465,544-548` deduplicates unchanged failures, with only
   merge conflict retryable. A pure probe reproduced suppression. Local maintainer
   metadata had 79 merged receipts and no failed receipt, so current incident rate
   is unknown. **Chosen:** role-local bounded safe technical retry; preserve uncertain
   execution fences and semantic-result deduplication.
5. **Medium, fact — prevention instructions disagree at the handoff.**
   `maintainer.py:162-171` advises dependency ordering for overlap, contradicting
   `skills/shared/PLANNING-CRAFT.md:170-182` and dynamic scheduler policy. Historical
   task 333-34 explicitly records a dependency for shared tests, not a product
   prerequisite. Separately, 388/390 acceptance requires executed checks but their
   typed checks only selected tests (`affected_tests.py --json`) and validated the
   store; `scripts/affected_tests.py:254-268` requires `--run` to execute. **Chosen:**
   align maintainer wording and repair inactive 390's check handoff in place; do not
   alter active 388 or build a new semantic validator. Source tests prove wording,
   not model adherence; compare handoff quality in a later authorized pilot.

Architecture judgment: keep the existing seams. The narrow rollback function,
maintainer prompt/result boundary, scorecard aggregator and batch-result consumer
have concrete callers and fixture oracles; adding another scheduler, evidence
registry or dependency layer fails the necessity test. General integration-lock
extraction and prompt compression are deferred until their measured contribution
outweighs migration/race risk. Existing check reuse and selective review are strengths,
not missing optimizations.

## Frontier, reconciliation and parallel lanes

Five new tasks, all under the existing **EVALUATION** goal (still unmet; priority/focus
unchanged). Exact contracts are in `tasks/items/<ID>.md`; proposed test oracles are
explicitly unrun. Existing unrelated queue ranks are unchanged.

| Order / ID | Outcome | Effort / risk | Prerequisites and parallel lane |
| --- | --- | --- | --- |
| 1 — TOOLSET-391-8eb4527a | Unknown attribution cannot trigger blanket rollback | S / medium | Highest-value next new task. Narrow optimistic function and existing tests; independent of metrics/maintainer work. |
| 2 — TOOLSET-392-5f9e11f6 | Maintainer does not invent dependencies for overlap alone | S / low | Independent source-contract fix; overlaps 393's maintainer file/tests, so coordinate integration. |
| 3 — TOOLSET-393-f5116fdc | Bounded safe technical maintainer retry | M / medium | Reuse current technical-recovery helpers and inspect active 385's final delta; no duplicate subsystem or artificial product dependency. |
| 4 — TOOLSET-394-5fe19498 | Scorecard phase distributions with honest coverage | M / low | Independent reporting lane; no accounting collector changes or live prerequisites. |
| 5 — TOOLSET-395-6cbb101f | Passing batch prefix lands before slow tail | M/L / high | Bounded five-file concurrency slice; no general lock rewrite. Coordinate coordinator-file overlap with 393/active 385, and test overlap with 391. |

No new product prerequisite edges: these are independent outcomes on already-present
source. Their shared cold files/tests are potential merge conflicts, not prerequisites;
current hot-file, protected-path and resource admission still governs real execution.
No new `exclusive`/`live` resource is justified. Candidate preparation/review may be
parallel, but canonical writes stay serialized. Attribution and scorecard are the
clearest separate lanes; maintainer/prefix changes require current ownership checks.

Updated existing **390** in place: executing focused/native/affected checks and an
explicit no-skips/qualified-interpreter handoff, without changing its 388/389 gate.
Updated **389** only with the experiment cross-reference, retaining its live denial,
owner ownership, scope and pilot limits. **388/385/386 and observer contracts are
untouched**. Closed implementation/history/qualification records are not reopened.
No automatic successor task is added: this known batch is complete, and further
optimization depends on evidence rather than a speculative roadmap.

Existing tasks deliberately reused, not duplicated:

| ID | Reconciliation |
| --- | --- |
| FLEET-OBSERVER-01 | Live-owned observer/writer repair under FLEET-RECOVERY; preserve its contract and guards. |
| TOOLSET-385-6021ba81 | Live-owned technical triage/provisioning reconciliation; new maintainer slice must inspect its final delta and avoid duplicating the shared mechanism. |
| TOOLSET-386-4288b2e0 | Live-owned JSON/compaction/nested-tool accounting; do not add a competing accounting implementation. |
| TOOLSET-388-b422fa9e | Integrating at the audit cutoff; integration refresh found coordinator-verified closure in `7e295706`, backed by `tasks/evidence/TOOLSET-388-b422fa9e.toml`. Preserve that closure and the new qualification report; no RPC reimplementation. Installed qualification remains 389. |
| TOOLSET-389-6dedfd8c | Existing owner-owned, live-denied installed delivery/recovery and matched measurement pilot. Reuse its single authority question; do not schedule it or duplicate a live task. |
| TOOLSET-390-e1c2afa6 | Still depends on 388 and 389. Reconcile its inactive check handoff; production channel/steering work remains blocked by installed qualification. |
| TOOLSET-334-f9 / TOOLSET-344-7dadea23 | Manually closed partial parallel-review/optimistic implementation; retain history. New tasks cover specific remaining gaps, not reopened old contracts. |
| TOOLSET-336-3c / 338-82 / 340-64b75d92 / 341-eb82856d / 342-0153a52b / 384-45005b0c | Existing check reuse, affected checks, half/single concurrency, test-path scheduling and completeness work; no duplicates. |
| TOOLSET-307-5a / 308-f9 / 309-05 / 310-50 | Existing telemetry, attribution, attention and scorecard; extend the existing report rather than replace them. |
| TOOLSET-311-d7 and manually closed live companions | Owner closed without live evidence. Keep closed and unqualified; this planning request does not reopen them. |

At the ownership snapshot, three workers were birth-matched live (observer, 385, 386)
and 388 was integrating; the coordinator release was `8b99850e`. Configuration
activation was not inspected. Snapshot freshness is not a continuing lease: refresh
actual activity before execution or contract changes. No active contract is edited.
Before landing this plan, canonical main advanced to `7e295706` with 388's
qualification report and verified closure. The planning branch incorporates those
changes; runtime source bytes are unchanged. Historical baseline/snapshot observations
above remain pinned to their original cutoff, not retroactively updated. Task 390's
remaining unfinished prerequisite is 389; its declared dependencies are preserved.
The prepare audit also reports unrelated historical-name/goal-without-work notices;
these are not proof of live defects or permission for a repository-wide rewrite.

**Genuine owner input:** the already-recorded 389 pilot decision: owned environment,
operator window, allowed spend/provider and publication limits. No new product choice
is needed for the bounded offline slices. The existing 390 delivery gate and closed
30-day evaluation decision remain binding. Model quality, installed engine closure,
real interruptions and cross-repository value remain unqualified.

## Verification and evidence confidence

- High confidence in current source branches and deterministic suppression/attribution
  probes; historical incident records corroborate rework without proving current rate.
- Moderate confidence in local descriptive timing: explicit samples/cutoff, but partial,
  non-atomic, completion-selected and right-censored. Low confidence in causal speedup;
  no matched optimization experiment ran.
- The read-only quality audit ran 18 focused offline tests: 4 planning decomposition,
  12 existing technical recovery, 2 maintainer overlap/conflict-retry tests. Passing
  existing guards does not implement the proposed behaviors. Other investigators ran
  structured queries/source probes, not product tests.
- Capability/prepare check: release `4955a2bf`, converted store, `READY`, no refusals;
  four in-flight IDs above. Legacy-name/goal notices were inventoried and left outside
  this bounded scope. SDD protocol pin verified at revision
  `1be8e34187e34647bb83adc3a1323b26ae6f6abe`, SHA-256
  `c4b97ce3d7f24be0e67fd612c7595f65504872e3a9f8d338d098b2363fdb66ef`.
  Application: capability boundaries, explicit exclusions, acceptance-to-oracle task
  records and experiment stop rules, reusing native owners rather than extra artifacts.
- Final planning checks: `autowork tasks validate --worktree .` passed for **160 tasks,
  18 goals, zero drafts**; changed-document link/anchor/script checks using the existing
  Docs Sync `check_document` API passed; `git diff --check` passed. All five new tasks
  have at most five existing-file touches and three acceptance oracles. Byte comparison
  confirmed all four active records unchanged. Parent independently reproduced the
  100/54/46 closure counts, task timing distributions, endpoint coverage, 25,387
  envelopes and 121/123 integration transitions at the fixed cutoff.
- Independent builder review found two material gaps, both corrected in the plan:
  atomic generation/attempt-bound batch publication was missing from current source,
  and phase endpoint/cohort rules were ambiguous. A bounded follow-up found no remaining
  blockers. This is plan readiness, not implementation or live acceptance.
- `scripts/affected_tests.py --base 4955a2bf --json` conservatively selected the full
  suite because untracked subagent runtime artifacts have no test mapping. That suite
  was **not run** for this documentation/task-only batch; those private artifacts are
  excluded from the commit. Document/task validation above is the proportional evidence.

No implementation, model/provider experiment, worker dispatch, installation, service
change or push was performed. Source/default configuration, offline tests, prior
bounded RPC smokes and live-installed qualification remain separate evidence levels.
