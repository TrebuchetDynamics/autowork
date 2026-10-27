# pi-toolset specialists inside Autowork

Read the [common contract](COMMON-CONTRACT.md) and apply the
[shared Ponytail method](PONYTAIL.md). The selected specialist and this adapter
contract take precedence over lifecycle, tool and delivery instructions in its
pinned upstream protocol and references. Upstream files remain byte-exact;
`UPSTREAM.json` in each specialist records the source revision, paths and hashes.

## Authority and task state

These are explicit, current-session workflows, not an installed controller or
background service. Invocation permits the selected local workflow within the
user's scope; merely reading a supporting protocol adds no authority. Reuse
existing authorization and decisions. Ask only for genuinely missing product,
risk or external-action authority, not routine reversible implementation details.
Questions-only, read-only and no-write requests change nothing, including task
records or reports. Audit/discovery is not permission to implement.

Use the existing [task store](TODO-WORKCENTER.md) for accepted scope, dependencies,
checks and progress; use `autowork tasks` for record changes. Do not create another
backlog, state database, goal extension or minimum-work quota. If that CLI is not
available, inspect existing records read-only and report the missing capability;
do not hand-edit the store or fabricate closure. Follow Autowork's existing
execution/review path, not upstream service-start examples.

Explicit slice, file, time, context, token and spend limits, and user pause/stop,
override upstream continuous-loop and minimum-three-slices language, and any
conflicting continuation advice in supporting engineering references. Do not
replenish limits or start a new session to bypass them. Report a reached limit as
a checkpoint with remaining work, never as completion of the whole objective.
Do not launch new work after pause/stop or promise progress after the session ends.

## Host and technique translation

Use the current host's exposed file, shell, search and delegation capabilities;
Hermes, Pi, Codex and Claude Code do not need another host installed. No pi-toolset
package, extension, hooks, shell controller or scanner is installed by these skills.
Upstream names describe capabilities, not tools granted by the protocol:

- `diagnose`, `systematic-debugging` and `tdd` map to the bundled
  [engineering methods](../engineering/SKILL.md) for debugging and test-first
  regression protection. Respect the existing [test budget](ENGINEERING-CYCLE.md#test-budget).
- `folder_refactor_scan/state/audit` and Understand graphs are optional. Use native
  tree/reference inspection and the existing task receipt instead; never invent
  tool calls or generate a map just to satisfy a dependency.
- Neighboring skills are optional handoffs only when available and relevant.
  `lgtm` resumes only the actual latest approved action; it grants no new scope.
- pi-subagents examples are not portable API requirements. Use discovered native
  roles when available. Without delegation, in-session execution is permitted only
  if repository policy allows it and required independent review can still be
  obtained. If required review is unavailable, keep discovery read-only; do not
  start implementation, self-approve, or silently waive the gate.

Keep one writer per checkout. Ordinary children receive one bounded task, never
the autonomous campaign controller. Before delegating or editing capture the
owned slice's recoverable starting state, including existing uncommitted work.
Timeout, cancellation or an error is not proof a writer stopped. Account for
in-flight tools, reconcile the actual delta, and establish quiescence before a
replacement writer, mutating tests or recovery. Restore only attributable changes
still matching the last observed state; never reset/clean a tree or overwrite a
concurrent edit. Stop with exact ownership uncertainty when safe recovery cannot
be proved.

## Evidence and delivery

Keep baseline, actual change, focused checks, required review and acceptance
separate. Use fresh independent review where required and resolve findings before
acceptance. Record applied methods in the existing task receipt, not just names
of loaded skills. A local commit, merge, push, deployment and live qualification
are separate outcomes requiring their corresponding authority. No implicit push,
broad upgrades, production access, paid services or global configuration changes.

The upstream evaluation receipt describes upstream observations only. Offline
packaging tests and read-only decision probes do not establish live campaign
reliability, model adherence or improvement over existing Autowork workflows.
