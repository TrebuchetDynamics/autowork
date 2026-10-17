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
all profiles for OMH, Ponytail, Graphify, speech support and OMH memory. Setup selects OMH with bounded `auto-safe` capture (an existing
store keeps an explicitly stored mode); no external
memory server or connection JSON is required.

```sh
hermes plugins install TrebuchetDynamics/autowork
hermes plugins enable autowork
hermes autowork setup --yes-deps
hermes autowork doctor
```

From a local checkout, one command performs the complete installation for every
existing live profile:

```sh
bash install-plugins.sh --yes-deps
```

`install.sh`, `install-plugins.sh`, and `hermes autowork setup` share the same
complete setup path: bundled skills, plugin installation/enablement, profile
configuration, OMH setup, per-profile readiness checks, and running-gateway command
refresh. No manual symlinks or per-profile enable commands are needed. Use
`--dry-run` to preview, `--bundle-only` to install only this bundle and its native
skills, or `--no-reload` to explicitly defer gateway wiring. Dependency consent
and native security scans still apply; a blocked dependency or failed readiness
check returns nonzero and reports setup as incomplete.

Plugins are enabled per profile. For a named profile, use that profile's home for
the link and `hermes -p PROFILE plugins enable autowork` to enable it.
`hermes autowork setup` installs and enables the sources in
[plugins/PLUGINS.md](../plugins/PLUGINS.md), including any external skill repositories
it lists (currently none), Graphify's Hermes integration, and OMH's full memory setup. It also links and enables
autowork itself in every existing live profile, preserving existing plugin
installations. After creating another profile, rerun setup or, from this checkout,
run `bash install-plugins.sh --bundle-only` to add just this bundle and its defaults
across profiles. The links depend on keeping this checkout installed. It applies
[our defaults](../plugins/defaults.json): select OMH with `auto-safe` memory in independent stores, keep the
current TUI, disable the optional menubar, allow toolset gateway injection, and
set `approvals.mode` to `off` for profiles with autowork installed. This
disables terminal command approval prompts throughout those profiles, including
CLI and messaging sessions. The plugin itself applies these approval and gateway
injection defaults whenever it loads, including disabling `/new`, `/clear`,
`/reset`, `/undo` and MCP-reload confirmations, and setting `agent.max_turns` to
`unlimited` so long Autowork turns are not cut off at a per-turn iteration cap
(Hermes quick setup writes `90`); each load also sets its Telegram
command-menu priority and installs the bundle's managed cron helper script. No setup command is needed for
this policy after the plugin is enabled. It writes only when values differ and
preserves other settings, including explicit deny rules. Hermes hard blocks still
apply. In profiles with OMH, each load also adds the OMH skills outside the bundle's
measured keep list (`omh_keep_skills` in `plugins/defaults.json`, 41 skills including
code review, verification, the core and memory skills) to `skills.disabled`, so Hermes
leaves them out of every prompt's skill index. Your own `skills.disabled` entries stay;
the bundle removes only names it added (recorded in
`plugins.entries.autowork.omh_trim`) and never leaves its own skills disabled. OMH
itself, its files and its memory provider are untouched. Setup also clears per-platform
skill disable lists.
To opt out of automatic policy application, first run
`hermes -p PROFILE config set plugins.entries.autowork.settings.apply_runtime_defaults false`,
then restore the desired settings, for example
`hermes -p PROFILE config set approvals.mode manual` and
`hermes -p PROFILE config set approvals.destructive_slash_confirm true`.
Setup, including `--bundle-only`, honors the same opt-out: it skips the approval,
gateway-injection and skill-disable-list settings for that profile and says so in
its preview.
Full setup runs OMH doctor, checks every profile, and refreshes live commands.
Native plugin loading provisions missing bundled skills, so full setup is not
required for the core questions-only interview. Use setup for external integrations,
OMH configuration and fleet-wide provisioning; native installation does not perform
those steps. Saving interview decisions through docs-sync additionally requires
the relevant file/terminal tools. Direct source evidence is sufficient for routine
task and document repairs; Graphify is useful for uncertain cross-component
relationships, or required when the request explicitly calls for it.
Use `hermes autowork setup --dry-run` to preview target profiles.

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
existing skill/plugin conflicts, OMH store isolation and source accessibility. Full
(not `--bundle-only`) preflight also refuses a profile whose `memory.provider` is
another product; clear it first (`hermes -p PROFILE memory off`).
Compatibility is inspected from local Hermes source without loading its plugins;
the configuration parser uses Hermes's managed Python and does not print config
values or parser excerpts that could contain credentials. Unrecognized runtime
layouts fail visibly instead of being assumed compatible.

A failed preflight exits nonzero before changing profile configuration, plugins,
skills or memory. This guarantee starts at the setup orchestrator: invoking it
through `hermes autowork setup` may already have loaded the plugin and applied its
runtime defaults. Use `bash install-plugins.sh --dry-run` for a preview that does not boot
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

`skills/grill-me/SKILL.md` (version 2.1.0) adapts the MIT-licensed official
`official/software-development/grill-me` skill (version 2.0.0) with
mattpocock/skills grilling guidance, preserving their attribution. `/grill-me` (CLI)
and `/grill_me` (Telegram) remain typeable compatibility commands that run
`plan-with-me` in challenge mode with this skill as its reference; `/grill_me` is not
shown in the Telegram menu. Enabling/loading autowork installs missing bundled
skills and shared support files into that profile's native skill directory, using
the same offline provisioner as full setup. Existing flat and categorized skills
are preserved; an incomplete existing slot is never replaced and is logged as a
warning while the remaining skills and every command still register.
Ordinary plugin loading writes only inside the owning profile (its config and
`scripts/`); it never installs network dependencies, changes sibling profiles, or
reloads a gateway. Full setup provisions native skills across all
profiles before external plugin setup.
Setup refreshes running gateway command handlers and checks their activation
receipts automatically. It does not send test messages or restart ongoing turns.
Existing sessions can retain prior tools, prompts and memory providers; those
changes apply to new sessions. A stopped gateway is reported as not running,
not as a tested messaging connection.

## Telegram setup

Enabling/loading autowork applies its gateway-injection setting in the
owning profile. There is no YAML wiring step. This lets a skill command queue an
agent turn in the chat where it was invoked. Full setup refreshes running gateway
commands and verifies activation receipts; `--no-reload` explicitly defers that.
Existing CLI chats must be reopened to receive a new plugin/tool inventory.

See [tested compatibility](testing.md#compatibility) for the recorded Hermes revision
and required plugin APIs. Hermes needs its normal model and Telegram
configuration; individual skills may require their own tools.


## Limits of the opt-out

The runtime-defaults opt-out covers plugin loading and setup's bundle policy
settings only. Full setup still applies the OMH memory defaults and installs
external integrations, so do not use it as a policy-preserving reinstall.
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

Run `/autowork update` in an authorized Hermes CLI or gateway chat. It starts a
background updater; use `/autowork update status` for its durable result, not the
initial “requested” message as proof of completion. The status is a short summary that
fits one chat message (outcome, revisions, files written, local edits, healed settings
and menus, gateway restart); `/autowork update status full` shows the whole receipt as JSON. `/autowork update --check`
fetches upstream and previews changes without advancing checkouts or writing
profile skills/configuration. It still writes Git fetch metadata and its receipt.

An update also self-heals each profile: plugin activation re-applies the bundle's
command menu, approval and gateway-injection settings, and finalize fails the
profile if they did not land (profiles that opted out of runtime defaults are not
checked). `settings_healed` lists profiles whose config changed.
Because Telegram menus refresh only when the gateway reconnects, an update that
changed code, skills or settings restarts the gateway once when every profile
activated cleanly and a gateway is running, but only while no chat or API turn is in
flight, so Hermes never has to force one. The updater reads Hermes' `active_agents`
from the root's `gateway_state.json` and subtracts cron runs (jobs holding a
`fire_claim`), which Hermes runs in restart-safe external workers; with several
recurring jobs a moment free of cron runs rarely comes, so they do not hold the
restart. When no chat turn is in flight it requests `hermes gateway restart` at once
(`gateway_restart: requested`). Otherwise, or when the gateway's activity cannot be
read (for example while it is starting or draining), it reports `deferred` with
`gateway_restart_waiting_on` and starts a detached waiter that checks every 30
seconds for up to 6 hours. The waiter restarts at the first quiet check and sets
the receipt to `requested`; if another restart loaded the update first it records
`reloaded`; if the gateway never went quiet it records `deferred_expired` with the
next step and restarts nothing. Cron schedules persist (a job mid-run during a
restart is marked `unknown` and not retried; its next tick runs normally).
Otherwise it reports `not_running`, or `not_needed` for a no-op or incomplete
activation. While a deferred or requested restart is outstanding, a later update
reports `pending` and joins it instead of starting another one, so a burst of
updates restarts the gateway once; that restart loads the newest release, and its
outcome reaches the latest receipt with `gateway_restart_covers`, the number of
updates it covers. The waiter never restarts while an update is still applying
files: it shares the update lock and waits for the next check. `/autowork update status` then shows the waiter's latest chat-turn
count, or the seconds left and turns a requested restart is draining
(`gateway_restart_progress` in the full receipt). Once a requested restart has
finished, the next `/autowork update status` or update records its outcome on the receipt:
`completed` with `gateway_restart_result` (the new gateway's PID and start time,
which profiles' Telegram bots logged a menu resend after the restart and which did
not, and any forced-drain interruptions from the gateway log), or `restart_failed`
when the restart ended with the old gateway still running. The outcome is also kept in
`restart.json`, so when a later update has already replaced that receipt, status shows
it as `Last gateway restart` (`last_gateway_restart` in the full receipt). To restart immediately anyway, run `hermes gateway restart` yourself;
Hermes then waits for chat turns up to `agent.restart_after_turn_timeout`. Drift,
error and check results carry no `gateway_restart` field. Only the gateway recorded
in the root's `gateway.pid` is detected and restarted; a separately running
named-profile gateway keeps its old menu until you restart it.

Telegram shows a chat's own command list ahead of the default, private and group
lists that Hermes refreshes, so a leftover chat-scoped list never updates. On an applied update (not check mode or drift), for each
profile bot token in that profile's `.env`, the update checks the chats in `TELEGRAM_ALLOWED_USERS` and
`TELEGRAM_HOME_CHANNEL` and deletes a chat-scoped list only when it still contains
a retired bundle command; that chat then uses the refreshed private or group list.
Chat lists without retired names are left alone. Each chat is checked
independently, so one failing chat does not stop the others. `chat_menus_healed`
reports cleared chats by their last four digits, plus any `failed` chats the
same way when only some chats fail; an unreachable Bot API is reported and never
fails the update.

`status` is the chat form handled by the plugin; it is not a positional argument
to the terminal command `hermes autowork update`. Terminal update forms below wait
for completion. The durable result is stored at the Hermes installation root in
`maintenance/toolset-update/latest.json`; named profiles share that update status.

Terminal equivalents wait for completion:

```sh
hermes autowork update --check
hermes autowork update
```

Only one update or check runs at a time. A second one waits up to 10 seconds (a
deferred-restart waiter holds the lock only briefly per check), then exits with
code 3 and `{"status": "busy", "running": {...}}` naming the running update's PID,
mode (`update` or `check`) and start time; it changes nothing and leaves that
update's receipt in place. In chat, `/autowork update` says which update is running
and starts nothing.

A named-profile invocation still targets every existing live profile under the
same Hermes root. The updater fetches the official Autowork `main` branch,
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
A profile that edited its installed copy (agents often add lessons there) no longer
blocks the update. The updater picks the same-path version from that bounded trusted
history that the copy is closest to, and merges the edit onto the release from it.
A copy that only adds lines to the current release is kept as is. When the starting
version is ambiguous (two versions equally close, or a copy closest to the release
that also removes or changes release lines) the updater does not guess: it stops
like a conflict. Every such file is listed under
`local_edits` (`merged` or `kept`) in the result; port the lessons that should reach
every profile. A conflicting edit still stops the update before any write. Check mode
reports the same `local_edits` without applying them. History
outside the bounded window or unavailable in a shallow checkout may require manual
reconciliation. A skill file removed from the bundle is deleted from profiles, together
with folders that leaves empty, whenever its installed bytes match a released version,
even when the shared checkout had already advanced; an edited copy stays and is listed
as `kept_retired`.
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
source revisions, profiles, merged or kept `local_edits` and the backup location. For updates started from chat,
`run.log` holds updater and setup output (terminal updates print it);
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
The new `/autowork update` handler itself first needs the normal plugin reload if
upgrading from a version that does not register it.

### Linked profiles and pinned clones

A source install links each profile's `plugins/autowork` to the checkout, so
the profile loads whatever that checkout holds at the next gateway restart,
including commits that were never released. A profile whose plugin is its own clone
changes only when an update advances it. `/autowork update status` and
`hermes autowork doctor` list the linked profiles; nothing converts them
automatically.

To pin one profile, preview it, then run it:

```sh
hermes autowork pin NAME --dry-run
hermes autowork pin NAME
```

Pinning clones the checkout at the revision the link resolves to now, saves the
link under `maintenance/toolset-update/pinned/NAME-*/` and puts the clone in its
place, so the profile stays on the same revision. It refuses, writing nothing, when
the checkout has uncommitted changes (the profile would lose them on its next
restart), when that revision is not yet on upstream `main` as last fetched (the next
update could not advance the clone), or while an update runs. The gateway loads the
clone at its next restart. `hermes autowork pin --unpin NAME` restores the
saved link and moves the clone beside it instead of deleting it; it also takes
`--dry-run`.

## Complete bundled skill installation

Native plugin loading provisions every bundled skill and its support files into
the selected profile, including Impeccable, Beautify GitHub README, Autoresearch,
Grill Me and the pinned engineering protocols. No separate hub installation is needed for these skills.
Fleet setup provisions the same bundle across existing live profiles. Existing
local or categorized skill installations are preserved rather than overwritten.
`hermes autowork doctor --core` checks registration; full setup and full diagnostics
still apply to external integrations such as Graphify and OMH. This does not install
the entire public skill catalog or guarantee optional browser/service readiness.
Impeccable’s upstream launcher may download its versioned engine on first use
(or use an existing configured engine). The bundled snapshot does not contain
or attest that external binary; instruction loading has a documented fallback.

## Deploy an exact local revision to selected profiles

The legacy `/autowork update` remains the all-profile upstream update. For an
already reviewed local fix, use the scoped updater from a clean checkout:

```bash
python3 update_bundle.py --hermes-home /path/to/hermes-home \
  --profile project-a --profile project-b \
  --source /path/to/reviewed-checkout --revision <full-40-character-commit> \
  --native-python /path/to/hermes-python --check
```

Remove `--check` to apply that exact selection and revision. All four local-mode
options are required; profile selectors never silently fall back to the fleet.
The source must be a clean standalone Git checkout at the supplied commit.
Local mode does not fetch, pull, advance the source checkout, expand the selection,
change enablement, reload gateways, restart workers or change schedules. Use the
Python interpreter from the installed Hermes environment, where `hermes_cli` and
its dependencies are importable; the Hermes source used for native admission is
resolved from the `hermes` on `PATH`. Missing native APIs fail closed.

Preflight holds the updater lock and checks tracked source closure, installed
checkout and skill drift and actual process references to the selected installation;
the worker handoff lock is taken before each profile is staged. Even `--check`
creates `maintenance/toolset-update/` and its lock file.
Historical Kanban cards, including missing, malformed, blocked or done records, are
not ownership leases or deployment vetoes and are not queried to establish safety.
Preserve actual active consumers and candidates; uncertain process/workspace ownership
still defers the affected deployment. Independent eligible selections continue.
Source symlinks and submodules are refused; selected installation links are supported.
The updater replaces only the selected plugin slot with an isolated checkout,
preserving shared source, other profiles' links and active runtimes.
Customized or ambiguous native skill copies defer deployment instead of merging
unreviewed content. Native registration is checked in a disposable home; this
proves the installed bundle registers there, not live gateway wiring or product
recovery. An existing process can retain loaded instructions until its ordinary
restart. The helper-launch lock coordinates this repository's launcher; it is not
an operating-system barrier against unrelated native/manual launches.

Each profile gets a staged Git checkout and its own native security scan. Staging
and linked-source snapshots are published atomically only after clone, pinned
checkout and closure checks finish; interrupted temporary clones are never reused. Scanning
disabled, a caution requiring confirmation, or a dangerous verdict stops that
profile before publication. There is no force option, scanner-approval cache or
inherited approval from another profile or revision. After scan admission and
fresh source/destination checks, the selected plugin slot is moved into its backup
and the native `plugins install` implementation installs the local staged URI at
the exact commit with force and enablement both false. Native manifest, kill-list,
security and dependency admission still apply. Missing dependency consent or any
native refusal is reported as incomplete; no dependency override is supplied.
The native manager owns any dependency-environment publication and its existing
runtime protection. The updater does not migrate or rewrite active cards.

`maintenance/toolset-update/scoped.json` records the local deployment separately
from the legacy updater receipt. Each run's backup directory retains a manifest,
original skill bytes, original plugin slot, and a Git snapshot of a previously
linked source. Successful profiles record installed SHA-256 hashes and the native
registration probe's commands. After a failure while the plugin slot is moved aside,
the original plugin is moved back if the slot is still empty; partial native output is preserved for inspection, never erased.
An interruption can leave plugin and skill publication at different phases.
Rerun the same command to resume the original source, selection, staging and
backup. A different revision/selection, including the same profiles in a different order,
is refused while that run is incomplete.
Completed unchanged deployments perform no native installation or scan; drift is
still checked. Retain the run directory: native installation provenance points to its staged local
source, and its original backups support later reconciliation.
Offline tests use real Git repositories and fake native admission; they do not
establish live scanner acceptance, dependency admission, Telegram delivery or
original-task recovery.

## Scheduled self-repair

Updated Autowork cron instructions use `scripts/heal-owner-cron.py` for bounded
repair of their own managed prompt/skill wiring. See [cron self-repair](../skills/autowork/references/cron-autoheal.md)
for the exact-profile/job command, private receipts and startup limitations. Existing
saved prompts are not updated merely by installing source: refresh their managed
wiring through the supported cron interface. A maintainer can invoke the same helper
for one existing job; it never creates a watchdog or resumes paused schedules.
