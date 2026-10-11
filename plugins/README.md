# Plugin installation

From the repository root:

```sh
./install-plugins.sh --dry-run
./install-plugins.sh
```

The public command performs full setup by default: bundled skills, plugin
installation and enablement, profile configuration, memory setup, verification,
and live gateway command refresh. `install.sh` and `hermes toolset setup` use the
same orchestrator. `--bundle-only` limits setup to this bundle; `--no-reload`
explicitly defers live command wiring. No separate per-profile wiring is needed.

The source stage reads `plugins/PLUGINS.md` relative to its own location, so it
also works when called from another directory. Add one catalog URL and scope
per line; blank lines and lines beginning with `#` are ignored:

```text
https://hermes-agent.nousresearch.com/docs/plugins/omh all profiles

https://github.com/dietrichgebert/ponytail all profiles
skills https://github.com/addyosmani/agent-skills all profiles
```

`all profiles` includes `default` and existing named profiles. Deleted profiles
and directories without Hermes identity markers are excluded. Rerun after
creating a profile to install its plugins. The selected active profile does
not change these rules.

The installer uses `HERMES_HOME`, or `~/.hermes` when unset. A named-profile
home resolves to its containing root. Use `--hermes-home /path/to/hermes-root`
to explicitly select a different installation.

GitHub URLs install native Hermes plugins directly. Prefix a GitHub URL with
`skills` for a skill repository instead: the installer uses Git to clone a
temporary discovery checkout, then calls `hermes skills install` for every
immediate `skills/*/SKILL.md` in each selected profile. Hermes handles existing
skills, scanning, and confirmation; no force-overwrite flag is passed. The
checkout is removed afterwards. These entries require Git. Discovery and
native installs use the default branch; updates during a run can change it.
Dry runs show the repository/profile plan without cloning or fetching skills.

Graphify uses its official `graphify install --platform hermes --project`
adapter in a temporary directory. The generated skill and references are copied
into selected profiles. Its CLI is installed with `uv tool install graphifyy`
when missing; existing skills are preserved.

Requires Bash, Python 3.9+, and `hermes` on `PATH`. GitHub plugin skips use
Hermes' recorded source metadata so differing repository and plugin names work.
Untracked manual installs are left for Hermes to handle without force-overwrite.
Installation uses the native catalog
command, preserving Hermes' dependency, security, and activation prompts;
run interactively to answer them. Plugins are enabled by default; `--yes-deps`
consents to native plugin dependencies. Skill installation skips the normal
confirmation prompt but still enforces security scans. Full setup runs OMH's
setup and doctor using `plugins/defaults.json`. The
memory provider is selected as OMH with `auto-safe` policy and an independent
store per profile; the current TUI is kept. Before enabling the bundle, it configures gateway injection,
turns off command and slash-confirmation prompts, and clears global/per-channel
skill disable lists in each profile. All declared plugin sources target all profiles. Existing installs and local edits
are preserved; readiness is checked per profile after setup. Running gateways are
refreshed through the native control socket and command activation receipts are
checked, without restarting in-flight turns. This verifies command registration,
not a live Telegram/model round trip; prior tools/prompts/memory in an existing
session can remain until a new session. A stopped gateway is reported separately.
An install failure is reported, other targets are attempted, and the script
exits nonzero if any installation, setup or verification stage failed. Even a
partial install refreshes successful command registrations and reports the gaps. `--dry-run` never invokes Hermes.

Run the isolated installer tests with:

```sh
python -m unittest discover -s tests -p 'test_install_plugins.py'
```

Native command reference: [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins).
