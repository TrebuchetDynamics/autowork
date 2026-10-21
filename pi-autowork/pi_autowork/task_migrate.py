"""`autowork migrate <repo> [--dry-run] [--no-commit]`: convert a repository to tasks/ once.

It reads TODO.md, goals.json and the archive once, builds tasks/items/ and tasks/goals/,
proves the result first (same task set, same contract fields read back, and the same
selection order as the current TODO.md queue), and only then changes anything. It refuses,
writing nothing, while anything is in flight: a live worker slot or an unfinished
integration or closure, a live lease, a claimed task, uncommitted planning files, or a
repository already converted. There is no reverse migration.

The change is one transaction. The converted commit (tasks/ added, TODO.md and goals.json
removed, no stub; TODO.archive.md stays as history) is built with plumbing and recorded as
refs/autowork/migration before any file changes. Its paths are then staged in the working
tree and index, and HEAD moves to it by compare-and-swap; the ref is deleted last. A run
interrupted at any step leaves that ref, and the next run finishes from wherever it
stopped, or refuses, changing nothing, when a path holds content that is neither the old
nor the converted version. `--no-commit` stops after staging: HEAD stays where it is, and
the owner's commit (or a later run) lands it.

One kind of slot does not stop it: a held slot that only waits for the owner's answer to a
worker-reported blocker (no live worker, no finished commit, not a repeated quick hold).
The runner that would take that answer cannot run before conversion, so the conversion sets
that attempt aside, as `--parallel-set-aside` does (worktrees and branches kept under
-set-aside-N names, the slot moved to slot-history), once the store is proven and before any
file changes; the task then dispatches fresh from its converted record, with whatever answer
its entry now holds.

Mapping (lossless; every other label becomes a `- Label: value` note in the body):
rank = 1000 x the queue's human order; Dependencies -> depends_on (task IDs, or the
whole prose clause when it names none, which keeps it waiting as before); Touches ->
touches (none -> ["**"], the whole repository, as an unknown set was treated);
Resources -> the resource tokens the engine enforces today (`port:8080 — ...` is `port`); Kind plan -> kind plan; an owner-only Ownership without a
recorded Live authorization -> ownership owner, otherwise worker; a Live authorization
-> live authorized. The original Ownership, Resources and Live authorization wording is
kept as notes.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ENGINE = Path(__file__).resolve().parents[1] / 'engine'
sys.path.insert(0, str(ENGINE))
import parallel_plan  # noqa: E402
import task_execution  # noqa: E402  (git only)
from pi_autowork import task_commands  # noqa: E402
from pi_autowork.legacy import reader  # noqa: E402
import task_select  # noqa: E402
import task_store  # noqa: E402
from task_store import StoreError, TaskStore, WriteError  # noqa: E402

STEP = 1000
PLANNING = ('TODO.md', 'goals.json', 'TODO.archive.md')
CANDIDATE = 'refs/autowork/migration'
SUBJECT = 'chore(tasks): convert to the tasks/ store (autowork migrate)'
TYPED_LABELS = ('Short', 'Status', 'Goal', 'Scope', 'Acceptance', 'Checks', 'Verification',
                'Dependencies', 'Touches', 'Exclusions', 'Kind')
KEPT_AS_NOTES = ('Ownership', 'Resources', 'Live authorization')
# Free text becomes a typed grant only here: a value that says no, or not yet, is refused
# (naming the task) rather than read as authorized, as any non-empty text was before.
NOT_A_GRANT = re.compile(
    # A bare "no" word, alone or followed by punctuation and an explanation ("none (ask)").
    r'(?:none|no|nope|n/?a|na|nil|null|-+|—|–|\?+|tbd|tba|todo|denied|refused|revoked|withdrawn|'
    r'missing|unknown|unauthori[sz]ed)\s*(?:[.;:,!)(—–]\s*.*)?'
    # A phrase that says the grant is still to come, whatever follows it.
    r'|(?:pending|awaiting|not\s+(?:yet|granted|given|recorded|authori[sz]ed)|to\s+be\s+'
    r'(?:decided|confirmed|granted)|ask)\b.*', re.I)


class Refused(Exception):
    """Conversion is unsafe or lossy; nothing was written."""


def _git(repo, *args, env=None, stdin=None):
    # No optional locks: a status read never refreshes the index, so --check writes nothing.
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')} | {'GIT_OPTIONAL_LOCKS': '0'}
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                            env={**clean, **(env or {})}, input=stdin, timeout=120)
    if result.returncode:
        raise Refused(f'git {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.strip()


# --- refusals --------------------------------------------------------------------------

def _ok(repo, *args):
    """git's output, or None when it fails: a missing ref or path is an answer, not an error."""
    try:
        return _git(repo, *args)
    except Refused:
        return None


def committed(repo, rev, path):
    return _ok(repo, 'rev-parse', '--verify', '-q', f'{rev}:{path}') is not None


def awaiting_answer(repo):
    """Held slots that only wait for the owner's answer to a worker-reported blocker: no live
    worker, and not a repeated quick hold (that one needs its Blocker resolution first)."""
    import parallel_state
    common = parallel_state.common_dir(Path(repo))
    try:
        slots = parallel_state.slots(common) if (common / 'slots').is_dir() else []
    except ValueError:
        return []  # busy() reports the unreadable slots
    return [s for s in slots if s['state'] == 'held' and s.get('cause') == 'blocker'
            and not parallel_state.worker_live(s) and not parallel_state.quick_hold(common, s)]


def busy(repo):
    """What is in flight, as plain sentences: nothing may convert under it. A slot waiting on
    an owner's answer is not in flight: conversion sets it aside."""
    held, problems = task_commands.in_flight(repo)
    held -= {s['task_id'] for s in awaiting_answer(repo)}
    if held:
        problems.append('worker slots in flight or unfinished integration/closure: ' + ', '.join(sorted(held)))
    return problems


def set_aside_waiting(repo):
    """Set aside every slot waiting on an owner's answer, under the engine's own locks; the
    task dispatches fresh after conversion. Returns their task IDs."""
    import parallel_integrate
    import parallel_state
    common = parallel_state.common_dir(Path(repo))
    done = []
    try:
        with task_execution.lock(common / 'dispatch.lock', 5), task_execution.lock(common / 'integration.lock', 5), \
                task_execution.lock(common / 'writer.lock', 5):
            if parallel_state.live_coordinator(common):
                raise Refused('a live parallel coordinator lease')
            for slot in awaiting_answer(repo):  # reread under the locks
                parallel_integrate._retire(repo, common, slot, True)
                done.append(slot['task_id'])
    except BlockingIOError:
        raise Refused('the engine is busy (its dispatch, integration or writer lock is held)') from None
    except ValueError as exc:
        raise Refused(f'setting aside a slot waiting on an answer failed: {exc}') from None
    return done


def refusals(repo):
    """Every reason conversion may not run now, as plain sentences."""
    repo = Path(repo)
    found = []
    if committed(repo, 'HEAD', 'tasks'):
        found.append('already converted: tasks/ is committed')
    if not (repo / 'TODO.md').is_file() or not (repo / 'goals.json').is_file():
        found.append('TODO.md and goals.json are both needed to convert')
    dirty = _git(repo, 'status', '--porcelain', '--', *PLANNING)
    if dirty:
        found.append('uncommitted planning files: ' + ', '.join(line[3:] for line in dirty.splitlines()))
    found += busy(repo)
    try:
        ledger = json.loads((repo / 'goals.json').read_text())
        claimed = sorted(t['id'] for t in ledger.get('tasks', []) if t.get('status') == 'in_progress')
        if claimed:
            found.append('claimed tasks (release them first): ' + ', '.join(claimed))
    except (OSError, ValueError, AttributeError):
        pass
    return found


# --- mapping ---------------------------------------------------------------------------

def _owner_only(fields):
    task = {'id': '', 'fields': {k: v for k, v in fields.items() if k != 'Live authorization'}}
    return bool(parallel_plan.authorization_wait(task))


def _task_record(tid, title, entry, fields, rank, known, listed=()):
    """(header fields, body) for one open task, or Refused naming what cannot be held."""
    checks = reader.task_checks(fields)
    deps_text = fields.get('Dependencies', 'None.').strip()
    deps = parallel_plan.dependency_ids(deps_text, known)
    try:
        touches = parallel_plan.paths(fields['Touches']) if fields.get('Touches', '').strip() else ['**']
    except ValueError as exc:
        raise Refused(f'{tid}: Touches cannot be converted ({exc})') from None
    resources = sorted(parallel_plan._resources({'fields': fields}))
    owner_only = _owner_only(fields)
    grant = ' '.join(fields.get('Live authorization', '').split())
    if grant and NOT_A_GRANT.fullmatch(grant):
        raise Refused(f'{tid}: "Live authorization: {grant}" is not a grant; write the authorization '
                      'or remove the line, then convert')
    live = bool(grant)
    header = dict(schema=1, id=tid, title=title, short=fields.get('Short', '').strip() or title,
                  status=entry['status'], goal=entry['goal'], section=entry['section'], rank=rank,
                  depends_on=list(deps), touches=list(touches), resources=resources,
                  kind='plan' if fields.get('Kind', '').strip().lower() == 'plan' else 'implementation',
                  ownership='owner' if owner_only and not live else 'worker', exclusions=[])
    if live:
        header['live'] = 'authorized'
    if fields.get('Scope', '').strip():
        header['scope'] = fields['Scope'].strip()
    if fields.get('Acceptance', '').strip():
        header['acceptance'] = _items(fields['Acceptance'])
    if checks and checks.strip():
        header['checks'] = _items(checks)
    if fields.get('Exclusions', '').strip():
        header['exclusions'] = [fields['Exclusions'].strip()]
    labels = [label for label, _ in listed]
    repeated = sorted({label for label in labels if labels.count(label) > 1
                       and (label in TYPED_LABELS or label in KEPT_AS_NOTES)})
    if repeated:
        raise Refused(f'{tid}: {", ".join(repeated)} written more than once; keep one, then convert')
    # Every note, repeated ones too: the field parser keeps only labels written once.
    notes = [(label, value) for label, value in (listed or fields.items())
             if label not in TYPED_LABELS or label in KEPT_AS_NOTES]
    if deps and deps_text and deps_text.rstrip('.') != ', '.join(deps):
        notes.append(('Dependencies', deps_text))
    if not fields.get('Touches', '').strip():
        notes.append(('Touches', 'none before conversion; ** stands for the whole repository'))
    return header, _notes(tid, notes)


ITEM = re.compile(r'(?:\d+[.)]|[-*])\s+')


def _items(text):
    """An array field's value: one item per numbered or bulleted point of a value written over
    several lines (`1. ...` / `- ...`, its continuation lines joined), in order; otherwise the
    whole value as one item, its line breaks folded."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) > 1 and ITEM.match(lines[0]):
        items = []
        for line in lines:
            if ITEM.match(line):
                items.append(ITEM.sub('', line, count=1))
            else:
                items[-1] += ' ' + line
        return items
    return [' '.join(lines)]


def _notes(tid, notes):
    lines = []
    for label, value in notes:
        value = ' '.join(str(value).split())
        if not value:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z '-]*", label):
            raise Refused(f'{tid}: field label {label!r} cannot be kept as a note')
        lines.append(f'- {label}: {value}\n')
    return '\n' + ''.join(lines)


def build(repo):
    """{relative path: text} for the whole store, plus the legacy order it must reproduce."""
    repo = Path(repo)
    try:
        inputs = reader.inputs(repo)
        legacy = reader.order(repo, inputs)
    except reader.Drift as exc:
        raise Refused(f'TODO.md order differs from the recorded priority ({exc}); reconcile it first') from None
    except (ValueError, SystemExit) as exc:
        raise Refused(f'the current queue does not validate: {exc}') from None
    ledger, bodies = inputs['ledger'], inputs['bodies']
    tasks = {t['id']: t for t in ledger['tasks']}
    known = set(tasks) | set(bodies)
    record = ledger.get('priority_order') or {}
    sections = ('Now', 'Next', 'Needs decision')
    todo_order = [tid for tid in bodies if tasks.get(tid, {}).get('status') in ('open', 'in_progress')]
    human = [tid for tid in record.get('tasks', []) if tid in todo_order] or todo_order
    human += [tid for tid in todo_order if tid not in human]
    human = sorted(human, key=lambda tid: (sections.index(tasks[tid]['section']), human.index(tid)))
    files = {}
    duplicated = sorted(tid for tid in human if len(bodies[tid]) != 1)
    if duplicated:
        raise Refused('more than one TODO.md entry for ' + ', '.join(duplicated) + '; keep one, then convert')
    for index, tid in enumerate(human):
        body, _mark, _section = bodies[tid][0]
        fields = reader.task_fields(body)
        title = body.splitlines()[0].split('—', 1)[-1].strip(' —:-') or tid
        header, notes = _task_record(tid, title, tasks[tid], fields, STEP * (index + 1), known,
                                     reader.task_field_list(body))
        files[f'tasks/items/{tid}.md'] = _render(tid, header, notes)
    archived = reader.archived_done(repo)
    for tid, entry in tasks.items():
        if entry['status'] in ('done', 'superseded'):
            header = dict(schema=1, id=tid, title=entry.get('title') or tid, status=entry['status'], goal=entry['goal'])
            notes = [('Archived', 'TODO.archive.md')] if tid in archived else []
            if entry['status'] == 'superseded':
                notes.append(('Superseded by', ', '.join(entry.get('superseded_by') or []) + '; '
                              + (entry.get('supersession_reason') or '')))
            files[f'tasks/items/{tid}.md'] = _render(tid, header, _notes(tid, notes))
    # Dependencies on tasks that exist only in the archive stay satisfied.
    needed = {d for tid in human for d in parallel_plan.dependency_ids(
        reader.task_fields(bodies[tid][0][0]).get('Dependencies', 'None.'), known)}
    for tid in sorted(needed & archived - set(tasks)):
        files[f'tasks/items/{tid}.md'] = _render(tid, dict(schema=1, id=tid, title=tid, status='done'),
                                                 _notes(tid, [('Archived', 'TODO.archive.md')]))
    focus = ledger.get('primary_milestone')
    for goal in ledger['goals']:
        header = dict(schema=1, id=goal['id'], title=goal['title'], priority=goal['priority'],
                      source=goal['source'], status=goal['status'], focus=goal['id'] == focus,
                      depends_on=list(goal.get('depends_on') or []))
        notes = [('Evidence', f"{e.get('kind', '')}: {e.get('ref', '')} ({e.get('result', '')})")
                 for e in goal.get('evidence') or []]
        try:
            files[f'tasks/goals/{goal["id"]}.md'] = task_store.render(header, _notes(goal['id'], notes), goal=True)
        except WriteError as exc:
            raise Refused(f'{goal["id"]}: {exc}') from None
    return files, legacy, set(tasks)


def _render(tid, header, body):
    try:
        return task_store.render(header, body)
    except WriteError as exc:
        raise Refused(f'{tid}: {exc}') from None


# --- proof and write -------------------------------------------------------------------

def converted_tree(repo, files):
    """HEAD's tree with the built store added and TODO.md and goals.json removed: no
    working-tree or index write."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {'GIT_INDEX_FILE': str(Path(tmp) / 'index')}
        _git(repo, 'read-tree', 'HEAD', env=env)
        for path, text in files.items():
            oid = _git(repo, 'hash-object', '-w', '--stdin', stdin=text)
            _git(repo, 'update-index', '--add', '--cacheinfo', f'100644,{oid},{path}', env=env)
        _git(repo, 'update-index', '--force-remove', '--', 'TODO.md', 'goals.json', env=env)
        return _git(repo, 'write-tree', env=env)


def proof_store(repo, tree):
    """The converted tree read back through a throwaway commit."""
    ident = {'GIT_AUTHOR_NAME': 'autowork', 'GIT_AUTHOR_EMAIL': 'autowork@localhost',
             'GIT_COMMITTER_NAME': 'autowork', 'GIT_COMMITTER_EMAIL': 'autowork@localhost'}
    commit = _git(repo, 'commit-tree', tree, '-p', 'HEAD', '-m', 'migration proof', env=ident)
    try:
        return TaskStore.at(repo, commit)
    except StoreError as exc:
        raise Refused(f'the converted store does not validate: {exc}') from None


def prove(repo, tree, legacy, ids):
    store = proof_store(repo, tree)
    missing = sorted(ids - set(store.tasks))
    if missing:
        raise Refused('tasks missing from the converted store: ' + ', '.join(missing))
    new = [t.id for t in task_select.order(store)]
    if new != legacy:
        raise Refused(f'selection order differs: TODO.md queue {legacy}, converted {new}')
    return store


# --- the transaction -------------------------------------------------------------------

def _changes(repo, old, new):
    """[(path, mode, old oid, new oid)] from ``old`` to ``new``; a zero oid is an absent file."""
    out = _git(repo, 'diff-tree', '-r', '--no-renames', '-z', old, new).split('\0')
    changes = []
    for meta, path in zip(out[0::2], out[1::2]):
        if meta:
            _old_mode, mode, old_oid, new_oid, _status = meta.lstrip(':').split()
            changes.append((path, mode, old_oid, new_oid))
    return changes


def _blob_id(repo, data):
    """The object ID ``data`` would have, computed without writing an object."""
    algorithm = _ok(repo, 'rev-parse', '--show-object-format') or 'sha1'
    return hashlib.new(algorithm, b'blob %d\0' % len(data) + data).hexdigest()


def _staged(repo, path):
    entry = _git(repo, 'ls-files', '-s', '--', path)
    return entry.split()[1] if entry else None


def stage(repo, old, new):
    """Bring the working tree and index of every path ``old``..``new`` changes to ``new``.
    A path may already be in either version (an interrupted run stopped part-way); any other
    content refuses before anything is written. A path whose new version is staged keeps its
    working-tree file, which may hold later edits."""
    zero = '0' * len(old)
    plan = []
    for path, mode, old_oid, new_oid in _changes(repo, old, new):
        index = _staged(repo, path) or zero
        if index == new_oid:
            continue
        if index != old_oid:
            raise Refused(f'{path} is staged with content that is neither the old nor the converted version')
        target = Path(repo) / path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise Refused(f'{path} is not a regular file; move it aside, then run again')
        present = _blob_id(repo, target.read_bytes()) if target.is_file() else zero
        if present not in (old_oid, new_oid):
            raise Refused(f'{path} holds working-tree content that is neither the old nor the converted '
                          'version; move it aside, then run again')
        plan.append((path, mode, new_oid))
    for path, _mode, new_oid in plan:
        target = Path(repo) / path
        if new_oid == zero:
            target.unlink(missing_ok=True)
            continue
        data = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', new_oid], capture_output=True,
                              check=True, timeout=60).stdout
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f'.{target.name}.{os.getpid()}.tmp')
        tmp.write_bytes(data)
        os.replace(tmp, target)
    if plan:
        _git(repo, 'update-index', '--index-info',
             stdin=''.join(f'{"0" if oid == zero else mode} {oid}\t{path}\n' for path, mode, oid in plan))


def finish(repo, candidate, commit=True):
    """Land a recorded conversion from wherever it stopped; returns the outcome."""
    old = _git(repo, 'rev-parse', f'{candidate}^')
    head = _git(repo, 'rev-parse', 'HEAD')
    if head not in (old, candidate):
        if committed(repo, 'HEAD', 'tasks') and not committed(repo, 'HEAD', 'TODO.md'):
            _git(repo, 'update-ref', '-d', CANDIDATE, candidate)  # landed by its own commit
            return 'ALREADY_CONVERTED'
        raise Refused(f'the conversion recorded at {CANDIDATE} ({candidate[:12]}) was built on {old[:12]}, '
                      f'but HEAD is now {head[:12]} and the conversion is staged; commit or unstage it, then run again')
    stage(repo, old, candidate)
    if head == old and not commit:
        return 'STAGED'
    if head == old:
        _git(repo, 'update-ref', '-m', 'autowork migrate', 'HEAD', candidate, old)
    _git(repo, 'update-ref', '-d', CANDIDATE, candidate)
    return 'CONVERTED'


def _stale(repo, candidate):
    """Drop a recorded conversion built on an older HEAD when nothing of it is staged or
    written: it is rebuilt from the planning files. True when dropped."""
    old = _git(repo, 'rev-parse', f'{candidate}^')
    if _git(repo, 'rev-parse', 'HEAD') in (old, candidate) or committed(repo, 'HEAD', 'tasks'):
        return False
    zero = '0' * len(old)
    for path, _mode, _old_oid, new_oid in _changes(repo, old, candidate):
        if new_oid != zero and ((Path(repo) / path).exists() or _staged(repo, path)):
            return False
    _git(repo, 'update-ref', '-d', CANDIDATE, candidate)
    return True


def pending(repo):
    """The recorded, unfinished conversion's commit, or None."""
    return _ok(repo, 'rev-parse', '--verify', '-q', CANDIDATE)


def migrate(repo, dry_run=False, commit=True):
    """Convert under the repository's task lock."""
    repo = Path(task_execution.git(Path(repo), 'rev-parse', '--show-toplevel')).resolve()
    with task_commands.locked(repo):
        return convert(repo, dry_run, commit)


def convert(repo, dry_run=False, commit=True):
    """Convert, or finish a recorded conversion; the caller holds the task lock."""
    candidate = pending(repo)
    if candidate and not dry_run and _stale(repo, candidate):
        candidate = None
    if candidate:
        if dry_run:
            return dict(outcome='PENDING', candidate=candidate)
        if found := busy(repo):
            raise Refused('; '.join(found))
        outcome = finish(repo, candidate, commit)
        summary = dict(outcome=outcome, candidate=candidate, resumed=True)
        if outcome == 'CONVERTED':
            summary['commit'] = _git(repo, 'rev-parse', '--short', 'HEAD')
        return summary
    if found := refusals(repo):
        raise Refused('; '.join(found))
    files, legacy, ids = build(repo)
    tree = converted_tree(repo, files)
    store = prove(repo, tree, legacy, ids)
    summary = dict(outcome='DRY_RUN' if dry_run else 'CONVERTED', tasks=len(store.tasks), goals=len(store.goals),
                   order=legacy)
    waiting = sorted(s['task_id'] for s in awaiting_answer(repo))
    if dry_run:
        if waiting:
            summary['would_set_aside'] = waiting
        return summary
    if waiting:
        summary['set_aside'] = set_aside_waiting(repo)
    head = _git(repo, 'rev-parse', 'HEAD')
    candidate = _git(repo, 'commit-tree', tree, '-p', head, '-m', SUBJECT, '-m',
                     f'{len(store.tasks)} tasks and {len(store.goals)} goals; selection order unchanged. '
                     'TODO.archive.md stays as history.')
    _git(repo, 'update-ref', '-m', 'autowork migrate: candidate', CANDIDATE, candidate, '')
    summary.update(outcome=finish(repo, candidate, commit), candidate=candidate)
    if summary['outcome'] == 'CONVERTED':
        summary['commit'] = _git(repo, 'rev-parse', '--short', 'HEAD')
    return summary


def add_parser(sub):
    p = sub.add_parser('migrate', help='convert a repository to the tasks/ store once (local commit)')
    p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--dry-run', action='store_true', help='check and show the result; write nothing')
    p.add_argument('--no-commit', action='store_true', help='stage the conversion; never move HEAD')
    return p


def run(args, repo):
    try:
        result = migrate(repo, args.dry_run, not args.no_commit)
    except Refused as exc:
        print(f'autowork migrate: refused, nothing written: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0
