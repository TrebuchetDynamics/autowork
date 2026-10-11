# First use: choose a profile, then a project

For an existing Hermes profile, the native plugin manager avoids maintaining a
source checkout. Replace `work` with your actual profile; omit `-p work` for default:

```sh
hermes -p work plugins install TrebuchetDynamics/hermes-toolset
hermes -p work plugins enable hermes-toolset
hermes -p work toolset doctor --core
```

This path affects the selected profile. Loading the plugin still applies its
[runtime policy](installation.md); it is not a policy-preserving trial. The
manifest declares dependencies and native installation does not perform the full
external stack's setup. Explicit fleet setup remains separate.

## Understand readiness

`doctor --core` checks this plugin loaded successfully and owns registrations for
its bundled skills and commands. It returns zero when those checks pass, even if
external plugins, imported skills or skill sources are unavailable. Those gaps
remain visible. A missing core skill or a command owned only by another plugin
fails the check.

Plain `hermes toolset doctor` checks the full stack and exits nonzero for external
gaps too. Both modes use one inventory snapshot; `--json` adds machine-readable
`scope`, `status`, `core_status`, `core_errors`, `integrations_status` and
`integration_gaps` alongside the existing inventory fields. Neither mode proves
model execution, worker availability, live delivery or workflow-specific tools.
Plugin discovery can apply its configured runtime defaults; diagnostics are not
a way to bypass that load behavior.

## CLI smoke check

Leave the Toolset source checkout and start Hermes in the intended repository:

```sh
cd /path/to/your-project
hermes -p work
```

In that chat:

```text
/toolset list
/repo-interview questions only: help me clarify a caching improvement; ask one question, then stop
```

Success means a relevant question arrives without file changes. Check the project's
Git status/diff against its pre-test state. This checks conversational invocation,
not documentation generation or autonomous implementation. Missing provider/tool
errors are failures to resolve, not reasons to report a successful workflow.

## Telegram smoke check

Configure the Telegram bot and intended profile using normal Hermes setup first.
Bind that profile's starting directory explicitly:

```sh
hermes -p work config set terminal.cwd /absolute/path/to/your-project
hermes -p work config get terminal.cwd
hermes -p work gateway status
```

Apply config/session changes through your normal gateway service procedure after
ongoing work is accounted for. Do not assume an already-running session picked up
the changed directory. In the intended bot chat, request a read-only terminal `pwd`
and inspect its actual tool result, then invoke `/toolset list` and the same
questions-only command as `/repo_interview`. Confirm the reply arrives in that
chat and that no project files changed. A registered command or successful CLI
probe does not establish Telegram delivery.

A profile selects state/configuration, not a filesystem sandbox. On the local
backend the agent retains your user account's filesystem access. An asserted
working directory is not confinement. See Hermes' [profile and workspace guidance](https://hermes-agent.nousresearch.com/docs/user-guide/profiles).

## Optional: see decisions become a task

Use a new disposable Git repository with no real product data, configured model
and the file/terminal capabilities needed by the workflow. Check full diagnostics
and the relevant skill prerequisites first; command registration alone is not
readiness for this exercise. In its CLI chat, try:

```text
/repo-interview Plan a tiny CLI that counts nonempty lines in a text file. Ask me the missing requirements, then save my accepted answers and one bounded implementation task. Do not implement, commit or push.
```

Answer the interview. Expected evidence: the existing/new design owner records
your actual accepted decisions; TODO.md contains a bounded task with acceptance
checks and dependencies; goals.json agrees with that task. The final response
names changed paths, task ID and the real backlog readiness state. Inspect the
files and diff yourself. A question or an unexecuted proposal is not completion
of this second milestone. Explicitly authorize a separate `/autogoal` run only
when you want implementation and its required supporting capabilities are ready.

These are operator-run live checks, not recorded model or Telegram test results.

## Update or remove

For a native Git install, use `hermes -p work plugins update hermes-toolset`, obey
any native request to stop the gateway, then reload/restart through your normal
service procedure and reopen CLI sessions. Recheck `doctor --core` and first use.

For a source install, the profile plugin links to your checkout. Keep its path
stable; moving or deleting it breaks those links. Review local edits before
updating that checkout. Re-run the appropriate setup only when you intend its
fleet configuration effects; updating code is not permission to reset policies.
Copied native skill files can be preserved by the installer, so inspect existing
copies when updating a skill rather than assuming every copy was overwritten.

See [removal and recovery](uninstall.md) for disabling/removing the plugin and
restoring configuration. Removal alone does not undo prior setup writes.
