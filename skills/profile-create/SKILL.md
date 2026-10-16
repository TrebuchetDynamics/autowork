---
name: profile-create
description: "Create repo-bound profiles with tools and isolated memory."
version: 0.2.0
author: TrebuchetDynamics
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [profiles, repositories, setup, memory]
---

# Profile Create

`/profile-create <name> <repository> [instructions]` creates one repository-bound
Hermes profile. Telegram uses `/profile_create`. A repository-only argument uses
its basename when it satisfies the native profile naming rules. Ask for a missing
repository or genuinely ambiguous name; never create a profile pointing at home.
A `--dry-run` request validates and reports the exact steps without writing.

## Prerequisites and scope

Load `hermes-agent` and the matching configuration/background references. Resolve
this skill's directory through `skill_view`; `<bundle>` is its grandparent, not a
hardcoded machine path. Use `terminal` for CLI commands, `read_file` for source
instructions, and `patch` for scoped identity edits.

Create only the requested new profile. Never clone credentials, messaging tokens,
sessions, private memories or unrelated user state. Never change the sticky default,
modify siblings, bypass security scans, overwrite an existing profile, or create
cron jobs unless explicitly requested. Never restart a shared gateway without
separate approval. Creation does not authorize repository changes, commits or pushes.

## Procedure

1. **Validate before writes.** Inspect `hermes profile create --help` and
   `hermes profile list`. Preserve an explicit name exactly and validate against
   the installed CLI; do not silently sanitize it. Resolve the repository to an
   existing absolute directory, including paths with spaces. Run through `terminal`:
   ```sh
   git -C "<repository>" rev-parse --show-toplevel
   ```
   Bind `terminal.cwd` to that repository root, not a shell prompt or arbitrary
   non-repository directory. Inspect applicable repository instructions. Refuse
   existing/deleted-name conflicts instead of force-replacing or resurrecting them.
   Resolve the active Hermes home and canonical root with native profile/config
   output; do not assume the caller is the default profile.
   When asked to study the project first, finish a bounded read-only orientation
   before creation: current README/instructions, package metadata, architecture
   and active task owners, then the source seams needed to distinguish current
   behavior from historical claims. Use an existing graph when available; do not
   build one or run broad tests merely to personalize a profile. Carry the
   project's purpose, working style and authority boundaries into a concise
   description/identity; link its governing docs instead of copying its backlog
   or historical metrics into permanent profile instructions.

2. **Create and bind.** Use the native commands through `terminal`, stopping on
   any failed prerequisite:
   ```sh
   hermes profile create "<name>" --description "<repository purpose>"
   hermes -p "<name>" config set terminal.cwd "<absolute repository root>"
   ```
   Do not use `--clone`, `--clone-all`, `--clone-channels`, or switch the default.
   Read the new profile's `SOUL.md`; change its generic opening identity to
   the requested assistant name, otherwise the uppercase profile name. When
   project tailoring was requested, add the concise orientation established in
   step 1 without duplicating shared workflow policy. Preserve Hermes/Nous
   attribution and existing safety rules.

3. **Install hermes-toolset, not copied prompt policy.** Inventory the new
   profile immediately after native creation with targeted `plugins show NAME`
   calls and resolved plugin paths; creation may already provision shared links.
   Preserve a discovered installation and use supported enablement rather than
   deleting its link or attempting a second install merely because it is disabled.
   Inspect `hermes plugins install --help`. The local bundle can be installed through
   the native `file://` source route, preserving native scanning and dependency
   consent; derive its URI from the resolved bundle directory, safely encoding
   spaces. Do not hand-copy or symlink around a blocked security scan.
   ```sh
   hermes -p "<name>" plugins install "<bundle file URI>" --enable --yes-deps
   hermes -p "<name>" plugins show hermes-toolset
   ```
   Inspect `<bundle>/plugin.yaml`, `plugins/defaults.json` and `plugins/PLUGINS.md`
   for the CURRENT required plugin set and source identifiers. Install/enable and
   verify that set in this profile only using native plugin commands; do not bring
   back removed plugins such as Hindsight. Existing default-profile
   availability is not proof of target-profile enablement. If a scan blocks an
   install, summarize its verdict and request approval for that exact plugin and
   profile, disclosing approval-policy changes applied on enablement; only then use
   the native installer's documented override. Consent for one plugin does not
   cover its dependencies. Never disable scanning globally, copy around it, or
   invoke a fleet-wide installer to configure one profile. Keep large scan output
   in a scratch log and show a bounded summary. Inspect the dependency and
   enablement result even on exit zero: a successful download can leave a plugin
   disabled after compatibility resolution. Read back each required plugin's
   status; do not treat install banners or a later successful command as baseline
   completion. `--yes-deps` is Python consent, not proof that declared Node
   dependencies installed; report affected features unverified. If a dependency or
   source is missing, report incomplete setup. Refresh native-file inventory after
   enablement, since registration may already provision bundled copies, and
   preserve differing files instead of overwriting.
   Check `required_skills` as well as `imported_plugins` in the defaults. For
   Graphify, run the targeted source helper for this profile only:
   ```sh
   python "<bundle>/install-graphify.py" --hermes-home "<canonical Hermes root>" --profile "<name>"
   ```
   and verify a readable `skills/graphify/SKILL.md` in the target; profile setup
   does not authorize repository instruction edits.
   Configure gateway injection through `hermes -p <name> config set` if required
   by the bundle; do not duplicate shared workflow policy in `SOUL.md` or cron prompts.

4. **Independent OMH memory.** Read the bundle's current memory defaults and
   `install-omh.py` before setup. Use that source helper for ONLY the new profile:
   ```sh
   python "<bundle>/install-omh.py" --hermes-home "<canonical Hermes root>" --profile "<name>" --dry-run
   python "<bundle>/install-omh.py" --hermes-home "<canonical Hermes root>" --profile "<name>"
   ```
   Check that the planned OMH store is profile-local and independent of every
   existing profile before applying it. Refuse shared resolved paths, symlinked
   stores or global routing that defeats isolation. Preserve all existing stores;
   never copy another profile's memory or silently migrate native memory records.
   Verify provider `omh`, the effective store binding, memory policy and the
   helper's final doctor results. A standalone doctor is not proof of live recall.

5. **Verify the exact target.** Read back:
   ```sh
   hermes -p "<name>" config get terminal.cwd
   hermes profile show "<name>"
   hermes -p "<name>" plugins show hermes-toolset
   hermes -p "<name>" memory status
   ```
   Verify every required plugin is enabled in the named profile, the repository
   root matches, the identity is correct and the OMH binding is unique. Inspect
   bundled command discovery for `profile-create`. Run `hermes -p "<name>" toolset
   doctor` and keep its core-versus-full verdict; core registration is not full
   integration readiness. Check each command's exit code, since a trailing
   successful readback can hide an earlier failed install. Do not launch paid chat calls,
   add Telegram credentials, run product tests or restart gateways just for setup.

## Completion and recovery

Report profile, assistant identity, repository, bundle/plugin verification,
independent memory status and launch command `hermes -p <name>`. Name missing
credentials, runtime reload, messaging and retain/recall checks separately.

A failed step leaves an **incomplete** profile, not a working bot. Record the exact
failed step and completed configuration; preserve it for an explicitly requested
resume instead of deleting it or creating a duplicate. Never claim plugin enablement,
authentication, Telegram delivery or memory isolation from directory creation alone.
