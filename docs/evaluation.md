# Is Autowork worth it?

Autowork has to answer one question: does it build more good software than it costs
in model spend and owner attention? This page records an outside assessment of the
project (2026-10-21) and the evaluation that would answer that question. The
assessment is a subjective engineering opinion supplied by the owner. It is not a
benchmark, and nothing on this page is a measured result.

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
| Accepted tasks completed without intervention | Over 70% | Partly: `autowork scorecard` counts closed tasks and new owner questions; intervention per task is not recorded |
| Regressions introduced by merged work | Under 5% | Not measured: needs a link from later fixes or reverts back to the task that introduced the defect |
| Owner attention per completed task | Falling week over week | Not measured: questions are counted, time spent is not |
| Cost per verified task | Lower than supervising an agent directly | Not measured: model spend is not attributed to tasks |
| Time from task creation to merge | Clearly faster than a baseline | Partly: the scorecard reports the median time from first dispatch to merge; task creation time and a baseline are missing |
| Crash and restart recovery | No lost work, no duplicate closure | Offline fixtures (runner restart, interrupted conversion, replayed close), plus one live run on a disposable repository (2026-10-15, TOOLSET-091-00 in `TODO.archive.md`: a coordinator killed with SIGKILL restarted and adopted its live worker without starting a second one); no record on real repositories |

[`autowork scorecard`](../pi-autowork/README.md#the-autowork-command) already
reports, per runner over 7 days: tasks closed, the share of integrations held,
median dispatch-to-merge time and new owner questions. It is the starting point;
the gaps in the last column are what the evaluation still has to instrument.

The goal is not the number of agents Autowork can run. It is how much good software
gets built while the owner is doing something else.
