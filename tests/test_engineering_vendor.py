"""Pinned engineering distribution and phase routing, without model/network calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'skills/engineering'

class EngineeringVendorTests(unittest.TestCase):
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
