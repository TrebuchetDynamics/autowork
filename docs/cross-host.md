# Codex and Pi installation

Hermes Toolset provides native packages for three hosts. Codex and Pi use the
portable adapters, not the Hermes plugin loader. Neither requires Hermes installed.
These adapters expose 11 skills: the four main workflows, Autoresearch, Engineering,
Impeccable, Grill Me, LGTM, Git Commit Push and Git Pull Merge. Supporting protocols
are bundled and loaded only when needed. Hermes profile creation, Telegram routing,
Kanban workers, fleet setup, memory and speech integrations remain Hermes-only.

## Codex

Requires a Codex CLI with `codex plugin` support. From this checkout:

```sh
codex plugin marketplace add .
codex plugin add hermes-toolset@hermes-toolset-marketplace
```

Install the published Git source with:

```sh
codex plugin marketplace add TrebuchetDynamics/hermes-toolset --ref main
codex plugin add hermes-toolset@hermes-toolset-marketplace
```

Start a new Codex session in your project. Invoke the namespaced native skills:

```text
$hermes-toolset:plan-with-me questions only: ask one question about this project
$hermes-toolset:plan-for-me investigate the next useful improvement; save the plan
$hermes-toolset:docs-sync update the docs and TODO.md
$hermes-toolset:autowork complete the next ready task; commit locally, no push
$hermes-toolset:autoresearch debug the failing test
```

Use `$hermes-toolset:docs-sync` in Codex; the Hermes spelling `/docs_sync`
is not a Codex slash command. Adding package files to a Git repository does not
install that plugin into your Codex configuration. After installation, use the
next turn if the client refreshes skill discovery; otherwise start a new session.

Codex uses skill invocation, not Hermes slash-command registration. The adapters
are explicit-only in Codex so installation does not automatically invoke a workflow.
Use the installed client's plugin marketplace controls to update; remove with
`codex plugin remove hermes-toolset@hermes-toolset-marketplace`. Removal does not
undo repository work or delete plans. A marketplace registration may remain.

## Pi coding agent

Requires Pi with package manifests and extension commands. From this checkout:

```sh
pi install .
```

Install the published Git source with:

```sh
pi install git:github.com/TrebuchetDynamics/hermes-toolset
```

Use `/reload` in an existing Pi session, or start a new one inside your project.
Local installs refer to this checkout; keep it in place. The extension registers:

```text
/plan_with_me questions only: ask one question about this project
/plan_for_me investigate the next useful improvement; save the plan
/docs_sync update the docs and TODO.md
/autowork complete the next ready task; commit locally, no push
/autoresearch_debug diagnose the failing test
```

All 13 `/autoresearch_<protocol>` commands are available. The other commands are
`/autoresearch`, `/engineering`, `/impeccable`, `/grill_me`, `/lgtm`,
`/git_commit_push` and `/git_pull_merge`. Native `/skill:<name>` invocation is also
available; skill names use hyphens. Command arguments remain literal prompt text.
A command entered during an active turn is queued as a follow-up, not injected as
shell code. Existing same-name third-party skills or commands may cause host collision
diagnostics; inspect those rather than assuming this package replaced them.

Use Pi's package controls (`pi list`, `pi update --extensions`, `pi remove <source>`)
for management. Removing the package leaves repository documents and commits intact.

## Behavior and verification

Both adapters ask native questions, inspect files, maintain TODO.md, and execute
through available host tools. Autowork coordinates a useful slice in the current
session; it does not create timers or promise background workers after the session
ends. Existing goals.json is synchronized through bundled helpers when applicable.
Python 3 is needed for those helpers; a questions-only interview needs no Python.

Neither package installs external integrations, modifies approval policies, copies
credentials, or changes model/memory settings. Host permissions and repo instructions
still apply. Installing the package exposes skills, not proof of an executed workflow.
The Gemini/Claude-specific commands in vendored research protocols are adapted to
native tools; the portable host contract wins over foreign runtime instructions.

Offline checks:

```sh
python3 -m pip install -r requirements-test.txt
python3 -m unittest discover -s tests -p test_portable_package.py
node --test tests/portable_pi.test.mjs
```

Validated locally with Codex CLI 0.162.1 and Pi 1.0.2: native marketplace/plugin
and Pi installation into temporary homes, Pi package/extension loading, plus
literal-argument and queued-command tests. These are tested versions, not an
established minimum-version guarantee.
These checks do not prove model output quality, Git delivery or Telegram execution.
The model smoke test is the questions-only invocation above: one useful question,
no repository edits. Follow it with planning and a bounded disposable-repo task
when you want to qualify end-to-end behavior with your configured model.

Host documentation: [Codex plugin schema](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/manifest.rs),
[Pi packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md),
[Pi extensions](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md).
