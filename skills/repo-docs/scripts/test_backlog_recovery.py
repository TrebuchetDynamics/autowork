"""Recovery is clerical, source-bound and leaves owner intent/leases unchanged."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('recover_backlog.py')
GOALS = Path(__file__).with_name('goals.py')


class BacklogRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@local')
        (self.repo / 'SPEC.md').write_text('# Slice\n\nStatus: Accepted\n\nCheck startup.\n')
        self.body = ('# TODO\n\n## Now\n\n- [ ] T1: Startup\n'
                     '  Goal: G1\n  Scope: Check startup\n  Acceptance: startup passes\n'
                     '  Dependencies: None\n  Ownership: fixture\n'
                     '  Sources: [Slice](SPEC.md#slice)\n')
        (self.repo / 'TODO.md').write_text(self.body)
        (self.repo / 'goals.json').write_text(json.dumps({
            'version': 1, 'goals': [{'id': 'G1', 'title': 'Startup', 'source': 'SPEC.md#slice',
                                    'status': 'unmet', 'priority': 1, 'tasks': ['T1']}],
            'tasks': [{'id': 'T1', 'goal': 'G1', 'title': 'Startup', 'status': 'open', 'section': 'Now'}]}))
        self.git('add', '.')
        self.git('commit', '-qm', 'Accepted fixture')
        self.pin = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def invoke(self, *extra):
        revision = subprocess.check_output([sys.executable, str(GOALS), 'revision', str(self.repo)], text=True).strip()
        return subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--plan', 'SPEC.md#slice',
                               '--tasks', 'T1', '--expected-revision', revision, *extra],
                              capture_output=True, text=True, timeout=10)

    def test_restore_legacy_complete_body_uses_same_shared_consumer_parser(self):
        (self.repo / 'README.md').write_text('fixture\n')
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Now / Next\n\n'
            '- [ ] **T1** — Goal: G1. Startup\n'
            '  Scope: Check startup\n  Acceptance: startup passes\n'
            '  Sources: [Readme](README.md),\n    [Slice](SPEC.md#slice).\n'
            '  Dependencies: None. Section: Now. Ownership: fixture\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Accepted legacy fixture')
        pin = self.git('rev-parse', 'HEAD')
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Now\n')
        result = self.invoke('--source-commit', pin)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['state'], 'ready_for_autowork')

    def test_byte_identical_duplicate_contract_is_deduplicated_without_owner_decision(self):
        entry = '- [ ] T1' + self.body.split('- [ ] T1', 1)[1]
        (self.repo / 'TODO.md').write_text(self.body + entry)
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['repairs'], ['T1: removed identical duplicate body'])
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)

    def test_consumer_reads_inline_goal_multiline_sources_and_explicit_combined_section(self):
        (self.repo / 'README.md').write_text('fixture\n')
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Now / Next\n\n'
            '- [ ] **T1** — Goal: G1. Startup\n'
            '  Scope: Check startup\n  Acceptance: startup passes\n'
            '  Sources: [Readme](README.md),\n    [Slice](SPEC.md#slice).\n'
            '  Dependencies: None. Section: Now. Ownership: fixture\n')
        before = (self.repo / 'TODO.md').read_bytes()
        result = subprocess.run([sys.executable, str(GOALS), 'backlog-check', str(self.repo),
                                 '--plan', 'SPEC.md#slice', '--tasks', 'T1'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['state'], 'ready_for_autowork')
        self.assertEqual(before, (self.repo / 'TODO.md').read_bytes())

    def test_binding_repair_changes_selected_body_not_matching_foreign_line(self):
        (self.repo / 'README.md').write_text('fixture\n')
        line = '  Sources: [Other](README.md)'
        first = self.body.replace('  Sources: [Slice](SPEC.md#slice)', line)
        second = first.split('- [ ] T1', 1)[1].replace(': Startup', ': Second', 1)
        (self.repo / 'TODO.md').write_text(first + '\n- [ ] T2' + second)
        ledger_path = self.repo / 'goals.json'
        data = json.loads(ledger_path.read_text())
        data['goals'][0]['tasks'].append('T2')
        data['tasks'].append({'id': 'T2', 'goal': 'G1', 'title': 'Second', 'status': 'open', 'section': 'Now'})
        ledger_path.write_text(json.dumps(data))
        result = self.invoke('--tasks', 'T2')
        self.assertEqual(result.returncode, 2, result.stderr)
        text = (self.repo / 'TODO.md').read_text()
        one, two = text.split('- [ ] T2', 1)
        self.assertNotIn('[Accepted plan]', one)
        self.assertIn('[Accepted plan](SPEC.md#slice)', two)

    def test_empty_missing_and_duplicate_sources_are_not_manufactured(self):
        for sources in ('', '  Sources:\n', '  Sources: [One](README.md)\n  Sources: [Two](README.md)\n'):
            with self.subTest(sources=sources):
                (self.repo / 'README.md').write_text('fixture\n')
                (self.repo / 'TODO.md').write_text(self.body.replace('  Sources: [Slice](SPEC.md#slice)\n', sources))
                before = (self.repo / 'TODO.md').read_bytes()
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('unique nonempty Sources', result.stderr)
                self.assertEqual(before, (self.repo / 'TODO.md').read_bytes())

    def test_proposed_plan_and_duplicate_bodies_are_not_changed(self):
        for text, status in ((self.body, 'Proposed'), (self.body + self.body.split('## Now', 1)[1], 'Accepted')):
            with self.subTest(status=status):
                (self.repo / 'SPEC.md').write_text('# Slice\n\nStatus: ' + status + '\n')
                (self.repo / 'TODO.md').write_text(text)
                before = (self.repo / 'TODO.md').read_bytes()
                result = self.invoke('--source-commit', self.pin)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before, (self.repo / 'TODO.md').read_bytes())

    def test_changed_task_intent_cannot_restore_historical_body(self):
        (self.repo / 'TODO.md').write_text('# TODO\n')
        ledger_path = self.repo / 'goals.json'
        data = json.loads(ledger_path.read_text())
        data['tasks'][0]['title'] = 'Different product outcome'
        ledger_path.write_text(json.dumps(data))
        result = self.invoke('--source-commit', self.pin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('immutable task intent differs', result.stderr)
        self.assertEqual((self.repo / 'TODO.md').read_text(), '# TODO\n')

    def test_restore_missing_body_from_immutable_same_task_then_ready(self):
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Now\n\nOwner notes stay.\n')
        ledger = (self.repo / 'goals.json').read_bytes()
        result = self.invoke('--source-commit', self.pin)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['state'], 'ready_for_autowork')
        self.assertEqual(receipt['repairs'], ['T1: restored committed task body'])
        self.assertIn('Owner notes stay.', (self.repo / 'TODO.md').read_text())
        self.assertEqual(ledger, (self.repo / 'goals.json').read_bytes())
        before = (self.repo / 'TODO.md').read_bytes()
        repeated = self.invoke('--source-commit', self.pin)
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(json.loads(repeated.stdout)['repairs'], [])
        self.assertEqual(before, (self.repo / 'TODO.md').read_bytes())


if __name__ == '__main__':
    unittest.main()
