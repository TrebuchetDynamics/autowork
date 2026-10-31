# Is Autowork worth it?

Autowork has to answer one question: does it build more good software than it costs
in model spend and owner attention? This page records an outside assessment of the
project (2026-10-21) and the evaluation that would answer that question. The
assessment is a subjective engineering opinion supplied by the owner, not a
benchmark. The later delivery-pipeline section links a bounded local baseline;
it does not qualify the proposed 30-day evaluation.

## Assessment (2026-10-21)

| Dimension | Rating | Reading |
| --- | --- | --- |
| Technical concept | 9/10 | Ambitious and well directed |
| Architecture | 8/10 | Thoughtful engineering decisions |
| Proven reliability | 5/10 | Needs sustained live evidence |
| Potential value to the owner | 9/10 | Especially across several projects |

Spawning several coding agents is not new. The interesting part is a persistent
software-development control system:

1. **A person defines intent:** requirements, goals and acceptance criteria.
2. **Autowork coordinates execution:** Git-native tasks, dependencies, leases and
   worktrees.
3. **Agents implement and review:** in parallel where it is safe, with independent
   verification.
4. **Verified changes reach Git:** receipts, recovery, integration, then the next
   ready task.

### What could set it apart

Established autonomous coding orchestrators already exist, so no single part is
novel. The combination might be:

- **Git-native intent:** tasks belong to the repository (`tasks/`), not an external
  database.
- **Several hosts:** Hermes, Claude Code, Codex and Pi run the same workflows.
- **Execution discipline:** typed authority, dependency and resource gates, verified
  closure and crash recovery.
- **Documentation-driven planning:** Docs Sync keeps requirements and executable
  tasks in step, and prepares the task store itself
  ([`autowork tasks prepare`](../pi-autowork/task-store.md#preparing-a-repository-autowork-tasks-prepare)).
- **Unattended operation:** runners keep doing useful work without step-by-step
  supervision, and an empty queue costs no model calls.

Whether this combination beats existing tools is **not yet benchmarked**.

### Risks

- **Recursive infrastructure.** Autowork can absorb more effort improving itself
  than building the products it exists for. Agents supervising agents, and then
  tasks to make that supervision safer, is interesting engineering, but it is not
  delivery.
- **Permissive defaults.** Loading the Hermes plugin sets `approvals.mode: off` and
  `agent.max_turns: unlimited` ([read before installing](../README.md#read-before-installing)).
  Combined with unattended runners, that matters wherever agents can reach
  credentials or production systems. Evaluate with controlled permissions: no
  production credentials, disposable or low-risk targets, and pushes only to
  repositories where an automatic push is acceptable.

### Recommendation

Prove safe, productive autonomy before adding layers. Spend the next development
cycle using Autowork to build other products, not mainly to build Autowork.

The bar is concrete: from a backlog of about 30 well-defined tasks, an unattended
overnight run delivers about 10 verified improvements that would otherwise take
hours of owner attention. If every session still needs review, deadlocks are
frequent, or the supervisor needs manual correction, the infrastructure is not yet
paying for itself.

Commercial potential exists, but a valuation would be premature. It first needs
repeatable reliability, simple onboarding for other developers, and evidence that
it outperforms the alternatives.

## 30-day evaluation

Status: Accepted

Owner decision, 2026-10-21: make `autowork scorecard` answer whether Autowork produces
more verified software per dollar and per hour of owner attention than manually
supervising coding agents. Success is enough trustworthy data to decide whether
Autowork is worth operating and improving, not a better dashboard. The targets below
are proposals to judge the result by, not acceptance criteria for the instrumentation.
The work is goal `EVALUATION` in [`tasks/`](../tasks/), in four bounded tasks plus the run:

1. Lifecycle telemetry in the existing engine journal and receipts (TOOLSET-307-5a).
2. Per-task cost and owner attention (TOOLSET-309-05).
3. Regression attribution through explicit links only (TOOLSET-308-f9).
4. The evaluation scorecard, with a 30-day window, JSON and CSV export and an
   optional baseline (TOOLSET-310-50).
5. The owner's 30-day run on at least two other repositories (TOOLSET-311-d7).

Rules for every measurement:

- Unavailable billing or attention data is **unknown, never zero**. Subscription usage
  gets no invented price. Each value is labelled measured, estimate or missing.
- Telemetry stays local and private: no credentials, prompts, usage records or
  sensitive logs are committed. Writes are cheap, nonblocking and crash-safe, with no
  new dependency or background service.
- Per-attempt data stays separate from per-task aggregates; retries never
  double-count completions or cost. Telemetry observes; it never changes execution or
  authority decisions.

Scheduling: the remaining TOOLSET-304-2c atomic-write fixes come before any broadening
of concurrent task-store writes, and this instrumentation must not dominate the next
cycle, whose main purpose is to use Autowork on other products. Measure at least two
other repositories, preferably on different stacks, before any major new architectural
change.

Run Autowork for 30 days on real development repositories with controlled
permissions. Measure:

| Metric | Proposed target | Measured today by |
| --- | --- | --- |
| Accepted tasks completed without intervention | Over 70% | Verified completions per day and the percentage of verified completions without recorded interventions or task-attributed owner time; manual closes are separate owner interventions. Missing lifecycle coverage remains unknown. This completion-cohort percentage is not a forecast for all accepted/open tasks. |
| Regressions introduced by merged work | Under 5% | Explicit receipt-linked reverts and `Regression of` notes; the rate counts distinct affected tasks in each verified completion cohort, not every fix or same-file edit. Unreported defects remain undetectable. |
| Owner attention per completed task | Falling week over week | Recorded minutes per verified completion, including repository overhead; missing task attention is unknown, never zero. Logging is not proof of full time coverage. |
| Cost per verified task | Lower than supervising an agent directly | Private provider-reported spend across all attempts and roles per verified completion; unknown billing/subscription prices remain missing. Optional owner-supplied baseline values and differences are estimates. |
| Time from task creation to merge | Clearly faster than a baseline | Median/p95 first acceptance-to-delivery and first dispatch-to-integration for verified completions; missing endpoints remain unknown. Acceptance is the first committed task record, not a draft's creation time. The supported baseline compares cost and owner minutes, not duration. |
| Crash and restart recovery | No lost work, no duplicate closure | Observed restart/interruption episodes recovered through worker adoption/resume, plus existing offline recovery fixtures. A resumed attempt is not proof of eventual delivery or no lost work. One live disposable-repository run is recorded (2026-10-15, TOOLSET-091-00 in `TODO.archive.md`: SIGKILL/restart adopted its worker without a second dispatch); real-repository qualification remains pending. |

### Run and interpret the scorecard

```sh
autowork scorecard --days 30 --json /path/to/project-a /path/to/project-b
autowork scorecard --days 30 --csv /path/to/project-a /path/to/project-b > /private/evaluation.csv
autowork scorecard --days 30 --baseline /private/baseline.json /path/to/project-a
```

The report has per-runner and pooled overall results, consecutive seven-day buckets
(oldest first, with a shorter last bucket if needed), and absolute first-to-last-week
changes. Throughput uses each bucket's actual day count. Metrics share the same
values and `measured`/`estimate`/`missing` labels across text, JSON and CSV. A window
without verified completions has missing rates, not zero rates. Retries add each
unique run's cost but no extra completion; manual closures enter neither verified
counts nor the unattended percentage. Missing inputs propagate into changes.

A baseline is an owner-supplied JSON object, for example:

```json
{"cost_per_verified_task_usd": 5, "owner_minutes_per_verified_task": 15}
```

Its values and summary-minus-baseline comparisons are labelled `estimate`, never
measured. Without it the report says `no baseline`. Keep these files and exports
private. The [component report contract](../pi-autowork/README.md#evaluation-report)
defines JSON/CSV fields, denominator and percentile rules, attribution, telemetry
coverage and partial-week limits. The 30-day fixture and format-parity checks live in
`pi-autowork/tests/test_scorecard.py`; these are offline evidence for the report, not
results from operating Autowork on other products. The owner's real-repository run
(TOOLSET-311-d7) remains separate and unqualified by this instrumentation.

The goal is not the number of agents Autowork can run. It is how much good software
gets built while the owner is doing something else.

## Delivery-pipeline optimization

Status: Accepted

### Objective and authority

The owner's 2026-10-24 planning request accepts discovery and a small executable
frontier to improve **verified deliveries per runner-hour**, with regressions and
human intervention as counter-metrics. This is an engineering refinement of
`EVALUATION`, not a new product strategy or permission to run experiments now.
The [source audit and baseline](research/delivery-pipeline-2026-10-24.md) record
observed source, coverage, unknowns and the existing tasks being reused.

Planning chooses reversible details below. Future implementation remains subject
to ordinary task admission and independent review. No fleet/model/configuration
change, worker launch, restart, live operation, remote publication or spend is
part of this planning occurrence. Preserve all owner pauses, including the
manually closed, unqualified 30-day run (TOOLSET-311-d7).

### Outcomes and measurement contract

1. **Trustworthy comparison:** existing scorecard outputs show per-phase observed
   sample counts, missing/censored coverage and median/p95 without changing the
   conservative full-cohort metrics. Never substitute attempt-hours for runner
   uptime, or integration/closure for actual main delivery.
2. **Less unnecessary rework:** no automatic cohort-wide revert when any failing
   test has unknown attribution; no dependency created merely for a shared path;
   safe maintainer transport failures get a bounded retry instead of permanent
   suppression. Existing genuine dependencies and semantic-result deduplication
   remain intact. These are deterministic acceptance outcomes, not claimed savings.
3. **Less post-review waiting:** an eligible contiguous passing batch prefix can
   land before its tail review finishes, without rerunning already-valid checks or
   changing evidence equivalence. Unknown, partial or stale evidence cannot land.
4. **Demonstrated benefit, not activity:** an authorized matched pilot should show
   a positive delivery/runner-hour change, with a planner-selected **20% relative
   improvement** as the practical adoption target, no increase in attributed
   regressions or owner minutes/interventions per verified delivery, and no lost
   work, duplicate closure or authority violation. This is an experiment decision
   threshold, not a measured effect or an offline implementation acceptance gate.
   Missing denominator, delivery evidence or attention coverage means **inconclusive**.

For a future pilot, count each receipt-qualified task once after its integration
is an ancestor of the sampled canonical main and a covering full-main check passes;
record close, landing and qualification times separately. The runner-hour denominator
is the union of explicitly observed owned-runner availability intervals, not worker
count multiplied by wall time. Include idle/admission/recovery intervals while the
runner is available; exclude only declared shutdowns, reporting them separately.
Unobserved gaps are missing, never assumed uptime. Report deliveries per elapsed
pilot hour as a separate end-to-end metric so shutdowns cannot improve the headline.

### Capability boundaries and chosen designs

Use the existing Python standard-library modules under `Src/pi_autowork/`, unittest
fixtures in `pi-autowork/tests/` and `tests/`, and existing docs/task records. No new
service, queue, telemetry store, spec registry, approval layer or scheduling authority.
The source style is small helpers and explicit dictionaries, for example the current
`scorecard.metric(value, unit, status='measured')` returns a missing value rather than
inventing zero. Keep that missing-value contract and existing JSON/CSV/text parity.

| Capability | Chosen boundary and executable oracle | Dependency |
| --- | --- | --- |
| Rollback attribution | `optimistic.regression`: if any named failure lacks supported attribution, return no automatic culprits for that cohort, including mixed known/unknown cases. Retain red main, last-green publication and existing repair handling; fully attributable regressions retain targeted rollback. Extend `test_optimistic.py` and main-check fixtures. | None; existing optimistic implementation is already present. |
| Overlap planning | Change only maintainer overlap instructions: real producer/consumer dependencies, not artificial edges for file overlap. Legitimate dynamic waits may remain unchanged. Extend the existing overlap prompt oracle. | None; preserve scheduler policy. |
| Technical maintainer recovery | Carry role-local failure and cleanup/acceptance certainty through ordinary/background/ledger/rolling-plan results. Reuse durable technical-recovery reservation/backoff; allow at most three safe submissions per unchanged incident with existing backoff. Completed semantic outcomes remain deduplicated; ambiguous submission or cleanup never replays. | Existing recovery work 385 must be inspected when landed, not duplicated or modified while active. |
| Phase diagnostics | Extend existing scorecard aggregation/exports with labelled observed task/attempt spans and coverage. Keep whole-cohort metrics strict. Do not infer main delivery or uptime from absent evidence, add collection services, or duplicate accounting work 386. | None; report-only, existing journal is the input. |
| Passing-prefix delivery | Consume only a contiguous independently reviewed passing prefix of an already-gated immutable batch chain. Keep producer lifetime separate from serial landing; upgrade the existing verdict channel for safe publication and reuse engine integration/closure. Tail reviewers continue in detached checkouts. Existing verdict files require the atomic/generation binding upgrade below before concurrent consumption. | No artificial dependency on other optimization tasks; existing guards apply. |

#### Prefix publication and crash contract

Current `worker.batch_review` writes a task-keyed JSON file directly; process exit
is the existing publication barrier. **Atomic, attempt-bound verdicts are not already
implemented.** The prefix task must upgrade this existing private batch channel:
allocate a fresh unpredictable generation per producer; publish by same-directory
temporary file, flush/fsync and atomic rename under a generation-specific directory
within the existing `state/batch/` owner. Each record binds generation, task ID,
engine attempt ID, accepted contract hash, candidate commit, batch base, prefix tree,
producing check selection/command and review policy. The parent carries the expected
identity from admission; review text cannot supply or override it.

Only the current owned producer's fully published matching records may enter the
contiguous prefix. A late cancelled/old producer writes only its old generation,
never the new producer's path. Stop invalidates its generation before replacement;
uncertain cleanup blocks replacement. Restart conservatively invalidates unconsumed
producer generations and uses existing engine recovery; do not adopt verdicts merely
because files exist. Already integrated prefixes are reconciled/closed from existing
engine receipts, never integrated again. A crash after consuming a verdict but before
engine integration may require ordinary re-verification, not invented acceptance;
a crash after integration but before closure uses idempotent engine close. A terminal
batch result cannot re-enqueue its already-integrated prefix. Existing per-task and
whole-chain checks still validate what would actually land; no widened equivalence.
No second registry, schema authority or general lock redesign is needed.

#### Phase cohort and endpoint contract

For the new diagnostic report, choose the **first timestamp of each endpoint kind**
per identity after deduplication, not the first convenient ordered pair. If first end
precedes first start, exclude as reversed even if a later end could yield a positive
span. Use all retained facts through the report cutoff to resolve endpoints.

Task and attempt-phase rows use tasks whose latest receipt-valid verified close lies
in the report window. Task rows collapse attempts; attempt rows retain distinct
`(task_id, attempt_id)` keys for those tasks, including failed/retry attempts. A phase
may start before the window; disclose that the window selects completions, not starts.
Within each phase, report eligible identities, observed pairs, missing-start,
missing-end-terminal, right-censored and reversed counts. Classify missing start first;
with start but no end, a later attempt of the same task or an observed closed state
at cutoff makes it terminal-missing; otherwise it is right-censored (including held
or interrupted attempts, which can resume). Do not infer terminal failure from a hold.

The separate all-attempt exposure diagnostic is a different cohort: attempts with
first running in `[window_start, cutoff]`, across all task outcomes. Sum only pairs
whose first reported endpoint is also within that window and not earlier than running;
classify other missing/reversed endpoints as above, never clip or extrapolate a span.
Exclude starts before the window and count them as left-excluded, not zero exposure.
Label this **observed completed attempt-span hours**, never runner uptime or delivery
throughput. Empty distributions have missing median/p95; p95 uses nearest rank.
Coverage counts accompany JSON, CSV and text without altering existing summary fields.

### Safety invariants and non-goals

Always preserve typed authority, task/attempt/contract identity, actual writer leases,
resource/port/check-slot limits, owner priority and holds; protected paths still require
admission. Independent reviewers inspect the complete candidate under current policy,
never receive steering, and cannot be replaced by worker attestations. Keep immutable
producing-tree/command evidence and existing narrowly defined planning-equivalence
exceptions; do not widen those exceptions. Affected evidence is never a full-main pass.
Only landing/closure writes are serialized; no unverified/stale tree may land.

Do not increase worker/review/check concurrency, change models or enable automatic
steering. Do not remove checks, broaden selective-review skips, disable optimistic
policy, mass-reopen historical tasks, rewrite receipts or treat manual closure as
qualification. Do not overhaul the integration lock, compress prompts or build a
causal bisection service without subsequent evidence. Unknown attribution is not
proof of innocence, and traceback ownership is not universal proof of causation.

Pre-mortem: a stale prefix lands after main/contract drift → existing identity guards
plus race fixtures; a retry duplicates an accepted uncertain call → durable reservation
and cleanup fences; partial metrics imply broad success → explicit coverage, censoring,
missing-value and format-parity fixtures. No source/test/instruction files change in
this planning pass.

### Controlled experiment plan

**Do not execute from this plan alone.** Offline implementation fixtures belong to
the saved tasks. Live/model work has no authorized task: the owner deleted the former
installed-pilot record on 2026-10-31. The separate production controls still wait for
installed delivery/recovery proof.

1. **Freeze inputs:** record baseline/candidate source and installed release, task
   contract hashes, model/provider, SDK/Pi versions, machine/resources, optimistic and
   review policy, checks and cache state. Match independent task pairs by risk,
   language, expected touches and acceptance complexity; exclude live-authority work.
2. **Replay offline first:** fake reviewers with deterministic barriers and bounded
   process fixtures compare unchanged baseline with one change at a time. Cases:
   unattributed versus attributable failures; hot-to-cold overlap without a real
   dependency; safe failure/readiness recovery versus uncertain submission; fast
   prefix/slow tail plus crash, replay and main drift. Record operation counts,
   simulated waits and safety outcomes, not real-model productivity.
3. **Authorized pilot:** reuse the installed-pilot isolation, spending cap and stop
   conditions; do not enlarge its currently denied authority. Initially use its
   bounded engineering pair; make no productivity claim from n=1. Only if separately
   authorized, target at least 20 comparable deliveries per condition in alternating
   baseline/candidate order. Bound the observation window to 7 days per condition;
   fewer samples or inadequate coverage produce an inconclusive result, not another
   automatic run. Never run the same accepted task twice against canonical state.
4. **Measure:** report attempted, failed, open/censored, manually closed and verified
   delivered cohorts; phase median/p95 and paired differences; check-slot wait versus
   check execution; reviews/retries/reverts and reused checks per delivery; runner and
   elapsed hours; all-attempt/role usage with billing coverage; recorded owner minutes
   and interventions. Use existing journals, receipts, private scorecard exports and
   `autowork attention`; collect explicit runner-window endpoints in the existing
   private pilot evidence. Baseline missing endpoints cannot be backfilled as facts.
5. **Interpret and stop:** publish only sanitized aggregate evidence in this owner.
   Separate source-contract results from model adherence. Show uncertainty (paired
   resampling intervals where sample size permits; otherwise descriptive results).
   One authority violation, lost candidate, duplicate closure, stale evidence landing,
   unexpected external write or unbounded retry stops the pilot. Any regression or
   attention increase triggers investigation before adoption; uncertain causality
   never triggers blanket rollback. Revert only the candidate optimization through
   normal reviewed Git changes if unsafe; do not restart/update services here.

The first measured experiments should target attribution/rework and completed-prefix
waiting. A specification-quality comparison can use the same matched protocol with
an acceptance-to-oracle handoff versus its prior form; no new semantic admission
engine is planned. RPC context compression and steering are hypotheses to evaluate
only after existing qualification/control prerequisites, not defaults to enable.

### Handoff and validation

The task records linked from the audit contain exact proposed focused checks,
write sets, acceptance oracles and stop conditions. Future test names are explicitly
proposed/unrun; they are not claimed to exist or pass today. Workers run focused/task
checks and `scripts/affected_tests.py --run`; normal merged-tree/main gates remain
with the runner. Existing active records are not re-contracted. Record-only readiness
is not live admission or execution authorization.

Keep the existing EVALUATION goal unmet. The five new bounded slices fit one batch;
there is no automatic rolling-plan successor or new live evaluation task. Revisit
further optimization only from the matched evidence, not an empty queue or agent
utilization. See the audit for canonical IDs, parallel lanes and actual planning
validation.
