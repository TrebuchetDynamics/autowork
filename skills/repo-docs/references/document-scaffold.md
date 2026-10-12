# Document scaffold and ownership

Use this reference when bootstrapping docs, assigning a new document role, or
resolving overlapping documentation. A small wording/link repair needs no scaffold pass.

## Choose the smallest useful structure

Inventory existing document paths and sections before creating anything. Reuse an
equivalent owner regardless of its filename. One document may cover several roles
in a small repository; split only when content, audience or navigation warrants it.
Do not rename existing docs to match the examples or generate empty template files.
The required bootstrap BLOCKERS.md exception remains in the parent skill.

For new substantial documents, start with a short purpose/scope sentence and links
to related owners. Use the section outlines below as prompts, not mandatory empty
headings. Fill them with repository evidence and accepted intent; label real unknowns.
Keep a fact in one authoritative place and link to it elsewhere. Preserve existing
requirement and task IDs. Read project instructions; this scaffold does not authorize
creating or rewriting AGENTS.md or changing repository policy.

## Baseline role templates

| Role / example path | Useful sections | Ownership boundary |
| --- | --- | --- |
| README.md | Purpose; quickstart; usage; tests; documentation links | Entry point, not a copy of every guide |
| docs/product/requirements.md | Users/problem; goals; scope/non-goals; constraints; acceptance; open questions | Accepted intent; distinguish proposals |
| docs/engineering/architecture.md | Current system map; components; boundaries; data flow; source references | Implemented structure; label planned extensions separately |
| docs/engineering/spec.md | Planned behavior; interfaces/data; failures; security; migration/rollout; requirement links | Change contract; link to current architecture instead of duplicating it |
| docs/engineering/test-plan.md | Risks; acceptance checks; environments; existing/planned tests; coverage gaps | Required verification and actual evidence are distinct |
| docs/operations/runbook.md | Prerequisites; run/health; diagnosis; recovery/rollback; backup limits | Supported operational procedures; no invented recovery guarantees |
| CHANGELOG.md | Notable changes grouped by actual version/release convention | Implemented/released changes, not proposed work or audit diaries |

Architecture and spec may share a file with explicit Current and Planned sections.
Link source paths/symbols for structural claims and task IDs for proposed changes.
Do not rewrite accepted requirements merely to match incomplete implementation.

## Work queue and coordination

| Role | Content |
| --- | --- |
| TODO.md | Now, Next, Needs decision; full task bodies with ID, outcome, sources, scope, acceptance/checks, dependencies and ownership |
| goals.json | Synchronized machine index of goals, tasks, priorities, dependencies and status; use the existing schema/helpers |
| BLOCKERS.md | Active/Resolved external inputs under the parent skill's hard-blocker contract |
| Existing archive or todo.archive.md | Completed-task history and substantive receipts; create only when there is history to move |

Preserve the repository's archive path; do not create a second history owner.
Keep progress diaries out of the live task queue. Task creation is not dispatch,
and passing offline tests is not production qualification. Follow the parent skill's
body validation, authority and concurrent-write rules rather than inventing a new schema.

## Conditional documents

Create these only when the trigger applies and substantive supported content exists.
Otherwise link an existing equivalent or record why the role is not applicable.

| Role / example | Trigger | Useful sections |
| --- | --- | --- |
| CONTRIBUTING.md | A contributor workflow needs more detail than README | Development setup; relevant checks; contribution/review process |
| SECURITY.md | Public project needs vulnerability-reporting guidance | Verified reporting channel; disclosure process; supported-version policy if established |
| Threat model | Meaningful trust boundaries, authentication or sensitive data | Assets; trust boundaries; threats; existing mitigations; open risks |
| DESIGN.md | UI consistency needs a shared reference | Visual language; components; interaction/accessibility rules; existing design sources |
| User guide | User journeys exceed README quickstart | Tasks; examples; limitations; troubleshooting |
| API/event contracts | Owned interfaces have consumers | Operations/messages; schemas; auth; errors; compatibility; generated-source authority |
| Data lifecycle guide | Persistent data needs explicit lifecycle rules | Storage; migrations; retention/deletion; backup/restore; established limits |
| Release guide | Packaging/distribution needs repeatable instructions | Build/check/package; versioning; publication; rollback; required authority |
| ADRs | Significant hard-to-reverse architectural decision | Status; context; options; decision; consequences; supersession links |

Do not invent a security contact, support promise, retention period, release history,
or accepted ADR. Record missing decisions without presenting recommendations as policy.
OpenAPI covers owned HTTP APIs; document event/WebSocket payloads separately when needed.
Installation, compatibility, dependencies, updates and removal may warrant separate
guides in plugin/tooling projects. Reuse existing guides before adding another layer.

## Navigation and maintenance

README links to the relevant owners. Add a docs index only when it improves navigation;
do not add one merely because a docs directory exists. Check links/anchors, documented
commands, task references and contradictory current/planned claims. When moving a fact,
update incoming links and preserve decision history. Keep unchanged files byte-identical:
an audit occurrence alone does not justify new timestamps, archive notes or tasks.

Report role-to-path mappings, including combined sections, and actual checks/gaps.
This is a documentation scaffold, not permission to implement features, execute
operational procedures, install tools, commit, push or change schedules.
