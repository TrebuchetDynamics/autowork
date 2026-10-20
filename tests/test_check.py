"""Exercise the offline runner in small copies without importing unsafe tests."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check.py'


class OfflineCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='offline checker ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'scripts').mkdir()
        self.script = self.root / 'scripts/check.py'
        if SCRIPT.exists():
            shutil.copy2(SCRIPT, self.script)

    def write(self, relative, content):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def run_check(self, *args, env=None):
        return subprocess.run([sys.executable, str(self.script), *args],
                              cwd=self.root, env=env, text=True,
                              capture_output=True, timeout=15)

    def test_listing_is_import_free_and_uses_owned_directories(self):
        sentinel = "raise RuntimeError('unsafe import must never run')\n"
        self.write('tests/test_unit.py', sentinel)
        self.write('skills/autowork/scripts/test_budget_controller.py', sentinel)
        self.write('vendor/examples/test_external.py', sentinel)
        self.write('skills/autowork/references/vendor/test_external.py', sentinel)
        self.write('skills/docs-sync/scripts/test_goal_gap_regression.py', sentinel)
        self.write('skills/autowork/scripts/test_native_lifecycle_controls.py', sentinel)
        self.write('tests/integration_plugin.py', sentinel)
        result = self.run_check('--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('RUN tests/test_unit.py', result.stdout)
        self.assertIn('RUN skills/autowork/scripts/test_budget_controller.py', result.stdout)
        self.assertIn('EXCLUDE skills/docs-sync/scripts/test_goal_gap_regression.py [model]', result.stdout)
        self.assertIn('EXCLUDE skills/autowork/scripts/test_native_lifecycle_controls.py [native]', result.stdout)
        self.assertIn('EXCLUDE tests/integration_plugin.py [integration]', result.stdout)
        self.assertNotIn('test_external.py', result.stdout)
        self.assertNotIn('unsafe import', result.stdout + result.stderr)

    def test_importable_inventory_is_side_effect_free(self):
        self.assertTrue(SCRIPT.is_file(), 'missing offline checker')
        spec = importlib.util.spec_from_file_location('check_inventory', SCRIPT)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        included = self.write('tests/test_unit.py', "raise RuntimeError('do not import')\n")
        self.assertEqual(checker.discover_tests(self.root), [included])
        alias = self.root / 'checkout-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(checker.discover_tests(alias), [included])
        (self.root / 'tests/test_link.py').symlink_to(included)
        self.assertEqual(checker.discover_tests(self.root), [included])

    def test_symlinked_directory_components_never_import_external_tests(self):
        cases = (('tests', 'test_external.py'),
                 ('skills', 'autowork/scripts/test_external.py'),
                 ('skills/autowork', 'scripts/test_external.py'),
                 ('skills/autowork/scripts', 'test_external.py'))
        base = self.root
        for index, (link_name, module_name) in enumerate(cases):
            with self.subTest(component=link_name):
                self.root = base / f'case-{index}'
                self.script = self.root / 'scripts/check.py'
                self.script.parent.mkdir(parents=True)
                shutil.copy2(SCRIPT, self.script)
                external = base / f'external-{index}'
                external.mkdir()
                sentinel = external / 'imported'
                module = external / module_name
                module.parent.mkdir(parents=True, exist_ok=True)
                module.write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).touch()\n')
                link = self.root / link_name
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(external, target_is_directory=True)
                try:
                    control = ('skills/docs-sync/scripts/test_owned.py'
                               if link_name == 'tests' else 'tests/test_owned.py')
                    self.write(control,
                               'import unittest\nclass Owned(unittest.TestCase):\n'
                               '    def test_owned(self): pass\n')
                    listed = self.run_check('--list')
                    self.assertEqual(listed.returncode, 0, listed.stderr)
                    self.assertNotIn('RUN ' + str(Path(link_name) / module_name), listed.stdout)
                    result = self.run_check()
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('Ran 1 test', result.stdout)
                    self.assertFalse(sentinel.exists(), 'external module was imported')
                finally:
                    link.unlink()

    def test_runs_real_tests_without_live_flags_or_unsafe_imports(self):
        self.write('tests/test_environment.py', '''import os, unittest
class Check(unittest.TestCase):
    def test_environment(self):
        for name in ('CONTAINMENT_LINUX_TESTS', 'RUN_CONTROLLER_BRIDGE_LINUX', 'HERMES_NATIVE_HANDOFF_TEST', 'HERMES_NATIVE_REGISTRATION_TEST',
                     'PI_AUTOWORK_MAIN_CHECK', 'AUTOWORK_CACHE'):
            self.assertFalse(name in os.environ, name + ' leaked into offline tests')
''')
        self.write('skills/docs-sync/scripts/test_goal_gap_regression.py',
                   "raise RuntimeError('live model imported')\n")
        env = dict(os.environ, CONTAINMENT_LINUX_TESTS='1', RUN_CONTROLLER_BRIDGE_LINUX='1',
                   HERMES_NATIVE_HANDOFF_TEST='1', HERMES_NATIVE_REGISTRATION_TEST='1',
                   PI_AUTOWORK_MAIN_CHECK='false', AUTOWORK_CACHE='/elsewhere')
        result = self.run_check(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Ran 1 test', result.stdout + result.stderr)
        self.assertIn('1 test directories passed', result.stdout)
        self.assertNotIn('live model imported', result.stdout + result.stderr)

    def test_a_broken_tree_fails_before_any_test_runs(self):
        """Conflict markers twice reached main in Python modules; the tree guard runs first."""
        guard = ROOT / 'scripts/tree_guard.py'
        self.assertTrue(guard.is_file(), 'missing tree guard')
        shutil.copy2(guard, self.root / 'scripts/tree_guard.py')
        self.write('tests/test_ran.py', 'import unittest\nfrom pathlib import Path\nclass Ran(unittest.TestCase):\n'
                   "    def test_ran(self): Path('ran').write_text('yes')\n")
        git = lambda *a: subprocess.run(['git', '-c', 'user.email=t@example.invalid', '-c', 'user.name=T', *a],
                                        cwd=self.root, check=True, capture_output=True)
        git('init', '-q')
        self.write('broken.py', 'def f(:\n')
        git('add', '-A')
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('broken.py:1: python', result.stdout)
        self.assertFalse((self.root / 'tests/ran').exists(), 'tests ran on a broken tree')
        self.assertTrue(self.run_check('--list').returncode == 0, 'listing stays import- and check-free')
        self.write('broken.py', 'x = 1\n')
        git('add', '-A')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('tree_guard: OK', result.stdout)

    def test_tests_the_resource_gate_skipped_are_counted_not_failed(self):
        """TOOLSET-193-54: a busy host is not a failing check."""
        self.write('tests/test_gate.py', '''import sys, unittest
class Gate(unittest.TestCase):
    def test_gated(self):
        print('RESOURCE_GATE_SKIP: resource gate: load average 30.00 >= 24 CPUs', file=sys.stderr)
        raise unittest.SkipTest('host busy')
''')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Skipped by the host resource gate: 1 test(s)', result.stdout)

    def test_fixtures_can_push_although_the_runner_guards_pushes(self):
        """TOOLSET-186-07: a runner's main check reported 20 failures, all fixture pushes its
        push guard refused; outside the runner the same tree passed."""
        self.write('tests/test_push.py', '''import os, subprocess, tempfile, unittest
class Push(unittest.TestCase):
    def test_push(self):
        with tempfile.TemporaryDirectory() as root:
            git = lambda *a: subprocess.run(['git', '-c', 'user.email=t@example.invalid', '-c', 'user.name=T', *a],
                                           check=True, capture_output=True)
            git('init', '-q', '--bare', root + '/bare')
            git('init', '-q', root + '/work')
            git('-C', root + '/work', 'commit', '-q', '--allow-empty', '-m', 'x')
            git('-C', root + '/work', 'push', '-q', root + '/bare', 'HEAD:refs/heads/main')
        self.assertEqual(os.environ.get('GIT_CONFIG_KEY_0'), 'core.abbrev')  # other settings stay
''')
        guard = {'GIT_CONFIG_COUNT': '3', 'GIT_CONFIG_KEY_0': 'url.pi-autowork-push-disabled:///.pushInsteadOf',
                 'GIT_CONFIG_VALUE_0': '', 'GIT_CONFIG_KEY_1': 'core.abbrev', 'GIT_CONFIG_VALUE_1': '12',
                 'GIT_CONFIG_KEY_2': 'protocol.pi-autowork-push-disabled.allow', 'GIT_CONFIG_VALUE_2': 'never'}
        result = self.run_check(env=dict(os.environ, **guard))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('1 test directories passed', result.stdout)
        with tempfile.TemporaryDirectory() as root:  # the guard itself still refuses pushes
            subprocess.run(['git', 'init', '-q', '--bare', root + '/bare'], check=True)
            pushed = subprocess.run(['git', 'push', root + '/bare', 'HEAD:refs/heads/x'], cwd=ROOT, capture_output=True,
                                    env=dict(os.environ, **guard))
            self.assertNotEqual(pushed.returncode, 0)

    def test_failure_propagates_but_other_directory_still_runs(self):
        self.write('tests/test_failure.py', '''import unittest
class Check(unittest.TestCase):
    def test_failure(self): self.fail('deliberate regression')
''')
        self.write('skills/docs-sync/scripts/test_marker.py', '''from pathlib import Path
import unittest
class Check(unittest.TestCase):
    def test_marker(self): Path('checked').write_text('yes')
''')
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('deliberate regression', result.stdout + result.stderr)
        self.assertTrue((self.root / 'skills/docs-sync/scripts/checked').is_file())

    def test_nonfinite_timeout_is_rejected_before_checks(self):
        marker = self.root / 'executed'
        self.write('tests/test_marker.py',
                   f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
        for value in ('nan', 'inf', '-inf'):
            with self.subTest(timeout=value):
                marker.unlink(missing_ok=True)
                result = self.run_check(f'--timeout={value}')
                self.assertFalse(marker.exists(), result.stdout + result.stderr)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn('--timeout must be positive', result.stderr)
                self.assertNotIn('CHECK', result.stdout)

    def test_invalid_output_bytes_preserve_results_and_other_directories(self):
        for fails in (False, True):
            with self.subTest(fails=fails):
                self.write('tests/test_bytes.py',
                           'import os, unittest\nclass Check(unittest.TestCase):\n'
                           '    def test_bytes(self):\n'
                           '        os.write(1, b"diagnostic-\\xff\\n")\n'
                           f'        self.assertFalse({fails!r}, "deliberate failure")\n')
                self.sleeper('skills/docs-sync/scripts/test_control.py', 0, 'control')
                result = self.run_check()
                self.assertEqual(result.returncode, int(fails), result.stdout + result.stderr)
                self.assertIn('diagnostic-\ufffd', result.stdout)
                self.assertIn('OUTPUT-control', result.stdout)
                self.assertIn(f'{2 - int(fails)} test directories passed; {int(fails)} failed',
                              result.stdout)
                self.assertNotIn('UnicodeDecodeError', result.stderr)

    def test_timeout_is_a_failure_not_a_skip(self):
        self.write('tests/test_hang.py', 'import time; time.sleep(3)\n')
        result = self.run_check('--timeout', '0.1')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('TIMEOUT', result.stdout)


    def sleeper(self, relative, seconds, marker):
        self.write(relative, f'''import time, unittest
class Check(unittest.TestCase):
    def test_{marker}(self):
        time.sleep({seconds})
        print('OUTPUT-{marker}', flush=True)
''')

    def test_directories_run_concurrently_with_output_in_directory_order(self):
        self.sleeper('tests/test_slow.py', 1.5, 'first')
        self.sleeper('skills/docs-sync/scripts/test_fast.py', 1.5, 'second')
        started = time.monotonic()
        result = self.run_check()
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(elapsed, 2.8, 'directories did not overlap')
        out = result.stdout
        self.assertLess(out.index('CHECK tests'), out.index('OUTPUT-first'))
        self.assertLess(out.index('OUTPUT-first'), out.index('CHECK skills/docs-sync/scripts'))
        self.assertLess(out.index('CHECK skills/docs-sync/scripts'), out.index('OUTPUT-second'))
        self.assertTrue(out.rstrip().endswith('Offline result: 2 test directories passed; 0 failed; 0 modules excluded.'))

    def test_modules_of_one_directory_run_concurrently(self):
        self.sleeper('tests/test_slow.py', 1.5, 'first')
        self.sleeper('tests/test_also_slow.py', 1.5, 'second')
        started = time.monotonic()
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(time.monotonic() - started, 2.8, 'modules did not overlap')
        self.assertLess(result.stdout.index('OUTPUT-second'), result.stdout.index('OUTPUT-first'))  # module order
        self.assertIn('1 test directories passed', result.stdout)

    def test_selected_split_module_runs_only_its_shards(self):
        body = ''.join(f'''    def test_{n}(self):
        Path('ran-{n}').write_text(str(os.getpid()))
''' for n in range(24))
        module = self.write('tests/test_pi_autowork.py', 'import os, unittest\nfrom pathlib import Path\n'
                            'class Runner(unittest.TestCase):\n' + body)
        self.write('skills/docs-sync/scripts/test_unselected.py', "raise RuntimeError('not selected')\n")
        for paths in (['tests/test_pi_autowork.py'], ['tests'], [str(module), 'tests']):
            with self.subTest(paths=paths):
                for marker in module.parent.glob('ran-*'):
                    marker.unlink()
                result = self.run_check(*paths)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Offline inventory: 1 modules in 1 directories', result.stdout)
                self.assertIn('1 test directories passed; 0 failed', result.stdout)
                pids = [(module.parent / f'ran-{n}').read_text() for n in range(24)]
                self.assertEqual(len(set(pids)), 12)  # two tests per shard, not serial or duplicated
                self.assertNotIn('not selected', result.stdout)
        for marker in module.parent.glob('ran-*'):
            marker.unlink()
        filtered = self.run_check('tests/test_pi_autowork.py', '-k', 'test_23')
        self.assertEqual(filtered.returncode, 0, filtered.stdout + filtered.stderr)
        self.assertEqual([p.name for p in module.parent.glob('ran-*')], ['ran-23'])
        self.assertIn('Ran 1 test', filtered.stdout)
        module.write_text(module.read_text() + '    def test_failure(self): self.fail("shard failure")\n')
        failed = self.run_check('tests/test_pi_autowork.py')
        self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
        self.assertIn('shard failure', failed.stdout)
        for path in ('tests/missing.py', 'vendor', '../outside',
                     'skills/docs-sync/scripts/test_goal_gap_regression.py'):
            with self.subTest(invalid=path):
                result = self.run_check('tests/test_pi_autowork.py', path)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertNotIn('CHECK', result.stdout)

    def test_default_jobs_follow_idle_cpus_between_four_and_eight(self):
        from unittest import mock
        spec = importlib.util.spec_from_file_location('check_jobs', SCRIPT)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        for cpus, load, jobs in ((22, 0.5, 8), (22, 16.2, 6), (22, 30.0, 4), (2, 0.0, 4)):
            with self.subTest(cpus=cpus, load=load), mock.patch.object(checker.os, 'cpu_count', return_value=cpus), \
                    mock.patch.object(checker.os, 'getloadavg', return_value=(load, load, load)):
                self.assertEqual(checker.default_jobs(), jobs)

    def test_jobs_one_runs_sequentially_with_the_same_output(self):
        self.sleeper('tests/test_slow.py', 1, 'first')
        self.sleeper('skills/docs-sync/scripts/test_fast.py', 1, 'second')
        started = time.monotonic()
        sequential = self.run_check('--jobs', '1')
        self.assertGreaterEqual(time.monotonic() - started, 2)
        concurrent = self.run_check()
        for result in (sequential, concurrent):
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        strip = lambda text: [line for line in text.splitlines() if not line.startswith(('Ran ', '---', 'OK'))]
        self.assertEqual(strip(sequential.stdout), strip(concurrent.stdout))

    def test_jobs_must_be_a_positive_integer(self):
        for value in ('0', '-1', 'x'):
            with self.subTest(jobs=value):
                result = self.run_check('--jobs', value)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertNotIn('CHECK', result.stdout)

    def test_concurrent_timeout_fails_only_its_directory(self):
        self.write('tests/test_hang.py', 'import time; time.sleep(5)\n')
        self.sleeper('skills/docs-sync/scripts/test_fast.py', 0, 'second')
        result = self.run_check('--timeout', '1')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('TIMEOUT: ', result.stdout)
        self.assertIn('OUTPUT-second', result.stdout)
        self.assertIn('1 test directories passed; 1 failed', result.stdout)

if __name__ == '__main__':
    unittest.main()
