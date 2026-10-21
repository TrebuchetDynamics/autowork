"""`autowork migrate <repo> [--dry-run]`: convert a repository to tasks/ once.

It reads TODO.md, goals.json and the archive once, builds tasks/items/ and tasks/goals/,
proves the result first (same task set, same contract fields read back, and the same
selection order as the current TODO.md queue), and only then writes the files, removes
TODO.md and goals.json (no stub) and makes one local commit. TODO.archive.md stays as
history. It refuses, writing nothing, while anything is in flight: a live worker slot or
an unfinished integration or closure, a live lease, a claimed task, uncommitted planning
files, or a repository already converted. There is no reverse migration.

Mapping (lossless; every other label becomes a `- Label: value` note in the body):
rank = 1000 x the queue's human order; Dependencies -> depends_on (task IDs, or the
whole prose clause when it names none, which keeps it waiting as before); Touches ->
touches (none -> ["**"], the whole repository, as an unknown set was treated);
Resources -> the resource tokens the engine enforces today (`port:8080 — ...` is `port`); Kind plan -> kind plan; an owner-only Ownership without a
recorded Live authorization -> ownership owner, otherwise worker; a Live authorization
-> live authorized. The original Ownership, Resources and Live authorization wording is
kept as notes.
"""
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
import parallel_state  # noqa: E402
import task_execution  # noqa: E402  (leases only: read, active_owner, git)
from pi_autowork.legacy import reader  # noqa: E402
import task_select  # noqa: E402
import task_store  # noqa: E402
from task_store import StoreError, TaskStore, WriteError  # noqa: E402

STEP = 1000
PLANNING = ('TODO.md', 'goals.json', 'TODO.archive.md')
OCCUPYING = ('dispatched', 'running', 'reported', 'integrating', 'integrated', 'held', 'interrupted')
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
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                            env={**clean, **(env or {})}, input=stdin, timeout=120)
    if result.returncode:
        raise Refused(f'git {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.strip()


# --- refusals --------------------------------------------------------------------------

def refusals(repo):
    """Every reason conversion may not run now, as plain sentences."""
    repo = Path(repo)
    found = []
    if (repo / 'tasks').exists():
        found.append('already converted: tasks/ exists')
    if not (repo / 'TODO.md').is_file() or not (repo / 'goals.json').is_file():
        found.append('TODO.md and goals.json are both needed to convert')
    dirty = _git(repo, 'status', '--porcelain', '--', *PLANNING)
    if dirty:
        found.append('uncommitted planning files: ' + ', '.join(line[3:] for line in dirty.splitlines()))
    common = parallel_state.common_dir(repo)
    try:
        slots = parallel_state.slots(common) if (common / 'slots').is_dir() else []
    except ValueError as exc:
        found.append(f'worker slots cannot be read ({exc})')
        slots = []
    busy = sorted(f"{s['task_id']} ({s['state']})" for s in slots if s['state'] in OCCUPYING)
    if busy:
        found.append('worker slots in flight or unfinished integration/closure: ' + ', '.join(busy))
    try:
        if parallel_state.live_coordinator(common):
            found.append('a live parallel coordinator lease')
    except ValueError as exc:
        found.append(f'the coordinator lease cannot be read ({exc})')
    sequential = task_execution.read(common / 'active.json') if (common / 'active.json').exists() else None
    if sequential and task_execution.active_owner(sequential):
        found.append('a live sequential execution lease')
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
        header['acceptance'] = [fields['Acceptance'].strip()]
    if checks and checks.strip():
        header['checks'] = [checks.strip()]
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
    except reader.Drift:
        raise Refused('TODO.md order differs from the recorded priority; reconcile it first') from None
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

def proof_store(repo, files):
    """The built store read back through a throwaway commit: no working-tree or index write."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {'GIT_INDEX_FILE': str(Path(tmp) / 'index')}
        _git(repo, 'read-tree', 'HEAD', env=env)
        for path, text in files.items():
            oid = _git(repo, 'hash-object', '-w', '--stdin', stdin=text)
            _git(repo, 'update-index', '--add', '--cacheinfo', f'100644,{oid},{path}', env=env)
        tree = _git(repo, 'write-tree', env=env)
    ident = {'GIT_AUTHOR_NAME': 'autowork', 'GIT_AUTHOR_EMAIL': 'autowork@localhost',
             'GIT_COMMITTER_NAME': 'autowork', 'GIT_COMMITTER_EMAIL': 'autowork@localhost'}
    commit = _git(repo, 'commit-tree', tree, '-p', 'HEAD', '-m', 'migration proof', env=ident)
    try:
        return TaskStore.at(repo, commit)
    except StoreError as exc:
        raise Refused(f'the converted store does not validate: {exc}') from None


def prove(repo, files, legacy, ids):
    store = proof_store(repo, files)
    missing = sorted(ids - set(store.tasks))
    if missing:
        raise Refused('tasks missing from the converted store: ' + ', '.join(missing))
    new = [t.id for t in task_select.order(store)]
    if new != legacy:
        raise Refused(f'selection order differs: TODO.md queue {legacy}, converted {new}')
    return store


def migrate(repo, dry_run=False):
    repo = Path(task_execution.git(Path(repo), 'rev-parse', '--show-toplevel')).resolve()
    if found := refusals(repo):
        raise Refused('; '.join(found))
    files, legacy, ids = build(repo)
    store = prove(repo, files, legacy, ids)
    summary = dict(outcome='DRY_RUN' if dry_run else 'CONVERTED', tasks=len(store.tasks), goals=len(store.goals),
                   order=legacy)
    if dry_run:
        return summary
    for path, text in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, 'rm', '-q', '--', 'TODO.md', 'goals.json')
    _git(repo, 'add', '--', 'tasks')
    _git(repo, 'commit', '-q', '-m', 'chore(tasks): convert to the tasks/ store (autowork migrate)\n\n'
         f'{len(store.tasks)} tasks and {len(store.goals)} goals; selection order unchanged. '
         'TODO.archive.md stays as history.', '--', 'tasks', 'TODO.md', 'goals.json')
    summary['commit'] = _git(repo, 'rev-parse', '--short', 'HEAD')
    return summary


def add_parser(sub):
    p = sub.add_parser('migrate', help='convert a repository to the tasks/ store once (local commit)')
    p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--dry-run', action='store_true', help='check and show the result; write nothing')
    return p


def run(args, repo):
    try:
        result = migrate(repo, args.dry_run)
    except Refused as exc:
        print(f'autowork migrate: refused, nothing written: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0
