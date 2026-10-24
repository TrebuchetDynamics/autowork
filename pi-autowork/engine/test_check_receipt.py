"""Source/dependency/environment-bound checks, no model or transport."""
import importlib
from pathlib import Path
import sys
import tempfile
import unittest


class ReceiptTests(unittest.TestCase):
    def load(self):
        path = Path(__file__).with_name('check_receipt.py')
        self.assertTrue(path.is_file(), 'check receipt implementation missing')
        import check_receipt
        return importlib.reload(check_receipt)

    def test_malformed_receipts_are_rejected_without_execution(self):
        import json, subprocess
        from unittest.mock import patch
        module = self.load()
        malformed = [None, [], {}, {'before': None},
                     {'before': {'files': [None]}},
                     {'before': {'files': [{'path': 'input'}]}, 'external_before': []}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / 'receipt.json'
            command = [sys.executable, '-c', 'from pathlib import Path; Path("ran").touch()']
            for value in malformed:
                with self.subTest(receipt=value), patch.object(module, 'runtime') as runtime:
                    self.assertFalse(module.reusable(value, root, command, paths=['input']))
                    runtime.assert_not_called()
                saved = json.dumps(value)
                receipt.write_text(saved)
                for action in ('reuse', 'run-or-reuse'):
                    result = subprocess.run([sys.executable, str(Path(__file__).with_name('check_receipt.py')), action,
                        '--workspace', str(root), '--receipt', str(receipt), '--path', 'input',
                        '--', *command], capture_output=True, text=True, timeout=15)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual(receipt.read_text(), saved)
                    self.assertFalse((root / 'ran').exists())

    def test_new_receipt_directory_is_prepared_before_check(self):
        import json, subprocess
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'input').write_text('fixture')
            receipt = root/'new'/'nested'/'check.json'
            argv = [sys.executable, str(Path(__file__).with_name('check_receipt.py')), 'run', '--workspace', str(root),
                    '--receipt', str(receipt), '--path', 'input', '--', sys.executable, '-c', 'pass']
            result = subprocess.run(argv, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(receipt.read_text())['outcome'], 'passed')
            receipt.unlink()
            receipt.parent.rmdir()
            (root/'new'/'nested').write_text('not a directory')
            argv[-1] = 'from pathlib import Path; Path("should-not-run").touch()'
            refused = subprocess.run(argv, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse((root/'should-not-run').exists(), 'destination failure discovered after executing check')

    def test_terminal_metadata_is_removed_from_execution_and_reuse_identity(self):
        import os
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'input').write_text('same')
            command = [sys.executable, '-c', "import os; assert not {'TERM_SESSION_ID', '_'} & os.environ.keys()"]
            with patch.dict(os.environ, TERM_SESSION_ID='first', _='/first/command', PWD=str(root)):
                receipt = module.execute(root, ['input'], command, 5)
            self.assertEqual(receipt['outcome'], 'passed')
            with patch.dict(os.environ, TERM_SESSION_ID='second', _='/second/command', PWD=str(root)):
                self.assertTrue(module.reusable(receipt, root, command))
            with patch.dict(os.environ, HERMES_KANBAN_TASK='different', PWD=str(root)):
                self.assertFalse(module.reusable(receipt, root, command))

    def test_runtime_inventory_preserves_unreadable_search_path_behavior(self):
        import os
        from unittest.mock import patch
        module = self.load()
        if os.geteuid() == 0:
            self.skipTest('root can read mode-000 directories')
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / 'unreadable'
            site.mkdir()
            site.chmod(0)
            try:
                with patch.object(sys, 'path', [str(site), *sys.path]):
                    expected = sorted([d.metadata['Name'] or '', d.version]
                                      for d in module.importlib.metadata.distributions())
                    self.assertEqual(module.runtime()['packages'], expected)
                    self.assertEqual(module.runtime()['packages'], expected)
            finally:
                site.chmod(0o700)

    def test_runtime_reuses_inventory_without_sharing_mutable_receipt_values(self):
        from unittest.mock import patch
        module = self.load()
        expected = sorted([d.metadata['Name'] or '', d.version]
                          for d in module.importlib.metadata.distributions())
        with patch.object(module.importlib.metadata, 'distributions',
                          wraps=module.importlib.metadata.distributions) as scan:
            first = module.runtime()
            second = module.runtime()
            self.assertEqual(first, second)
            self.assertEqual(second['packages'], expected)
            self.assertEqual(scan.call_count, 1)
            first['packages'].append(['not-installed', '0'])
            second['packages'][0][0] = 'caller-mutated'
            self.assertEqual(module.runtime()['packages'], expected)

    def test_runtime_cache_keeps_distribution_drift_visible_during_checks(self):
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / 'site'
            site.mkdir()
            (root / 'input').write_text('unchanged')
            info = site / 'receipt_cache_fixture-1.dist-info'
            for mode in ('add', 'edit', 'remove'):
                with self.subTest(mode=mode), patch.object(sys, 'path', [str(site), *sys.path]):
                    if mode == 'remove':
                        code = f'import shutil; shutil.rmtree({str(info)!r})'
                    else:
                        version = '1' if mode == 'add' else '2'
                        code = (f'from pathlib import Path; p=Path({str(info)!r}); '
                                f'p.mkdir(exist_ok=True); (p/"METADATA").write_text('
                                f'"Name: receipt-cache-fixture\\nVersion: {version}\\n")')
                    receipt = module.execute(root, ['input'], [sys.executable, '-c', code], 5,
                                             resource_lock=root / 'lock')
                    self.assertEqual(receipt['outcome'], 'environment_changed')
                    self.assertEqual(receipt['before'], receipt['after'])
                    self.assertNotEqual(receipt['runtime']['packages'],
                                        receipt['runtime_after']['packages'])

    def test_runtime_reuses_interpreter_hash_until_file_replacement(self):
        import hashlib
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / 'python'
            executable.write_bytes(b'first interpreter')
            original = Path.read_bytes
            reads = []
            def read(path):
                if path == executable:
                    reads.append(path)
                return original(path)
            with patch.object(sys, 'executable', str(executable)), patch.object(Path, 'read_bytes', read):
                first = module.runtime()['executable_sha256']
                self.assertEqual(module.runtime()['executable_sha256'], first)
                self.assertEqual(len(reads), 1)
                replacement = executable.with_suffix('.new')
                replacement.write_bytes(b'other interpreter')
                replacement.replace(executable)
                second = module.runtime()['executable_sha256']
                self.assertEqual(first, hashlib.sha256(b'first interpreter').hexdigest())
                self.assertEqual(second, hashlib.sha256(b'other interpreter').hexdigest())
                self.assertNotEqual(first, second)
                self.assertEqual(len(reads), 2)

    def test_runtime_inventory_tracks_custom_distribution_providers(self):
        from unittest.mock import patch
        from importlib.metadata import Distribution, DistributionFinder
        module = self.load()
        class DynamicDistribution(Distribution):
            version_text = '1'
            def read_text(self, filename):
                if filename == 'METADATA':
                    return f'Name: dynamic-receipt-fixture\nVersion: {self.version_text}\n'
            def locate_file(self, path):
                return Path(path)
        distribution = DynamicDistribution()
        class Finder(DistributionFinder):
            def find_distributions(self, context=None):
                return [distribution]
        with patch.object(sys, 'meta_path', [*sys.meta_path, Finder()]):
            self.assertIn(['dynamic-receipt-fixture', '1'], module.runtime()['packages'])
            distribution.version_text = '2'
            self.assertIn(['dynamic-receipt-fixture', '2'], module.runtime()['packages'])
        self.assertNotIn(['dynamic-receipt-fixture', '2'], module.runtime()['packages'])

    def test_runtime_inventory_tracks_legacy_egg_and_archive_subpaths(self):
        import zipfile
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            egg = root / 'fixture-1.egg'
            info = egg / 'EGG-INFO'
            info.mkdir(parents=True)
            metadata = info / 'PKG-INFO'
            metadata.write_text('Name: legacy-receipt-fixture\nVersion: 1\n')
            with patch.object(sys, 'path', [str(egg), *sys.path]):
                self.assertIn(['legacy-receipt-fixture', '1'], module.runtime()['packages'])
                metadata.write_text('Name: legacy-receipt-fixture\nVersion: 2\n')
                self.assertIn(['legacy-receipt-fixture', '2'], module.runtime()['packages'])
            archive = root / 'fixture.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('inside/file', 'fixture')
            with patch.object(sys, 'path', [str(archive / 'inside'), *sys.path]):
                expected = sorted([d.metadata['Name'] or '', d.version]
                                  for d in module.importlib.metadata.distributions())
                self.assertEqual(module.runtime()['packages'], expected)

    def test_runtime_inventory_invalidates_when_standard_finders_are_removed(self):
        from unittest.mock import patch
        module = self.load()
        self.assertTrue(module.runtime()['packages'])
        finders = [finder for finder in sys.meta_path
                   if not getattr(finder, 'find_distributions', None)]
        with patch.object(sys, 'meta_path', finders):
            self.assertEqual(module.runtime()['packages'], [])
        self.assertTrue(module.runtime()['packages'])

    def test_runtime_inventory_tracks_case_insensitive_egg_metadata(self):
        from unittest.mock import patch
        module = self.load()
        for egg_name, info_name in (('fixture.EGG', 'EGG-INFO'), ('fixture.egg', 'egg-info')):
            with self.subTest(egg=egg_name, info=info_name), tempfile.TemporaryDirectory() as tmp:
                egg = Path(tmp) / egg_name
                info = egg / info_name
                info.mkdir(parents=True)
                metadata = info / 'PKG-INFO'
                metadata.write_text('Name: case-receipt-fixture\nVersion: 1\n')
                with patch.object(sys, 'path', [str(egg), *sys.path]):
                    self.assertIn(['case-receipt-fixture', '1'], module.runtime()['packages'])
                    metadata.write_text('Name: case-receipt-fixture\nVersion: 2\n')
                    self.assertIn(['case-receipt-fixture', '2'], module.runtime()['packages'])

    def test_runtime_inventory_preserves_symlink_egg_alias_semantics(self):
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'unpacked'
            info = target / 'EGG-INFO'
            info.mkdir(parents=True)
            alias = root / 'fixture.egg'
            alias.symlink_to(target, target_is_directory=True)
            metadata = info / 'PKG-INFO'
            metadata.write_text('Name: alias-receipt-fixture\nVersion: 1\n')
            with patch.object(sys, 'path', [str(alias), *sys.path]):
                self.assertIn(['alias-receipt-fixture', '1'], module.runtime()['packages'])
                metadata.write_text('Name: alias-receipt-fixture\nVersion: 2\n')
                self.assertIn(['alias-receipt-fixture', '2'], module.runtime()['packages'])
            with patch.object(sys, 'path', [str(target), *sys.path]):
                self.assertNotIn(['alias-receipt-fixture', '2'], module.runtime()['packages'])

    def test_runtime_fingerprints_actual_execution_environment(self):
        module = self.load()
        import os
        environment = dict(os.environ, CHECK_EXECUTION_ENV='remapped-value', PWD='/isolated/one')
        first = module.runtime([sys.executable], '/isolated/one', environment)
        changed = dict(environment, CHECK_EXECUTION_ENV='different-value')
        self.assertNotEqual(first['environment_sha256'],
                            module.runtime([sys.executable], '/isolated/one', changed)['environment_sha256'])
        other = dict(environment, PWD='/isolated/two')
        second = module.runtime([sys.executable], '/isolated/two', other)
        self.assertEqual(first['environment_sha256'], second['environment_sha256'])
        self.assertNotEqual(first['execution_environment_sha256'], second['execution_environment_sha256'])

    def test_shared_resource_lock_is_bounded_across_processes(self):
        import subprocess
        import time
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            lock = root / 'resource.lock'
            ready = root / 'ready'
            holder_code = ('import fcntl,time; from pathlib import Path; '
                           f'f=open({str(lock)!r}, "a"); fcntl.flock(f, fcntl.LOCK_EX); '
                           f'Path({str(ready)!r}).touch(); time.sleep(10)')
            holder = subprocess.Popen([sys.executable, '-c', holder_code])
            try:
                deadline = time.monotonic() + 3
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists())
                with self.assertRaisesRegex(ValueError, 'resource lock'):
                    module.execute(root, ['input'], [sys.executable, '-c', 'pass'], 5,
                                   resource_lock=lock, lock_timeout=0.05)
            finally:
                holder.terminate()
                holder.wait(timeout=5)

    def test_backend_environment_and_tool_executable_reject_reuse_without_secret_values(self):
        import os
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            tool = root / 'tool'
            tool.write_text('#!/bin/sh\nexit 0\n')
            tool.chmod(0o700)
            command = [str(tool)]
            with patch.dict(os.environ, {'CHECK_BACKEND': 'fixture-a', 'TEST_API_TOKEN': 'secret-fixture-value'}):
                receipt = module.execute(root, ['input'], command, 5)
                self.assertNotIn('secret-fixture-value', str(receipt))
                with patch.dict(os.environ, {'CHECK_BACKEND': 'fixture-b'}):
                    self.assertFalse(module.reusable(receipt, root, command))
                tool.write_text('#!/bin/sh\n# changed toolchain\nexit 0\n')
                self.assertFalse(module.reusable(receipt, root, command))

    def test_workspace_path_executable_changes_reject_reuse(self):
        import os
        from contextlib import chdir
        from unittest.mock import patch
        module = self.load()
        cases = (('bin', 'bin', 'workspace', 'bin'),
                 ('', '.', 'workspace', '.'),
                 ('.', '.', 'workspace', '.'),
                 ('bin', 'bin', 'workspace:local', 'local/bin'))
        for search_path, tool_dir, workspace, decoy_dir in cases:
            with self.subTest(path=search_path, workspace=workspace), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                root = parent / workspace
                root.mkdir()
                (root / 'input').write_text('unchanged')
                tool = root / tool_dir / 'receipt-test-tool'
                tool.parent.mkdir(exist_ok=True)
                tool.write_text('#!/bin/sh\nexit 0\n')
                tool.chmod(0o700)
                # A caller-side namesake must never supply the executed tool's hash.
                decoy = parent / decoy_dir / tool.name
                decoy.parent.mkdir(parents=True, exist_ok=True)
                decoy.write_text('#!/bin/sh\nexit 99\n')
                decoy.chmod(0o700)
                command = [tool.name]
                with chdir(parent), patch.dict(os.environ, PATH=search_path):
                    receipt = module.execute(root, ['input'], command, 5, resource_lock=parent / 'lock')
                    self.assertEqual(receipt['outcome'], 'passed')
                    self.assertTrue(module.reusable(receipt, root, command))
                    tool.write_text('#!/bin/sh\nexit 1\n')
                    fresh = module.execute(root, ['input'], command, 5, resource_lock=parent / 'lock')
                    self.assertEqual(fresh['outcome'], 'failed')
                    self.assertFalse(module.reusable(receipt, root, command))

    def test_receipts_without_execution_directory_resolution_policy_are_not_reused(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('unchanged')
            command = [sys.executable, '-c', 'pass']
            receipt = module.execute(root, ['input'], command, 5, resource_lock=root / 'lock')
            self.assertTrue(module.reusable(receipt, root, command))
            for key in ('runtime', 'runtime_after'):
                receipt[key].pop('command_resolution_policy', None)
            self.assertFalse(module.reusable(receipt, root, command))

    def test_runtime_uses_default_search_path_for_empty_execution_environment(self):
        import hashlib
        import os
        import shutil
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decoy = root / 'sh'
            decoy.write_text('#!/bin/sh\nexit 99\n')
            decoy.chmod(0o700)
            expected = hashlib.sha256(Path(shutil.which('sh', path=os.defpath)).read_bytes()).hexdigest()
            with patch.dict(os.environ, PATH=str(root)):
                actual = module.runtime(['sh'], root, execution_env={})
            self.assertEqual(actual['command_executable_sha256'], expected)

    def test_reuse_cannot_change_declared_input_contract(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('one')
            (root / 'dependency').write_text('two')
            command = [sys.executable, '-c', 'pass']
            receipt = module.execute(root, ['input'], command, 5)
            self.assertFalse(module.reusable(receipt, root, command, paths=['input', 'dependency']))

    def test_reuse_requires_same_source_dependencies_environment_and_command(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('artifact', 'lock', 'environment'):
                (root / name).write_text('original')
            command = [sys.executable, '-c', 'pass']
            receipt = module.execute(root, ['artifact', 'lock', 'environment'], command, 5)
            self.assertTrue(module.reusable(receipt, root, command))
            for name in ('artifact', 'lock', 'environment'):
                (root / name).write_text('changed')
                self.assertFalse(module.reusable(receipt, root, command))
                (root / name).write_text('original')
            self.assertFalse(module.reusable(receipt, root, command + ['different']))
            receipt['runtime']['python'] = 'different runtime'
            self.assertFalse(module.reusable(receipt, root, command))

    def test_cli_round_trip_and_refusal_preserves_receipt(self):
        import json
        import subprocess
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            receipt = root / 'receipt.json'
            base = [sys.executable, str(Path(__file__).with_name('check_receipt.py')), 'run', '--workspace', str(root),
                    '--receipt', str(receipt), '--path', 'input', '--', sys.executable, '-c', 'pass']
            result = subprocess.run(base, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            before = receipt.read_bytes()
            base[2] = 'reuse'
            result = subprocess.run(base, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            (root / 'input').write_text('drift')
            result = subprocess.run(base, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(receipt.read_bytes(), before)

    def test_run_or_reuse_executes_once_and_preserves_stale_evidence(self):
        import subprocess, json
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'input').write_text('fixture')
            receipt = root/'receipt.json'
            argv = [sys.executable, str(Path(__file__).with_name('check_receipt.py')), 'run-or-reuse', '--workspace', str(root),
                    '--receipt', str(receipt), '--path', 'input', '--', sys.executable, '-c', 'pass']
            first = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)['execution'], 'executed')
            saved = receipt.read_bytes()
            second = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)['execution'], 'reused')
            (root/'input').write_text('changed')
            third = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(third.returncode, 2)
            self.assertEqual(receipt.read_bytes(), saved)

    def test_cli_reuse_cannot_omit_external_input_contract(self):
        import subprocess
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            (root / 'dependency.lock').write_text('pinned')
            argv = [sys.executable, str(Path(__file__).with_name('check_receipt.py')), 'run', '--workspace', str(root),
                    '--receipt', str(root / 'receipt.json'), '--path', 'input',
                    '--external-path', 'dependency.lock', '--', sys.executable, '-c', 'pass']
            result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            argv[2] = 'reuse'
            omitted = argv[:9] + argv[11:]
            result = subprocess.run(omitted, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_failed_diagnostics_and_command_never_store_credential_values(self):
        import os
        from unittest.mock import patch
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            with patch.dict(os.environ, {'TEST_API_TOKEN': 'sensitive-fixture-token'}):
                command = [sys.executable, '-c', 'print("sensitive-fixture-token"); raise SystemExit(1)']
                receipt = module.execute(root, ['input'], command, 5)
                self.assertNotIn('sensitive-fixture-token', str(receipt))
                self.assertIn('[REDACTED]', receipt['diagnostic'])

    def test_shell_last_command_success_cannot_mask_failed_check(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            command = ['sh', '-c', 'false; true']
            receipt = module.execute(root, ['input'], command, 5)
            self.assertEqual(receipt['exit_code'], 0)
            self.assertNotEqual(receipt['outcome'], 'passed')
            self.assertFalse(module.reusable(receipt, root, command))
            receipt['outcome'] = 'passed'  # Legacy last-command-only receipt.
            self.assertFalse(module.reusable(receipt, root, command))

    def test_failed_check_retains_diagnostic_without_retry(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            receipt = module.execute(root, ['input'], [sys.executable, '-c',
                                     'print("fixture failure detail"); raise SystemExit(2)'], 5)
            self.assertIn('fixture failure detail', receipt.get('diagnostic', ''))
            self.assertEqual(receipt['attempts'], 1)

    def test_timeout_stops_descendants(self):
        import time
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('fixture')
            child = 'import time; from pathlib import Path; time.sleep(0.4); Path("escaped").touch()'
            parent = f'import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", {child!r}]); time.sleep(5)'
            receipt = module.execute(root, ['input'], [sys.executable, '-c', parent], 0.15)
            self.assertEqual(receipt['outcome'], 'timeout')
            time.sleep(0.5)
            self.assertFalse((root / 'escaped').exists(), 'timed-out check left a live descendant')

    def test_failure_timeout_and_in_check_drift_cannot_qualify(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'artifact').write_text('original')
            for code, timeout in [('raise SystemExit(1)', 5),
                                  ('import time; time.sleep(5)', 0.05),
                                  ('from pathlib import Path; Path("artifact").write_text("changed")', 5)]:
                command = [sys.executable, '-c', code]
                receipt = module.execute(root, ['artifact'], command, timeout)
                self.assertFalse(module.reusable(receipt, root, command))
                self.assertEqual(receipt['attempts'], 1)
                self.assertIn(receipt['outcome'], ('failed', 'timeout', 'source_changed'))


class CandidateReceiptTests(unittest.TestCase):
    load = ReceiptTests.load

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.root / 'input').write_text('base')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        import subprocess
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def identity(self):
        import candidate_identity
        self.git('branch', 'candidate')
        return candidate_identity.capture(self.root, self.base, 'candidate')

    def test_python_import_does_not_contaminate_exact_candidate(self):
        import os
        from unittest.mock import patch
        module = self.load()
        (self.root / 'dependency.py').write_text('value = 42\n')
        (self.root / 'check.py').write_text('import dependency; assert dependency.value == 42\n')
        self.git('add', 'dependency.py', 'check.py')
        self.git('commit', '-qm', 'python check')
        candidate = self.identity()
        command = [sys.executable, 'check.py']
        with patch.dict(os.environ, PYTHONDONTWRITEBYTECODE='', PWD=str(self.root)):
            receipt = module.execute(self.root, ['dependency.py', 'check.py'], command, 10,
                                     candidate=candidate)
            self.assertEqual(receipt['outcome'], 'passed', receipt.get('generated_files'))
            self.assertEqual(receipt['qualification'], 'exact_candidate')
            self.assertEqual(receipt['generated_files'], [])
            self.assertTrue(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_external_script_argv_cannot_qualify_clean_candidate(self):
        module = self.load()
        candidate = self.identity()
        with tempfile.TemporaryDirectory() as outside:
            script = Path(outside) / 'helper.py'
            script.write_text('print("augmented local check")\n')
            command = [sys.executable, '-B', str(script)]
            receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
            self.assertEqual(receipt['outcome'], 'passed')
            self.assertNotEqual(receipt['qualification'], 'exact_candidate')
            self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_embedded_shared_checkout_read_cannot_qualify(self):
        module = self.load()
        candidate = self.identity()
        dependency = self.root / 'untracked-dependency'
        dependency.write_text('outside candidate')
        command = [sys.executable, '-c', f'from pathlib import Path; assert Path({str(dependency)!r}).read_text()']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        self.assertNotEqual(receipt['qualification'], 'exact_candidate')
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_new_untracked_dependency_cannot_qualify(self):
        module = self.load()
        candidate = self.identity()
        command = [sys.executable, '-c', 'from pathlib import Path; p=Path("not-in-candidate.py"); p.write_text("VALUE=1"); assert p.read_text()']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'undeclared_generated_files')
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_declared_generated_output_preserves_only_narrow_evidence(self):
        module = self.load()
        candidate = self.identity()
        command = [sys.executable, '-c', 'from pathlib import Path; Path("report.json").write_text("{}")']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate,
                                 generated_outputs=['report.json'])
        self.assertEqual(receipt['outcome'], 'passed')
        self.assertEqual(receipt['generated_outputs'], ['report.json'])
        self.assertNotEqual(receipt['qualification'], 'exact_candidate')
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))
        with self.assertRaisesRegex(ValueError, 'output'):
            module.execute(self.root, ['input'], command, 5, candidate=candidate,
                           generated_outputs=['not-in-candidate.py'])

    def test_transient_generated_source_cannot_qualify(self):
        module = self.load()
        candidate = self.identity()
        command = [sys.executable, '-c', 'from pathlib import Path; p=Path("transient.py"); p.write_text("VALUE=1"); assert p.read_text(); p.unlink()']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        self.assertNotEqual(receipt['qualification'], 'exact_candidate')
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_pre_repair_exact_receipts_cannot_be_reused(self):
        module = self.load()
        candidate = self.identity()
        command = [sys.executable, '-c', 'pass']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        receipt.pop('qualification_policy', None)
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_candidate_symlink_to_shared_checkout_is_refused(self):
        module = self.load()
        dependency = self.root / 'untracked-dependency'
        dependency.write_text('outside candidate')
        (self.root / 'linked-input').symlink_to(dependency)
        self.git('add', 'linked-input')
        self.git('commit', '-qm', 'unsafe symlink fixture')
        self.base = self.git('rev-parse', 'HEAD')
        candidate = self.identity()
        with self.assertRaisesRegex(ValueError, 'symlink'):
            module.execute(self.root, ['input'], [sys.executable, '-c', 'pass'], 5,
                           candidate=candidate)

    def test_candidate_ref_drift_and_undeclared_tracked_drift_invalidate(self):
        module = self.load()
        candidate = self.identity()
        command = [sys.executable, '-c', 'pass']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        (self.root / 'input').write_text('next')
        self.git('add', 'input')
        self.git('commit', '-qm', 'next')
        self.git('branch', '-f', 'candidate', 'HEAD')
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))
        with self.assertRaises(ValueError):
            module.execute(self.root, ['input'], command, 5, candidate=candidate)

    def test_external_dependencies_reject_reuse_and_drift_during_check(self):
        module = self.load()
        candidate = self.identity()
        (self.root / 'external-lock').write_text('one')
        command = [sys.executable, '-c', 'pass']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate,
                                 external_paths=['external-lock'])
        self.assertTrue(module.reusable(receipt, self.root, command, candidate=candidate))
        (self.root / 'external-lock').write_text('two')
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_named_scope_is_preserved_and_scope_changes_reject_reuse(self):
        import inspect
        module = self.load()
        self.assertIn('qualification_scope', inspect.signature(module.execute).parameters)
        candidate = self.identity()
        command = [sys.executable, '-c', 'pass']
        scope = {'platform': 'linux-native', 'backend': 'offline', 'mode': 'fixture',
                 'toolchain': {'python': sys.version}}
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate,
                                 qualification_scope=scope)
        self.assertEqual(receipt['qualification_scope'], scope)
        self.assertTrue(module.reusable(receipt, self.root, command, candidate=candidate,
                                        qualification_scope=scope))
        for key, value in [('platform', 'android'), ('backend', 'provider-x'),
                           ('mode', 'live'), ('toolchain', {'python': 'different'})]:
            changed = dict(scope, **{key: value})
            self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate,
                                             qualification_scope=changed), key)
        with self.assertRaises(ValueError):
            module.execute(self.root, ['input'], command, 5, candidate=candidate,
                           qualification_scope={'platform': 'linux-native'})

    def test_exact_candidate_cli_reports_execution_vs_reuse(self):
        import json
        import subprocess
        module = self.load()
        candidate = self.identity()
        receipt = self.root / 'receipt.json'
        argv = [sys.executable, str(Path(__file__).with_name('check_receipt.py')), 'run', '--workspace', str(self.root),
                '--receipt', str(receipt), '--path', 'input', '--base', self.base,
                '--candidate', 'candidate', '--tree', candidate['candidate_tree'],
                '--timeout', '301', '--platform', 'linux-native', '--backend', 'offline',
                '--mode', 'fixture', '--toolchain', 'python=' + sys.version,
                '--', sys.executable, '-c', 'pass']
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['execution'], 'executed')
        argv[2] = 'reuse'
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['execution'], 'reused')
        self.assertEqual(report['attempts'], 0)
        self.assertGreaterEqual(report['elapsed_seconds'], 0)

    def test_exact_cli_reuse_ignores_shell_last_command_metadata(self):
        import json, os, subprocess
        module = self.load()
        candidate = self.identity()
        receipt = self.root / 'receipt.json'
        command = [sys.executable, '-c', 'pass']
        argv = [sys.executable, str(Path(__file__).with_name('check_receipt.py')), 'run', '--workspace', str(self.root),
                '--receipt', str(receipt), '--path', 'input', '--base', self.base,
                '--candidate', 'candidate', '--tree', candidate['candidate_tree'],
                '--', *command]
        environment = dict(os.environ, _='/previous/shell-command')
        result = subprocess.run(argv, env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        saved = receipt.read_bytes()
        argv[2] = 'reuse'
        environment['_'] = '/next/shell-command'
        result = subprocess.run(argv, env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['execution'], 'reused')
        environment['HERMES_KANBAN_TASK'] = 'different-authority'
        result = subprocess.run(argv, env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(receipt.read_bytes(), saved)

    def test_isolated_head_change_cannot_qualify_even_with_same_tree(self):
        module = self.load()
        candidate = self.identity()
        self.git('commit', '--allow-empty', '-qm', 'empty next')
        next_commit = self.git('rev-parse', 'HEAD')
        receipt = module.execute(self.root, ['input'], ['git', 'checkout', '--detach', next_commit],
                                 5, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'candidate_changed')

    def test_prerequisite_ref_moving_during_check_invalidates_receipt(self):
        import candidate_identity
        module = self.load()
        self.git('branch', 'sibling')
        self.git('branch', 'candidate')
        candidate = candidate_identity.capture(self.root, self.base, 'candidate', {'sibling': self.base})
        self.git('commit', '--allow-empty', '-qm', 'next sibling')
        next_commit = self.git('rev-parse', 'HEAD')
        receipt = module.execute(self.root, ['input'], ['git', '-C', str(self.root), 'branch', '-f',
                                 'sibling', next_commit], 5, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'candidate_changed')

    def test_repository_root_argument_uses_frozen_candidate_not_dirty_source(self):
        module = self.load()
        script = self.root/'runner.py'
        script.write_text('import sys\nfrom pathlib import Path\nassert (Path(sys.argv[1])/"input").read_text() == "base"\n')
        self.git('add', 'runner.py')
        self.git('commit', '-qm', 'runner')
        self.base = self.git('rev-parse', 'HEAD')
        candidate = self.identity()
        (self.root/'input').write_text('uncommitted unrelated value')
        command = [sys.executable, str(script), str(self.root)]
        receipt = module.execute(self.root, ['input', 'runner.py'], command, 5, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'passed')
        self.assertEqual(receipt['qualification'], 'exact_candidate')
        self.assertTrue(module.reusable(receipt, self.root, command, candidate=candidate))
        self.assertEqual((self.root/'input').read_text(), 'uncommitted unrelated value')

    def test_absolute_workspace_script_executes_candidate_copy(self):
        module = self.load()
        script = self.root / 'runner.py'
        script.write_text('from pathlib import Path\nassert Path("input").read_text() == "base"\n')
        self.git('add', 'runner.py')
        self.git('commit', '-qm', 'runner')
        self.base = self.git('rev-parse', 'HEAD')
        candidate = self.identity()
        script.write_text('raise SystemExit(7)\n')
        command = [sys.executable, str(script)]
        receipt = module.execute(self.root, ['input', 'runner.py'], command, 5, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'passed')
        self.assertTrue(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_candidate_environment_cannot_redirect_git_index_or_python_imports_to_shared_tree(self):
        import os
        from unittest.mock import patch
        module = self.load()
        (self.root / 'fixture_module.py').write_text('VALUE = "base"\n')
        self.git('add', 'fixture_module.py')
        self.git('commit', '-qm', 'module')
        self.base = self.git('rev-parse', 'HEAD')
        candidate = self.identity()
        (self.root / 'fixture_module.py').write_text('VALUE = "dirty"\n')
        # No implicit cache-output allowance: prevent bytecode output explicitly.
        command = [sys.executable, '-B', '-c', 'import os,fixture_module; assert "GIT_INDEX_FILE" not in os.environ; assert fixture_module.VALUE == "base"']
        before_index = (self.root / '.git/index').read_bytes()
        with patch.dict(os.environ, {'GIT_INDEX_FILE': str(self.root / '.git/index'),
                                    'PYTHONPATH': str(self.root)}):
            receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'passed')
        self.assertEqual((self.root / '.git/index').read_bytes(), before_index)

    def test_exact_reuse_revalidates_candidate_input_fingerprints(self):
        module = self.load()
        candidate = self.identity()
        command = [sys.executable, '-c', 'pass']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        receipt['before']['files'][0]['sha256'] = '0' * 64
        receipt['after']['files'][0]['sha256'] = '0' * 64
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))

    def test_undeclared_tracked_candidate_mutation_invalidates_check(self):
        module = self.load()
        (self.root / 'other-source').write_text('original')
        self.git('add', 'other-source')
        self.git('commit', '-qm', 'other source')
        self.base = self.git('rev-parse', 'HEAD')
        candidate = self.identity()
        command = [sys.executable, '-c', 'from pathlib import Path; Path("other-source").write_text("changed")']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'source_changed')
        self.assertFalse(module.reusable(receipt, self.root, command, candidate=candidate))
        self.assertEqual((self.root / 'other-source').read_text(), 'original')

    def test_external_dependency_drift_during_check_invalidates_receipt(self):
        module = self.load()
        candidate = self.identity()
        external = self.root / 'external-lock'
        external.write_text('original')
        command = [sys.executable, '-c', f'from pathlib import Path; Path({str(external)!r}).write_text("changed")']
        receipt = module.execute(self.root, ['input'], command, 5, candidate=candidate,
                                 external_paths=['external-lock'])
        self.assertEqual(receipt['outcome'], 'source_changed')

    def test_exact_candidate_executes_in_isolation_not_dirty_union(self):
        module = self.load()
        candidate = self.identity()
        (self.root / 'input').write_text('dirty unrelated union')
        command = [sys.executable, '-c', 'from pathlib import Path; assert Path("input").read_text() == "base"']
        receipt = module.execute(self.root, ['input'], command, 301, candidate=candidate)
        self.assertEqual(receipt['outcome'], 'passed')
        self.assertEqual(receipt['qualification'], 'exact_candidate')
        self.assertEqual(receipt['candidate'], candidate)
        self.assertTrue(module.reusable(receipt, self.root, command, candidate=candidate))
        (self.root / 'receipt-only.json').write_text('bookkeeping')
        self.assertTrue(module.reusable(receipt, self.root, command, candidate=candidate))
        self.assertEqual((self.root / 'input').read_text(), 'dirty unrelated union')


if __name__ == '__main__':
    unittest.main()
