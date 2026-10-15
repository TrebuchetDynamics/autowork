"""Retirement preserves unpassed acceptance and never satisfies dependencies."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('goals.py')


def archived_form(block):
    """A body as archived: trailing blank lines are a separator, not content (TOOLSET-042)."""
    nl = (b'\r\n' if b'\r\n' in block else b'\n') if isinstance(block, bytes) else ('\r\n' if '\r\n' in block else '\n')
    return block.rstrip(b'\r\n' if isinstance(block, bytes) else '\r\n') + nl


class SupersessionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.ledger = self.repo/'goals.json'; self.todo = self.repo/'TODO.md'
        self.archive = self.repo/'TODO.archive.md'
        self.old = ('- [ ] OLD: Native recovery\n  Goal: G\n  Scope: original operation\n'
                    '  Acceptance: native check passes\n  Dependencies: None\n'
                    '  Sources: [Plan](SPEC.md#intent)\n  Status: blocked\n'
                    '  - [ ] Original acceptance not executed\n  Evidence: native check failed\n\n')
        def body(tid, deps):
            return (f'- [ ] {tid}: Replacement work\n  Goal: G\n  Scope: direct execution\n'
                    f'  Acceptance: offline checks pass\n  Dependencies: {deps}\n'
                    '  Sources: [Plan](SPEC.md#intent)\n\n')
        self.todo.write_text('# TODO\n\n## Now\n\n' + self.old + body('NEW', 'None') + body('WAIT', 'OLD'))
        (self.repo/'SPEC.md').write_text('# Intent\n\nStatus: Accepted\n')
        self.data = {'version': 1, 'goals': [
            {'id': 'G', 'title': 'Execution', 'source': 'SPEC.md#intent', 'status': 'partial',
             'tasks': ['OLD', 'NEW', 'WAIT'], 'evidence': [
                 {'kind': 'executed', 'ref': 'old native check', 'result': 'fail'}]}],
            'tasks': [{'id': tid, 'goal': 'G', 'title': tid, 'status': 'open', 'section': 'Now',
                       'depends_on': ['OLD'] if tid == 'WAIT' else []}
                      for tid in ('OLD', 'NEW', 'WAIT')]}
        self.ledger.write_text(json.dumps(self.data))

    def cli(self, command, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), command, str(self.repo), *args],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def supersede(self):
        return self.cli('supersede', 'OLD', '--by', 'NEW', '--reason', 'Accepted card-free replacement')

    def test_disposition_does_not_complete_or_unlock_dependencies(self):
        before = self.todo.read_bytes(); self.supersede()
        data = json.loads(self.ledger.read_text())
        old = next(t for t in data['tasks'] if t['id'] == 'OLD')
        self.assertEqual(old['status'], 'superseded')
        self.assertEqual(old['section'], 'Superseded')
        self.assertEqual(old['superseded_by'], ['NEW'])
        self.assertEqual(old['supersession_reason'], 'Accepted card-free replacement')
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertEqual(data['goals'][0]['evidence'], self.data['goals'][0]['evidence'])
        picks = json.loads(self.cli('next', '--json').stdout)
        self.assertEqual([p['task']['id'] for p in picks], ['NEW'])
        self.cli('validate')

    def test_archive_preserves_unchecked_original_and_repeat_is_byte_stable(self):
        self.supersede(); self.cli('render')
        archived = self.archive.read_text()
        for fragment in (archived_form(self.old), 'Superseded; not completed', 'Successors: NEW', 'Accepted card-free replacement'):
            self.assertIn(fragment, archived)
        self.assertNotIn(self.old, self.todo.read_text())
        self.assertIn('- [ ] NEW:', self.todo.read_text())
        before = tuple(p.read_bytes() for p in (self.ledger, self.todo, self.archive))
        self.supersede(); self.cli('render'); self.cli('archive')
        self.assertEqual(tuple(p.read_bytes() for p in (self.ledger, self.todo, self.archive)), before)
        result = self.cli('backlog-check', '--plan', 'SPEC.md#intent', '--tasks', 'NEW')
        self.assertEqual(json.loads(result.stdout)['state'], 'ready_for_autowork')

    def test_successor_completion_does_not_pass_old_dependency_or_goal(self):
        self.supersede(); self.cli('task', 'NEW', 'done')
        self.assertEqual(json.loads(self.cli('next', '--json').stdout), [])
        self.cli('task', 'WAIT', 'done')
        self.cli('evidence', 'G', '--kind', 'executed', '--ref', 'new check', '--result', 'pass')
        self.assertEqual(json.loads(self.ledger.read_text())['goals'][0]['status'], 'partial')

    def test_invalid_supersession_writes_nothing(self):
        before = self.ledger.read_bytes()
        for successors, reason in (('', 'reason'), ('MISSING', 'reason'), ('OLD', 'reason'),
                                   ('NEW', ' '), ('WAIT', 'reason')):
            with self.subTest(successors=successors, reason=reason):
                self.cli('supersede', 'OLD', '--by', successors, '--reason', reason, expected=1)
                self.assertEqual(self.ledger.read_bytes(), before)

    def test_supersession_cannot_silently_be_completed_or_reopened(self):
        self.supersede(); before = self.ledger.read_bytes()
        for status in ('done', 'open', 'in_progress'):
            self.cli('task', 'OLD', status, expected=1)
            self.assertEqual(self.ledger.read_bytes(), before)
        self.cli('section', 'OLD', 'Now', expected=1)

    def test_completed_task_cannot_be_relabelled_superseded(self):
        self.cli('task', 'OLD', 'done'); before = self.ledger.read_bytes()
        self.cli('supersede', 'OLD', '--by', 'NEW', '--reason', 'replacement', expected=1)
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_missing_metadata_is_invalid_and_cannot_archive(self):
        self.data['tasks'][0]['status'] = 'superseded'
        self.ledger.write_text(json.dumps(self.data)); self.cli('validate', expected=1)
        before = self.todo.read_bytes(); self.cli('render', expected=1)
        self.assertEqual(self.todo.read_bytes(), before); self.assertFalse(self.archive.exists())

    def test_supersession_chain_cycle_is_rejected(self):
        self.supersede(); before = self.ledger.read_bytes()
        self.cli('supersede', 'NEW', '--by', 'OLD', '--reason', 'cycle', expected=1)
        self.assertEqual(self.ledger.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
