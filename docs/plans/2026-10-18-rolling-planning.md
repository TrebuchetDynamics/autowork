# Rolling planning: tasks that plan more tasks

Status: Accepted

Accepted by the planner on 2026-10-18 under owner direction ("i want tasks to
sometimes explode in more tasks when ran by autowork. for example `plan_for_me
porting this <project> to flutter`. autowork may assign more tasks after planning to
keep planning and building. like a goal tool"). Every decision below is the planner's
call.

## Rolling planning design

Status: Accepted

**Problem.** A large request ("port this project to Flutter") cannot be planned to the
end up front: the later tasks depend on what the first ones find. Today a plan saves
one batch of tasks; when the batch is done the queue is empty and nothing plans the
next batch, though the goal is not met. Workers cannot plan more, because `TODO.md`,
`goals.json` and the archive are coordinator files a worker may not change.

**Design.** A batch ends with a *planning task*: a TODO entry with `Kind: plan`, whose
`Dependencies:` are the batch's other tasks. It is not dispatched to a code worker.
Once its dependencies are done, the runner hands it to the docs maintainer, which
already runs a model with planning-only writes and lands planning commits. The
maintainer runs [Plan For Me](../../skills/plan-for-me/SKILL.md) on the entry's scope
and the evidence the finished batch left (its reports, the code, the goal's remaining
proof), saves the next batch under the same goal, and, while the goal is not met,
ends that batch with the next planning task. The planning task itself is closed in
the same planning commit. So a goal plans, builds, plans again and builds again
until it is met, without the owner starting each round.

**Bounds.**

- `Plan round: N of M` on each planning task; the next one carries `N+1 of M`. The
  default M is 10. At round M the maintainer saves no further planning task and asks
  the owner in `BLOCKERS.md` whether the goal should continue, with what is left.
- A round that adds no building task ends the chain the same way: planning that
  finds nothing to build is a question, not another round.
- A planning task adds at most 8 tasks. Gaps that need the owner (product choices,
  live authorization, outside inputs) go to `Needs decision` with their one question,
  and the chain carries on with what can be built.
- Planning tasks run one at a time per repository: they all write `TODO.md`.

**Entry point.** Plan For Me and Plan With Me, asked for work too large for one batch,
save the first batch and its closing planning task. A planning task can also be
written by hand.

## Planner's calls

- The maintainer, not a code worker, runs planning tasks: it already owns planning
  writes, so no worker gains access to coordinator files.
- The chain is a dependency, not a new goal field: a planning task depends on its
  batch, so the existing scheduler starts it at the right time, and `goals.json`
  needs no new schema.
- Round and size limits are defaults, not owner requirements; a task may set a
  smaller M. Raising them is the owner's answer to the round-M question.
