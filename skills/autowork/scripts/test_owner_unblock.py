"""Real Git owner recovery, no native dispatch or product fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import retry_selection
import source_freshness

SCRIPT = Path(__file__).with_name('owner_unblock.py')


class OwnerUnblockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@local')
        (self.repo / 'README.md').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        (self.repo / 'SPEC.md').write_text('# Slice\n\nStatus: Accepted\n')
        self.ledger = {'version': 1, 'primary_milestone': 'G1', 'goals': [
            {'id': 'G1', 'title': 'Slice', 'source': 'SPEC.md#slice', 'status': 'unmet', 'priority': 1, 'tasks': ['T1']}],
            'tasks': [{'id': 'T1', 'goal': 'G1', 'title': 'Slice', 'status': 'open', 'section': 'Now'}]}
        self.save_ledger()
        self.body = ('# TODO\n\n## Now\n\n- [ ] T1: Slice\n  Goal: G1\n'
            '  Scope: startup\n  Acceptance: startup passes\n  Dependencies: None\n'
            '  Ownership: fixture\n  Sources: [Readme](README.md)\n')
        (self.repo / 'TODO.md').write_text(self.body)
        (self.repo / 'foreign.txt').write_bytes(b'foreign staged\x00bytes')
        self.git('add', 'foreign.txt')
        self.index = self.git('write-tree')
        self.revision = retry_selection.goals.revision(self.repo)
        self.authority = {'version': 1, 'workspace': str(self.repo), 'plan': 'SPEC.md#slice',
            'task_ids': ['T1'], 'expected_revision': self.revision, 'source_commit': None,
            'owner': 'fixture-owner', 'evidence_ref': 'fixture://owner', 'no_overlapping_writer': True}
        self.auth = self.root / 'authority.json'
        self.auth.write_text(json.dumps(self.authority))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def save_ledger(self):
        (self.repo / 'goals.json').write_text(json.dumps(self.ledger))

    def run_cli(self, *args):
        self.assertTrue(SCRIPT.is_file(), 'missing executable owner-side composition')
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--plan', 'SPEC.md#slice',
            '--tasks', 'T1', *args], text=True, capture_output=True, timeout=30)
        self.assertTrue(result.stdout, result.stderr)
        return result, json.loads(result.stdout)

    def accepted_history(self, status='Status: Accepted', missing_body=False):
        plan = '# Slice\n\n' + status + '\nScope: startup only\n\n# Foreign\nStatus: Proposed\nForeign bytes\n'
        (self.repo / 'SPEC.md').write_text(plan)
        self.git('add', 'SPEC.md', 'TODO.md', 'goals.json')
        self.git('commit', '-qm', 'immutable plan fixture')
        pin = self.git('rev-parse', 'HEAD')
        current = plan.replace(status + '\n', 'Status: Accepted (implementation only)\n', 1)
        (self.repo / 'SPEC.md').write_text(current)
        if missing_body:
            (self.repo / 'TODO.md').write_text('# TODO\n\n## Now\n')
        self.authority.update(expected_revision=retry_selection.goals.revision(self.repo),
                              accepted_plan_source_commit=pin, source_commit=pin if missing_body else None)
        self.auth.write_text(json.dumps(self.authority))
        return plan, current

    def test_metadata_and_link_repair_ready_preserves_foreign_bytes(self):
        plan, current = self.accepted_history()
        plan = plan.replace('Foreign bytes', 'Uncommitted foreign bytes')
        (self.repo / 'SPEC.md').write_text(current.replace('Foreign bytes', 'Uncommitted foreign bytes'))
        head, index = self.git('rev-parse', 'HEAD'), self.git('write-tree')
        result, receipt = self.run_cli('--apply', '--authority', str(self.auth))
        self.assertEqual(result.returncode, 0, receipt)
        self.assertEqual(receipt['selection']['selected_task']['id'], 'T1')
        self.assertEqual((self.repo / 'SPEC.md').read_text(), plan)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('write-tree'), index)
        self.assertEqual((self.repo / 'foreign.txt').read_bytes(), b'foreign staged\x00bytes')

    def test_missing_metadata_with_body_repair_ready(self):
        plan, current = self.accepted_history(missing_body=True)
        (self.repo / 'SPEC.md').write_text(current.replace('Status: Accepted (implementation only)\n', '', 1))
        result, receipt = self.run_cli('--apply', '--authority', str(self.auth))
        self.assertEqual(result.returncode, 0, receipt)
        self.assertEqual((self.repo / 'SPEC.md').read_text(), plan)
        self.assertIn('T1: restored committed task body', receipt['stages'][1]['repairs'])

    def test_metadata_recovery_rejects_invalid_evidence_without_any_write(self):
        for case in ('scope', 'proposed_source', 'missing_pin', 'short_pin', 'tree_pin',
                     'stale', 'in_progress', 'bad_body_source', 'duplicate_status', 'unrelated'):
            with self.subTest(case=case):
                fixture = OwnerUnblockTests()
                fixture.setUp()
                try:
                    _, current = fixture.accepted_history('Status: Proposed' if case == 'proposed_source' else 'Status: Accepted',
                                                         missing_body=case == 'bad_body_source')
                    if case == 'scope':
                        (fixture.repo / 'SPEC.md').write_text(current.replace('startup only', 'other scope'))
                    elif case == 'missing_pin':
                        del fixture.authority['accepted_plan_source_commit']
                    elif case == 'short_pin':
                        fixture.authority['accepted_plan_source_commit'] = 'HEAD'
                    elif case == 'tree_pin':
                        fixture.authority['accepted_plan_source_commit'] = fixture.git('rev-parse', 'HEAD^{tree}')
                    elif case == 'stale':
                        fixture.authority['expected_revision'] = 'stale'
                    elif case == 'in_progress':
                        fixture.ledger['tasks'][0]['status'] = 'in_progress'
                        fixture.save_ledger()
                    elif case == 'bad_body_source':
                        fixture.authority['source_commit'] = fixture.base
                    elif case == 'duplicate_status':
                        (fixture.repo / 'SPEC.md').write_text(current.replace('Scope:', 'Status: Proposed\nScope:', 1))
                    elif case == 'unrelated':
                        (fixture.repo / 'README.md').unlink()
                    fixture.auth.write_text(json.dumps(fixture.authority))
                    before = {name: (fixture.repo / name).read_bytes() for name in ('SPEC.md', 'TODO.md', 'goals.json', 'foreign.txt')}
                    head, index = fixture.git('rev-parse', 'HEAD'), fixture.git('write-tree')
                    result, receipt = fixture.run_cli('--apply', '--authority', str(fixture.auth))
                    self.assertNotEqual(result.returncode, 0, receipt)
                    self.assertEqual({name: (fixture.repo / name).read_bytes() for name in before}, before)
                    self.assertEqual(fixture.git('rev-parse', 'HEAD'), head)
                    self.assertEqual(fixture.git('write-tree'), index)
                finally:
                    fixture.doCleanups()

    def test_historical_acceptance_cannot_overwrite_current_unaccepted_status(self):
        for status in ('Proposed', 'Rejected', 'Draft', 'Superseded'):
            with self.subTest(status=status):
                fixture = OwnerUnblockTests()
                fixture.setUp()
                try:
                    _, current = fixture.accepted_history()
                    (fixture.repo / 'SPEC.md').write_text(current.replace('Accepted (implementation only)', status, 1))
                    fixture.authority['expected_revision'] = retry_selection.goals.revision(fixture.repo)
                    fixture.auth.write_text(json.dumps(fixture.authority))
                    before = {name: (fixture.repo / name).read_bytes() for name in ('SPEC.md', 'TODO.md', 'goals.json')}
                    result, receipt = fixture.run_cli('--apply', '--authority', str(fixture.auth))
                    self.assertNotEqual(result.returncode, 0, receipt)
                    self.assertEqual({name: (fixture.repo / name).read_bytes() for name in before}, before)
                finally:
                    fixture.doCleanups()

    def test_gated_task_contract_can_be_repaired_without_releasing_gate(self):
        self.ledger['tasks'][0]['section'] = 'Needs decision'
        self.save_ledger()
        todo = self.repo / 'TODO.md'
        todo.write_text(self.body.replace('## Now', '## Needs decision'))
        ledger_before = (self.repo / 'goals.json').read_bytes()
        self.authority['expected_revision'] = retry_selection.goals.revision(self.repo)
        self.auth.write_text(json.dumps(self.authority))
        _, diagnosis = self.run_cli()
        self.assertEqual(diagnosis['gate'], 'accepted_body_repair')
        result, receipt = self.run_cli('--apply', '--authority', str(self.auth))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt['gate'], 'consumer_readiness')
        self.assertEqual([s['stage'] for s in receipt['stages']], ['diagnose', 'repair', 'retry_selection'])
        self.assertIn('[Accepted plan](SPEC.md#slice)', todo.read_text())
        self.assertEqual((self.repo / 'goals.json').read_bytes(), ledger_before)
        self.assertIsNone(receipt['selection']['selected_task'])
        self.assertTrue(any('section=Needs decision' in r for r in receipt['required_inputs']))

    def test_binding_repair_retries_same_invocation_preserves_foreign_index(self):
        result, receipt = self.run_cli('--apply', '--authority', str(self.auth))
        self.assertEqual(result.returncode, 0, receipt)
        self.assertEqual(receipt['selection']['selected_task']['id'], 'T1')
        self.assertEqual(receipt['gate'], 'ready_for_autowork')
        self.assertEqual(receipt['task_goals'], {'T1': 'G1'})
        self.assertEqual([s['stage'] for s in receipt['stages']], ['diagnose', 'repair', 'retry_selection'])
        self.assertEqual(self.git('write-tree'), self.index)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)
        self.assertEqual((self.repo / 'foreign.txt').read_bytes(), b'foreign staged\x00bytes')

    def test_repair_and_explicit_prerequisites_reach_candidate_validation(self):
        expected_body = self.body.replace('[Readme](README.md)', '[Readme](README.md) [Accepted plan](SPEC.md#slice)')
        snapshot = source_freshness.capture(self.repo, ['goals.json', 'TODO.md', 'SPEC.md'])
        for row in snapshot['files']:
            if row['path'] == 'TODO.md':
                row['sha256'] = hashlib.sha256(expected_body.encode()).hexdigest()
        attribution = {'version': 1, 'workspace': str(self.repo), 'base': self.base,
            'owner': 'fixture-owner', 'evidence_ref': 'fixture://accepted-inputs', 'files': snapshot['files']}
        request = {'source': str(self.repo), 'target': str(self.root / 'inputs'), 'base': self.base,
            'snapshot': snapshot, 'attribution': attribution, 'profile': 'fixture', 'task': 'inputs-T1',
            'checks': [['python3', '-c', 'from pathlib import Path; assert "Accepted plan" in Path("TODO.md").read_text()']],
            'candidate_target': str(self.root / 'candidate'), 'required_paths': ['goals.json', 'TODO.md', 'SPEC.md']}
        path = self.root / 'request.json'
        path.write_text(json.dumps(request))
        result, receipt = self.run_cli('--apply', '--authority', str(self.auth), '--prerequisite-request', str(path))
        self.assertEqual(result.returncode, 0, receipt)
        self.assertEqual(receipt['gate'], 'candidate_validated')
        self.assertEqual(receipt['selection']['selected_task']['id'], 'T1')
        self.assertEqual(receipt['candidate_manifest']['candidate_identity']['candidate_commit'], receipt['prerequisites']['commit'])
        self.assertEqual(self.git('write-tree'), self.index)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)
        self.assertFalse((self.root / 'candidate' / 'foreign.txt').exists())

    def test_missing_body_requires_and_uses_same_task_immutable_source(self):
        (self.repo / 'TODO.md').write_text(self.body.replace('[Readme](README.md)', '[Accepted plan](SPEC.md#slice)'))
        self.git('add', 'SPEC.md', 'TODO.md', 'goals.json')
        self.git('commit', '-qm', 'accepted same-task source')
        pin = self.git('rev-parse', 'HEAD')
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Now\n')
        self.authority.update(expected_revision=retry_selection.goals.revision(self.repo), source_commit=pin)
        self.auth.write_text(json.dumps(self.authority))
        result, receipt = self.run_cli('--apply', '--authority', str(self.auth))
        self.assertEqual(result.returncode, 0, receipt)
        self.assertEqual(receipt['selection']['selected_task']['id'], 'T1')
        self.assertIn('T1: restored committed task body', receipt['stages'][1]['repairs'])

    def test_stale_revision_and_unattributed_prerequisites_refuse(self):
        self.authority['expected_revision'] = 'stale'
        self.auth.write_text(json.dumps(self.authority))
        result, receipt = self.run_cli('--apply', '--authority', str(self.auth))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['gate'], 'refused')
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)

    def test_existing_candidate_request_is_verified_without_prerequisite_invention(self):
        (self.repo / 'TODO.md').write_text(self.body.replace('[Readme](README.md)', '[Accepted plan](SPEC.md#slice)'))
        self.git('add', 'TODO.md', 'goals.json', 'SPEC.md')
        self.git('commit', '-qm', 'accepted candidate')
        snapshot = source_freshness.capture(self.repo, ['TODO.md', 'goals.json', 'SPEC.md'])
        request = {'source': str(self.repo), 'target': str(self.root / 'candidate'), 'base': self.base,
            'candidate': self.git('rev-parse', 'HEAD'), 'prerequisites': {},
            'required_paths': ['TODO.md', 'goals.json', 'SPEC.md'], 'snapshot': snapshot}
        path = self.root / 'candidate.json'
        path.write_text(json.dumps(request))
        result, receipt = self.run_cli('--apply', '--candidate-request', str(path))
        self.assertEqual(result.returncode, 0, receipt)
        self.assertEqual(receipt['gate'], 'candidate_validated')
        self.assertNotIn('prerequisites', receipt)

    def test_mismatched_candidate_snapshot_refuses_before_creating_workspace(self):
        (self.repo / 'TODO.md').write_text(self.body.replace('[Readme](README.md)', '[Accepted plan](SPEC.md#slice)'))
        self.git('add', 'TODO.md', 'goals.json', 'SPEC.md')
        self.git('commit', '-qm', 'accepted candidate')
        snapshot = source_freshness.capture(self.repo, ['TODO.md', 'goals.json', 'SPEC.md'])
        snapshot['workspace'] = str(self.root / 'unrelated')
        target = self.root / 'candidate'
        request = {'source': str(self.repo), 'target': str(target), 'base': self.base,
                   'candidate': self.git('rev-parse', 'HEAD'), 'prerequisites': {},
                   'required_paths': ['TODO.md', 'goals.json', 'SPEC.md'], 'snapshot': snapshot}
        path = self.root / 'candidate.json'
        path.write_text(json.dumps(request))
        result, receipt = self.run_cli('--apply', '--candidate-request', str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['gate'], 'refused')
        self.assertFalse(target.exists(), 'invalid request created a candidate workspace')

    def test_explicit_authority_fields_cannot_be_inferred(self):
        for key in ('owner', 'evidence_ref', 'source_commit', 'no_overlapping_writer'):
            with self.subTest(key=key):
                authority = dict(self.authority)
                del authority[key]
                self.auth.write_text(json.dumps(authority))
                result, receipt = self.run_cli('--apply', '--authority', str(self.auth))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(receipt['gate'], 'refused')
                self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)

    def test_absent_consumer_ledger_returns_earliest_required_input(self):
        (self.repo / 'goals.json').unlink()
        _, receipt = self.run_cli()
        self.assertEqual(receipt['gate'], 'ledger')
        self.assertIn('goals.json', receipt['required_inputs'])
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)

    def test_diagnose_does_not_mutate_and_names_required_authority(self):
        _, receipt = self.run_cli()
        self.assertEqual(receipt['gate'], 'accepted_body_repair')
        self.assertIn('authority', receipt['required_inputs'])
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)

    def test_missing_authority_refuses_without_write(self):
        result, receipt = self.run_cli('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['gate'], 'owner_authority')
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)

    def test_in_progress_ownership_refuses_before_repair(self):
        self.ledger['tasks'][0]['status'] = 'in_progress'
        self.save_ledger()
        _, receipt = self.run_cli('--apply', '--authority', str(self.auth))
        self.assertEqual(receipt['gate'], 'ownership')
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)


if __name__ == '__main__':
    unittest.main()
