"""`autowork migrate`: a TODO.md + goals.json repository converts to tasks/ once, losslessly."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'pi-autowork/pi_autowork/command.py'
GOALS = ROOT / 'skills/docs-sync/scripts/goals.py'
sys.path.insert(0, str(ROOT / 'pi-autowork/engine'))
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork.legacy import reader  # noqa: E402
from task_store import TaskStore  # noqa: E402

EVIDENCE = [{'kind': 'executed', 'ref': 'fixture check', 'result': 'pass'}]


def entry(tid, title, goal, done=False, **fields):
    lines = [f'### {tid} — {title}', '', f'- [{"x" if done else " "}] {tid} — {title}',
             f'- Short: {title}', f'- Status: {"done" if done else "open"}', f'- Goal: {goal}',
             '- Scope: change it', '- Acceptance: it works', '- Checks: python3 -m unittest']
    lines += [f'- {label.replace("_", " ")}: {value}' for label, value in fields.items()]
    return '\n'.join(lines) + '\n\n'


TODO = ('# Work queue\n\n## Now\n\n'
        + entry('T-001', 'Alpha', 'G1', Touches='src/a.py', Resources='port:8080 — the dev server',
                Dependencies='None.', Sources='[plan](docs/plan.md)')
        + entry('T-002', 'Beta', 'G2', Touches='src/b.py', Dependencies='T-001')
        + entry('T-003', 'Gamma', 'G1', Dependencies='None.', Kind='plan')
        + '## Next\n\n'
        + entry('T-004', 'Delta', 'G2', Touches='src/d.py', Ownership='Owner only',
                Live_authorization='granted 2026-10-20 for the staging deploy', Dependencies='None.')
        + entry('T-005', 'Epsilon', 'G1', Touches='src/e.py', Dependencies='T-006 (archived)')
        + '## Needs decision\n\n'
        + entry('T-007', 'Eta', 'G1', Touches='src/h.py', Dependencies='None.', Owner_decision='2026-10-20: later')
        + entry('T-006', 'Zeta', 'G3', done=True, Touches='src/z.py', Dependencies='None.'))


def ledger():
    task = lambda tid, goal, section, status='open', deps=(): dict(
        id=tid, title=tid, goal=goal, section=section, status=status, depends_on=list(deps))
    return {'version': 1, 'primary_milestone': 'G2',
            'goals': [dict(id='G1', title='One', source='TODO.md', status='unmet', priority=2, depends_on=[],
                           tasks=['T-001', 'T-003', 'T-005', 'T-007']),
                      dict(id='G2', title='Two', source='TODO.md', status='partial', priority=1, depends_on=[],
                           tasks=['T-002', 'T-004']),
                      dict(id='G3', title='Three', source='TODO.md', status='met', priority=3, depends_on=[],
                           tasks=['T-006'], evidence=EVIDENCE)],
            'tasks': [task('T-001', 'G1', 'Now'), task('T-002', 'G2', 'Now', deps=['T-001']),
                      task('T-003', 'G1', 'Now'), task('T-004', 'G2', 'Next'),
                      task('T-005', 'G1', 'Next', deps=['T-006']), task('T-007', 'G1', 'Needs decision'),
                      task('T-006', 'G3', 'Done', 'done')]}


class MigrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        (self.repo / 'TODO.md').write_text(TODO)
        (self.repo / 'goals.json').write_text(json.dumps(ledger(), indent=2))
        archived = subprocess.run([sys.executable, str(GOALS), 'archive', str(self.repo)],
                                  capture_output=True, text=True)
        self.assertEqual(archived.returncode, 0, archived.stderr)
        self.assertIn('T-006', archived.stdout)
        order = subprocess.run([sys.executable, str(GOALS), 'bootstrap-order', str(self.repo), '--dry-run'],
                               capture_output=True, text=True)
        revision = json.loads(order.stdout)['revision']
        subprocess.run([sys.executable, str(GOALS), 'bootstrap-order', str(self.repo), '--expected-revision',
                        revision], check=True, capture_output=True)
        self.commit()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=f@example.invalid',
                               '-c', 'user.name=F', *args], check=True, capture_output=True, text=True).stdout

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', 'fixture')

    def migrate(self, *args):
        return subprocess.run([sys.executable, str(COMMAND), 'migrate', str(self.repo), *args],
                              capture_output=True, text=True, timeout=120)

    def test_migration_keeps_order_and_fields(self):
        legacy = reader.order(self.repo)
        recorded = json.loads((self.repo / 'goals.json').read_text())['priority_order']['tasks']
        # Focus G2 first (T-004, though in Next; T-002 waits for T-001), then Now, then Next.
        self.assertEqual(legacy, ['T-004', 'T-001', 'T-003', 'T-005'])
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual((summary['outcome'], summary['order']), ('CONVERTED', legacy))
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse((self.repo / 'TODO.md').exists())
        self.assertFalse((self.repo / 'goals.json').exists())
        self.assertTrue((self.repo / 'TODO.archive.md').exists())
        self.assertIn('autowork migrate', self.git('log', '-1', '--format=%s'))
        store = TaskStore.at(self.repo, 'HEAD')
        t = store.tasks
        # The engine reads `port:8080 — ...` as the resource `port`; conversion keeps that meaning.
        self.assertEqual((t['T-001'].touches, t['T-001'].resources), (('src/a.py',), ('port',)))
        self.assertIn('- Resources: port:8080 — the dev server', t['T-001'].body)
        self.assertIn('- Sources: [plan](docs/plan.md)', t['T-001'].body)
        self.assertEqual((t['T-002'].depends_on, t['T-003'].kind.value, t['T-003'].touches), (('T-001',), 'plan', ('**',)))
        self.assertEqual((t['T-004'].ownership.value, t['T-004'].live.value, t['T-004'].section), ('worker', 'authorized', 'Next'))
        self.assertIn('- Ownership: Owner only', t['T-004'].body)
        self.assertEqual((t['T-005'].depends_on, t['T-006'].status), (('T-006',), 'done'))
        self.assertEqual((t['T-007'].section, t['T-007'].scope, t['T-007'].acceptance), ('Needs decision', 'change it', ('it works',)))
        self.assertIn('- Owner decision: 2026-10-20: later', t['T-007'].body)
        self.assertEqual([t[tid].rank for tid in recorded], [1000 * (n + 1) for n in range(len(recorded))])
        g = store.goals
        self.assertEqual((g['G2'].focus, g['G1'].focus, g['G3'].status), (True, False, 'met'))
        self.assertIn('- Evidence: executed: fixture check (pass)', g['G3'].body)
        self.assertEqual(self.migrate().returncode, 1, 'a converted repository is refused')

    def test_migration_refuses_unsafe_states(self):
        common = self.repo / '.git/autowork-execution'
        cases = {
            'uncommitted planning files': lambda: (self.repo / 'TODO.md').write_text(TODO + '\n'),
            'worker slots in flight': lambda: self.slot('running'),
            'unfinished integration/closure': lambda: self.slot('integrating'),
            'claimed tasks': lambda: self.claim(),
            'already converted': lambda: (self.repo / 'tasks').mkdir(),
        }
        for message, make in cases.items():
            with self.subTest(state=message):
                make()
                head = self.git('rev-parse', 'HEAD')
                result = self.migrate('--dry-run')
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(message.split(' (')[0].split('/')[0], result.stderr)
                self.assertEqual(self.git('rev-parse', 'HEAD'), head)
                self.git('checkout', '-q', '--', '.')
                for leftover in (self.repo / 'tasks', common / 'slots'):
                    if leftover.exists():
                        subprocess.run(['rm', '-rf', str(leftover)], check=True)

    def slot(self, state):
        folder = self.repo / '.git/autowork-execution/slots'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'T-001.json').write_text(json.dumps({'task_id': 'T-001', 'state': state, 'attempt': 1}))

    def claim(self):
        data = json.loads((self.repo / 'goals.json').read_text())
        data['tasks'][0]['status'] = 'in_progress'
        (self.repo / 'goals.json').write_text(json.dumps(data, indent=2))
        self.commit()

    def test_a_placeholder_live_authorization_is_not_a_grant(self):
        text = (self.repo / 'TODO.md').read_text()
        grant = '- Live authorization: granted 2026-10-20 for the staging deploy'
        for value in ('none', 'n/a', 'Pending owner review', 'not yet', 'TBD', 'denied', 'unknown (ask owner)'):
            with self.subTest(value=value):
                (self.repo / 'TODO.md').write_text(text.replace(grant, f'- Live authorization: {value}'))
                self.commit()
                refused = self.migrate('--dry-run')
                self.assertEqual(refused.returncode, 1, refused.stdout)
                self.assertIn(f'T-004: "Live authorization: {value}" is not a grant', refused.stderr)
        (self.repo / 'TODO.md').write_text(text)
        self.commit()
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(TaskStore.at(self.repo, 'HEAD').tasks['T-004'].live.value, 'authorized')

    def test_a_repeated_note_is_kept_and_a_repeated_typed_field_refused(self):
        text = (self.repo / 'TODO.md').read_text()
        alpha = '- Sources: [plan](docs/plan.md)'
        (self.repo / 'TODO.md').write_text(text.replace(alpha, alpha + '\n- Evidence: first run\n- Evidence: second run'))
        self.commit()
        self.assertEqual(self.migrate().returncode, 0)
        body = TaskStore.at(self.repo, 'HEAD').tasks['T-001'].body
        self.assertIn('- Evidence: first run\n- Evidence: second run', body)

    def test_two_entries_for_one_task_refuse(self):
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('## Next', entry('T-001', 'Alpha again', 'G1') + '## Next'))
        self.commit()
        refused = self.migrate('--dry-run')
        self.assertEqual(refused.returncode, 1)
        self.assertIn('T-001', refused.stderr)

    def test_a_repeated_typed_field_refuses(self):
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('- Touches: src/a.py', '- Touches: src/a.py\n- Touches: src/z.py'))
        self.commit()
        refused = self.migrate('--dry-run')
        self.assertEqual(refused.returncode, 1)
        self.assertIn('T-001: Touches written more than once', refused.stderr)

    def test_migration_refuses_unlossless_input(self):
        dry = self.migrate('--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)['outcome'], 'DRY_RUN')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')
        self.assertTrue((self.repo / 'TODO.md').exists())
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('- Touches: src/a.py', '- Touches: /etc/passwd'))
        self.commit()
        refused = self.migrate()
        self.assertEqual(refused.returncode, 1)
        self.assertIn('T-001: Touches cannot be converted', refused.stderr)
        self.assertFalse((self.repo / 'tasks').exists())


if __name__ == '__main__':
    unittest.main()
