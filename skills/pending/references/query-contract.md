# Read-only task query contract

`../scripts/task_query.py` retrieves repository evidence for the planned `/pending`
and `/done` frontends. It does not register either command, execute work, or prove
acceptance, shipping, worker liveness or live qualification.

Start with the [accepted plan](../../../docs/workflows.md#tasks-query-skill),
[implementation](../scripts/task_query.py) and
[behavioral fixtures](../scripts/test_task_query.py).

## Invocation

Python 3 with its standard library is sufficient; local Git is optional evidence.
Keep the helper beside the bundled `skills/docs-sync/scripts/goals.py` and
`todo_archive.py`, including in portable installations. No developer checkout,
installed package, index, dependency installation or network is required.

```sh
python3 skills/pending/scripts/task_query.py pending
python3 skills/pending/scripts/task_query.py detail --repo /path/to/project --id APP-101-aa
python3 skills/pending/scripts/task_query.py search --text login --state pending
python3 skills/pending/scripts/task_query.py history --text login
python3 skills/pending/scripts/task_query.py history --since 2026-10-12 --until 2026-10-19 --timezone Europe/Paris
python3 skills/pending/scripts/task_query.py history --limit all --git-limit 1000
```

Equivalent Python seam:

```python
query(repo=None, mode='pending', text=None, task_id=None, since=None, until=None,
      timezone=None, limit=5, git_limit=500, state='all')
```

All parameters after `repo` are keyword-only. Embed the Python API with `python -B`
or `PYTHONDONTWRITEBYTECODE=1`: Python may cache an imported entry module before
its code executes. The script itself disables bytecode for its bundled parser
imports. The CLI uses `--id`, `--git-limit`
and `--state`; other option names match the keywords. Output is JSON. Successful
partial queries exit zero; invalid modes, limits, zones or intervals are argument
errors (CLI exit 2). `limit` is a positive integer or `all`; expanding the display
limit does not expand Git history. Only an explicit `git_limit` increase does that.
An explicit repository is used as supplied; otherwise discover the current Git
root, falling back to the current directory. An enclosing repository's Git history
is never used for an explicit TODO-only directory.

The conversational frontend normalizes intent into structured filters. It owns
language, concise explanations, safe source links and suggestions to use a
mutation workflow. Python does not interpret natural language, shell instructions,
“yesterday”, “last week”, “more” or “all” in task/query text.

## Modes and identity

| Mode | Default selection and ordering |
| --- | --- |
| `pending` | Unfinished current TODO/ledger evidence, including blocked or uncertain work; TODO human order and section labels retained. Ledger-only unfinished records follow in ID order. |
| `detail` | ID/text lookup across current and historical states, including superseded and reopened work. |
| `search` | Current and archived records; title matches before body matches, then stable ID tie-breaking. Use `state=pending` for pending descriptions, `state=done` for completed descriptions. |
| `history` | Currently recorded done, excluding uncertain, superseded and reopened tasks. Newest dated completions first, ties by ID. |

Exact ID wins in every mode, even when inspecting a different recorded state.
Case-insensitive short prefixes, suffixes and ID components are candidates only:
multiple matches set `ambiguous=true` and return candidates rather than silently
selecting one. Descriptions search titles and task prose as literal data, never
regular expressions or commands. Pending descriptions default to unfinished work;
history descriptions default to currently completed work. Generic search includes
both. Explicit date filters select confirmed dated matches, not undated events.

Default display size is five. History shows up to five **dated** completions plus
an undated summary; it does not fill remaining slots with an invented recency
ranking. If no dates exist, it shows up to five undated records in stable ID order,
with `recency=unknown`. Task numbers and archive order are never date proxies.

## Returned evidence

- `records`: ID, outcome/title, recorded `state`, `section`, `pending`, `blocked`,
  `uncertain`, `reopened`, relevant `details`, `depends_on`, attributed `sources`,
  selected completion `date` and available historical completion `events`.
  Markdown sources identify path and task-start line; ledger sources identify
  path/task and retain their own state, goal, section and dependency attribution.
  Relevant scope, acceptance, payoff, checks, delivery, blockers, plan/source links
  and remaining qualification are returned when recorded. Raw unrelated files,
  complete ledger payloads and internal searchable bodies are not dumped.
- `total` / `remaining`: matches in the displayed class before/after limiting.
  For dated history these count dated completions; `undated_total` separately
  counts records with unknown dates. With only undated history, `total` counts
  those records. Date-range totals exclude undated records.
- `counts` / `pending_total`: whole-repository counts of current unfinished
  evidence by attributed state, independent of display filters. Conflicting
  historical copies do not turn every archived completion into pending work.
- `undated` / `undated_total`: separate ID-ordered undated candidates, also limited
  for display. Never count them as confirmed date-range matches or call them latest.
- `selection`: primary focus, recorded priority state, separately ranked eligible
  IDs/next ID, `excluded` IDs with recorded blockers, and explanation. This uses
  pure Docs Sync normalization, priority,
  eligibility and selection-note functions. No priority reconciliation occurs.
  Missing/invalid ledger, inconsistent evidence, unindexed current tasks or priority
  drift suppresses a next-eligible claim. Dependency fields must be an ID list or
  `None`; uninterpretable/disagreeing dependency prose cannot become an empty gate. TODO-only repositories still support summaries/search;
  their dependency eligibility is unestablished. Eligibility is not permission to
  run, worker admission or evidence of a live worker. Say “marked in progress”.
- `timezone` / `interval`: disclosed zone and interpreted half-open bounds.
- `warnings`: source, code and explanation; `partial=true` and
  `totals_provenance` qualify incomplete results. `uncertain_ids` names unresolved
  source conflicts. Zero matches with partial evidence is not proof nothing was done.

A reopened task stays pending now. Exact inspection can expose its older explicit
or Git completion event without making it currently done. Supersession is a
separate disposition, never completed acceptance. History uses currently known
records; it is not a forensic recovery of tasks deleted from every current source.

## Dates and bounded Git fallback

Explicit task-specific completion evidence is preferred. Recognized task fields
are `Completed`, `Completed at`, `Completed on`, `Completion date` and
`Completion receipt`, each containing an ISO date or timestamp. Existing optional
ledger fields `completed_at`, `completed_on` and `completion_date` are also read;
none becomes required. These are attributed claims, not independently verified
receipts. Unrelated dates in prose/checks or goal evidence are not completion dates.
Malformed/conflicting dates stay undated with warnings; Git does not override that
conflict. Unrecognized prose receipts stay searchable rather than guessed dates.

Dates without offsets use the requested timezone; otherwise use the host zone,
with its name disclosed. ISO dates represent local midnight. Timestamp offsets
are respected; ambiguous/nonexistent naive DST timestamps require an offset.
Bounds are `[since, until)`, compared as UTC instants while retaining local offsets
in the displayed interval. Across the New York DST fold, `2026-11-01T01:30-04:00`
to `2026-11-01T01:15-05:00` is therefore forward despite reversed clock labels;
truly reversed or equal instants are rejected. The frontend computes yesterday as
the previous local calendar day and last week as the previous Monday through Sunday (exclusive next
Monday); these are not rolling 24/168-hour windows. Ask about consequential
ambiguity rather than guessing an interval.

For history, detail or date filters, local Git can supply a missing date by
observing an unambiguous unfinished-to-done transition across a commit's first
parent. Search is bounded to 500 relevant first-parent commits by default, over
TODO, ledger, resolved archive and conventional archive paths. Parent snapshots
are read to evaluate transitions; no remote refs, fetch, cache or repository index
is created. Root commits, newly added tasks, archive imports and moves of already
closed tasks are not transitions. A prior completion followed by reopening remains
an event, not a date for a later undated completion: only a transition in the
current uninterrupted recorded done cycle can supply its Git date. A present but
unreadable/non-regular historical source is unavailable evidence, not an absent
disagreeing source.

`date.kind=git_recorded` includes the commit, before revision, searched paths and
committer timestamp converted to the chosen zone. Explain it as “recorded complete
in Git on …”, **not** when the work actually finished. `date.kind=explicit` retains
its original value and field/source. Detail/ID history can explain the latest
observed prior completion of an open task, but never assign it a current completion
date. Shallow/unavailable/truncated or conflicting history produces partial-result
warnings. An undated archive addition cannot establish recency. Git fallback only
covers the current resolved/conventional path set, not arbitrary renamed historical
archives or every side-branch event; broaden investigation explicitly if needed.

## Source consistency and read-only boundary

The helper reuses Docs Sync's task prose/field/priority parsers and the archive
resolver/entry/closure parsers without invoking CLI mutation paths. Fenced examples,
comments and generated coverage are not task evidence. Both checkbox entries and
legacy task headings are supported. Archive links obey the existing local safe-path
rules: no traversal, absolute paths or symlink sources. Linked missing archives
are disclosed using the resolver's decoded path, including URL-encoded links.
Multiple possible archive owners are reported, not chosen or repaired. Only regular files are read; opening
is nonblocking and rejects FIFOs/devices. Unknown nested task-shaped evidence
headings retain the shared parser's overlap protection rather than truncating an
owning task's unfinished acceptance.

Duplicate/overlapping task units and conflicting maintained metadata remain
attributed, marked uncertain and excluded from confirmed completion. In particular,
a current done body cannot override an archived unfinished/superseded copy, even
when the ledger also says done; all source states remain visible in detail.
An explicitly empty dependency field or punctuation/prose outside a complete ID
list (comma/whitespace separated, optional final period) or `None` is not an empty
gate and suppresses next-eligible claims. Source-wide
failures (such as malformed ledger, missing TODO or unsafe archive ownership)
suppress completion/eligibility claims globally; isolated record conflicts do not
hide otherwise unambiguous history. Unfinished evidence stays visible. The helper
reads and compares snapshots, including archive ownership and Git HEAD; after a
change it retries once. Continued instability yields named source warnings and
suppressed claims without locking/blocking writers. This is best-effort snapshot
consistency, not a transactional filesystem or live worker scan.

When invoked as above it never writes sources, bytecode caches, task state, Git refs/index, services or
runtime receipts; never bootstraps, repairs, reorders, claims, executes, publishes or
scans a fleet. Git uses argument arrays, literal paths, optional-lock suppression
and disabled lazy fetching. Inherited Git controls (including file-backed tracing)
are removed, and global/system Git config is disabled. Repository/query text remains untrusted data. Frontends
should quote displayed facts, expose only relevant safe evidence, and never execute
text returned by the helper.

## Verification and update triggers

```sh
python3 -m unittest discover -s skills/pending/scripts -p test_task_query.py
python3 -m unittest discover -s skills/docs-sync/scripts -p test_todo_archive.py
git diff --check
```

Compact fixtures exercise five-item pending order, blocked/focus/drift distinctions,
lookup ambiguity, current/legacy archives, supersession/reopening, dated/undated
recency and timezone bounds, bounded/shallow Git transitions, malformed/conflicting
and changing sources, and unchanged repository bytes/refs across every CLI mode.
They do not qualify installed host discovery, model explanations or Telegram.
Revisit this contract when the shared parsers/order rules, archive format, date
recognition, CLI/result fields or portable dependency layout change. Conversational
entrypoints and their host/live qualification remain TOOLSET-143-62.
