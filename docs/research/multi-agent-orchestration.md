# Multi-agent orchestration for coding runners

Status: research for the [more parallel workers plan](../plans/2026-10-19-more-parallel-workers.md).
Gathered 2026-10-19 with ResearchForge (`rforge` v0.1.21): `rforge search batch` with eight
queries across OpenAlex, arXiv and Semantic Scholar gave 450 records, 388 after
deduplication, and 6 source failures. Abstracts were read from the arXiv API. The raw
search directory was kept outside this repository; rerun it with the queries below.

Queries: multi-agent LLM software engineering parallel agents; LLM agent orchestration
planner worker hierarchical; parallel tool calling LLM agents task decomposition;
multi-agent coding agents merge conflicts parallel development; swarm of LLM agents
collaborative problem solving; LLM agents best-of-n sampling software engineering
verification; subagent delegation context isolation large language model agents;
speculative parallel execution LLM agents.

## What the evidence says

| Source | Finding | What it means for Autowork |
|---|---|---|
| Verifying Coordination in Parallel Coding Agents: NP-Bench and a Scheduling Planner ([arXiv 2610.07261](https://arxiv.org/abs/2610.07261)) | Partitioning work into disjoint scopes up front and ordering merges along the producer→consumer graph raised clean integration from 1/9 to 9/9 scenarios and cut merge conflicts from 13 to 0. The gap grows with the number of agents. Reactive conflict warnings arrive after the wasted edit. | Autowork's `Touches:` admission and priority-ordered integration are the proactive kind. More workers pay off only if tasks are split into disjoint scopes before dispatch, not by letting several agents edit one area. |
| AgentRoom: Concurrent Multi-Agent Coding in a CRDT-Backed Shared Workspace ([arXiv 2608.23740](https://arxiv.org/abs/2608.23740)) | Two coordinated agents abandon fewer tasks than one, with less run-to-run variation. "Coordination, not parallelism or CRDT-merge, bears the load." | Extra workers on one task need explicit roles and claims, not just two copies racing in one tree. |
| When Sub-Agents Work in Parallel ([arXiv 2610.10263](https://arxiv.org/abs/2610.10263)) | Across 354 tasks and 2,124 runs of Codex, Claude Code and Kimi Code with dynamic sub-agent concurrency on or off: model capability decides short tasks, orchestration decides long-horizon ones. The paper names 13 failure modes specific to concurrency. | Let a worker fan out only on long or separable tasks, and give it a budget. Keep concurrency off for small fixes. |
| Beyond the Model: Demystifying Harness Effects in Software Engineering Agents ([arXiv 2609.32459](https://arxiv.org/abs/2609.32459)) | Of the components tried (tool registry, context compression, explicit planning, subagents, lazy skills), structured tool use and task-specific subagents gave the most stable gains. Complex harnesses help stronger models less on small issue repairs. | Offer workers a narrow, task-specific helper (look something up, triage a failing test, review the diff), not a general swarm. |
| Glite ARF: Verifier-Driven Research with Parallel LLM Coding Agents ([arXiv 2606.27416](https://arxiv.org/abs/2606.27416)) | Up to twelve parallel coding agents ran 273 tracked tasks. Deterministic verifier scripts enforced task isolation and kept completed work immutable. | Autowork's own form: one worktree per task, an engine that verifies, and a full check run on the merged tree. More agents need more of this, not less. |
| AI Agent Pull Requests on GitHub ([arXiv 2607.04697](https://arxiv.org/abs/2607.04697)) | 40% of repositories had co-active agent PR pairs. Replaying 747 three-way merges showed far more textual conflicts between different agents than within one agent's PRs. | Parallel attempts of one task conflict with each other by design: only one of them may land. |
| ProgRouter ([arXiv 2608.25992](https://arxiv.org/abs/2608.25992)) | Choosing a model per workflow step from measured progress keeps quality within cost and time budgets. | A second, parallel attempt can use the fallback model: a different model is a cheap way to make two attempts differ. |

## Measured state of the fleet (2026-10-19, 05:30)

- Host: 22 CPUs, 62 GB of memory with 39 GB available, load average about 24.
- Nine runners: 9 workers running, 119 tasks waiting. Eight runners allow 8 workers each and this
  repository's runner 1, so up to 65 workers.
- What the waiting tasks wait for:
  - This repository: 27 wait "for a free worker slot" (one worker allowed), 21 on
    dependencies, and 17 behind one must-run-alone task.
  - Every other runner: mostly dependencies (between 2 and 9 tasks per runner), plus a few
    must-run-alone and sequential waits.
- Every runner's resource gate refuses another worker once the load average reaches the
  CPU count, whatever the worker would spend its time on. The load average stayed between
  22 and 50 throughout the day.

So the caps on workers are not the limit. Throughput is limited by the plan's shape
(dependency chains), by one runner's worker setting, and by a CPU gate that treats a
model-bound worker like a test run.
