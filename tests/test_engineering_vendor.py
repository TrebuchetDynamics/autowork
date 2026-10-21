"""Pinned engineering distribution and phase routing, without model/network calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'skills/engineering'

class EngineeringVendorTests(unittest.TestCase):
    def test_the_engine_ships_with_pi_autowork_not_the_installed_skill(self):
        """The autowork skill carries no code: profiles get its instructions and Docs Sync's
        helpers, and the engine runs from the toolset's pi-autowork/engine."""
        spec = importlib.util.spec_from_file_location('ready_install_fixture', ROOT / 'install_skills.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            selected = [ROOT / 'skills' / name for name in ('autowork', 'docs-sync', 'engineering')]
            self.assertEqual(module.install(ROOT / 'skills', [('fixture', home)], skills=selected, report=lambda _: None), 0)
            self.assertTrue((home / 'skills/autowork/SKILL.md').is_file())
            self.assertFalse((home / 'skills/autowork/scripts').exists())
            self.assertEqual((home / 'skills/docs-sync/scripts/goals.py').read_bytes(),
                             (ROOT / 'skills/docs-sync/scripts/goals.py').read_bytes())
            result = subprocess.run(['python3', str(ROOT / 'pi-autowork/engine/owner_cycle.py'), '--help'],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--source-path', result.stdout)
            self.assertIn('--profile', result.stdout)

    def test_exact_protocol_selection_has_no_implicit_phase_bundle(self):
        result = subprocess.run(['python3', str(PACK/'scripts/route.py'),
                                 '--protocol', 'performance-optimization'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        selection = json.loads(result.stdout)
        self.assertIsNone(selection['phase'])
        self.assertEqual([row['name'] for row in selection['skills']],
                         ['performance-optimization'])
        self.assertEqual(Path(selection['skills'][0]['path']),
                         PACK/'upstream/skills/performance-optimization/PROTOCOL.md')

    def test_toolset_protocol_routes_without_a_pin_and_cannot_shadow_one(self):
        result = subprocess.run(['python3', str(PACK/'scripts/route.py'),
                                 '--protocol', 'test-suite-optimization'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads(result.stdout)['skills'][0]
        self.assertEqual(row['source'], 'toolset')
        self.assertEqual(Path(row['path']), PACK/'local/test-suite-optimization/PROTOCOL.md')
        self.assertNotIn('sha256', row)
        protocol = Path(row['path']).read_text()
        for part in ('## Measure first', '## Find candidates', '## Keep', '## Record tasks, do not edit',
                     '## Acceptance for each change', '## Never'):
            self.assertIn(part, protocol)
        spec = importlib.util.spec_from_file_location('route_shadow', PACK/'scripts/route.py')
        router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(router)
        router.LOCAL = dict(router.LOCAL, **{'performance-optimization': 'local/x/PROTOCOL.md'})
        with self.assertRaisesRegex(ValueError, 'shadows a pinned protocol'):
            router.route(protocol='performance-optimization')
        with self.assertRaisesRegex(ValueError, 'phase bundles use pinned protocols only'):
            router.route('implement', ['test-suite-optimization'])

    def test_exact_selection_rejects_unknown_or_mixed_requests(self):
        for args in ([], ['--domain', 'performance-optimization'],
                     ['--protocol', '../../bad'],
                     ['implement', '--protocol', 'performance-optimization'],
                     ['--protocol', 'performance-optimization', '--domain', 'context-engineering']):
            with self.subTest(args=args):
                result = subprocess.run(['python3', str(PACK/'scripts/route.py'), *args],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')

    def test_exact_and_phase_routes_reject_tampered_protocols_and_references(self):
        for relative in ('upstream/skills/test-driven-development/PROTOCOL.md',
                         'upstream/references/definition-of-done.md'):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as td:
                pack = Path(td)/'engineering'
                shutil.copytree(PACK, pack)
                with (pack/relative).open('a') as changed:
                    changed.write('\nTampered fixture\n')
                for args in (['implement'], ['--protocol', 'test-driven-development']):
                    result = subprocess.run(['python3', str(pack/'scripts/route.py'), *args],
                                            capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('changed:', result.stderr)
                    self.assertEqual(result.stdout, '')

    def test_integrity_and_no_nested_skill_discovery(self):
        manifest=json.loads((PACK/'UPSTREAM.json').read_text())
        self.assertEqual(len(manifest['skills']),25)
        self.assertRegex(manifest['revision'],r'^[0-9a-f]{40}$')
        for original,item in manifest['files'].items():
            p=PACK/item['path']
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),item['sha256'],original)
        self.assertEqual(list((PACK/'upstream').rglob('SKILL.md')),[])
        self.assertIn('MIT License',(PACK/'upstream/LICENSE').read_text())
        for ref in ['definition-of-done.md','security-checklist.md','performance-checklist.md']:
            self.assertTrue((PACK/'upstream/references'/ref).is_file())

    def test_phases_select_pinned_protocols_and_reject_unknown_names(self):
        script=PACK/'scripts/route.py'
        for phase in ['plan','implement','debug','review','document','deliver']:
            r=subprocess.run(['python3',str(script),phase],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            result=json.loads(r.stdout)
            self.assertTrue(result['skills'])
            for skill in result['skills']:self.assertTrue(Path(skill['path']).is_file())
            self.assertIn('not proof',result['boundary'])
        r=subprocess.run(['python3',str(script),'plan','--domain','../../bad'],capture_output=True)
        self.assertNotEqual(r.returncode,0)

    def test_native_install_preserves_support_tree(self):
        spec=importlib.util.spec_from_file_location('install_fixture',ROOT/'install_skills.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)
            self.assertEqual(module.install(ROOT/'skills',[('fixture',home)],skills=[PACK],report=lambda _:None),0)
            self.assertTrue((home/'skills/engineering/upstream/references/security-checklist.md').is_file())
            self.assertEqual((home/'skills/engineering/UPSTREAM.json').read_bytes(),(PACK/'UPSTREAM.json').read_bytes())

if __name__=='__main__':unittest.main()
