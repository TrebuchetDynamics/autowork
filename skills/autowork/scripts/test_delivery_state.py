"""Real isolated Git/helper evidence; no native board or provider execution."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
import candidate_identity
import check_receipt
import delivery_state as m

SCRATCH = (Path.home() / '.hermes/cache/scratch/executable-safeguards/state-repair')
SCRATCH.mkdir(parents=True, exist_ok=True)


class EvidenceFixture:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.repo = Path(self.temp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.base = self.commit('base\n')
        self.git('update-ref', 'refs/heads/main', self.base)
        self.commit_id = self.commit('candidate\n', self.base)
        self.git('update-ref', 'refs/heads/candidate', self.commit_id)
        self.identity = candidate_identity.capture(self.repo, self.base, 'refs/heads/candidate')
        self.command = [sys.executable, '-c', 'from pathlib import Path; assert Path("a.py").read_text() == "candidate\\n"']
        self.scope = {'platform': 'linux', 'backend': 'offline', 'mode': 'fixture',
                      'toolchain': {'python': sys.version}}
        self.receipt = self.execute()
        self.evidence = {'candidate': self.identity, 'implementation': {'artifacts': ['a.py']},
                         'qualification': {'candidate': self.identity, 'required_checks': ['unit'],
                                           'checks': [self.check()]}}
        return self

    def git(self, *args, text=None):
        import subprocess
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.repo), *args], input=text, text=True, stderr=subprocess.PIPE).strip()

    def commit(self, text, parent=None):
        blob = self.git('hash-object', '-w', '--stdin', text=text)
        tree = self.git('mktree', text=f'100644 blob {blob}\ta.py\n')
        return self.git('commit-tree', tree, *(['-p', parent] if parent else []), text=text)

    def execute(self, command=None, scope=None):
        return check_receipt.execute(self.repo, ['a.py'], command or self.command, 10,
                                     candidate=self.identity, qualification_scope=scope or self.scope,
                                     external_paths=[])

    def check(self):
        return {'name': 'unit', 'command': self.command, 'paths': ['a.py'], 'external_paths': [],
                'qualification_scope': self.scope, 'receipt': self.receipt,
                'platform': 'linux', 'backend': 'offline', 'mode': 'fixture', 'result': 'passed'}

    def integrated(self):
        self.git('update-ref', 'refs/heads/main', self.commit_id)
        self.evidence['integration'] = {'candidate': self.identity, 'action': 'merge', 'before': self.base,
            'after': self.commit_id, 'target': 'refs/heads/main', 'provenance': {
                'source': 'protected_pr', 'id': 'fixture-pr-1', 'observed': True, 'protected': True,
                'required_checks': 'passed', 'head': self.commit_id, 'merge_commit': self.commit_id}}
        return self.evidence

    def __exit__(self, *args):
        self.temp.cleanup()

    def local_integration(self):
        self.git('update-ref', 'refs/heads/main', self.commit_id)
        policy = {'version': 1, 'mode': 'reviewed_local', 'candidate': self.identity,
                  'target': 'refs/heads/main', 'authority': 'fixture-standing-policy',
                  'implementer': 'worker', 'reviewers': ['reviewer']}
        self.evidence['integration'] = {
            'candidate': self.identity, 'action': 'merge', 'before': self.base,
            'after': self.commit_id, 'target': 'refs/heads/main', 'provenance': {
                'source': 'reviewed_local', 'authority': policy['authority'], 'observed': True,
                'review': {'candidate': self.identity, 'reviewer': 'reviewer',
                           'implementer': 'worker', 'id': 'fixture-review',
                           'observed': True, 'outcome': 'approved'}}}
        return policy


class DeliveryStateTests(unittest.TestCase):
    def test_historical_local_delivery_survives_main_descendants_only(self):
        for merged in (False, True):
            for changed_tree in (False, True):
                with self.subTest(merged=merged, changed_tree=changed_tree), EvidenceFixture() as f:
                    policy = f.local_integration()
                    after = f.commit_id
                    if merged:
                        after = f.git('commit-tree', f.identity['candidate_tree'],
                                      '-p', f.base, '-p', f.commit_id, text='integration\n')
                        f.evidence['integration']['after'] = after
                    tree = (f.git('rev-parse', f.commit('later\n', after) + '^{tree}')
                            if changed_tree else f.identity['candidate_tree'])
                    descendant = f.git('commit-tree', tree, '-p', after, text='advance\n')
                    f.git('update-ref', 'refs/heads/main', descendant)
                    original = copy.deepcopy(f.evidence)
                    refs = f.git('show-ref')
                    self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=policy)['delivered'])
                    result = m.evaluate(f.evidence, f.repo, local_policy=policy, historical=True)
                    self.assertTrue(result['delivered'])
                    self.assertEqual(result['integration'], 'historically locally integrated')
                    self.assertEqual(result['integration_evaluation'], 'historical')
                    self.assertEqual(result['publication'], 'unknown')
                    self.assertFalse(result['milestone_complete'])
                    self.assertEqual(f.evidence, original)
                    self.assertEqual(f.git('show-ref'), refs)
                    for main in (f.base, f.commit('divergent\n', f.base)):
                        f.git('update-ref', 'refs/heads/main', main)
                        self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=policy,
                                                    historical=True)['delivered'])

    def test_historical_local_delivery_keeps_all_evidence_gates(self):
        with EvidenceFixture() as f:
            policy = f.local_integration()
            descendant = f.commit('later\n', f.commit_id)
            f.git('update-ref', 'refs/heads/main', descendant)
            self.assertTrue(m.evaluate(f.evidence, f.repo, local_policy=policy,
                                       historical=True)['delivered'])
            for field, value in [('authority', 'forged'), ('candidate', {}),
                                 ('reviewers', ['worker'])]:
                self.assertFalse(m.evaluate(f.evidence, f.repo,
                    local_policy=dict(policy, **{field: value}), historical=True)['delivered'])
            bad = copy.deepcopy(f.evidence)
            bad['integration']['provenance']['review']['outcome'] = 'pending'
            self.assertFalse(m.evaluate(bad, f.repo, local_policy=policy, historical=True)['delivered'])
            bad = copy.deepcopy(f.evidence)
            bad['qualification']['checks'] = []
            result = m.evaluate(bad, f.repo, local_policy=policy, historical=True)
            self.assertFalse(result['delivered'])
            self.assertEqual(result['integration'], 'historically locally integrated')
            for field, value in [('action', 'synchronize'), ('before', f.commit_id),
                                 ('target', 'refs/heads/other'), ('after', 'main')]:
                bad = copy.deepcopy(f.evidence)
                bad['integration'][field] = value
                self.assertFalse(m.evaluate(bad, f.repo, local_policy=policy,
                                            historical=True)['delivered'])
            for after in (descendant,
                          f.git('commit-tree', f.identity['candidate_tree'], '-p', f.commit_id,
                                text='not integration\n'),
                          f.git('commit-tree', f.identity['candidate_tree'], '-p', f.commit_id,
                                '-p', f.base, text='reversed parents\n'),
                          f.git('commit-tree', f.identity['candidate_tree'], '-p', f.base,
                                '-p', f.commit_id, '-p', descendant, text='octopus\n'),
                          f.commit('foreign tree\n', f.commit_id)):
                f.git('update-ref', 'refs/heads/main', after)
                bad = copy.deepcopy(f.evidence)
                bad['integration']['after'] = after
                self.assertFalse(m.evaluate(bad, f.repo, local_policy=policy,
                                            historical=True)['delivered'])
            f.git('update-ref', 'refs/heads/main', descendant)
            f.git('update-ref', 'refs/heads/candidate', f.base)
            self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=policy,
                                        historical=True)['delivered'])

    def test_historical_delivery_refuses_moved_prerequisite_refs(self):
        with EvidenceFixture() as f:
            f.git('update-ref', 'refs/heads/prerequisite', f.base)
            f.identity = candidate_identity.capture(f.repo, f.base, 'refs/heads/candidate',
                                                    {'refs/heads/prerequisite': f.base})
            f.receipt = f.execute()
            f.evidence = {'candidate': f.identity, 'implementation': {'artifacts': ['a.py']},
                          'qualification': {'candidate': f.identity, 'required_checks': ['unit'],
                                            'checks': [f.check()]}}
            policy = f.local_integration()
            f.git('update-ref', 'refs/heads/main', f.commit('later\n', f.commit_id))
            self.assertTrue(m.evaluate(f.evidence, f.repo, local_policy=policy,
                                       historical=True)['delivered'])
            f.git('update-ref', 'refs/heads/prerequisite', f.commit_id)
            result = m.evaluate(f.evidence, f.repo, local_policy=policy, historical=True)
            self.assertFalse(result['qualified'])
            self.assertEqual(result['integration'], 'unknown')

    def test_local_integration_requires_separate_exact_policy_and_review(self):
        with EvidenceFixture() as f:
            policy = f.local_integration()
            self.assertFalse(m.evaluate(f.evidence, f.repo)['delivered'])
            result = m.evaluate(f.evidence, f.repo, local_policy=policy)
            self.assertTrue(result['delivered'])
            self.assertEqual(result['integration'], 'locally integrated')
            self.assertIn('local main', result['progress'])
            self.assertNotIn('merged main', result['progress'])
            self.assertEqual(result['publication'], 'unknown')
            self.assertFalse(result['milestone_complete'])
            for field in policy:
                bad = copy.deepcopy(policy)
                del bad[field]
                self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=bad)['delivered'], field)
            for field in f.evidence['integration']['provenance']['review']:
                bad = copy.deepcopy(f.evidence)
                del bad['integration']['provenance']['review'][field]
                self.assertFalse(m.evaluate(bad, f.repo, local_policy=policy)['delivered'], field)

    def test_local_integration_refuses_foreign_stale_and_forged_evidence(self):
        with EvidenceFixture() as f:
            policy = f.local_integration()
            for field, value in [('source', 'protected_pr'), ('authority', 'foreign'),
                                 ('observed', False), ('review', None)]:
                bad = copy.deepcopy(f.evidence)
                bad['integration']['provenance'][field] = value
                self.assertFalse(m.evaluate(bad, f.repo, local_policy=policy)['delivered'], field)
            for field, value in [('candidate', {}), ('reviewer', 'worker'),
                                 ('reviewer', 'foreign'), ('implementer', 'foreign'),
                                 ('outcome', 'pending'), ('observed', False), ('id', '')]:
                bad = copy.deepcopy(f.evidence)
                bad['integration']['provenance']['review'][field] = value
                self.assertFalse(m.evaluate(bad, f.repo, local_policy=policy)['delivered'], field)
            for field, value in [('candidate', {}), ('target', 'refs/heads/other'),
                                 ('before', f.commit_id), ('action', 'synchronize')]:
                bad = copy.deepcopy(f.evidence)
                bad['integration'][field] = value
                self.assertFalse(m.evaluate(bad, f.repo, local_policy=policy)['delivered'], field)
            f.evidence['local_policy'] = policy
            self.assertFalse(m.evaluate(f.evidence, f.repo)['delivered'])
            f.git('update-ref', 'refs/heads/main', f.commit('later\n', f.commit_id))
            self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=policy)['delivered'])
            f.git('update-ref', 'refs/heads/main', f.commit_id)
            f.git('update-ref', 'refs/heads/candidate', f.base)
            self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=policy)['delivered'])

    def test_local_merge_binds_parents_tree_and_does_not_mutate_git(self):
        with EvidenceFixture() as f:
            policy = f.local_integration()
            tree = f.identity['candidate_tree']
            merge = f.git('commit-tree', tree, '-p', f.base, '-p', f.commit_id, text='merge\n')
            f.git('update-ref', 'refs/heads/main', merge)
            f.evidence['integration']['after'] = merge
            refs = f.git('show-ref')
            self.assertTrue(m.evaluate(f.evidence, f.repo, local_policy=policy)['delivered'])
            self.assertEqual(f.git('show-ref'), refs)
            # Descendant ancestry alone is not an observed exact integration.
            for bad in (f.commit('foreign tree\n', f.commit_id),
                        f.git('commit-tree', tree, '-p', f.commit_id, text='extra\n')):
                f.git('update-ref', 'refs/heads/main', bad)
                f.evidence['integration']['after'] = bad
                self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=policy)['delivered'])
            f.git('update-ref', 'refs/heads/main', f.base)
            f.evidence['integration']['after'] = merge
            self.assertFalse(m.evaluate(f.evidence, f.repo, local_policy=policy)['delivered'])

    def test_required_runner_checks_cannot_be_omitted_or_replaced_by_app_pass(self):
        with EvidenceFixture() as f:
            qualification = f.evidence['qualification']
            qualification['required_checks'] = ['unit', 'preservation', 'runner']
            self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'])
            for name in ('preservation', 'runner'):
                check = copy.deepcopy(f.check())
                check['name'] = name
                qualification['checks'].append(check)
            self.assertTrue(m.evaluate(f.evidence, f.repo)['qualified'])
            failed = [sys.executable, '-c', 'raise SystemExit(1)']
            runner = qualification['checks'][-1]
            runner.update(command=failed, receipt=f.execute(failed))
            self.assertFalse(m.evaluate(f.integrated(), f.repo)['delivered'])
            runner.update(command=f.command, receipt=f.receipt)
            for required in (None, [], ['unit', 'unit'], ['unit', 'missing']):
                qualification['required_checks'] = required
                self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'], required)
            qualification['required_checks'] = ['unit', 'preservation', 'runner']
            qualification['checks'][-1]['name'] = 'unit'
            self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'])

    def test_assertions_without_helper_receipt_cannot_qualify(self):
        with EvidenceFixture() as f:
            del f.evidence['qualification']['checks'][0]['receipt']
            self.assertEqual(m.evaluate(f.evidence, f.repo)['state'], 'implemented')

    def test_validated_receipt_is_only_scope_authority(self):
        with EvidenceFixture() as f:
            check = f.evidence['qualification']['checks'][0]
            check.update(platform='invented', backend='provider-x', mode='live', result='passed')
            result = m.evaluate(f.evidence, f.repo)
            self.assertEqual(result['qualification_scope'], ['unit: linux/offline (fixture)'])
            f.evidence['required_mode'] = 'live'
            self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'])

    def test_failed_and_stale_receipts_cannot_qualify(self):
        with EvidenceFixture() as f:
            check = f.evidence['qualification']['checks'][0]
            command = [sys.executable, '-c', 'raise SystemExit(1)']
            check.update(command=command, receipt=f.execute(command))
            self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'])
            check.update(command=f.command, receipt=f.receipt)
            f.git('update-ref', 'refs/heads/candidate', f.base)
            self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'])

    def test_each_check_requires_explicit_inputs_and_exact_passed_receipt(self):
        with EvidenceFixture() as f:
            self.assertTrue(m.evaluate(f.evidence, f.repo)['qualified'])
            for field in ('name', 'command', 'paths', 'external_paths', 'qualification_scope', 'receipt'):
                bad = copy.deepcopy(f.evidence)
                del bad['qualification']['checks'][0][field]
                self.assertFalse(m.evaluate(bad, f.repo)['qualified'], field)
            for field, value in [('version', 1), ('qualification', 'shared_tree_declared_inputs_only'),
                                 ('outcome', 'failed'), ('candidate', {}), ('qualification_scope', None)]:
                bad = copy.deepcopy(f.evidence)
                bad['qualification']['checks'][0]['receipt'][field] = value
                self.assertFalse(m.evaluate(bad, f.repo)['qualified'], field)
            bad = copy.deepcopy(f.evidence)
            bad['qualification']['checks'][0]['qualification_scope'] = None
            self.assertFalse(m.evaluate(bad, f.repo)['qualified'])

    def test_missing_or_wrong_repo_cannot_claim_implementation_or_qualification(self):
        with EvidenceFixture() as f:
            self.assertEqual(m.evaluate(f.evidence)['state'], 'unknown')
            self.assertEqual(m.evaluate(f.evidence, f.repo/'missing')['state'], 'unknown')
            self.assertEqual(m.evaluate({'candidate': f.identity}, f.repo)['state'], 'unknown')
            self.assertEqual(m.evaluate(f.evidence, f.repo)['candidate'], f.identity)

    def test_delivered_slice_never_closes_full_milestone(self):
        with EvidenceFixture() as f:
            result = m.evaluate(f.integrated(), f.repo)
            self.assertEqual(result['state'], 'delivered')
            self.assertFalse(result['milestone_complete'])

    def test_live_scope_and_all_check_inputs_are_bound_to_helper_execution(self):
        with EvidenceFixture() as f:
            scope = dict(f.scope, mode='live', backend='local-process')
            receipt = f.execute(scope=scope)
            check = f.evidence['qualification']['checks'][0]
            check.update(qualification_scope=scope, receipt=receipt)
            f.evidence['required_mode'] = 'live'
            self.assertEqual(m.evaluate(f.evidence, f.repo)['qualification_scope'],
                             ['unit: linux/local-process (live)'])
            for field, value in [('command', [sys.executable, '-c', 'pass']),
                                 ('paths', []), ('external_paths', ['not-declared']),
                                 ('qualification_scope', f.scope)]:
                bad = copy.deepcopy(f.evidence)
                bad['qualification']['checks'][0][field] = value
                self.assertFalse(m.evaluate(bad, f.repo)['qualified'], field)
            f.evidence['qualification']['checks'].append({'name': 'invented', 'mode': 'live', 'result': 'passed'})
            self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'])

    def test_external_dependency_drift_invalidates_delivery_qualification(self):
        with EvidenceFixture() as f:
            external = f.repo/'dependency.txt'
            external.write_text('before\n')
            receipt = check_receipt.execute(f.repo, ['a.py'], f.command, 10, candidate=f.identity,
                                            qualification_scope=f.scope, external_paths=['dependency.txt'])
            f.evidence['qualification']['checks'][0].update(receipt=receipt, external_paths=['dependency.txt'])
            self.assertTrue(m.evaluate(f.evidence, f.repo)['qualified'])
            external.write_text('after\n')
            self.assertFalse(m.evaluate(f.evidence, f.repo)['qualified'])

    def test_integration_uses_supplied_repo_not_inherited_git_routing(self):
        import os
        import subprocess
        from unittest.mock import patch
        with EvidenceFixture() as f, tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            evidence = f.integrated()
            foreign = Path(directory) / 'foreign'
            subprocess.run(['git', 'clone', '--quiet', str(f.repo), str(foreign)], check=True)
            f.git('update-ref', 'refs/heads/main', f.base)
            routing = {'GIT_DIR': str(foreign / '.git'), 'GIT_WORK_TREE': str(foreign)}
            with patch.dict(os.environ, routing):
                self.assertEqual(m.integration_state(f.identity, evidence['integration'], f.repo),
                                 'unknown', 'Foreign main must not prove supplied repo integration')
            subprocess.run(['git', '-C', str(foreign), 'update-ref', 'refs/heads/main', f.base], check=True)
            f.git('update-ref', 'refs/heads/main', f.commit_id)
            with patch.dict(os.environ, routing):
                self.assertEqual(m.integration_state(f.identity, evidence['integration'], f.repo), 'merged')

    def test_integration_gaps_and_noop_synchronization_remain_undelivered(self):
        with EvidenceFixture() as f:
            self.assertEqual(m.evaluate(f.evidence, f.repo)['state'], 'qualified')
            f.integrated()
            for field in ('candidate', 'action', 'before', 'after', 'target', 'provenance'):
                bad = copy.deepcopy(f.evidence)
                del bad['integration'][field]
                self.assertFalse(m.evaluate(bad, f.repo)['delivered'], field)
            for field in ('source', 'id', 'observed', 'protected', 'required_checks', 'head', 'merge_commit'):
                bad = copy.deepcopy(f.evidence)
                del bad['integration']['provenance'][field]
                self.assertFalse(m.evaluate(bad, f.repo)['delivered'], field)
            f.evidence['integration'].update(action='synchronize', before=f.commit_id)
            result = m.evaluate(f.evidence, f.repo)
            self.assertEqual(result['integration'], 'already synchronized')
            self.assertFalse(result['delivered'])
            self.assertNotIn('merged', result['progress'])


if __name__ == '__main__':
    unittest.main()
