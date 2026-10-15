# Claude Code, Codex and Pi installation

Hermes Toolset provides native packages for four hosts. Claude Code, Codex and Pi
use the portable adapters, not the Hermes plugin loader. None requires Hermes installed.
These adapters expose 12 skills: Plan With Me, Plan For Me, Docs Sync, Autowork,
Cron Autowork, Autoresearch, Engineering, Impeccable, UI Taste, Beautify GitHub README,
LGTM and Git Commit Push, which also pulls and merges. Grill Me is Plan With Me's
challenge mode, not a thirteenth skill.
Every adapter is explicit-only: Claude Code and Pi read `disable-model-invocation: true`
in its frontmatter and Codex reads `agents/openai.yaml`, so the model never starts a
workflow on its own.
Supporting protocols are bundled and loaded only when needed. Hermes profile
creation, Telegram routing,
Kanban workers, fleet setup, memory and speech integrations remain Hermes-only.

## Claude Code

Requires Claude Code with plugin marketplaces. From this checkout:

```sh
claude plugin marketplace add .
claude plugin install hermes-toolset@hermes-toolset
```

Install the published Git source with:

```sh
claude plugin marketplace add TrebuchetDynamics/hermes-toolset
claude plugin install hermes-toolset@hermes-toolset
```

Inside a session, `/plugin marketplace add TrebuchetDynamics/hermes-toolset` and
`/plugin install hermes-toolset@hermes-toolset` do the same; run `/reload-plugins` or
start a new session. Add `--scope project` to the install to record it in the
repository's `.claude/settings.json` for everyone who works there. Invoke the
namespaced skills:

```text
/hermes-toolset:plan-with-me questions only: ask one question about this project
/hermes-toolset:plan-with-me challenge this plan; read-only, no implementation
/hermes-toolset:plan-for-me investigate the next useful improvement; save the plan
/hermes-toolset:docs-sync update the docs and TODO.md
/hermes-toolset:autowork complete the next ready task; commit locally, no push
/hermes-toolset:autoresearch debug the failing test
```

The marketplace entry lists `./adapters/skills/` as the plugin's only skills folder,
so the Hermes-only skills in the repository's root `skills/` folder are never loaded;
the plugin itself ships no hooks, agents, MCP servers or settings. Claude Code copies
the whole repository into its plugin cache, so adapter links into `skills/` resolve
there. Update with `claude plugin marketplace update hermes-toolset` and then
`claude plugin update hermes-toolset@hermes-toolset`; remove with
`claude plugin uninstall hermes-toolset@hermes-toolset` (add the same `--scope` used
to install) and `claude plugin marketplace remove hermes-toolset`. Removal does not
undo repository work or delete plans.

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
$hermes-toolset:plan-with-me challenge this plan; read-only, no implementation
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
are explicit-only in Codex (`allow_implicit_invocation: false` in each
`agents/openai.yaml`) so installation does not automatically invoke a workflow.
Update a Git install with `codex plugin marketplace upgrade hermes-toolset-marketplace`
(it refreshes Git marketplace snapshots only); remove with
`codex plugin remove hermes-toolset@hermes-toolset-marketplace`. Removal does not
undo repository work or delete plans. The marketplace registration remains until
`codex plugin marketplace remove hermes-toolset-marketplace`.

## Pi coding agent

Requires Pi with package manifests and extension commands, and Node 22 or later. From
this checkout:

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
/grill_me challenge this plan; questions only, no implementation
/plan_for_me investigate the next useful improvement; save the plan
/docs_sync update the docs and TODO.md
/autowork complete the next ready task; commit locally, no push
/autoresearch_debug diagnose the failing test
```

All 13 `/autoresearch_<protocol>` commands are available. The other commands are
`/cron_autowork` (scheduling guidance through host capabilities, not a Hermes timer),
`/autoresearch`, `/engineering`, `/impeccable`, `/ui_taste`, `/beautify_github_readme`,
`/lgtm` and `/git_commit_push` (`/git_commit_push pull` or `merge <branch>` integrates
upstream changes). Native `/skill:<name>` invocation is also
available; skill names use hyphens. Command arguments remain literal prompt text.
`/grill_me` loads Plan With Me with explicit challenge mode and preserves the
request unchanged. The old standalone `grill-me` skill is no longer discoverable;
use `$hermes-toolset:plan-with-me` in Codex or `/skill:plan-with-me` in Pi with
`challenge` in the request. Autoresearch stays independent; its `plan` selector
routes to Plan For Me, which reads the pinned plan protocol directly, never back
through Autoresearch. All other selectors retain their shipped protocols.
A command entered during an active turn is queued as a follow-up, not injected as
shell code. A same-name third-party skill keeps the first one discovered and Pi
warns; same-name extension commands are all kept but renamed `/name:1`, `/name:2`
without a warning. Check `/` completions rather than assuming this package replaced them.

Use Pi's package controls (`pi list`, `pi update --extensions`, `pi remove <source>`)
for management. Removing the package leaves repository documents and commits intact.

## Behavior and verification

The adapters ask native questions, inspect files, maintain TODO.md, and execute
through available host tools. Autowork coordinates a useful slice in the current
session; it does not create timers or promise background workers after the session
ends. Existing goals.json is synchronized through bundled helpers when applicable.
Python 3 is needed for those helpers; a questions-only interview needs no Python.

No package installs external integrations, modifies approval policies, copies
credentials, or changes model/memory settings. Host permissions and repo instructions
still apply. Installing the package exposes skills, not proof of an executed workflow.
Host-specific commands in vendored research protocols are adapted to
native tools; the portable host contract wins over foreign runtime instructions.

Offline checks:

```sh
python3 -m pip install -r requirements-test.txt
python3 -m unittest discover -s tests -p test_portable_package.py
node --test tests/portable_pi.test.mjs
claude plugin validate . --strict   # needs the Claude Code CLI
```

Validated locally with Claude Code 2.1.300: `claude plugin validate . --strict`
passed, and a marketplace add and install into an isolated configuration directory
listed exactly the 13 adapter skills (no root `skills/` entries, hooks, agents or MCP
servers) with all adapter links resolving in the installed copy. No Claude Code model
session has run a workflow from it yet.

Validated locally with Codex CLI 0.162.1 and Pi 1.2.0: native marketplace/plugin
and Pi installation into isolated temporary homes, Codex app-server skill discovery
and Pi's installed resource loader discovered 11 portable skills and Pi loaded 25
commands, including `/grill_me` compatibility and all 13 research selectors. That run
predates UI Taste, Beautify GitHub README and the Git Pull Merge merge into Git Commit
Push: the package now ships 12 skills and 26 Pi commands, checked offline by `tests/portable_pi.test.mjs`; no live Codex or Pi
install has been rerun. Archive extraction tests check installed references, literal
arguments and queued commands without checkout files. No credentials or configured live accounts are used. These are
tested versions, not an established minimum-version guarantee.
These checks do not prove model output quality, Git delivery or Telegram execution.
The model smoke test is the questions-only invocation above: one useful question,
no repository edits. Follow it with planning and a bounded disposable-repo task
when you want to qualify end-to-end behavior with your configured model.

Host documentation: [Claude Code plugins](https://code.claude.com/docs/en/plugins/manifest-reference),
[Claude Code marketplaces](https://code.claude.com/docs/en/plugins/marketplace-reference),
[Codex plugin schema](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/manifest.rs),
[Pi packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md),
[Pi extensions](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md).
