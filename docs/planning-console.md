# Planning and decisions in the TUI and CLI

Sources of truth: [CLI](../Src/pi_autowork/planning_commands.py),
[controller](../Src/pi_autowork/planning.py),
[RPC transport](../Src/pi_autowork/planning_rpc.py),
[proposal validation/Apply](../Src/pi_autowork/planning_proposals.py),
[TUI](../Src/pi_autowork/planning_ui.py) and
[task decisions](../Src/pi_autowork/task_commands.py) (`cmd_decide`).
Update this page when those contracts, launch flags or safety guards change.

The planning console is separate from execution. It uses a Pi RPC subprocess for
conversation, read-only investigation and proposed task/spec changes. It needs a
configured **Pi 1.3 or newer** with the documented RPC commands/events; there is no
Python SDK dependency. The separate [worker/reviewer execution adapter](pi-rpc.md)
uses the pinned Python SDK; this console does not replace that runtime.
An execution service may be paused, stopped, absent or
working on the same repository. Opening the console does not start a model;
**Send** does. Opening a project can create private session-storage directories.

## TUI

- **g Plan** from the fleet opens the selected project's workspace, even for an
  unprepared project. With no runner, it starts at the current directory; enter
  another Git repository path and press **Load**. The directory browser also has
  **g Plan**, independent of Play/Prepare.
- From a task list/detail, **g Discuss** scopes the new conversation to that task;
  **v Investigate** asks for source-backed blocker investigation. Neither grants
  execution/live authority. Closed history may be discussed, but not reopened by
  the planner.
- Choose **Plan**, **Discuss**, or **Investigate**, optionally enter a task ID,
  then write an objective and press **Send** (Ctrl+Enter). A blank objective for a
  new Plan session starts autonomous discovery. Resumed sessions keep their mode
  and task; use New to start with a different scope.
- Chat streams text and tool progress. **Steer** queues your current input during
  an active turn; acknowledgement is not proof it has been acted on. **Cancel**
  (Ctrl+X) requests cancellation and waits for child cleanup.
- **Proposal** contains the exact diff, validation errors and review fingerprint.
  **Review** (F2) refreshes it after a turn; **Apply** asks confirmation for that
  fingerprint. **Roadmap** renders goals, tasks, dependency edges and ordering
  waves, marking missing references/cycles. It is not an execution-admission or
  verification claim. **History** shows saved conversation (refreshed on session
  selection and Review).
- Select another saved session to resume it, or change project with Load. Back
  preserves an active turn in the app. Closing the app cancels owned turns and
  keeps their transcripts/proposals for explicit resume. It starts no daemon.
- View-only mode does not offer planning or decision mutations. Terminal/browser
  controls use the same controller and permission checks.

## CLI

Run from any directory; the target is a repository path or configured runner name.
The controller resolves linked worktrees/subdirectories to the canonical project.
All examples use placeholders, not existing session IDs or live run receipts.

```sh
autowork plan /path/to/repo --objective 'Find the highest-value reliability work'
autowork plan /path/to/repo                 # bare autonomous discovery
autowork plan /path/to/repo --mode discuss --task TASK-1 --objective 'Reduce this scope'
autowork plan /path/to/repo --mode investigate --task TASK-1 --objective 'Explain its blocker'
autowork plan /path/to/repo --list
autowork plan /path/to/repo --session SESSION_ID --interactive
autowork plan /path/to/repo --session SESSION_ID --message 'Prefer the smaller design'
autowork plan /path/to/repo --session SESSION_ID --history
autowork plan /path/to/repo --roadmap
autowork plan /path/to/repo --session SESSION_ID --preview
autowork plan /path/to/repo --session SESSION_ID --apply REVIEW_REVISION
```

`--json` prints one machine-readable result; streaming progress uses stderr.
`--model provider/model` chooses a model for a new session; saved sessions retain
its model. `AUTOWORK_PI` selects the Pi executable. Interactive chat recognizes
`/preview`, `/roadmap`, `/history`, `/apply REV`, `/cancel`, `/steer TEXT`, and `/quit`.
While a turn is running, ordinary text steers it; otherwise it starts a follow-up.
Other input is literal conversation, not a shell or Pi command. Ctrl+C cancels the current turn; quit
retains the session. With `--session` and no message, a noninteractive invocation
shows history without making another model call. Listing, history, roadmap,
preview and apply do not invoke a model.

`autowork plan --legacy [target]` explicitly retains the earlier external-agent
workflow (`AUTOWORK_AGENT`, else Claude/Pi), with its original permissions and
owner-time accounting. It is **not** the restricted proposal workflow described
here; it can write the target checkout through that agent. Nothing silently falls
back to it when RPC planning fails.

## Record a decision without AI

From the fleet screen, select a runner and press **e Answer** (also shown in the
menu when an editable task question exists). One question opens directly; several
open a picker navigated with **↑/↓**, **Enter**, and **Esc**. Questions about missing
or closed records remain read-only in **b Blockers**, not new editable tasks.

From an open task list/detail, **e Decide** opens the same editor. It shows the
question, the runner's suggested answer, dependent task IDs from the committed
snapshot, and the current working record's scope, section, ownership and live
permission. A suggestion is context only: it is never filled in as your answer.
The context pane scrolls independently and identifies its snapshot/working-record
sources.

Type an answer, choose **Save answer — keep section**, **Move to Next**, **Defer —
Needs decision**, or **Move to Now**, then press **Ctrl+Enter** or **Save answer**.
**Esc** cancels before saving. During a save the editor is locked against duplicate
submissions or new edits; wait for its result rather than treating it as cancelled.
The record loads off the UI thread and Save stays disabled until a current open
record is available. A concurrent task edit causes a revision-guarded refusal and
keeps your answer draft; copy it and reopen to review the latest record before retrying.

Success explicitly reports **Saved locally — pending commit**. The action does not
commit, restart the runner or grant authorization; committed inventory updates only
after a later commit (including any separately authorized coordinator sweep).
For an owner-owned task, or one requiring the `live` resource without authorization,
an answer or section change alone cannot make it executable. Moving an ordinary
worker-owned, non-live task to Next/Now can make it eligible after commit, subject
to its other admission gates. CLI equivalent:

```sh
autowork tasks decide TASK-1 'Use the smaller design' /path/to/repo
autowork tasks decide TASK-1 'Input supplied; proceed' /path/to/repo --section Next
autowork tasks decide TASK-1 'Wait for the hardware' /path/to/repo --section 'Needs decision'
```

This records a dated `Owner decision:` note through the task-store transaction.
`--expect REVISION` is available for stale-write protection. The decision does not
mark acceptance verified, close the task, remove a hold, change live authorization,
or automatically commit. Section changes retain existing live-worker contract
guards. Committed inventory remains unchanged until the decision edit is committed.
A quick-hold fingerprint still requires its specific Blocker resolution; recording
an unrelated decision must not falsely clear it.

## Proposal and Apply safety

Sessions/transcripts are private (0700 directories, 0600 files) beneath the planning
controller's state root, keyed by canonical repository identity and session ID.
Proposals live in `.worktrees/planning-<ID>/` under the canonical checkout; that
directory must already be ignored. The starting revision is pinned. Dirty source
edits are not silently included in the proposal snapshot.

The planner can use read/grep/find/ls only. Discovered extensions, MCP, prompt
templates, project executable configuration and arbitrary command expansion are
disabled; bundled Plan For Me, Plan With Me and Docs Sync guidance are explicitly
loaded and discovered by RPC. Their shell/write/commit steps are not available:
the host stages proposed complete file contents from an `autowork-plan` JSON block.
This is a deliberate proposal-only adaptation, not a claim that the full Docs Sync
CLI ran. Investigate mode reports findings and cannot stage file proposals.

Allowed proposed paths are task/goal Markdown records and Markdown beneath
`docs/plans/` or `docs/specs/`. No code, deletions, receipts, symlinks, executable
files, credential-like content, invented closure/qualification, hold release or new
live authorization may be applied. Proposals are capped at 64 files, 256 KiB/file
and 2 MiB total. Task changes validate against the schema-1 store. These checks
are not a substitute for reviewing the semantic scope and executable check strings.

Apply checks the reviewed fingerprint, current target revision/branch, proposal
content and file types, live execution/interactive writers, Git operation state
and dirty overlapping files. It refuses drift instead of silently rebasing an old
plan. A successful apply creates a scoped **local commit** through normal Git
hooks and guarded landing; it never pushes, starts/restarts a service or unpauses a
runner. An already-running, authorized scheduler can subsequently pick up accepted
runnable tasks. Busy repositories may be planned now and applied when the relevant
writers and unfinished attempts are resolved; stopping a process alone need not
release a retained attempt. Unreadable ownership state fails closed.

Failed/stale/invalid proposals and candidate worktrees are retained. Read the error,
inspect/refine and Review again. A moved canonical base requires a fresh planning
session rather than reusing stale acceptance. No automatic worktree cleanup erases
unmerged proposals.

## Limits and qualification

Read-only tools are **not a filesystem sandbox**: they can read files accessible
to the Pi process. Trusted global provider configuration and credential resolvers
still run normally; do not launch it with production secrets or untrusted global
providers. Use an appropriately restricted account/container for a stronger boundary.
Unsupported RPC extension dialogs stop the turn rather than being silently approved.

Offline tests use disposable Git repositories, fake RPC subprocesses and pinned
Textual pilots. They establish transport/control behavior, proposal validation and
local Git safety; they do not establish live provider availability, model adherence
to the proposal format, token cost, or deployed TUI/browser behavior. No live model
session or running service is exercised by those tests.
