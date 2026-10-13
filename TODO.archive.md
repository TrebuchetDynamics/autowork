# Completed tasks


<!-- archived from TODO.md -->

Source section: Completed local changes

### TOOLSET-004 — Reduce fragmented Autowork handoffs and misleading zero-progress reports

- Status: done (local implementation and focused contract tests; not a live throughput claim).
- Goal: Complete connected accepted outcomes with fewer redundant preparation/review cycles.
- Sources: [delivery batch contract](skills/autowork/references/delivery-batches.md),
  [worker body generation](skills/autowork/scripts/start_goal.py), [cron prompts](scripts/wire-owner-cron.py).
- Scope delivered: Coherent-batch guidance, worker/cron prompt propagation, portable
  coordinator guidance and delivery-first reporting with truthful parent status.
- Acceptance checked: Generated worker text retains the explicit scope/exclusions,
  directs completion of every admitted consumer, and retains independent review;
  generated cron text includes batching, evidence reuse limits and parent reporting.
- Checks: Worker role contracts (5 tests) and cron prompt tests (15 tests) passed.
- Remaining qualification: Real model batching and reduced elapsed time are unverified;
  TOOLSET-003 still owns live bounded recovery qualification.
- Dependencies: None.
- Owner: Current repository change; no claim on any product worker or schedule.



<!-- archived from TODO.md -->

Source section: Completed local changes

### TOOLSET-005 — Recover registration context across filtered terminal environments

- Status: done (local helper regression; live worker recovery not yet verified).
- Goal: Prevent a missing terminal environment field from holding a correctly registered task.
- Source: [workspace guard](skills/autowork/scripts/pass_workspace.py).
- Scope delivered: Exact original-handoff recovery for registration only; no environment
  forgery, registry mutation, candidate repinning or native ownership bypass.
- Checks: 22 workspace tests pass, including missing, stale, wrong-task, wrong-card
  and conflicting handoffs plus conflicting inherited context.
- Remaining qualification: Existing workers retain their original admitted contracts;
  they need same-card reconciliation before using a changed helper.



<!-- archived from TODO.md -->

Source section: Completed local changes

### TOOLSET-006 — Preserve review progress and direct coordinator closeout

- Status: done (local regression coverage; autonomous model follow-through unverified).
- Goal: Keep new review outcomes visible and direct completed cards to integration checks.
- Source: [reconciliation helper](skills/autowork/scripts/reconcile.py).
- Scope delivered: Report-cache identity includes run and outcome; phase-specific next
  actions distinguish active/queued cards, recovery and terminal closeout.
- Checks: 12 reconciliation tests pass; terminal hints never claim delivery or approval.
- Remaining qualification: A model must execute the advised closeout; the read-only
  helper itself does not merge, dispatch, authenticate liveness or resume jobs.

<!-- End of migrated task history. -->


<!-- archived from TODO.md -->

Source section: Next

- [x] TOOLSET-010 — Bind Telegram reports and setup confirmation independently of invocation
  - Status: done (source instructions, offline contract checks and independent scenario review).
  - Goal: CRON-REPORTING — Resolve Telegram reporting independently of the invoking surface.
  - Sources: User request to report in Telegram from any invocation surface;
    [native workflow](skills/cron-autowork/SKILL.md),
    [portable workflow](adapters/skills/cron-autowork/SKILL.md),
    [workflow documentation](docs/workflows.md).
  - Scope delivered: Explicit profile/chat/topic routing, one setup confirmation,
    nonempty per-occurrence reports, delivery receipt checks and truthful failure reporting.
  - Exclusions: No live profile/job changes, unrequested immediate execution,
    cross-profile messaging, push, deployment or real-device operations.
  - Acceptance checked: Guidance covers CLI and Telegram topic setup, explicit local/quiet
    preferences, existing-job repair, missing transports and queued/ambiguous delivery.
    Setup confirmation remains distinct from scheduled execution and message delivery.
  - Checks: `uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests`
    passed: 246 tests run, two skipped; five cron contract tests passed. Independent
    before/after scenario review approved the source changes. Markdown links and diff checks passed.
  - Remaining qualification: Instructions and fixtures do not prove live agent behavior;
    TOOLSET-011 owns installation and Telegram receipt verification on the affected host.
  - Dependencies: None.
  - Ownership: Current Autowork coordinator for local closeout; no live worker claim.

Closeout repair for TOOLSET-010: task-source links to archive policies and test
code were incorrectly treated as history destinations, blocking this move.
Owner discovery now uses navigation outside task bodies; default/custom-owner
regression cases reproduce the failure and pass after the fix. All 36 archive,
policy and redaction tests passed, with independent preservation review.
Combined closeout validation: `uv run --python 3.12 --no-project
--with-requirements requirements-test.txt python scripts/check.py` passed
(803 tests run, two skipped; eight live/native modules excluded).
Existing open bodies and prior archive bytes were preserved; the completed
entry appears exactly once and a repeated render was byte-stable.
