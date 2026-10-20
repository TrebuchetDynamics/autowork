#!/usr/bin/env python3
"""goals.json: the machine-readable goal list that docs-sync writes and autowork reads.

TODO.md stays the human view; its `Goal coverage` table is rendered from this file.
Agents change goals.json only through these commands, never by hand-editing JSON.

  goals.py init <repo> --intent JSON [--todo-file MARKDOWN]
                                                initialize from accepted intent and full task bodies; never overwrite
  goals.py propose <repo> --intent JSON [--todo-file MARKDOWN]
                                                first index without accepted sources: check as init would,
                                                save docs/tasks/proposed-goals.json, ask the owner in BLOCKERS.md
  goals.py accept <repo>                         on the owner's yes: mark the proposal's sources Accepted and init
  goals.py validate <repo>                       structural + evidence-rule check (exit 1 on errors)
  goals.py fmt <repo>                            canonical byte-stable rewrite (applies the "met" rule)
  goals.py next <repo> [--json]                  next eligible open task (dependencies satisfied);
                                                exit 3 with a PRIORITY_DRIFT report when TODO.md order changed
  goals.py reorder <repo>                        record TODO.md task order as the human priority (goals.json only)
  goals.py move <repo> <task> up|down            move an open task among its TODO.md group's open tasks
  goals.py place <repo> <task> <section>         move an open task to Now, Next or Needs decision (TODO.md and ledger)
  goals.py field <repo> <task> <label> <value>   set one single-line field of an open task's entry
                                                (TODO.md only; reorder records the new order)
  goals.py bootstrap-order <repo> [--dry-run]    one-time move of legacy priority into TODO.md order;
                                                apply requires --expected-revision from the dry run
  goals.py focus <repo> <GOAL>                   set the primary milestone without changing priorities
  goals.py focus <repo> --json                   read primary milestone without writing
  goals.py focus <repo> --clear                  remove focus and restore legacy selection order
  goals.py redact <repo> --replacements-file JSON --archive-dir PRIVATE
                                                redact historical refs/sources and render under one lock
  goals.py revision <repo>                       content token for goals.json and TODO.md
  goals.py merge-driver goals|todo|archive BASE OURS THEIRS
                                                Git low-level driver; writes OURS only, exits 1 on conflict
  goals.py merge-finalize <repo>                 rebuild order and coverage before committing a resolved merge
  goals.py render <repo>                         rewrite TODO.md's goal-coverage block from goals.json
  goals.py archive <repo> [--verified-tasks T1,T2]
                                                move closed task bodies to TODO.archive.md; keep ledger history
  goals.py backlog-check <repo> --plan path#heading --tasks T1,T2 [--receipt prior.json]
                                                read-only consumer-bound completion receipt (0 ready, 1 draft, 2 ineligible)
  Every command accepts --expected-revision TOKEN and --canonical-repo CHECKOUT.
  Explicit --canonical-repo targets another verified checkout of the same Git repository.
  Commands target the requested checkout; legacy native authority config is ignored.
  CLI operations lock the common Git directory (or a local no-Git fixture) before load.
  goals.py task <repo> <TASK> <open|in_progress|done>
  goals.py supersede <repo> <TASK> --by T1,T2 --reason TEXT
                                                retire without acceptance; render archives unchecked original history
  goals.py section <repo> <TASK> <Now|Next|Needs decision>
  goals.py new-id <repo> [--prefix P]           print an unused ID such as P-084-a7 (next number + 2-hex hash)
  goals.py add-task <repo> [TASK] --goal <GOAL> --title <text> [--section Now|Next|Needs decision] [--depends-on T1,T2]
                                                omit TASK to allocate one with new-id rules
  goals.py evidence <repo> <GOAL> --kind executed|inspection --ref <cmd/path> --result pass|fail [--ran-at ISO]

Rule (the met rule): a goal is `met` only with executed+pass evidence and all tasks done.
Fmt downgrades missing evidence to `unverified`, or reopens unfinished work as `partial`.
Superseded tasks never satisfy dependencies or the all-done met rule, even when
their successors finish. Explicit goal/dependency reconciliation remains required;
supersession is a disposition, not completion evidence.
Only version 1 ledgers are supported. Incompatible field shapes and duplicate JSON
keys are rejected before writing; formatting preserves additional metadata.
Next applies the same normalization in memory, then rejects invalid ledger state;
completed goals awaiting evidence remain dependency gates, not runnable work.
Optional `primary_milestone` names one existing goal. Its eligible tasks sort first,
even in Next; all eligible fallback tasks remain available after them in next --json.
"""
import argparse
from contextvars import ContextVar
from functools import partial
from types import SimpleNamespace
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Private spec loaders do not necessarily put this scripts directory on sys.path.
_scripts = str(Path(__file__).resolve().parent)
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

# Compatibility exports: moved names used by this CLI and import-goals callers.
# Concerns depend only on earlier layers (ledger -> TODO -> queue -> backlog),
# never on this facade or its private transaction state.
from goals_backlog import (
    accept, backlog_check, initialize, local_reference, plan_acceptance_error,
    propose, reference_key,
)
from goals_ledger import (
    KINDS, NEW_ID_SOURCES, PRIORITY_SCHEMA, RESULTS, SECTIONS,
    TASK_ID, TASK_STATUS, atomic_write, backlog_authority, checked_bytes, coordination,
    dump, errors, git_identity, load, new_task_id,
    normalize, parse_ledger, path_of, revision, shape_errors,
)
from goals_queue import (
    PriorityDrift, active_task_ids, bootstrap_plan, eligible, priority_status,
    queue, reconcile_order, selection_notes,
)
from goals_todo import (
    BEGIN, CHECK_LABELS, END, TASK_MARK, archive_tasks,
    deferred_tasks, heading_rows, markdown_prose, move_block, place_block,
    render, render_text, set_field, task_blocks, task_bodies,
    task_checks, task_fields, task_prose, todo_text,
)


TRANSACTION: ContextVar[tuple[Path, str] | None] = ContextVar('goals_transaction', default=None)


def redact(repo, data, replacements_file, archive_dir):
    """Redact historical metadata, preserving original bytes outside the repo.

    This uses the existing cooperative lock/stale guard, not a crash-atomic
    two-file transaction or protection against writers ignoring the lock.
    """
    repo = Path(repo)
    replacements = json.loads(checked_bytes(Path(replacements_file)))
    if not isinstance(replacements, dict) or not replacements or any(
            not isinstance(k, str) or not Path(k).is_absolute()
            or not isinstance(v, str) or not v or Path(v).is_absolute()
            for k, v in replacements.items()):
        sys.exit('replacements must map absolute literal prefixes to nonempty portable placeholders')
    if any(prefix in value for prefix in replacements for value in replacements.values()):
        sys.exit('portable placeholders must not contain replacement prefixes')
    archive = Path(archive_dir).resolve()
    if archive == repo or repo in archive.parents:
        sys.exit('archive directory must be outside repository')
    # One pass, longest literal first: overlapping mappings never cascade.
    pattern = re.compile('|'.join(re.escape(k) for k in sorted(replacements, key=len, reverse=True)))
    changed = False
    for goal in data['goals']:
        source = goal.get('source')
        if isinstance(source, str):
            new = pattern.sub(lambda m: replacements[m.group()], source)
            changed |= new != source
            goal['source'] = new
        for entry in goal.get('evidence', []):
            ref = entry.get('ref')
            if isinstance(ref, str):
                new = pattern.sub(lambda m: replacements[m.group()], ref)
                if new != ref:
                    entry['ref'] = new
                    entry['redacted'] = True
                    changed = True
    if not changed:
        print('ok no redaction needed'); return
    # Validate the second write before changing the ledger. A malformed TODO
    # must not leave a partially redacted pair that becomes a no-op on retry.
    render_text(repo, data)
    originals = {n: checked_bytes(repo / n) for n in ('goals.json', 'TODO.md')}
    token = TRANSACTION.get()[1]
    destination = archive / token
    if destination.is_symlink():
        sys.exit('refusing symlink archive revision directory')
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    hashes = {}
    for name, blob in originals.items():
        hashes[name] = hashlib.sha256(blob).hexdigest() if blob is not None else None
        path = destination / name
        existing = checked_bytes(path)
        if existing is not None and existing != blob:
            sys.exit(f'archive mismatch: {path}; no write')
        if blob is not None:
            if existing is None:
                atomic_write(path, blob.decode('utf-8'))
            if checked_bytes(path) != blob:
                sys.exit(f'archive verification failed: {path}; no write')
    manifest = json.dumps({'revision': token, 'sha256': hashes}, indent=2, sort_keys=True) + '\n'
    path = destination / 'manifest.json'
    existing = checked_bytes(path)
    if existing is not None and existing != manifest.encode():
        sys.exit(f'archive mismatch: {path}; no write')
    atomic_write(path, manifest)
    if checked_bytes(path) != manifest.encode():
        sys.exit('archive manifest verification failed; no write')
    # Do not normalize: redaction must not change status, ordering or other metadata.
    output = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    atomic_write(path_of(repo), output)
    # Advance only to our exact expected bytes, never bless an intervening edit.
    digest = hashlib.sha256()
    for name, blob in (('goals.json', output.encode()), ('TODO.md', originals['TODO.md'])):
        digest.update(name.encode() + b'\0')
        digest.update(b'missing\0' if blob is None else str(len(blob)).encode() + b'\0' + blob)
    TRANSACTION.set((repo, digest.hexdigest()))
    render(repo, data, archive=False)
    print(f'ok redacted historical metadata; originals archived at {destination}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    init = sub.add_parser('init', help='create a version-1 index from accepted intent without overwriting existing state')
    init.add_argument('repo')
    init.add_argument('--intent', required=True, help='JSON file using the existing version-1 goals/tasks schema')
    init.add_argument('--todo-file', help='complete Markdown bodies when TODO.md is absent; must byte-match if it exists')
    pr = sub.add_parser('propose', help='first index without accepted sources: save the draft and ask the owner once')
    pr.add_argument('repo')
    pr.add_argument('--intent', required=True, help='version-1 goals/tasks JSON, as init takes it')
    pr.add_argument('--todo-file', help='complete Markdown bodies when TODO.md is absent')
    sub.add_parser('accept', help="the owner accepted the proposal: mark its sources Accepted and initialize").add_argument('repo')
    md = sub.add_parser('merge-driver', help='Git low-level driver; writes OURS only')
    md.add_argument('kind', choices=('goals', 'todo', 'archive'))
    md.add_argument('ancestor'); md.add_argument('ours'); md.add_argument('theirs')
    for name in ('validate', 'fmt', 'render', 'revision', 'merge-finalize', 'merge-attributes'):
        sub.add_parser(name).add_argument('repo')
    ar = sub.add_parser('archive'); ar.add_argument('repo')
    ar.add_argument('--verified-tasks', default='', help='explicitly verified closed IDs in a TODO-only repository')
    n = sub.add_parser('next'); n.add_argument('repo'); n.add_argument('--json', action='store_true')
    sub.add_parser('reorder', help='record TODO.md task order as the human priority (writes goals.json only)').add_argument('repo')
    bo = sub.add_parser('bootstrap-order', help='one-time migration of legacy priority into TODO.md order')
    bo.add_argument('repo'); bo.add_argument('--dry-run', action='store_true', help='report every proposed move; write nothing')
    f = sub.add_parser('focus'); f.add_argument('repo'); f.add_argument('goal', nargs='?')
    f.add_argument('--clear', action='store_true', help='remove primary milestone focus')
    f.add_argument('--json', action='store_true', help='read primary milestone without writing')
    t = sub.add_parser('task'); t.add_argument('repo'); t.add_argument('task'); t.add_argument('status', choices=[s for s in TASK_STATUS if s != 'superseded'])
    sup = sub.add_parser('supersede'); sup.add_argument('repo'); sup.add_argument('task')
    sup.add_argument('--by', required=True, help='comma-separated existing successor task IDs')
    sup.add_argument('--reason', required=True, help='accepted disposition, never passing evidence')
    mv = sub.add_parser('move', help='move an open task up or down among the open tasks of its TODO.md group')
    mv.add_argument('repo'); mv.add_argument('task'); mv.add_argument('direction', choices=('up', 'down'))
    s2 = sub.add_parser('section'); s2.add_argument('repo'); s2.add_argument('task')
    s2.add_argument('section', choices=[s for s in SECTIONS if s not in ('Done', 'Superseded')])
    ni = sub.add_parser('new-id'); ni.add_argument('repo')
    ni.add_argument('--prefix', help='ID prefix (default: the ledger\'s most common one)')
    n2 = sub.add_parser('add-task'); n2.add_argument('repo'); n2.add_argument('task', nargs='?', help='omit to allocate a new hashed ID')
    n2.add_argument('--prefix', help='prefix for an allocated ID (default: the ledger\'s most common one)')
    n2.add_argument('--goal', required=True); n2.add_argument('--title', required=True)
    n2.add_argument('--section', default='Next', choices=[s for s in SECTIONS if s not in ('Done', 'Superseded')])
    n2.add_argument('--depends-on', default='')
    n2.add_argument('--todo', action='store_true', help='also write its TODO.md entry at the top of its section')
    for flag in ('--short', '--scope', '--acceptance', '--checks'):
        n2.add_argument(flag, help='with --todo: that field of the entry (--short is required, at most 40 characters)')
    fd = sub.add_parser('field', help="set one single-line field of an open task's TODO.md entry (an owner answer)")
    fd.add_argument('repo'); fd.add_argument('task'); fd.add_argument('label'); fd.add_argument('value')
    pl = sub.add_parser('place', help="move an open task's TODO.md entry and ledger section to Now, Next or Needs decision")
    pl.add_argument('repo'); pl.add_argument('task'); pl.add_argument('section', choices=('Now', 'Next', 'Needs decision'))
    r = sub.add_parser('redact'); r.add_argument('repo')
    r.add_argument('--replacements-file', required=True, help='JSON absolute literal prefix to portable placeholder map')
    r.add_argument('--archive-dir', required=True, help='private original-byte archive outside repository')
    e = sub.add_parser('evidence'); e.add_argument('repo'); e.add_argument('goal')
    e.add_argument('--kind', choices=KINDS, required=True); e.add_argument('--ref', required=True)
    e.add_argument('--result', choices=RESULTS, required=True); e.add_argument('--ran-at', default='')
    e.add_argument('--task', help='completed task whose archive owns this closeout evidence')
    e.add_argument('--summary', help='short coverage summary (at most 80 characters); exact ref stays in ledger')
    b = sub.add_parser('backlog-check'); b.add_argument('repo')
    b.add_argument('--plan', required=True, help='accepted repo-relative path#heading')
    b.add_argument('--tasks', required=True, help='existing comma-separated task IDs')
    b.add_argument('--receipt', help='prior JSON stdout receipt to recheck for staleness')
    pl = sub.add_parser('plan-lint', help='read-only lint of TODO.md task contracts before dispatch'); pl.add_argument('repo')
    pl.add_argument('--tasks', default='', help='comma-separated task IDs (default: open Now/Next tasks)')
    pl.add_argument('--json', action='store_true'); pl.add_argument('--strict', action='store_true', help='exit 1 on warnings too')
    for parser in sub.choices.values():
        parser.add_argument('--expected-revision', help='refuse if goals.json or TODO.md changed since revision')
        parser.add_argument('--canonical-repo', help='explicit target checkout of the same Git repository (default: requested repo)')
    a = ap.parse_args()
    if a.cmd == 'merge-driver':
        from planning_merge import driver
        sys.exit(driver(a.kind, a.ancestor, a.ours, a.theirs))
    if a.cmd == 'plan-lint':  # read-only: no lock or revision guard needed
        import plan_lint
        sys.exit(plan_lint.report(a.repo, plan_lint.task_list(a.tasks), as_json=a.json, strict=a.strict))
    if a.cmd == 'focus' and sum((a.clear, a.goal is not None, a.json)) != 1:
        f.error('provide exactly one of GOAL, --clear or --json')
    with coordination(a.repo, a.canonical_repo) as repo:
        a.repo = str(repo)
        current = revision(repo)
        if a.expected_revision is not None and a.expected_revision != current:
            sys.exit(f'stale revision: expected {a.expected_revision}, current {current}; no write')
        if a.cmd == 'revision':
            print(current); return
        if a.cmd == 'backlog-check':
            sys.exit(backlog_check(a))
        execute(a)


SHORT_LIMIT = 40  # `Short:` fits a task list's column (the autowork TUI's Tasks window)


def short_errors(repo, data):
    """Open tasks whose `Short:` title is longer than SHORT_LIMIT characters or spans lines."""
    text = checked_bytes(Path(repo) / 'TODO.md')
    if text is None:
        return []
    bodies = task_bodies(text.decode('utf-8'))
    found = []
    for task in data.get('tasks') or []:
        if task.get('status') in ('done', 'superseded') or not bodies.get(task['id']):
            continue
        value = task_fields(bodies[task['id']][0][0]).get('Short')
        if value is not None and (len(value) > SHORT_LIMIT or '\n' in value):
            found.append(f'{task["id"]}: Short is one line of at most {SHORT_LIMIT} characters, not {len(value)}: '
                         f'{" ".join(value.split())[:60]}')
    return found


def touches_errors(repo, data):
    """Open tasks whose `Touches:` is not a list of paths (TOOLSET-213-45): prose or a note ran
    into it, and the engine would hold the worker's own files as outside Touches."""
    text = checked_bytes(Path(repo) / 'TODO.md')
    if text is None:
        return []
    bodies = task_bodies(text.decode('utf-8'))
    found = []
    for task in data.get('tasks') or []:
        if task.get('status') in ('done', 'superseded') or not bodies.get(task['id']):
            continue
        value = task_fields(bodies[task['id']][0][0]).get('Touches') or ''
        value = re.split(r'\n(?:[ \t]*[-*][ \t]|[ \t]*#|[ \t]*\n)', value, maxsplit=1)[0]
        bad = next((p.strip() for p in value.split(',') if '\n' in p.strip() or p.strip().count(' ') >= 3), None)
        if bad:
            found.append(f'{task["id"]}: Touches is not a list of paths: {" ".join(bad.split())[:80]}')
    return found


def execute(a):
    if a.cmd == 'merge-attributes':
        import todo_archive
        text = todo_text(a.repo)
        known = set(task_bodies(text))
        owner = todo_archive.archive_owner(Path(a.repo), todo_archive.navigation(text, task_prose(text), known))
        print('goals.json merge=docs-sync-goals\nTODO.md merge=docs-sync-todo')
        for name in dict.fromkeys((todo_archive.DEFAULT, *todo_archive.LEGACY, owner.as_posix())):
            print(json.dumps(name) + ' merge=docs-sync-archive' if any(c.isspace() for c in name)
                  else name + ' merge=docs-sync-archive')
        return
    if a.cmd == 'merge-finalize':
        from planning_merge import finalize
        try:
            finalize(a.repo)
        except ValueError as exc:
            sys.exit(str(exc))
        print('ok'); return
    if a.cmd == 'init':
        initialize(a); return
    if a.cmd == 'propose':
        propose(a); return
    if a.cmd == 'accept':
        accept(a); return
    if a.cmd == 'archive':
        data = load(a.repo) if path_of(a.repo).exists() else None
        result = archive_tasks(a.repo, data, verified_tasks=tuple(filter(None, a.verified_tasks.split(','))))
        print(json.dumps(result)); return
    if a.cmd == 'new-id':
        print(new_task_id(a.repo, load(a.repo) if path_of(a.repo).exists() else None, a.prefix)); return
    if a.cmd == 'field':  # TODO.md only: an answer the runner reads from the task's entry
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        new_text, why = set_field(before.decode('utf-8'), a.task, a.label, a.value)
        if why:
            sys.exit(why + '; no write')
        atomic_write(todo, new_text, expected_bytes=before)
        print(f'ok {a.task} {a.label}: {" ".join(a.value.split())}'); return
    if a.cmd == 'move':  # TODO.md only: goals.json is neither read nor written
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        new_text, why = move_block(before.decode('utf-8'), a.task, -1 if a.direction == 'up' else 1)
        if why:
            sys.exit(why + '; no write')
        atomic_write(todo, new_text, expected_bytes=before)
        # goals.json is untouched: `reorder` (the runner runs it) records the new order as priority.
        print(f'ok {a.task} moved {a.direction}'); return
    data = load(a.repo)

    if a.cmd == 'redact':
        redact(a.repo, data, a.replacements_file, a.archive_dir); return

    if a.cmd == 'focus':
        if a.json:
            print(json.dumps({'primary_milestone': data.get('primary_milestone')})); return
        if a.clear:
            data.pop('primary_milestone', None)
            dump(a.repo, data); print('ok focus cleared'); return
        if not any(g['id'] == a.goal for g in data['goals']):
            sys.exit(f'unknown goal {a.goal}')
        data['primary_milestone'] = a.goal
        dump(a.repo, data); print(f'ok focus -> {a.goal}'); return

    if a.cmd == 'validate':
        errs = errors(data) + touches_errors(a.repo, data) + short_errors(a.repo, data)
        print('\n'.join(errs) if errs else 'ok')
        sys.exit(1 if errs else 0)
    if a.cmd == 'fmt':
        dump(a.repo, data); print('ok'); return
    if a.cmd == 'render':
        render(a.repo, normalize(data)); print('ok'); return
    if a.cmd == 'next':
        data = normalize(data)
        # Closing the last task precedes recording its evidence. Keep that
        # goal as a dependency gate while allowing independent work to proceed.
        problems = errors(data, allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
        try:
            picks, status = queue(data, todo_text(a.repo))
        except PriorityDrift as drift:
            print(json.dumps(dict(drift.status, outcome='PRIORITY_DRIFT', revision=revision(a.repo)), indent=2))
            sys.exit(3)
        if status['state'] == 'unmigrated':
            print(status['action'], file=sys.stderr)
        if a.json:
            print(json.dumps([{'task': t, 'goal': g['id'], 'goal_status': g['status'],
                               'priority_state': status['state']} for t, g in picks], indent=2))
        elif picks:
            t, g = picks[0]
            print(f"{t['id']} ({t['section']}) → {g['id']} [{g['status']}]: {t['title']}")
        else:
            print('none')
        return
    if a.cmd == 'reorder':
        data = normalize(data)
        problems = errors(data, allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
        record, status = reconcile_order(data, todo_text(a.repo))
        previous = data['priority_order']['tasks']
        report = {'priority_order': record['tasks'], 'previous': previous,
                  'notes': selection_notes(dict(data, priority_order=record), record['tasks'])}
        if status['state'] == 'synced':
            print(json.dumps(dict(report, outcome='UNCHANGED'), indent=2)); return
        data['priority_order'] = record
        dump(a.repo, data)
        print(json.dumps(dict(report, outcome='RECONCILED'), indent=2)); return
    if a.cmd == 'bootstrap-order':
        data = normalize(data)
        if data.get('priority_order'):
            print(json.dumps({'outcome': 'ALREADY_BOOTSTRAPPED', 'schema': data['priority_order']['schema'],
                              'action': 'Bootstrap never reruns; use `goals.py reorder` for later TODO.md edits.'}, indent=2))
            return
        problems = errors(data, allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        plan = bootstrap_plan(data, before.decode('utf-8'))
        rewrite = plan['text'].encode('utf-8') != before
        report = {'regions': plan['regions'], 'rewrite_todo': rewrite, 'priority_order': plan['record']['tasks'],
                  'next_before': plan['next_before'], 'next_after': plan['next_after'],
                  'eligible_order_changes': plan['eligible_order_changes'], 'revision': revision(a.repo)}
        if plan['reasons']:
            print(json.dumps(dict(report, outcome='BOOTSTRAP_CONFLICT', reasons=plan['reasons']), indent=2))
            sys.exit(1)
        if a.dry_run:
            print(json.dumps(dict(report, outcome='BOOTSTRAP_PLAN'), indent=2)); return
        if a.expected_revision is None:
            sys.exit('bootstrap-order apply requires --expected-revision from a --dry-run report; no write')
        ledger_before = checked_bytes(path_of(a.repo))
        if rewrite:
            atomic_write(todo, plan['text'], expected_bytes=before)
            if checked_bytes(todo) != plan['text'].encode('utf-8') or checked_bytes(path_of(a.repo)) != ledger_before:
                sys.exit('bootstrap verification failed after TODO.md write; ledger unchanged; rerun --dry-run')
            # The TODO.md write is this transaction's own; guard the ledger against anything else.
            TRANSACTION.set((Path(a.repo), revision(a.repo)))
        data['priority_order'] = plan['record']
        dump(a.repo, data)
        print(json.dumps(dict(report, outcome='BOOTSTRAPPED', revision=revision(a.repo)), indent=2)); return
    if a.cmd == 'supersede':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task['status'] == 'done':
            sys.exit('completed task history cannot be relabelled superseded; no write')
        successors = sorted(set(tid.strip() for tid in a.by.split(',') if tid.strip()))
        reason = a.reason.strip()
        if task['status'] == 'superseded' and (task.get('superseded_by') != successors
                or task.get('supersession_reason') != reason):
            sys.exit('supersession already recorded with a different disposition; no write')
        task.update(status='superseded', section='Superseded', superseded_by=successors,
                    supersession_reason=reason)
        problems = errors(normalize(data), allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems) + '; no write')
        dump(a.repo, data)
        print('ok superseded; acceptance remains unpassed; run render to retain original history in archive')
        return
    if a.cmd == 'task':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task['status'] == 'superseded':
            sys.exit('superseded history cannot be reopened or completed; use its successor tasks; no write')
        task['status'] = a.status
        goal = next((g for g in data['goals'] if g['id'] == task['goal']), None)
        if a.status != 'done':
            if task.get('section') == 'Done':
                task['section'] = 'Next'
            if goal and goal.get('status') == 'met':
                goal['status'] = 'partial'
        dump(a.repo, data)
        still_open = [t for t in data['tasks'] if t.get('goal') == task['goal'] and t.get('status') != 'done']
        if a.status == 'done' and goal and goal.get('status') != 'met' and not still_open:
            print(f"WARNING: {goal['id']} is still {goal['status']} with no open task. Record the check you ran: "
                  f"goals.py evidence {a.repo} {goal['id']} --kind executed --ref \"<command>\" --result pass")
        print('ok'); return
    if a.cmd == 'place':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task.get('status') in ('done', 'superseded'):
            sys.exit(f'task {a.task} is {task["status"]}; no write')
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        new_text, why = place_block(before.decode('utf-8'), a.task, a.section)
        if why:
            sys.exit(why + '; no write')
        atomic_write(todo, new_text, expected_bytes=before)
        TRANSACTION.set((Path(a.repo), revision(a.repo)))  # the TODO.md write is this command's own
        task['section'] = a.section
        dump(a.repo, data); print(f'ok {a.task} -> {a.section}'); return
    if a.cmd == 'section':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task.get('status') in ('done', 'superseded'):
            sys.exit(f'task {a.task} is {task["status"]}')
        task['section'] = a.section
        dump(a.repo, data); print(f'ok {a.task} -> {a.section}'); return
    if a.cmd == 'add-task':
        if a.task is None:
            a.task = new_task_id(a.repo, data, a.prefix)
        elif a.prefix:
            sys.exit('--prefix applies only when TASK is omitted; no write')
        if re.fullmatch(TASK_ID, a.task) is None:
            sys.exit('invalid task ID: use letters, digits, underscores or hyphens; start with a letter or digit; no write')
        if any(x['id'] == a.task for x in data['tasks']):
            sys.exit(f'task {a.task} already exists')
        goal = next((x for x in data['goals'] if x['id'] == a.goal), None) or sys.exit(f'unknown goal {a.goal}')
        deps = [d for d in a.depends_on.split(',') if d]
        known = {x['id'] for x in data['tasks']}
        missing = [d for d in deps if d not in known]
        if missing:
            sys.exit(f'unknown depends_on task(s): {missing}')
        if a.todo:
            short = ' '.join((a.short or '').split())
            if not short or len(short) > SHORT_LIMIT:
                sys.exit(f'--todo needs --short of 1 to {SHORT_LIMIT} characters; no write')
            todo = Path(a.repo) / 'TODO.md'
            before = checked_bytes(todo)
            if before is None:
                sys.exit('TODO.md not found; no write')
            title = ' '.join(a.title.split())
            entry = [f'### {a.task} — {title}', '', f'- [ ] {a.task} — {title}', f'- Short: {short}',
                     '- Status: open', f'- Goal: {a.goal}']
            entry += [f'- {label}: {" ".join(value.split())}' for label, value in
                      (('Scope', a.scope), ('Acceptance', a.acceptance), ('Checks', a.checks)) if value]
            entry.append(f'- Dependencies: {", ".join(deps) if deps else "None."}')
            text = before.decode('utf-8')
            heading = re.search(r'^##[ \t]+' + re.escape(a.section) + r'[ \t]*\r?$', text, re.M)
            if heading is None:
                sys.exit(f'TODO.md has no "## {a.section}" section; no write')
            at = heading.end() + len(re.match(r'(?:\r?\n)*', text[heading.end():])[0])
            atomic_write(todo, text[:at] + '\n'.join(entry) + '\n\n' + text[at:], expected_bytes=before)
            TRANSACTION.set((Path(a.repo), revision(a.repo)))  # the TODO.md write is this command's own
        data['tasks'].append({'id': a.task, 'goal': a.goal, 'title': a.title, 'status': 'open',
                              'section': a.section, 'depends_on': deps})
        goal['tasks'] = sorted(set(goal.get('tasks', []) + [a.task]))
        if goal.get('status') == 'met':
            goal['status'] = 'partial'
        dump(a.repo, data); print(f'ok {a.task} -> {a.goal} ({a.section})'); return
    if a.cmd == 'evidence':
        goal = next((x for x in data['goals'] if x['id'] == a.goal), None) or sys.exit(f'unknown goal {a.goal}')
        entry = {'kind': a.kind, 'ref': a.ref, 'result': a.result}
        completed = [t['id'] for t in data['tasks'] if t.get('goal') == a.goal and t.get('status') == 'done']
        task = a.task or (completed[-1] if completed else None)
        if a.task and a.task not in completed:
            sys.exit('--task must name a completed task of this goal; no write')
        summary = a.summary or f'{a.kind.capitalize()} check: {a.result}'
        if not summary.strip() or len(summary) > 80 or '\n' in summary or '\r' in summary:
            sys.exit('--summary must be one short line (1–80 characters); no write')
        entry['summary'] = summary
        if task:
            import todo_archive
            text = todo_text(a.repo)
            prose = todo_archive.navigation(text, task_prose(text), {t['id'] for t in data['tasks']})
            owner = todo_archive.archive_owner(Path(a.repo), prose)
            anchor = task.lower()
            history = (checked_bytes(Path(a.repo) / owner) or b'').decode('utf-8')
            if history and task not in task_bodies(text) and f'<a id="{anchor}"></a>' not in history:
                # Legacy history may have a task heading rather than an ID-only anchor.
                # Reuse real headings without rewriting append-only historical bytes.
                spans, _ = todo_archive.entries(history, markdown_prose(history), {task})
                source = next((start for start, _, tid, _ in spans if tid == task), None)
                headings = [h for h in heading_rows(markdown_prose(history))
                            if source is not None and h[1] <= source]
                own = [h for h in headings if re.search(r'(?<![\w-])' + re.escape(task) +
                                                       r'(?![\w-])', history[h[1]:h[2]])]
                anchor = (own or headings)[-1][0] if (own or headings) else ''
            entry.update(task=task, archive=owner.as_posix(), anchor=anchor)
        if a.ran_at:
            entry['ran_at'] = a.ran_at
        goal['evidence'] = [x for x in goal.get('evidence', []) if (x.get('kind'), x.get('ref')) != (a.kind, a.ref)] + [entry]
        for previous in goal['evidence']:
            previous.pop('coverage_current', None)
        entry['coverage_current'] = True
        if a.kind == 'executed' and a.result == 'pass' and goal.get('status') in ('unmet', 'unverified', 'partial') \
                and all(t.get('status') == 'done' for t in data['tasks'] if t.get('goal') == a.goal):
            goal['status'] = 'met'
        if a.kind == 'executed' and a.result == 'fail' and goal.get('status') == 'met':
            goal['status'] = 'partial'
        dump(a.repo, data); print(f"ok {goal['id']} → {goal['status']}"); return



# Bind each facade copy's private write state explicitly. Late lookup preserves
# instrumentation of atomic_write without giving shared modules mutable state.
_writes = SimpleNamespace(transaction=TRANSACTION, write=lambda *a, **kw: atomic_write(*a, **kw))
coordination = partial(coordination, transaction=TRANSACTION)
atomic_write = partial(atomic_write, transaction=TRANSACTION)
dump = partial(dump, write=_writes.write)
archive_tasks = partial(archive_tasks, write=_writes.write)
render = partial(render, write=_writes.write)
initialize = partial(initialize, writes=_writes)
propose = partial(propose, writes=_writes)
accept = partial(accept, writes=_writes)


if __name__ == '__main__':
    # Merge helpers must share this invocation's lock/stale-write context.
    sys.modules['goals'] = sys.modules[__name__]
    main()
