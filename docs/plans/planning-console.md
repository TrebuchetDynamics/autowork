# Planning and decisions console

## Accepted scope

The owner requested all phases in the conversation: embedded autonomous and interactive planning, task-aware refinement, blocker investigation, roadmap/dependency browsing, persistent per-project history/resume, and explicit review/apply, available through TUI and CLI. This implementation proceeds under that authorization; no new planning-approval ceremony, runner activation, remote push or deployment is implied.

## Design

- A standard-library `Planner` controller owns repository-bound private session metadata and Pi transcripts. Both `autowork plan` and the Textual Plan screen call it. No new daemon. A turn survives screen navigation; closing the app cancels its owned turn, retaining its history and proposal for explicit resume.
- Pi is a JSONL RPC child, not a nested terminal. Command acknowledgements are not completion; `agent_settled`, provider errors, EOF and cancellation determine the result. Known bundled planning skills are discovered through `get_commands`; arbitrary user text is not executed as a slash command. Runtime/model errors are visible, never empty-plan success.
- Planning uses read/search tools only; discovered extensions, MCP, prompt templates and project executable configuration are disabled. The model cannot implement, commit, mutate tasks or launch workers through these tools. It emits complete proposed Markdown file contents in an `autowork-plan` JSON block; the host stages only validated task/goal records and plan/spec Markdown. This is a write-capability restriction, not a filesystem-read sandbox or protection from a compromised Pi executable.
- Each proposal has a worktree under canonical `.worktrees/`, an immutable starting revision, a private session ID and an exact review fingerprint. Proposal files never constitute the live queue. Explicit Apply checks the fingerprint, current target revision, supported file paths, task validity, live writers and dirty conflicts; it makes a scoped local commit and lands through existing guarded Git machinery. No force, reset, automatic rebase, publication or inferred qualification.
- Roadmap displays goals, tasks, states and explicit dependency edges including missing/cyclic references. It is a derived view, not a new task database or an admission/verification claim. Investigate includes the selected task's blocker context but grants no new execution or live authority.
- Direct decisions remain available without a model: `tasks decide ID TEXT [--section Now|Next|Needs decision]` and a TUI Decide form record dated owner direction. They do not infer completion or live authorization.

## Implementation checklist

- [x] Backend: `planning.py`, `planning_rpc.py`, proposal helpers; offline real-Git and fake-RPC tests.
- [x] Shared views and app-owned session controller: bounded events, cancel/steer, navigation-safe state; deterministic tests.
- [x] CLI: `plan` flags for objectives, modes, resume/history/list/roadmap, preview and fingerprinted apply; preserve external-agent invocation with `--legacy`.
- [x] TUI: Plan screen with project/session selection, chat/progress, preview, roadmap, history, task discussion/investigation, explicit apply confirmation, view-only enforcement.
- [x] Direct decision API/CLI/TUI with dated notes and optional section transitions; existing worker guards remain.
- [x] Documentation, independent review and focused offline checks; live model qualification remains separate.

## Verification and remaining qualification

- 38 planning tests passed across `pi-autowork/tests/test_planning{,_rpc,_commands,_hub,_ui}.py`:
  real disposable Git, fake JSONL subprocesses and pinned Textual 8.2.8 pilots at 80/120 columns.
- 121 existing command/planning-contract, attention, fleet, blocker-report, history,
  snapshot and transaction tests passed; 9 landing and 26 task-command tests also passed.
  These are focused checks, not a claim that the entire repository suite passed.
- CLI `plan --help` and `tasks decide --help`, guide links, tree guard and `git diff --check` passed.
- Independent CLI/UI and backend safety reviews found and verified fixes for project
  identity switching, canonical aliases, resume/error handling, live-resource gate
  removal and cancellation at settlement. Bounded follow-ups reported no remaining blockers.
- The conservative affected-test selector expands changed pilot helpers to the entire
  suite. That full run was not repeated for this focused feature. A backend worker's
  broader affected-check attempt timed out; it is not passing evidence.
- Pending: live provider/model behavior, model adherence to the proposal format, and
  deployed terminal/browser qualification. No model/provider call, runner activation,
  remote publication or live acceptance was performed. The feature worktree is retained
  for a separate integration decision; canonical changes were not overwritten.

## Review focus / acceptance

1. Provider failure, EOF before settle, cancelled run, malformed JSON and unsupported skill never produce successful apply authority.
2. Path traversal, symlinks, executable paths, receipt/closure fabrication and new live authorization are refused.
3. Target drift, proposal drift, busy writer, dirty overlap and stale fingerprint preserve all original bytes and leave the proposal available.
4. Switching screens/projects, double clicking Send/Apply, closing during a turn and resuming after process restart do not create duplicate writers or publish into the wrong project.
5. An 80-column TUI retains chat entry and controls; keyboard and mouse controls share handlers; view-only never launches a model or writes a decision.
6. Tests use disposable repositories and fake RPC, with no paid model call, live service changes or remote publication. Offline coverage does not qualify the installed provider or model's adherence to the proposal format.
