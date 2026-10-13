---
name: plan-for-me
description: "Investigate the repository, decide an approach and save plans and tasks. Includes on-demand Autoresearch experiment protocols; not required for a ready implementation task."
version: 0.1.0
license: MIT
---

# Plan For Me

Default to the plan protocol when invoked as a skill without an explicit subcommand.
Explicit Autoresearch subcommands select their own protocol.

Run the pinned Udit Goenka autoresearch protocols with Hermes tools and the existing
docs-sync → TODO.md/goals.json → autowork cycle. Read this adapter first, then the
selected upstream protocol. For `plan`, also apply the
[planning adaptations](../shared/RESEARCH-PLAN.md) before following upstream phases.
These integration rules govern host/tool substitutions,
repository ownership and handoff; preserve upstream research methods and flags.

When called by Autowork, investigate the named uncertainty and return to its
current task. Do not assume coordination of the repository, reopen settled plans,
or start another worker/scheduler. Explicit subcommands retain their documented
behavior within the user's scope. An empty queue with an obvious repair needs no
research protocol.

## Default output: update the work queue

Apply [TODO work center](../shared/TODO-WORKCENTER.md) before planning and closeout.
Every command saves in-scope actionable findings to TODO.md by default and keeps
its goals.json execution index synchronized. No extra “save” instruction is needed.
Planning-only permits documentation/backlog writes, not product implementation;
explicit read-only, chat-only, no-write and --dry-run requests write nothing.
Report saved paths, task IDs and the next executable action. Reuse existing plans
and tasks; preserve user orders before rendering and never claim planning as delivery.

## Planning and protocol selection

`/plan_for_me` (also `/plan-for-me`) is the primary planning command. It routes
to this adapter's `plan` protocol: investigate the repository, choose a supported
approach, and save the plan and tasks. Decide routine engineering choices without
an interview; ask only for consequential missing product intent or authority.
`/autoresearch:plan` and `/autoresearch_plan` remain compatibility aliases. Other
Autoresearch commands keep their existing behavior and names.

## Commands and dispatch

`/autoresearch` is the upstream router. `/autoresearch:<command>` is the original
CLI spelling; `/autoresearch_<command>` is the Telegram spelling. Hyphen aliases
also work in CLI. All spellings load this same skill, not separate research state.

Supported commands: `plan`, `debug`, `fix`, `security`, `ship`, `probe`, `scenario`,
`predict`, `reason`, `learn`, `improve`, `evals`, `regression`.

1. An injected `Selected subcommand: NAME` selects `upstream/NAME.md`. Otherwise
   accept `/autoresearch NAME ...` when the first token is a listed command.
   Preserve the remaining arguments, including `Goal:`, `Scope:`, `Metric:`,
   `Direction:`, `Verify:`, `Guard:`, `Iterations:`, and upstream flags.
2. Explicit bare `/autoresearch` loads [upstream router](upstream/ROUTER.md): explicit metric or
   verify uses [classic loop](upstream/autoresearch.md); a natural-language goal
   uses its orchestrator; no goal uses setup. Honor `--classic` and `--auto`.
3. Load only the selected protocol and references it requires. In upstream files,
   resolve `scripts/` and `references/` under this skill's **upstream/** directory.
   Use `bash "<skill-dir>/upstream/scripts/orchestrate.sh" ...` and the bundled
   `score-regression.sh`; shell paths must be quoted. Scripts classify/score state;
   they do not run an autonomous agent for you.
4. `--chain` targets reuse this adapter for each named command and preserve the
   current repository, authorized scope and remaining budget. Unknown targets are
   an error; never interpret them as arbitrary shell commands or skill paths.

`$autoresearch`, `/autoresearch:*` and upstream “invoke” instructions mean load
that protocol and perform it in the current Hermes conversation. Map upstream
`request_user_input`/`AskUserQuestion` to the available clarification tool or a
direct chat question. Map execution, file operations and delegates to actual Hermes
tools. No Claude hooks, Codex-only tools, plugin install or second harness is needed.
Personas are analytical viewpoints; call them independent agents only when separate
agents actually ran. Record unavailable tools/checks honestly.

## First: bind research to the repository

Load [engineering cycle](../shared/ENGINEERING-CYCLE.md). Inspect project rules,
accepted intent, current docs, canonical goals/TODO, active task ownership, dirty
changes and existing research receipts. Resolve canonical authority with docs-sync;
an experiment worktree's copied backlog is not canonical. Reuse the current task
and requirement IDs. Research logs, TSV and upstream `handoff.json` remain evidence,
not a second backlog or proof of completion. Use a unique per-run output directory
under the existing research owner (avoid minute-timestamp collisions).

The selected Autoresearch protocol is normally sufficient. Consult an Addy
protocol only for a concrete method gap or explicit request; do not add a phase
sequence or separate review/versioning workflow to an analysis-only command.
Record the decision/artifact/check each selected skill changed. `plan-with-me`
or `grill-me` handles genuinely missing owner intent; routine reversible choices
are autonomous. Existing accepted scope is enough: do not repeat upstream's generic
“confirm”/“run now?” questions when the user already authorized that action.

When invoked by autowork for backlog recovery, follow its
[bounded planning fallback](../autowork/references/backlog-planning.md): accepted
scope only, up to three useful slices, canonical reconciliation, same-occurrence
selection and a persisted input-bound receipt. Do not launch a recurring research
loop or ask again for settled implementation choices.

## Document and schedule through docs-sync

Apply the [single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
Persist new actionable findings at a bounded checkpoint; unchanged checkpoints
reuse their existing receipt and do not trigger another documentation pass.
A new investigation result does not automatically require a docs edit: if the
existing task and docs already preserve its material reasoning/evidence and scope,
acceptance, sources and dependencies remain correct, return the decision/evidence to the same Autowork
coordinator without invoking Docs Sync. Keep any needed execution receipt in the
existing task journal. When documentation or backlog actually needs a change, load
`hermes-toolset:docs-sync` (or the verified sibling SKILL.md) in **narrow Maintain**
for affected owners; do not start a whole-repository bootstrap implicitly.

1. Supply a compact finding receipt: command/run path, accepted requirement/source,
   task ID if any, exact observed evidence, scope, baseline/target/units, Verify and
   Guard commands with actual results, recommendation, residual gap and dependencies.
   Failed/unrun checks stay failed/unverified; a prediction is not an observed bug.
2. Update existing spec/ADR/test-plan/runbook owners with supported findings. Reuse
   matching goals and tasks before creating anything. Preserve active leases,
   ownership, focus, completed history and unrelated edits. An in-progress cache
   benchmark remains that same task, not a second “research cache” task.
3. For accepted unmet work, have docs-sync reconcile canonical `goals.json` and
   full **TODO.md** bodies: Goal/payoff, Sources (research receipt plus graph/source
   evidence), bounded Scope/exclusions, measurable Acceptance/checks,
   `Dependencies:` and `Ownership:`. Order **Now/Next** with actual ledger priority
   and dependencies. Use one discriminating investigation only for a blocking
   unknown; produce implementation plus verification slices for known gaps.
   Keep speculative product ideas Proposed/Needs decision unless the user's
   request already supplies acceptance. No invented approval or priority changes.
4. After the final changed batch, run docs-sync `goals.py fmt`, `validate`, `render` and consumer `backlog-check`
   against the actual canonical repository and accepted source heading. Repair
   supported missing metadata; never fabricate `Status: Accepted`. Report the
   exact state/exit, touched task IDs and eligible next slice. Repeat reconciliation
   of unchanged evidence must preserve IDs and bytes, not duplicate tasks.
5. This is **backlog scheduling**: documenting and ordering tasks in TODO.md.
   It does not mean installing a cron job or claiming an autowork task. If the user
   also authorized implementation, pass the current ready receipt to `autowork`;
   reuse an existing worker instead of spawning a competing worker for its task.
   A request for periodic execution uses autowork's native schedule workflow with
   the user's cadence/profile/repository; never invent or duplicate a timer.

`plan`, `probe`, `predict`, `reason`, `scenario`, `learn`, `improve`, `evals` and
`security` do not silently turn recommendations into product-code changes. Use the
selected protocol's analysis scope and persist accepted follow-ups through the
handoff. Explicit audit/read-only requests write nothing, even research logs or
TODO; return proposed updates inline. `--dry-run` performs no mutations or dispatch
and must not run a mutating Verify command. “Do not implement” remains binding
despite `--chain fix`, upstream “execute immediately”, or an accepted backlog.

## Execution, experiments and completion

Use upstream bounded iteration/cycle limits and stop on plateau/ceiling/blockers;
explicit unlimited work still checkpoints and stops on user interruption. No hidden
background loop. Pin the metric/predicate, record baseline and check the same signal
after each change; do not relax acceptance to obtain a win. Re-screen persisted
commands before resume per upstream. Screening is a coarse check, not a security
boundary or approval substitute; inspect commands and follow actual task authority.

Experiment commits/reverts belong in an isolated owned worktree/branch. Do not
stage all files or revert a shared HEAD. Record an experiment's exact SHA and only
revert that owned experiment there. Where worktree use is prohibited, use a private
snapshot for experiments and transplant only verified owned changes; record snapshot
identity rather than pretending an experiment commit exists. Preserve dirty user work.
Honor no-commit instructions. For autowork work, its `finish_task.py` validation and
owned-file commit gate remain authoritative; upstream experiment commits do not
replace the accepted-task commit, review or canonical completion evidence.

`ship` follows the upstream readiness protocol within existing authority. Push,
deploy, publication and external messages need the actual user-authorized scope;
research success or command chaining alone provides none. Carry prior authorization
without reasking. Do not close canonical tasks just because an upstream handoff
says COMPLETE: use docs-sync evidence and autowork's normal closure gates.

Finish with: result/stop reason; metric/check evidence; changed document owners;
TODO/goals task IDs and Now/Next; consumer readiness or blocker; committed SHA when
applicable; and whether execution/timed scheduling actually occurred.

## Vendoring

[UPSTREAM.json](UPSTREAM.json) pins source revision, commands and file hashes.
[MIT license](upstream/LICENSE) preserves upstream attribution. `upstream/ROUTER.md`
is the upstream SKILL.md renamed to prevent duplicate native skill discovery;
all upstream contents are otherwise byte-identical. Update this pinned subtree
deliberately, review command/runtime changes, then rerun distribution/dispatch tests.
