+++
schema = 1
id = "TOOLSET-408-38a6a41f"
title = "Add a Graphify workflow and retire the Understand Anything graph pass"
short = "Add and reuse the Graphify workflow"
status = "open"
goal = "GRAPHIFY"
section = "Now"
rank = 1000
depends_on = []
touches = ["adapters/skills/graphify/SKILL.md", "adapters/skills/graphify/agents/openai.yaml", "adapters/pi.mjs", "skills/unused-code/SKILL.md", "skills/git-commit-push/SKILL.md", "tests/test_portable_package.py", "tests/portable_pi.test.mjs", "docs/cross-host.md", "docs/workflows.md", "README.md", "CHANGELOG.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Add an explicit-only portable Graphify workflow that reuses the official graphify CLI and its graphify-out/graph.json without installing the tool, adding hooks or bundling upstream's skill. Replace the Understand Anything graph references in local Autowork skills with that workflow while leaving pinned upstream bytes and the external Hermes graphify skill unchanged. Register the adapter for Pi, wire packaging and docs, and keep every collection and code-claim rule bounded."
acceptance = ["The portable graphify skill links the shared Ponytail method, the shared writing rules and the host contract; it declares disable-model-invocation and an explicit-only Codex policy; it states the CLI package, code-only build, version and schema checks, exit codes 0/3/4, EXTRACTED versus INFERRED meaning, staleness handling, the no-install/no-hook rule, graphify-out not being committed, and that a graph never proves dead code.", "Local Unused Code points candidates at a current graphify graph and keeps the pinned protocol's Understand pass only as a legacy-path fallback; the commit workflow treats graphify-out as a generated artifact. Pinned upstream files, plugins/defaults.json required skills and the external Hermes graphify installation stay byte-exact and unchanged.", "Pi declares the command, portable packaging and description tests cover the new adapter, and docs describe the host invocation for all four hosts. python3 scripts/check.py for the affected modules and node --test tests/portable_pi.test.mjs pass. Packaging and link checks do not qualify a live graph build or model behavior."]
checks = ["python3 scripts/check.py tests/test_portable_package.py tests/test_skill_descriptions.py tests/test_ponytail_bundle.py", "node --test tests/portable_pi.test.mjs"]
exclusions = ["No bundled skills/graphify folder, no upstream skill vendoring, no tool installation, hooks, MCP servers, model calls, host settings or permission changes, no edits to pinned upstream protocols or evidence, and no live graph, dead-code or model-behavior claim."]
+++
