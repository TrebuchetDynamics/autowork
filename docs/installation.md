# Installation and profile effects

Source: [setup orchestrator](../setup_bundle.py), [source installer](../install-plugins.sh),
[profile defaults](../runtime_defaults.py), [native skill provisioning](../install_skills.py).

## Install

Prerequisites: configured Hermes, Bash and Python 3.12+. Full setup also needs Git
and `uv` when `omh` or `graphify` is not already installed. Setup now checks these
prerequisites before starting installation stages; later runtime failures can
still leave partial setup.
See [compatibility](testing.md#compatibility) for the verified environment.

Setup is broader than installing this plugin: the current source inventory targets
all profiles for OMH, Ponytail, external skills, Graphify, speech support,
and OMH memory. Setup selects OMH with bounded `auto-safe` capture; no external
memory server or connection JSON is required.

```sh
hermes plugins install TrebuchetDynamics/hermes-toolset
hermes plugins enable hermes-toolset
hermes toolset setup --yes-deps
hermes toolset doctor
```

From a local checkout, one command performs the complete installation for every
existing live profile:

```sh
bash install.sh --yes-deps
```

`install.sh`, `install-plugins.sh`, and `hermes toolset setup` share the same
complete setup path: bundled skills, plugin installation/enablement, profile
configuration, OMH setup, per-profile readiness checks, and running-gateway command
refresh. No manual symlinks or per-profile enable commands are needed. Use
`--dry-run` to preview, `--bundle-only` to install only this bundle and its native
skills, or `--no-reload` to explicitly defer gateway wiring. Dependency consent
and native security scans still apply; a blocked dependency or failed readiness
check returns nonzero and reports setup as incomplete.

Plugins are enabled per profile. For a named profile, use that profile's home for
the link and `hermes -p PROFILE plugins enable hermes-toolset` to enable it.
`hermes toolset setup` installs and enables the sources in
[plugins/PLUGINS.md](../plugins/PLUGINS.md), including external skill repositories,
Graphify's Hermes integration, and OMH's full memory setup. It also links and enables
hermes-toolset itself in every existing live profile, preserving existing plugin
installations. After creating another profile, rerun setup or, from this checkout,
run `bash install-plugins.sh --bundle-only` to add just this bundle and its defaults
across profiles. The links depend on keeping this checkout installed. It applies
[our defaults](../plugins/defaults.json): select OMH with `auto-safe` memory in independent stores, keep the
current TUI, disable the optional menubar, allow toolset gateway injection, and
set `approvals.mode` to `off` for profiles with hermes-toolset installed. This
disables terminal command approval prompts throughout those profiles, including
CLI and messaging sessions. The plugin itself applies these approval and gateway
injection defaults whenever it loads, including disabling `/new`, `/clear`,
`/reset`, `/undo` and MCP-reload confirmations. No setup command is needed for
this policy after the plugin is enabled. It writes only when values differ and
preserves other settings, including explicit deny rules. Hermes hard blocks still
apply. Setup also clears global and per-channel skill disable lists.
To opt out of automatic policy application, first run
`hermes -p PROFILE config set plugins.entries.hermes-toolset.settings.apply_runtime_defaults false`,
then restore the desired settings, for example
`hermes -p PROFILE config set approvals.mode manual` and
`hermes -p PROFILE config set approvals.destructive_slash_confirm true`.
Full setup runs OMH doctor, checks every profile, and refreshes live commands.
Native plugin loading provisions missing bundled skills, so full setup is not
required for the core questions-only interview. Use setup for external integrations,
OMH configuration and fleet-wide provisioning; native installation does not perform
those steps. Saving interview decisions through repo-docs additionally requires
Graphify and the relevant file/terminal tools.
Use `hermes toolset setup --dry-run` to preview target profiles.

## Preflight before fleet writes

Every complete setup starts with [read-only preflight](../setup_preflight.py).
It inventories all live profiles and prints planned skill copies, preserved
existing skills, plugin links, approval/gateway settings and memory effects.
The autonomous fleet defaults are unchanged; this adds no interactive approval
round. `--dry-run` runs preflight only and exits without installation stages.
Full previews contact Git source servers with bounded timeouts; core previews
need no dependency network access.

Checks include executable availability, the required Hermes skill/injection APIs,
strict YAML parsing (including duplicate keys), writable installation paths,
existing skill/plugin conflicts, OMH store isolation and source accessibility.
Compatibility is inspected from local Hermes source without loading its plugins;
the configuration parser uses Hermes's managed Python and does not print config
values or parser excerpts that could contain credentials. Unrecognized runtime
layouts fail visibly instead of being assumed compatible.

A failed preflight exits nonzero before changing profile configuration, plugins,
skills or memory. This guarantee starts at the setup orchestrator: invoking it
through `hermes toolset setup` may already have loaded the plugin and applied its
runtime defaults. Use `bash install.sh --dry-run` for a preview that does not boot
Hermes. The internal `--sources-only` adapter and standalone helper scripts are
not the complete setup entry point.

Preflight is not a transaction or a security-scan approval. Native scans still
run during dependency installation; rejection, package resolution failures,
network changes, concurrent edits and later runtime failures can leave partial
setup after preflight passes. No rollback is implied. Source reachability alone
does not certify a pinned version or a usable integration. Profiles linked to
another bundle checkout are blocked until that installation is explicitly
updated/removed, avoiding finalization through stale code.

## Bundled Grill Me

`skills/grill-me/SKILL.md` bundles the MIT-licensed official
`official/software-development/grill-me` skill (version 2.0.0), preserving its
upstream attribution. It is available through `/grill-me` in CLI chat and
`/grill_me` in Telegram. Enabling/loading hermes-toolset installs missing bundled
skills and shared support files into that profile's native skill directory, using
the same offline provisioner as full setup. Existing flat and categorized skills
are preserved; incomplete existing slots fail visibly instead of being replaced.
Ordinary plugin loading never installs network dependencies, changes sibling
profiles, or reloads a gateway. Full setup provisions native skills across all
profiles before external plugin setup.
Setup refreshes running gateway command handlers and checks their activation
receipts automatically. It does not send test messages or restart ongoing turns.
Existing sessions can retain prior tools, prompts and memory providers; those
changes apply to new sessions. A stopped gateway is reported as not running,
not as a tested messaging connection.

## Telegram setup

Enabling/loading hermes-toolset applies its gateway-injection setting in the
owning profile. There is no YAML wiring step. This lets a skill command queue an
agent turn in the chat where it was invoked. Full setup refreshes running gateway
commands and verifies activation receipts; `--no-reload` explicitly defers that.
Existing CLI chats must be reopened to receive a new plugin/tool inventory.

See [tested compatibility](testing.md#compatibility) for the recorded Hermes revision
and required plugin APIs. Hermes needs its normal model and Telegram
configuration; individual skills may require their own tools.


## Limits of the opt-out

The runtime-defaults opt-out controls plugin loading only. Full setup writes its
configured defaults directly, so do not use it as a policy-preserving reinstall.
Back up configurations first and review [removal and recovery](uninstall.md).

Updating this page: reconcile changes to setup flags, profile discovery, runtime
policy writes and native provisioning against the source links above.

## Upgrade to Autowork

Autowork replaces the former command and skill, rather than registering an alias.
The skill, helper paths, readiness value (`ready_for_autowork`) and new private
state use the same name. Update integrations that consume the old readiness value.

Before upgrading an existing scheduled profile, wait for its current cron and
native workers to finish; preserve paused schedules. Back up its skill directories,
cron jobs and private state. Provision `skills/autowork` from this checkout,
preserving local skill customizations, and retire the old skill's `SKILL.md` from
native discovery. Replace old command, helper and skill names in existing job
names, prompts and attached skills through `hermes cron edit`; retain job IDs,
schedules, enabled states, delivery and model settings.

From the source checkout, preview and migrate each existing profile's private state:

```sh
python3 scripts/migrate-autowork.py --home /path/to/profile-home
python3 scripts/migrate-autowork.py --home /path/to/profile-home --apply
```

The migration refuses conflicting stores and held owner/handoff locks. It moves
the existing directory, preserving receipt bytes and lock inodes; it does not
restart workers or declare their tasks complete. A filesystem link at the retired
state path preserves historical receipt references, not a command alias. Do not
rewrite pinned manifests or signed evidence to change their historical spelling.
Update pending owner-mailbox routing paths to the new real state directory before
using them; private-state helpers reject symlink paths. Retain retired execution
files needed by historical/native contracts outside skill discovery until those
contracts are retired. Reload gateway commands and refresh Telegram menus after
provisioning; verify `/autowork` is present and the retired command is absent.

## Update all profiles

Run `/toolset update` in an authorized Hermes CLI or gateway chat. It starts a
background updater; use `/toolset update status` for its durable result, not the
initial “requested” message as proof of completion. `/toolset update --check`
fetches upstream and previews changes without advancing checkouts or writing
profile skills/configuration. It still writes Git fetch metadata and its receipt.

Terminal equivalents wait for completion:

```sh
hermes toolset update --check
hermes toolset update
```

A named-profile invocation still targets every existing live profile under the
same Hermes root. The updater fetches the official Hermes Toolset `main` branch,
checks each distinct installed Git checkout, and accepts only clean fast-forward
updates. Dirty checkouts, local commits absent upstream, unsafe paths and skill
merge conflicts stop preflight before checkout/profile writes. Review and commit
or move local changes yourself; the updater never stashes, resets or force-pulls.
Non-Git plugin distributions need a supported Git installation before this update.

Bundled native skill copies are synchronized, including shared references and
upstream deletions of unmodified files. Compatible local edits are merged;
conflicting edits are preserved for reconciliation. If the checkout already advanced,
the updater can refresh a native file whose bytes exactly match that same path in
trusted upstream history (at most 100 path-changing commits, cached per checkout).
It does not infer a merge base for modified older copies. Unknown differences on
unchanged upstream paths are reported as `drift`, with an `incomplete` result;
all checkout/profile writes are deferred until those files are reconciled. Check
mode reports the same drift and planned copies without applying them. History
outside the bounded window or unavailable in a shallow checkout may require manual
reconciliation; files absent from both checkout revisions are not inventoried.
An exact byte match establishes historical content, not whether someone intended
to pin it. There is no per-file pin setting in this updater: review intentional
pins before invoking an update, and retain them outside the managed copy if needed.
Missing bundle installations
are linked to the updated source. Native enablement loads the plugin and applies
its documented runtime defaults; per-profile bundle-only finalization verifies
registrations and refreshes gateway commands. Separate native checkouts remain
separate. It does not upgrade unrelated plugins, Hermes Agent or external imports.
Existing setup prerequisites still apply; this is not a policy-neutral operation.

`maintenance/toolset-update/latest.json` in the root Hermes home records status,
source revisions, profiles, unresolved drift paths/actions and the backup location. `run.log` holds setup details;
per-run backups include original skill files and a manifest. An `incomplete` result
may follow partial application: preserve the backups, fix the reported cause and
rerun. There is no automatic rollback. A stopped gateway is reported by setup;
an unreachable live gateway is not treated as verified wiring.

Workers and schedules are not restarted or changed. Update between active tasks
after quiescing or reconciling running workers because runtime/helper files change.
Historical byte matching does not establish compatibility with an active run or
its pinned execution files, manifests or evidence; update receipts do not qualify
that compatibility. Existing conversations may
retain already-loaded instructions; open a new conversation to load updated skills.
The new `/toolset update` handler itself first needs the normal plugin reload if
upgrading from a version that does not register it.
