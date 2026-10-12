"""Real repositories: isolate attributed prerequisites, never commit a dirty union."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import source_freshness
import importlib.util


class PrerequisiteRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@local')
        (self.repo / 'README.md').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Base')
        self.base = self.git('rev-parse', 'HEAD')
        (self.repo / 'goals.json').write_text('{"accepted":true}\n')
        (self.repo / 'TODO.md').write_text('accepted task body\n')
        (self.repo / 'foreign.txt').write_text('foreign dirty content\n')
        self.git('add', 'foreign.txt')
        self.snapshot = source_freshness.capture(self.repo, ['goals.json', 'TODO.md'])
        self.authority = {'version': 1, 'workspace': str(self.repo), 'base': self.base,
                          'owner': 'fixture-integrator', 'evidence_ref': 'fixture://accepted-input-attribution',
                          'files': self.snapshot['files']}
        self.target = self.root / 'private'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def test_pinned_preparation_commit_refuses_foreign_preexisting_task_parent(self):
        import os
        foreign = self.git('commit-tree', self.git('write-tree'), '-p', self.base, '-m', 'Foreign parent')
        self.git('update-ref', 'refs/heads/agent/fixture/inputs', foreign)
        result = subprocess.run(['bash', str(Path(__file__).with_name('agent_commit.sh')),
            str(self.repo), 'fixture', 'inputs', 'Prepare pinned inputs', 'goals.json', 'TODO.md'],
            env={**os.environ, 'AGENT_COMMIT_EXPECTED_BASE': self.base}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git('rev-parse', 'refs/heads/agent/fixture/inputs'), foreign)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)

    def test_stale_attribution_refuses_before_any_worktree_or_ref(self):
        import prepare_prerequisites as recovery
        (self.repo / 'TODO.md').write_text('new concurrent input\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            recovery.prepare(self.repo, self.target, self.base, self.snapshot, self.authority,
                             'fixture', 'inputs', [['python3', '-c', 'pass']], 30)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.git('for-each-ref', '--format=%(refname)', 'refs/heads/agent/'), '')

    def test_missing_provenance_and_foreign_file_attribution_are_refused(self):
        import prepare_prerequisites as recovery
        for changed in ({'evidence_ref': ''}, {'files': self.snapshot['files'][:-1]}, {'base': '0' * 40}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                recovery.prepare(self.repo, self.target, self.base, self.snapshot,
                                 dict(self.authority, **changed), 'fixture', 'inputs',
                                 [['python3', '-c', 'pass']], 30)
            self.assertFalse(self.target.exists())

    def test_failed_acceptance_does_not_commit_and_removes_private_worktree(self):
        import prepare_prerequisites as recovery
        before = self.git('status', '--porcelain')
        with self.assertRaisesRegex(ValueError, 'acceptance/commit failed'):
            recovery.prepare(self.repo, self.target, self.base, self.snapshot, self.authority,
                             'fixture', 'inputs', [['python3', '-c', 'raise SystemExit(7)']], 30)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.git('for-each-ref', '--format=%(refname)', 'refs/heads/agent/'), '')
        self.assertEqual(self.git('status', '--porcelain'), before)

    def test_attributed_dirty_inputs_become_verified_private_commit(self):
        self.assertIsNotNone(importlib.util.find_spec('prepare_prerequisites'), 'missing attributable-input recovery helper')
        import prepare_prerequisites as recovery
        before = self.git('status', '--porcelain')
        index = self.git('write-tree')
        result = recovery.prepare(self.repo, self.target, self.base, self.snapshot, self.authority,
                                  'fixture', 'inputs', [['python3', '-c',
                                  'from pathlib import Path; assert Path("TODO.md").read_text()=="accepted task body\\n"']], 30)
        self.assertEqual(result['status'], 'committed')
        self.assertEqual(result['authority_validation'], 'caller_attribution_not_independent_authorization')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)
        self.assertEqual(self.git('write-tree'), index)
        self.assertEqual(self.git('status', '--porcelain'), before)
        commit = result['commit']
        self.assertEqual(self.git('show', commit + ':TODO.md'), 'accepted task body')
        absent = subprocess.run(['git', '-C', str(self.repo), 'cat-file', '-e', commit + ':foreign.txt'], capture_output=True)
        self.assertNotEqual(absent.returncode, 0)
        self.assertEqual(self.git('rev-parse', 'refs/heads/' + result['branch']), commit)


if __name__ == '__main__':
    unittest.main()
