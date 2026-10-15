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

### Optional role manifest

A repository may record its role mapping in `docs/roles.json` so coverage and
integrity are checked by the bundled `scripts/docs.py`, not only by reading:

```json
{"version": 1, "roles": {
  "readme": {"status": "maintained", "path": "README.md", "covers": ["src"], "verified_at": "fb2798f"},
  "architecture": {"status": "maintained", "path": "docs/design.md#current-system"},
  "runbook": {"status": "not_applicable", "reason": "No deployed service."}
}}
```

Statuses are the role outcomes reported by the parent skill. Mapped roles need a
repository-relative `path` (optionally `#anchor`); not-applicable roles need a
`reason` and no path. `covers` lists source paths the role documents and
`verified_at` the commit at which it was last verified. Run `docs.py validate <repo>`
for shape and `docs.py check <repo>` to also check mapped documents and anchors,
local and reference-style links, `python`/`python3`/`sh`/`bash`/`node` script paths in
inline code (including after a relative `cd`), covered paths and
unmapped baseline roles (the selected
[profile](#repository-type-profiles)'s, otherwise README, PRD, architecture, spec,
test-plan, runbook and CHANGELOG). Both are read-only, never fetch URLs and report `no manifest` when none
exists. Create a manifest only when the repository adopts one; never to fill a gap.

`docs.py stale <repo>` lists roles whose `covers` paths changed in commits after
their `verified_at` commit, and reports a missing, unknown or non-ancestor commit as
unverifiable rather than fresh. Use it to scope a Maintain pass; after actually
verifying a role, set its `verified_at` to the commit you verified against. It reads
Git history only and ignores inherited `GIT_*` overrides.

### Repository-type profiles

A manifest may set `"profile"` to choose which roles `check` treats as baseline, so
applicability is not re-decided on every pass. Without a profile the baseline is the
service set. A profile names roles that must be mapped or recorded as not applicable;
it never requires an empty document, and other roles stay conditional. Choose the
profile that matches what the repository ships; `docs.py profiles` prints this table.

| Profile | Ships | Baseline roles |
| --- | --- | --- |
| `service` | A deployed service or API | `readme`, `prd`, `architecture`, `spec`, `test-plan`, `runbook`, `changelog` |
| `library` | A package other code imports | `readme`, `reference`, `architecture`, `test-plan`, `changelog` |
| `cli-plugin` | A command-line tool, plugin or skill bundle | `readme`, `reference`, `install-upgrade`, `troubleshooting`, `architecture`, `test-plan`, `changelog` |
| `application` | An end-user web, mobile or desktop app | `readme`, `prd`, `architecture`, `spec`, `test-plan`, `user-guide`, `troubleshooting`, `changelog` |
| `infrastructure` | Deployment, provisioning or platform configuration | `readme`, `architecture`, `runbook`, `test-plan`, `changelog` |

Roles beyond the baseline table above:

| Role | Useful sections | Ownership boundary |
| --- | --- | --- |
| `reference` | Commands, options, configuration keys, environment variables, exit codes | Exact current interface; generate from source and check drift where possible |
| `install-upgrade` | Supported platforms; install; upgrade/migration; compatibility; removal | Supported procedures only; README keeps the shortest path |
| `troubleshooting` | Symptom; likely cause; check; fix; when to escalate | User-side diagnosis; operator recovery stays in the runbook |
| `user-guide` | Tasks; examples; limitations | User journeys beyond the README quickstart |
| `glossary` | Term; meaning; not-to-be-confused-with; source | Project language shared by docs and planning (for example CONTEXT.md) |

Architecture and spec may share a file with explicit Current and Planned sections.
Link source paths/symbols for structural claims and task IDs for proposed changes.
Do not rewrite accepted requirements merely to match incomplete implementation.

Recorded branch evidence, an accepted design or an approved isolated artifact proves
neither canonical inclusion nor deployment. Check current source, manifests, schema
inputs, generators and drift-check entrypoints; add a missing inclusion prerequisite
to the existing owning task rather than fabricating files or a parallel plan. Keep
Proposed designs Proposed with a source-inspection notice. Withdraw unsupported
recovery recipes in place with a dated notice linking the correction or gap. Derive
guard commands from current manifests, not guessed script names.

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

## First task-index initialization

Use `goals.py init`, not a manually seeded consumer `goals.json`. The input is the
existing version-1 schema, not a second tracker: provide goal IDs/titles/local
accepted sources/status/task membership, and task IDs/goals/titles/status/sections/
dependencies. Optional priorities, evidence, milestone focus and extension metadata
are retained. An initialized goal is not marked met without existing executed
passing evidence and completed work. Do not fabricate those records.

For an empty Git repository, include actual accepted intent in the task Markdown,
with a source heading like this (only when the owner accepted this scope):

```markdown
# Startup slice

Status: Accepted

The application must start successfully; verify startup with the project test.
```

Save the corresponding input as `intent.json` (it need not live inside the consumer):

```json
{
  "version": 1,
  "goals": [{
    "id": "STARTUP", "title": "Application starts", "source": "TODO.md#startup-slice",
    "status": "unmet", "priority": 1, "tasks": ["STARTUP-01"]
  }],
  "tasks": [{
    "id": "STARTUP-01", "goal": "STARTUP", "title": "Verify startup",
    "status": "open", "section": "Now", "depends_on": []
  }]
}
```

Save complete bodies as `tasks.md`, substituting the real owner, scope and checks:

```markdown
# TODO

## Startup slice

Status: Accepted

The application must start successfully; verify startup with the project test.

## Now

- [ ] STARTUP-01 — Verify startup
  Goal: STARTUP — Confirm the application can start.
  Sources: [Accepted startup slice](#startup-slice)
  Scope: Add the startup check; no deployment or runtime configuration changes.
  Acceptance: The project's startup test passes; record its exact command/result.
  Dependencies: None
  Ownership: Project maintainer
  Status: open
```

Run against the actual consumer root (replace absolute paths with yours):

```sh
python3 /absolute/toolset/skills/docs-sync/scripts/goals.py init /absolute/consumer --intent /absolute/intent.json --todo-file /absolute/tasks.md
python3 /absolute/toolset/skills/docs-sync/scripts/goals.py fmt /absolute/consumer
python3 /absolute/toolset/skills/docs-sync/scripts/goals.py validate /absolute/consumer
python3 /absolute/toolset/skills/docs-sync/scripts/goals.py render /absolute/consumer
python3 /absolute/toolset/skills/docs-sync/scripts/goals.py backlog-check /absolute/consumer --plan TODO.md#startup-slice --tasks STARTUP-01
```

Expected: `validate` prints `ok`; the consumer check returns
`ready_for_autowork`, exit 0, for this dependency-ready accepted fixture. The check
is read-only and leaves live ownership unknown; it neither authorizes nor starts
execution. Ineligible accepted dependencies can initialize successfully but remain
ineligible on the subsequent consumer check. Non-Git fixtures can initialize, but
they are not consumer authority and cannot pass the readiness gate.

For an existing TODO-only repository, retain its full bodies, IDs and sections;
author the matching intent input and omit `--todo-file`. An accepted source may be
an existing heading in TODO itself. Missing source/acceptance/body/ownership context,
duplicate bodies or executable IDs absent from intent fail before content writes.
Before `init`, compare each body with its intent object: ID, goal, section, checkbox,
exact Status token and task dependencies. Keep explanatory status text in a separate
field, use `Ownership:` (not an `Owner` alias), keep external evidence gates out of
dependency IDs, and link Sources to the goal's actual accepted heading that governs
the task. Accepting research or bookkeeping does not accept a future production
outcome; keep unaccepted proposals in TODO rather than relabeling sources to pass.
An explicit body `Status:` must match the input status; do not claim/reopen a task
to obtain readiness. No source or approval is inferred from TODO prose.

`init` preserves existing TODO and archive bytes. It preflights coverage rendering
but leaves rendering/archival to the explicit commands above. If `--todo-file` is
supplied when TODO exists, the input must byte-match it; after rendering, omit that
flag for repeat initialization. Repeating with unchanged intent and reconciled
TODO is a no-write success, even when the existing ledger uses different whitespace.
Conflicting/incompatible ledgers, missing TODO beside an existing index, symlinks,
unsafe references or stale revisions are refused, never overwritten or merged.
Reconcile existing projects through the canonical maintenance owner instead.

The command shares the existing lock, path/authority policy and optional
`--expected-revision`/`--canonical-repo` controls. Linked workers can maintain
branch-local task files and return scoped changes for normal integration; explicit
canonical targeting does not bypass ownership. All inputs and referenced
sources are checked before content writes. A failed ledger replacement rolls back
only an exact newly created TODO; pre-existing TODO is never removed. This is local
cooperative coordination, not a crash-atomic multi-file transaction or protection
against a hostile direct writer. See [concurrent maintenance](concurrent-maintenance.md).

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
