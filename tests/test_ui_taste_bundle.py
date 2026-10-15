"""The vendored UI Taste skill is an exact, licensed snapshot of a pinned Uizze commit behind a toolset adapter."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'skills/ui-taste'
UPSTREAM = PACK / 'upstream'
REVISION = 'afd703a14a5db5f2fe6c2860badbe811058aa9e5'
# The upstream SKILL.md is stored as PROTOCOL.md so Hermes registers only the adapter.
RENAMED = {'SKILL.md': 'PROTOCOL.md'}


class UiTasteBundleTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((PACK / 'UPSTREAM.json').read_text())

    def test_snapshot_is_pinned_and_byte_exact(self):
        self.assertEqual(self.manifest['repository'], 'https://github.com/uizze/uizze')
        self.assertEqual(self.manifest['revision'], REVISION)
        self.assertEqual(self.manifest['source_path'], 'skills/ui-taste')
        self.assertEqual(self.manifest['license'], 'Apache-2.0')
        self.assertIn('PROTOCOL.md', self.manifest['transform'])
        vendored = {p.relative_to(UPSTREAM).as_posix() for p in UPSTREAM.rglob('*') if p.is_file()}
        self.assertEqual(vendored, set(self.manifest['files']))
        self.assertEqual(len(self.manifest['files']), 16)
        top = {p.relative_to(PACK).as_posix() for p in PACK.iterdir()}
        self.assertEqual(top, {'SKILL.md', 'UPSTREAM.json', 'upstream'})
        for name, digest in self.manifest['files'].items():
            self.assertEqual(hashlib.sha256((UPSTREAM / name).read_bytes()).hexdigest(), digest, name)

    def test_upstream_checksums_license_and_plain_files(self):
        for line in (UPSTREAM / 'CHECKSUMS.sha256').read_text().splitlines():
            digest, name = line.split(maxsplit=1)
            name = RENAMED.get(name, name)
            self.assertEqual(hashlib.sha256((UPSTREAM / name).read_bytes()).hexdigest(), digest, name)
        self.assertIn('Apache License', (UPSTREAM / 'LICENSE').read_text())
        notice = (UPSTREAM / 'NOTICE').read_text()
        self.assertIn('Impeccable', notice)
        self.assertIn('platform-design-skills', notice)
        for path in PACK.rglob('*'):
            if path.is_file():
                self.assertFalse(path.stat().st_mode & 0o111, f'{path} must not be executable')
        self.assertIn('\nname: ui-taste\n', (UPSTREAM / 'PROTOCOL.md').read_text())

    def test_only_the_adapter_registers_with_a_short_trigger(self):
        self.assertEqual([p.relative_to(PACK).as_posix() for p in PACK.rglob('SKILL.md')], ['SKILL.md'])
        adapter = (PACK / 'SKILL.md').read_text()
        self.assertIn('\nname: ui-taste\n', adapter)
        description = re.search(r'\ndescription: "?(.*?)"?\n', adapter).group(1)
        # Hermes' skill index keeps 60 characters; the trigger must survive it.
        self.assertLessEqual(len(description), 60, description)
        self.assertTrue(description.startswith('Use '), description)
        for rule in ('upstream/PROTOCOL.md', 'Impeccable', 'audit only unless',
                     'find_ui_references', 'never configure', 'UPSTREAM.json'):
            self.assertIn(rule, adapter)
        for link in re.findall(r'\]\(([^)#]+)', adapter):
            if not link.startswith('http'):
                self.assertTrue((PACK / link).exists(), link)

    def test_portable_adapter_points_at_the_wrapped_protocol(self):
        portable = (ROOT / 'adapters/skills/ui-taste/SKILL.md').read_text()
        self.assertIn('../../../skills/ui-taste/SKILL.md', portable)
        self.assertIn('../../../skills/ui-taste/upstream/PROTOCOL.md', portable)

    def test_clean_profile_receives_ui_taste_offline(self):
        spec = importlib.util.spec_from_file_location('ui_taste_installer', ROOT / 'install_skills.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / 'default'
            self.assertEqual(module.install(ROOT / 'skills', [('default', home)], report=lambda _: None), 0)
            for name in ('SKILL.md', 'upstream/PROTOCOL.md', 'upstream/reference/craft.md',
                         'upstream/NOTICE', 'upstream/LICENSE'):
                self.assertTrue((home / 'skills/ui-taste' / name).is_file(), name)


if __name__ == '__main__':
    unittest.main()
