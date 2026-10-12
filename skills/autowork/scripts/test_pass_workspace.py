"""Real local Git fixtures; no provider, remote or native dispatch proof."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

class PassWorkspaceTests(unittest.TestCase):
    def setUp(self):
        (Path.home() / '.hermes/cache/scratch').mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'source'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@local')
        (self.root / 'owned.py').write_text('base\n')
        self.git('add', 'owned.py'); self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def module(self):
        path = Path(__file__).with_name('pass_workspace.py')
        self.assertTrue(path.exists(), 'Executable isolated pass helper required')
        spec = importlib.util.spec_from_file_location('pass_workspace', path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def planning_fixture(self):
        import hashlib, json
        data={'goals':[{'id':'G1','source':'docs/plan.md#slice'}],
              'tasks':[{'id':'T1','goal':'G1'}]}
        (self.root/'goals.json').write_text(json.dumps(data))
        (self.root/'TODO.md').write_text('T1: accepted fixture work\n')
        (self.root/'docs').mkdir()
        (self.root/'docs/plan.md').write_text('# Slice\nStatus: Accepted\n')
        names=['owned.py','goals.json','TODO.md','docs/plan.md']
        snapshot={'files':[{'path':n,'sha256':hashlib.sha256((self.root/n).read_bytes()).hexdigest()} for n in names]}
        admission={'goal_task':'T1','goal':'G1','ledger_sha256':snapshot['files'][1]['sha256']}
        return snapshot,admission

    def test_proposal_worker_uses_frozen_planning_context_without_committing_owner_dirt(self):
        module=self.module();snapshot,admission=self.planning_fixture()
        before=self.git('status','--porcelain')
        context=module.capture_planning_context(self.root,snapshot,admission,'parent')
        target=Path(self.tmp.name)/'context-worker'
        identity=module.prepare(self.root,target,self.base,self.base)
        manifest={'source_workspace':str(self.root),'candidate_identity':identity,
                  'files':snapshot['files'],'ledger_sha256':admission['ledger_sha256'],
                  'ledger_mode':'proposal','planning_context':context}
        self.assertTrue(module.verify(manifest,target))
        self.assertFalse((target/'goals.json').exists())
        self.assertEqual(self.git('status','--porcelain'),before)
        self.assertEqual(self.git('rev-parse','HEAD'),self.base)
        (self.root/'TODO.md').write_text('Task withdrawn')
        with self.assertRaisesRegex(ValueError,'Source changed'):
            module.verify(manifest,target)

    def admitted_transition_fixture(self):
        import hashlib, json
        module = self.module()
        snapshot, admission = self.planning_fixture()
        ledger = json.loads((self.root / 'goals.json').read_text())
        ledger['version'] = 1
        ledger['goals'][0].update(title='Fixture goal', status='unmet', tasks=['T1', 'T2'])
        ledger['tasks'][0].update(title='Selected task', status='open', section='Next')
        ledger['tasks'].append({'id': 'T2', 'goal': 'G1', 'title': 'Other task',
                                'status': 'open', 'section': 'Next'})
        (self.root / 'goals.json').write_text(json.dumps(ledger))
        goals = Path(__file__).resolve().parents[2] / 'repo-docs/scripts/goals.py'
        subprocess.run(['python3', str(goals), 'fmt', str(self.root)], check=True, capture_output=True)
        snapshot['files'][1]['sha256'] = hashlib.sha256((self.root / 'goals.json').read_bytes()).hexdigest()
        admission['ledger_sha256'] = snapshot['files'][1]['sha256']
        context = module.capture_planning_context(self.root, snapshot, admission, 'parent')
        target = Path(self.tmp.name) / 'transition-worker'
        identity = module.prepare(self.root, target, self.base, self.base)
        manifest = {'version': 1, 'source_workspace': str(self.root), 'candidate_identity': identity,
                    'files': snapshot['files'], 'ledger_sha256': admission['ledger_sha256'],
                    'ledger_mode': 'proposal', 'planning_context': context}
        subprocess.run(['python3', str(goals), 'task', str(self.root), 'T1', 'in_progress'],
                       check=True, capture_output=True)
        return module, manifest, target

    def worker_transition_fixture(self):
        import json
        module, proposal, _ = self.admitted_transition_fixture()
        source_ledger = self.root / 'goals.json'
        changed = source_ledger.read_bytes()
        source_ledger.write_text(proposal['planning_context']['files']['goals.json'])
        self.git('add', '.'); self.git('commit', '-qm', 'admitted worker inputs')
        base = self.git('rev-parse', 'HEAD')
        target = Path(self.tmp.name) / 'ledger-worker'
        identity = module.prepare(self.root, target, base, base)
        manifest = {'version':1, 'source_workspace':str(self.root),
            'candidate_identity':identity, 'files':proposal['files'],
            'ledger_sha256':proposal['ledger_sha256'], 'goal_task':'T1'}
        source_ledger.write_bytes(changed)
        return module, manifest, target

    def test_worker_ledger_allows_only_bound_task_start_bookkeeping(self):
        import json
        module, manifest, target = self.worker_transition_fixture()
        self.assertTrue(module.verify(manifest, target))
        manifest['goal_task'] = 'T2'
        with self.assertRaises(ValueError): module.verify(manifest, target)
        manifest.pop('goal_task')
        with self.assertRaises(ValueError): module.verify(manifest, target)
        manifest['goal_task'] = 'T1'
        self.assertEqual(module.run_checked(manifest, target, ['python3', '-c',
                         "open('owned.py','w').write('authorized initial write')"]), 0)
        with self.assertRaisesRegex(ValueError, 'workspace changed'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('wrong')"])
        self.assertEqual((target / 'owned.py').read_text(), 'authorized initial write')

    def test_worker_rejects_foreign_candidate_blob_despite_clean_matching_worktree(self):
        import json
        module, manifest, target = self.worker_transition_fixture()
        original = (target / 'goals.json').read_bytes()
        foreign = json.loads(original)
        foreign['tasks'][0]['section'] = 'Needs decision'
        (self.root / 'goals.json').write_text(json.dumps(foreign))
        self.git('add', 'goals.json'); self.git('commit', '-qm', 'foreign candidate ledger')
        commit = self.git('rev-parse', 'HEAD')
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', commit],
                       check=True, capture_output=True)
        manifest['candidate_identity'] = module.candidate_identity.capture(target, manifest['candidate_identity']['base_commit'], commit)
        (target / 'goals.json').write_bytes(original)
        subprocess.run(['git', '-C', str(target), 'update-index', '--assume-unchanged', 'goals.json'], check=True)
        changed = json.loads(original)
        changed['tasks'][0]['status'] = 'in_progress'
        (self.root / 'goals.json').write_text(json.dumps(changed, indent=2, sort_keys=True) + '\n')
        self.assertEqual(module.candidate_identity.git(target, 'status', '--porcelain'), '')
        with self.assertRaisesRegex(ValueError, 'Pinned ledger differs'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('wrong')"])
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_worker_status_tolerance_requires_canonical_ledger_semantics(self):
        import hashlib, json
        module, manifest, target = self.worker_transition_fixture()
        ledger = json.loads((target / 'goals.json').read_bytes())
        ledger['tasks'][1].pop('depends_on')
        original = (json.dumps(ledger, indent=2, sort_keys=True) + '\n').encode()
        (self.root / 'goals.json').write_bytes(original)
        self.git('add', 'goals.json'); self.git('commit', '-qm', 'noncanonical ledger')
        commit = self.git('rev-parse', 'HEAD')
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', commit], check=True, capture_output=True)
        manifest['candidate_identity'] = module.candidate_identity.capture(target, manifest['candidate_identity']['base_commit'], commit)
        manifest['ledger_sha256'] = hashlib.sha256(original).hexdigest()
        next(r for r in manifest['files'] if r['path'] == 'goals.json')['sha256'] = manifest['ledger_sha256']
        ledger['tasks'][0]['status'] = 'in_progress'
        (self.root / 'goals.json').write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('wrong')"])
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_worker_rejects_missing_candidate_ledger_before_write(self):
        module, manifest, target = self.worker_transition_fixture()
        self.git('rm', '-f', 'goals.json'); self.git('commit', '-qm', 'candidate without ledger')
        commit = self.git('rev-parse', 'HEAD')
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', commit], check=True, capture_output=True)
        manifest['candidate_identity'] = module.candidate_identity.capture(target, manifest['candidate_identity']['base_commit'], commit)
        with self.assertRaisesRegex(ValueError, 'Pinned candidate ledger missing'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('wrong')"])
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_worker_rejects_held_candidate_promotion_or_stale_admission_pin(self):
        import hashlib, json
        module, manifest, target = self.worker_transition_fixture()
        manifest['ledger_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Pinned ledger differs'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('wrong')"])
        ledger = json.loads((target / 'goals.json').read_bytes())
        ledger['tasks'][0]['section'] = 'Needs decision'
        original = (json.dumps(ledger, indent=2, sort_keys=True) + '\n').encode()
        (self.root / 'goals.json').write_bytes(original)
        self.git('add', 'goals.json'); self.git('commit', '-qm', 'held task')
        commit = self.git('rev-parse', 'HEAD')
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', commit], check=True, capture_output=True)
        manifest['candidate_identity'] = module.candidate_identity.capture(target, manifest['candidate_identity']['base_commit'], commit)
        manifest['ledger_sha256'] = hashlib.sha256(original).hexdigest()
        next(r for r in manifest['files'] if r['path'] == 'goals.json')['sha256'] = manifest['ledger_sha256']
        ledger['tasks'][0].update(section='Next', status='in_progress')
        (self.root / 'goals.json').write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('wrong')"])
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_legacy_worker_uses_exact_existing_handoff_without_repinning(self):
        import json, hashlib
        module, manifest, target = self.worker_transition_fixture()
        manifest.pop('goal_task')
        path = Path(self.tmp.name) / 'pass.json'
        path.write_text(json.dumps(manifest)); pinned = path.read_bytes()
        digest = hashlib.sha256(pinned).hexdigest()
        receipt = {'pass_manifest_path':str(path), 'pass_manifest_sha256':digest,
            'workspace':str(target), 'source_workspace':str(self.root),
            'pass_manifest':manifest, 'goal_task':'T1', 'task_id':'original-card'}
        handoff = path.parent / 'goal-handoff.json'
        handoff.write_text(json.dumps(receipt))
        args = ['python3',str(Path(__file__).with_name('pass_workspace.py')),
            '--manifest',str(path),'--manifest-sha256',digest,'--workspace',str(target)]
        result = subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_bytes(), pinned)
        receipt['goal_task'] = 'T2';handoff.write_text(json.dumps(receipt))
        self.assertNotEqual(subprocess.run(args,capture_output=True).returncode, 0)
        receipt['goal_task'] = 'T1';receipt['pass_manifest_sha256'] = '0'*64
        handoff.write_text(json.dumps(receipt))
        self.assertNotEqual(subprocess.run(args,capture_output=True).returncode, 0)

    def test_same_admitted_task_transition_preserves_pinned_context_and_first_guard(self):
        import hashlib, json
        module, manifest, target = self.admitted_transition_fixture()
        receipt = Path(self.tmp.name) / 'manifest.json'
        receipt.write_text(json.dumps(manifest))
        pinned = receipt.read_bytes()
        digest = hashlib.sha256(pinned).hexdigest()
        result = subprocess.run(['python3', str(Path(__file__).with_name('pass_workspace.py')),
                                 '--manifest', str(receipt), '--manifest-sha256', digest,
                                 '--workspace', str(target), '--', 'python3', '-c',
                                 "open('owned.py','w').write('authorized initial write')"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'owned.py').read_text(), 'authorized initial write')
        self.assertEqual(receipt.read_bytes(), pinned)
        self.assertEqual(json.loads(manifest['planning_context']['files']['goals.json'])['tasks'][0]['status'], 'open')
        self.assertFalse((target / 'goals.json').exists())
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)

    def test_admitted_transition_rejects_every_other_source_delta_before_write(self):
        self.assert_transition_rejects_other_source_deltas(*self.admitted_transition_fixture())

    def test_worker_transition_rejects_every_other_source_delta_before_write(self):
        self.assert_transition_rejects_other_source_deltas(*self.worker_transition_fixture())

    def assert_transition_rejects_other_source_deltas(self, module, manifest, target):
        import copy, json
        original = (self.root / 'goals.json').read_bytes()
        current = json.loads(original)
        mutations = [
            ('task title', lambda d: d['tasks'][0].update(title='Changed scope')),
            ('task goal', lambda d: d['tasks'][0].update(goal='Other goal')),
            ('task dependencies', lambda d: d['tasks'][0].update(depends_on=['T2'])),
            ('task scope', lambda d: d['tasks'][0].update(scope='Changed scope')),
            ('task acceptance', lambda d: d['tasks'][0].update(acceptance=['Changed check'])),
            ('task ownership', lambda d: d['tasks'][0].update(owner='foreign')),
            ('needs decision', lambda d: d['tasks'][0].update(section='Needs decision')),
            ('done status', lambda d: d['tasks'][0].update(status='done')),
            ('other task status', lambda d: d['tasks'][1].update(status='in_progress')),
            ('other task title', lambda d: d['tasks'][1].update(title='Changed task')),
            ('goal status', lambda d: d['goals'][0].update(status='partial')),
            ('goal acceptance', lambda d: d['goals'][0].update(acceptance=['Changed check'])),
            ('goal plan', lambda d: d['goals'][0].update(source='docs/other.md')),
            ('goal dependencies', lambda d: d['goals'][0].update(depends_on=['Other'])),
            ('focus', lambda d: d.update(primary_milestone='Other')),
            ('duplicate task', lambda d: d['tasks'].append(copy.deepcopy(d['tasks'][0]))),
        ]
        command = ['python3', '-c', "open('owned.py','w').write('wrong')"]
        for name, mutate in mutations:
            with self.subTest(delta=name):
                changed = copy.deepcopy(current)
                mutate(changed)
                (self.root / 'goals.json').write_text(json.dumps(changed, indent=2, sort_keys=True) + '\n')
                with self.assertRaisesRegex(ValueError, 'Source changed'):
                    module.run_checked(manifest, target, command)
                self.assertEqual((target / 'owned.py').read_text(), 'base\n')
        (self.root / 'goals.json').write_bytes(original + b'\n')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            module.run_checked(manifest, target, command)
        (self.root / 'goals.json').write_bytes(original)
        for name in ('owned.py', 'TODO.md', 'docs/plan.md'):
            with self.subTest(file=name):
                path = self.root / name
                before = path.read_bytes()
                path.write_bytes(before + b'changed\n')
                with self.assertRaisesRegex(ValueError, 'Source changed'):
                    module.run_checked(manifest, target, command)
                path.write_bytes(before)
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_status_tolerance_cannot_promote_held_or_previously_claimed_context(self):
        import json, hashlib
        module, manifest, target = self.admitted_transition_fixture()
        original = manifest['planning_context']['files']['goals.json']
        current = (self.root / 'goals.json').read_bytes()
        for field, value in [('section', 'Needs decision'), ('status', 'in_progress'),
                             ('status', 'done')]:
            with self.subTest(original_field=field, original_value=value):
                (self.root / 'goals.json').write_bytes(current)
                ledger = json.loads(original)
                ledger['tasks'][0][field] = value
                frozen = json.dumps(ledger, indent=2, sort_keys=True) + '\n'
                digest = hashlib.sha256(frozen.encode()).hexdigest()
                manifest['planning_context']['files']['goals.json'] = frozen
                manifest['ledger_sha256'] = digest
                next(r for r in manifest['files'] if r['path'] == 'goals.json')['sha256'] = digest
                if field == 'status' and value == 'in_progress':
                    ledger['tasks'][0]['status'] = 'open'
                    (self.root / 'goals.json').write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
                with self.assertRaisesRegex(ValueError, 'Source changed'):
                    module.run_checked(manifest, target, ['python3', '-c',
                                       "open('owned.py','w').write('wrong')"])
                self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_admitted_transition_requires_original_bound_proposal_manifest(self):
        import copy, json, hashlib
        module, manifest, target = self.admitted_transition_fixture()
        command = ['python3', '-c', "open('owned.py','w').write('wrong')"]
        for name, mutate in [
                ('missing context', lambda m: m.pop('planning_context')),
                ('unbound task', lambda m: m['planning_context'].update(goal_task='absent')),
                ('foreign task', lambda m: m['planning_context'].update(goal_task='T2')),
                ('missing owner', lambda m: m['planning_context'].update(integration_owner='')),
                ('ledger writer', lambda m: m.update(ledger_mode='worker')),
                ('stale ledger pin', lambda m: m.update(ledger_sha256='0' * 64)),
                ('forged context', lambda m: m['planning_context']['files'].update(
                    {'goals.json': (self.root / 'goals.json').read_text()})),
                ('foreign workspace', lambda m: m['candidate_identity'].update(workspace=str(self.root)))]:
            with self.subTest(manifest=name):
                changed = copy.deepcopy(manifest)
                mutate(changed)
                with self.assertRaises(ValueError):
                    module.run_checked(changed, target, command)
        receipt = Path(self.tmp.name) / 'manifest.json'
        receipt.write_text(json.dumps(manifest))
        digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
        changed = copy.deepcopy(manifest)
        changed['planning_context']['integration_owner'] = 'foreign'
        receipt.write_text(json.dumps(changed))
        result = subprocess.run(['python3', str(Path(__file__).with_name('pass_workspace.py')),
                                 '--manifest', str(receipt), '--manifest-sha256', digest,
                                 '--workspace', str(target), '--', *command],
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('manifest changed', result.stderr)
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_planning_context_cannot_hide_code_drift_or_grant_ledger_write_role(self):
        module=self.module();snapshot,admission=self.planning_fixture()
        context=module.capture_planning_context(self.root,snapshot,admission,'parent')
        target=Path(self.tmp.name)/'context-worker'
        identity=module.prepare(self.root,target,self.base,self.base)
        manifest={'source_workspace':str(self.root),'candidate_identity':identity,
                  'files':snapshot['files'],'ledger_sha256':admission['ledger_sha256'],
                  'ledger_mode':'worker','planning_context':context}
        with self.assertRaises(ValueError):module.verify(manifest,target)
        manifest['ledger_mode']='proposal'
        context['files']['owned.py']='base\n'
        with self.assertRaises(ValueError):module.verify(manifest,target)
        del context['files']['owned.py']
        (self.root/'owned.py').write_text('uncommitted code\n')
        with self.assertRaisesRegex(ValueError,'Source changed'):module.verify(manifest,target)
        context['files']['TODO.md']='forged task'
        with self.assertRaises(ValueError):module.verify(manifest,target)

    def test_required_sibling_must_be_explicitly_assembled(self):
        self.git('checkout', '-qb', 'sibling')
        (self.root / 'dependency.py').write_text('needed\n')
        self.git('add', 'dependency.py'); self.git('commit', '-qm', 'sibling')
        pin = self.git('rev-parse', 'HEAD')
        self.git('checkout', '--detach', self.base)
        (self.root / 'candidate.py').write_text('selected candidate\n')
        self.git('add', 'candidate.py'); self.git('commit', '-qm', 'candidate')
        candidate = self.git('rev-parse', 'HEAD')
        module = self.module()
        with self.assertRaisesRegex(ValueError, 'required path'):
            module.prepare(self.root, Path(self.tmp.name) / 'missing', self.base, self.base,
                           required_paths=['dependency.py'])
        identity = module.prepare(self.root, Path(self.tmp.name) / 'assembled', self.base,
                                  candidate, {'sibling': pin}, ['dependency.py', 'candidate.py'])
        self.assertEqual((Path(identity['workspace']) / 'dependency.py').read_text(), 'needed\n')
        self.assertEqual((Path(identity['workspace']) / 'candidate.py').read_text(), 'selected candidate\n')
        self.assertTrue(module.candidate_identity.check(identity, identity['workspace']))
        self.git('update-ref', 'refs/heads/sibling', self.base)
        self.assertFalse(module.candidate_identity.check(identity, identity['workspace']))

    def test_worker_start_refuses_retracted_source_before_command_writes(self):
        import hashlib
        module = self.module()
        target = Path(self.tmp.name) / 'pass'
        identity = module.prepare(self.root, target, self.base, self.base)
        manifest = {'source_workspace': str(self.root), 'candidate_identity': identity,
                    'files': [{'path': 'owned.py', 'sha256': hashlib.sha256(b'base\n').hexdigest()}],
                    'ledger_sha256': None}
        (self.root / 'owned.py').write_text('finding retracted\n')
        self.assertTrue(callable(getattr(module, 'run_checked', None)), 'Worker start requires executable guard')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('production edit')"])
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_worker_start_refuses_clean_checkout_at_different_commit(self):
        import hashlib
        module = self.module()
        target = Path(self.tmp.name) / 'pass'
        identity = module.prepare(self.root, target, self.base, self.base)
        manifest = {'source_workspace': str(self.root), 'candidate_identity': identity,
                    'files': [{'path': 'owned.py', 'sha256': hashlib.sha256(b'base\n').hexdigest()}],
                    'ledger_sha256': None}
        self.git('commit', '--allow-empty', '-qm', 'different candidate')
        other = self.git('rev-parse', 'HEAD')
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', other], check=True)
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            module.verify(manifest, target)

    def test_worker_guard_allows_fresh_initial_write_but_refuses_workspace_drift(self):
        import hashlib
        module = self.module()
        target = Path(self.tmp.name) / 'pass'
        identity = module.prepare(self.root, target, self.base, self.base)
        manifest = {'source_workspace': str(self.root), 'candidate_identity': identity,
                    'files': [{'path': 'owned.py', 'sha256': hashlib.sha256(b'base\n').hexdigest()},
                              {'path': 'new.py', 'sha256': None}], 'ledger_sha256': None}
        self.assertEqual(module.run_checked(manifest, target, ['python3', '-c',
                         "open('owned.py','w').write('authorized initial write')"]), 0)
        with self.assertRaisesRegex(ValueError, 'workspace changed'):
            module.verify(manifest, target)
        self.assertEqual((self.root / 'owned.py').read_text(), 'base\n')

    def test_ledger_appearance_after_create_refuses_worker_start(self):
        import hashlib
        module = self.module()
        target = Path(self.tmp.name) / 'pass'
        identity = module.prepare(self.root, target, self.base, self.base)
        manifest = {'source_workspace': str(self.root), 'candidate_identity': identity,
                    'files': [{'path': 'owned.py', 'sha256': hashlib.sha256(b'base\n').hexdigest()}],
                    'ledger_sha256': None}
        (self.root / 'goals.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'ledger changed'):
            module.run_checked(manifest, target, ['python3', '-c', "open('owned.py','w').write('wrong')"])
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_cli_worker_guard_refuses_manifest_replacement_before_initial_write(self):
        import hashlib
        import json
        import sys
        module = self.module()
        target = Path(self.tmp.name) / 'pass'
        identity = module.prepare(self.root, target, self.base, self.base)
        manifest = {'source_workspace': str(self.root), 'candidate_identity': identity,
                    'files': [{'path': 'owned.py', 'sha256': hashlib.sha256(b'base\n').hexdigest()}],
                    'ledger_sha256': None}
        receipt = Path(self.tmp.name) / 'manifest.json'
        receipt.write_text(json.dumps(manifest))
        digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
        receipt.write_text(receipt.read_text() + '\n')
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('pass_workspace.py')),
                                 '--manifest', str(receipt), '--manifest-sha256', digest,
                                 '--workspace', str(target), '--', sys.executable, '-c',
                                 "open('owned.py','w').write('wrong')"], capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('manifest changed', result.stderr)
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')

    def test_dirty_shared_source_never_becomes_write_workspace(self):
        (self.root / 'owned.py').write_text('foreign dirty\n')
        (self.root / 'foreign.py').write_text('untracked foreign\n')
        index = (self.root / '.git/index').read_bytes()
        target = Path(self.tmp.name) / 'pass'
        identity = self.module().prepare(self.root, target, self.base, self.base)
        self.assertEqual(identity['workspace'], str(target))
        self.assertEqual((target / 'owned.py').read_text(), 'base\n')
        self.assertFalse((target / 'foreign.py').exists())
        (target / 'owned.py').write_text('worker change\n')
        self.assertEqual((self.root / 'owned.py').read_text(), 'foreign dirty\n')
        self.assertEqual((self.root / '.git/index').read_bytes(), index)
