---
name: ask-autowork
description: "Find the skill that fits the situation."
license: MIT
---

# Ask Autowork

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

You do not remember every command, so ask. This map names the skill for a situation; it
never replaces reading it. Before you describe what a skill does or recommend skipping
a step, read that skill's `SKILL.md`: a summary here is orientation only.

## Main flow: idea to delivered work

1. **Sharpen the idea.** `/grilling` interviews you in rounds and stops when the
   decision tree is empty. Working in a repository? `/grill-with-docs` also records the
   settled decisions as ADRs and glossary terms. A plan that already exists gets
   `/grill-me`, the plan-specific branch.
2. **Make the plan executable.** `/plan-for-me` investigates and saves goals and tasks
   without an interview; `/plan-with-me` asks only what it cannot find.
3. **Do the work.** `/autowork` implements one ready task, verifies it, and closes it.
   For many lanes at once, `/autonomous-codebase-improver`.
4. **Deliver.** `/git-commit-push` commits, syncs and pushes when the request allows.
   `/lgtm` continues a concrete step you already approved.

## On-ramps

| Situation | Skill |
| --- | --- |
| Something is broken and you cannot yet reproduce it | `/bug-harvest` |
| The suite is bloated, slow or full of low-value tests | `/test-optimizer` |
| Code looks unused and you want it gone | `/unused-code` |
| One folder needs splitting without behavior change | `/skill-folder-refactor` |
| Modules are shallow or seams leak | `/improve-codebase-architecture` |
| Queue work is held and the owner must decide | `/blockers` |
| Docs or task records drifted | `/docs-sync` |
| A question needs measured evidence | `/autoresearch` |
| One engineering method is missing (TDD, review, debugging) | `/engineering` |
| A compact Android release build is needed | `/apk-get` |

## Design and writing

| Situation | Skill |
| --- | --- |
| Interface design, polish or frontend audit | `/impeccable` |
| Uizze's UI playbooks | `/ui-taste` |
| README visuals and SVG assets | `/beautify-github-readme` |
| Writing or pruning a skill, `AGENTS.md` or agent doc | `/writing-for-agents` |
| Orientation in code before reading many files | `/graphify` |
| Ponytail guidance, review, audit, debt or benchmarks | `/ponytail`, `/ponytail-review`,
  `/ponytail-audit`, `/ponytail-debt`, `/ponytail-gain`, `/ponytail-help` |
| Hermes profile setup | `/profile-create` |
| What is open, done or next | `/pending` |

## How to answer

1. Name the one command that fits, then the next concrete step it implies.
2. When two fit, read both `## Boundaries` sections and pick the narrower one.
3. Say plainly when a request needs no skill, or when it needs an owner decision
   rather than a command.
4. This map grants no authority: scope, review gates, publication and live operations
   keep their own rules.

## Boundaries

- Not a dispatcher: it recommends a command, and the user or caller runs it.
- Not a queue or status report; use `/pending` or `/blockers`.
- Not a substitute for the chosen skill's instructions; read that file.

**Done when:** one command is named with its next step, or the request is reported as
needing no skill or an owner decision.
