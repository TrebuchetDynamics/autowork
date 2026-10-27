# Installation and profile effects

Source: [setup orchestrator](../setup_bundle.py), [source installer](../install-plugins.sh),
[profile defaults](../runtime_defaults.py), [native skill provisioning](../install_skills.py).

The native setup bodies live in [`Src/autowork_runtime/`](../Src/autowork_runtime/):
`setup_bundle.py`, `setup_preflight.py`, `setup_runtime.py`, `install_skills.py`,
`install_omh.py` and `install_graphify.py`. The root Python files remain the public
entrypoints, including `install-omh.py` and `install-graphify.py`. Keep their
same-release `autowork_bootstrap.py` and `Src/` payload together; a single copied
installer is not standalone. Preflight rejects missing declared source payloads
before installation stages. This layout does not change setup targets or policy.

## Full suite from a checkout

`./install.sh` installs the full suite for every available host with verbose output.
Use `--menu` when you want to select components interactively:

```sh
./install.sh
./install.sh --menu
./install.sh --dry-run
./install.sh --only codex
```

The suite includes the Pi package, `autowork` command/TUI, `tx` launcher, Hermes
fleet setup, and Claude Code and Codex plugins with their complete portable skill
suites, including [bundled Ponytail](cross-host.md#bundled-ponytail-on-every-host).
All Autowork skills apply its shared method within their existing authority; no
separate Ponytail plugin, hooks or persistent modes are installed. Existing external
Ponytail installs are not changed or removed. `--full` (`--all`) is the default; `--skip` excludes components. Host CLIs
must already be installed: full mode reports missing hosts as skipped, while
`--only` reports a requested missing host as failed. Hermes also needs a Hermes
home (`~/.hermes`, or `--hermes-home`/`HERMES_HOME`); a default home that does not
exist yet counts as missing. The TUI/web view needs `uv`, and using the tmux
launcher needs `tmux`. A replaced `~/.local/bin/autowork` or `~/.local/bin/tx` is
kept as `<name>.bak`, then `.bak.1` and so on, so no earlier backup is lost; a
symlinked `tx` is moved aside, never written through. Existing tmux configuration,
helpers and shell completions are kept, including dangling symlinks; only missing
files are installed.

Output streams during each install step, including native prompts. Verbose output
is on by default (`--verbose`) and shows shell-quoted commands; `--quiet` shows summaries and failure diagnostics,
while leaving native output visible when input is a terminal. The failure
transcript in quiet mode is limited to its last 16,384 characters. Colors are
automatic on terminals (`NO_COLOR=1` or `TERM=dumb` disables them); use
`--color always`, `--color never`, or `--color auto` to override. Each summary
reports installed, planned, skipped and failed components with total elapsed
time. A failed command stops that component, continues independent components,
and causes a nonzero exit. Even an error mentioning “already” remains a failure.
For a structured updater receipt, the summary includes its status, cause (including
per-profile recovery errors) and supported next action, rather than its closing
JSON brace. Non-JSON or truncated output gets a bounded diagnostic fallback.
Successful components remain installed; retry just Hermes with
`./install.sh --only hermes` (and the same `--hermes-home` if supplied).

`--dry-run` prints selected commands without installing. `--hermes-home`,
`--bundle-only`, `--no-reload` and `--yes-deps` apply only to Hermes. When a
profile already has its own plugin clone, Hermes is updated with `update_bundle.py`,
which supports none of those three and can restart gateways on ordinary updates, so passing one fails the
Hermes item instead of being ignored. Host security and dependency prompts still
apply; full mode does not supply consent flags.

## Install

Prerequisites: configured Hermes, Bash and Python 3.12+. Full setup also needs Git
and `uv` when `omh` or `graphify` is not already installed. Setup now checks these
prerequisites before starting installation stages; later runtime failures can
still leave partial setup.
See [compatibility](testing.md#compatibility) for the verified environment.

Setup is broader than installing this plugin: the current source inventory targets
all profiles for OMH, Graphify, speech support and OMH memory. With the
checked-in defaults, setup requests bounded `auto-safe` capture while preserving
existing store bindings. An explicitly stored mode is retained only when the
configured `memory_mode` is `preserve`; binding preservation alone does not preserve
that policy. No external memory server or connection JSON is required.

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

The Hermes item in `install.sh`, `install-plugins.sh`, and `hermes autowork setup`
share the same complete setup path: bundled skills, plugin installation/enablement, profile
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
Ordinary plugin loading writes only inside the owning profile: its config,
`scripts/`, and missing bundled native skills and shared support under `skills/`.
It never installs network dependencies, changes sibling profiles, or
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

After a changed all-profile update activates successfully, the updater also runs
that fetched release's `install.sh --full --skip hermes,pi -q` once from its updated
plugin checkout. This refreshes the `autowork` command/TUI, `tx`, and the Claude Code
and Codex plugins through the same supported installer used for initial setup.
Hermes was just updated; Pi package updates remain owned by the runners at their
safe point. Missing host CLIs are skipped. No privilege escalation or consent flags
are supplied, and stdin is closed so background updates cannot wait for a person's
answer. Native host security/dependency requirements still apply.

Host refresh is best effort, with a five-minute limit for the whole installer run;
on timeout its process group is stopped. It never rolls back or fails a successful
Hermes update. The receipt's `hosts` list records `item`, `status` and `exit` for
`autowork`, `tx`, `claude` and `codex`, and chat status adds one `Hosts:` line.
Completed items retain their outcomes if a later item times out; remaining items
report `timeout`. An unavailable installer reports `unavailable`; missing or invalid
item reports use the installer's failure exit, or `unreported` if it exited zero.
Skipped/unavailable/timed-out items have no item exit code (`null`). The installer
writes incremental JSONL progress to `AUTOWORK_INSTALL_REPORT` when that internal
environment variable is set; native output is not parsed as a receipt.

`--check`, scoped local deployments, and pin/unpin operations never run the host
installer. An `up_to_date` update skips it too: a no-op rerun does not retry failed
host items. To retry those independently, run `./install.sh --full --skip hermes,pi`
from the updated checkout. Existing user config, including `~/.tmux.conf` and shell
completions, is preserved; command replacements retain the `.bak` rule above.
Offline fixture checks exercise preview mode and a real `install.sh --only tx`
without contacting host services; they do not establish live plugin acceptance.

An update also self-heals each profile: plugin activation re-applies the bundle's
command menu, approval and gateway-injection settings, and finalize fails the
profile if they did not land (profiles that opted out of runtime defaults are not
checked). `settings_healed` lists profiles whose config changed.
An update that starts while a restart it requested is between gateways (the old one
gone, the new one `starting`) waits up to 5 minutes for the new one before activating
profiles, then finalizes any profile whose commands are not wired yet again after 15,
30 and 60 seconds, instead of reporting `incomplete`. A draining gateway still serves,
so an update then goes ahead and joins that restart.

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
checks each distinct installed Git checkout, and normally accepts clean equal or
fast-forward revisions. A verified managed checkout with rewritten upstream history
can instead use [managed checkout recovery](#managed-checkout-recovery).
Dirty checkouts, unproven local commits, unsafe paths and skill
merge conflicts stop preflight before checkout/profile writes. Review and commit
or move local changes yourself; the updater never stashes, resets or force-pulls.
Non-Git plugin distributions need a supported Git installation before this update.

Bundled native skill copies are synchronized, including shared references and
upstream deletions of unmodified files. Every released skill file is reset to the
release byte for byte. A profile that edited its installed copy (Hermes' background
skill review rewrites them, agents add lessons there) gets the release; its old copy
is saved in the update's backup and listed under `local_edits` as `reset`, so port
any lesson that should reach every profile into the bundle. Kept edits used to block
every later release of that file. A copy whose bytes match that same path in trusted
upstream history (at most 100 path-changing commits, cached per checkout) is an
older release, refreshed without a report; history unavailable in a shallow checkout
is fetched first. Check mode reports the same `local_edits` without applying them.
A skill file removed from the bundle is deleted from profiles, together
with folders that leaves empty, even when the shared checkout had already advanced; an
edited copy goes too, saved in the backup and listed as `removed`. The update is
idempotent: a second run with no new release writes nothing, reports no local edits,
leaves no backup and needs no gateway restart.
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
source revisions, profiles, reset or removed `local_edits` and the backup location.
Managed-checkout recovery has separate merge evidence; ordinary skill-copy reset
is not a three-way merge. For updates started from chat,
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

### Managed checkout recovery

A negative `merge-base --is-ancestor` result is not a Git failure. The updater
classifies it separately from actual Git/network failures and locally advanced
checkouts. A shallow checkout gets one trusted fetch with at most 1,000 additional
history levels; if negative ancestry remains shallow, recovery defers rather than
assuming a rewrite. Equal/fast-forward updates retain their normal path.

Automatic recovery requires a same-user standalone `plugins/autowork` checkout,
the expected plugin identity, a native `plugins/.install-metadata.json` record
bound to the trusted upstream, and HEAD matching its saved installed revision or
a trusted tracking tip captured **before fetch**. A clean tree or matching URL
alone is insufficient. Dirty/untracked files, extra Git worktrees, shared object
stores, unknown provenance, an unselected profile link, a live gateway or a live/
unknown helper consumer prevent replacement. Quiesce consumers yourself and
reconcile the reported evidence; recovery never kills or restarts them.

The updater stages the exact trusted fetched main commit and reuses the scoped
native transaction below: all selected consumers are preflighted and scanned,
worker-handoff locks are held, the complete original checkout (including `.git`)
is moved into an owned backup, and native installation publishes the staged local
URI without force or enablement. Selected links to that canonical checkout remain
links; their source is recovered once. Additional native metadata fields and other
plugins' records are retained, and the Autowork record keeps its trusted source
binding. New unselected consumers or foreign source/profile edits on retry defer
instead of becoming a new baseline.

Unlike ordinary release synchronization, **recovery three-way merges native skill
customizations against the original checkout**. Compatible edits and executable/
file permissions survive; conflicting edits or edited deletions defer without
resetting them. Original skill bytes and modes, source/base revisions and exact
merged output are retained in the transaction backup/manifest. Configuration,
runtime-policy opt-outs, credentials, jobs and paused schedules are not rewritten.
Recovery performs no profile finalization, gateway activation or host refresh.

`maintenance/toolset-update/recovery.json` journals per-profile phases and errors;
`latest.json` includes that recovery result. Native readiness alone does not complete
the run: originally selected independent fast-forward/profile writes also retain
frozen targets, original bytes/modes and resumable backups until their publication
reads back. A retry does not enlist new profiles or overwrite newer foreign edits.
Keep the referenced backup and staged source.
Rerun the same all-profile update, or `./install.sh --only hermes`, to resume
that original target and backup, even after upstream moves. An empty failed slot
can be restored from its original checkout; partial native output and newer foreign
edits are never deleted or overwritten to roll back. Read-back checks the exact
published HEAD, tracked bytes, profile output, permissions and source binding before
success. An unchanged retry validates the completed recovery without reinstalling,
rescanning, resetting preserved customizations or creating a new backup.

`python3 update_bundle.py --hermes-home /path/to/home --dry-run` only previews;
it performs no fetch, staging or state/profile writes. `--check` retains its
fetch/check semantics, but performs no recovery publication. Installer `--dry-run`
and `--skip hermes` never execute recovery. Offline real-Git fixtures cover recovery,
shared consumers, preservation, refusals and interrupted retry; they do not qualify
native scanner acceptance, a live profile reinstall or Telegram delivery.

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
Grill Me, Ponytail and the pinned engineering protocols. No separate hub installation
is needed for these skills.
Fleet setup provisions the same bundle across existing live profiles. Existing
local or categorized skill installations are preserved rather than overwritten.
Existing `shared/` support directories receive missing Markdown files only, with
atomic no-replace publication; local edits stay intact. A symlinked shared directory
is refused rather than written through. This also makes the new Ponytail method
available when installing over an older profile; use the normal updater to refresh
existing skill contents. If the old external Ponytail plugin owns a command, setup
and doctor require the corresponding `autowork:ponytail-*` skill registration and
report it under `bundled_skill_fallbacks`; they do not treat the external command
as an Autowork handler or remove it. Other foreign command collisions remain errors.
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

If the original source is gone and **publication never began**, inspect the receipt
and its backup manifest, then cancel only that exact attempt:

```bash
sha256sum /path/to/hermes-home/maintenance/toolset-update/scoped.json
python3 update_bundle.py --hermes-home /path/to/hermes-home \
  --cancel-scoped <receipt-sha256> --check
# After inspecting the preview, repeat without --check.
```

Cancellation takes the updater lock, requires matching receipt/backup evidence,
and refuses any recorded publication phase (including `backed_up`), saved plugin
slot, malformed state or archive collision. It archives the original receipt
unchanged as `scoped-cancelled-<receipt-sha256>.json` beside the active journal;
all staging and backups remain. It does not require the vanished source, alter
profiles, restart services or accept a scanner caution. Retry a reviewed deployment
normally afterward; native admission still applies. Partially published attempts
must instead resume their original recovery path. Never delete their journal to
force another deployment.

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
