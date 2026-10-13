"""End-to-end clerical recovery -> immutable input commit -> real initial guard.

No profiles, model workers or product repositories are mutated.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pass_workspace
import prepare_prerequisites
import retry_selection
import source_freshness

SCRIPTS = Path(__file__).parent
DOCS = SCRIPTS.parents[1] / 'docs-sync/scripts'


class BlockerRecoveryPipelineTests(unittest.TestCase):
    def test_missing_attributed_prerequisites_reach_clean_candidate_initial_admission(self):
        self.assert_recovery_pipeline()

    def test_continued_sources_binding_reaches_supported_admission(self):
        self.assert_recovery_pipeline(continued_sources=True)

    def assert_recovery_pipeline(self, continued_sources=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@local')
            (source / 'README.md').write_text('base\n')
            git('add', '.')
            git('commit', '-qm', 'Base')
            base = git('rev-parse', 'HEAD')
            plan = '# Slice\n\nStatus: Accepted\n\nCheck startup.\n'
            ledger = json.dumps({'version': 1, 'primary_milestone': 'G1',
                'goals': [{'id': 'G1', 'title': 'Startup', 'source': 'SPEC.md#slice',
                           'status': 'unmet', 'priority': 1, 'tasks': ['T1']}],
                'tasks': [{'id': 'T1', 'goal': 'G1', 'title': 'Startup', 'status': 'open', 'section': 'Now'}]})
            body = ('# TODO\n\n## Now\n\n- [ ] T1: Startup\n'
                    '  Goal: G1\n  Scope: Check startup\n  Acceptance: startup passes\n'
                    '  Dependencies: None\n  Ownership: fixture\n  Sources: [Plan](SPEC.md#slice)\n')
            for name, text in {'SPEC.md': plan, 'goals.json': ledger, 'TODO.md': body}.items():
                (source / name).write_text(text)
            git('add', '.')
            git('commit', '-qm', 'Accepted source fixture')
            authority_commit = git('rev-parse', 'HEAD')
            git('branch', 'accepted-fixture', authority_commit)
            git('checkout', '-q', '--detach', base)
            (source / 'SPEC.md').write_text(plan)
            (source / 'goals.json').write_text(ledger)
            if continued_sources:
                (source / 'TODO.md').write_text(body.replace(
                    '  Sources: [Plan](SPEC.md#slice)', '  Sources:\n    [Readme](README.md)'))
            else:
                (source / 'TODO.md').write_text('# TODO\n\n## Now\n')
            (source / 'foreign.txt').write_text('foreign staged bytes\n')
            git('add', 'foreign.txt')
            index = git('write-tree')
            revision = subprocess.check_output([sys.executable, str(DOCS / 'goals.py'), 'revision', str(source)], text=True).strip()
            recovered = subprocess.run([sys.executable, str(DOCS / 'recover_backlog.py'), str(source),
                '--plan', 'SPEC.md#slice', '--tasks', 'T1', '--expected-revision', revision,
                '--source-commit', authority_commit], capture_output=True, text=True, timeout=10)
            self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
            self.assertEqual(json.loads(recovered.stdout)['state'], 'ready_for_autowork')
            if continued_sources:
                self.assertEqual(json.loads(recovered.stdout)['repairs'], ['T1: linked accepted goal source'])
                self.assertIn('    [Readme](README.md)', (source / 'TODO.md').read_text())
            selected = retry_selection.select(source)
            self.assertEqual(selected['selected_task']['id'], 'T1')
            snapshot = source_freshness.capture(source, ['goals.json', 'TODO.md', 'SPEC.md'])
            attribution = {'version': 1, 'workspace': str(source), 'base': base,
                           'owner': 'fixture-integrator', 'evidence_ref': 'fixture://accepted-input-owner',
                           'files': snapshot['files']}
            prepared = prepare_prerequisites.prepare(source, root / 'inputs', base, snapshot, attribution,
                'fixture', 'inputs-T1', [['python3', '-c',
                    'import json; from pathlib import Path; assert json.loads(Path("goals.json").read_text())["tasks"][0]["id"] == "T1"']], 30)
            self.assertEqual(prepared['status'], 'committed')
            self.assertEqual(git('rev-parse', 'HEAD'), base)
            self.assertEqual(git('write-tree'), index)
            candidate = pass_workspace.prepare(source, root / 'worker', base, prepared['commit'],
                {'refs/heads/' + prepared['branch']: prepared['commit']}, ['goals.json', 'TODO.md', 'SPEC.md'])
            manifest = {'candidate_identity': candidate, 'source_workspace': str(source),
                        'files': snapshot['files'], 'ledger_sha256': snapshot['files'][0]['sha256']}
            self.assertTrue(pass_workspace.verify(manifest, root / 'worker'))
            manifest_path = root / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            admitted = subprocess.run([sys.executable, str(SCRIPTS / 'pass_workspace.py'),
                '--manifest', str(manifest_path), '--manifest-sha256', hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                '--workspace', str(root / 'worker')], capture_output=True, text=True, timeout=10)
            self.assertEqual(admitted.returncode, 0, admitted.stdout + admitted.stderr)
            self.assertEqual(json.loads(admitted.stdout)['outcome'], 'worker_start_admitted')
            snapshot_path = root / 'snapshot.json'
            snapshot_path.write_text(json.dumps(snapshot))
            contract_path = root / 'contract.txt'
            contract_path.write_text('\n'.join(label + ': fixture startup' for label in (
                'Objective', 'Scope', 'Verification', 'Source', 'Project payoff', 'Current evidence',
                'Expected change', 'Acceptance', 'Stop conditions', 'Repo-docs pass')))
            validated = subprocess.run([sys.executable, str(SCRIPTS / 'start_goal.py'),
                '--profile', 'fixture', '--workspace', str(source), '--title', 'Startup',
                '--contract-file', str(contract_path), '--goal-task', 'T1',
                '--source-snapshot', str(snapshot_path), '--validate-only'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
            self.assertEqual(json.loads(validated.stdout)['admission']['goal_task'], 'T1')
            self.assertFalse((root / 'worker' / 'foreign.txt').exists())
            self.assertEqual((source / 'foreign.txt').read_text(), 'foreign staged bytes\n')
            self.assertEqual(git('write-tree'), index)
            print('RECOVERY_FIXTURE ' + json.dumps({
                'case': 'continued_sources' if continued_sources else 'missing_body',
                'base': base, 'accepted_history': authority_commit,
                'prerequisite_ref': 'refs/heads/' + prepared['branch'],
                'prerequisite_commit': prepared['commit'], 'files': snapshot['files'],
                'candidate_commit': candidate['candidate_commit'],
                'initial_guard': json.loads(admitted.stdout)['outcome'],
                'validation': json.loads(validated.stdout)['outcome'],
                'goal_task': json.loads(validated.stdout)['admission']['goal_task'],
                'boundary': 'real_git_fixture_no_native_dispatch'}, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
