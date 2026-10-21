"""Tests only: turn a fixture written in the old TODO.md + goals.json form into a tasks/ store.

Fixtures keep describing their scenario as TODO entries; this converts them with
`autowork migrate`'s own mapping (offline, no refusal checks, no proof against the old
queue) so the engine reads them from tasks/ as it reads any repository. A TODO.md without
goals.json gets one goal, `FIXTURE`, holding every task.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import task_migrate  # noqa: E402
from pi_autowork.legacy import reader  # noqa: E402

FIXTURE_GOAL = 'FIXTURE'


def _ledger_for(todo):
    """A ledger for a TODO.md-only fixture: one goal, each task's checkbox and section kept."""
    bodies = reader.task_bodies(todo)
    tasks = []
    for tid, items in bodies.items():
        body, mark, section = items[0]
        if section not in ('Now', 'Next', 'Needs decision', None, ''):
            continue  # a loose checklist line (a Backlog idea) was never an indexed task
        fields = reader.task_fields(body)
        status = 'done' if mark.lower() == 'x' else (fields.get('Status', 'open').split()[0].strip('.;') or 'open')
        status = status if status in ('open', 'done', 'superseded') else 'open'
        tasks.append(dict(id=tid, title=tid, goal=FIXTURE_GOAL, status=status, depends_on=[],
                          section={'done': 'Done', 'superseded': 'Superseded'}.get(status, section or 'Now')))
    return {'version': 1, 'goals': [dict(id=FIXTURE_GOAL, title='Fixture', source='TODO.md', status='unmet',
                                         priority=1, depends_on=[], tasks=[t['id'] for t in tasks])],
            'tasks': tasks}


def write_todo(repo, text, ledger=None, *, commit=True):
    """Write a fixture's TODO.md text (and an optional goals.json ledger) and convert it at once."""
    repo = Path(repo)
    (repo / 'TODO.md').write_text(text)
    if ledger is not None:
        (repo / 'goals.json').write_text(ledger if isinstance(ledger, str) else json.dumps(ledger, indent=2))
    return convert(repo, commit=commit)


def convert(repo, *, commit=True, message='fixture: tasks/ store'):
    """Write tasks/ from the fixture's TODO.md (and goals.json), remove both, and commit. A
    fixture that writes a new TODO.md later converts again: the old tasks/items and goals go."""
    repo = Path(repo)
    for folder in ('tasks/items', 'tasks/goals'):
        shutil.rmtree(repo / folder, ignore_errors=True)
    synthesized = not (repo / 'goals.json').exists()
    if synthesized:
        (repo / 'goals.json').write_text(json.dumps(_ledger_for((repo / 'TODO.md').read_text()), indent=2))
    files, _order, _ids = task_migrate.build(repo)
    for path, text in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(text)
    for name in ('TODO.md', 'goals.json'):
        (repo / name).unlink(missing_ok=True)
    if commit:
        git = ['git', '-C', str(repo), '-c', 'user.email=fixture@example.invalid', '-c', 'user.name=Fixture']
        if subprocess.run(['git', '-C', str(repo), 'rev-parse', '--show-toplevel'], capture_output=True,
                          text=True).stdout.strip() != str(repo.resolve()):
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        subprocess.run([*git, 'add', '-A', '--', 'tasks'], check=True, capture_output=True)
        subprocess.run([*git, 'rm', '-q', '--cached', '--ignore-unmatch', '--', 'TODO.md', 'goals.json'],
                       check=True, capture_output=True)
        subprocess.run([*git, 'commit', '-q', '--allow-empty', '-m', message], check=True, capture_output=True)
    return sorted(files)
