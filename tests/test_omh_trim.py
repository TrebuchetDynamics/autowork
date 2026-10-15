"""The managed OMH trim: unused OMH skills join skills.disabled without touching user entries."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OmhTrimTests(unittest.TestCase):
    def setUp(self):
        self.keep = ['code-review', 'context']
        pkg = types.ModuleType('trim_pkg'); pkg.__path__ = [str(ROOT)]
        bundle = types.ModuleType('trim_pkg.bundle')
        bundle.defaults = lambda: {'hermes': {'approvals_mode': 'off', 'destructive_slash_confirm': False,
                                              'mcp_reload_confirm': False, 'max_turns': 'unlimited',
                                              'allow_gateway_injection': True},
                                   'omh_keep_skills': self.keep}
        sys.modules.update({'trim_pkg': pkg, 'trim_pkg.bundle': bundle})
        self.addCleanup(lambda: [sys.modules.pop(k, None) for k in list(sys.modules) if k.startswith('trim_pkg')])
        spec = importlib.util.spec_from_file_location('trim_pkg.runtime_defaults', ROOT / 'runtime_defaults.py')
        self.rd = importlib.util.module_from_spec(spec); sys.modules[spec.name] = self.rd; spec.loader.exec_module(self.rd)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name) / 'omh'
        skills = {'code-review': 'omh-code-review', 'context': 'ulw-context',
                  'wiki-export': 'omh-wiki-export', 'browser-operator': 'omh-browser'}
        rows = []
        for catalog, registered in skills.items():
            path = self.store / 'skills/group' / registered / 'SKILL.md'
            path.parent.mkdir(parents=True)
            path.write_text(f'---\nname: "{registered}"\ndescription: x\n---\n# {catalog}\n')
            rows.append({'name': catalog, 'path': f'group/{registered}/SKILL.md'})
        self.manifest = {'package': 'oh-my-hermes', 'skills': rows}
        (self.store / 'manifest.json').write_text(json.dumps(self.manifest))
        self.raw = {'skills': {'external_dirs': [str(self.store / 'skills')], 'disabled': ['my-own-skill']},
                    'platforms': {'telegram': {'extra': {'command_menu': {'priority': []}}}}}

    def apply(self, raw):
        patch = self.rd.expected_settings(raw)
        if 'skills' in patch:
            raw.setdefault('skills', {})['disabled'] = patch['skills']['disabled']
        entry = patch['plugins']['entries']['hermes-toolset']
        if 'omh_trim' in entry:
            raw.setdefault('plugins', {}).setdefault('entries', {}).setdefault('hermes-toolset', {})['omh_trim'] = entry['omh_trim']
        return patch

    def test_unkept_omh_skills_join_user_entries_by_registered_name(self):
        self.apply(self.raw)
        self.assertEqual(self.raw['skills']['disabled'], ['my-own-skill', 'omh-browser', 'omh-wiki-export'])
        self.assertEqual(self.raw['plugins']['entries']['hermes-toolset']['omh_trim'], ['omh-browser', 'omh-wiki-export'])
        # Idempotent: a second pass reports no drift.
        drift = self.rd.settings_drift(self.raw, self.rd.expected_settings(self.raw))
        self.assertNotIn('skills.disabled', drift)
        self.assertNotIn('plugins.entries.hermes-toolset.omh_trim', drift)

    def test_keeping_a_skill_removes_only_that_managed_entry(self):
        self.apply(self.raw)
        self.keep.append('browser-operator')
        self.apply(self.raw)
        self.assertEqual(self.raw['skills']['disabled'], ['my-own-skill', 'omh-wiki-export'])
        self.assertEqual(self.raw['plugins']['entries']['hermes-toolset']['omh_trim'], ['omh-wiki-export'])

    def test_profiles_without_omh_or_keep_list_gain_nothing(self):
        plain = {'platforms': {'telegram': {'extra': {'command_menu': {'priority': []}}}}}
        patch = self.rd.expected_settings(plain)
        self.assertNotIn('skills', patch)
        self.assertNotIn('omh_trim', patch['plugins']['entries']['hermes-toolset'])
        self.keep.clear(); self.keep.extend([])
        sys.modules['trim_pkg.bundle'].defaults = lambda: {'hermes': {'approvals_mode': 'off', 'destructive_slash_confirm': False,
            'mcp_reload_confirm': False, 'max_turns': 'unlimited', 'allow_gateway_injection': True}}
        self.assertNotIn('skills', self.rd.expected_settings(self.raw))

    def test_foreign_manifest_and_escaping_paths_are_ignored(self):
        self.manifest['package'] = 'someone-else'
        (self.store / 'manifest.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.rd.omh_skills(self.raw), {})
        self.manifest.update(package='oh-my-hermes', skills=[{'name': 'evil', 'path': '../../outside/SKILL.md'}])
        (self.store / 'manifest.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.rd.omh_skills(self.raw), {})

    def test_bundled_toolset_skills_are_never_left_disabled(self):
        self.raw['skills']['disabled'].append('autowork')
        self.apply(self.raw)
        self.assertNotIn('autowork', self.raw['skills']['disabled'])
        self.assertIn('my-own-skill', self.raw['skills']['disabled'])

    def test_bundle_keep_list_names_real_catalog_skills(self):
        keep = json.loads((ROOT / 'plugins/defaults.json').read_text())['omh_keep_skills']
        self.assertEqual(keep, sorted(set(keep)))
        for name in ('code-review', 'verification-gate', 'oh-my-hermes', 'doctor', 'memory-new'):
            self.assertIn(name, keep)


if __name__ == '__main__':
    unittest.main()
