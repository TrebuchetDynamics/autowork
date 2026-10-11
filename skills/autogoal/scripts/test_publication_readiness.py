"""Exact permitted publication targets, exercised against local bare remotes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class PublicationReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@local')
        (self.repo / 'README.md').write_text('fixture\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Base')
        self.sha = self.git('rev-parse', 'HEAD')
        for name in ('origin', 'other'):
            remote = self.root / (name + '.git')
            subprocess.run(['git', 'init', '-q', '--bare', str(remote)], check=True)
            self.git('remote', 'add', name, str(remote))
        self.contract = 'Fixture contract'
        self.authority = {'version': 1, 'workspace': str(self.repo), 'profile': 'fixture',
                          'goal_task': 'T1', 'contract_sha256': hashlib.sha256(self.contract.encode()).hexdigest(),
                          'remote': 'other', 'ref': 'refs/heads/agent/fixture/T1',
                          'owner': 'fixture-integrator', 'evidence_ref': 'fixture://publish-decision'}

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def readiness(self, authority=None):
        self.assertIsNotNone(importlib.util.find_spec('publication'), 'missing exact-target readiness helper')
        import publication
        return publication.readiness(self.repo, self.sha, self.sha, authority,
                                     'fixture', 'T1', self.contract)

    def test_missing_authority_and_multiple_push_destinations_remain_decisions(self):
        self.assertEqual(self.readiness()['state'], 'publication_decision_required')
        self.git('config', '--add', 'remote.other.pushurl', str(self.root / 'origin.git'))
        self.git('config', '--add', 'remote.other.pushurl', str(self.root / 'other.git'))
        result = self.readiness(self.authority)
        self.assertEqual(result['state'], 'publication_decision_required')
        self.assertIn('multiple push destinations', result['reason'])

    def test_ancestry_conflict_never_becomes_force_push_readiness(self):
        (self.repo / 'README.md').write_text('remote successor\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Remote successor')
        successor = self.git('rev-parse', 'HEAD')
        self.git('push', '-q', 'other', successor + ':' + self.authority['ref'])
        result = self.readiness(self.authority)
        self.assertEqual(result['state'], 'publication_conflict')
        self.assertEqual(result['remote_commit'], successor)
        self.assertFalse(result['main_delivered'])

    def test_contract_mismatch_and_main_target_are_refused(self):
        for changed in ({'ref': 'refs/heads/main'}, {'contract_sha256': '0' * 64}, {'remote': '--all'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.readiness(dict(self.authority, **changed))

    def test_multiple_remotes_are_resolved_by_bound_authority_not_origin_guess(self):
        before = self.git('status', '--porcelain')
        result = self.readiness(self.authority)
        self.assertEqual(result['state'], 'ready_to_publish')
        self.assertEqual(result['remote'], 'other')
        self.assertEqual(result['remote_commit'], None)
        self.git('push', '-q', 'other', self.sha + ':' + self.authority['ref'])
        result = self.readiness(self.authority)
        self.assertEqual(result['state'], 'published_exact_ref')
        self.assertEqual(result['remote_commit'], self.sha)
        self.assertFalse(result['main_delivered'])
        self.assertEqual(self.git('ls-remote', '--heads', 'origin', self.authority['ref']), '')
        self.assertEqual(self.git('status', '--porcelain'), before)


if __name__ == '__main__':
    unittest.main()
