"""task_select over TaskStore matches the TODO.md selector, fixture by fixture.

Each fixture is written once and built both ways in one Git repository: TODO.md,
goals.json and TODO.archive.md for the current selector, and the equivalent tasks/
tree (rank = 1000 x the recorded human order) for the new one.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import time
import tracemalloc
import unittest

import task_execution
import task_select
from task_store import TaskStore

MET = [{'kind': 'executed', 'ref': 'fixture check', 'result': 'pass'}]


def goal(gid, priority=1, status='unmet', depends_on=()):
    return dict(id=gid, priority=priority, status=status, depends_on=list(depends_on))


def task(tid, gid='G', section='Now', status='open', depends_on=(), draft=False, kind=''):
    return dict(id=tid, goal=gid, section=section, status=status, depends_on=list(depends_on),
                draft=draft, kind=kind)


# name -> (focus goal, goals, tasks in human order, expected order)
FIXTURES = {
    'human order within a section': (None, [goal('G')], [task('B'), task('A'), task('C')], ['B', 'A', 'C']),
    'Now before Next': (None, [goal('G')], [task('N1', section='Next'), task('N2')], ['N2', 'N1']),
    'Needs decision never runs': (None, [goal('G')], [task('D', section='Needs decision'), task('A')], ['A']),
    'focus goal first': ('F', [goal('G'), goal('F', priority=9)],
                         [task('A'), task('B', 'F', section='Next')], ['B', 'A']),
    'cross-goal priority keeps human order': (None, [goal('G', 2), goal('H', 1)],
                                              [task('A'), task('B', 'H')], ['A', 'B']),
    'an unmet dependency blocks': (None, [goal('G')],
                                   [task('A', depends_on=['B']), task('B'), task('C')], ['B', 'C']),
    'a done (archived) dependency is satisfied': (None, [goal('G')],
                                                  [task('X', status='done'), task('A', depends_on=['X'])], ['A']),
    'a met goal runs nothing': (None, [goal('G'), goal('M', status='met')],
                                [task('A'), task('Z', 'M', status='done')], ['A']),
    'a superseded task never runs': (None, [goal('G')], [task('S', status='superseded'), task('A')], ['A']),
    'a draft is not runnable': (None, [goal('G')], [task('A', draft=True), task('B')], ['B']),
    'an unmet goal dependency blocks': (None, [goal('G'), goal('H', depends_on=['G'])],
                                        [task('B', 'H'), task('A')], ['A']),
    'planning tasks are ordered, not next': (None, [goal('G')], [task('P', kind='plan'), task('A')], ['P', 'A']),
}


def legacy_body(t):
    acceptance = '' if t['draft'] else '- Acceptance: x\n'
    kind = f"- Kind: {t['kind']}\n" if t['kind'] else ''
    deps = ', '.join(t['depends_on']) or 'None.'
    mark = 'x' if t['status'] == 'done' else ' '
    return (f"### {t['id']} — {t['id']}\n\n- [{mark}] {t['id']} — {t['id']}\n- Status: {t['status']}\n"
            f"- Goal: {t['goal']}\n- Scope: x\n{acceptance}- Checks: true\n- Dependencies: {deps}\n{kind}\n")


def store_file(t, rank):
    lines = ['+++', 'schema = 1', f'id = "{t["id"]}"', f'title = "{t["id"]}"', f'short = "{t["id"]}"',
             f'status = "{t["status"]}"', f'goal = "{t["goal"]}"', f'section = "{t["section"]}"',
             f'rank = {rank}', 'depends_on = ' + json.dumps(t['depends_on']), 'touches = ["src/"]',
             'resources = []', f'kind = "{t["kind"] or "implementation"}"', 'ownership = "worker"',
             'live = "denied"', 'scope = "x"', 'checks = ["true"]', 'exclusions = []']
    if not t['draft']:
        lines.append('acceptance = ["x"]')
    return '\n'.join(lines + ['+++', 'Notes.', ''])


def build(root, focus, goals, tasks):
    """Write both forms of one fixture into a fresh repository and commit it."""
    root.mkdir()
    sections = {'Now': [], 'Next': [], 'Needs decision': []}
    archive = []
    for t in tasks:
        (archive if t['status'] in ('done', 'superseded') else sections[t['section']]).append(legacy_body(t))
    (root / 'TODO.md').write_text('# Work\n\n' + ''.join(f'## {name}\n\n' + ''.join(bodies)
                                                        for name, bodies in sections.items()))
    (root / 'TODO.archive.md').write_text('# Completed tasks\n\n' + ''.join(
        body for t, body in zip([t for t in tasks if t['status'] in ('done', 'superseded')], archive)
        if t['status'] == 'done'))
    # The human order is TODO.md's sequence (sections in order); ranks follow it, as conversion does.
    order = [t for name in sections for t in tasks
             if t['status'] not in ('done', 'superseded') and t['section'] == name]
    order += [t for t in tasks if t['status'] in ('done', 'superseded')]
    active = [t['id'] for t in order if t['status'] not in ('done', 'superseded')]
    ledger = {'version': 1, 'priority_order': {'schema': 1, 'tasks': active}, 'goals': [
        dict(id=g['id'], title=g['id'], source='TODO.md', status=g['status'], priority=g['priority'],
             depends_on=g['depends_on'], tasks=[t['id'] for t in tasks if t['goal'] == g['id']],
             **({'evidence': MET} if g['status'] == 'met' else {})) for g in goals],
        'tasks': [dict(id=t['id'], title=t['id'], goal=t['goal'], status=t['status'], depends_on=t['depends_on'],
                       section={'done': 'Done', 'superseded': 'Superseded'}.get(t['status'], t['section']),
                       **({'superseded_by': [active[0]], 'supersession_reason': 'fixture'}
                          if t['status'] == 'superseded' else {}))
                  for t in tasks]}
    if focus:
        ledger['primary_milestone'] = focus
    (root / 'goals.json').write_text(json.dumps(ledger, indent=2))
    for folder in ('tasks/items', 'tasks/goals'):
        (root / folder).mkdir(parents=True)
    for index, t in enumerate(order):
        (root / f'tasks/items/{t["id"]}.md').write_text(store_file(t, 1000 * (index + 1)))
    for g in goals:
        (root / f'tasks/goals/{g["id"]}.md').write_text('\n'.join([
            '+++', 'schema = 1', f'id = "{g["id"]}"', f'title = "{g["id"]}"', f'priority = {g["priority"]}',
            'source = "TODO.md"', f'status = "{g["status"]}"', f'focus = {"true" if g["id"] == focus else "false"}',
            'depends_on = ' + json.dumps(g['depends_on']), '+++', '']))
    git = lambda *args: subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
    git('init', '-q')
    git('-c', 'user.email=f@example.invalid', '-c', 'user.name=F', 'add', '.')
    git('-c', 'user.email=f@example.invalid', '-c', 'user.name=F', 'commit', '-qm', 'fixture')
    return TaskStore.at(root, 'HEAD')


def legacy_order(root):
    try:
        return [contract['id'] for contract in task_execution.select_all(root)]
    except task_execution.NoEligibleTask:
        return []


def legacy_next(root):
    try:
        return task_execution.select(root, None, None)['id']
    except task_execution.NoEligibleTask:
        return None


class SelectionParityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_each_fixture_selects_like_the_todo_queue(self):
        for index, (name, (focus, goals, tasks, expected)) in enumerate(FIXTURES.items()):
            with self.subTest(fixture=name):
                root = Path(self.tmp.name) / f'f{index}'
                store = build(root, focus, goals, tasks)
                new = [t.id for t in task_select.order(store)]
                self.assertEqual(legacy_order(root), expected, 'the recorded expectation is the current selector')
                self.assertEqual(new, expected)
                picked = task_select.next(store)
                self.assertEqual(picked.id if picked else None, legacy_next(root))


class WhyTests(unittest.TestCase):
    def test_why_names_the_blocking_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            goals = [goal('G'), goal('M', status='met'), goal('H', depends_on=['G'])]
            tasks = [task('A'), task('B'), task('D', section='Needs decision'), task('X', depends_on=['A']),
                     task('S', status='superseded'), task('R', draft=True), task('Z', 'M', status='done'),
                     task('W', 'M'), task('Y', 'H'), task('N', section='Next')]
            store = build(Path(tmp) / 'repo', None, goals, tasks)
            expected = {'D': 'NEEDS_DECISION', 'X': 'DEPENDENCY_UNFINISHED', 'S': 'SUPERSEDED',
                        'R': 'DRAFT', 'Z': 'DONE', 'W': 'GOAL_MET', 'Y': 'GOAL_DEPENDENCY_UNMET',
                        'Q': 'UNKNOWN_TASK'}
            for tid, code in expected.items():
                with self.subTest(task=tid):
                    first, reasons = task_select.why(store, tid)
                    self.assertFalse(first)
                    self.assertEqual(reasons[0].code, code)
            self.assertEqual(task_select.why(store, 'X')[1][0].detail, 'A')
            self.assertEqual(task_select.why(store, 'A'), (True, [task_select.Reason('POSITION', '1')]))
            self.assertEqual(task_select.why(store, 'B')[1],
                             [task_select.Reason('POSITION', '2'), task_select.Reason('AFTER_RANK', 'A')])
            self.assertEqual(task_select.why(store, 'N')[1][1], task_select.Reason('AFTER_SECTION', 'B'))


class ScaleMeasurement(unittest.TestCase):
    """A baseline for a later budget, not a pass/fail gate."""
    def test_measure_a_thousand_task_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            tasks = [task(f'T{n:04d}', depends_on=[f'T{n - 1:04d}'] if n % 7 else []) for n in range(1000)]
            build(root, None, [goal('G')], tasks)
            tracemalloc.start()
            started = time.perf_counter()
            store = TaskStore.at(root, 'HEAD')
            ordered = task_select.order(store)
            seconds = time.perf_counter() - started
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            self.assertEqual(len(store.tasks), 1000)
            self.assertTrue(ordered)
            print(f'\n1,000-task store: read and ordered in {seconds:.2f}s, peak {peak / 2**20:.1f} MiB')


if __name__ == '__main__':
    unittest.main()
