import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests/fixtures"))
"""Offline original-card preservation and independent task admission checks."""
import hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

class DisjointFallbackTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.workspace = self.root / 'original'
        self.workspace.mkdir()
        self.base = 'a' * 40
        self.registry = self.repo / 'writers.jsonl'
        self.registry.write_text('')
        expected = dict(card='old', task='T1', workspace=str(self.workspace), base=self.base, scope=['src/reader.rs'])
        self.requirement = self.root / 'requirement.json'
        self.requirement.write_text(json.dumps(dict(registry=str(self.registry), sha256=self.digest(self.registry), fields={k: k for k in expected}, expected=expected)))
        self.manifest = self.root / 'manifest.json'
        manifest = dict(candidate_identity=dict(base_commit=self.base, workspace=str(self.workspace)), goal_task='T1', source_workspace=str(self.repo))
        self.manifest.write_text(json.dumps(manifest))
        self.handoff = self.root / 'goal-handoff.json'
        self.handoff.write_text(json.dumps(dict(task_id='old', profile='fixture', board_id='board', goal_task='T1', workspace=str(self.workspace), source_workspace=str(self.repo), goal_max_turns=50, max_retries=1, pass_manifest=manifest, pass_manifest_path=str(self.manifest), pass_manifest_sha256=self.digest(self.manifest))))
        self.declaration = self.root / 'declaration.json'
        self.declaration.write_text(json.dumps(dict(registry=str(self.registry), scope=['tests/layout.py'])))
        self.evidence = self.root / 'disjoint.json'
        self.payload = dict(version=1, original_handoff_sha256=self.digest(self.handoff), original_card='old', original_task='T1', original_workspace=str(self.workspace), original_base=self.base, original_run_id=3, original_requirement=str(self.requirement), original_requirement_sha256=self.digest(self.requirement), goal_task='T2', scope=['tests/layout.py'], reason='Accepted standalone contract repair uses no reader resources', evidence_ref='TODO.md#T2')
        self.native = dict(task=dict(id='old', title='Original reader', assignee='fixture', board_id='board', status='blocked', workspace_kind='dir', workspace_path=str(self.workspace), current_run_id=None, worker_pid=None, goal_mode=True, goal_max_turns=50, max_retries=1, completion_contract='local-only', body=str(self.requirement) + ' ' + self.digest(self.requirement)), runs=[dict(id=3, status='blocked', outcome='blocked', ended_at=10)])

    def digest(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def check(self):
        import disjoint_fallback
        self.evidence.write_text(json.dumps(self.payload))
        with patch.object(disjoint_fallback.registration, 'native_observation', return_value=self.native):
            return disjoint_fallback.verify(self.evidence, self.handoff, self.repo, 'fixture', 'T2', self.declaration)

    def test_distinct_scope_preserves_original_broken_registration(self):
        before = [p.read_bytes() for p in (self.handoff, self.requirement, self.registry)]
        result = self.check()
        self.assertEqual(result['original_card'], 'old')
        self.assertEqual(result['goal_task'], 'T2')
        self.assertEqual(before, [p.read_bytes() for p in (self.handoff, self.requirement, self.registry)])

    def test_live_or_unknown_claim_and_changed_run_refused(self):
        for field, value in [('current_run_id', 5), ('worker_pid', 123), ('status', 'running')]:
            with self.subTest(field=field):
                old = self.native['task'][field]
                self.native['task'][field] = value
                with self.assertRaises(ValueError):
                    self.check()
                self.native['task'][field] = old
        self.native['runs'].append(dict(id=4, status='blocked', ended_at=11))
        with self.assertRaises(ValueError):
            self.check()

    def test_same_task_or_directory_overlap_refused(self):
        for key, value in [('goal_task', 'T1'), ('scope', ['src']), ('scope', ['src/reader.rs']), ('scope', ['src/reader.rs/new'])]:
            with self.subTest(value=value):
                old = self.payload[key]
                self.payload[key] = value
                with self.assertRaises(ValueError):
                    self.check()
                self.payload[key] = old

    def test_unbound_scope_or_registration_or_handoff_refused(self):
        for key, value in [('scope', ['other.py']), ('original_base', 'b' * 40), ('original_handoff_sha256', '0' * 64), ('original_requirement_sha256', '0' * 64)]:
            with self.subTest(key=key):
                old = self.payload[key]
                self.payload[key] = value
                with self.assertRaises(ValueError):
                    self.check()
                self.payload[key] = old
        self.native['task']['body'] = 'unbound requirement'
        with self.assertRaises(ValueError):
            self.check()
if __name__ == '__main__':
    unittest.main()

class ComposedDisjointTests(unittest.TestCase):

    def test_verified_distinct_task_reaches_native_handoff_and_forwards_registration(self):
        import legacy_owner_cycle as owner_cycle, contextlib, io
        from test_owner_cycle import ComposedReadyTests
        fixture = ComposedReadyTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.ready_backlog()
        evidence = fixture.root / 'disjoint.json'
        evidence.write_text('{}')
        declaration = fixture.root / 'registration.json'
        declaration.write_text('{}')
        report = dict(original_card='old', goal_task='T1', original_preserved=True)
        native = dict(exit_code=0, result=dict(outcome='handed_off', task_id='new', goal_mode=True, status='ready'))
        with patch.object(owner_cycle.reconcile, 'profile_home', return_value=fixture.root), patch.object(owner_cycle.reconcile, 'reconcile', return_value=dict(task_id='old', next_action='recover_original_card')), patch.object(owner_cycle, 'handoff', return_value=native) as dispatch, patch('disjoint_fallback.verify', return_value=report), contextlib.redirect_stdout(io.StringIO()):
            code = owner_cycle.main([str(fixture.repo), '--profile', 'fixture', '--plan', 'SPEC.md#slice', '--tasks', 'T1', '--state-dir', str(fixture.state), '--source-path', 'code.py', '--apply', '--disjoint-blocked-handoff', str(evidence), '--registration-declaration', str(declaration), '--registration-native-python', '/fixture/native-python'])
        self.assertEqual(code, 0)
        dispatch.assert_called_once()
        request = json.loads((fixture.state / 'handoff-requests/T1.json').read_text())
        self.assertEqual(request['options']['registration-declaration'], str(declaration))
        self.assertEqual(request['options']['registration-native-python'], '/fixture/native-python')
        self.assertEqual(request['options']['disjoint-blocked-handoff'], str(evidence))
