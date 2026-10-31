+++
schema = 1
id = "TOOLSET-419-8fdddf6f"
title = "Add the Ask Autowork router and the fresh-context rule"
short = "Add router and fresh-context rule"
status = "open"
goal = "SKILL-STYLE"
section = "Now"
rank = 1000
depends_on = []
touches = ["skills/ask-autowork", "adapters/skills/ask-autowork", "adapters/pi.mjs", "AGENTS.md", "docs/skill-standard.md", "docs/workflows.md", "docs/cross-host.md", "README.md", "CHANGELOG.md", "tests", "skills/autowork/SKILL.md", "skills/grilling/SKILL.md", "skills/improve-codebase-architecture/SKILL.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Adapt two practices from mattpocock/skills that the first standard pass missed: a single router skill over the bundle, and the rule that every dispatched subagent or worker starts in a fresh context window. The router names one command per situation and never grants authority; the rule goes into the repository instructions, the standard and the skills that dispatch. Keep the router registered on every host and covered by the packaging tests."
acceptance = ["Skills/ask-autowork maps the main flow and the on-ramps to commands, states that it is orientation rather than authority, reads the chosen skill before describing it, and satisfies the skill standard (summary description, Boundaries, one Done when).", "The repository instructions and docs/skill-standard.md state the fresh-context rule, and the skills that dispatch work (autowork, grilling, improve-codebase-architecture) tell the agent to start the child fresh.", "Pi, Claude Code, Codex and Hermes expose the router; packaging, doctor, Ponytail, plugin, bundle, task-prepare and skill-standard checks pass, plus node --test tests/portable_pi.test.mjs. No model behavior is claimed."]
checks = ["python3 scripts/check.py tests/test_skill_standard.py tests/test_skill_descriptions.py tests/test_portable_package.py tests/test_doctor_modes.py", "node --test tests/portable_pi.test.mjs"]
exclusions = ["No authority change, no upstream edit, no new runtime or dependency, no claim of model behavior from prose."]
+++
