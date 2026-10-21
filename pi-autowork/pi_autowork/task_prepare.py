"""`autowork tasks prepare [repo] [--check | --no-commit]`: bring a repository to a valid tasks/ store.

Docs Sync runs it first on every host, so an owner never converts, initializes or repairs
the store by hand. It detects the repository's state and does only what needs no judgement:

- converted: reads the store (the working tree's when task files are uncommitted) and
  reports diagnostics, each with the `autowork tasks` command that repairs it from evidence;
- legacy (TODO.md + goals.json): converts through `autowork migrate`'s transaction, one
  local commit (`--no-commit`: staged, HEAD unmoved);
- conversion pending (an interrupted or staged conversion): finishes it, or refuses;
- none: reports the accepted headings a bootstrap may take goals from; the first
  `autowork tasks goal` starts the store;
- invalid: refuses with the store's path:line errors.

It never decides intent: goals, tasks and contract repairs come from accepted documents
through the existing `autowork tasks` writers. It refuses, changing nothing, while a worker
or lease is in flight for a conversion, and names in-flight tasks whose contracts must not
change. `--check` is read-only: no file, ref, index, lock or object is written. On an
unchanged repository a second run reports the same result and changes nothing.
"""
from pathlib import Path
import re
import subprocess

from pi_autowork import task_commands, task_migrate
from pi_autowork.task_commands import worktree_store
import task_select  # noqa: E402  (task_commands put the engine on the path)
from task_store import StoreError, TaskStore  # noqa: E402

HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
ACCEPTED = re.compile(r'^\s*(?:\*\*)?Status:?(?:\*\*)?:?\s*Accepted\b', re.I)
LINK = re.compile(r'\]\(([^)\s]+)\)')


def _git(repo, *args):
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args],
                            capture_output=True, text=True, timeout=60)
    return result.stdout.strip() if result.returncode == 0 else None


def _slug(text, seen):
    """A GitHub heading anchor; repeated headings take -1, -2, ..."""
    base = re.sub(r'[^\w\- ]', '', re.sub(r'<[^>]+>|`', '', text).strip().lower()).replace(' ', '-')
    count = seen.get(base, 0)
    seen[base] = count + 1
    return f'{base}-{count}' if count else base


def headings(text):
    """[(anchor, accepted)] for every Markdown heading outside code fences."""
    found, seen, fenced = [], {}, False
    for line in text.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
            continue
        if fenced:
            continue
        if match := HEADING.match(line):
            found.append([_slug(match.group(2), seen), False])
        elif found and ACCEPTED.match(line):
            found[-1][1] = True
    return [tuple(item) for item in found]


def intent(repo):
    """Tracked Markdown documents and their headings marked `Status: Accepted`, as path#anchor."""
    listed = _git(repo, 'ls-files', '-z', '--', '*.md') or ''
    documents, accepted = [], []
    for path in sorted(p for p in listed.split('\0') if p):
        if path.startswith('tasks/') or path in ('TODO.md', 'TODO.archive.md', 'BLOCKERS.md'):
            continue
        try:
            text = (Path(repo) / path).read_text(errors='replace')
        except OSError:
            continue
        documents.append(path)
        accepted += [f'{path}#{anchor}' for anchor, ok in headings(text) if ok]
    return dict(documents=documents, accepted=accepted)


def _target(repo, reference):
    """Why a repository path#anchor reference is broken, or None. URLs and prose are skipped."""
    if re.match(r'^[a-z][a-z0-9+.-]*:', reference) or ' ' in reference.strip():
        return None
    path, _, anchor = reference.partition('#')
    if not path or not (path.endswith('.md') or '/' in path):
        return None
    target = Path(repo) / path
    if not target.exists():
        return f'{path} does not exist'
    if anchor and target.is_file() and path.endswith('.md'):
        if anchor not in {a for a, _ in headings(target.read_text(errors='replace'))}:
            return f'{path} has no heading #{anchor}'
    return None


def diagnose(repo, store, held=()):
    """Defects an evidence-driven repair can fix, each with the command that does it. Sorted,
    so an unchanged store reports the same list."""
    found = []

    def add(code, rid, detail, fix):
        found.append(dict(code=code, id=rid, detail=detail, fix=fix))

    tasks, goals = store.tasks, store.goals
    for t in tasks.values():
        if t.status != 'open':
            continue
        if t.draft:
            add('DRAFT', t.id, 'missing ' + ', '.join(t.missing_fields),
                f'autowork tasks field {t.id} <field> <value> from its accepted source; never invent it')
        elif t.section in ('Now', 'Next') and not t.runnable:
            if 'live' in t.resources and t.live.value != 'authorized':
                add('LIVE_NOT_AUTHORIZED', t.id, 'claims the live resource without an owner grant',
                    f'autowork tasks place {t.id} "Needs decision" --decision "<what the owner must grant>"')
            else:
                add('NOT_RUNNABLE', t.id, f'kind {t.kind.value}, ownership {t.ownership.value}',
                    'leave it unless an accepted decision names a worker contract; never grant authority')
        for dep in t.depends_on:
            if dep not in tasks:
                add('UNKNOWN_DEPENDENCY', t.id, f'depends on {dep!r}, which is no task',
                    f'autowork tasks field {t.id} depends_on <task IDs> from the evidence')
            elif tasks[dep].status == 'superseded':
                add('SUPERSEDED_DEPENDENCY', t.id, f'depends on superseded {dep}',
                    f"autowork tasks field {t.id} depends_on <{dep}'s successor>")
        if any(p == 'tasks' or p.startswith('tasks/') for p in t.touches):
            add('TOUCHES_TASK_STORE', t.id, 'touches lists tasks/, which only the coordinator writes',
                f'autowork tasks field {t.id} touches <paths outside tasks/>')
        if t.goal in goals and goals[t.goal].status == 'met':
            add('OPEN_TASK_UNDER_MET_GOAL', t.id, f'goal {t.goal} is met',
                f'autowork tasks goal {t.goal} --status partial, or close {t.id} with its evidence')
        for ref in LINK.findall(t.body):
            if reason := _target(repo, ref):
                add('BROKEN_SOURCE', t.id, reason, f'autowork tasks field {t.id} Sources "<accepted path#anchor>"')
        if t.id in held:
            add('IN_FLIGHT', t.id, 'a worker or lease holds it: rank, title and notes only',
                'change no contract field until its attempt ends')
    titles = {}
    for t in sorted(tasks.values(), key=lambda t: t.id):
        if t.status == 'open':
            titles.setdefault((t.goal, ' '.join(t.title.lower().split())), []).append(t.id)
    for ids in titles.values():
        for other in ids[1:]:
            add('DUPLICATE_TASK', other, f'same goal and title as {ids[0]}',
                f'autowork tasks supersede {other} --by {ids[0]} --reason "duplicate of the same outcome"')
    for g in goals.values():
        open_tasks = [t for t in tasks.values() if t.goal == g.id and t.status == 'open']
        if g.status != 'met' and not open_tasks:
            add('GOAL_WITHOUT_WORK', g.id, f'{g.status} with no open task',
                f'autowork tasks add --goal {g.id} ... for the evidenced remaining work, or '
                f'autowork tasks goal {g.id} --status met --evidence "<executed check>: pass"')
        if reason := _target(repo, g.source):
            add('BROKEN_SOURCE', g.id, reason, f'autowork tasks goal {g.id} --source "<accepted path#anchor>"')
    return sorted(found, key=lambda d: (d['id'], d['code'], d['detail']))


def _summary(store):
    counts = {}
    for t in store.tasks.values():
        key = t.status if t.status != 'open' else f'open:{t.section}'
        counts[key] = counts.get(key, 0) + 1
    return dict(tasks=len(store.tasks), goals=len(store.goals), counts=dict(sorted(counts.items())),
                drafts=sorted(t.id for t in store.tasks.values() if t.draft),
                order=[t.id for t in task_select.order(store)])


def detect(repo):
    """The repository's task-store state, from committed and working-tree facts only."""
    if task_migrate.pending(repo):
        return 'conversion_pending'
    head = _git(repo, 'rev-parse', '--verify', '-q', 'HEAD')
    if head and task_migrate.committed(repo, 'HEAD', 'tasks'):
        return 'converted'
    names = ('TODO.md', 'goals.json')
    if any((Path(repo) / name).exists() or (head and task_migrate.committed(repo, 'HEAD', name)) for name in names):
        return 'legacy'
    if any(p.is_file() for p in (Path(repo) / 'tasks').glob('*/*.md')):
        return 'uncommitted'
    return 'none'


def prepare(repo, mode='commit'):
    """One report dict; ``mode`` is check (read-only), stage (no commit) or commit."""
    top = _git(repo, 'rev-parse', '--show-toplevel')
    if not top:
        return dict(ok=False, state='no_repository', refusals=[f'{repo} is not a Git working tree'])
    repo = Path(top).resolve()
    if mode == 'check':
        return _prepare(repo, mode)
    with task_commands.locked(repo):
        return _prepare(repo, mode)


def _prepare(repo, mode):
    held, problems = task_commands.in_flight(repo, task_commands.ACTIVE)
    report = dict(ok=True, repo=str(repo), mode=mode, state=detect(repo), actions=[], refusals=[],
                  in_flight=sorted(held), pending=[], diagnostics=[])
    state = report['state']
    if state in ('legacy', 'conversion_pending'):
        if mode == 'check':
            return _check_conversion(repo, report)
        try:
            result = task_migrate.convert(repo, commit=mode == 'commit')
        except task_migrate.Refused as exc:
            report.update(ok=False, refusals=[str(exc)],
                          next='nothing was written; resolve the refusal, then run prepare again')
            return report
        report['actions'].append(dict(action='convert', **result))
        state = report['state'] = 'converted' if result['outcome'] in ('CONVERTED', 'ALREADY_CONVERTED') \
            else 'uncommitted'
    if state == 'none':
        report.update(intent(repo))
        report['next'] = ('bootstrap: add one goal per accepted outcome with `autowork tasks goal`, then its '
                          'tasks with `autowork tasks add`' if report['accepted'] else
                          'no heading is marked Status: Accepted; record accepted intent first, or report the '
                          'missing input; create no executable tasks')
        return report
    try:
        report['pending'] = list(TaskStore.pending(repo))
    except StoreError:
        report['pending'] = []
    store = None
    if report['pending'] and mode != 'check':
        try:
            store = worktree_store(repo)
            report['read'] = 'worktree'
        except StoreError as exc:
            report.update(ok=False, state='invalid', refusals=[str(exc)],
                          next='fix the named line of the uncommitted record, or revert it, then run again')
            return report
    if store is None:
        try:
            store = TaskStore.at(repo, 'HEAD')
            report['read'] = 'HEAD'
        except StoreError as exc:
            report.update(ok=False, state='invalid', refusals=[str(exc)],
                          next='the committed store is invalid: fix the named line from its accepted source '
                               'or Git history, then run again')
            return report
    report.update(_summary(store))
    report['diagnostics'] = diagnose(repo, store, held)
    report['next'] = ('reconcile accepted documents with these records through `autowork tasks`; '
                      'repair the diagnostics only from evidence')
    if problems:
        report['in_flight_state'] = problems
    return report


def _check_conversion(repo, report):
    """Read-only: what a conversion would do, without building its proof commit."""
    if candidate := task_migrate.pending(repo):
        report['would'] = f'finish the recorded conversion {candidate[:12]}'
        report['refusals'] = task_migrate.busy(repo)
        return report
    report['refusals'] = task_migrate.refusals(repo)
    if not report['refusals']:
        try:
            files, order, _ids = task_migrate.build(repo)
            report['would'] = dict(convert=len([p for p in files if p.startswith('tasks/items/')]),
                                   goals=len([p for p in files if p.startswith('tasks/goals/')]), order=order,
                                   set_aside=sorted(s['task_id'] for s in task_migrate.awaiting_answer(repo)))
        except task_migrate.Refused as exc:
            report['refusals'] = [str(exc)]
    report['ok'] = not report['refusals']
    return report
