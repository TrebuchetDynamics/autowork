"""Core command readiness is separate from external integration readiness."""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class DoctorModes(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('doctor_bundle', ROOT / 'bundle.py')
        self.bundle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bundle)
        names = [p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')]
        self.report = {
            'plugins': [{'name': 'autowork', 'enabled': True, 'error': None}],
            'plugin_skills': ['autowork:' + name for name in ('autowork', 'cron-autowork', 'docs-sync', 'plan-with-me', 'blockers', 'plan-for-me', 'autoresearch', 'engineering', 'git-commit-push', 'impeccable', 'lgtm', 'profile-create', 'ui-taste', 'beautify-github-readme', 'pending',
                'ponytail', 'ponytail-review', 'ponytail-audit', 'ponytail-debt', 'ponytail-gain', 'ponytail-help')],
            'commands': [{'command': name.replace('_', '-'), 'source': 'autowork', 'kind': 'plugin'}
                         for name in names],
            'missing_plugins': ['omh'], 'missing_skills': ['graphify'],
            'unchecked_skill_sources': ['https://example.invalid/skills'],
        }

    def run_doctor(self, *options):
        parser = argparse.ArgumentParser()
        self.bundle.setup_parser(parser)
        args = parser.parse_args(['doctor', *options])
        output = io.StringIO()
        with patch.object(self.bundle, 'inventory', return_value=self.report) as inventory:
            with contextlib.redirect_stdout(output):
                code = self.bundle.handle_cli(args)
            self.assertEqual(inventory.call_count, 1)
        return code, output.getvalue()

    def test_doctor_lists_linked_profiles_without_failing(self):
        rows = [{'profile': 'work', 'target': '/src/autowork', 'link': '/src/autowork',
                 'revision': 'a' * 40, 'dirty': False, 'released': True}]
        with patch.object(self.bundle, 'linked_profiles', return_value=rows):
            code, output = self.run_doctor('--core', '--json')
            self.assertEqual((code, json.loads(output)['linked_profiles']), (0, rows))
            code, output = self.run_doctor('--core')
        self.assertIn('any gateway restart loads its current files: work', output)
        self.assertIn('hermes autowork pin NAME --dry-run', output)

    def test_pin_command_runs_the_updater_for_one_profile(self):
        parser = argparse.ArgumentParser()
        self.bundle.setup_parser(parser)
        for options, flag in ((['--dry-run'], '--pin-profile'), (['--unpin'], '--unpin-profile')):
            args = parser.parse_args(['pin', 'work', '--hermes-home', '/h', *options])
            with patch.object(self.bundle.subprocess, 'run') as run:
                run.return_value.returncode = 0
                self.assertEqual(self.bundle.handle_cli(args), 0)
            argv = run.call_args.args[0]
            self.assertEqual(argv[2:], ['--hermes-home', '/h', flag, 'work'] + (['--dry-run'] if flag == '--pin-profile' else []))

    def test_core_succeeds_with_visible_external_gaps(self):
        code, output = self.run_doctor('--core', '--json')
        data = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(data['scope'], 'core')
        self.assertEqual(data['status'], 'ready')
        self.assertEqual(data['integrations_status'], 'unavailable')
        self.assertEqual(data['missing_plugins'], ['omh'])

    def test_default_full_check_fails_on_external_gaps(self):
        code, output = self.run_doctor('--json')
        self.assertEqual(code, 1)
        data = json.loads(output)
        self.assertEqual(data['core_status'], 'ready')
        self.assertEqual(data['status'], 'incomplete')

    def test_existing_ponytail_command_uses_verified_bundled_skill_fallback(self):
        row = next(row for row in self.report['commands'] if row['command'] == 'ponytail-review')
        row['source'] = 'ponytail'
        code, output = self.run_doctor('--core', '--json')
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(output)['bundled_skill_fallbacks'], ['autowork:ponytail-review'])
        code, output = self.run_doctor('--core')
        self.assertIn('autowork:ponytail-review', output)
        self.report['plugin_skills'].remove('autowork:ponytail-review')
        self.assertEqual(self.run_doctor('--core', '--json')[0], 1)

    def test_foreign_command_cannot_certify_core(self):
        self.report['commands'][0]['source'] = 'another-plugin'
        code, output = self.run_doctor('--core', '--json')
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(output)['core_errors'])

    def test_missing_skill_registration_fails_even_with_command(self):
        self.report['plugin_skills'].pop()
        code, output = self.run_doctor('--core', '--json')
        self.assertEqual(code, 1)
        self.assertIn('skill', ' '.join(json.loads(output)['core_errors']).lower())

    def test_disabled_or_failed_plugin_fails_core(self):
        for change in ({'enabled': False}, {'error': 'load failed'}):
            with self.subTest(change=change):
                self.report['plugins'][0] = dict(name='autowork', enabled=True, error=None)
                self.report['plugins'][0].update(change)
                code, _ = self.run_doctor('--core', '--json')
                self.assertEqual(code, 1)

    def test_human_output_distinguishes_registration_from_live_use(self):
        code, output = self.run_doctor('--core')
        self.assertEqual(code, 0)
        self.assertIn('Core: ready', output)
        self.assertIn('Integrations: unavailable', output)
        self.assertIn('omh', output)
        self.assertIn('not tested', output)

    def test_complete_full_install_passes(self):
        for field in ('missing_plugins', 'missing_skills', 'unchecked_skill_sources'):
            self.report[field] = []
        code, output = self.run_doctor('--json')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)['integrations_status'], 'ready')


if __name__ == '__main__':
    unittest.main()
