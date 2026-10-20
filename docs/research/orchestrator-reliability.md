# Orchestrator reliability and plan quality

Status: research, 2026-10-19. Companion to
[multi-agent orchestration](multi-agent-orchestration.md). It asks why the Pi
Autowork runner keeps needing fixes, what comparable systems and the literature do
instead, and what the planning skills can do so that fewer bugs and conflicts are
created to begin with. Implemented results are listed at the end; the remaining
changes are tasks in [TODO.md](../../TODO.md).

Method: a classification of this repository's `fix(...)` history; an audit of the
planning skills against the parsers that consume their output; ResearchForge
(`rforge`, standard depth) searches on three topics (multi-agent failures,
testing stateful orchestration, LLM task planning: 1,499 unique records, Semantic
Scholar rate-limited, no topic saturated; the raw search directory is kept outside
this repository); and a review of the official documentation of the tools below.

## What the history says

203 `fix(...)` commits touched the runner or the engine scripts in thirteen days
(counts ±3, each commit counted once):

| Class | Fixes | Fix-of-a-fix chain (example) |
|---|---|---|
| Planning ledger, `Touches:` and schema drift | 33 | task closing: 263b174 → 3817f75 → b11971e → 5b99722 → af49a0b → e8a987b |
| Merge, conflict and landing | 30 | conflict holds: 74a7136 → 04aec01 → 8e5268b → d076676 → c426bf7 |
| Main checkout, dirty files, locks, writers | 30 | nine fixes from 508919a to 2efdafb |
| Process lifecycle: timeouts, kill, reload, release | 29 | reload: f4a7d11 → … → 89ac909 (eight) |
| Hold, retry and queue state | ~25 | dbc0ba0 → 74a7136 → 8e5268b |
| Worker environment: temporary directory, disk, ports | 22 | eight fixes for the temporary directory alone |
| Review and check verdicts | ~12 | 08599b4 → a9d5149 → c386628 → 1c0fe5f |
| Status that disagrees with reality | ~10 | still open as TOOLSET-200-c1, 235-0d |

Two regressions reached main as conflict markers committed into Python modules
(b69b2d2 into `coordinator.py`; 34b7f31 into `parallel_dispatch.py`, after which
every engine call failed). Nothing refused a tree that did not parse.

Hot files: `coordinator.py` (89 commits, 59 fixes; one 2,644-line class with about
50 mutable attributes), `parallel_integrate.py` (74/55), `tests/test_pi_autowork.py`
(2,980 lines, 47 fixes), `parallel_dispatch.py` (50/34). Run
`python3 scripts/fix_hotspots.py` for the current table.

Root causes, most damaging first:

1. **Many writers to main and its checkout.** The quiet-edit sweep, autostash, hand
   landings and `land_around_edits` all write there; this produced the session fixes,
   GitHub #3 and both marker incidents.
2. **One `held` state carries about ten causes**, and recovery in `retry_held`
   partly reads the human-readable reason string.
3. **Failures read as "empty" or "clean".** A failed `git status` returns `''`; a
   failed status read looked like "nothing running".
4. **State in about thirty files with no journal of intent**, so a crash or reload
   between two writes leaves them disagreeing (TOOLSET-119-2b).
5. **The model does mechanical Git work** (session merges, planning-file
   normalization; GitHub #7).
6. **Shared hot files plus parallel dispatch.** 476 of 595 pairs of open Now tasks
   share a file; `coordinator.py` and `tests/test_pi_autowork.py` are each named by
   about 38 tasks. Since `Touches:` became a ranking hint (TOOLSET-161-17), the plan is
   the only place that keeps write sets apart, and the planning skills still described
   the old holding rule.
7. **Slow, timing-dependent tests**: a 22-minute full check, 77 `sleep` calls and 84
   wall-clock assertions in one module; the recorded red main was exactly these.

## What comparable systems do

No leading system lets an agent integrate. Claude Code, Codex cloud, Cursor
background agents and Devin produce a branch per task; integration is a person or a
merge queue. Merge queues (bors' "not rocket science" rule, Zuul dependent pipelines,
GitHub merge queue) share one rule: a single deterministic integrator tests the exact
tree that will land, in queue order, and evicts a failing entry.

| Practice | Source | Applied here |
|---|---|---|
| Merge without a working copy; move refs by compare-and-swap | [git merge-tree](https://git-scm.com/docs/git-merge-tree), [git update-ref](https://git-scm.com/docs/git-update-ref) | TOOLSET-230-bf |
| Single serial integrator with speculative trials | [Zuul gating](https://zuul-ci.org/docs/zuul/latest/gating.html), [GitHub merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) | TOOLSET-231-49 |
| Level-triggered reconciliation: compute status from observed state | [Kubernetes controllers](https://kubernetes.io/docs/concepts/architecture/controller/) | TOOLSET-200-c1, 235-0d |
| Intent journal, idempotent steps keyed by task and step | [Temporal workflows](https://docs.temporal.io/workflows); Where Does Exactly-Once Live? ([arXiv 2609.29095](https://arxiv.org/abs/2609.29095)): idempotency keys cut duplicate writes from 28% to 4% | TOOLSET-119-2b |
| Crash-only design, process groups, timeouts on every child | [Crash-only software](https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea.pdf) | existing `killpg` paths |
| Model-based state-machine tests; seeded simulation with fault injection | [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html), [FoundationDB testing](https://apple.github.io/foundationdb/testing.html), [TigerBeetle VOPR](https://docs.tigerbeetle.com/about/vopr) | stdlib random walk (below) |
| Every error branch tested | Simple Testing Can Prevent Most Critical Failures (OSDI 2014) | follow-up tasks |
| Retry budgets with jitter; pause during correlated outages | Retry Amplification ([arXiv 2608.25403](https://arxiv.org/abs/2608.25403)): naive retries lowered success from 55% to 42% | existing failure pause |

Evidence about agents themselves:

- MAST ([arXiv 2503.13657](https://arxiv.org/abs/2503.13657)): task verification is
  one of three failure classes in multi-agent systems; "done" must be a mechanical
  check the orchestrator owns.
- LLMs cannot self-correct reasoning without outside feedback
  ([arXiv 2310.01798](https://arxiv.org/abs/2310.01798)); LLM errors are correlated,
  so an LLM reviewer is not an independent check ([10.1145/3847307](https://doi.org/10.1145/3847307)).
  Keep automated gates first; the reviewer never overrides a failing gate.
- 20–30% of patches that pass the tests are still wrong
  ([10.1145/3744916.3764576](https://doi.org/10.1145/3744916.3764576)): passing tests is
  necessary, not sufficient.
- Agent PRs conflict often: 42% of replayed merges between different agents' PRs
  against 20% within one agent ([arXiv 2607.04697](https://arxiv.org/abs/2607.04697)).
  Disjoint scopes decided before dispatch cut conflicts to zero in NP-Bench
  ([arXiv 2610.07261](https://arxiv.org/abs/2610.07261)).

## What makes a plan produce fewer bugs

- **Executable acceptance written first.** Test-driven generation and AgentCoder
  ([10.1145/3691620.3695527](https://doi.org/10.1145/3691620.3695527),
  [arXiv 2312.13010](https://arxiv.org/abs/2312.13010)) gain from tests written before
  the code, ideally by another role. Only 1 of 90 open tasks named a test in
  `Acceptance:`.
- **Explicit constraints.** Fewer than half of "resolved" issues met their design
  constraints ([arXiv 2604.05955](https://arxiv.org/abs/2604.05955)): plans name
  invariants and the reviewer checks them.
- **Name target functions, not only files**
  ([arXiv 2604.00167](https://arxiv.org/abs/2604.00167)).
- **Dependency-ordered, disjoint tasks** (CodePlan,
  [arXiv 2309.12499](https://arxiv.org/abs/2309.12499); NP-Bench above).
- **A pre-mortem**: name the likely regressions before saving and give each a guard
  test.

Some takeaways for the stateful-testing papers come from titles and metadata only;
check them against the full text before relying on a specific number.

## Implemented with this research

- Planning skills: corrected the `Touches:` rule; added sizing, disjoint write sets,
  `Produces:`/`Consumes:` interfaces, executable acceptance, a pre-mortem and a stronger
  builder check ([planning craft](../../skills/shared/PLANNING-CRAFT.md)).
- `goals.py plan-lint`: a deterministic lint of saved tasks (required fields, unknown
  or cyclic dependencies, `Checks:` that name missing tests, coordinator files in
  `Touches:`, overlapping write sets, hot files, oversize tasks).
- `scripts/tree_guard.py`: refuses conflict markers, Python that does not compile
  and JSON that does not parse; the first step of `scripts/check.py`, and usable on a
  candidate commit (`--rev`) without a checkout.
- `scripts/fix_hotspots.py`: fix-of-a-fix hotspots from Git history.
- A model-based random-walk test of the worker slot state machine
  (`test_parallel_state_model.py`). It found three defects, now fixed: `reconcile`
  aborted for every slot when one worker's HEAD shared no history with its baseline;
  that diverged hold recorded no `cause` (now `diverged`); and a worker adopted after
  surviving the stop that paused it kept its pause marker, so its later crash was
  resumed instead of held.

Remaining runner changes need files that live workers own (`coordinator.py`,
`parallel_integrate.py`); they are queued as tasks rather than edited around them.
