"""The vendored UI Taste skill is an exact, licensed snapshot of a pinned Uizze commit."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'skills/ui-taste'
REVISION = 'afd703a14a5db5f2fe6c2860badbe811058aa9e5'


class UiTasteBundleTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((PACK / 'UPSTREAM.json').read_text())

    def test_snapshot_is_pinned_and_byte_exact(self):
        self.assertEqual(self.manifest['repository'], 'https://github.com/uizze/uizze')
        self.assertEqual(self.manifest['revision'], REVISION)
        self.assertEqual(self.manifest['path'], 'skills/ui-taste')
        self.assertEqual(self.manifest['license'], 'Apache-2.0')
        vendored = {p.relative_to(PACK).as_posix() for p in PACK.rglob('*') if p.is_file()}
        self.assertEqual(vendored, set(self.manifest['sha256']) | {'UPSTREAM.json'})
        self.assertEqual(len(self.manifest['sha256']), 16)
        for name, digest in self.manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((PACK / name).read_bytes()).hexdigest(), digest, name)

    def test_upstream_checksums_license_and_plain_files(self):
        for line in (PACK / 'CHECKSUMS.sha256').read_text().splitlines():
            digest, name = line.split(maxsplit=1)
            self.assertEqual(hashlib.sha256((PACK / name).read_bytes()).hexdigest(), digest, name)
        self.assertIn('Apache License', (PACK / 'LICENSE').read_text())
        notice = (PACK / 'NOTICE').read_text()
        self.assertIn('Impeccable', notice)
        self.assertIn('platform-design-skills', notice)
        for path in PACK.rglob('*'):
            if path.is_file():
                self.assertFalse(path.stat().st_mode & 0o111, f'{path} must not be executable')
        self.assertIn('\nname: ui-taste\n', (PACK / 'SKILL.md').read_text())

    def test_clean_profile_receives_ui_taste_offline(self):
        spec = importlib.util.spec_from_file_location('ui_taste_installer', ROOT / 'install_skills.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / 'default'
            self.assertEqual(module.install(ROOT / 'skills', [('default', home)], report=lambda _: None), 0)
            for name in ('SKILL.md', 'reference/craft.md', 'NOTICE', 'LICENSE'):
                self.assertTrue((home / 'skills/ui-taste' / name).is_file(), name)


if __name__ == '__main__':
    unittest.main()
