# Shared skill contract

Use the [ASD-STE100 and project language rules](COMMUNICATION.md) for user-facing text.
Read the target project's glossary map and glossary when available.

Apply the [shared Ponytail method](PONYTAIL.md) within each workflow's authority.
Reuse existing code and artifact owners; choose the smallest complete result,
without weakening accepted behavior, safety or verification.

User instructions and repository rules define the authorized scope. Read the
relevant instructions, current source, tests and existing documentation before
changing their owners. Keep proposals distinct from accepted requirements and
implemented behavior. An explicit skill invocation authorizes its documented default
actions within the user's scope: planning commands may save docs/tasks, and Autowork
may implement, test and commit locally. Loading a supporting skill adds no authority.
Installation, publication, third-party contact and destructive actions require their
own authorization; specific no-write/no-commit restrictions always take precedence.

Inspect status and preserve pre-existing edits, untracked files and live ownership.
Use [worktree isolation](WORKTREE-ISOLATION.md) when a separate writing checkout
is required. Do not reset, clean, stage or overwrite unrelated work. Keep secrets
and generated scratch out of deliverables.

Run the checks that discriminate the claimed change. Record actual commands,
results and the source they exercised; label missing coverage NOT_CHECKED.
Static policy checks and offline fixtures do not prove model adherence, native
worker execution, provider behavior or delivery. Review scoped diffs and links,
and reconcile affected documentation and task state without inventing evidence.
Report changed artifacts, verified behavior, limitations and remaining work.

Resolve helper paths from the actual loaded skill directory, not an assumed
Hermes home. Sibling bundled skills and this support directory retain their
relative layout. Quote absolute paths and repository arguments in shell commands.
Edit task and goal records through `autowork tasks` ([work center](TODO-WORKCENTER.md)).
See [plan handoff](PLAN-HANDOFF.md) for accepted backlog boundaries.
