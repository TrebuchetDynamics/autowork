"""Preflight must finish before any profile mutation stage is admitted."""
import contextlib
import importlib.util
import io
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'path', [str(ROOT), *sys.path]):
        spec.loader.exec_module(value)
    return value


class PreflightTests(unittest.TestCase):
    def test_failed_preflight_never_runs_installers_or_changes_profiles(self):
        setup = module('setup_bundle')
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / 'config.yaml').write_text('memory:\n  provider: existing\n')
            before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob('*') if p.is_file()}
            with patch.object(setup, 'preflight', return_value={'errors': ['missing uv'], 'plan': []}), \
                 patch.object(setup.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.main(['--hermes-home', tmp]), 1)
            run.assert_not_called()
            self.assertEqual(before, {str(p.relative_to(home)): p.read_bytes() for p in home.rglob('*') if p.is_file()})

    def check(self, home):
        pre = module('setup_preflight')
        with patch.object(pre, 'runtime_check', return_value=[]), \
             patch.object(pre.shutil, 'which', return_value='/bin/available'):
            return pre.preflight(ROOT, home, [('default', home)], bundle_only=True)

    def test_incomplete_skill_and_plugin_conflicts_abort_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / 'skills/repo-docs').mkdir(parents=True)
            (home / 'plugins').mkdir()
            (home / 'plugins/hermes-toolset').write_text('owned')
            before = sorted(str(p) for p in home.rglob('*'))
            report = self.check(home)
            self.assertTrue(report['errors'])
            self.assertEqual(before, sorted(str(p) for p in home.rglob('*')))

    def test_core_plan_preserves_memory_and_states_autonomous_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.check(Path(tmp))
            self.assertEqual(report['errors'], [])
            plan = '\n'.join(report['plan'])
            self.assertIn('approvals.mode', plan)
            self.assertIn('memory unchanged', plan)
            self.assertIn('default', plan)

    def test_network_failure_is_required_failure(self):
        pre = module('setup_preflight')
        with patch.object(pre.subprocess, 'run', side_effect=TimeoutError):
            self.assertFalse(pre.source_available('https://github.com/example/repo'))

    def test_full_preflight_rejects_file_at_memory_store_before_network(self):
        pre = module('setup_preflight')
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / 'omh').write_text('existing owner data')
            with patch.object(pre, 'runtime_check', return_value=[]), \
                 patch.object(pre.shutil, 'which', return_value='/bin/available'), \
                 patch.object(pre, 'source_available') as network:
                report = pre.preflight(ROOT, home, [('default', home)])
            self.assertTrue(any('OMH store destination' in e for e in report['errors']), report)
            network.assert_not_called()
            self.assertEqual((home / 'omh').read_text(), 'existing owner data')
            self.assertEqual(list(home.iterdir()), [home / 'omh'])

    def test_unknown_path_launcher_is_not_validated_against_other_checkout(self):
        pre = module('setup_preflight')
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / 'hermes'
            script.write_text('#!/bin/sh\necho unknown\n')
            with patch.object(pre.shutil, 'which', return_value=str(script)):
                self.assertIsNone(pre.selected_source())
                self.assertTrue(pre.runtime_check(ROOT, Path(tmp), [], True))


class ConfigProbeTests(unittest.TestCase):
    def setUp(self):
        try:
            import ruamel.yaml
        except ImportError:
            self.skipTest('Run with Hermes managed Python to exercise strict YAML parser')
        spec = importlib.util.spec_from_file_location('config_probe', ROOT / 'scripts/preflight_config.py')
        self.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.probe)

    def test_duplicate_keys_bad_shapes_and_foreign_memory_are_rejected_without_writes(self):
        for config in ('approvals:\n  mode: off\n  mode: manual\n',
                       'plugins: []\n', 'plugins:\n  entries:\n    omh: false\n',
                       'memory:\n  provider: another\n', 'key: [\n'):
            with self.subTest(config=config), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'config.yaml'
                path.write_text(config)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(self.probe.main([str(path)]), 1)
                self.assertEqual(path.read_text(), config)
                self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_core_preserves_foreign_memory_and_errors_do_not_disclose_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.yaml'
            path.write_text('memory:\n  provider: another\n')
            self.assertEqual(self.probe.main(['--core', str(path)]), 0)
            path.write_text('secret: [DO_NOT_PRINT\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(self.probe.main([str(path)]), 1)
            self.assertNotIn('DO_NOT_PRINT', output.getvalue())


if __name__ == '__main__': unittest.main()
