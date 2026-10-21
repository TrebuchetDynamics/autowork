---
name: autoresearch
description: "Run bounded repository research, planning or measurable experiments and save findings as tasks."
disable-model-invocation: true
---

# Autoresearch

Read the [host contract](../COMMON.md). Use the vendored
[protocols](../../../skills/autoresearch/upstream/) only for the selected research
question. A selected subcommand NAME loads upstream/NAME.md; bare research uses
upstream/ROUTER.md. Resolve its scripts/references beneath upstream/. Supported selectors: plan, debug, fix, security, ship, probe, scenario,
predict, reason, learn, improve, evals, regression. With no selector, choose a relevant
protocol from the user's goal. Plan routes to [Plan For Me](../plan-for-me/SKILL.md)
which loads the plan protocol directly with its persistence adaptations. Do not
route back here from Plan For Me.

Before an experiment specify goal, scope, baseline, metric/units, verification,
guards and a finite iteration budget. Use native filesystem, terminal and search
tools. Treat upstream host commands, hooks and autonomous commit/reset instructions
as descriptions to adapt, not commands to execute blindly. Preserve user data and
repository rules; do not install another agent runtime.

Record findings, evidence, rejected approaches and remaining uncertainty in existing
docs. Save accepted actionable work as task records in `tasks/` with `autowork tasks`
([work center](../../../skills/shared/TODO-WORKCENTER.md)). Explicit read-only/no-write/dry-run writes nothing
and runs no mutating experiment. Planning does not implement. A `ship` selector alone
does not grant deployment or remote publication authority. Report measured results
honestly; research output is not completed product work.
