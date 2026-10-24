# Source compatibility foundation

The accepted [source-layout plan](../docs/plans/structural-audit-2026-10.md#compatibility-foundation--existing-toolset-368-24bdb225)
separates source ownership from stable entry paths. This foundation does **not**
relocate production implementations: the existing root native files and
`pi-autowork/` runner files still own their behavior. The source package
initializers are inert; do not redirect an entry to an incomplete source package.

## Selected-release APIs

`autowork_bootstrap.py` loads only its own `Src/autowork_bootstrap.py`, with one
root-keyed identity even for path-based native callers. There is no cwd, Git,
site-packages or other-release fallback. Bootstrap loading and source discovery
do not write bytecode, start processes or import product modules.

`Layout(root)` is frozen and resolves a linked selected root. Its `root`, `src`,
`runtime`, `package`, `engine` and `component` properties locate the toolset,
not the target repository. `resource(relative)` confines resources to that root.
`entrypoint(name)` returns stable public paths (native names, runner names,
canonical dotted runner names, `autowork`, `agent_commit`, or explicit relative
paths). `implementation(public_relative)` follows literal native `execute`
payloads and corresponding canonical runner owners; an unmigrated entry remains
its own owner. A declared but missing native payload fails.

`Layout.python_sources(root)` returns sorted bounded production Python owners,
including nested source modules and unmigrated entries. It excludes tests,
fixtures, bytecode directories and escaping symlinks. Source checks must inspect
these owners, not only public shims. The checker retains the existing test
inventory and sharding keys and validates source syntax/closure without imports.
Canonical runner sources must not use unqualified flat engine imports.

### Native namespace boundary

A migrating native public entry calls `execute(namespace, source_relative)` from
its exact tree-local bootstrap. The implementation compiles with its real source
filename but runs in the caller's existing dictionary. Caller module identity,
package/spec/path and public `__file__` remain intact, so global monkeypatches
continue to affect functions. The loader injects `_AUTOWORK_LAYOUT` and
`_AUTOWORK_COMPAT`.

Native dependencies use `_AUTOWORK_COMPAT.peer(globals(), name)`. Peers bind to
the current plugin package or a root-keyed private package, never an unrelated
top-level cached module. Independent native releases may coexist in a process.
Missing or escaping payloads refuse; they are not repaired from another release.

### Runner package boundary

`activate(root) -> Layout` selects the canonical `Src/pi_autowork` package for an
explicit caller. `load(root, canonical_name)` validates selected-root origins and
returns a single imported module. Flat engine aliases and canonical engine names
share objects in either import order, without adding engine directories to
`sys.path`. A runner already bound to another release is refused. This is separate
from native multiple-release loading. The only legacy origin exceptions are the
standalone `worktree_paths.py` and `checkout_lock.py` hooks.

`run(root, canonical_name, argv)` calls the module's explicit `_compat_main(argv)`
adapter; it never executes the canonical module body a second time. Production
adapters and their terminal-block semantics belong to the subsequent relocation,
not this foundation. Existing release pinning and environment contracts are unchanged.

## Offline qualification and packaging

The npm allowlist includes root/Src bootstrap and `Src/pi_autowork/`, together with
existing portable entries/resources. It excludes Hermes-only
`Src/autowork_runtime/`. Archive help and read probes are distinct from immutable
runner launch: release pinning still requires a committed Git toolset.

`tests/src_fixture.py:copy_sources` copies complete selected Python source closure
plus explicitly requested resources into private fixtures, including both standalone
hooks. `tests/test_install_plugins.py` uses it because its shell fixture imports
native runtime policy; it is not a shell-discovery-only fixture.

Focused checks:

```sh
python3 scripts/check.py tests/test_src_bootstrap.py tests/test_affected_tests.py tests/test_check.py tests/test_portable_package.py tests/test_install_plugins.py
node --test tests/portable_pi.test.mjs
python3 scripts/affected_tests.py --run
```

The package test uses private sources, offline `npm pack --ignore-scripts`, and
extracted files; it runs no installation or lifecycle scripts. Affected selection
resolves qualified/relative imports, package initializers and old-entry-to-source
edges. The command-line selector falls back to the full inventory for unresolved,
deleted, initializer or global inputs rather than silently losing coverage.
These offline oracles do not qualify installed profiles, live models or jobs.
