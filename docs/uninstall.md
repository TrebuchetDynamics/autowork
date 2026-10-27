# Removal and configuration recovery

Removing the plugin stops future use; it does **not** restore the profile to its
pre-install state. The installer has no complete transaction journal or automatic
rollback command. This page describes manual recovery, not a guarantee of reversal.

Source: [runtime configuration writes](../runtime_defaults.py),
[setup configuration writes](../install-plugins.sh), and
[native skill provisioning](../install_skills.py).

## Before installation

Keep a private backup of each target profile's `config.yaml` and an inventory of
its plugin and skill directories and `scripts/`. Include memory-provider selection,
existing store bindings (including `plugins.entries.omh.settings.omh_home`),
`approvals`, disabled-skill lists, the Telegram
`platforms.telegram.extra.command_menu.priority` list and plugin enablement. Configs
can contain credentials; do not commit or publish backups. Full setup discovers
all live profiles, so a default-profile backup alone is insufficient.

Keep the dry-run output alongside the backup, after checking it for sensitive
paths. A preview is not a record of which writes subsequently succeeded.

## Remove from one profile

Use its actual name in place of `PROFILE`; `default` names the default profile.
Stop active work that depends on this plugin before removing it.

```sh
hermes -p PROFILE config set plugins.entries.autowork.settings.apply_runtime_defaults false
hermes -p PROFILE plugins disable autowork
hermes -p PROFILE plugins remove autowork
```

These are Hermes' native removal commands. `plugins remove` also deletes the whole
`plugins.entries.autowork` entry, including that opt-out, so set the opt-out
again before any later reinstall. Repeat for each profile you intend to remove. A shared gateway can still have loaded handlers: restart it through your
normal service procedure after ongoing work has stopped, and reopen CLI sessions.
Removing a local plugin link does not mean its source checkout should be deleted.

## Restore configuration deliberately

Restore only the keys changed by setup from your pre-install backup, preserving
later unrelated edits. Loading the plugin with runtime defaults enabled would
reapply its policy, which is why the opt-out comes first.

Without a backup, the old values cannot be recovered from this repository. You
can choose a new policy explicitly, for example (Hermes' own default mode is `smart`):

```sh
hermes -p PROFILE config set approvals.mode manual
hermes -p PROFILE config set approvals.destructive_slash_confirm true
hermes -p PROFILE config set approvals.mcp_reload_confirm true
hermes -p PROFILE config set agent.max_turns 90
hermes -p PROFILE config check
```

These are example settings, **not** reconstructed previous values. Also inspect
global/per-platform skill-disable lists, the Telegram command-menu priority, plugin
activation, memory configuration and the bundle-managed
`scripts/autowork-start-notice.py`. Restore removed keys as absent (`hermes -p
PROFILE config unset KEY`) when that was the prior state; do not replace an entire config with an old copy blindly.

## Skills, integrations and memories remain separate

- Bundled native skills were copied into profile skill directories. Existing
  same-name skills were preserved. There is no per-file ownership journal that can
  prove a current copy belongs exclusively to this installer. Compare against your
  inventory and inspect local edits before removing any skill or shared support files.
- OMH, speech, Graphify and external skills are separate installations. A previously
  installed external Ponytail plugin also remains separate; the current pinned
  Ponytail skill suite is bundled with Autowork.
  Do not remove one merely because Toolset is gone; other workflows may use it.
- Select your intended memory provider before removing an active provider plugin.
  Removing a plugin is not erasure of its memory store, a migration, or deletion
  from backups. See [memory](memory.md) for inspection and retention limitations.
- Hindsight is no longer part of the bundle. Older stores are retained; this
  removal does not imply that their data was migrated or erased.

Verify profile config, plugin/skill inventory and the intended memory provider
before resuming work. A successful plugin-removal message alone proves none of
those restoration steps.
