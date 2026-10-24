"""Real installer orchestration with fake child processes, no network or profiles."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src_fixture import copy_sources

ROOT = Path(__file__).resolve().parents[1]


class CompleteSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo with spaces'
        copy_sources(self.repo)
        self.home = Path(self.tmp.name) / 'hermes home'
        self.home.mkdir()
        for name in ('sample', 'deleted', 'ghost'):
            p = self.home / 'profiles' / name
            p.mkdir(parents=True)
            if name != 'ghost': (p / 'config.yaml').touch()
        (self.home / 'profiles/.deleted').mkdir()
        (self.home / 'profiles/.deleted/deleted').touch()
        self.log = self.repo / 'calls.jsonl'
        self.env = dict(os.environ, HERMES_HOME=str(self.home), LOG=str(self.log))
        # These tests exercise orchestration after admission; the real preflight
        # and its no-write failure paths are covered in test_preflight.py.
        (self.repo / 'setup_preflight.py').write_text(
            "def preflight(*args, **kwargs): return {'errors': [], 'plan': []}\n"
            "def print_plan(report): pass\n")
        for name in ('install-skills.sh', 'install-plugins.sh'):
            (self.repo / name).write_text('''#!/bin/bash
python3 - "$0" "$@" <<'CHILD'
import json,os,sys
with open(os.environ['LOG'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
sys.exit(int(os.environ.get('CHILD_FAIL','0')))
CHILD
''')
        binary = self.repo / 'hermes'
        binary.write_text('''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['LOG'],'a') as f:f.write(json.dumps(['hermes']+sys.argv[1:])+'\\n')
sys.exit(5 if os.environ.get('VERIFY_FAIL')==sys.argv[2] else 0)
''')
        binary.chmod(0o755)
        self.env['PATH'] = str(self.repo) + ':' + self.env['PATH']

    def run_setup(self, *args):
        self.assertTrue((ROOT / 'setup_bundle.py').is_file(), 'missing complete setup orchestrator')
        return subprocess.run([sys.executable, str(self.repo / 'setup_bundle.py'), *args],
                              env=self.env, capture_output=True, text=True)

    def test_missing_declared_source_payload_refuses_before_any_stage(self):
        copy_sources(self.repo)
        for name in ('plugin.yaml', 'plugins/defaults.json', 'plugins/PLUGINS.md',
                     'scripts/preflight_config.py'):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        skill = self.repo / 'skills/example/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('fixture')
        spec = importlib.util.spec_from_file_location('copied_preflight', self.repo / 'setup_preflight.py')
        pre = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pre)
        payload = ['autowork_bootstrap.py', 'Src/autowork_bootstrap.py',
                   *['Src/autowork_runtime/' + name for name in (
                       'install_skills.py', 'setup_bundle.py', 'setup_preflight.py',
                       'setup_runtime.py', 'install_omh.py', 'install_graphify.py')]]
        before = sorted(self.home.rglob('*'))
        for name in payload:
            with self.subTest(missing=name):
                path = self.repo / name
                body = path.read_bytes()
                path.unlink()
                try:
                    with patch.object(pre, 'runtime_check', return_value=[]), \
                         patch.object(pre.shutil, 'which', return_value='/bin/available'), \
                         patch.object(pre.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='')) as run:
                        report = pre.preflight(self.repo, self.home, [('default', self.home)], bundle_only=True)
                    self.assertTrue(any(name in error for error in report['errors']), report)
                    run.assert_not_called()
                    self.assertEqual(before, sorted(self.home.rglob('*')))
                finally:
                    path.write_bytes(body)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_default_installs_skills_configures_and_finalizes_each_live_profile(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertTrue(calls[0][0].endswith('install-skills.sh'))
        self.assertTrue(calls[1][0].endswith('install-plugins.sh'))
        for option in ('--sources-only', '--setup', '--enable'): self.assertIn(option, calls[1])
        self.assertEqual([c[2] for c in calls[2:]], ['default', 'sample'])
        self.assertTrue(all(c[3:5] == ['autowork', 'finalize'] for c in calls[2:]))

    def test_failure_keeps_finalization_and_nonzero_status(self):
        self.env['CHILD_FAIL'] = '9'
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([c[2] for c in self.calls() if c[0]=='hermes'], ['default','sample'])
        self.assertIn('incomplete', result.stdout.lower())

    def test_verification_failure_does_not_claim_complete(self):
        self.env['VERIFY_FAIL'] = 'sample'
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('incomplete', result.stdout.lower())

    def test_named_profile_home_resolves_to_all_profiles_and_bundle_only_forwards(self):
        self.env['HERMES_HOME'] = str(self.home / 'profiles/sample')
        result = self.run_setup('--bundle-only', '--no-reload')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--bundle-only', self.calls()[1])
        for call in self.calls()[2:]:
            self.assertIn('--bundle-only', call)
            self.assertIn('--no-reload', call)
            self.assertEqual(call[call.index('--hermes-home')+1], str(self.home))

    def test_symlinked_profile_refuses_before_configuration(self):
        import shutil
        sample=self.home/'profiles/sample'
        shutil.rmtree(sample)
        shared=Path(self.tmp.name)/'shared'
        shared.mkdir()
        (shared/'config.yaml').touch()
        sample.symlink_to(shared,target_is_directory=True)
        self.assertNotEqual(self.run_setup().returncode,0)
        self.assertEqual(self.calls(),[])

    def test_profile_symlinks_hermes_ignores_do_not_abort_setup(self):
        profiles=self.home/'profiles'
        shared=Path(self.tmp.name)/'shared'
        shared.mkdir()
        (shared/'config.yaml').touch()
        (profiles/'.deleted/gone').touch()
        (profiles/'gone').symlink_to(shared,target_is_directory=True)
        (profiles/'Bad.Name').symlink_to(shared,target_is_directory=True)
        (profiles/'dangling').symlink_to(Path(self.tmp.name)/'missing')
        empty=Path(self.tmp.name)/'empty'
        empty.mkdir()
        (profiles/'unmarked').symlink_to(empty,target_is_directory=True)
        result=self.run_setup()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual([c[2] for c in self.calls()[2:]],['default','sample'])

    def test_dry_run_never_finalizes_and_invalid_flags_never_run_children(self):
        self.assertEqual(self.run_setup('--dry-run').returncode, 0)
        self.assertEqual(self.calls(), [])
        self.assertNotEqual(self.run_setup('--unknown').returncode, 0)
        self.assertEqual(self.calls(), [])


if __name__ == '__main__': unittest.main()
