"""Every bundled skill is available offline, including Impeccable's support tree."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CompleteBundleTests(unittest.TestCase):
    def test_impeccable_snapshot_has_license_and_exact_hashes(self):
        pack = ROOT / 'skills/impeccable'
        manifest = json.loads((pack / 'UPSTREAM.json').read_text())
        self.assertEqual(manifest['revision'], '245ad82def45831dc56a21b683c7a1ff530b06cc')
        self.assertIn('Apache License', (pack / 'LICENSE').read_text())
        self.assertTrue((pack / 'NOTICE.md').is_file())
        notices = json.loads((pack / 'THIRD-PARTY.json').read_text())
        self.assertEqual(set(notices), {'modern-screenshot', 'platform-design-skills'})
        for notice in notices.values():
            self.assertEqual(hashlib.sha256((pack / notice['license_file']).read_bytes()).hexdigest(), notice['license_sha256'])
        third = notices['modern-screenshot']
        license_bytes = (pack / third['license_file']).read_bytes()
        self.assertEqual(hashlib.sha256(license_bytes).hexdigest(), third['license_sha256'])
        self.assertIn(b'2021-present wxm', license_bytes)
        for name, digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((pack / name).read_bytes()).hexdigest(), digest, name)
        self.assertIn('scripts/impeccable', manifest['sha256'])
        self.assertIn('reference/routing.md', manifest['sha256'])

    def test_clean_profiles_receive_every_skill_and_support_file_offline(self):
        spec = importlib.util.spec_from_file_location('complete_bundle_installer', ROOT / 'install_skills.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            homes = [('default', Path(td)/'default'), ('work', Path(td)/'work')]
            self.assertEqual(module.install(ROOT/'skills', homes, report=lambda _: None), 0)
            for _, home in homes:
                self.assertTrue((home/'skills/impeccable/SKILL.md').is_file())
                for folder in (ROOT/'skills').iterdir():
                    if folder.name in {'repo-docs', 'repo-interview'}:
                        self.assertFalse((home/'skills'/folder.name).exists())
                        continue
                    if not (folder/'SKILL.md').is_file() and folder.name != 'shared':
                        continue
                    for source in folder.rglob('*'):
                        if source.is_file() and '__pycache__' not in source.parts and source.suffix not in ('.pyc', '.pyo'):
                            target = home/'skills'/source.relative_to(ROOT/'skills')
                            self.assertEqual(target.read_bytes(), source.read_bytes(), str(target))
                            self.assertEqual(target.stat().st_mode & 0o111, source.stat().st_mode & 0o111)

if __name__ == '__main__':
    unittest.main()
