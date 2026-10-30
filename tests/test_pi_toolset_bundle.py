"""Offline integrity and native provisioning of the pi-toolset specialist snapshot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('bug-harvest', 'autonomous-codebase-improver',
         'skill-folder-refactor', 'unused-code')


class PiToolsetBundleTests(unittest.TestCase):
    def test_pinned_instruction_closure_is_complete_and_not_executable(self):
        for name in NAMES:
            with self.subTest(skill=name):
                folder = ROOT / 'skills' / name
                self.assertTrue((folder / 'UPSTREAM.json').is_file(), name)
                pin = json.loads((folder / 'UPSTREAM.json').read_text())
                self.assertEqual(pin['repository'], 'https://github.com/TrebuchetDynamics/pi-toolset')
                self.assertEqual(pin['revision'], '5e9aa8398adb6812fb816bf887d1ad10f12c55db')
                self.assertIn(f'skills/engineering/{name}/SKILL.md', pin['files'])
                self.assertIn('LICENSE', pin['files'])
                actual = {p.relative_to(folder).as_posix()
                          for p in (folder / 'upstream').rglob('*') if p.is_file()}
                self.assertEqual(actual, {f['path'] for f in pin['files'].values()})
                for item in pin['files'].values():
                    target = folder / item['path']
                    self.assertTrue(target.resolve().is_relative_to(folder / 'upstream'))
                    self.assertTrue(target.suffix == '.md' or target.name == 'LICENSE')
                    self.assertNotEqual(target.name, 'SKILL.md')
                    self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), item['sha256'])
                self.assertIn('Copyright (c) 2026 Trebuchet Dynamics',
                              (folder / 'upstream/LICENSE').read_text())
        refs = ROOT / 'skills/autonomous-codebase-improver/upstream/references'
        self.assertTrue(refs.is_dir())
        self.assertEqual({p.name for p in refs.iterdir()},
                         {'campaign.md', 'delegation-and-recovery.md',
                          'pressure-scenarios.md', 'evaluation-receipt.md'})

    def test_local_campaign_evaluation_is_linked_and_has_paired_scenarios(self):
        # Inventory checks only: model decisions and execution need separate evidence.
        folder = ROOT / 'skills/autonomous-codebase-improver'
        reference = 'references/adapter-evaluation.md'
        self.assertIn(f']({reference})', (folder / 'SKILL.md').read_text())
        scenarios = (folder / reference).read_text()
        rows = [line.strip('|').split('|') for line in scenarios.splitlines()
                if re.match(r'^\| A\d+ \|', line)]
        self.assertEqual([row[0].strip() for row in rows],
                         [f'A{number}' for number in range(1, 17)])
        for row in rows:
            self.assertEqual(len(row), 4, row)
            self.assertTrue(all(cell.strip() for cell in row), row)

    def test_native_profile_receives_self_contained_specialists_and_preserves_edits(self):
        spec = importlib.util.spec_from_file_location('specialist_install', ROOT / 'install_skills.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        selected = [ROOT / 'skills' / name for name in (*NAMES, 'shared', 'ponytail', 'engineering')]
        self.assertTrue(all(p.is_dir() for p in selected))
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            for attempt in range(2):
                self.assertEqual(installer.install(ROOT / 'skills', [('fixture', home)],
                                                  skills=selected, report=lambda _: None), 0)
                for name in NAMES:
                    folder = home / 'skills' / name
                    for source in folder.rglob('*.md'):
                        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', source.read_text()):
                            if '://' not in link and not link.startswith('#'):
                                self.assertTrue((source.parent / link.split('#')[0]).exists(),
                                                (source, link))
                    self.assertTrue((folder / 'upstream/PROTOCOL.md').is_file())
                evaluation = Path('autonomous-codebase-improver/references/adapter-evaluation.md')
                self.assertEqual((home / 'skills' / evaluation).read_bytes(),
                                 (ROOT / 'skills' / evaluation).read_bytes())
                shared = home / 'skills/shared/PI-TOOLSET.md'
                self.assertTrue(shared.is_file())
                if attempt == 0:
                    shared.write_text(shared.read_text() + '\nProfile-owned note.\n')
            self.assertTrue(shared.read_text().endswith('Profile-owned note.\n'))


if __name__ == '__main__':
    unittest.main()
